from hanabi_ck.actions import Action
from hanabi_ck.micro_scenarios import get_pair_micro_scenario


def test_pair_micro_rank1_hint_makes_three_cards_safe():
    scenario = get_pair_micro_scenario("sender_receiver_newest_intent")
    observation = scenario.receiver_observation_after_hint(
        scenario.convention_trigger_hint
    )

    assert observation.provably_playable_indices == [1, 2, 4]
    assert observation.newest_card_index[1] == 4
    assert scenario.receiver_target_action == Action.play(4)


def test_pair_micro_sender_candidates_are_only_legal_hints():
    scenario = get_pair_micro_scenario("sender_receiver_newest_intent")

    assert scenario.sender_hint_actions
    assert all(action.type == "hint" for action in scenario.sender_hint_actions)
    assert scenario.convention_trigger_hint in scenario.sender_hint_actions


def test_pair_micro_non_rank_hint_does_not_make_newest_provably_safe():
    scenario = get_pair_micro_scenario("sender_receiver_newest_intent")
    color_y = Action.hint(1, "color", "Y")
    observation = scenario.receiver_observation_after_hint(color_y)

    assert 4 not in observation.provably_playable_indices


def test_pair_micro_removes_rank4_number_collision():
    scenario = get_pair_micro_scenario("sender_receiver_newest_intent")
    rank_values = {
        int(action.value)
        for action in scenario.sender_hint_actions
        if action.attribute == "rank"
    }

    assert 4 not in rank_values
    assert rank_values == {1, 2, 3}
    assert "index 4" not in scenario.sender_goal
    assert "card 4" not in scenario.sender_goal


def test_pair_micro_exposes_public_hint_touch_sets():
    scenario = get_pair_micro_scenario("sender_receiver_newest_intent")

    assert scenario.touched_indices_for_hint(Action.hint(1, "rank", 1)) == (
        1,
        2,
        4,
    )
    assert scenario.touched_indices_for_hint(Action.hint(1, "rank", 2)) == (0,)
    assert scenario.touched_indices_for_hint(Action.hint(1, "rank", 3)) == (3,)
