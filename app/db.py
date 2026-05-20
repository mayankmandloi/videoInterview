from datetime import datetime, timezone
from enum import Enum
from typing import Generator

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class InterviewStatus(str, Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    candidate_name: Mapped[str] = mapped_column(String(200))
    candidate_email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(200))
    skills: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=20)
    status: Mapped[str] = mapped_column(String(32), default=InterviewStatus.scheduled.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    turns: Mapped[list["TranscriptTurn"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="TranscriptTurn.id",
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        uselist=False,
    )
    cheating_flags: Mapped[list["CheatingFlag"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="CheatingFlag.id",
    )


class TranscriptTurn(Base):
    __tablename__ = "transcript_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    speaker: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    interview: Mapped[Interview] = relationship(back_populates="turns")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), unique=True)
    score: Mapped[int] = mapped_column(Integer)
    recommendation: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(Text)
    strengths: Mapped[str] = mapped_column(Text)
    concerns: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    interview: Mapped[Interview] = relationship(back_populates="report")


class CheatingFlag(Base):
    __tablename__ = "cheating_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    flag_type: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    interview: Mapped[Interview] = relationship(back_populates="cheating_flags")


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
