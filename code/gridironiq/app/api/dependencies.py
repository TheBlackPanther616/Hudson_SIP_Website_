"""Dependency wiring. Overriding these in tests is how the layers stay swappable."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.data.db import make_session_factory
from app.data.repositories import CallRepository
from app.services.advisor import default_advisor
from app.services.analysis_service import AnalysisService
from app.services.rule_engine import RuleEngine

_session_factory = None


def session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = make_session_factory()
    return _session_factory


def get_session() -> Iterator[Session]:
    session = session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_analysis_service(session: Session) -> AnalysisService:
    return AnalysisService(
        engine=RuleEngine(),
        advisor=default_advisor(),
        repository=CallRepository(session),
    )
