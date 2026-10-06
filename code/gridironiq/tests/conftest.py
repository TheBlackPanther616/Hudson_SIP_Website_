"""Shared fixtures.

Every test that touches the stack runs against a temporary SQLite file and the
FakePenaltyAdvisor, so no test depends on network availability or model output.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import dependencies
from app.data.db import make_session_factory
from app.data.repositories import CallRepository
from app.main import create_app
from app.services.advisor import FakePenaltyAdvisor
from app.services.analysis_service import AnalysisService
from app.services.rule_engine import RuleEngine


@pytest.fixture
def session_factory(tmp_path):
    return make_session_factory(f"sqlite:///{tmp_path/'test.db'}")


@pytest.fixture
def session(session_factory) -> Iterator[Session]:
    s = session_factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def fake_advisor() -> FakePenaltyAdvisor:
    return FakePenaltyAdvisor()


@pytest.fixture
def client(session_factory, fake_advisor) -> Iterator[TestClient]:
    """A TestClient with the database and the advisor both swapped for test doubles."""
    app = create_app()

    def _session_override() -> Iterator[Session]:
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    def _service_override(session: Session) -> AnalysisService:
        return AnalysisService(RuleEngine(), fake_advisor, CallRepository(session))

    app.dependency_overrides[dependencies.get_session] = _session_override
    original = dependencies.get_analysis_service
    dependencies.get_analysis_service = _service_override
    # routes.py imported the symbol directly, so patch it there too
    from app.api import routes

    routes.get_analysis_service = _service_override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        dependencies.get_analysis_service = original
        routes.get_analysis_service = original
        app.dependency_overrides.clear()


DPI_PLAY = (
    "The quarterback threw a catchable pass down the right sideline and the cornerback "
    "grabbed the receiver's arm before the ball arrived."
)
ROUGHING_PLAY = (
    "The quarterback released the ball and the edge rusher made contact after the release, "
    "driving him to the turf."
)
CLEAN_PLAY = (
    "The offense broke the huddle, lined up in a standard formation, and the running back "
    "was tackled after a short gain."
)
