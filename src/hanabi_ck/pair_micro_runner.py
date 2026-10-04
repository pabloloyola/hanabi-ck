from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .actions import Action
from .agents import OpenAICompatibleAgent
from .conditions import DEFAULT_CONVENTION, get_condition
from .logging import JsonlLogger
from .micro_runner import (
    _agent_spec_for_sample,
    _all_pairwise_comparisons,
    _all_pairwise_hash_comparisons,
    _comparisons_vs_baseline,
    _payload_hash,
    _wilson_interval,
)
from .micro_scenarios import get_pair_micro_scenario
from .runner import (
    ERROR_POLICIES,
    _build_agent,
    _hash_text,
    _resolve_agent_decision,
    load_config,
)


def _shuffle_actions(
    actions: tuple[Action, ...] | list[Action],
    *,
    seed: int,
    enabled: bool,
) -> list[Action]:
    out = list(actions)
    if enabled:
        random.Random(seed).shuffle(out)
    return out


def _hint_label(action: Action) -> str:
    if action.type != "hint":
        return action.type
    return f"{action.attribute}={action.value}"


def _expected_receiver_convention_knowledge(condition: str) -> str:
    expected = {
        "ck0": "no_convention",
        "ck1_private": "unknown",
        "ck2_shared": "unknown",
        "ck3_mutual": "known",
        "ck_inf_common": "known",
    }
    try:
        return expected[condition]
    except KeyError as exc:
        raise ValueError(
            f"No sender-probe epistemic expectation for condition {condition!r}"
        ) from exc


def aggregate_pair_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [sample for sample in samples if sample["valid"]]
    if not valid:
        return {
            "n_samples": len(samples),
            "n_valid_samples": 0,
            "n_error_samples": len(samples),
            "sender_convention_hint_rate": None,
            "sender_hint_counts": {},
            "receiver_newest_rate": None,
            "safe_coordination_success_rate": None,
            "convention_chain_success_rate": None,
            "receiver_newest_given_convention_hint_rate": None,
            "sender_probe_valid_count": 0,
            "sender_probe_error_count": 0,
            "sender_probe_identified_convention_hint_rate": None,
            "sender_probe_mapping_accuracy": None,
            "sender_probe_partner_knowledge_accuracy": None,
            "sender_probe_partner_knowledge_counts": {},
            "sender_probe_knowledge_to_action_gap": None,
            "sender_action_matches_probe_hint_rate": None,
        }

    sender_trigger_count = sum(
        bool(sample["sender_used_convention_hint"])
        for sample in valid
    )
    receiver_newest_count = sum(
        bool(sample["receiver_selected_newest"])
        for sample in valid
    )
    trigger_samples = [
        sample for sample in valid
        if sample["sender_used_convention_hint"]
    ]
    safe_coordination_count = sum(
        bool(sample["safe_coordination_success"])
        for sample in valid
    )
    convention_chain_count = sum(
        bool(sample["convention_chain_success"])
        for sample in valid
    )
    receiver_action_types = Counter(
        sample["receiver_action"]["type"]
        for sample in valid
    )
    sender_hint_counts = Counter(
        sample["sender_hint_label"]
        for sample in valid
    )
    probe_valid = [
        sample for sample in valid
        if sample.get("sender_probe_valid") is True
    ]
    probe_enabled = [
        sample for sample in valid
        if sample.get("sender_probe_enabled")
    ]
    probe_identified_count = sum(
        bool(sample.get("sender_probe_identified_convention_hint"))
        for sample in probe_valid
    )
    probe_mapping_correct_count = sum(
        bool(sample.get("sender_probe_mapping_correct"))
        for sample in probe_valid
    )
    probe_partner_correct_count = sum(
        bool(sample.get("sender_probe_partner_knowledge_correct"))
        for sample in probe_valid
    )
    probe_partner_counts = Counter(
        str(sample.get("sender_probe_receiver_convention_knowledge"))
        for sample in probe_valid
    )
    probe_action_match_count = sum(
        sample.get("sender_probe_convention_hint_index")
        == sample.get("sender_model_action_index")
        for sample in probe_valid
        if sample.get("sender_probe_convention_hint_index") != -1
    )
    probe_action_match_denominator = sum(
        sample.get("sender_probe_convention_hint_index") != -1
        for sample in probe_valid
    )

    return {
        "n_samples": len(samples),
        "n_valid_samples": len(valid),
        "n_error_samples": len(samples) - len(valid),
        "sender_convention_hint_count": sender_trigger_count,
        "sender_convention_hint_rate": sender_trigger_count / len(valid),
        "sender_convention_hint_rate_ci95_wilson": _wilson_interval(
            sender_trigger_count,
            len(valid),
        ),
        "sender_hint_counts": dict(sorted(sender_hint_counts.items())),
        "receiver_newest_count": receiver_newest_count,
        "receiver_newest_rate": receiver_newest_count / len(valid),
        "receiver_newest_rate_ci95_wilson": _wilson_interval(
            receiver_newest_count,
            len(valid),
        ),
        "safe_coordination_success_count": safe_coordination_count,
        "safe_coordination_success_rate": (
            safe_coordination_count / len(valid)
        ),
        "safe_coordination_success_rate_ci95_wilson": _wilson_interval(
            safe_coordination_count,
            len(valid),
        ),
        "convention_chain_success_count": convention_chain_count,
        "convention_chain_success_rate": (
            convention_chain_count / len(valid)
        ),
        "convention_chain_success_rate_ci95_wilson": _wilson_interval(
            convention_chain_count,
            len(valid),
        ),
        "receiver_newest_given_convention_hint_rate": (
            mean(
                float(sample["receiver_selected_newest"])
                for sample in trigger_samples
            )
            if trigger_samples
            else None
        ),
        "receiver_action_type_counts": dict(
            sorted(receiver_action_types.items())
        ),
        "receiver_epistemically_safe_play_rate": (
            mean(
                float(sample["receiver_epistemically_safe_play"])
                for sample in valid
                if sample["receiver_action"]["type"] == "play"
            )
            if any(
                sample["receiver_action"]["type"] == "play"
                for sample in valid
            )
            else None
        ),
        "sender_probe_valid_count": len(probe_valid),
        "sender_probe_error_count": len(probe_enabled) - len(probe_valid),
        "sender_probe_identified_convention_hint_rate": (
            probe_identified_count / len(probe_valid)
            if probe_valid
            else None
        ),
        "sender_probe_mapping_accuracy": (
            probe_mapping_correct_count / len(probe_valid)
            if probe_valid
            else None
        ),
        "sender_probe_partner_knowledge_accuracy": (
            probe_partner_correct_count / len(probe_valid)
            if probe_valid
            else None
        ),
        "sender_probe_partner_knowledge_counts": dict(
            sorted(probe_partner_counts.items())
        ),
        "sender_probe_knowledge_to_action_gap": (
            probe_identified_count / len(probe_valid)
            - sender_trigger_count / len(valid)
            if probe_valid
            else None
        ),
        "sender_action_matches_probe_hint_rate": (
            probe_action_match_count / probe_action_match_denominator
            if probe_action_match_denominator
            else None
        ),
    }


def run_pair_micro_experiment(config_path: str | Path) -> dict[str, Any]:
    cfg = load_config(config_path)
    experiment = str(cfg.get("experiment", "hanabi_ck_pair_micro"))
    scenario = get_pair_micro_scenario(
        str(cfg.get("scenario", "sender_receiver_newest_intent"))
    )
    output_root = (
        Path(cfg.get("output_dir", "runs"))
        / experiment
        / "micro_pair"
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

    sender_spec_base = dict(cfg.get("sender_agent") or cfg["agent"])
    receiver_spec_base = dict(cfg.get("receiver_agent") or cfg["agent"])
    if (
        sender_spec_base.get("type") != "openai_compatible"
        or receiver_spec_base.get("type") != "openai_compatible"
    ):
        raise ValueError(
            "micro-pair currently requires openai_compatible sender and receiver"
        )

    sample_seed_start = int(cfg.get("sample_seed_start", 0))
    receiver_seed_offset = int(cfg.get("receiver_seed_offset", 1_000_000))
    sender_probe = bool(cfg.get("sender_shadow_probe", False))
    sender_probe_seed_offset = int(
        cfg.get("sender_probe_seed_offset", 2_000_000)
    )
    vary_api_seed = bool(cfg.get("vary_api_seed", True))
    shuffle_actions = bool(cfg.get("shuffle_legal_actions", True))
    sender_action_order_seed = int(
        cfg.get("sender_action_order_seed", 300_000)
    )
    receiver_action_order_seed = int(
        cfg.get("receiver_action_order_seed", 400_000)
    )
    condition_order_seed = int(cfg.get("condition_order_seed", 500_000))
    ck1_informed_players = {
        int(p)
        for p in cfg.get(
            "ck1_informed_players",
            [scenario.sender_player],
        )
    }

    loggers: dict[str, JsonlLogger] = {}
    for condition_name in conditions:
        log_path = output_root / f"{condition_name}.jsonl"
        if log_path.exists():
            log_path.unlink()
        loggers[condition_name] = JsonlLogger(log_path)

    all_samples: list[dict[str, Any]] = []

    for repetition in range(repetitions):
        sender_seed = sample_seed_start + repetition
        receiver_seed = receiver_seed_offset + sender_seed
        condition_order = list(conditions)
        random.Random(
            condition_order_seed + repetition
        ).shuffle(condition_order)

        sender_actions = _shuffle_actions(
            scenario.sender_hint_actions,
            seed=sender_action_order_seed + repetition,
            enabled=shuffle_actions,
        )
        sender_hint_effects = [
            {
                "action_index": index,
                "action": action.to_dict(),
                "touched_indices": list(
                    scenario.touched_indices_for_hint(action)
                ),
            }
            for index, action in enumerate(sender_actions)
        ]
        sender_convention_hint_index = sender_actions.index(
            scenario.convention_trigger_hint
        )

        for condition_order_index, condition_name in enumerate(condition_order):
            condition = get_condition(condition_name)
            logger = loggers[condition_name]

            sender_spec = _agent_spec_for_sample(
                sender_spec_base,
                sample_seed=sender_seed,
                vary_api_seed=vary_api_seed,
            )
            sender = _build_agent(sender_spec, seed=sender_seed)
            if not isinstance(sender, OpenAICompatibleAgent):
                raise RuntimeError("sender must be OpenAICompatibleAgent")

            sender_condition_instruction = condition.private_instruction(
                player_id=scenario.sender_player,
                num_players=scenario.num_players,
                convention=convention,
                informed_players=ck1_informed_players,
            )
            sender_instruction = (
                sender_condition_instruction
                + "\n\nDIAGNOSTIC COMMUNICATION GOAL:\n"
                + scenario.sender_goal
                + "\n\nPUBLIC MECHANICAL HINT EFFECTS:\n"
                + "The following touched_indices are deterministic consequences "
                + "of the visible receiver hand, not hidden information. Use them "
                + "to reason about which legal hint communicates the goal:\n"
                + json.dumps(sender_hint_effects, ensure_ascii=False)
            )
            sender_request_hash = _payload_hash(
                sender._request_payload(
                    scenario.sender_observation,
                    sender_actions,
                    sender_instruction,
                )
            )
            sender_decision = sender.act(
                scenario.sender_observation,
                sender_actions,
                sender_instruction,
            )
            sender_action, sender_fallback = _resolve_agent_decision(
                sender_decision,
                error_policy=error_policy,
                observation=scenario.sender_observation,
                legal_actions=sender_actions,
            )

            if sender_action is None:
                record = {
                    "event_kind": "micro_pair_sample",
                    "experiment": experiment,
                    "scenario": scenario.name,
                    "condition": condition_name,
                    "repetition": repetition,
                    "valid": False,
                    "stage": "sender",
                    "sender_error": sender_decision.parse_error,
                    "sender_request_payload_hash": sender_request_hash,
                }
                logger.write(record)
                all_samples.append(record)
                continue

            sender_probe_seed: int | None = None
            sender_probe_request_hash: str | None = None
            sender_probe_valid = False
            sender_probe_error: str | None = None
            sender_probe_convention_hint_index: int | None = None
            sender_probe_receiver_knowledge: str | None = None
            sender_probe_raw_response: str | None = None
            sender_probe_response_channel: str | None = None
            sender_probe_api_response: dict[str, Any] | None = None

            if sender_probe:
                sender_probe_seed = sender_probe_seed_offset + sender_seed
                sender_probe_spec = _agent_spec_for_sample(
                    sender_spec_base,
                    sample_seed=sender_probe_seed,
                    vary_api_seed=vary_api_seed,
                )
                sender_probe_agent = _build_agent(
                    sender_probe_spec,
                    seed=sender_probe_seed,
                )
                if not isinstance(
                    sender_probe_agent,
                    OpenAICompatibleAgent,
                ):
                    raise RuntimeError(
                        "sender shadow probe requires OpenAICompatibleAgent"
                    )
                sender_probe_request_hash = _payload_hash(
                    sender_probe_agent._sender_epistemic_probe_payload(
                        scenario.sender_observation,
                        sender_condition_instruction,
                        scenario.sender_goal,
                        sender_hint_effects,
                    )
                )
                probe_decision = sender_probe_agent.probe_sender_epistemics(
                    scenario.sender_observation,
                    sender_condition_instruction,
                    scenario.sender_goal,
                    sender_hint_effects,
                )
                sender_probe_valid = (
                    probe_decision.parse_error is None
                    and probe_decision.convention_hint_index is not None
                    and probe_decision.receiver_convention_knowledge is not None
                )
                sender_probe_error = probe_decision.parse_error
                sender_probe_convention_hint_index = (
                    probe_decision.convention_hint_index
                )
                sender_probe_receiver_knowledge = (
                    probe_decision.receiver_convention_knowledge
                )
                sender_probe_raw_response = probe_decision.raw_response
                sender_probe_response_channel = (
                    probe_decision.response_channel
                )
                sender_probe_api_response = probe_decision.api_response

            expected_probe_hint_index = (
                -1
                if condition_name == "ck0"
                else sender_convention_hint_index
            )
            expected_receiver_knowledge = (
                _expected_receiver_convention_knowledge(condition_name)
            )
            sender_probe_identified_convention_hint = (
                sender_probe_valid
                and sender_probe_convention_hint_index
                == sender_convention_hint_index
            )
            sender_probe_mapping_correct = (
                sender_probe_valid
                and sender_probe_convention_hint_index
                == expected_probe_hint_index
            )
            sender_probe_partner_knowledge_correct = (
                sender_probe_valid
                and sender_probe_receiver_knowledge
                == expected_receiver_knowledge
            )

            receiver_observation = (
                scenario.receiver_observation_after_hint(sender_action)
            )
            receiver_actions = _shuffle_actions(
                scenario.receiver_legal_actions_after_hint(sender_action),
                seed=receiver_action_order_seed + repetition,
                enabled=shuffle_actions,
            )

            receiver_spec = _agent_spec_for_sample(
                receiver_spec_base,
                sample_seed=receiver_seed,
                vary_api_seed=vary_api_seed,
            )
            receiver = _build_agent(receiver_spec, seed=receiver_seed)
            if not isinstance(receiver, OpenAICompatibleAgent):
                raise RuntimeError("receiver must be OpenAICompatibleAgent")

            receiver_instruction = condition.private_instruction(
                player_id=scenario.receiver_player,
                num_players=scenario.num_players,
                convention=convention,
                informed_players=ck1_informed_players,
            )
            receiver_request_hash = _payload_hash(
                receiver._request_payload(
                    receiver_observation,
                    receiver_actions,
                    receiver_instruction,
                )
            )
            receiver_decision = receiver.act(
                receiver_observation,
                receiver_actions,
                receiver_instruction,
            )
            receiver_action, receiver_fallback = _resolve_agent_decision(
                receiver_decision,
                error_policy=error_policy,
                observation=receiver_observation,
                legal_actions=receiver_actions,
            )

            valid = receiver_action is not None
            receiver_selected_newest = (
                receiver_action == scenario.receiver_target_action
                if receiver_action is not None
                else False
            )
            receiver_epistemically_safe_play: bool | None = None
            if receiver_action is not None and receiver_action.type == "play":
                assert receiver_action.card_index is not None
                receiver_epistemically_safe_play = (
                    receiver_action.card_index
                    in receiver_observation.provably_playable_indices
                )

            safe_coordination_success = (
                receiver_selected_newest
                and receiver_epistemically_safe_play is True
            )
            convention_chain_success = (
                sender_action == scenario.convention_trigger_hint
                and safe_coordination_success
            )

            record = {
                "event_kind": "micro_pair_sample",
                "experiment": experiment,
                "scenario": scenario.name,
                "scenario_description": scenario.description,
                "condition": condition_name,
                "repetition": repetition,
                "condition_order": condition_order,
                "condition_order_index": condition_order_index,
                "sender_seed": sender_seed,
                "receiver_seed": receiver_seed,
                "sender_private_instruction_hash": _hash_text(
                    sender_condition_instruction
                ),
                "receiver_private_instruction_hash": _hash_text(
                    receiver_instruction
                ),
                "sender_request_payload_hash": sender_request_hash,
                "receiver_request_payload_hash": receiver_request_hash,
                "sender_probe_enabled": sender_probe,
                "sender_probe_seed": sender_probe_seed,
                "sender_probe_request_payload_hash": (
                    sender_probe_request_hash
                ),
                "sender_probe_valid": sender_probe_valid,
                "sender_probe_error": sender_probe_error,
                "sender_probe_expected_hint_index": expected_probe_hint_index,
                "sender_probe_convention_hint_index": (
                    sender_probe_convention_hint_index
                ),
                "sender_probe_identified_convention_hint": (
                    sender_probe_identified_convention_hint
                ),
                "sender_probe_mapping_correct": sender_probe_mapping_correct,
                "sender_probe_expected_receiver_convention_knowledge": (
                    expected_receiver_knowledge
                ),
                "sender_probe_receiver_convention_knowledge": (
                    sender_probe_receiver_knowledge
                ),
                "sender_probe_partner_knowledge_correct": (
                    sender_probe_partner_knowledge_correct
                ),
                "sender_probe_response_channel": (
                    sender_probe_response_channel
                ),
                "sender_probe_raw_response": (
                    sender_probe_raw_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
                "sender_probe_api_response": (
                    sender_probe_api_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
                "sender_goal": scenario.sender_goal,
                "sender_observation": scenario.sender_observation.to_dict(),
                "sender_legal_hints": [
                    action.to_dict() for action in sender_actions
                ],
                "sender_hint_effects": sender_hint_effects,
                "sender_model_action_index": sender_decision.action_index,
                "sender_action": sender_action.to_dict(),
                "sender_hint_label": _hint_label(sender_action),
                "sender_touched_indices": list(
                    scenario.touched_indices_for_hint(sender_action)
                ),
                "sender_used_convention_hint": (
                    sender_action == scenario.convention_trigger_hint
                ),
                "sender_agent": {
                    "model": sender_spec.get("model"),
                    "response_error": sender_decision.parse_error is not None,
                    "response_channel": sender_decision.response_channel,
                    "error": sender_decision.parse_error,
                    "fallback_used": sender_fallback,
                    "raw_response": (
                        sender_decision.raw_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                    "api_response": (
                        sender_decision.api_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                },
                "receiver_observation": receiver_observation.to_dict(),
                "receiver_legal_actions": [
                    action.to_dict() for action in receiver_actions
                ],
                "receiver_model_action_index": receiver_decision.action_index,
                "receiver_action": (
                    receiver_action.to_dict()
                    if receiver_action is not None
                    else None
                ),
                "receiver_selected_newest": receiver_selected_newest,
                "receiver_epistemically_safe_play": (
                    receiver_epistemically_safe_play
                ),
                "safe_coordination_success": safe_coordination_success,
                "convention_chain_success": convention_chain_success,
                "receiver_agent": {
                    "model": receiver_spec.get("model"),
                    "response_error": receiver_decision.parse_error is not None,
                    "response_channel": receiver_decision.response_channel,
                    "error": receiver_decision.parse_error,
                    "fallback_used": receiver_fallback,
                    "raw_response": (
                        receiver_decision.raw_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                    "api_response": (
                        receiver_decision.api_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                },
                "valid": valid,
            }
            logger.write(record)
            all_samples.append(record)

    aggregate_by_condition: dict[str, Any] = {}
    for condition_name in conditions:
        subset = [
            sample for sample in all_samples
            if sample["condition"] == condition_name
        ]
        aggregate_by_condition[condition_name] = aggregate_pair_samples(subset)

    receiver_pairwise = _all_pairwise_comparisons(
        all_samples,
        conditions,
        field="receiver_selected_newest",
        valid_field="valid",
    )
    safe_coordination_pairwise = _all_pairwise_comparisons(
        all_samples,
        conditions,
        field="safe_coordination_success",
        valid_field="valid",
    )
    convention_chain_pairwise = _all_pairwise_comparisons(
        all_samples,
        conditions,
        field="convention_chain_success",
        valid_field="valid",
    )
    sender_probe_identification_pairwise = (
        _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="sender_probe_identified_convention_hint",
            valid_field="sender_probe_valid",
        )
        if sender_probe
        else {}
    )
    sender_probe_request_hash_pairwise = (
        _all_pairwise_hash_comparisons(
            all_samples,
            conditions,
            field="sender_probe_request_payload_hash",
            valid_field="sender_probe_valid",
        )
        if sender_probe
        else {}
    )
    sender_request_hash_pairwise = _all_pairwise_hash_comparisons(
        all_samples,
        conditions,
        field="sender_request_payload_hash",
        valid_field="valid",
    )
    receiver_request_hash_pairwise = _all_pairwise_hash_comparisons(
        all_samples,
        conditions,
        field="receiver_request_payload_hash",
        valid_field="valid",
    )
    baseline = "ck0" if "ck0" in conditions else conditions[0]
    summary = {
        "experiment": experiment,
        "scenario": scenario.name,
        "scenario_description": scenario.description,
        "repetitions": repetitions,
        "conditions": conditions,
        "ck1_informed_players": sorted(ck1_informed_players),
        "sender_shadow_probe": sender_probe,
        "sender_probe_seed_offset": sender_probe_seed_offset,
        "aggregate_by_condition": aggregate_by_condition,
        "paired_receiver_comparisons": receiver_pairwise,
        "paired_receiver_vs_baseline": _comparisons_vs_baseline(
            receiver_pairwise,
            baseline,
        ),
        "paired_safe_coordination_comparisons": (
            safe_coordination_pairwise
        ),
        "paired_safe_coordination_vs_baseline": _comparisons_vs_baseline(
            safe_coordination_pairwise,
            baseline,
        ),
        "paired_convention_chain_comparisons": convention_chain_pairwise,
        "paired_convention_chain_vs_baseline": _comparisons_vs_baseline(
            convention_chain_pairwise,
            baseline,
        ),
        "paired_sender_probe_identification_comparisons": (
            sender_probe_identification_pairwise
        ),
        "paired_sender_probe_identification_vs_baseline": (
            _comparisons_vs_baseline(
                sender_probe_identification_pairwise,
                baseline,
            )
            if sender_probe_identification_pairwise
            else {}
        ),
        "paired_sender_probe_request_hash_comparisons": (
            sender_probe_request_hash_pairwise
        ),
        "paired_sender_request_hash_comparisons": (
            sender_request_hash_pairwise
        ),
        "paired_receiver_request_hash_comparisons": (
            receiver_request_hash_pairwise
        ),
        "samples": all_samples,
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary
