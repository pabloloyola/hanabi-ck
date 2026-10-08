"""Orchestrate sender/receiver micro experiments.

Keep experiment execution here; aggregation lives in :mod:`pair_analysis` and
intervention rendering lives in :mod:`pair_interventions`.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .actions import Action
from .agents import OpenAICompatibleAgent
from .conditions import DEFAULT_CONVENTION, get_condition
from .logging import JsonlLogger
from .micro_runner import _agent_spec_for_sample, _payload_hash
from .micro_scenarios import get_pair_micro_scenario
from .pair_analysis import aggregate_pair_samples, build_pairwise_metrics
from .pair_interventions import (
    INTERVENTION_ARMS,
    _self_derived_intervention_instruction,
)
from .scaffolds import normalize_mechanical_scaffold, render_hint_effects
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
    condition_wording_variant = str(
        cfg.get("condition_wording_variant", "canonical")
    )
    if condition_wording_variant not in {"canonical", "minimal_pair"}:
        raise ValueError(
            "condition_wording_variant must be 'canonical' or 'minimal_pair'"
        )
    error_policy = str(cfg.get("agent_error_policy", "abort"))
    if error_policy not in ERROR_POLICIES:
        raise ValueError(
            f"agent_error_policy must be one of {sorted(ERROR_POLICIES)}"
        )

    mechanical_scaffold = normalize_mechanical_scaffold(
        cfg.get("mechanical_scaffold", "derived")
    )
    sender_only = bool(cfg.get("sender_only", False))
    sender_spec_base = dict(cfg.get("sender_agent") or cfg["agent"])
    receiver_spec_base = dict(cfg.get("receiver_agent") or cfg["agent"])
    sender_spec_base.setdefault("mechanical_scaffold", mechanical_scaffold)
    receiver_spec_base.setdefault("mechanical_scaffold", mechanical_scaffold)
    if sender_spec_base.get("type") != "openai_compatible":
        raise ValueError("micro-pair requires an openai_compatible sender")
    if (
        not sender_only
        and receiver_spec_base.get("type") != "openai_compatible"
    ):
        raise ValueError("micro-pair requires an openai_compatible receiver")

    sample_seed_start = int(cfg.get("sample_seed_start", 0))
    receiver_seed_offset = int(cfg.get("receiver_seed_offset", 1_000_000))
    sender_probe = bool(cfg.get("sender_shadow_probe", False))
    sender_probe_seed_offset = int(
        cfg.get("sender_probe_seed_offset", 2_000_000)
    )
    sender_mechanical_probe = bool(
        cfg.get("sender_shadow_mechanical_probe", False)
    )
    sender_mechanical_probe_seed_offset = int(
        cfg.get("sender_mechanical_probe_seed_offset", 3_000_000)
    )
    if sender_mechanical_probe and not scenario.epistemic_reliance_test:
        raise ValueError(
            "sender_shadow_mechanical_probe currently requires an "
            "epistemic-reliance scenario"
        )
    configured_intervention_arms = cfg.get("sender_intervention_arms")
    if configured_intervention_arms is None:
        sender_intervention_arms = (
            ["both"]
            if bool(cfg.get("sender_self_derived_intervention", False))
            else []
        )
    else:
        sender_intervention_arms = [
            str(arm).strip().lower()
            for arm in configured_intervention_arms
        ]
    if len(set(sender_intervention_arms)) != len(sender_intervention_arms):
        raise ValueError("sender_intervention_arms must not contain duplicates")
    unknown_intervention_arms = (
        set(sender_intervention_arms) - set(INTERVENTION_ARMS)
    )
    if unknown_intervention_arms:
        raise ValueError(
            "sender_intervention_arms contains unknown values: "
            + ", ".join(sorted(unknown_intervention_arms))
        )
    sender_self_derived_intervention = bool(sender_intervention_arms)
    sender_intervention_seed_offset = int(
        cfg.get("sender_intervention_seed_offset", 4_000_000)
    )
    sender_intervention_order_seed = int(
        cfg.get("sender_intervention_order_seed", 4_500_000)
    )
    if (
        any(
            arm in {"epistemic", "both"}
            for arm in sender_intervention_arms
        )
        and not sender_probe
    ):
        raise ValueError(
            "epistemic/both intervention arms require sender_shadow_probe"
        )
    if (
        any(
            arm in {"mechanical", "both"}
            for arm in sender_intervention_arms
        )
        and not sender_mechanical_probe
    ):
        raise ValueError(
            "mechanical/both intervention arms require "
            "sender_shadow_mechanical_probe"
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
        sender_hint_effects = []
        for index, action in enumerate(sender_actions):
            receiver_after = scenario.receiver_observation_after_hint(action)
            sender_hint_effects.append(
                {
                    "action_index": index,
                    "action": action.to_dict(),
                    "touched_indices": list(
                        scenario.touched_indices_for_hint(action)
                    ),
                    "receiver_provably_playable_indices_after_hint": list(
                        receiver_after.provably_playable_indices
                    ),
                    "receiver_provably_obsolete_indices_after_hint": list(
                        receiver_after.provably_obsolete_indices
                    ),
                }
            )
        sender_hint_effects_for_prompt = render_hint_effects(
            sender_hint_effects,
            mechanical_scaffold,
        )
        sender_convention_hint_index = sender_actions.index(
            scenario.convention_trigger_hint
        )

        mechanical_probe_candidates: list[dict[str, Any]] = []
        mechanical_probe_expected_effects: list[dict[str, Any]] = []
        robust_hint_index: int | None = None
        if sender_mechanical_probe:
            assert scenario.robust_hint is not None
            robust_hint_index = sender_actions.index(scenario.robust_hint)
            diagnostic_indices = [
                robust_hint_index,
                sender_convention_hint_index,
            ]
            effects_by_index = {
                int(effect["action_index"]): effect
                for effect in sender_hint_effects
            }
            for action_index in diagnostic_indices:
                effect = effects_by_index[action_index]
                mechanical_probe_candidates.append(
                    {
                        "action_index": action_index,
                        "action": dict(effect["action"]),
                    }
                )
                mechanical_probe_expected_effects.append(
                    {
                        "action_index": action_index,
                        "touched_indices": sorted(
                            int(index)
                            for index in effect["touched_indices"]
                        ),
                        "receiver_provably_playable_indices_after_hint": sorted(
                            int(index)
                            for index in effect[
                                "receiver_provably_playable_indices_after_hint"
                            ]
                        ),
                    }
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
                wording_variant=condition_wording_variant,
            )
            sender_instruction = (
                sender_condition_instruction
                + "\n\nDIAGNOSTIC COMMUNICATION GOAL:\n"
                + scenario.sender_goal
            )
            if mechanical_scaffold == "derived":
                sender_instruction += (
                    "\n\nPUBLIC MECHANICAL HINT EFFECTS:\n"
                    + "The following touched_indices and post-hint provable-safety "
                    + "annotations are deterministic consequences of the visible "
                    + "receiver hand, public knowledge, and public stacks; they are "
                    + "not hidden information. Use them to reason about which legal "
                    + "hint best achieves the goal:\n"
                    + json.dumps(
                        sender_hint_effects_for_prompt,
                        ensure_ascii=False,
                    )
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

            expected_sender_hint = (
                scenario.expected_sender_hint_for_condition(condition_name)
            )
            sender_used_robust_hint = (
                scenario.robust_hint is not None
                and sender_action == scenario.robust_hint
            )
            sender_epistemic_choice_correct = (
                sender_action == expected_sender_hint
                if expected_sender_hint is not None
                else None
            )

            sender_mechanical_probe_seed: int | None = None
            sender_mechanical_probe_request_hash: str | None = None
            sender_mechanical_probe_valid = False
            sender_mechanical_probe_error: str | None = None
            sender_mechanical_probe_effects: list[dict[str, Any]] | None = None
            sender_mechanical_probe_exact_correct: bool | None = None
            sender_mechanical_probe_robust_effect_correct: bool | None = None
            sender_mechanical_probe_convention_effect_correct: bool | None = None
            sender_mechanical_probe_raw_response: str | None = None
            sender_mechanical_probe_response_channel: str | None = None
            sender_mechanical_probe_api_response: dict[str, Any] | None = None

            if sender_action is None:
                record = {
                    "event_kind": "micro_pair_sample",
                    "experiment": experiment,
                    "scenario": scenario.name,
                    "condition": condition_name,
                    "condition_wording_variant": condition_wording_variant,
                    "mechanical_scaffold": mechanical_scaffold,
                    "repetition": repetition,
                    "valid": False,
                    "sender_only": sender_only,
                    "stage": "sender",
                    "sender_error": sender_decision.parse_error,
                    "sender_request_payload_hash": sender_request_hash,
                }
                logger.write(record)
                all_samples.append(record)
                continue

            if sender_mechanical_probe:
                sender_mechanical_probe_seed = (
                    sender_mechanical_probe_seed_offset + sender_seed
                )
                sender_mechanical_probe_spec = _agent_spec_for_sample(
                    sender_spec_base,
                    sample_seed=sender_mechanical_probe_seed,
                    vary_api_seed=vary_api_seed,
                )
                sender_mechanical_probe_agent = _build_agent(
                    sender_mechanical_probe_spec,
                    seed=sender_mechanical_probe_seed,
                )
                if not isinstance(
                    sender_mechanical_probe_agent,
                    OpenAICompatibleAgent,
                ):
                    raise RuntimeError(
                        "sender mechanical shadow probe requires "
                        "OpenAICompatibleAgent"
                    )

                sender_mechanical_probe_request_hash = _payload_hash(
                    sender_mechanical_probe_agent._sender_mechanical_probe_payload(
                        scenario.sender_observation,
                        mechanical_probe_candidates,
                    )
                )
                mechanical_probe_decision = (
                    sender_mechanical_probe_agent.probe_sender_mechanics(
                        scenario.sender_observation,
                        mechanical_probe_candidates,
                    )
                )
                sender_mechanical_probe_valid = (
                    mechanical_probe_decision.parse_error is None
                    and mechanical_probe_decision.hint_effects is not None
                )
                sender_mechanical_probe_error = (
                    mechanical_probe_decision.parse_error
                )
                sender_mechanical_probe_effects = (
                    mechanical_probe_decision.hint_effects
                )
                sender_mechanical_probe_raw_response = (
                    mechanical_probe_decision.raw_response
                )
                sender_mechanical_probe_response_channel = (
                    mechanical_probe_decision.response_channel
                )
                sender_mechanical_probe_api_response = (
                    mechanical_probe_decision.api_response
                )

                if sender_mechanical_probe_valid:
                    assert sender_mechanical_probe_effects is not None
                    expected_by_index = {
                        int(effect["action_index"]): effect
                        for effect in mechanical_probe_expected_effects
                    }
                    observed_by_index = {
                        int(effect["action_index"]): effect
                        for effect in sender_mechanical_probe_effects
                    }

                    def _mechanical_effect_matches(action_index: int) -> bool:
                        expected = expected_by_index[action_index]
                        observed = observed_by_index.get(action_index)
                        return (
                            observed is not None
                            and observed["touched_indices"]
                            == expected["touched_indices"]
                            and observed[
                                "receiver_provably_playable_indices_after_hint"
                            ]
                            == expected[
                                "receiver_provably_playable_indices_after_hint"
                            ]
                        )

                    assert robust_hint_index is not None
                    sender_mechanical_probe_robust_effect_correct = (
                        _mechanical_effect_matches(robust_hint_index)
                    )
                    sender_mechanical_probe_convention_effect_correct = (
                        _mechanical_effect_matches(
                            sender_convention_hint_index
                        )
                    )
                    sender_mechanical_probe_exact_correct = (
                        sender_mechanical_probe_robust_effect_correct
                        and sender_mechanical_probe_convention_effect_correct
                    )

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
                        sender_hint_effects_for_prompt,
                    )
                )
                probe_decision = sender_probe_agent.probe_sender_epistemics(
                    scenario.sender_observation,
                    sender_condition_instruction,
                    scenario.sender_goal,
                    sender_hint_effects_for_prompt,
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

            sender_epistemic_probe_exact_correct: bool | None = None
            sender_joint_probe_valid = (
                sender_probe_valid and sender_mechanical_probe_valid
            )
            sender_joint_mechanics_epistemics_correct: bool | None = None
            sender_failure_classification: str | None = None

            if sender_probe_valid:
                sender_epistemic_probe_exact_correct = (
                    sender_probe_mapping_correct
                    and sender_probe_partner_knowledge_correct
                )

            if sender_joint_probe_valid:
                sender_joint_mechanics_epistemics_correct = (
                    sender_mechanical_probe_exact_correct is True
                    and sender_epistemic_probe_exact_correct is True
                )
                if sender_mechanical_probe_exact_correct is not True:
                    sender_failure_classification = "mechanics_wrong"
                elif sender_epistemic_probe_exact_correct is not True:
                    sender_failure_classification = (
                        "mechanics_correct_epistemics_wrong"
                    )
                elif sender_epistemic_choice_correct is True:
                    sender_failure_classification = (
                        "both_probes_correct_action_correct"
                    )
                else:
                    sender_failure_classification = (
                        "both_probes_correct_action_wrong"
                    )

            sender_interventions: dict[str, dict[str, Any]] = {}
            arm_seed_slot = {
                "both": 0,
                "fresh": 1,
                "mechanical": 2,
                "epistemic": 3,
            }
            sender_intervention_order = list(sender_intervention_arms)
            random.Random(
                sender_intervention_order_seed
                + repetition * max(1, len(conditions))
                + condition_order_index
            ).shuffle(sender_intervention_order)

            for intervention_arm in sender_intervention_order:
                arm_result: dict[str, Any] = {
                    "enabled": True,
                    "valid": False,
                    "error": None,
                    "seed": None,
                    "instruction_hash": None,
                    "request_payload_hash": None,
                    "model_action_index": None,
                    "action": None,
                    "hint_label": None,
                    "used_convention_hint": None,
                    "used_robust_hint": None,
                    "epistemic_choice_correct": None,
                    "response_channel": None,
                    "raw_response": None,
                    "api_response": None,
                }

                prerequisite_ok = True
                if (
                    intervention_arm in {"mechanical", "both"}
                    and not sender_mechanical_probe_valid
                ):
                    prerequisite_ok = False
                    arm_result["error"] = "mechanical_probe_invalid"
                if (
                    intervention_arm in {"epistemic", "both"}
                    and not sender_probe_valid
                ):
                    prerequisite_ok = False
                    arm_result["error"] = (
                        "joint_probe_invalid"
                        if intervention_arm == "both"
                        else "epistemic_probe_invalid"
                    )

                if prerequisite_ok:
                    intervention_instruction = (
                        _self_derived_intervention_instruction(
                            sender_instruction,
                            arm=intervention_arm,
                            mechanical_effects=(
                                sender_mechanical_probe_effects
                                if intervention_arm in {"mechanical", "both"}
                                else None
                            ),
                            convention_hint_index=(
                                sender_probe_convention_hint_index
                                if intervention_arm in {"epistemic", "both"}
                                else None
                            ),
                            receiver_convention_knowledge=(
                                sender_probe_receiver_knowledge
                                if intervention_arm in {"epistemic", "both"}
                                else None
                            ),
                        )
                    )
                    arm_result["instruction_hash"] = _hash_text(
                        intervention_instruction
                    )
                    arm_seed = (
                        sender_intervention_seed_offset
                        + arm_seed_slot[intervention_arm] * 1_000_000
                        + sender_seed
                    )
                    arm_result["seed"] = arm_seed
                    intervention_spec = _agent_spec_for_sample(
                        sender_spec_base,
                        sample_seed=arm_seed,
                        vary_api_seed=vary_api_seed,
                    )
                    intervention_agent = _build_agent(
                        intervention_spec,
                        seed=arm_seed,
                    )
                    if not isinstance(
                        intervention_agent,
                        OpenAICompatibleAgent,
                    ):
                        raise RuntimeError(
                            "sender intervention requires "
                            "OpenAICompatibleAgent"
                        )

                    arm_result["request_payload_hash"] = _payload_hash(
                        intervention_agent._request_payload(
                            scenario.sender_observation,
                            sender_actions,
                            intervention_instruction,
                        )
                    )
                    intervention_decision = intervention_agent.act(
                        scenario.sender_observation,
                        sender_actions,
                        intervention_instruction,
                    )
                    intervention_action, _ = _resolve_agent_decision(
                        intervention_decision,
                        error_policy=error_policy,
                        observation=scenario.sender_observation,
                        legal_actions=sender_actions,
                    )
                    arm_result["error"] = intervention_decision.parse_error
                    arm_result["raw_response"] = (
                        intervention_decision.raw_response
                    )
                    arm_result["response_channel"] = (
                        intervention_decision.response_channel
                    )
                    arm_result["api_response"] = (
                        intervention_decision.api_response
                    )
                    arm_result["model_action_index"] = (
                        intervention_decision.action_index
                    )
                    arm_result["valid"] = (
                        intervention_action is not None
                        and intervention_decision.parse_error is None
                    )
                    if intervention_action is not None:
                        arm_result["action"] = intervention_action.to_dict()
                        arm_result["hint_label"] = _hint_label(
                            intervention_action
                        )
                        arm_result["used_convention_hint"] = (
                            intervention_action
                            == scenario.convention_trigger_hint
                        )
                        arm_result["used_robust_hint"] = (
                            scenario.robust_hint is not None
                            and intervention_action
                            == scenario.robust_hint
                        )
                        arm_result["epistemic_choice_correct"] = (
                            intervention_action == expected_sender_hint
                            if expected_sender_hint is not None
                            else None
                        )

                sender_interventions[intervention_arm] = arm_result

            # Backward-compatible aliases: the historical intervention is
            # exactly the "both" arm.
            legacy_intervention = sender_interventions.get("both")
            sender_intervention_seed = (
                legacy_intervention.get("seed")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_request_payload_hash = (
                legacy_intervention.get("request_payload_hash")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_instruction_hash = (
                legacy_intervention.get("instruction_hash")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_valid = bool(
                legacy_intervention
                and legacy_intervention.get("valid")
            )
            sender_intervention_error = (
                legacy_intervention.get("error")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_model_action_index = (
                legacy_intervention.get("model_action_index")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_action = (
                legacy_intervention.get("action")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_hint_label = (
                legacy_intervention.get("hint_label")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_used_convention_hint = (
                legacy_intervention.get("used_convention_hint")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_used_robust_hint = (
                legacy_intervention.get("used_robust_hint")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_epistemic_choice_correct = (
                legacy_intervention.get("epistemic_choice_correct")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_response_channel = (
                legacy_intervention.get("response_channel")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_raw_response = (
                legacy_intervention.get("raw_response")
                if legacy_intervention is not None
                else None
            )
            sender_intervention_api_response = (
                legacy_intervention.get("api_response")
                if legacy_intervention is not None
                else None
            )

            if sender_only:
                record = {
                    "event_kind": "micro_pair_sample",
                    "experiment": experiment,
                    "scenario": scenario.name,
                    "scenario_description": scenario.description,
                    "condition": condition_name,
                    "condition_wording_variant": condition_wording_variant,
                    "mechanical_scaffold": mechanical_scaffold,
                    "repetition": repetition,
                    "condition_order": condition_order,
                    "condition_order_index": condition_order_index,
                    "sender_only": True,
                    "sender_seed": sender_seed,
                    "sender_private_instruction_hash": _hash_text(
                        sender_condition_instruction
                    ),
                    "sender_request_payload_hash": sender_request_hash,
                    "sender_intervention_enabled": (
                        sender_self_derived_intervention
                    ),
                    "sender_intervention_arms": sender_intervention_arms,
                    "sender_intervention_order": sender_intervention_order,
                    "sender_interventions": sender_interventions,
                    "sender_intervention_seed": sender_intervention_seed,
                    "sender_intervention_instruction_hash": (
                        sender_intervention_instruction_hash
                    ),
                    "sender_intervention_request_payload_hash": (
                        sender_intervention_request_payload_hash
                    ),
                    "sender_intervention_valid": sender_intervention_valid,
                    "sender_intervention_error": sender_intervention_error,
                    "sender_intervention_model_action_index": (
                        sender_intervention_model_action_index
                    ),
                    "sender_intervention_action": sender_intervention_action,
                    "sender_intervention_hint_label": (
                        sender_intervention_hint_label
                    ),
                    "sender_intervention_used_convention_hint": (
                        sender_intervention_used_convention_hint
                    ),
                    "sender_intervention_used_robust_hint": (
                        sender_intervention_used_robust_hint
                    ),
                    "sender_intervention_epistemic_choice_correct": (
                        sender_intervention_epistemic_choice_correct
                    ),
                    "sender_intervention_response_channel": (
                        sender_intervention_response_channel
                    ),
                    "sender_intervention_raw_response": (
                        sender_intervention_raw_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                    "sender_intervention_api_response": (
                        sender_intervention_api_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                    "sender_mechanical_probe_enabled": sender_mechanical_probe,
                    "sender_mechanical_probe_seed": sender_mechanical_probe_seed,
                    "sender_mechanical_probe_request_payload_hash": (
                        sender_mechanical_probe_request_hash
                    ),
                    "sender_mechanical_probe_valid": sender_mechanical_probe_valid,
                    "sender_mechanical_probe_error": sender_mechanical_probe_error,
                    "sender_mechanical_probe_candidates": mechanical_probe_candidates,
                    "sender_mechanical_probe_expected_effects": (
                        mechanical_probe_expected_effects
                    ),
                    "sender_mechanical_probe_effects": (
                        sender_mechanical_probe_effects
                    ),
                    "sender_mechanical_probe_exact_correct": (
                        sender_mechanical_probe_exact_correct
                    ),
                    "sender_mechanical_probe_robust_effect_correct": (
                        sender_mechanical_probe_robust_effect_correct
                    ),
                    "sender_mechanical_probe_convention_effect_correct": (
                        sender_mechanical_probe_convention_effect_correct
                    ),
                    "sender_mechanical_probe_response_channel": (
                        sender_mechanical_probe_response_channel
                    ),
                    "sender_mechanical_probe_raw_response": (
                        sender_mechanical_probe_raw_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                    "sender_mechanical_probe_api_response": (
                        sender_mechanical_probe_api_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
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
                    "sender_epistemic_probe_exact_correct": (
                        sender_epistemic_probe_exact_correct
                    ),
                    "sender_joint_probe_valid": sender_joint_probe_valid,
                    "sender_joint_mechanics_epistemics_correct": (
                        sender_joint_mechanics_epistemics_correct
                    ),
                    "sender_failure_classification": (
                        sender_failure_classification
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
                    "sender_hint_effects_prompt": sender_hint_effects_for_prompt,
                    "sender_model_action_index": sender_decision.action_index,
                    "sender_action": sender_action.to_dict(),
                    "sender_hint_label": _hint_label(sender_action),
                    "sender_touched_indices": list(
                        scenario.touched_indices_for_hint(sender_action)
                    ),
                    "sender_used_convention_hint": (
                        sender_action == scenario.convention_trigger_hint
                    ),
                    "sender_used_robust_hint": sender_used_robust_hint,
                    "sender_expected_hint": (
                        expected_sender_hint.to_dict()
                        if expected_sender_hint is not None
                        else None
                    ),
                    "sender_epistemic_choice_correct": (
                        sender_epistemic_choice_correct
                    ),
                    "sender_agent": {
                        "model": sender_spec.get("model"),
                        "response_error": (
                            sender_decision.parse_error is not None
                        ),
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
                    "receiver_action": None,
                    "valid": True,
                }
                logger.write(record)
                all_samples.append(record)
                continue

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
                wording_variant=condition_wording_variant,
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
                "condition_wording_variant": condition_wording_variant,
                "mechanical_scaffold": mechanical_scaffold,
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
                "sender_intervention_enabled": (
                    sender_self_derived_intervention
                ),
                "sender_intervention_arms": sender_intervention_arms,
                "sender_intervention_order": sender_intervention_order,
                "sender_interventions": sender_interventions,
                "sender_intervention_seed": sender_intervention_seed,
                "sender_intervention_instruction_hash": (
                    sender_intervention_instruction_hash
                ),
                "sender_intervention_request_payload_hash": (
                    sender_intervention_request_payload_hash
                ),
                "sender_intervention_valid": sender_intervention_valid,
                "sender_intervention_error": sender_intervention_error,
                "sender_intervention_model_action_index": (
                    sender_intervention_model_action_index
                ),
                "sender_intervention_action": sender_intervention_action,
                "sender_intervention_hint_label": (
                    sender_intervention_hint_label
                ),
                "sender_intervention_used_convention_hint": (
                    sender_intervention_used_convention_hint
                ),
                "sender_intervention_used_robust_hint": (
                    sender_intervention_used_robust_hint
                ),
                "sender_intervention_epistemic_choice_correct": (
                    sender_intervention_epistemic_choice_correct
                ),
                "sender_intervention_response_channel": (
                    sender_intervention_response_channel
                ),
                "sender_intervention_raw_response": (
                    sender_intervention_raw_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
                "sender_intervention_api_response": (
                    sender_intervention_api_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
                "sender_mechanical_probe_enabled": sender_mechanical_probe,
                "sender_mechanical_probe_seed": sender_mechanical_probe_seed,
                "sender_mechanical_probe_request_payload_hash": (
                    sender_mechanical_probe_request_hash
                ),
                "sender_mechanical_probe_valid": sender_mechanical_probe_valid,
                "sender_mechanical_probe_error": sender_mechanical_probe_error,
                "sender_mechanical_probe_candidates": mechanical_probe_candidates,
                "sender_mechanical_probe_expected_effects": (
                    mechanical_probe_expected_effects
                ),
                "sender_mechanical_probe_effects": (
                    sender_mechanical_probe_effects
                ),
                "sender_mechanical_probe_exact_correct": (
                    sender_mechanical_probe_exact_correct
                ),
                "sender_mechanical_probe_robust_effect_correct": (
                    sender_mechanical_probe_robust_effect_correct
                ),
                "sender_mechanical_probe_convention_effect_correct": (
                    sender_mechanical_probe_convention_effect_correct
                ),
                "sender_mechanical_probe_response_channel": (
                    sender_mechanical_probe_response_channel
                ),
                "sender_mechanical_probe_raw_response": (
                    sender_mechanical_probe_raw_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
                "sender_mechanical_probe_api_response": (
                    sender_mechanical_probe_api_response
                    if cfg.get("log_raw_model_responses", True)
                    else None
                ),
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
                "sender_epistemic_probe_exact_correct": (
                    sender_epistemic_probe_exact_correct
                ),
                "sender_joint_probe_valid": sender_joint_probe_valid,
                "sender_joint_mechanics_epistemics_correct": (
                    sender_joint_mechanics_epistemics_correct
                ),
                "sender_failure_classification": (
                    sender_failure_classification
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
                "sender_hint_effects_prompt": sender_hint_effects_for_prompt,
                "sender_model_action_index": sender_decision.action_index,
                "sender_action": sender_action.to_dict(),
                "sender_hint_label": _hint_label(sender_action),
                "sender_touched_indices": list(
                    scenario.touched_indices_for_hint(sender_action)
                ),
                "sender_used_convention_hint": (
                    sender_action == scenario.convention_trigger_hint
                ),
                "sender_used_robust_hint": sender_used_robust_hint,
                "sender_expected_hint": (
                    expected_sender_hint.to_dict()
                    if expected_sender_hint is not None
                    else None
                ),
                "sender_epistemic_choice_correct": (
                    sender_epistemic_choice_correct
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

    pairwise_metrics = build_pairwise_metrics(
        all_samples,
        conditions,
        sender_only=sender_only,
        epistemic_reliance_test=scenario.epistemic_reliance_test,
        sender_probe=sender_probe,
        sender_mechanical_probe=sender_mechanical_probe,
        sender_intervention_arms=sender_intervention_arms,
    )
    summary = {
        "experiment": experiment,
        "scenario": scenario.name,
        "scenario_description": scenario.description,
        "mechanical_scaffold": mechanical_scaffold,
        "repetitions": repetitions,
        "conditions": conditions,
        "condition_wording_variant": condition_wording_variant,
        "ck1_informed_players": sorted(ck1_informed_players),
        "sender_only": sender_only,
        "sender_shadow_probe": sender_probe,
        "sender_probe_seed_offset": sender_probe_seed_offset,
        "sender_shadow_mechanical_probe": sender_mechanical_probe,
        "sender_mechanical_probe_seed_offset": (
            sender_mechanical_probe_seed_offset
        ),
        "sender_self_derived_intervention": (
            sender_self_derived_intervention
        ),
        "sender_intervention_arms": sender_intervention_arms,
        "sender_intervention_seed_offset": sender_intervention_seed_offset,
        "sender_intervention_order_seed": sender_intervention_order_seed,
        "aggregate_by_condition": aggregate_by_condition,
        **pairwise_metrics,
        "samples": all_samples,
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary
