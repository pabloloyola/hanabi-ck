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


def test_openai_compatible_agent_merges_extra_body_into_request():
    from hanabi_ck.agents import OpenAICompatibleAgent

    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)
    legal = game.legal_actions(0)

    agent = OpenAICompatibleAgent(
        name="qwen",
        model="qwen/qwen3.8-27b",
        max_tokens=256,
        extra_body={"enable_thinking": False},
    )
    payload = agent._request_payload(observation, legal, "test")

    assert payload["model"] == "qwen/qwen3.8-27b"
    assert payload["max_tokens"] == 256
    assert payload["enable_thinking"] is False
    assert "extra_body" not in payload


def test_openai_compatible_agent_rejects_extra_body_reserved_collision():
    import pytest

    from hanabi_ck.agents import OpenAICompatibleAgent

    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)
    legal = game.legal_actions(0)

    agent = OpenAICompatibleAgent(
        name="bad",
        model="qwen/qwen3.8-27b",
        extra_body={"model": "other-model"},
    )

    with pytest.raises(ValueError, match="reserved request fields"):
        agent._request_payload(observation, legal, "test")
