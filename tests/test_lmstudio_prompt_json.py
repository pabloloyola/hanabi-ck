from pathlib import Path

import httpx
import pytest
import yaml

from hanabi_ck.engine import HanabiGame
from hanabi_ck.runner import _build_agent


@pytest.mark.parametrize("mode", ["hidden", "named"])
def test_local_thinking_request_has_no_schema(mode):
    path = Path(__file__).parents[1] / "configs" / f"identity_lmstudio_qwen38_thinking_{mode}.yaml"
    cfg = yaml.safe_load(path.read_text())
    game = HanabiGame(num_players=2, seed=0)
    for spec in cfg["agents"]:
        agent = _build_agent(dict(spec, mechanical_scaffold=cfg["mechanical_scaffold"]), seed=0)
        payload = agent._request_payload(game.observe(0), game.legal_actions(0), "instruction")
        assert "response_format" not in payload
        assert payload["chat_template_kwargs"] == {
            "enable_thinking": True,
            "preserve_thinking": False,
        }
        assert agent.api_key == "lm-studio"
        assert agent.base_url == "http://localhost:1234/v1"
        assert cfg["agent_error_policy"] == "abort"
        assert "JSON" in payload["messages"][0]["content"]


@pytest.mark.parametrize("valid", [True, False])
def test_final_content_is_parsed_strictly_with_reasoning_separate(monkeypatch, valid):
    game = HanabiGame(num_players=2, seed=0)
    legal = game.legal_actions(0)
    seen = []
    content = '{"action_index": 1}' if valid else '{"action_index": 1, "explanation": "extra"}'
    data = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": content, "reasoning_content": "A separate reasoning trace."},
            }
        ]
    }

    def respond(request):
        seen.append(request.read().decode())
        return httpx.Response(200, json=data)

    real_client = httpx.Client
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(
        "hanabi_ck.agents.httpx.Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    agent = _build_agent(
        {
            "type": "openai_compatible",
            "model": "local",
            "api_key": "lm-studio",
            "base_url": "http://localhost:1234/v1",
            "structured_output": False,
        },
        seed=0,
    )
    decision = agent.act(game.observe(0), legal, "instruction")
    assert len(seen) == 1
    assert "response_format" not in seen[0]
    assert decision.response_channel == "content"
    assert decision.api_response == data
    assert (
        (decision.action == legal[1])
        if valid
        else (decision.action is None and decision.parse_error)
    )
