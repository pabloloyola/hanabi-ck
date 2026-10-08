"""Aggregation and paired summaries for sender/receiver micro experiments.

This module is intentionally free of API calls and game execution so result
analysis can evolve independently from experiment orchestration.
"""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from .micro_runner import _wilson_interval
from .pair_interventions import INTERVENTION_ARMS


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
            "sender_intervention_by_arm": {},
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

    intervention_by_arm: dict[str, Any] = {}
    observed_arms = [
        arm
        for arm in INTERVENTION_ARMS
        if any(
            arm in (sample.get("sender_interventions") or {})
            for sample in valid
        )
    ]
    for arm in observed_arms:
        enabled_arm = [
            sample for sample in valid
            if arm in (sample.get("sender_interventions") or {})
        ]
        valid_arm = [
            sample for sample in enabled_arm
            if sample["sender_interventions"][arm].get("valid") is True
        ]
        convention_count = sum(
            bool(
                sample["sender_interventions"][arm].get(
                    "used_convention_hint"
                )
            )
            for sample in valid_arm
        )
        request_hash_match_count = sum(
            sample.get("sender_request_payload_hash")
            == sample["sender_interventions"][arm].get(
                "request_payload_hash"
            )
            for sample in valid_arm
        )
        choice_arm = [
            sample for sample in valid_arm
            if sample["sender_interventions"][arm].get(
                "epistemic_choice_correct"
            ) is not None
        ]
        choice_correct_count = sum(
            bool(
                sample["sender_interventions"][arm].get(
                    "epistemic_choice_correct"
                )
            )
            for sample in choice_arm
        )
        transitions: Counter[str] = Counter()
        for sample in choice_arm:
            baseline_correct = (
                sample.get("sender_epistemic_choice_correct") is True
            )
            arm_correct = (
                sample["sender_interventions"][arm].get(
                    "epistemic_choice_correct"
                )
                is True
            )
            transitions[
                (
                    "baseline_correct_intervention_correct"
                    if baseline_correct and arm_correct
                    else "baseline_correct_intervention_wrong"
                    if baseline_correct
                    else "baseline_wrong_intervention_correct"
                    if arm_correct
                    else "baseline_wrong_intervention_wrong"
                )
            ] += 1

        baseline_wrong_arm = [
            sample for sample in choice_arm
            if sample.get("sender_epistemic_choice_correct") is False
        ]
        rescued_arm = sum(
            sample["sender_interventions"][arm].get(
                "epistemic_choice_correct"
            )
            is True
            for sample in baseline_wrong_arm
        )
        joint_correct_baseline_wrong_arm = [
            sample for sample in choice_arm
            if sample.get("sender_joint_mechanics_epistemics_correct") is True
            and sample.get("sender_epistemic_choice_correct") is False
        ]
        joint_rescued_arm = sum(
            sample["sender_interventions"][arm].get(
                "epistemic_choice_correct"
            )
            is True
            for sample in joint_correct_baseline_wrong_arm
        )

        intervention_by_arm[arm] = {
            "n_enabled": len(enabled_arm),
            "n_valid": len(valid_arm),
            "n_error": len(enabled_arm) - len(valid_arm),
            "convention_hint_count": convention_count,
            "convention_hint_rate": (
                convention_count / len(valid_arm)
                if valid_arm
                else None
            ),
            "request_hash_matches_baseline_count": request_hash_match_count,
            "request_hash_matches_baseline_rate": (
                request_hash_match_count / len(valid_arm)
                if valid_arm
                else None
            ),
            "epistemic_choice_correct_count": (
                choice_correct_count if choice_arm else None
            ),
            "epistemic_choice_accuracy": (
                choice_correct_count / len(choice_arm)
                if choice_arm
                else None
            ),
            "baseline_intervention_choice_transition_counts": dict(
                sorted(transitions.items())
            ),
            "baseline_wrong_intervention_rescue_rate": (
                rescued_arm / len(baseline_wrong_arm)
                if baseline_wrong_arm
                else None
            ),
            "joint_correct_baseline_wrong_intervention_rescue_rate": (
                joint_rescued_arm / len(joint_correct_baseline_wrong_arm)
                if joint_correct_baseline_wrong_arm
                else None
            ),
        }

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
        "sender_intervention_by_arm": intervention_by_arm,
    }
