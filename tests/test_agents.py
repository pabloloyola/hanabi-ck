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


def test_structured_output_schema_selects_only_legal_action_index():
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
    assert schema["required"] == ["action_index"]
    assert schema["properties"]["action_index"]["enum"] == list(
        range(len(legal))
    )


def test_select_response_text_prefers_content_then_reasoning_content():
    from hanabi_ck.agents import _select_response_text

    text, channel = _select_response_text(
        {
            "content": "{\"type\":\"play\",\"card_index\":0}",
            "reasoning_content": "{\"type\":\"discard\",\"card_index\":1}",
        }
    )
    assert channel == "content"
    assert "\"play\"" in text

    text, channel = _select_response_text(
        {
            "content": "",
            "reasoning_content": (
                "{\"type\":\"hint\",\"target\":1,"
                "\"attribute\":\"color\",\"value\":\"R\"}"
            ),
        }
    )
    assert channel == "reasoning_content"
    assert "\"hint\"" in text


def test_action_from_index_object_maps_exact_legal_action():
    from hanabi_ck.agents import _action_from_index_object

    game = HanabiGame(num_players=2, seed=0)
    legal = game.legal_actions(0)

    index, action = _action_from_index_object(
        {"action_index": 3},
        legal,
    )

    assert index == 3
    assert action == legal[3]


def test_action_from_index_object_rejects_extra_fields():
    import pytest

    from hanabi_ck.agents import _action_from_index_object

    game = HanabiGame(num_players=2, seed=0)
    legal = game.legal_actions(0)

    with pytest.raises(ValueError, match="exactly one field"):
        _action_from_index_object(
            {"action_index": 0, "type": "play"},
            legal,
        )


def test_llm_prompt_states_base_safety_and_hand_order():
    from hanabi_ck.agents import OpenAICompatibleAgent

    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)
    legal = game.legal_actions(0)

    agent = OpenAICompatibleAgent(
        name="qwen",
        model="qwen/qwen3.8-27b",
    )
    messages = agent._prompt(observation, legal, "NO EXTRA CONVENTION")
    system = messages[0]["content"]
    user = messages[1]["content"]

    assert "provably_playable_indices" in system
    assert "intention" in system
    assert "does not make an unsafe card safe" in system
    assert "newest_card_index" in system
    assert '"legal_actions"' in user
    assert '"output_example"' not in user


def test_intention_probe_payload_constrains_candidate_card_indices():
    from hanabi_ck.agents import OpenAICompatibleAgent

    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)

    agent = OpenAICompatibleAgent(
        name="qwen",
        model="qwen/qwen3.8-27b",
        structured_output=True,
    )
    payload = agent._intention_probe_payload(
        observation,
        "TEST CONVENTION",
        {
            "actor": 1,
            "target": 0,
            "attribute": "rank",
            "value": 1,
            "touched_indices": [1, 2, 4],
        },
        [1, 2, 4],
    )

    schema = payload["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["intended_card_index"]
    assert schema["properties"]["intended_card_index"]["enum"] == [1, 2, 4]
    assert schema["additionalProperties"] is False
    assert "legal_actions" not in payload["messages"][1]["content"]


def test_sender_epistemic_probe_payload_constrains_hint_and_knowledge():
    from hanabi_ck.agents import OpenAICompatibleAgent

    game = HanabiGame(num_players=2, seed=0)
    observation = game.observe(0)
    agent = OpenAICompatibleAgent(
        name="qwen",
        model="qwen/qwen3.8-27b",
        structured_output=True,
    )
    hint_effects = [
        {
            "action_index": 0,
            "action": Action.hint(1, "rank", 3).to_dict(),
            "touched_indices": [3],
        },
        {
            "action_index": 4,
            "action": Action.hint(1, "rank", 1).to_dict(),
            "touched_indices": [1, 2, 4],
        },
    ]

    payload = agent._sender_epistemic_probe_payload(
        observation,
        "TEST CONVENTION",
        "Communicate that the receiver should play their newest card.",
        hint_effects,
    )
    schema = payload["response_format"]["json_schema"]["schema"]

    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "convention_hint_index",
        "receiver_convention_knowledge",
    ]
    assert schema["properties"]["convention_hint_index"]["enum"] == [-1, 0, 4]
    assert schema["properties"]["receiver_convention_knowledge"]["enum"] == [
        "no_convention",
        "unknown",
        "known",
    ]
    user = payload["messages"][1]["content"]
    assert "touched_indices" in user
    assert "communication_goal" in user
