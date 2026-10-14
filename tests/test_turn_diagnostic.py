import copy
import json

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

from hanabi_ck.actions import Action
from hanabi_ck.agents import AgentDecision, OpenAICompatibleAgent
from hanabi_ck.engine import HanabiGame
from hanabi_ck.runner import _build_agent
from hanabi_ck.turn_diagnostic import diagnose_turn


def source(tmp_path):
    spec = {"type": "openai_compatible", "model": "test", "api_key": "test",
            "structured_output": True, "action_index_schema": "bounds",
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False,
                                                    "preserve_thinking": False}}}
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({"agents": [spec, spec], "mechanical_scaffold": "derived"}))
    game = HanabiGame(num_players=2, seed=0)
    game.step(Action.from_dict({"type": "hint", "target": 1, "attribute": "rank", "value": 1}))
    game.step(Action.from_dict({"type": "play", "card_index": 1}))
    obs, legal = game.observe(0), game.legal_actions(0)
    agent = _build_agent(dict(spec, mechanical_scaffold="derived"), seed=0)
    payload = agent._request_payload(obs, legal, "test instruction")
    log = tmp_path / "source.jsonl"
    log.write_text(json.dumps({"event_kind": "turn", "turn": 2, "player": 0,
                              "private_instruction": "test instruction", "request_payload": payload,
                              "legal_actions": [a.to_dict() for a in legal],
                              "observation": obs.to_dict()}, sort_keys=True) + "\n")
    return config, log, payload, legal


def check_fixed_state_and_index_mapping(tmp_path):
    config, log, original, legal = source(tmp_path)
    calls = []

    def act(self, obs, presented, instruction, *, prepared_payload):
        assert self.http_max_retries == 0 and self.record_http_attempts
        calls.append(copy.deepcopy(prepared_payload))
        # Choose the same actual action even when its presented index moves.
        selected = presented.index(legal[10])
        return AgentDecision(action=presented[selected], action_index=selected,
                             raw_response=json.dumps({"action_index": selected}),
                             api_response={"choices": [{"message": {"reasoning_content": "test"}}]})

    patcher = patch.object(OpenAICompatibleAgent, "act", act)
    patcher.start()
    output = tmp_path / "diagnostic.jsonl"
    before = log.read_bytes()
    report = diagnose_turn(config, log, turn=2, output=output)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(calls) == len(rows) == 4
    assert {(r["thinking_requested"], r["shuffled"]) for r in rows} == {
        (False, False), (False, True), (True, False), (True, True)}
    assert all(r["original_action_index"] == 10 for r in rows)
    original_user = json.loads(original["messages"][1]["content"])
    for row, payload in zip(rows, calls):
        assert payload["response_format"] == original["response_format"]
        assert payload["messages"][0] == original["messages"][0]
        user = json.loads(payload["messages"][1]["content"])
        assert user["observation"] == original_user["observation"]
        assert user["private_experimental_instruction"] == original_user["private_experimental_instruction"]
        assert row["api_response"]["choices"][0]["message"]["reasoning_content"] == "test"
        if row["shuffled"]:
            assert row["presented_action_index"] != 10
            assert all(i != v for i, v in enumerate(row["presented_index_to_original_index"]))
        else:
            assert payload["messages"] == original["messages"]
    assert all(r["ok"] for r in report["results"])
    assert log.read_bytes() == before
    with unittest.TestCase().assertRaises(FileExistsError):
        diagnose_turn(config, log, turn=2, output=output)
    patcher.stop()
    assert len(calls) == 4


def check_changed_controls_rejected_before_call(tmp_path):
    config, log, _, _ = source(tmp_path)
    cfg = yaml.safe_load(config.read_text())
    cfg["agents"][0]["max_tokens"] = 123
    config.write_text(yaml.safe_dump(cfg))
    with patch.object(OpenAICompatibleAgent, "act", side_effect=AssertionError("HTTP call")):
        with unittest.TestCase().assertRaisesRegex(ValueError, "beyond thinking"):
            diagnose_turn(config, log, turn=2, output=tmp_path / "out.jsonl")


class TestTurnDiagnostic(unittest.TestCase):
    def test_fixed_state_and_index_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            check_fixed_state_and_index_mapping(Path(directory))

    def test_changed_controls_rejected_before_call(self):
        with tempfile.TemporaryDirectory() as directory:
            check_changed_controls_rejected_before_call(Path(directory))
