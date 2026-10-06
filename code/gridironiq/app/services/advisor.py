"""The LLM seam.

The analysis service depends on the PenaltyAdvisor protocol, never on a concrete
model client. FakePenaltyAdvisor makes the entire stack deterministic under test;
ClaudeAdvisor is the production implementation. Isolating the nondeterministic
dependency behind this seam is what keeps the test suite reliable.
"""
from __future__ import annotations

import json
import os
from typing import Protocol

from app.services.facts import PlayFacts


class PenaltyAdvisor(Protocol):
    """Supplies a natural-language second opinion on a parsed play."""

    def review(self, facts: PlayFacts, engine_codes: list[str]) -> str:  # pragma: no cover - protocol
        ...


class FakePenaltyAdvisor:
    """Deterministic stand-in used by every automated test."""

    def __init__(self, note: str = "") -> None:
        self._note = note
        self.calls: list[tuple[PlayFacts, list[str]]] = []

    def review(self, facts: PlayFacts, engine_codes: list[str]) -> str:
        self.calls.append((facts, list(engine_codes)))
        if self._note:
            return self._note
        if engine_codes:
            return f"Engine flagged {', '.join(engine_codes)}; description is consistent with that call."
        return "No rule condition was satisfied by the described play."


class NullAdvisor:
    """Used when no API key is configured. The engine result stands alone."""

    def review(self, facts: PlayFacts, engine_codes: list[str]) -> str:
        return ""


class ClaudeAdvisor:
    """Production advisor. Network failures degrade to an empty note, never a 500."""

    ENDPOINT = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-6") -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model

    def review(self, facts: PlayFacts, engine_codes: list[str]) -> str:
        if not self._api_key:
            return ""
        import httpx

        prompt = (
            "You are assisting a football official. A deterministic rule engine has already "
            "evaluated the play below and returned these penalty codes: "
            f"{engine_codes or ['none']}.\n\n"
            f"Play description: {facts.raw_text}\n"
            f"Parsed facts: {json.dumps(facts.as_dict(), default=str)}\n\n"
            "In two sentences, state whether the description supports that outcome and name any "
            "fact an official would need to confirm on review. Do not invent facts."
        )
        try:
            response = httpx.post(
                self.ENDPOINT,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=20.0,
            )
            response.raise_for_status()
            blocks = response.json().get("content", [])
            return " ".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        except Exception:  # noqa: BLE001 - advisor is advisory; never fail the call
            return ""


def default_advisor() -> PenaltyAdvisor:
    return ClaudeAdvisor() if os.environ.get("ANTHROPIC_API_KEY") else NullAdvisor()
