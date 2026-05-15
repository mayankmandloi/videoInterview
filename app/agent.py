import json
import os

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, inference

from app.db import SessionLocal, TranscriptTurn


load_dotenv()

server = AgentServer()


def _agent_instructions(metadata: dict) -> str:
    candidate = metadata.get("candidate_name", "the candidate")
    role = metadata.get("role", "the role")
    skills = metadata.get("skills", "the listed skills")
    duration = metadata.get("duration_minutes", 20)
    return f"""
You are a professional AI technical interviewer named Intervue Bot.
You are interviewing {candidate} for {role}.
Assess these skills: {skills}.
Target duration: {duration} minutes.

Run a concise technical interview by voice:
- Greet the candidate and explain that you will ask one question at a time.
- Ask practical, role-relevant technical questions.
- Ask follow-ups when answers are vague or need deeper reasoning.
- Do not reveal ideal answers.
- Keep each spoken response under 90 words.
- At the end, summarize that the interview is complete and thank the candidate.
""".strip()


def _text_from_item(item) -> str:
    text_content = getattr(item, "text_content", None)
    if text_content:
        return str(text_content).strip()

    content = getattr(item, "content", None) or []
    text_parts = [part for part in content if isinstance(part, str)]
    return "\n".join(text_parts).strip()


def _save_transcript_turn(interview_id: int, speaker: str, text: str) -> None:
    if not text:
        return

    db = SessionLocal()
    try:
        db.add(TranscriptTurn(interview_id=interview_id, speaker=speaker, text=text))
        db.commit()
    finally:
        db.close()


@server.rtc_session(agent_name=os.getenv("LIVEKIT_AGENT_NAME", "technical-interviewer"))
async def technical_interviewer(ctx: JobContext):
    metadata = json.loads(ctx.job.metadata or "{}")
    interview_id = int(metadata.get("interview_id", 0) or 0)
    session = AgentSession(
        stt=inference.STT(
            model=os.getenv("LIVEKIT_INFERENCE_STT_MODEL", "deepgram/flux-general-en"),
            language=os.getenv("LIVEKIT_INFERENCE_STT_LANGUAGE", "en"),
        ),
        llm=inference.LLM(
            model=os.getenv("LIVEKIT_INFERENCE_LLM_MODEL", "openai/gpt-oss-120b"),
        ),
        tts=inference.TTS(
            model=os.getenv("LIVEKIT_INFERENCE_TTS_MODEL", "cartesia/sonic-3"),
            voice=os.getenv(
                "LIVEKIT_INFERENCE_TTS_VOICE",
                "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
            ),
        ),
    )

    if interview_id:
        @session.on("user_input_transcribed")
        def on_user_input_transcribed(event):
            if not getattr(event, "is_final", False):
                return
            _save_transcript_turn(
                interview_id,
                "candidate",
                str(getattr(event, "transcript", "") or "").strip(),
            )

        @session.on("conversation_item_added")
        def on_conversation_item_added(event):
            item = getattr(event, "item", None)
            if item is None:
                return

            role = getattr(item, "role", "")
            if role == "assistant":
                speaker = "ai"
            elif role == "user":
                return
            else:
                speaker = role or "unknown"

            _save_transcript_turn(interview_id, speaker, _text_from_item(item))

    await session.start(
        room=ctx.room,
        agent=Agent(instructions=_agent_instructions(metadata)),
    )
    await session.generate_reply(
        instructions="Start the interview now with a short greeting and the first technical question."
    )


if __name__ == "__main__":
    cli.run_app(server)
