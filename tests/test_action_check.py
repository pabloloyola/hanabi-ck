import json

import pytest
import yaml

from hanabi_ck.action_check import check_hanabi_action
from hanabi_ck.agents import AgentDecision, OpenAICompatibleAgent
from hanabi_ck.engine import HanabiGame
from hanabi_ck.runner import _build_agent


def config(tmp_path):
    cfg = {
        "conditions": ["ck0"],
        "num_players": 2,
        "mechanical_scaffold": "derived",
        "agents": [
            {
                "type": "openai_compatible",
                "model": "test-model",
                "api_key": "test",
                "structured_output": True,
                "max_tokens": 100,
                "extra_body": {"provider": {"only": ["deepinfra"]}},
            }
        ]
        * 2,
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path, cfg


def test_initial_check_makes_one_action_without_game_mutation(tmp_path, monkeypatch):
    path, _ = config(tmp_path)
    calls = []

    def act(self, obs, legal, instruction, **kwargs):
        calls.append((obs, instruction, self.http_max_retries, self.record_http_attempts))
        return AgentDecision(
            action=legal[0], api_response={"model": "test-model", "provider": "DeepInfra"}
        )

    monkeypatch.setattr(OpenAICompatibleAgent, "act", act)
    report = check_hanabi_action(path)
    assert len(calls) == 1 and calls[0][2:] == (0, True)
    assert report["ok"] and report["returned_provider"] == "DeepInfra"
    assert not report["matches_original_except_provider"]


def make_log(tmp_path, cfg):
    game = HanabiGame(num_players=2, seed=0)
    obs, legal = game.observe(0), game.legal_actions(0)
    spec = dict(cfg["agents"][0], mechanical_scaffold="derived")
    agent = _build_agent(spec, seed=0)
    payload = agent._request_payload(obs, legal, "original identity instruction")
    payload["provider"] = {"order": ["venice"]}
    log = tmp_path / "failed.jsonl"
    log.write_text(
        json.dumps(
            {
                "event_kind": "agent_error",
                "player": 0,
                "turn": 3,
                "agent": {"model": "test-model"},
                "observation": obs.to_dict(),
                "legal_actions": [a.to_dict() for a in legal],
                "private_instruction": "original identity instruction",
                "request_payload": payload,
            },
            sort_keys=True,
        )
        + "\n"
    )
    return log


def test_reuses_failed_observation_and_instruction(tmp_path, monkeypatch):
    path, cfg = config(tmp_path)
    log = make_log(tmp_path, cfg)
    calls = []

    def act(self, obs, legal, instruction, **kwargs):
        calls.append((instruction, kwargs["prepared_payload"]))
        return AgentDecision(action=legal[0])

    monkeypatch.setattr(OpenAICompatibleAgent, "act", act)
    report = check_hanabi_action(path, log_path=log)
    original = json.loads(log.read_text())["request_payload"]
    assert calls[0][0] == "original identity instruction"
    assert calls[0][1]["messages"] == original["messages"]
    assert calls[0][1]["provider"] == {"only": ["deepinfra"]}
    assert {k: v for k, v in calls[0][1].items() if k != "provider"} == {
        k: v for k, v in original.items() if k != "provider"
    }
    assert report["matches_original_except_provider"]
    assert report["source"]["turn"] == 3


def test_rejects_other_request_changes_before_call(tmp_path, monkeypatch):
    path, cfg = config(tmp_path)
    log = make_log(tmp_path, cfg)
    cfg["agents"][0]["max_tokens"] = 200
    path.write_text(yaml.safe_dump(cfg))
    monkeypatch.setattr(
        OpenAICompatibleAgent, "act", lambda *a: pytest.fail("Request must not be sent")
    )
    with pytest.raises(ValueError, match="beyond provider"):
        check_hanabi_action(path, log_path=log)


def test_sends_original_prompt_text_from_sorted_log(tmp_path, monkeypatch):
    import httpx

    path, cfg = config(tmp_path)
    log = make_log(tmp_path, cfg)
    original = json.loads(log.read_text())["request_payload"]
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "provider": "DeepInfra",
                "model": "test-model",
                "choices": [
                    {"finish_reason": "stop", "message": {"content": '{"action_index":0}'}}
                ],
            },
        )

    client_class = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "hanabi_ck.agents.httpx.Client", lambda **kw: client_class(transport=transport, **kw)
    )
    before = log.read_bytes()
    report = check_hanabi_action(path, log_path=log)
    assert report["ok"] and len(sent) == 1
    assert sent[0]["messages"] == original["messages"]
    assert {k: v for k, v in sent[0].items() if k != "provider"} == {
        k: v for k, v in original.items() if k != "provider"
    }
    assert log.read_bytes() == before
