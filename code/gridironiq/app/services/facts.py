"""Domain value objects shared across the service layer.

No dependency on FastAPI or SQLAlchemy lives in this module. Keeping the domain
vocabulary isolated is what allows the rule engine to be unit tested without a
web server or a database.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PlayType(str, Enum):
    PASS = "pass"
    RUN = "run"
    KICK = "kick"
    UNKNOWN = "unknown"


@dataclass
class PlayFacts:
    """Normalized, machine-checkable description of a single football play."""

    play_type: PlayType = PlayType.UNKNOWN
    raw_text: str = ""
    # Pre-snap
    offensive_player_moved_before_snap: bool = False
    players_on_line_of_scrimmage: int = 7
    defender_in_neutral_zone_at_snap: bool = False
    # Passing
    ball_thrown: bool = False
    pass_was_catchable: bool = False
    contact_with_receiver_before_ball_arrival: bool = False
    contact_beyond_five_yards: bool = False
    receiver_had_completed_catch: bool = False
    # Contact and blocking
    defender_restricted_outside_frame: bool = False
    blocker_is_offensive_player: bool = False
    contact_with_passer_after_release: bool = False
    contact_to_head_or_neck: bool = False
    defenseless_player: bool = False
    # Situational
    offending_player: str = ""
    yard_line: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["play_type"] = self.play_type.value
        return data


@dataclass(frozen=True)
class RuleMatch:
    """A single rule that fired against a set of play facts."""

    code: str
    name: str
    citation: str
    yards: int
    automatic_first_down: bool
    penalized_team: str
    rationale: str
    spot_foul: bool = False


@dataclass
class PenaltyDecision:
    """The engine's full answer for one play."""

    is_penalty: bool
    matches: list[RuleMatch] = field(default_factory=list)
    confidence: float = 0.0
    advisor_note: str = ""

    @property
    def primary(self) -> RuleMatch | None:
        return self.matches[0] if self.matches else None
