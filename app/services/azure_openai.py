import json
import logging
from typing import Any

from openai import AzureOpenAI, OpenAI

from app.config import get_settings
from app.db import Interview, TranscriptTurn

logger = logging.getLogger("videoInterview.azure_openai")


def _client() -> AzureOpenAI | OpenAI:
    settings = get_settings()
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        raise RuntimeError("Azure OpenAI endpoint/key are not configured")
    if settings.azure_openai_endpoint.rstrip("/").endswith("/openai/v1"):
        return OpenAI(
            base_url=settings.azure_openai_endpoint.rstrip("/"),
            api_key=settings.azure_openai_api_key,
        )
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def _system_prompt(interview: Interview) -> str:
    return f"""
You are an AI technical interviewer conducting a concise POC interview.
Role: {interview.role}
Skills to assess: {interview.skills}
Duration target: {interview.duration_minutes} minutes.

Ask one clear technical question at a time. Prefer practical questions.
After the candidate answers, ask a brief follow-up if needed, otherwise move to the next topic.
Do not provide the answer. Keep each response under 90 words.
""".strip()


def first_question(interview: Interview) -> str:
    return (
        f"Hello {interview.candidate_name}. I will ask a few technical questions for the "
        f"{interview.role} role. Let's start with {interview.skills}: describe a recent "
        "technical problem you solved in this area and the tradeoffs you considered."
    )


def next_question(interview: Interview, turns: list[TranscriptTurn]) -> str:
    messages: list[dict[str, str]] = [{"role": "system", "content": _system_prompt(interview)}]
    for turn in turns[-10:]:
        role = "assistant" if turn.speaker == "ai" else "user"
        messages.append({"role": role, "content": turn.text})
    messages.append(
        {
            "role": "user",
            "content": "Ask the next best interview question or follow-up based on the conversation so far.",
        }
    )

    settings = get_settings()
    response = _client().chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=messages,
        temperature=0.4,
        max_tokens=220,
    )
    return response.choices[0].message.content or "Tell me more about your technical approach."


def generate_report(interview: Interview, turns: list[TranscriptTurn]) -> dict[str, Any]:
    transcript = "\n".join(f"{turn.speaker.upper()}: {turn.text}" for turn in turns)
    prompt = f"""
Evaluate this technical interview for the role: {interview.role}
Skills: {interview.skills}

Return strict JSON with these keys:
score: integer from 0 to 100
recommendation: one of "strong hire", "hire", "borderline", "no hire"
summary: short paragraph
strengths: array of strings
concerns: array of strings

Transcript:
{transcript}
""".strip()

    settings = get_settings()
    response = _client().chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": "You are a strict technical interview evaluator."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    logger.info(
        "Azure OpenAI report response for interview_id=%s: %s",
        interview.id,
        content,
    )
    try:
        parsed = json.loads(content)
        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            summary = "No summary generated."
    except json.JSONDecodeError as exc:
        logger.error(
            "Failed to parse Azure OpenAI report response for interview_id=%s: %s",
            interview.id,
            content,
            exc_info=exc,
        )
        summary = "No summary generated."
        parsed = {}

    result = {
        "score": int(parsed.get("score", 0)),
        "recommendation": str(parsed.get("recommendation", "borderline")),
        "summary": summary,
        "strengths": "\n".join(parsed.get("strengths", []) or []),
        "concerns": "\n".join(parsed.get("concerns", []) or []),
    }
    logger.info(
        "Azure OpenAI report parsed for interview_id=%s: score=%s recommendation=%s summary_len=%s",
        interview.id,
        result["score"],
        result["recommendation"],
        len(result["summary"]),
    )
    return result
