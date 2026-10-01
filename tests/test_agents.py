from hanabi_ck.actions import Action
from hanabi_ck.agents import SimpleAgent
from hanabi_ck.engine import Card, HanabiGame


def test_simple_agent_plays_rank_one_without_knowing_color():
    game = HanabiGame(num_players=2, seed=0)
    game.knowledge[0][0].possible_ranks = {1}

    decision = SimpleAgent().act(
        game.observe(0),
        game.legal_actions(0),
        "",
    )

    assert decision.action == Action.play(0)


def test_simple_agent_prefers_hint_that_creates_safe_play():
    game = HanabiGame(num_players=2, seed=0)
    game.hands[1] = [
        Card("R", 1),
        Card("G", 2),
        Card("B", 3),
        Card("Y", 4),
        Card("W", 5),
    ]

    decision = SimpleAgent().act(
        game.observe(0),
        game.legal_actions(0),
        "",
    )

    assert decision.action == Action.hint(1, "rank", 1)


def test_simple_agent_avoids_redundant_rank_hint():
    game = HanabiGame(num_players=2, seed=0)
    game.hands[1] = [
        Card("R", 1),
        Card("G", 2),
        Card("B", 3),
        Card("Y", 4),
        Card("W", 5),
    ]
    game.knowledge[1][0].possible_ranks = {1}

    decision = SimpleAgent().act(
        game.observe(0),
        game.legal_actions(0),
        "",
    )

    assert decision.action != Action.hint(1, "rank", 1)
