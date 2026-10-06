"""Integration tests: real routes, real ORM, real SQLite file, faked advisor."""
from __future__ import annotations

from tests.conftest import CLEAN_PLAY, DPI_PLAY, ROUGHING_PLAY


def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index_serves_ui(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "GridironIQ" in r.text


def test_analyze_returns_penalty_with_citation(client) -> None:
    r = client.post("/api/plays", json={"description": DPI_PLAY})
    assert r.status_code == 201
    body = r.json()
    assert body["is_penalty"] is True
    assert body["matches"][0]["code"] == "DPI"
    assert body["matches"][0]["citation"]
    assert body["call_id"] is not None


def test_analyze_returns_no_call_for_clean_play(client) -> None:
    body = client.post("/api/plays", json={"description": CLEAN_PLAY}).json()
    assert body["is_penalty"] is False
    assert body["matches"] == []


def test_analyze_rejects_short_description(client) -> None:
    assert client.post("/api/plays", json={"description": "short"}).status_code == 422


def test_analyze_rejects_missing_field(client) -> None:
    assert client.post("/api/plays", json={}).status_code == 422


def test_advisor_is_invoked_with_engine_codes(client, fake_advisor) -> None:
    client.post("/api/plays", json={"description": ROUGHING_PLAY})
    assert fake_advisor.calls, "advisor should have been consulted"
    _, codes = fake_advisor.calls[-1]
    assert "RTP" in codes


def test_persist_false_skips_the_audit_log(client) -> None:
    body = client.post("/api/plays", json={"description": DPI_PLAY, "persist": False}).json()
    assert body["call_id"] is None
    assert client.get("/api/history").json() == []


def test_rules_endpoint_lists_and_searches(client) -> None:
    assert len(client.get("/api/rules").json()) == 8
    results = client.get("/api/rules", params={"q": "holding"}).json()
    assert [r["code"] for r in results] == ["HLD"]


def test_rule_detail_and_404(client) -> None:
    assert client.get("/api/rules/DPI").json()["name"] == "Defensive Pass Interference"
    assert client.get("/api/rules/NOPE").status_code == 404


def test_history_records_calls_newest_first(client) -> None:
    client.post("/api/plays", json={"description": DPI_PLAY})
    client.post("/api/plays", json={"description": ROUGHING_PLAY})
    history = client.get("/api/history").json()
    assert [h["primary_code"] for h in history] == ["RTP", "DPI"]
    assert history[0]["citations"]


def test_history_filters_by_code(client) -> None:
    client.post("/api/plays", json={"description": DPI_PLAY})
    client.post("/api/plays", json={"description": ROUGHING_PLAY})
    filtered = client.get("/api/history", params={"code": "dpi"}).json()
    assert len(filtered) == 1 and filtered[0]["primary_code"] == "DPI"


def test_history_limit_is_validated(client) -> None:
    assert client.get("/api/history", params={"limit": 0}).status_code == 422


def test_single_call_lookup_and_404(client) -> None:
    call_id = client.post("/api/plays", json={"description": DPI_PLAY}).json()["call_id"]
    assert client.get(f"/api/history/{call_id}").json()["call_id"] == call_id
    assert client.get("/api/history/99999").status_code == 404
