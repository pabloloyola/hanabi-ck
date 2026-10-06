from __future__ import annotations

import pytest

from hanabi_ck.actions import Action
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
    """Build a native state with the same dealt hands for no-draw parity checks."""
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
    native.stacks = dict(truth["stacks"])
    native.discards = []
    native.information_tokens = int(truth["information_tokens"])
    native.life_tokens = int(truth["life_tokens"])
    native.current_player = int(truth["current_player"])
    native.history = []
    native.final_turns_remaining = None
    native.done = False
    return native


def test_hle_and_native_match_hint_legality_and_knowledge_update():
    hle = _hle_or_skip(seed=7)
    native = _mirror_hle_initial_state_into_native(hle, seed=7)

    assert set(hle.legal_actions()) == set(native.legal_actions())

    hint = next(action for action in hle.legal_actions() if action.type == "hint")
    hle_result = hle.step(hint)
    native_result = native.step(hint)

    assert hle_result.outcome["touched_indices"] == native_result.outcome["touched_indices"]
    assert hle.observe(1).own_knowledge == native.observe(1).own_knowledge
    assert hle.observe(0).information_tokens == native.observe(0).information_tokens == 7


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
    assert action in hle.legal_actions()
    assert action in native.legal_actions()

    hle_result = hle.step(action)

    # HLE does not expose remaining deck identities. After HLE draws, recover
    # the drawn newest card and feed exactly that card to the mirrored native
    # state, while preserving the same post-draw deck size.
    drawn = hle.true_state()["hands"][0][-1]
    remaining_after_draw = hle.true_state()["deck_size"]
    native.deck = [
        Card("R", 1) for _ in range(max(0, remaining_after_draw))
    ] + [Card(str(drawn["color"]), int(drawn["rank"]))]

    native_result = native.step(action)

    assert hle_result.outcome["play_success"] is expected_success
    assert native_result.outcome["play_success"] is expected_success
    assert hle_result.outcome["score_after"] == native_result.outcome["score_after"]
    assert (
        hle_result.outcome["life_tokens_after"]
        == native_result.outcome["life_tokens_after"]
    )
    assert hle.true_state()["hands"] == native.true_state()["hands"]
