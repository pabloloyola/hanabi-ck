from __future__ import annotations

import pytest

from hanabi_ck.actions import Action
from hanabi_ck.engine import HanabiGame
from hanabi_ck.scaffolds import (
    normalize_mechanical_scaffold,
    render_hint_effects,
    render_observation,
)


def test_derived_scaffold_preserves_historical_observation():
    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)

    assert render_observation(observation, "derived") == observation.to_dict()


def test_raw_scaffold_removes_only_synthetic_safety_summaries():
    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)

    rendered = render_observation(observation, "raw")

    assert "provably_playable_indices" not in rendered
    assert "provably_obsolete_indices" not in rendered
    assert "play_safety" not in rendered
    assert rendered["own_knowledge"] == observation.own_knowledge
    assert rendered["public_knowledge"] == observation.public_knowledge
    assert 0 not in rendered["other_hands"]


def test_raw_hint_effects_hide_precomputed_touch_and_safety_annotations():
    effects = [
        {
            "action_index": 2,
            "action": Action.hint(1, "rank", 2).to_dict(),
            "touched_indices": [1, 2, 4],
            "receiver_provably_playable_indices_after_hint": [1, 2, 4],
            "receiver_provably_obsolete_indices_after_hint": [],
        }
    ]

    assert render_hint_effects(effects, "raw") == [
        {
            "action_index": 2,
            "action": Action.hint(1, "rank", 2).to_dict(),
        }
    ]
    assert render_hint_effects(effects, "derived") == effects


def test_unknown_mechanical_scaffold_is_rejected():
    with pytest.raises(ValueError, match="mechanical_scaffold"):
        normalize_mechanical_scaffold("mystery")
