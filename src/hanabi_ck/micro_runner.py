from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path
from statistics import mean, stdev
from typing import Any

from .actions import Action
from .agents import OpenAICompatibleAgent
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


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _paired_hash_comparison(
    left_samples: list[dict[str, Any]],
    right_samples: list[dict[str, Any]],
    *,
    field: str,
    valid_field: str,
    left_condition: str,
    right_condition: str,
) -> dict[str, Any]:
    left_by_rep = {
        int(sample["repetition"]): sample
        for sample in left_samples
        if sample.get(valid_field) and sample.get(field)
    }
    right_by_rep = {
        int(sample["repetition"]): sample
        for sample in right_samples
        if sample.get(valid_field) and sample.get(field)
    }
    repetitions = sorted(set(left_by_rep).intersection(right_by_rep))
    matches = sum(
        left_by_rep[rep][field] == right_by_rep[rep][field]
        for rep in repetitions
    )
    n = len(repetitions)
    return {
        "left_condition": left_condition,
        "right_condition": right_condition,
        "n_paired": n,
        "hash_match_count": matches,
        "hash_match_rate": matches / n if n else None,
    }


def _all_pairwise_hash_comparisons(
    samples: list[dict[str, Any]],
    conditions: list[str],
    *,
    field: str,
    valid_field: str,
) -> dict[str, Any]:
    by_condition = {
        condition: [
            sample for sample in samples
            if sample["condition"] == condition
        ]
        for condition in conditions
    }
    out: dict[str, Any] = {}
    for left_index, left in enumerate(conditions):
        for right in conditions[left_index + 1:]:
            key = f"{left}__vs__{right}"
            out[key] = _paired_hash_comparison(
                by_condition[left],
                by_condition[right],
                field=field,
                valid_field=valid_field,
                left_condition=left,
                right_condition=right,
            )
    return out


def _wilson_interval(
    successes: int,
    n: int,
    *,
    z: float = 1.959963984540054,
) -> list[float] | None:
    if n <= 0:
        return None
    p = successes / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denominator
    half = (
        z
        * math.sqrt(
            p * (1.0 - p) / n
            + z2 / (4.0 * n * n)
        )
        / denominator
    )
    return [max(0.0, center - half), min(1.0, center + half)]


def _paired_binary_comparison(
    left_samples: list[dict[str, Any]],
    right_samples: list[dict[str, Any]],
    *,
    field: str,
    valid_field: str,
    left_condition: str,
    right_condition: str,
) -> dict[str, Any]:
    left_by_rep = {
        int(sample["repetition"]): sample
        for sample in left_samples
        if sample.get(valid_field)
    }
    right_by_rep = {
        int(sample["repetition"]): sample
        for sample in right_samples
        if sample.get(valid_field)
    }
    repetitions = sorted(set(left_by_rep).intersection(right_by_rep))

    pairs: list[tuple[bool, bool]] = [
        (
            bool(left_by_rep[rep].get(field)),
            bool(right_by_rep[rep].get(field)),
        )
        for rep in repetitions
    ]
    n = len(pairs)
    both = sum(left and right for left, right in pairs)
    neither = sum((not left) and (not right) for left, right in pairs)
    left_only = sum(left and not right for left, right in pairs)
    right_only = sum((not left) and right for left, right in pairs)

    if not pairs:
        return {
            "left_condition": left_condition,
            "right_condition": right_condition,
            "n_paired": 0,
            "both_positive": 0,
            "neither_positive": 0,
            "left_only": 0,
            "right_only": 0,
            "left_rate": None,
            "right_rate": None,
            "delta_right_minus_left": None,
            "delta_ci95_normal": None,
        }

    left_rate = mean(float(left) for left, _ in pairs)
    right_rate = mean(float(right) for _, right in pairs)
    differences = [
        float(right) - float(left)
        for left, right in pairs
    ]
    delta = mean(differences)

    if len(differences) > 1:
        se = stdev(differences) / math.sqrt(len(differences))
        ci = [
            max(-1.0, delta - 1.959963984540054 * se),
            min(1.0, delta + 1.959963984540054 * se),
        ]
    else:
        ci = [delta, delta]

    return {
        "left_condition": left_condition,
        "right_condition": right_condition,
        "n_paired": n,
        "both_positive": both,
        "neither_positive": neither,
        "left_only": left_only,
        "right_only": right_only,
        "left_rate": left_rate,
        "right_rate": right_rate,
        "delta_right_minus_left": delta,
        "delta_ci95_normal": ci,
    }


def _all_pairwise_comparisons(
    samples: list[dict[str, Any]],
    conditions: list[str],
    *,
    field: str,
    valid_field: str,
) -> dict[str, Any]:
    by_condition = {
        condition: [
            sample for sample in samples
            if sample["condition"] == condition
        ]
        for condition in conditions
    }
    comparisons: dict[str, Any] = {}
    for left_index, left in enumerate(conditions):
        for right in conditions[left_index + 1:]:
            key = f"{left}__vs__{right}"
            comparisons[key] = _paired_binary_comparison(
                by_condition[left],
                by_condition[right],
                field=field,
                valid_field=valid_field,
                left_condition=left,
                right_condition=right,
            )
    return comparisons


def _comparisons_vs_baseline(
    comparisons: dict[str, Any],
    baseline: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, comparison in comparisons.items():
        if comparison["left_condition"] == baseline:
            result[comparison["right_condition"]] = comparison
        elif comparison["right_condition"] == baseline:
            flipped = dict(comparison)
            flipped["left_condition"] = baseline
            flipped["right_condition"] = comparison["left_condition"]
            flipped["left_rate"] = comparison["right_rate"]
            flipped["right_rate"] = comparison["left_rate"]
            flipped["left_only"] = comparison["right_only"]
            flipped["right_only"] = comparison["left_only"]
            delta = comparison["delta_right_minus_left"]
            flipped["delta_right_minus_left"] = (
                -delta if delta is not None else None
            )
            ci = comparison["delta_ci95_normal"]
            flipped["delta_ci95_normal"] = (
                [-ci[1], -ci[0]] if ci is not None else None
            )
            result[flipped["right_condition"]] = flipped
    return result


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
                "newest_selection_rate_ci95_wilson": None,
                "play_rate": None,
                "safe_candidate_play_rate": None,
                "newest_given_safe_candidate_play_rate": None,
                "epistemically_safe_play_rate": None,
                "action_type_counts": {},
                "play_card_index_counts": {},
                "probe_valid_count": 0,
                "probe_error_count": 0,
                "probe_newest_count": 0,
                "probe_newest_rate": None,
                "probe_newest_rate_ci95_wilson": None,
                "action_matches_probe_rate": None,
                "coindexed_action_newest_when_probe_newest_rate": None,
                "recognition_behavior_gap": None,
                "recognition_behavior_table": {},
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

    probe_valid = [
        sample for sample in valid
        if sample.get("probe_valid") is True
    ]
    probe_error_count = sum(
        1 for sample in valid
        if sample.get("probe_enabled")
        and not sample.get("probe_valid")
    )
    probe_newest_count = sum(
        bool(sample.get("probe_inferred_newest_target"))
        for sample in probe_valid
    )
    action_matches_probe_count = sum(
        sample.get("selected_card_index")
        == sample.get("probe_intended_card_index")
        for sample in probe_valid
        if sample.get("selected_card_index") is not None
    )
    probe_with_play = [
        sample for sample in probe_valid
        if sample.get("selected_card_index") is not None
    ]
    probe_newest = [
        sample for sample in probe_valid
        if sample.get("probe_inferred_newest_target")
    ]

    recognition_behavior_table = {
        "both_newest": sum(
            bool(sample.get("probe_inferred_newest_target"))
            and bool(sample["selected_newest_target"])
            for sample in probe_valid
        ),
        "probe_newest_action_not": sum(
            bool(sample.get("probe_inferred_newest_target"))
            and not bool(sample["selected_newest_target"])
            for sample in probe_valid
        ),
        "action_newest_probe_not": sum(
            not bool(sample.get("probe_inferred_newest_target"))
            and bool(sample["selected_newest_target"])
            for sample in probe_valid
        ),
        "neither_newest": sum(
            not bool(sample.get("probe_inferred_newest_target"))
            and not bool(sample["selected_newest_target"])
            for sample in probe_valid
        ),
    }

    out.update(
        {
            "newest_selection_count": newest_count,
            "newest_selection_rate": newest_count / len(valid),
            "newest_selection_rate_ci95_wilson": _wilson_interval(
                newest_count,
                len(valid),
            ),
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
            "probe_valid_count": len(probe_valid),
            "probe_error_count": probe_error_count,
            "probe_newest_count": probe_newest_count,
            "probe_newest_rate": (
                probe_newest_count / len(probe_valid)
                if probe_valid
                else None
            ),
            "probe_newest_rate_ci95_wilson": _wilson_interval(
                probe_newest_count,
                len(probe_valid),
            ),
            "action_matches_probe_rate": (
                action_matches_probe_count / len(probe_with_play)
                if probe_with_play
                else None
            ),
            "coindexed_action_newest_when_probe_newest_rate": (
                mean(
                    float(sample["selected_newest_target"])
                    for sample in probe_newest
                )
                if probe_newest
                else None
            ),
            "recognition_behavior_gap": (
                (
                    probe_newest_count / len(probe_valid)
                    - newest_count / len(valid)
                )
                if probe_valid
                else None
            ),
            "recognition_behavior_table": recognition_behavior_table,
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
    repetitions = int(cfg.get("repetitions", 100))
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
    condition_order_seed = int(cfg.get("condition_order_seed", 200_000))
    shadow_probe = bool(cfg.get("shadow_intention_probe", False))
    probe_seed_offset = int(cfg.get("probe_seed_offset", 1_000_000))
    if shadow_probe and base_agent_spec.get("type") != "openai_compatible":
        raise ValueError(
            "shadow_intention_probe currently requires an openai_compatible agent"
        )

    ck1_informed_players = {
        int(p)
        for p in cfg.get(
            "ck1_informed_players",
            [scenario.acting_player],
        )
    }

    all_samples: list[dict[str, Any]] = []
    loggers: dict[str, JsonlLogger] = {}
    for condition_name in conditions:
        log_path = output_root / f"{condition_name}.jsonl"
        if log_path.exists():
            log_path.unlink()
        loggers[condition_name] = JsonlLogger(log_path)

    for repetition in range(repetitions):
        sample_seed = sample_seed_start + repetition
        legal_actions = _ordered_actions(
            scenario,
            repetition=repetition,
            shuffle=shuffle_actions,
            action_order_seed=action_order_seed,
        )
        target_action_index = legal_actions.index(scenario.target_action)

        condition_order = list(conditions)
        random.Random(
            condition_order_seed + repetition
        ).shuffle(condition_order)

        for condition_order_index, condition_name in enumerate(condition_order):
            condition = get_condition(condition_name)
            logger = loggers[condition_name]
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

            request_payload_hash: str | None = None
            if isinstance(agent, OpenAICompatibleAgent):
                request_payload_hash = _payload_hash(
                    agent._request_payload(
                        scenario.observation,
                        legal_actions,
                        private_instruction,
                    )
                )

            # Action is sampled first. The shadow probe is a separate stateless
            # request and is never included in the action prompt or future context.
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

            probe_valid = False
            probe_error: str | None = None
            probe_intended_card_index: int | None = None
            probe_inferred_newest_target = False
            probe_raw_response: str | None = None
            probe_response_channel: str | None = None
            probe_api_response: dict[str, Any] | None = None
            probe_request_payload_hash: str | None = None
            probe_seed: int | None = None

            if shadow_probe:
                probe_seed = probe_seed_offset + sample_seed
                probe_agent_spec = _agent_spec_for_sample(
                    base_agent_spec,
                    sample_seed=probe_seed,
                    vary_api_seed=vary_api_seed,
                )
                probe_agent = _build_agent(
                    probe_agent_spec,
                    seed=probe_seed,
                )
                if not isinstance(probe_agent, OpenAICompatibleAgent):
                    raise RuntimeError(
                        "shadow probe requires OpenAICompatibleAgent"
                    )
                probe_request_payload_hash = _payload_hash(
                    probe_agent._intention_probe_payload(
                        scenario.observation,
                        private_instruction,
                        scenario.trigger_hint,
                        list(scenario.diagnostic_safe_card_indices),
                    )
                )
                probe = probe_agent.probe_intended_card(
                    scenario.observation,
                    private_instruction,
                    scenario.trigger_hint,
                    list(scenario.diagnostic_safe_card_indices),
                )
                probe_valid = (
                    probe.parse_error is None
                    and probe.intended_card_index is not None
                )
                probe_error = probe.parse_error
                probe_intended_card_index = probe.intended_card_index
                probe_inferred_newest_target = (
                    probe.intended_card_index
                    == scenario.target_action.card_index
                )
                probe_raw_response = probe.raw_response
                probe_response_channel = probe.response_channel
                probe_api_response = probe.api_response

            record = {
                "event_kind": "micro_sample",
                "experiment": experiment,
                "scenario": scenario.name,
                "scenario_description": scenario.description,
                "condition": condition_name,
                "condition_description": condition.description,
                "repetition": repetition,
                "sample_seed": sample_seed,
                "condition_order_seed": condition_order_seed + repetition,
                "condition_order": condition_order,
                "condition_order_index": condition_order_index,
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
                "request_payload_hash": request_payload_hash,
                "model_action_index": decision.action_index,
                "executed_action_index": executed_action_index,
                "selected_action": (
                    executable_action.to_dict()
                    if executable_action is not None
                    else None
                ),
                "selected_card_index": selected_card_index,
                "selected_newest_target": selected_newest_target,
                "selected_safe_candidate_play": selected_safe_candidate_play,
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
                "probe_enabled": shadow_probe,
                "probe_seed": probe_seed,
                "probe_request_payload_hash": probe_request_payload_hash,
                "probe_valid": probe_valid,
                "probe_error": probe_error,
                "probe_intended_card_index": probe_intended_card_index,
                "probe_inferred_newest_target": probe_inferred_newest_target,
                "probe_response_channel": probe_response_channel,
                "probe_raw_response": (
                    probe_raw_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
                "probe_api_response": (
                    probe_api_response
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

    action_pairwise = _all_pairwise_comparisons(
        all_samples,
        conditions,
        field="selected_newest_target",
        valid_field="valid",
    )
    probe_pairwise = (
        _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="probe_inferred_newest_target",
            valid_field="probe_valid",
        )
        if shadow_probe
        else {}
    )

    request_hash_pairwise = _all_pairwise_hash_comparisons(
        all_samples,
        conditions,
        field="request_payload_hash",
        valid_field="valid",
    )
    probe_hash_pairwise = (
        _all_pairwise_hash_comparisons(
            all_samples,
            conditions,
            field="probe_request_payload_hash",
            valid_field="probe_valid",
        )
        if shadow_probe
        else {}
    )

    baseline = "ck0" if "ck0" in conditions else conditions[0]
    paired_action_vs_baseline = _comparisons_vs_baseline(
        action_pairwise,
        baseline,
    )
    paired_probe_vs_baseline = (
        _comparisons_vs_baseline(probe_pairwise, baseline)
        if probe_pairwise
        else {}
    )

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
        "condition_order_seed": condition_order_seed,
        "vary_api_seed": vary_api_seed,
        "shadow_intention_probe": shadow_probe,
        "probe_seed_offset": probe_seed_offset,
        "ck1_informed_players": sorted(ck1_informed_players),
        "agent_error_policy": error_policy,
        "aggregate_by_condition": aggregate_by_condition,
        "paired_action_comparisons": action_pairwise,
        "paired_action_vs_baseline": paired_action_vs_baseline,
        "paired_probe_comparisons": probe_pairwise,
        "paired_probe_vs_baseline": paired_probe_vs_baseline,
        "paired_request_hash_comparisons": request_hash_pairwise,
        "paired_probe_hash_comparisons": probe_hash_pairwise,
        "samples": all_samples,
    }
    summary_path = output_root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary
