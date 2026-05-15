from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Interview, InterviewStatus, Report, TranscriptTurn, get_db
from app.services.azure_openai import generate_report
from app.services.livekit import build_room_name, create_livekit_token, dispatch_agent


router = APIRouter()


class AnswerPayload(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)


@router.get("/interview/{token}")
def interview_page(request: Request, token: str, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(token=token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview link not found")
    return request.app.state.templates.TemplateResponse(
        "interview.html",
        {
            "request": request,
            "interview": interview,
            "livekit_url": get_settings().livekit_url,
        },
    )


@router.post("/api/interviews/{token}/start")
def start_interview(token: str, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(token=token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview link not found")

    if interview.status == InterviewStatus.scheduled.value:
        interview.status = InterviewStatus.in_progress.value
        db.commit()
    else:
        db.commit()

    room_name = build_room_name(interview.id)
    livekit_token = create_livekit_token(
        f"candidate-{interview.id}",
        room_name,
        name=interview.candidate_name,
    )
    return {
        "room": room_name,
        "livekitToken": livekit_token,
        "livekitUrl": get_settings().livekit_url,
        "agentName": get_settings().livekit_agent_name,
    }


@router.post("/api/interviews/{token}/dispatch-agent")
def dispatch_interview_agent(token: str, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(token=token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview link not found")
    if interview.status == InterviewStatus.completed.value:
        raise HTTPException(status_code=409, detail="Interview is already completed")

    room_name = build_room_name(interview.id)
    try:
        dispatch_id = dispatch_agent(
            room_name,
            {
                "interview_id": interview.id,
                "candidate_name": interview.candidate_name,
                "role": interview.role,
                "skills": interview.skills,
                "duration_minutes": interview.duration_minutes,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to dispatch LiveKit agent: {exc}") from exc
    return {"status": "dispatched", "dispatchId": dispatch_id, "agentName": get_settings().livekit_agent_name}


@router.post("/api/interviews/{token}/answer")
def answer_question(token: str, payload: AnswerPayload, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(token=token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview link not found")
    if interview.status == InterviewStatus.completed.value:
        raise HTTPException(status_code=409, detail="Interview is already completed")

    db.add(TranscriptTurn(interview_id=interview.id, speaker="note", text=payload.answer.strip()))
    db.commit()
    return {"status": "saved"}


@router.post("/api/interviews/{token}/finish")
def finish_interview(token: str, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(token=token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview link not found")

    data = generate_report(interview, interview.turns)
    if interview.report:
        interview.report.score = data["score"]
        interview.report.recommendation = data["recommendation"]
        interview.report.summary = data["summary"]
        interview.report.strengths = data["strengths"]
        interview.report.concerns = data["concerns"]
    else:
        db.add(Report(interview_id=interview.id, **data))
    interview.status = InterviewStatus.completed.value
    db.commit()
    return {"status": "completed", **data}
