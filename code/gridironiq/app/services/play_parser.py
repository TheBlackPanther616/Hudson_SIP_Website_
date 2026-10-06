"""Turns a free-text play description into structured PlayFacts.

The parser is intentionally conservative: it only sets a fact to True when the
description contains an unambiguous cue. Anything it cannot establish is left at
its default so the rule engine never fires on an assumption the parser invented.
"""
from __future__ import annotations

import re

from app.services.facts import PlayFacts, PlayType

_PLAY_TYPE_CUES: dict[PlayType, tuple[str, ...]] = {
    PlayType.PASS: ("pass", "throw", "threw", "quarterback drops", "downfield", "receiver"),
    PlayType.KICK: ("punt", "field goal", "kickoff", "kick"),
    PlayType.RUN: ("run", "ran", "handoff", "hand off", "carry", "rush"),
}

_BOOLEAN_CUES: dict[str, tuple[str, ...]] = {
    "offensive_player_moved_before_snap": ("flinch", "moved before the snap", "jumped early", "false start"),
    "defender_in_neutral_zone_at_snap": ("in the neutral zone", "across the line at the snap", "offside"),
    "ball_thrown": ("threw", "thrown", "released the ball", "pass was in the air"),
    "pass_was_catchable": ("catchable", "in stride", "hit him in the hands", "on target"),
    "contact_with_receiver_before_ball_arrival": (
        "before the ball arrived",
        "arrived early",
        "played through the receiver",
        "grabbed the receiver's arm",
    ),
    "contact_beyond_five_yards": ("beyond five yards", "past five yards", "downfield contact"),
    "receiver_had_completed_catch": ("after the catch", "completed the catch", "had possession"),
    "defender_restricted_outside_frame": (
        "outside the frame", "grabbed the jersey", "hooked the arm", "held",
    ),
    "contact_with_passer_after_release": (
        "after the release", "after the ball was out", "late hit on the quarterback",
    ),
    "contact_to_head_or_neck": ("helmet to helmet", "head or neck", "hit high", "to the head"),
    "defenseless_player": ("defenseless", "did not see him coming", "in a defenseless posture"),
}

_LINEMEN_RE = re.compile(r"(\d+)\s+(?:players?|men)\s+on the line", re.IGNORECASE)
_YARD_RE = re.compile(r"(?:at|on) the (?:offense|defense)?\s*(\d{1,2})\s*(?:-|\s)?yard line", re.IGNORECASE)


def detect_play_type(text: str) -> PlayType:
    lowered = text.lower()
    best: tuple[int, PlayType] = (0, PlayType.UNKNOWN)
    for play_type, cues in _PLAY_TYPE_CUES.items():
        hits = sum(1 for cue in cues if cue in lowered)
        if hits > best[0]:
            best = (hits, play_type)
    return best[1]


def parse(text: str) -> PlayFacts:
    """Parse a play description into facts. Never raises on odd input."""
    text = text or ""
    lowered = text.lower()
    facts = PlayFacts(raw_text=text.strip(), play_type=detect_play_type(text))

    for attribute, cues in _BOOLEAN_CUES.items():
        if any(cue in lowered for cue in cues):
            setattr(facts, attribute, True)

    if facts.contact_with_receiver_before_ball_arrival and not facts.ball_thrown:
        # Contact "before the ball arrived" only makes sense if a ball was thrown.
        facts.ball_thrown = True

    if (match := _LINEMEN_RE.search(text)) is not None:
        facts.players_on_line_of_scrimmage = int(match.group(1))

    if (match := _YARD_RE.search(text)) is not None:
        facts.yard_line = int(match.group(1))

    # Offensive holding requires an offensive blocker; the cue phrases above only
    # describe the restriction, so infer the blocker side from context.
    blocker_cues = ("blocker", "lineman", "guard", "tackle")
    if facts.defender_restricted_outside_frame and any(cue in lowered for cue in blocker_cues):
        facts.blocker_is_offensive_player = True

    return facts
