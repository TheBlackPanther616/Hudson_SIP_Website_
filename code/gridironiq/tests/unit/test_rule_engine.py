"""Unit tests: rule engine only. Facts are constructed directly, bypassing the parser."""
from __future__ import annotations

from app.services.facts import PlayFacts, PlayType
from app.services.rule_engine import RuleEngine
from app.services.rule_library import all_rules, find_rule, search_rules


def engine() -> RuleEngine:
    return RuleEngine()


def test_no_penalty_on_clean_play() -> None:
    facts = PlayFacts(raw_text="clean play", play_type=PlayType.RUN)
    decision = engine().evaluate(facts)
    assert decision.is_penalty is False
    assert decision.matches == []


def test_false_start_fires() -> None:
    facts = PlayFacts(raw_text="x", offensive_player_moved_before_snap=True)
    decision = engine().evaluate(facts)
    assert decision.is_penalty
    assert decision.primary.code == "FST"
    assert decision.primary.yards == 5


def test_illegal_formation_boundary_at_seven() -> None:
    """Seven on the line is legal; six is not. Boundary conditions get their own test."""
    legal = engine().evaluate(PlayFacts(raw_text="x", players_on_line_of_scrimmage=7))
    illegal = engine().evaluate(PlayFacts(raw_text="x", players_on_line_of_scrimmage=6))
    assert legal.is_penalty is False
    assert illegal.primary.code == "ILF"


def test_defensive_pass_interference_requires_catchable_pass() -> None:
    base = dict(
        raw_text="x",
        play_type=PlayType.PASS,
        ball_thrown=True,
        contact_with_receiver_before_ball_arrival=True,
    )
    uncatchable = engine().evaluate(PlayFacts(**base, pass_was_catchable=False))
    catchable = engine().evaluate(PlayFacts(**base, pass_was_catchable=True))
    assert uncatchable.is_penalty is False
    assert catchable.primary.code == "DPI"
    assert catchable.primary.spot_foul is True


def test_no_interference_after_completed_catch() -> None:
    facts = PlayFacts(
        raw_text="x",
        play_type=PlayType.PASS,
        ball_thrown=True,
        pass_was_catchable=True,
        contact_with_receiver_before_ball_arrival=True,
        receiver_had_completed_catch=True,
    )
    assert engine().evaluate(facts).is_penalty is False


def test_illegal_contact_only_before_the_throw() -> None:
    common = dict(raw_text="x", play_type=PlayType.PASS, contact_beyond_five_yards=True)
    thrown = PlayFacts(**common, ball_thrown=True)
    not_thrown = PlayFacts(**common, ball_thrown=False)
    assert engine().evaluate(thrown).is_penalty is False
    assert engine().evaluate(not_thrown).primary.code == "ILC"


def test_holding_requires_offensive_blocker() -> None:
    facts = PlayFacts(
        raw_text="x", defender_restricted_outside_frame=True, blocker_is_offensive_player=False
    )
    assert engine().evaluate(facts).is_penalty is False
    facts.blocker_is_offensive_player = True
    assert engine().evaluate(facts).primary.code == "HLD"


def test_roughing_the_passer_is_automatic_first_down() -> None:
    decision = engine().evaluate(PlayFacts(raw_text="x", contact_with_passer_after_release=True))
    assert decision.primary.code == "RTP"
    assert decision.primary.automatic_first_down is True
    assert decision.primary.penalized_team == "defense"


def test_unnecessary_roughness_requires_defenseless_player() -> None:
    facts = PlayFacts(raw_text="x", contact_to_head_or_neck=True, defenseless_player=False)
    assert engine().evaluate(facts).is_penalty is False
    facts.defenseless_player = True
    assert engine().evaluate(facts).primary.code == "UNR"


def test_matches_are_ordered_by_priority() -> None:
    """Roughing (priority 10) must outrank a false start (priority 50) on the same play."""
    facts = PlayFacts(
        raw_text="x",
        contact_with_passer_after_release=True,
        offensive_player_moved_before_snap=True,
    )
    decision = engine().evaluate(facts)
    assert [m.code for m in decision.matches] == ["RTP", "FST"]


def test_confidence_is_zero_for_empty_description() -> None:
    assert engine().evaluate(PlayFacts(raw_text="   ")).confidence == 0.0


def test_confidence_drops_when_rules_compete() -> None:
    single = engine().evaluate(
        PlayFacts(raw_text="x", play_type=PlayType.PASS, contact_with_passer_after_release=True)
    )
    competing = engine().evaluate(
        PlayFacts(
            raw_text="x",
            play_type=PlayType.PASS,
            contact_with_passer_after_release=True,
            offensive_player_moved_before_snap=True,
        )
    )
    assert competing.confidence < single.confidence


def test_confidence_never_leaves_bounds() -> None:
    for facts in (
        PlayFacts(raw_text="x"),
        PlayFacts(raw_text="x", play_type=PlayType.PASS, contact_with_passer_after_release=True),
        PlayFacts(
            raw_text="x",
            contact_with_passer_after_release=True,
            contact_to_head_or_neck=True,
            defenseless_player=True,
            offensive_player_moved_before_snap=True,
            players_on_line_of_scrimmage=5,
            defender_in_neutral_zone_at_snap=True,
        ),
    ):
        assert 0.0 <= engine().evaluate(facts).confidence <= 1.0


def test_rule_library_lookup() -> None:
    assert find_rule("dpi").name == "Defensive Pass Interference"
    assert find_rule("ZZZ") is None
    assert len(search_rules("")) == len(all_rules())
    assert [r.code for r in search_rules("neutral zone")] == ["OFF"]


def test_every_rule_has_a_citation() -> None:
    assert all(r.citation.strip() for r in all_rules())
