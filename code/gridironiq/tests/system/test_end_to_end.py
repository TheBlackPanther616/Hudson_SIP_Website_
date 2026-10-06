"""System tests: known plays through the full stack, asserting the outcome an
official would expect. These are the scenarios demonstrated in the presentation.
"""
from __future__ import annotations

import pytest

SCENARIOS = [
    (
        "defensive pass interference",
        "The quarterback threw a catchable pass down the sideline; the cornerback grabbed "
        "the receiver's arm before the ball arrived.",
        "DPI",
    ),
    (
        "roughing the passer",
        "The quarterback released the ball and the defensive end hit him after the release.",
        "RTP",
    ),
    (
        "offensive holding",
        "The left guard, a blocker, hooked the arm of the defender outside the frame as he "
        "worked toward the quarterback.",
        "HLD",
    ),
    (
        "illegal formation",
        "The offense came out with 6 players on the line and snapped the ball immediately.",
        "ILF",
    ),
    (
        "no call",
        "The running back took the handoff, ran off tackle, and was brought down after a "
        "gain of four yards with no contact issues.",
        None,
    ),
]


@pytest.mark.parametrize("label,description,expected_code", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_known_play_scenarios(client, label, description, expected_code) -> None:
    body = client.post("/api/plays", json={"description": description}).json()
    if expected_code is None:
        assert body["is_penalty"] is False, f"{label} should be a no-call"
    else:
        assert body["is_penalty"] is True, f"{label} should be a penalty"
        assert body["matches"][0]["code"] == expected_code


def test_full_officiating_workflow(client) -> None:
    """Submit a play, read the rule it cited, then confirm it appears in the audit log."""
    analysis = client.post("/api/plays", json={"description": SCENARIOS[0][1]}).json()
    code = analysis["matches"][0]["code"]

    rule = client.get(f"/api/rules/{code}").json()
    assert rule["citation"] == analysis["matches"][0]["citation"]

    entry = client.get(f"/api/history/{analysis['call_id']}").json()
    assert entry["primary_code"] == code
    assert rule["citation"] in entry["citations"]
