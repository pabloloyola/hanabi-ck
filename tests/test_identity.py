import json
from pathlib import Path

import pytest
import yaml

from hanabi_ck.agents import AgentDecision, SimpleAgent
from hanabi_ck.identity import (
    analyze_identity_suite,
    identity_instruction,
    prepare_identity_suite,
)
from hanabi_ck.runner import run_experiment

SPECS = [{"type": "simple", "model": "model-A"}, {"type": "simple", "model": "model-B"}]


def suite(tmp_path):
    source = tmp_path / "suite.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "experiment": "identity",
                "seeds": [0, 1],
                "models": dict(zip("AB", SPECS)),
                "game": {"output_dir": str(tmp_path / "runs")},
            }
        )
    )
    output = tmp_path / "prepared"
    manifest = prepare_identity_suite(source, output)
    return manifest, output


def test_disclosure_changes_only_partner_identity():
    hidden = identity_instruction(SPECS, 0, "hidden")
    named = identity_instruction(SPECS, 0, "named")
    assert "model-A" in hidden and "model-A" in named
    assert "model-B" not in hidden and "model-B" in named
    assert identity_instruction(SPECS, 1, "hidden").count("model-B") == 1
    assert "model-A" not in identity_instruction(SPECS, 1, "hidden")
    assert hidden.splitlines()[-1] == named.splitlines()[-1]
    with pytest.raises(ValueError):
        identity_instruction(SPECS, 0, "unknown")
    with pytest.raises(ValueError):
        identity_instruction([SPECS[0]], 0, "hidden")


def test_suite_balances_pairings_and_preserves_settings(tmp_path):
    manifest, output = suite(tmp_path)
    assert manifest["n_games_planned"] == 16
    assert len(manifest["cells"]) == 8
    for pairing in ("AA", "BB", "AB", "BA"):
        hidden = yaml.safe_load((output / f"{pairing}_hidden.yaml").read_text())
        named = yaml.safe_load((output / f"{pairing}_named.yaml").read_text())
        assert hidden["agents"] == named["agents"]
        assert hidden["seeds"] == named["seeds"] == [0, 1]
        assert hidden["conditions"] == named["conditions"] == ["ck0"]
        assert [a["model"] for a in hidden["agents"]] == [manifest["models"][m] for m in pairing]
    with pytest.raises(ValueError, match="empty"):
        prepare_identity_suite(tmp_path / "suite.yaml", output)


def test_identity_reaches_action_prompt_and_logs(tmp_path, monkeypatch):
    manifest, output = suite(tmp_path)
    instructions = []

    class RecordingAgent(SimpleAgent):
        def act(self, observation, legal_actions, private_instruction):
            instructions.append((observation.player_id, private_instruction))
            return super().act(observation, legal_actions, private_instruction)

    monkeypatch.setattr(
        "hanabi_ck.runner._build_agent", lambda spec, seed: RecordingAgent(name=spec["name"])
    )
    summary = run_experiment(output / "AB_hidden.yaml")
    assert summary["identity_setup"]["mode"] == "hidden"
    for player, text in instructions:
        assert SPECS[player]["model"] in text
        assert SPECS[1 - player]["model"] not in text
    records = [
        json.loads(line) for line in Path(summary["games"][0]["log_path"]).read_text().splitlines()
    ]
    assert all(r["identity_setup"] == summary["identity_setup"] for r in records)
    with pytest.raises(ValueError, match="overwrite"):
        run_experiment(output / "AB_hidden.yaml")


def test_aborted_identity_is_recorded(tmp_path, monkeypatch):
    _, output = suite(tmp_path)

    class ErrorAgent:
        name = "error"

        def act(self, *args):
            return AgentDecision(action=None, parse_error="test error")

    monkeypatch.setattr("hanabi_ck.runner._build_agent", lambda spec, seed: ErrorAgent())
    summary = run_experiment(output / "AB_named.yaml")
    assert summary["games"][0]["aborted"]
    record = json.loads(Path(summary["games"][0]["log_path"]).read_text())
    assert record["identity_setup"]["mode"] == "named"
    assert "model-B" in record["private_instruction"]


def test_analysis_pairs_only_valid_completed_seeds(tmp_path):
    manifest, output = suite(tmp_path)
    for cell in manifest["cells"][:2]:
        mode = cell["disclosure"]
        path = Path(cell["summary_path"])
        path.parent.mkdir(parents=True)
        games = [
            {
                "seed": seed,
                "valid": seed == 0,
                "agent_error_count": seed,
                "score": 10 + (mode == "named"),
                "turns": 50,
                "hints": 20,
                "misplays": 0,
                "fallback_count": 0,
            }
            for seed in (0, 1)
        ]
        # aggregate_games requires all standard metrics on valid games.
        for g in games:
            for key in (
                "plays",
                "successful_plays",
                "epistemically_safe_plays",
                "epistemically_unsafe_plays",
                "successful_unsafe_plays",
                "unsafe_play_rate",
                "discards",
                "fallback_rate",
                "successful_plays_per_hint",
                "perfect",
                "failed",
            ):
                g[key] = 0
        path.write_text(
            json.dumps(
                {
                    "conditions": ["ck0"],
                    "games": games,
                    "identity_config_sha256": cell["config_sha256"],
                    "identity_setup": {"mode": mode, "agent_models": ["model-A"] * 2},
                }
            )
        )
    report = analyze_identity_suite(output / "manifest.json")
    assert report["paired"]["AA"]["n_valid_pairs"] == 1
    assert report["paired"]["AA"]["mean_score_difference"] == 1
    assert len(report["missing_cells"]) == 6
    assert report["cells"]["AA_hidden"]["aggregate"]["n_aborted_games"] == 1
