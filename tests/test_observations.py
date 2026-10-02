from hanabi_ck.actions import Action
from hanabi_ck.engine import HanabiGame


def test_observation_exposes_public_knowledge_for_all_players():
    game = HanabiGame(num_players=2, seed=3)
    rank = game.hands[1][0].rank

    game.step(Action.hint(1, "rank", rank))
    observation = game.observe(1)

    assert set(observation.public_knowledge) == {0, 1}
    assert observation.public_knowledge[1] == observation.own_knowledge
    assert any(
        card_knowledge["possible_ranks"] == [rank]
        for card_knowledge in observation.public_knowledge[1]
    )


def test_observation_exposes_hand_order_and_newest_slots():
    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)

    assert observation.hand_order == "oldest_to_newest"
    assert observation.newest_card_index == {0: 4, 1: 4}
    serialized = observation.to_dict()
    assert serialized["hand_order"] == "oldest_to_newest"
    assert serialized["newest_card_index"][0] == 4
    assert serialized["newest_card_index"][1] == 4
