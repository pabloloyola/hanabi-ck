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
        structured_output=True,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
                "preserve_thinking": False,
            }
        },
    )
    payload = agent._request_payload(observation, legal, "test")

    assert payload["model"] == "qwen/qwen3.8-27b"
    assert payload["max_tokens"] == 256
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
    assert payload["chat_template_kwargs"]["preserve_thinking"] is False
    assert payload["response_format"]["type"] == "json_schema"
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


def test_structured_output_schema_requires_complete_action_shape():
    from hanabi_ck.agents import OpenAICompatibleAgent

    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)
    legal = game.legal_actions(0)

    agent = OpenAICompatibleAgent(
        name="qwen",
        model="qwen/qwen3.8-27b",
        structured_output=True,
    )
    payload = agent._request_payload(observation, legal, "test")
    schema = payload["response_format"]["json_schema"]["schema"]

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "type",
        "card_index",
        "target",
        "attribute",
        "value",
    }
