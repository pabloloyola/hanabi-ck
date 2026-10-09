"""Offline golden traces recorded from the pre-cleanup runner at 9d18ede.

These checks lock request payloads/order, seeds, logs, and complete summaries.
No model API is called. Golden fixtures must not be regenerated from a refactor.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from hanabi_ck import pair_execution, pair_micro_runner
from hanabi_ck.actions import Action
from hanabi_ck.agents import (
    AgentDecision,
    OpenAICompatibleAgent,
    SenderEpistemicProbeDecision,
    SenderMechanicalProbeDecision,
)
from hanabi_ck.micro_scenarios import get_pair_micro_scenario

CASES = [
    "sender_factorial", "receiver_factorial", "no_probes", "epistemic_only",
    "mechanical_only", "legacy_both", "logging_off", "vary_api_seed",
    "derived", "mechanical_invalid", "epistemic_invalid", "both_invalid",
    "sender_invalid", "receiver_invalid", "safe_baseline", "intervention_invalid",
    "mechanics_wrong", "ck_ladder", "canonical", "unshuffled",
]


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _offline_run(tmp_path, monkeypatch, case, runner=pair_micro_runner):
    cfg = yaml.safe_load(Path(
        "configs/micro_sender_reliance_openrouter_gpt_5_4_raw_factorial_intervention_smoke.yaml"
    ).read_text())
    cfg.update(experiment="offline_regression", output_dir=str(tmp_path), repetitions=3)
    cfg["agent"]["api_key"] = "offline-test-key"
    cfg["sender_only"] = case not in {"receiver_factorial", "receiver_invalid"}
    if case == "no_probes":
        cfg.update(sender_shadow_probe=False, sender_shadow_mechanical_probe=False,
                   sender_intervention_arms=[])
    elif case == "epistemic_only":
        cfg.update(sender_shadow_mechanical_probe=False,
                   sender_intervention_arms=["epistemic", "fresh"])
    elif case == "mechanical_only":
        cfg.update(sender_shadow_probe=False,
                   sender_intervention_arms=["mechanical", "fresh"])
    elif case == "legacy_both":
        cfg.pop("sender_intervention_arms")
        cfg["sender_self_derived_intervention"] = True
    elif case == "logging_off":
        cfg["log_raw_model_responses"] = False
    elif case == "vary_api_seed":
        cfg["vary_api_seed"] = True
    elif case == "derived":
        cfg["mechanical_scaffold"] = "derived"
    elif case == "safe_baseline":
        cfg["agent_error_policy"] = "safe_baseline"
    elif case == "ck_ladder":
        cfg["conditions"] = ["ck0", "ck1_private", "ck2_shared", "ck3_mutual", "ck_inf_common"]
    elif case == "canonical":
        cfg["condition_wording_variant"] = "canonical"
    elif case == "unshuffled":
        cfg["shuffle_legal_actions"] = False
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    trace = []
    build = runner._build_agent

    def traced_build(spec, *, seed):
        trace.append({"kind": "build", "spec": spec, "seed": seed})
        return build(spec, seed=seed)

    monkeypatch.setattr(runner, "_build_agent", traced_build)
    monkeypatch.setattr(pair_execution, "_build_agent", traced_build)

    action_count = 0

    def act(self, observation, legal_actions, private_instruction):
        nonlocal action_count
        action_count += 1
        trace.append({"kind": "action", "payload": self._request_payload(
            observation, legal_actions, private_instruction)})
        invalid = (case in {"sender_invalid", "safe_baseline"} and observation.player_id == 0) or (
            case == "receiver_invalid" and observation.player_id == 1) or (
            case == "intervention_invalid" and action_count % 3 == 2)
        index = len(trace) % len(legal_actions)
        return AgentDecision(
            action=None if invalid else legal_actions[index],
            action_index=None if invalid else index,
            parse_error="offline_invalid_action" if invalid else None,
            raw_response="offline_action", response_channel="content",
            api_response={"offline": "action"},
        )

    def mechanics(self, observation, candidates):
        trace.append({"kind": "mechanical", "payload":
                      self._sender_mechanical_probe_payload(observation, candidates)})
        scenario = get_pair_micro_scenario(cfg["scenario"])
        effects = []
        for candidate in candidates:
            action = Action.from_dict(candidate["action"])
            after = scenario.receiver_observation_after_hint(action)
            effects.append({
                "action_index": candidate["action_index"],
                "touched_indices": list(scenario.touched_indices_for_hint(action)),
                "receiver_provably_playable_indices_after_hint": list(
                    after.provably_playable_indices),
            })
        if case == "mechanics_wrong":
            effects[0]["touched_indices"] = []
        invalid = case in {"mechanical_invalid", "both_invalid"}
        return SenderMechanicalProbeDecision(
            hint_effects=None if invalid else effects,
            parse_error="offline_invalid_mechanics" if invalid else None,
            raw_response="offline_mechanics", response_channel="content",
            api_response={"offline": "mechanics"},
        )

    def epistemics(self, observation, instruction, goal, effects):
        trace.append({"kind": "epistemic", "payload":
                      self._sender_epistemic_probe_payload(observation, instruction, goal, effects)})
        invalid = case in {"epistemic_invalid", "both_invalid"}
        return SenderEpistemicProbeDecision(
            convention_hint_index=None if invalid else 0,
            receiver_convention_knowledge=None if invalid else "unknown",
            parse_error="offline_invalid_epistemics" if invalid else None,
            raw_response="offline_epistemics", response_channel="content",
            api_response={"offline": "epistemics"},
        )

    monkeypatch.setattr(OpenAICompatibleAgent, "act", act)
    monkeypatch.setattr(OpenAICompatibleAgent, "probe_sender_mechanics", mechanics)
    monkeypatch.setattr(OpenAICompatibleAgent, "probe_sender_epistemics", epistemics)
    summary = runner.run_pair_micro_experiment(path)
    logs = {p.name: p.read_text() for p in tmp_path.rglob("*.jsonl")}
    return {"summary": _digest(summary), "trace": _digest(trace), "logs": _digest(logs)}


@pytest.mark.parametrize("case", CASES)
def test_pair_execution_preserves_pre_cleanup_behavior(tmp_path, monkeypatch, case):
    expected = json.loads(Path("tests/fixtures/pair_execution_pre_cleanup.json").read_text())
    assert _offline_run(tmp_path, monkeypatch, case) == expected[case]
