"""Repositories: the only place raw ORM queries are written."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.data.models import CallRuleRef, PenaltyCallRecord, PlayRecord, RuleRecord
from app.services.facts import PenaltyDecision, PlayFacts
from app.services.rule_library import all_rules


class RuleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def seed(self) -> int:
        """Load the in-code rule library into the database. Idempotent."""
        existing = {code for (code,) in self._session.execute(select(RuleRecord.code))}
        added = 0
        for rule in all_rules():
            if rule.code in existing:
                continue
            self._session.add(
                RuleRecord(
                    code=rule.code,
                    name=rule.name,
                    citation=rule.citation,
                    summary=rule.summary,
                    yards=rule.yards,
                    automatic_first_down=rule.automatic_first_down,
                    penalized_side=rule.penalized_side,
                )
            )
            added += 1
        self._session.commit()
        return added

    def list_all(self) -> list[RuleRecord]:
        return list(self._session.execute(select(RuleRecord).order_by(RuleRecord.code)).scalars())


class CallRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, facts: PlayFacts, decision: PenaltyDecision) -> int:
        play = PlayRecord(
            description=facts.raw_text,
            play_type=facts.play_type.value,
            facts_json=json.dumps(facts.as_dict(), default=str),
        )
        self._session.add(play)
        self._session.flush()

        call = PenaltyCallRecord(
            play_id=play.id,
            is_penalty=decision.is_penalty,
            primary_code=decision.primary.code if decision.primary else "",
            confidence=decision.confidence,
            advisor_note=decision.advisor_note,
        )
        self._session.add(call)
        self._session.flush()

        for index, match in enumerate(decision.matches):
            self._session.add(
                CallRuleRef(
                    call_id=call.id,
                    rule_code=match.code,
                    citation=match.citation,
                    rationale=match.rationale,
                    ordinal=index,
                )
            )
        self._session.commit()
        return call.id

    def get(self, call_id: int) -> PenaltyCallRecord | None:
        stmt = (
            select(PenaltyCallRecord)
            .options(selectinload(PenaltyCallRecord.rule_refs), selectinload(PenaltyCallRecord.play))
            .where(PenaltyCallRecord.id == call_id)
        )
        return self._session.execute(stmt).scalars().first()

    def history(self, limit: int = 50, code: str | None = None) -> list[PenaltyCallRecord]:
        stmt = (
            select(PenaltyCallRecord)
            .options(selectinload(PenaltyCallRecord.rule_refs), selectinload(PenaltyCallRecord.play))
            .order_by(PenaltyCallRecord.id.desc())
            .limit(limit)
        )
        if code:
            stmt = stmt.where(PenaltyCallRecord.primary_code == code.upper())
        return list(self._session.execute(stmt).scalars())
