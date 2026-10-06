"""Unit tests: parser only. No database, no network, no web server."""
from __future__ import annotations

import pytest

from app.services.facts import PlayType
from app.services.play_parser import detect_play_type, parse


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The quarterback threw a pass to the receiver downfield", PlayType.PASS),
        ("Handoff to the running back who ran off tackle", PlayType.RUN),
        ("The punt was fielded at midfield", PlayType.KICK),
        ("Something happened on the field", PlayType.UNKNOWN),
    ],
)
def test_detect_play_type(text: str, expected: PlayType) -> None:
    assert detect_play_type(text) is expected


def test_parse_returns_defaults_for_empty_input() -> None:
    facts = parse("")
    assert facts.raw_text == ""
    assert facts.play_type is PlayType.UNKNOWN
    assert facts.players_on_line_of_scrimmage == 7


def test_parse_never_raises_on_none() -> None:
    assert parse(None).raw_text == ""


def test_parse_sets_pass_interference_cues() -> None:
    facts = parse(
        "The quarterback threw a catchable pass and the corner grabbed the receiver's arm "
        "before the ball arrived."
    )
    assert facts.play_type is PlayType.PASS
    assert facts.pass_was_catchable
    assert facts.contact_with_receiver_before_ball_arrival


def test_parse_infers_ball_thrown_from_contact_timing() -> None:
    """Contact 'before the ball arrived' is incoherent unless a ball was thrown."""
    facts = parse("The corner arrived early, before the ball arrived, on the receiver.")
    assert facts.ball_thrown is True


def test_parse_extracts_line_of_scrimmage_count() -> None:
    facts = parse("The offense lined up with 6 players on the line and motioned late.")
    assert facts.players_on_line_of_scrimmage == 6


def test_parse_extracts_yard_line() -> None:
    facts = parse("The play began at the 35 yard line and the runner was tackled immediately.")
    assert facts.yard_line == 35


def test_parse_does_not_invent_facts() -> None:
    """A description with no cues must leave every boolean at its default."""
    facts = parse("The team broke the huddle and lined up in a standard formation.")
    booleans = [v for k, v in facts.as_dict().items() if isinstance(v, bool)]
    assert not any(booleans)


def test_parse_requires_blocker_context_for_holding() -> None:
    without_context = parse("The defender was held outside the frame.")
    with_context = parse("The right guard, a blocker, held him outside the frame.")
    assert without_context.blocker_is_offensive_player is False
    assert with_context.blocker_is_offensive_player is True
