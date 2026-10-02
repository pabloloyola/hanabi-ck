from hanabi_ck.actions import Action
from hanabi_ck.micro_scenarios import get_micro_scenario


def test_newest_rank1_micro_scenario_has_three_safe_touched_choices():
    scenario = get_micro_scenario("newest_rank1_three_safe")
    observation = scenario.observation

    assert scenario.acting_player == 1
    assert observation.newest_card_index[1] == 4
    assert observation.provably_playable_indices == [1, 2, 4]
    assert scenario.diagnostic_safe_card_indices == (1, 2, 4)
    assert scenario.trigger_hint["touched_indices"] == [1, 2, 4]
    assert scenario.target_action == Action.play(4)
    assert scenario.target_action in scenario.legal_actions


def test_micro_observation_does_not_expose_acting_players_true_hand():
    scenario = get_micro_scenario("newest_rank1_three_safe")
    observation = scenario.observation.to_dict()

    assert set(observation["other_hands"]) == {0}
    assert "acting_hand" not in observation
    assert scenario.researcher_truth["acting_hand"][4] == {
        "color": "Y",
        "rank": 1,
    }
