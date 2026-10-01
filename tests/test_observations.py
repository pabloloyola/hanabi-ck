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
