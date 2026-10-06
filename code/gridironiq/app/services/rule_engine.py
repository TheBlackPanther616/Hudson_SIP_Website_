"""Evaluates PlayFacts against the rule library.

Pure and deterministic: same facts in, same decision out. Every branch here is
covered by unit tests that need neither a database nor a network call.
"""
from __future__ import annotations

from app.services.facts import PenaltyDecision, PlayFacts, PlayType, RuleMatch
from app.services.rule_library import Rule, all_rules


class RuleEngine:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules = sorted(rules if rules is not None else all_rules(), key=lambda r: r.priority)

    def evaluate(self, facts: PlayFacts) -> PenaltyDecision:
        matches: list[RuleMatch] = []
        for rule in self._rules:
            match = rule.evaluate(facts)
            if match is not None:
                matches.append(match)
        return PenaltyDecision(
            is_penalty=bool(matches),
            matches=matches,
            confidence=self.score(facts, matches),
        )

    def score(self, facts: PlayFacts, matches: list[RuleMatch]) -> float:
        """Confidence reflects how much of the decision rests on parsed evidence.

        A no-call on an unparseable description is low confidence; a single clean
        match on a recognized play type is high. Competing matches lower it,
        because the official has a judgment call to make between them.
        """
        if not facts.raw_text.strip():
            return 0.0
        base = 0.55 if facts.play_type is PlayType.UNKNOWN else 0.75
        if matches:
            base += 0.15
            base -= 0.10 * (len(matches) - 1)
        else:
            base -= 0.10
        return round(max(0.05, min(base, 0.95)), 2)
