"""SQLAlchemy ORM models. The persistence layer knows nothing about HTTP."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class RuleRecord(Base):
    """Rule library persisted for search and reporting."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    citation: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    yards: Mapped[int] = mapped_column(Integer)
    automatic_first_down: Mapped[bool] = mapped_column(Boolean, default=False)
    penalized_side: Mapped[str] = mapped_column(String(16))


class PlayRecord(Base):
    __tablename__ = "plays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text)
    play_type: Mapped[str] = mapped_column(String(16), default="unknown")
    facts_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    call: Mapped[PenaltyCallRecord] = relationship(back_populates="play", uselist=False)


class PenaltyCallRecord(Base):
    __tablename__ = "penalty_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    play_id: Mapped[int] = mapped_column(ForeignKey("plays.id"), index=True)
    is_penalty: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_code: Mapped[str] = mapped_column(String(8), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    advisor_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    play: Mapped[PlayRecord] = relationship(back_populates="call")
    rule_refs: Mapped[list[CallRuleRef]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )


class CallRuleRef(Base):
    """Join table: one call may cite several rules, ordered by priority."""

    __tablename__ = "call_rule_refs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("penalty_calls.id"), index=True)
    rule_code: Mapped[str] = mapped_column(String(8), index=True)
    citation: Mapped[str] = mapped_column(String(120), default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    ordinal: Mapped[int] = mapped_column(Integer, default=0)

    call: Mapped[PenaltyCallRecord] = relationship(back_populates="rule_refs")
