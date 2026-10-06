"""HTTP routers. Thin by policy: validate, delegate, shape the response."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_analysis_service, get_session
from app.api.schemas import AnalysisOut, HistoryItemOut, PlaySubmission, RuleMatchOut, RuleOut
from app.data.repositories import CallRepository
from app.services import rule_library

plays_router = APIRouter(prefix="/api/plays", tags=["plays"])
rules_router = APIRouter(prefix="/api/rules", tags=["rules"])
history_router = APIRouter(prefix="/api/history", tags=["history"])


@plays_router.post("", response_model=AnalysisOut, status_code=201)
def analyze_play(submission: PlaySubmission, session: Session = Depends(get_session)) -> AnalysisOut:
    """Core feature 1: submit a play description, receive a penalty determination."""
    service = get_analysis_service(session)
    result = service.analyze(submission.description, persist=submission.persist)
    return AnalysisOut(
        call_id=result.call_id,
        is_penalty=result.decision.is_penalty,
        confidence=result.decision.confidence,
        play_type=result.facts.play_type.value,
        advisor_note=result.decision.advisor_note,
        matches=[RuleMatchOut(**m.__dict__) for m in result.decision.matches],
    )


@rules_router.get("", response_model=list[RuleOut])
def list_rules(
    q: str = Query("", description="Free-text search across name, summary, citation"),
) -> list[RuleOut]:
    """Core feature 2: search the rule library."""
    return [
        RuleOut(
            code=r.code,
            name=r.name,
            citation=r.citation,
            summary=r.summary,
            yards=r.yards,
            automatic_first_down=r.automatic_first_down,
            penalized_side=r.penalized_side,
        )
        for r in rule_library.search_rules(q)
    ]


@rules_router.get("/{code}", response_model=RuleOut)
def get_rule(code: str) -> RuleOut:
    rule = rule_library.find_rule(code)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"No rule with code {code!r}")
    return RuleOut(
        code=rule.code,
        name=rule.name,
        citation=rule.citation,
        summary=rule.summary,
        yards=rule.yards,
        automatic_first_down=rule.automatic_first_down,
        penalized_side=rule.penalized_side,
    )


@history_router.get("", response_model=list[HistoryItemOut])
def list_history(
    limit: int = Query(50, ge=1, le=500),
    code: str | None = Query(None),
    session: Session = Depends(get_session),
) -> list[HistoryItemOut]:
    """Core feature 3: reviewable audit log of every call the system made."""
    repo = CallRepository(session)
    return [
        HistoryItemOut(
            call_id=c.id,
            description=c.play.description if c.play else "",
            is_penalty=c.is_penalty,
            primary_code=c.primary_code,
            confidence=c.confidence,
            created_at=c.created_at,
            citations=[ref.citation for ref in sorted(c.rule_refs, key=lambda r: r.ordinal)],
        )
        for c in repo.history(limit=limit, code=code)
    ]


@history_router.get("/{call_id}", response_model=HistoryItemOut)
def get_call(call_id: int, session: Session = Depends(get_session)) -> HistoryItemOut:
    call = CallRepository(session).get(call_id)
    if call is None:
        raise HTTPException(status_code=404, detail=f"No call with id {call_id}")
    return HistoryItemOut(
        call_id=call.id,
        description=call.play.description if call.play else "",
        is_penalty=call.is_penalty,
        primary_code=call.primary_code,
        confidence=call.confidence,
        created_at=call.created_at,
        citations=[ref.citation for ref in sorted(call.rule_refs, key=lambda r: r.ordinal)],
    )
