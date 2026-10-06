"""Integration tests for the persistence layer in isolation from HTTP."""
from __future__ import annotations

from app.data.repositories import CallRepository, RuleRepository
from app.services.advisor import FakePenaltyAdvisor
from app.services.analysis_service import AnalysisService
from app.services.rule_engine import RuleEngine
from tests.conftest import DPI_PLAY


def test_rule_seed_is_idempotent(session) -> None:
    repo = RuleRepository(session)
    assert repo.seed() == 8
    assert repo.seed() == 0
    assert len(repo.list_all()) == 8


def test_call_is_saved_with_rule_references(session) -> None:
    service = AnalysisService(RuleEngine(), FakePenaltyAdvisor(), CallRepository(session))
    result = service.analyze(DPI_PLAY)
    stored = CallRepository(session).get(result.call_id)
    assert stored.primary_code == "DPI"
    assert stored.play.description == DPI_PLAY.strip()
    assert [ref.rule_code for ref in stored.rule_refs] == ["DPI"]


def test_history_respects_limit(session) -> None:
    service = AnalysisService(RuleEngine(), FakePenaltyAdvisor(), CallRepository(session))
    for _ in range(5):
        service.analyze(DPI_PLAY)
    assert len(CallRepository(session).history(limit=3)) == 3
