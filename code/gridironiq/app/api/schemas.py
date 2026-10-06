"""Pydantic request/response contracts. Validation lives here, logic does not."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlaySubmission(BaseModel):
    description: str = Field(min_length=10, max_length=2000, description="Structured play description")
    persist: bool = True


class RuleMatchOut(BaseModel):
    code: str
    name: str
    citation: str
    yards: int
    spot_foul: bool
    automatic_first_down: bool
    penalized_team: str
    rationale: str


class AnalysisOut(BaseModel):
    call_id: int | None
    is_penalty: bool
    confidence: float
    play_type: str
    matches: list[RuleMatchOut]
    advisor_note: str = ""


class RuleOut(BaseModel):
    code: str
    name: str
    citation: str
    summary: str
    yards: int
    automatic_first_down: bool
    penalized_side: str


class HistoryItemOut(BaseModel):
    call_id: int
    description: str
    is_penalty: bool
    primary_code: str
    confidence: float
    created_at: datetime
    citations: list[str]
