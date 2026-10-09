import json
import re

import pytest
import yaml

from hanabi_ck.replay import export_replay
from hanabi_ck.runner import run_experiment


def _game(tmp_path):
    config = {
        "experiment": "test_replay",
        "output_dir": str(tmp_path),
        "num_players": 2,
        "seeds": [0],
        "conditions": ["ck0"],
        "agents": [{"type": "simple"}, {"type": "simple"}],
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    summary = run_experiment(path)
    log = tmp_path / "test_replay/ck0/seed_000000.jsonl"
    return log, summary


def test_full_game_logs_before_after_and_final_state(tmp_path):
    log, summary = _game(tmp_path)
    records = [json.loads(line) for line in log.read_text().splitlines()]
    for current, following in zip(records, records[1:]):
        assert current["researcher_true_state_after"] == following["researcher_true_state_before"]
        assert (
            current["observation_after"]["stacks"]
            == current["researcher_true_state_after"]["stacks"]
        )
    assert records[-1]["game_done"] is True
    assert records[-1]["researcher_true_state_after"]["score"] == summary["games"][0]["score"]
    assert records[0]["request_payload"] is None  # Rule-based game, no fabricated model request.


def test_export_preserves_original_log_and_escapes_script_text(tmp_path):
    log, _ = _game(tmp_path)
    original = log.read_text()
    title = "</script><script>window.attacked=true</script>"
    output = export_replay(log, tmp_path / "replay.html", title=title)
    html = output.read_text()
    embedded = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    data = json.loads(embedded.group(1))
    assert data["source"] == original
    assert data["title"] == title
    assert title not in html
    assert 'src="http' not in html
    assert "__REPLAY_DATA__" not in html


def test_old_logs_remain_exportable_without_fabricating_fields(tmp_path):
    log, _ = _game(tmp_path)
    record = json.loads(log.read_text().splitlines()[0])
    for key in ["request_payload", "observation_after", "researcher_true_state_after", "game_done"]:
        record.pop(key)
    log.write_text(json.dumps(record) + "\n")
    output = export_replay(log, tmp_path / "old.html")
    assert "Not recorded." in output.read_text()


@pytest.mark.parametrize("source", ["", "{bad json}", '{"event_kind":"micro_pair_sample"}'])
def test_replay_rejects_empty_invalid_and_micro_logs(tmp_path, source):
    log = tmp_path / "bad.jsonl"
    log.write_text(source)
    with pytest.raises(ValueError):
        export_replay(log, tmp_path / "bad.html")


def test_replay_cannot_overwrite_source(tmp_path):
    log, _ = _game(tmp_path)
    with pytest.raises(ValueError, match="overwrite"):
        export_replay(log, log)


def test_agent_captures_actual_payload_on_success_and_http_failure(monkeypatch):
    import httpx

    from hanabi_ck.agents import OpenAICompatibleAgent
    from hanabi_ck.engine import HanabiGame

    sent = []
    fail = False

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, *, headers, json):
            sent.append(json)
            if fail:
                raise httpx.ConnectError("offline failure")
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": '{"action_index":0}'},
                        }
                    ]
                },
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "Client", Client)
    agent = OpenAICompatibleAgent(name="offline", model="test", api_key="never-export-this-key")
    game = HanabiGame(num_players=2, seed=0)
    for failed in [False, True]:
        fail = failed
        decision = agent.act(game.observe(0), game.legal_actions(0), "private instruction")
        assert decision.request_payload == sent[-1]
        assert "never-export-this-key" not in json.dumps(decision.request_payload)
        assert (decision.parse_error is not None) is failed


@pytest.mark.parametrize("flag", [None, "log_request_payloads", "log_private_instructions"])
def test_runner_records_failed_request_and_respects_logging_controls(tmp_path, monkeypatch, flag):
    from hanabi_ck.agents import AgentDecision, OpenAICompatibleAgent

    def failed_act(self, observation, legal, instruction):
        return AgentDecision(
            action=None,
            parse_error="offline error",
            request_payload={"messages": [{"content": instruction}]},
        )

    monkeypatch.setattr(OpenAICompatibleAgent, "act", failed_act)
    config = {
        "experiment": "failed",
        "output_dir": str(tmp_path),
        "conditions": ["ck0"],
        "agents": [{"type": "openai_compatible", "model": "offline"}] * 2,
    }
    if flag:
        config[flag] = False
    path = tmp_path / "failed.yaml"
    path.write_text(yaml.safe_dump(config))
    summary = run_experiment(path)
    record = json.loads((tmp_path / "failed/ck0/seed_000000.jsonl").read_text())
    assert record["event_kind"] == "agent_error"
    assert summary["games"][0]["aborted"] is True
    assert (record["request_payload"] is None) is (flag is not None)
    export_replay(tmp_path / "failed/ck0/seed_000000.jsonl", tmp_path / "failed.html")
