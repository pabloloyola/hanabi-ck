from __future__ import annotations

import pytest

from hanabi_ck.actions import Action
from hanabi_ck.agents import SimpleAgent
from hanabi_ck.backends import HanabiBackend, NativeHanabiBackend, create_backend
from hanabi_ck.engine import Card
from hanabi_ck.observations import CardKnowledge


def test_native_backend_conforms_to_protocol():
    backend = NativeHanabiBackend(num_players=2, seed=0)
    assert isinstance(backend, HanabiBackend)
    assert backend.current_player == 0
    assert backend.score == 0
    assert not backend.done


def test_backend_factory_defaults_are_explicit():
    backend = create_backend("native", num_players=2, seed=0)
    assert isinstance(backend, NativeHanabiBackend)

    with pytest.raises(ValueError, match="Unknown backend"):
        create_backend("not-a-backend", num_players=2, seed=0)


def _hle_or_skip(seed: int = 0):
    from hanabi_ck.backends.hle import HLEHanabiBackend

    try:
        return HLEHanabiBackend(num_players=2, seed=seed)
    except RuntimeError as exc:
        pytest.skip(str(exc))


def test_hle_backend_initial_observation_is_hidden_and_structured():
    backend = _hle_or_skip(seed=0)
    observation = backend.observe(0)

    assert backend.current_player == 0
    assert backend.score == 0
    assert observation.deck_size == 40
    assert observation.information_tokens == 8
    assert observation.life_tokens == 3
    assert 0 not in observation.other_hands
    assert 1 in observation.other_hands
    assert len(observation.own_knowledge) == 5

    for knowledge in observation.own_knowledge:
        assert set(knowledge["possible_colors"]) == {"R", "G", "B", "Y", "W"}
        assert knowledge["possible_ranks"] == [1, 2, 3, 4, 5]


def _mirror_hle_initial_state_into_native(hle, *, seed: int):
    """Build a native state with the same dealt hands."""
    native = NativeHanabiBackend(num_players=2, seed=seed)
    truth = hle.true_state()

    native.hands = [
        [Card(str(card["color"]), int(card["rank"])) for card in hand]
        for hand in truth["hands"]
    ]
    native.knowledge = [
        [CardKnowledge() for _ in hand]
        for hand in native.hands
    ]
    native.deck = [Card("R", 1) for _ in range(int(truth["deck_size"]))]
    native.stacks = dict(truth["stacks"])
    native.discards = []
    native.information_tokens = int(truth["information_tokens"])
    native.life_tokens = int(truth["life_tokens"])
    native.current_player = int(truth["current_player"])
    native.history = []
    native.final_turns_remaining = None
    native.done = False
    return native


def _prepare_native_draw_after_hle_step(
    native,
    hle,
    *,
    actor: int,
    action: Action,
    deck_size_before: int,
) -> None:
    """Feed the HLE-drawn card to native while preserving deck length.

    HLE does not expose undealt card identities. We therefore let HLE sample its
    next card first, recover that card from the actor's newest hand slot, and
    arrange the native deck so its next pop is exactly the same card.
    """
    if action.type not in {"play", "discard"}:
        return

    after = hle.true_state()
    deck_size_after = int(after["deck_size"])
    if deck_size_before == 0:
        assert deck_size_after == 0
        native.deck = []
        return

    assert deck_size_after == deck_size_before - 1
    drawn = after["hands"][actor][-1]
    native.deck = [
        Card("R", 1) for _ in range(deck_size_after)
    ] + [Card(str(drawn["color"]), int(drawn["rank"]))]


def _assert_backend_state_parity(hle, native) -> None:
    hle_state = hle.true_state()
    native_state = native.true_state()

    for key in (
        "hands",
        "stacks",
        "discards",
        "information_tokens",
        "life_tokens",
        "deck_size",
        "final_turns_remaining",
        "score",
    ):
        assert hle_state[key] == native_state[key], key

    assert hle.done == native.done
    if not hle.done:
        assert hle.current_player == native.current_player

    for player in range(hle.num_players):
        hle_obs = hle.observe(player)
        native_obs = native.observe(player)
        assert hle_obs.current_player == native_obs.current_player
        assert hle_obs.other_hands == native_obs.other_hands
        assert hle_obs.own_knowledge == native_obs.own_knowledge
        assert hle_obs.public_knowledge == native_obs.public_knowledge
        assert hle_obs.newest_card_index == native_obs.newest_card_index
        assert hle_obs.provably_playable_indices == native_obs.provably_playable_indices
        assert hle_obs.provably_obsolete_indices == native_obs.provably_obsolete_indices
        assert hle_obs.play_safety == native_obs.play_safety
        assert hle_obs.stacks == native_obs.stacks
        assert hle_obs.discards == native_obs.discards
        assert hle_obs.information_tokens == native_obs.information_tokens
        assert hle_obs.life_tokens == native_obs.life_tokens
        assert hle_obs.deck_size == native_obs.deck_size
        assert hle_obs.final_turns_remaining == native_obs.final_turns_remaining


def _step_both(hle, native, action: Action):
    actor = hle.current_player
    assert actor == native.current_player
    assert action in hle.legal_actions(actor)
    assert action in native.legal_actions(actor)

    deck_size_before = int(hle.true_state()["deck_size"])
    hle_result = hle.step(action)
    _prepare_native_draw_after_hle_step(
        native,
        hle,
        actor=actor,
        action=action,
        deck_size_before=deck_size_before,
    )
    native_result = native.step(action)
    return hle_result, native_result


def test_hle_and_native_match_hint_legality_and_knowledge_update():
    hle = _hle_or_skip(seed=7)
    native = _mirror_hle_initial_state_into_native(hle, seed=7)

    assert set(hle.legal_actions()) == set(native.legal_actions())

    hint = next(action for action in hle.legal_actions() if action.type == "hint")
    hle_result, native_result = _step_both(hle, native, hint)

    assert hle_result.outcome["touched_indices"] == native_result.outcome["touched_indices"]
    assert hle.observe(1).own_knowledge == native.observe(1).own_knowledge
    assert hle.observe(0).information_tokens == native.observe(0).information_tokens == 7


def test_hle_and_native_match_discard_token_recovery():
    hle = _hle_or_skip(seed=7)
    native = _mirror_hle_initial_state_into_native(hle, seed=7)

    hint = next(action for action in hle.legal_actions() if action.type == "hint")
    _step_both(hle, native, hint)
    assert hle.true_state()["information_tokens"] == 7

    discard = Action.discard(0)
    assert discard in hle.legal_actions()
    _step_both(hle, native, discard)

    assert hle.true_state()["information_tokens"] == 8
    _assert_backend_state_parity(hle, native)


def _first_seed_with_rank(predicate) -> tuple[int, int]:
    for seed in range(100):
        hle = _hle_or_skip(seed=seed)
        hand = hle.true_state()["hands"][0]
        for index, card in enumerate(hand):
            if predicate(int(card["rank"])):
                return seed, index
    raise AssertionError("Could not find requested initial card in seeds 0..99")


@pytest.mark.parametrize(
    ("predicate", "expected_success"),
    [
        (lambda rank: rank == 1, True),
        (lambda rank: rank > 1, False),
    ],
)
def test_hle_and_native_match_single_play_outcome(predicate, expected_success):
    seed, card_index = _first_seed_with_rank(predicate)
    hle = _hle_or_skip(seed=seed)
    native = _mirror_hle_initial_state_into_native(hle, seed=seed)

    action = Action.play(card_index)
    hle_result, native_result = _step_both(hle, native, action)

    assert hle_result.outcome["play_success"] is expected_success
    assert native_result.outcome["play_success"] is expected_success
    assert hle_result.outcome["score_after"] == native_result.outcome["score_after"]
    assert (
        hle_result.outcome["life_tokens_after"]
        == native_result.outcome["life_tokens_after"]
    )
    assert hle.true_state()["hands"] == native.true_state()["hands"]


def test_hle_and_native_match_life_exhaustion():
    hle = _hle_or_skip(seed=0)
    native = _mirror_hle_initial_state_into_native(hle, seed=0)

    while not hle.done:
        actor = hle.current_player
        hand = hle.true_state()["hands"][actor]
        stacks = hle.true_state()["stacks"]
        bad_index = next(
            index
            for index, card in enumerate(hand)
            if stacks[card["color"]] + 1 != card["rank"]
        )
        action = Action.play(bad_index)
        hle_result, native_result = _step_both(hle, native, action)

        assert hle_result.outcome["play_success"] is False
        assert native_result.outcome["play_success"] is False
        _assert_backend_state_parity(hle, native)

    assert hle.true_state()["life_tokens"] == 0
    assert native.true_state()["life_tokens"] == 0


@pytest.mark.parametrize("seed", [0, 1, 7])
def test_hle_and_native_match_full_simple_agent_trajectory(seed):
    hle = _hle_or_skip(seed=seed)
    native = _mirror_hle_initial_state_into_native(hle, seed=seed)
    agent = SimpleAgent(name="parity_simple")

    turns = 0
    saw_final_round = False

    while not hle.done:
        _assert_backend_state_parity(hle, native)
        assert set(hle.legal_actions()) == set(native.legal_actions())

        actor = hle.current_player
        decision = agent.act(hle.observe(actor), hle.legal_actions(actor), "")
        assert decision.action is not None

        hle_result, native_result = _step_both(
            hle,
            native,
            decision.action,
        )
        assert hle_result.done == native_result.done
        assert hle_result.outcome["score_after"] == native_result.outcome["score_after"]
        assert (
            hle_result.outcome["life_tokens_after"]
            == native_result.outcome["life_tokens_after"]
        )

        saw_final_round = saw_final_round or (
            hle.true_state()["final_turns_remaining"] is not None
        )
        turns += 1
        assert turns < 200

    _assert_backend_state_parity(hle, native)
    assert saw_final_round
    assert hle.true_state()["final_turns_remaining"] == 0
