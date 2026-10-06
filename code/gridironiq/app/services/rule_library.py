"""The rule library: penalty rules expressed as data plus a pure predicate.

Rules are deterministic and free of side effects by design. Every rule carries
the citation it was derived from, so the API can always answer "why".
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.services.facts import PlayFacts, PlayType, RuleMatch


@dataclass(frozen=True)
class Rule:
    code: str
    name: str
    citation: str
    summary: str
    yards: int
    automatic_first_down: bool
    penalized_side: str  # "offense" or "defense"
    predicate: Callable[[PlayFacts], bool]
    rationale: str
    priority: int = 50  # lower number fires first when several rules match
    spot_foul: bool = False

    def evaluate(self, facts: PlayFacts) -> RuleMatch | None:
        if not self.predicate(facts):
            return None
        return RuleMatch(
            code=self.code,
            name=self.name,
            citation=self.citation,
            yards=self.yards,
            automatic_first_down=self.automatic_first_down,
            penalized_team=self.penalized_side,
            rationale=self.rationale,
            spot_foul=self.spot_foul,
        )


def _false_start(f: PlayFacts) -> bool:
    return f.offensive_player_moved_before_snap


def _illegal_formation(f: PlayFacts) -> bool:
    return f.players_on_line_of_scrimmage < 7


def _offside(f: PlayFacts) -> bool:
    return f.defender_in_neutral_zone_at_snap


def _defensive_pass_interference(f: PlayFacts) -> bool:
    return (
        f.play_type is PlayType.PASS
        and f.ball_thrown
        and f.pass_was_catchable
        and f.contact_with_receiver_before_ball_arrival
        and not f.receiver_had_completed_catch
    )


def _illegal_contact(f: PlayFacts) -> bool:
    return (
        f.play_type is PlayType.PASS
        and f.contact_beyond_five_yards
        and not f.ball_thrown
    )


def _offensive_holding(f: PlayFacts) -> bool:
    return f.defender_restricted_outside_frame and f.blocker_is_offensive_player


def _roughing_the_passer(f: PlayFacts) -> bool:
    return f.contact_with_passer_after_release


def _unnecessary_roughness(f: PlayFacts) -> bool:
    return f.contact_to_head_or_neck and f.defenseless_player


RULES: list[Rule] = [
    Rule(
        code="RTP",
        name="Roughing the Passer",
        citation="Rule 12, Section 2, Article 9",
        summary="A defender may not unnecessarily contact the passer after the ball has left his hand.",
        yards=15,
        automatic_first_down=True,
        penalized_side="defense",
        predicate=_roughing_the_passer,
        rationale=(
            "Contact was made with the passer after the ball was released, which the rule "
            "treats as unnecessary contact regardless of intent."
        ),
        priority=10,
    ),
    Rule(
        code="UNR",
        name="Unnecessary Roughness",
        citation="Rule 12, Section 2, Article 8",
        summary="Forcible contact to the head or neck area of a defenseless player is prohibited.",
        yards=15,
        automatic_first_down=True,
        penalized_side="defense",
        predicate=_unnecessary_roughness,
        rationale=(
            "The receiver met the defenseless-player criteria and absorbed forcible contact "
            "to the head or neck area."
        ),
        priority=15,
    ),
    Rule(
        code="DPI",
        name="Defensive Pass Interference",
        citation="Rule 8, Section 5, Article 2",
        summary=(
            "Contact that significantly hinders an eligible receiver's opportunity to catch "
            "a catchable pass."
        ),
        yards=0,
        automatic_first_down=True,
        penalized_side="defense",
        predicate=_defensive_pass_interference,
        rationale=(
            "The pass was catchable and contact occurred before the ball arrived, hindering "
            "the receiver's opportunity to make the catch. Enforced as a spot foul."
        ),
        priority=20,
        spot_foul=True,
    ),
    Rule(
        code="ILC",
        name="Illegal Contact",
        citation="Rule 8, Section 4, Article 3",
        summary=(
            "A defender may not contact a receiver more than five yards downfield before the "
            "pass is thrown."
        ),
        yards=5,
        automatic_first_down=True,
        penalized_side="defense",
        predicate=_illegal_contact,
        rationale=(
            "Contact occurred beyond the five-yard chuck zone while the ball was still in the "
            "passer's hand."
        ),
        priority=30,
    ),
    Rule(
        code="OFF",
        name="Defensive Offside",
        citation="Rule 7, Section 4, Article 4",
        summary="A defensive player may not be in the neutral zone when the ball is snapped.",
        yards=5,
        automatic_first_down=False,
        penalized_side="defense",
        predicate=_offside,
        rationale="A defensive player was inside the neutral zone at the moment of the snap.",
        priority=40,
    ),
    Rule(
        code="HLD",
        name="Offensive Holding",
        citation="Rule 12, Section 1, Article 3",
        summary="An offensive blocker may not grasp or restrict a defender outside the frame of the body.",
        yards=10,
        automatic_first_down=False,
        penalized_side="offense",
        predicate=_offensive_holding,
        rationale=(
            "The blocker restricted the defender outside the frame of the body, materially "
            "affecting his path to the ball."
        ),
        priority=45,
    ),
    Rule(
        code="FST",
        name="False Start",
        citation="Rule 7, Section 4, Article 2",
        summary="An offensive player in a set position may not move before the snap.",
        yards=5,
        automatic_first_down=False,
        penalized_side="offense",
        predicate=_false_start,
        rationale="An offensive player who had come set moved prior to the snap.",
        priority=50,
    ),
    Rule(
        code="ILF",
        name="Illegal Formation",
        citation="Rule 7, Section 5, Article 1",
        summary="The offense must have at least seven players on the line of scrimmage at the snap.",
        yards=5,
        automatic_first_down=False,
        penalized_side="offense",
        predicate=_illegal_formation,
        rationale="The offense lined up with fewer than seven players on the line of scrimmage.",
        priority=55,
    ),
]


def all_rules() -> list[Rule]:
    return list(RULES)


def find_rule(code: str) -> Rule | None:
    return next((r for r in RULES if r.code == code.upper()), None)


def search_rules(query: str) -> list[Rule]:
    q = (query or "").lower().strip()
    if not q:
        return all_rules()
    return [
        r
        for r in RULES
        if q in r.name.lower()
        or q in r.summary.lower()
        or q in r.citation.lower()
        or q == r.code.lower()
    ]
