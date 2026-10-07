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


def _self_derived_intervention_instruction(
    sender_instruction: str,
    *,
    mechanical_effects: list[dict[str, Any]],
    convention_hint_index: int,
    receiver_convention_knowledge: str,
) -> str:
    """Append the model's own shadow-probe outputs to a fresh action prompt."""
    self_derived = {
        "mechanical_hint_effects": mechanical_effects,
        "epistemic_facts": {
            "convention_hint_index": convention_hint_index,
            "receiver_convention_knowledge": receiver_convention_knowledge,
        },
    }
    return (
        sender_instruction
        + "\n\nSELF-DERIVED FACTS FROM INDEPENDENT SHADOW PROBES:\n"
        + "These are your own independently elicited derivations, not "
        + "researcher ground truth. Use them together with the visible Hanabi "
        + "state and the communication goal when selecting an action.\n"
        + json.dumps(self_derived, ensure_ascii=False)
    )


def aggregate_pair_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [sample for sample in samples if sample["valid"]]
    if not valid:
        return {
            "n_samples": len(samples),
            "n_valid_samples": 0,
            "n_error_samples": len(samples),
            "sender_convention_hint_rate": None,
            "sender_robust_hint_rate": None,
            "sender_epistemic_choice_accuracy": None,
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
            "sender_mechanical_probe_valid_count": 0,
            "sender_mechanical_probe_error_count": 0,
            "sender_mechanical_probe_exact_accuracy": None,
            "sender_mechanical_probe_robust_effect_accuracy": None,
            "sender_mechanical_probe_convention_effect_accuracy": None,
            "sender_choice_accuracy_given_exact_mechanics": None,
            "sender_mechanics_correct_but_choice_wrong_rate": None,
            "sender_joint_probe_valid_count": 0,
            "sender_joint_probe_error_count": 0,
            "sender_joint_mechanics_epistemics_accuracy": None,
            "sender_choice_accuracy_given_joint_probe_correct": None,
            "sender_both_probes_correct_but_choice_wrong_rate": None,
            "sender_failure_classification_counts": {},
            "sender_intervention_valid_count": 0,
            "sender_intervention_error_count": 0,
            "sender_intervention_convention_hint_rate": None,
            "sender_intervention_epistemic_choice_accuracy": None,
            "sender_baseline_intervention_choice_transition_counts": {},
            "sender_baseline_wrong_intervention_rescue_rate": None,
            "sender_joint_correct_baseline_wrong_intervention_rescue_rate": None,
        }

    sender_trigger_count = sum(
        bool(sample["sender_used_convention_hint"])
        for sample in valid
    )
    sender_robust_count = sum(
        bool(sample.get("sender_used_robust_hint"))
        for sample in valid
    )
    epistemic_choice_samples = [
        sample for sample in valid
        if sample.get("sender_epistemic_choice_correct") is not None
    ]
    epistemic_choice_correct_count = sum(
        bool(sample.get("sender_epistemic_choice_correct"))
        for sample in epistemic_choice_samples
    )
    receiver_valid = [
        sample for sample in valid
        if sample.get("receiver_action") is not None
    ]
    receiver_newest_count = sum(
        bool(sample.get("receiver_selected_newest"))
        for sample in receiver_valid
    )
    trigger_samples = [
        sample for sample in receiver_valid
        if sample["sender_used_convention_hint"]
    ]
    safe_coordination_count = sum(
        bool(sample.get("safe_coordination_success"))
        for sample in receiver_valid
    )
    convention_chain_count = sum(
        bool(sample.get("convention_chain_success"))
        for sample in receiver_valid
    )
    receiver_action_types = Counter(
        sample["receiver_action"]["type"]
        for sample in receiver_valid
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

    mechanical_probe_valid = [
        sample for sample in valid
        if sample.get("sender_mechanical_probe_valid") is True
    ]
    mechanical_probe_enabled = [
        sample for sample in valid
        if sample.get("sender_mechanical_probe_enabled")
    ]
    mechanical_exact_count = sum(
        bool(sample.get("sender_mechanical_probe_exact_correct"))
        for sample in mechanical_probe_valid
    )
    mechanical_robust_correct_count = sum(
        bool(sample.get("sender_mechanical_probe_robust_effect_correct"))
        for sample in mechanical_probe_valid
    )
    mechanical_convention_correct_count = sum(
        bool(sample.get("sender_mechanical_probe_convention_effect_correct"))
        for sample in mechanical_probe_valid
    )
    exact_mechanics_with_choice = [
        sample for sample in mechanical_probe_valid
        if sample.get("sender_mechanical_probe_exact_correct") is True
        and sample.get("sender_epistemic_choice_correct") is not None
    ]
    exact_mechanics_choice_correct_count = sum(
        bool(sample.get("sender_epistemic_choice_correct"))
        for sample in exact_mechanics_with_choice
    )

    joint_probe_valid = [
        sample for sample in valid
        if sample.get("sender_probe_valid") is True
        and sample.get("sender_mechanical_probe_valid") is True
    ]
    joint_probe_enabled = [
        sample for sample in valid
        if sample.get("sender_probe_enabled")
        and sample.get("sender_mechanical_probe_enabled")
    ]
    joint_correct = [
        sample for sample in joint_probe_valid
        if sample.get("sender_mechanical_probe_exact_correct") is True
        and sample.get("sender_probe_mapping_correct") is True
        and sample.get("sender_probe_partner_knowledge_correct") is True
    ]
    joint_correct_with_choice = [
        sample for sample in joint_correct
        if sample.get("sender_epistemic_choice_correct") is not None
    ]
    joint_correct_choice_correct_count = sum(
        bool(sample.get("sender_epistemic_choice_correct"))
        for sample in joint_correct_with_choice
    )

    failure_classification_counts: Counter[str] = Counter()
    for sample in joint_probe_valid:
        mechanics_correct = (
            sample.get("sender_mechanical_probe_exact_correct") is True
        )
        epistemics_correct = (
            sample.get("sender_probe_mapping_correct") is True
            and sample.get("sender_probe_partner_knowledge_correct") is True
        )
        action_correct = sample.get("sender_epistemic_choice_correct") is True

        if not mechanics_correct:
            label = "mechanics_wrong"
        elif not epistemics_correct:
            label = "mechanics_correct_epistemics_wrong"
        elif action_correct:
            label = "both_probes_correct_action_correct"
        else:
            label = "both_probes_correct_action_wrong"
        failure_classification_counts[label] += 1

    intervention_enabled = [
        sample for sample in valid
        if sample.get("sender_intervention_enabled")
    ]
    intervention_valid = [
        sample for sample in valid
        if sample.get("sender_intervention_valid") is True
    ]
    intervention_convention_count = sum(
        bool(sample.get("sender_intervention_used_convention_hint"))
        for sample in intervention_valid
    )
    intervention_choice_samples = [
        sample for sample in intervention_valid
        if sample.get("sender_intervention_epistemic_choice_correct") is not None
    ]
    intervention_choice_correct_count = sum(
        bool(sample.get("sender_intervention_epistemic_choice_correct"))
        for sample in intervention_choice_samples
    )

    transition_counts: Counter[str] = Counter()
    for sample in intervention_choice_samples:
        baseline_correct = (
            sample.get("sender_epistemic_choice_correct") is True
        )
        intervention_correct = (
            sample.get("sender_intervention_epistemic_choice_correct") is True
        )
        transition_counts[
            (
                "baseline_correct_intervention_correct"
                if baseline_correct and intervention_correct
                else "baseline_correct_intervention_wrong"
                if baseline_correct
                else "baseline_wrong_intervention_correct"
                if intervention_correct
                else "baseline_wrong_intervention_wrong"
            )
        ] += 1

    baseline_wrong_with_intervention = [
        sample for sample in intervention_choice_samples
        if sample.get("sender_epistemic_choice_correct") is False
    ]
    baseline_wrong_rescued_count = sum(
        sample.get("sender_intervention_epistemic_choice_correct") is True
        for sample in baseline_wrong_with_intervention
    )
    joint_correct_baseline_wrong = [
        sample for sample in intervention_choice_samples
        if sample.get("sender_joint_mechanics_epistemics_correct") is True
        and sample.get("sender_epistemic_choice_correct") is False
    ]
    joint_correct_baseline_wrong_rescued_count = sum(
        sample.get("sender_intervention_epistemic_choice_correct") is True
        for sample in joint_correct_baseline_wrong
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
        "sender_robust_hint_count": sender_robust_count,
        "sender_robust_hint_rate": sender_robust_count / len(valid),
        "sender_epistemic_choice_correct_count": (
            epistemic_choice_correct_count
            if epistemic_choice_samples
            else None
        ),
        "sender_epistemic_choice_accuracy": (
            epistemic_choice_correct_count / len(epistemic_choice_samples)
            if epistemic_choice_samples
            else None
        ),
        "sender_hint_counts": dict(sorted(sender_hint_counts.items())),
        "receiver_newest_count": (
            receiver_newest_count if receiver_valid else None
        ),
        "receiver_newest_rate": (
            receiver_newest_count / len(receiver_valid)
            if receiver_valid
            else None
        ),
        "receiver_newest_rate_ci95_wilson": (
            _wilson_interval(receiver_newest_count, len(receiver_valid))
            if receiver_valid
            else None
        ),
        "safe_coordination_success_count": (
            safe_coordination_count if receiver_valid else None
        ),
        "safe_coordination_success_rate": (
            safe_coordination_count / len(receiver_valid)
            if receiver_valid
            else None
        ),
        "safe_coordination_success_rate_ci95_wilson": (
            _wilson_interval(safe_coordination_count, len(receiver_valid))
            if receiver_valid
            else None
        ),
        "convention_chain_success_count": (
            convention_chain_count if receiver_valid else None
        ),
        "convention_chain_success_rate": (
            convention_chain_count / len(receiver_valid)
            if receiver_valid
            else None
        ),
        "convention_chain_success_rate_ci95_wilson": (
            _wilson_interval(convention_chain_count, len(receiver_valid))
            if receiver_valid
            else None
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
                for sample in receiver_valid
                if sample["receiver_action"]["type"] == "play"
            )
            if any(
                sample["receiver_action"]["type"] == "play"
                for sample in receiver_valid
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
        "sender_mechanical_probe_valid_count": len(mechanical_probe_valid),
        "sender_mechanical_probe_error_count": (
            len(mechanical_probe_enabled) - len(mechanical_probe_valid)
        ),
        "sender_mechanical_probe_exact_accuracy": (
            mechanical_exact_count / len(mechanical_probe_valid)
            if mechanical_probe_valid
            else None
        ),
        "sender_mechanical_probe_robust_effect_accuracy": (
            mechanical_robust_correct_count / len(mechanical_probe_valid)
            if mechanical_probe_valid
            else None
        ),
        "sender_mechanical_probe_convention_effect_accuracy": (
            mechanical_convention_correct_count / len(mechanical_probe_valid)
            if mechanical_probe_valid
            else None
        ),
        "sender_choice_accuracy_given_exact_mechanics": (
            exact_mechanics_choice_correct_count / len(exact_mechanics_with_choice)
            if exact_mechanics_with_choice
            else None
        ),
        "sender_mechanics_correct_but_choice_wrong_rate": (
            1.0
            - exact_mechanics_choice_correct_count / len(exact_mechanics_with_choice)
            if exact_mechanics_with_choice
            else None
        ),
        "sender_joint_probe_valid_count": len(joint_probe_valid),
        "sender_joint_probe_error_count": (
            len(joint_probe_enabled) - len(joint_probe_valid)
        ),
        "sender_joint_mechanics_epistemics_accuracy": (
            len(joint_correct) / len(joint_probe_valid)
            if joint_probe_valid
            else None
        ),
        "sender_choice_accuracy_given_joint_probe_correct": (
            joint_correct_choice_correct_count / len(joint_correct_with_choice)
            if joint_correct_with_choice
            else None
        ),
        "sender_both_probes_correct_but_choice_wrong_rate": (
            1.0
            - joint_correct_choice_correct_count / len(joint_correct_with_choice)
            if joint_correct_with_choice
            else None
        ),
        "sender_failure_classification_counts": dict(
            sorted(failure_classification_counts.items())
        ),
        "sender_intervention_valid_count": len(intervention_valid),
        "sender_intervention_error_count": (
            len(intervention_enabled) - len(intervention_valid)
        ),
        "sender_intervention_convention_hint_rate": (
            intervention_convention_count / len(intervention_valid)
            if intervention_valid
            else None
        ),
        "sender_intervention_epistemic_choice_accuracy": (
            intervention_choice_correct_count / len(intervention_choice_samples)
            if intervention_choice_samples
            else None
        ),
        "sender_baseline_intervention_choice_transition_counts": dict(
            sorted(transition_counts.items())
        ),
        "sender_baseline_wrong_intervention_rescue_rate": (
            baseline_wrong_rescued_count / len(baseline_wrong_with_intervention)
            if baseline_wrong_with_intervention
            else None
        ),
        "sender_joint_correct_baseline_wrong_intervention_rescue_rate": (
            joint_correct_baseline_wrong_rescued_count
            / len(joint_correct_baseline_wrong)
            if joint_correct_baseline_wrong
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
    sender_self_derived_intervention = bool(
        cfg.get("sender_self_derived_intervention", False)
    )
    sender_intervention_seed_offset = int(
        cfg.get("sender_intervention_seed_offset", 4_000_000)
    )
    if sender_self_derived_intervention and not (
        sender_probe and sender_mechanical_probe
    ):
        raise ValueError(
            "sender_self_derived_intervention requires both "
            "sender_shadow_probe and sender_shadow_mechanical_probe"
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

            sender_intervention_seed: int | None = None
            sender_intervention_request_payload_hash: str | None = None
            sender_intervention_instruction_hash: str | None = None
            sender_intervention_valid = False
            sender_intervention_error: str | None = None
            sender_intervention_model_action_index: int | None = None
            sender_intervention_action: Action | None = None
            sender_intervention_hint_label: str | None = None
            sender_intervention_used_convention_hint: bool | None = None
            sender_intervention_used_robust_hint: bool | None = None
            sender_intervention_epistemic_choice_correct: bool | None = None
            sender_intervention_raw_response: str | None = None
            sender_intervention_response_channel: str | None = None
            sender_intervention_api_response: dict[str, Any] | None = None

            if sender_self_derived_intervention:
                if not sender_joint_probe_valid:
                    sender_intervention_error = "prerequisite_probe_invalid"
                else:
                    assert sender_mechanical_probe_effects is not None
                    assert sender_probe_convention_hint_index is not None
                    assert sender_probe_receiver_knowledge is not None

                    intervention_instruction = (
                        _self_derived_intervention_instruction(
                            sender_instruction,
                            mechanical_effects=sender_mechanical_probe_effects,
                            convention_hint_index=(
                                sender_probe_convention_hint_index
                            ),
                            receiver_convention_knowledge=(
                                sender_probe_receiver_knowledge
                            ),
                        )
                    )
                    sender_intervention_instruction_hash = _hash_text(
                        intervention_instruction
                    )
                    sender_intervention_seed = (
                        sender_intervention_seed_offset + sender_seed
                    )
                    intervention_spec = _agent_spec_for_sample(
                        sender_spec_base,
                        sample_seed=sender_intervention_seed,
                        vary_api_seed=vary_api_seed,
                    )
                    intervention_agent = _build_agent(
                        intervention_spec,
                        seed=sender_intervention_seed,
                    )
                    if not isinstance(
                        intervention_agent,
                        OpenAICompatibleAgent,
                    ):
                        raise RuntimeError(
                            "sender self-derived intervention requires "
                            "OpenAICompatibleAgent"
                        )
                    sender_intervention_request_payload_hash = _payload_hash(
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
                    (
                        sender_intervention_action,
                        _,
                    ) = _resolve_agent_decision(
                        intervention_decision,
                        error_policy=error_policy,
                        observation=scenario.sender_observation,
                        legal_actions=sender_actions,
                    )
                    sender_intervention_error = intervention_decision.parse_error
                    sender_intervention_raw_response = (
                        intervention_decision.raw_response
                    )
                    sender_intervention_response_channel = (
                        intervention_decision.response_channel
                    )
                    sender_intervention_api_response = (
                        intervention_decision.api_response
                    )
                    sender_intervention_model_action_index = (
                        intervention_decision.action_index
                    )
                    sender_intervention_valid = (
                        sender_intervention_action is not None
                        and intervention_decision.parse_error is None
                    )
                    if sender_intervention_action is not None:
                        sender_intervention_hint_label = _hint_label(
                            sender_intervention_action
                        )
                        sender_intervention_used_convention_hint = (
                            sender_intervention_action
                            == scenario.convention_trigger_hint
                        )
                        sender_intervention_used_robust_hint = (
                            scenario.robust_hint is not None
                            and sender_intervention_action
                            == scenario.robust_hint
                        )
                        sender_intervention_epistemic_choice_correct = (
                            sender_intervention_action == expected_sender_hint
                            if expected_sender_hint is not None
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
                    "sender_intervention_action": (
                        sender_intervention_action.to_dict()
                        if sender_intervention_action is not None
                        else None
                    ),
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
                "sender_intervention_action": (
                    sender_intervention_action.to_dict()
                    if sender_intervention_action is not None
                    else None
                ),
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

    sender_convention_pairwise = _all_pairwise_comparisons(
        all_samples,
        conditions,
        field="sender_used_convention_hint",
        valid_field="valid",
    )
    sender_epistemic_choice_pairwise = (
        _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="sender_epistemic_choice_correct",
            valid_field="valid",
        )
        if scenario.epistemic_reliance_test
        else {}
    )
    receiver_pairwise = (
        {}
        if sender_only
        else _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="receiver_selected_newest",
            valid_field="valid",
        )
    )
    safe_coordination_pairwise = (
        {}
        if sender_only
        else _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="safe_coordination_success",
            valid_field="valid",
        )
    )
    convention_chain_pairwise = (
        {}
        if sender_only
        else _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="convention_chain_success",
            valid_field="valid",
        )
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
    sender_mechanical_probe_exact_pairwise = (
        _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="sender_mechanical_probe_exact_correct",
            valid_field="sender_mechanical_probe_valid",
        )
        if sender_mechanical_probe
        else {}
    )
    sender_mechanical_probe_request_hash_pairwise = (
        _all_pairwise_hash_comparisons(
            all_samples,
            conditions,
            field="sender_mechanical_probe_request_payload_hash",
            valid_field="sender_mechanical_probe_valid",
        )
        if sender_mechanical_probe
        else {}
    )
    sender_intervention_convention_pairwise = (
        _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="sender_intervention_used_convention_hint",
            valid_field="sender_intervention_valid",
        )
        if sender_self_derived_intervention
        else {}
    )
    sender_intervention_choice_pairwise = (
        _all_pairwise_comparisons(
            all_samples,
            conditions,
            field="sender_intervention_epistemic_choice_correct",
            valid_field="sender_intervention_valid",
        )
        if sender_self_derived_intervention
        else {}
    )
    sender_request_hash_pairwise = _all_pairwise_hash_comparisons(
        all_samples,
        conditions,
        field="sender_request_payload_hash",
        valid_field="valid",
    )
    receiver_request_hash_pairwise = (
        {}
        if sender_only
        else _all_pairwise_hash_comparisons(
            all_samples,
            conditions,
            field="receiver_request_payload_hash",
            valid_field="valid",
        )
    )
    baseline = "ck0" if "ck0" in conditions else conditions[0]
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
        "sender_intervention_seed_offset": sender_intervention_seed_offset,
        "aggregate_by_condition": aggregate_by_condition,
        "paired_sender_convention_hint_comparisons": sender_convention_pairwise,
        "paired_sender_convention_hint_vs_baseline": _comparisons_vs_baseline(
            sender_convention_pairwise,
            baseline,
        ),
        "paired_sender_epistemic_choice_comparisons": (
            sender_epistemic_choice_pairwise
        ),
        "paired_receiver_comparisons": receiver_pairwise,
        "paired_receiver_vs_baseline": (
            _comparisons_vs_baseline(receiver_pairwise, baseline)
            if receiver_pairwise
            else {}
        ),
        "paired_safe_coordination_comparisons": (
            safe_coordination_pairwise
        ),
        "paired_safe_coordination_vs_baseline": (
            _comparisons_vs_baseline(safe_coordination_pairwise, baseline)
            if safe_coordination_pairwise
            else {}
        ),
        "paired_convention_chain_comparisons": convention_chain_pairwise,
        "paired_convention_chain_vs_baseline": (
            _comparisons_vs_baseline(convention_chain_pairwise, baseline)
            if convention_chain_pairwise
            else {}
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
        "paired_sender_mechanical_probe_exact_comparisons": (
            sender_mechanical_probe_exact_pairwise
        ),
        "paired_sender_mechanical_probe_request_hash_comparisons": (
            sender_mechanical_probe_request_hash_pairwise
        ),
        "paired_sender_intervention_convention_hint_comparisons": (
            sender_intervention_convention_pairwise
        ),
        "paired_sender_intervention_epistemic_choice_comparisons": (
            sender_intervention_choice_pairwise
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
