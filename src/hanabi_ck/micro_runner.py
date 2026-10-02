from __future__ import annotations

import copy
import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .actions import Action
from .conditions import DEFAULT_CONVENTION, get_condition
from .logging import JsonlLogger
from .micro_scenarios import MicroScenario, get_micro_scenario
from .runner import (
    ERROR_POLICIES,
    _build_agent,
    _hash_text,
    _resolve_agent_decision,
    load_config,
)


def _ordered_actions(
    scenario: MicroScenario,
    *,
    repetition: int,
    shuffle: bool,
    action_order_seed: int,
) -> list[Action]:
    actions = list(scenario.legal_actions)
    if shuffle:
        random.Random(action_order_seed + repetition).shuffle(actions)
    return actions


def _agent_spec_for_sample(
    base_spec: dict[str, Any],
    *,
    sample_seed: int,
    vary_api_seed: bool,
) -> dict[str, Any]:
    spec = copy.deepcopy(base_spec)
    if spec.get("type") == "openai_compatible" and vary_api_seed:
        extra_body = dict(spec.get("extra_body") or {})
        extra_body["seed"] = sample_seed
        spec["extra_body"] = extra_body
    return spec


def aggregate_micro_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [sample for sample in samples if sample["valid"]]
    out: dict[str, Any] = {
        "n_samples": len(samples),
        "n_valid_samples": len(valid),
        "n_error_samples": len(samples) - len(valid),
        "agent_error_count": sum(
            1 for sample in samples if sample.get("agent_error")
        ),
    }
    if not valid:
        out.update(
            {
                "newest_selection_count": 0,
                "newest_selection_rate": None,
                "play_rate": None,
                "safe_candidate_play_rate": None,
                "newest_given_safe_candidate_play_rate": None,
                "epistemically_safe_play_rate": None,
                "action_type_counts": {},
                "play_card_index_counts": {},
            }
        )
        return out

    newest_count = sum(
        bool(sample["selected_newest_target"]) for sample in valid
    )
    play_samples = [
        sample for sample in valid
        if sample["selected_action"]["type"] == "play"
    ]
    candidate_samples = [
        sample for sample in valid
        if sample["selected_safe_candidate_play"]
    ]
    safe_play_samples = [
        sample for sample in play_samples
        if sample["selected_epistemically_safe_play"]
    ]

    action_type_counts = Counter(
        sample["selected_action"]["type"] for sample in valid
    )
    play_card_index_counts = Counter(
        str(sample["selected_action"]["card_index"])
        for sample in play_samples
    )

    out.update(
        {
            "newest_selection_count": newest_count,
            "newest_selection_rate": newest_count / len(valid),
            "play_rate": len(play_samples) / len(valid),
            "safe_candidate_play_rate": len(candidate_samples) / len(valid),
            "newest_given_safe_candidate_play_rate": (
                mean(
                    float(sample["selected_newest_target"])
                    for sample in candidate_samples
                )
                if candidate_samples
                else None
            ),
            "epistemically_safe_play_rate": (
                len(safe_play_samples) / len(play_samples)
                if play_samples
                else None
            ),
            "action_type_counts": dict(sorted(action_type_counts.items())),
            "play_card_index_counts": dict(
                sorted(play_card_index_counts.items())
            ),
        }
    )
    return out


def run_micro_experiment(config_path: str | Path) -> dict[str, Any]:
    cfg = load_config(config_path)
    experiment = str(cfg.get("experiment", "hanabi_ck_micro"))
    scenario = get_micro_scenario(
        str(cfg.get("scenario", "newest_rank1_three_safe"))
    )
    output_root = (
        Path(cfg.get("output_dir", "runs"))
        / experiment
        / "micro"
        / scenario.name
    )
    output_root.mkdir(parents=True, exist_ok=True)

    conditions = list(
        cfg.get(
            "conditions",
            [
                "ck0",
                "ck1_private",
                "ck2_shared",
                "ck3_mutual",
                "ck_inf_common",
            ],
        )
    )
    repetitions = int(cfg.get("repetitions", 20))
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")

    convention = str(cfg.get("convention", DEFAULT_CONVENTION))
    error_policy = str(cfg.get("agent_error_policy", "abort"))
    if error_policy not in ERROR_POLICIES:
        raise ValueError(
            f"agent_error_policy must be one of {sorted(ERROR_POLICIES)}"
        )

    base_agent_spec = dict(cfg["agent"])
    sample_seed_start = int(cfg.get("sample_seed_start", 0))
    vary_api_seed = bool(cfg.get("vary_api_seed", True))
    shuffle_actions = bool(cfg.get("shuffle_legal_actions", True))
    action_order_seed = int(cfg.get("action_order_seed", 100_000))
    ck1_informed_players = {
        int(p)
        for p in cfg.get(
            "ck1_informed_players",
            [scenario.acting_player],
        )
    }

    all_samples: list[dict[str, Any]] = []

    for condition_name in conditions:
        condition = get_condition(condition_name)
        log_path = output_root / f"{condition_name}.jsonl"
        if log_path.exists():
            log_path.unlink()
        logger = JsonlLogger(log_path)

        for repetition in range(repetitions):
            sample_seed = sample_seed_start + repetition
            legal_actions = _ordered_actions(
                scenario,
                repetition=repetition,
                shuffle=shuffle_actions,
                action_order_seed=action_order_seed,
            )
            target_action_index = legal_actions.index(scenario.target_action)
            agent_spec = _agent_spec_for_sample(
                base_agent_spec,
                sample_seed=sample_seed,
                vary_api_seed=vary_api_seed,
            )
            agent = _build_agent(agent_spec, seed=sample_seed)

            private_instruction = condition.private_instruction(
                player_id=scenario.acting_player,
                num_players=scenario.num_players,
                convention=convention,
                informed_players=ck1_informed_players,
            )
            decision = agent.act(
                scenario.observation,
                legal_actions,
                private_instruction,
            )
            executable_action, runner_fallback_used = _resolve_agent_decision(
                decision,
                error_policy=error_policy,
                observation=scenario.observation,
                legal_actions=legal_actions,
            )

            valid = executable_action is not None
            selected_newest_target = (
                executable_action == scenario.target_action
                if executable_action is not None
                else False
            )
            selected_safe_candidate_play = False
            selected_epistemically_safe_play: bool | None = None
            selected_card_index: int | None = None

            if executable_action is not None and executable_action.type == "play":
                assert executable_action.card_index is not None
                selected_card_index = executable_action.card_index
                selected_safe_candidate_play = (
                    selected_card_index
                    in scenario.diagnostic_safe_card_indices
                )
                selected_epistemically_safe_play = (
                    selected_card_index
                    in scenario.observation.provably_playable_indices
                )

            executed_action_index = (
                legal_actions.index(executable_action)
                if executable_action is not None
                else None
            )
            record = {
                "event_kind": "micro_sample",
                "experiment": experiment,
                "scenario": scenario.name,
                "scenario_description": scenario.description,
                "condition": condition_name,
                "condition_description": condition.description,
                "repetition": repetition,
                "sample_seed": sample_seed,
                "action_order_seed": action_order_seed + repetition,
                "shuffle_legal_actions": shuffle_actions,
                "vary_api_seed": vary_api_seed,
                "acting_player": scenario.acting_player,
                "ck1_informed_players": sorted(ck1_informed_players),
                "private_instruction_hash": _hash_text(private_instruction),
                "private_instruction": (
                    private_instruction
                    if cfg.get("log_private_instructions", True)
                    else None
                ),
                "observation": scenario.observation.to_dict(),
                "trigger_hint": scenario.trigger_hint,
                "diagnostic_safe_card_indices": list(
                    scenario.diagnostic_safe_card_indices
                ),
                "target_action": scenario.target_action.to_dict(),
                "target_action_index": target_action_index,
                "legal_actions": [
                    {
                        "action_index": index,
                        "action": action.to_dict(),
                    }
                    for index, action in enumerate(legal_actions)
                ],
                "agent": {
                    "name": agent.name,
                    "type": agent_spec["type"],
                    "model": agent_spec.get("model"),
                    "response_error": decision.parse_error is not None,
                    "response_channel": decision.response_channel,
                    "error": decision.parse_error,
                    "fallback_used": runner_fallback_used,
                    "fallback_policy": (
                        error_policy if runner_fallback_used else None
                    ),
                },
                "model_action_index": decision.action_index,
                "executed_action_index": executed_action_index,
                "selected_action": (
                    executable_action.to_dict()
                    if executable_action is not None
                    else None
                ),
                "selected_card_index": selected_card_index,
                "selected_newest_target": selected_newest_target,
                "selected_safe_candidate_play": (
                    selected_safe_candidate_play
                ),
                "selected_epistemically_safe_play": (
                    selected_epistemically_safe_play
                ),
                "valid": valid,
                "agent_error": decision.parse_error is not None,
                "raw_response": (
                    decision.raw_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
                "api_response": (
                    decision.api_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
                "researcher_truth": scenario.researcher_truth,
            }
            logger.write(record)
            all_samples.append(record)

    aggregate_by_condition: dict[str, Any] = {}
    for condition_name in conditions:
        subset = [
            sample
            for sample in all_samples
            if sample["condition"] == condition_name
        ]
        aggregate_by_condition[condition_name] = aggregate_micro_samples(subset)

    summary = {
        "experiment": experiment,
        "config_path": str(config_path),
        "scenario": scenario.name,
        "scenario_description": scenario.description,
        "acting_player": scenario.acting_player,
        "target_action": scenario.target_action.to_dict(),
        "diagnostic_safe_card_indices": list(
            scenario.diagnostic_safe_card_indices
        ),
        "conditions": conditions,
        "repetitions": repetitions,
        "sample_seed_start": sample_seed_start,
        "shuffle_legal_actions": shuffle_actions,
        "action_order_seed": action_order_seed,
        "vary_api_seed": vary_api_seed,
        "ck1_informed_players": sorted(ck1_informed_players),
        "agent_error_policy": error_policy,
        "aggregate_by_condition": aggregate_by_condition,
        "samples": all_samples,
    }
    summary_path = output_root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary
