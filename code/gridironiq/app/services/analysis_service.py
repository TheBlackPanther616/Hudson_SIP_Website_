"""Application service: the single entry point for analyzing a play.

Orchestrates parser -> engine -> advisor -> repository. This is the only service
class the API layer talks to, and it knows nothing about HTTP.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services import play_parser
from app.services.advisor import PenaltyAdvisor
from app.services.facts import PenaltyDecision, PlayFacts
from app.services.rule_engine import RuleEngine


@dataclass
class AnalysisResult:
    facts: PlayFacts
    decision: PenaltyDecision
    call_id: int | None = None


class CallRepositoryProtocol:  # structural, satisfied by data.repositories.CallRepository
    def save(self, facts: PlayFacts, decision: PenaltyDecision) -> int:  # pragma: no cover
        raise NotImplementedError


class AnalysisService:
    def __init__(
        self,
        engine: RuleEngine,
        advisor: PenaltyAdvisor,
        repository: CallRepositoryProtocol | None = None,
    ) -> None:
        self._engine = engine
        self._advisor = advisor
        self._repository = repository

    def analyze(self, description: str, persist: bool = True) -> AnalysisResult:
        facts = play_parser.parse(description)
        decision = self._engine.evaluate(facts)
        decision.advisor_note = self._advisor.review(facts, [m.code for m in decision.matches])

        call_id = None
        if persist and self._repository is not None:
            call_id = self._repository.save(facts, decision)
        return AnalysisResult(facts=facts, decision=decision, call_id=call_id)
