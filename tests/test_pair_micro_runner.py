from hanabi_ck.actions import Action
from hanabi_ck.pair_analysis import (
    aggregate_pair_samples,
    build_pairwise_metrics,
)
from hanabi_ck.pair_interventions import _self_derived_intervention_instruction
from hanabi_ck.pair_micro_runner import _expected_receiver_convention_knowledge


def _sample(
    *,
    sender_trigger: bool,
    receiver_index: int,
    receiver_safe: bool,
    safe_success: bool,
    chain_success: bool,
    sender_hint_label: str | None = None,
):
    return {
        "valid": True,
        "sender_used_convention_hint": sender_trigger,
        "sender_hint_label": (
            sender_hint_label
            if sender_hint_label is not None
            else ("rank=1" if sender_trigger else "rank=2")
        ),
        "receiver_selected_newest": receiver_index == 4,
        "receiver_action": Action.play(receiver_index).to_dict(),
        "receiver_epistemically_safe_play": receiver_safe,
        "safe_coordination_success": safe_success,
        "convention_chain_success": chain_success,
    }


def test_pair_aggregation_distinguishes_newest_from_safe_coordination():
    samples = [
        _sample(
            sender_trigger=True,
            receiver_index=4,
            receiver_safe=True,
            safe_success=True,
            chain_success=True,
        ),
        _sample(
            sender_trigger=False,
            receiver_index=4,
            receiver_safe=False,
            safe_success=False,
            chain_success=False,
        ),
        _sample(
            sender_trigger=True,
            receiver_index=1,
            receiver_safe=True,
            safe_success=False,
            chain_success=False,
        ),
    ]

    result = aggregate_pair_samples(samples)

    assert result["receiver_newest_rate"] == 2 / 3
    assert result["safe_coordination_success_rate"] == 1 / 3
    assert result["convention_chain_success_rate"] == 1 / 3
    assert result["sender_convention_hint_rate"] == 2 / 3
    assert result["sender_hint_counts"] == {"rank=1": 2, "rank=2": 1}
    assert result["receiver_newest_given_convention_hint_rate"] == 0.5


def test_sender_probe_epistemic_expectations_follow_ck_ladder():
    assert _expected_receiver_convention_knowledge("ck0") == "no_convention"
    assert _expected_receiver_convention_knowledge("ck1_private") == "unknown"
    assert _expected_receiver_convention_knowledge("ck2_shared") == "unknown"
    assert _expected_receiver_convention_knowledge("ck3_mutual") == "known"
    assert _expected_receiver_convention_knowledge("ck_inf_common") == "known"


def test_pair_aggregation_separates_probe_knowledge_from_action():
    samples = [
        {
            **_sample(
                sender_trigger=False,
                receiver_index=1,
                receiver_safe=True,
                safe_success=False,
                chain_success=False,
                sender_hint_label="color=B",
            ),
            "sender_model_action_index": 2,
            "sender_probe_enabled": True,
            "sender_probe_valid": True,
            "sender_probe_convention_hint_index": 6,
            "sender_probe_identified_convention_hint": True,
            "sender_probe_mapping_correct": True,
            "sender_probe_receiver_convention_knowledge": "known",
            "sender_probe_partner_knowledge_correct": True,
        },
        {
            **_sample(
                sender_trigger=True,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=True,
            ),
            "sender_model_action_index": 6,
            "sender_probe_enabled": True,
            "sender_probe_valid": True,
            "sender_probe_convention_hint_index": 6,
            "sender_probe_identified_convention_hint": True,
            "sender_probe_mapping_correct": True,
            "sender_probe_receiver_convention_knowledge": "known",
            "sender_probe_partner_knowledge_correct": True,
        },
    ]

    result = aggregate_pair_samples(samples)

    assert result["sender_convention_hint_rate"] == 0.5
    assert result["sender_probe_identified_convention_hint_rate"] == 1.0
    assert result["sender_probe_mapping_accuracy"] == 1.0
    assert result["sender_probe_partner_knowledge_accuracy"] == 1.0
    assert result["sender_probe_knowledge_to_action_gap"] == 0.5
    assert result["sender_action_matches_probe_hint_rate"] == 0.5
    assert result["sender_probe_partner_knowledge_counts"] == {"known": 2}



def test_pair_aggregation_reports_epistemic_reliance_choice():
    samples = [
        {
            **_sample(
                sender_trigger=False,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=False,
                sender_hint_label="rank=1",
            ),
            "sender_used_robust_hint": True,
            "sender_epistemic_choice_correct": True,
        },
        {
            **_sample(
                sender_trigger=True,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=True,
                sender_hint_label="rank=2",
            ),
            "sender_used_robust_hint": False,
            "sender_epistemic_choice_correct": True,
        },
    ]

    result = aggregate_pair_samples(samples)

    assert result["sender_convention_hint_rate"] == 0.5
    assert result["sender_robust_hint_rate"] == 0.5
    assert result["sender_epistemic_choice_accuracy"] == 1.0



def test_pair_aggregation_supports_sender_only_samples():
    samples = [
        {
            "valid": True,
            "sender_only": True,
            "sender_used_convention_hint": False,
            "sender_used_robust_hint": True,
            "sender_epistemic_choice_correct": True,
            "sender_hint_label": "rank=1",
            "receiver_action": None,
        },
        {
            "valid": True,
            "sender_only": True,
            "sender_used_convention_hint": True,
            "sender_used_robust_hint": False,
            "sender_epistemic_choice_correct": True,
            "sender_hint_label": "rank=2",
            "receiver_action": None,
        },
    ]

    result = aggregate_pair_samples(samples)

    assert result["sender_convention_hint_rate"] == 0.5
    assert result["sender_robust_hint_rate"] == 0.5
    assert result["sender_epistemic_choice_accuracy"] == 1.0
    assert result["receiver_newest_rate"] is None
    assert result["safe_coordination_success_rate"] is None
    assert result["convention_chain_success_rate"] is None


def test_pair_aggregation_separates_mechanical_reasoning_from_policy():
    samples = [
        {
            **_sample(
                sender_trigger=True,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=True,
                sender_hint_label="rank=2",
            ),
            "sender_used_robust_hint": False,
            "sender_epistemic_choice_correct": False,
            "sender_mechanical_probe_enabled": True,
            "sender_mechanical_probe_valid": True,
            "sender_mechanical_probe_exact_correct": True,
            "sender_mechanical_probe_robust_effect_correct": True,
            "sender_mechanical_probe_convention_effect_correct": True,
        },
        {
            **_sample(
                sender_trigger=False,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=False,
                sender_hint_label="rank=1",
            ),
            "sender_used_robust_hint": True,
            "sender_epistemic_choice_correct": True,
            "sender_mechanical_probe_enabled": True,
            "sender_mechanical_probe_valid": True,
            "sender_mechanical_probe_exact_correct": False,
            "sender_mechanical_probe_robust_effect_correct": True,
            "sender_mechanical_probe_convention_effect_correct": False,
        },
    ]

    result = aggregate_pair_samples(samples)

    assert result["sender_mechanical_probe_valid_count"] == 2
    assert result["sender_mechanical_probe_error_count"] == 0
    assert result["sender_mechanical_probe_exact_accuracy"] == 0.5
    assert result["sender_mechanical_probe_robust_effect_accuracy"] == 1.0
    assert result["sender_mechanical_probe_convention_effect_accuracy"] == 0.5
    assert result["sender_choice_accuracy_given_exact_mechanics"] == 0.0
    assert result["sender_mechanics_correct_but_choice_wrong_rate"] == 1.0



def test_pair_aggregation_classifies_joint_probe_policy_failures():
    samples = [
        {
            **_sample(
                sender_trigger=True,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=True,
                sender_hint_label="rank=2",
            ),
            "sender_used_robust_hint": False,
            "sender_epistemic_choice_correct": False,
            "sender_probe_enabled": True,
            "sender_probe_valid": True,
            "sender_probe_mapping_correct": True,
            "sender_probe_partner_knowledge_correct": True,
            "sender_mechanical_probe_enabled": True,
            "sender_mechanical_probe_valid": True,
            "sender_mechanical_probe_exact_correct": True,
            "sender_mechanical_probe_robust_effect_correct": True,
            "sender_mechanical_probe_convention_effect_correct": True,
        },
        {
            **_sample(
                sender_trigger=False,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=False,
                sender_hint_label="rank=1",
            ),
            "sender_used_robust_hint": True,
            "sender_epistemic_choice_correct": True,
            "sender_probe_enabled": True,
            "sender_probe_valid": True,
            "sender_probe_mapping_correct": False,
            "sender_probe_partner_knowledge_correct": True,
            "sender_mechanical_probe_enabled": True,
            "sender_mechanical_probe_valid": True,
            "sender_mechanical_probe_exact_correct": True,
            "sender_mechanical_probe_robust_effect_correct": True,
            "sender_mechanical_probe_convention_effect_correct": True,
        },
        {
            **_sample(
                sender_trigger=False,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=False,
                sender_hint_label="rank=1",
            ),
            "sender_used_robust_hint": True,
            "sender_epistemic_choice_correct": True,
            "sender_probe_enabled": True,
            "sender_probe_valid": True,
            "sender_probe_mapping_correct": True,
            "sender_probe_partner_knowledge_correct": True,
            "sender_mechanical_probe_enabled": True,
            "sender_mechanical_probe_valid": True,
            "sender_mechanical_probe_exact_correct": False,
            "sender_mechanical_probe_robust_effect_correct": True,
            "sender_mechanical_probe_convention_effect_correct": False,
        },
        {
            **_sample(
                sender_trigger=False,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=False,
                sender_hint_label="rank=1",
            ),
            "sender_used_robust_hint": True,
            "sender_epistemic_choice_correct": True,
            "sender_probe_enabled": True,
            "sender_probe_valid": True,
            "sender_probe_mapping_correct": True,
            "sender_probe_partner_knowledge_correct": True,
            "sender_mechanical_probe_enabled": True,
            "sender_mechanical_probe_valid": True,
            "sender_mechanical_probe_exact_correct": True,
            "sender_mechanical_probe_robust_effect_correct": True,
            "sender_mechanical_probe_convention_effect_correct": True,
        },
    ]

    result = aggregate_pair_samples(samples)

    assert result["sender_joint_probe_valid_count"] == 4
    assert result["sender_joint_probe_error_count"] == 0
    assert result["sender_joint_mechanics_epistemics_accuracy"] == 0.5
    assert result["sender_choice_accuracy_given_joint_probe_correct"] == 0.5
    assert result["sender_both_probes_correct_but_choice_wrong_rate"] == 0.5
    assert result["sender_failure_classification_counts"] == {
        "both_probes_correct_action_correct": 1,
        "both_probes_correct_action_wrong": 1,
        "mechanics_correct_epistemics_wrong": 1,
        "mechanics_wrong": 1,
    }



def test_self_derived_intervention_instruction_uses_probe_outputs_only():
    import json

    base = "CK CONDITION\n\nDIAGNOSTIC COMMUNICATION GOAL:\nplay newest"
    mechanical = [
        {
            "action_index": 2,
            "touched_indices": [0, 3],
            "receiver_provably_playable_indices_after_hint": [4],
        },
        {
            "action_index": 7,
            "touched_indices": [1, 2, 4],
            "receiver_provably_playable_indices_after_hint": [1, 2, 4],
        },
    ]

    rendered = _self_derived_intervention_instruction(
        base,
        mechanical_effects=mechanical,
        convention_hint_index=7,
        receiver_convention_knowledge="unknown",
    )

    assert rendered.startswith(base)
    payload_text = rendered.split(
        "SELF-DERIVED FACTS FROM INDEPENDENT SHADOW PROBES:\n",
        1,
    )[1]
    payload_text = payload_text.split("\n", 1)[1]
    payload = json.loads(payload_text)
    assert payload["mechanical_hint_effects"] == mechanical
    assert payload["epistemic_facts"] == {
        "convention_hint_index": 7,
        "receiver_convention_knowledge": "unknown",
    }
    assert "expected" not in payload_text.lower()
    assert "robust_hint" not in payload_text


def test_pair_aggregation_reports_self_derived_intervention_rescue():
    samples = [
        {
            **_sample(
                sender_trigger=True,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=True,
                sender_hint_label="rank=2",
            ),
            "sender_epistemic_choice_correct": False,
            "sender_joint_mechanics_epistemics_correct": True,
            "sender_intervention_enabled": True,
            "sender_intervention_valid": True,
            "sender_intervention_used_convention_hint": False,
            "sender_intervention_epistemic_choice_correct": True,
        },
        {
            **_sample(
                sender_trigger=True,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=True,
                sender_hint_label="rank=2",
            ),
            "sender_epistemic_choice_correct": False,
            "sender_joint_mechanics_epistemics_correct": True,
            "sender_intervention_enabled": True,
            "sender_intervention_valid": True,
            "sender_intervention_used_convention_hint": True,
            "sender_intervention_epistemic_choice_correct": False,
        },
        {
            **_sample(
                sender_trigger=False,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=False,
                sender_hint_label="rank=1",
            ),
            "sender_epistemic_choice_correct": True,
            "sender_joint_mechanics_epistemics_correct": True,
            "sender_intervention_enabled": True,
            "sender_intervention_valid": True,
            "sender_intervention_used_convention_hint": False,
            "sender_intervention_epistemic_choice_correct": True,
        },
    ]

    result = aggregate_pair_samples(samples)

    assert result["sender_intervention_valid_count"] == 3
    assert result["sender_intervention_error_count"] == 0
    assert result["sender_intervention_convention_hint_rate"] == 1 / 3
    assert result["sender_intervention_epistemic_choice_accuracy"] == 2 / 3
    assert result["sender_baseline_intervention_choice_transition_counts"] == {
        "baseline_correct_intervention_correct": 1,
        "baseline_wrong_intervention_correct": 1,
        "baseline_wrong_intervention_wrong": 1,
    }
    assert result["sender_baseline_wrong_intervention_rescue_rate"] == 0.5
    assert (
        result[
            "sender_joint_correct_baseline_wrong_intervention_rescue_rate"
        ]
        == 0.5
    )



def test_intervention_instruction_factorial_arms():
    base = "BASE"
    mechanical = [
        {
            "action_index": 2,
            "touched_indices": [0, 3],
            "receiver_provably_playable_indices_after_hint": [4],
        }
    ]

    fresh = _self_derived_intervention_instruction(
        base,
        arm="fresh",
    )
    mechanical_only = _self_derived_intervention_instruction(
        base,
        arm="mechanical",
        mechanical_effects=mechanical,
    )
    epistemic_only = _self_derived_intervention_instruction(
        base,
        arm="epistemic",
        convention_hint_index=7,
        receiver_convention_knowledge="unknown",
    )
    both = _self_derived_intervention_instruction(
        base,
        arm="both",
        mechanical_effects=mechanical,
        convention_hint_index=7,
        receiver_convention_knowledge="unknown",
    )

    assert fresh == base
    assert "mechanical_hint_effects" in mechanical_only
    assert "epistemic_facts" not in mechanical_only
    assert "mechanical_hint_effects" not in epistemic_only
    assert "epistemic_facts" in epistemic_only
    assert "mechanical_hint_effects" in both
    assert "epistemic_facts" in both


def test_pair_aggregation_reports_factorial_intervention_arms():
    samples = [
        {
            **_sample(
                sender_trigger=True,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=True,
                sender_hint_label="rank=2",
            ),
            "sender_epistemic_choice_correct": False,
            "sender_joint_mechanics_epistemics_correct": True,
            "sender_interventions": {
                "fresh": {
                    "valid": True,
                    "used_convention_hint": True,
                    "epistemic_choice_correct": False,
                },
                "mechanical": {
                    "valid": True,
                    "used_convention_hint": True,
                    "epistemic_choice_correct": False,
                },
                "epistemic": {
                    "valid": True,
                    "used_convention_hint": False,
                    "epistemic_choice_correct": True,
                },
                "both": {
                    "valid": True,
                    "used_convention_hint": False,
                    "epistemic_choice_correct": True,
                },
            },
            "sender_intervention_enabled": True,
            "sender_intervention_valid": True,
            "sender_intervention_used_convention_hint": False,
            "sender_intervention_epistemic_choice_correct": True,
        },
        {
            **_sample(
                sender_trigger=False,
                receiver_index=4,
                receiver_safe=True,
                safe_success=True,
                chain_success=False,
                sender_hint_label="rank=1",
            ),
            "sender_epistemic_choice_correct": True,
            "sender_joint_mechanics_epistemics_correct": True,
            "sender_interventions": {
                "fresh": {
                    "valid": True,
                    "used_convention_hint": True,
                    "epistemic_choice_correct": False,
                },
                "mechanical": {
                    "valid": True,
                    "used_convention_hint": False,
                    "epistemic_choice_correct": True,
                },
                "epistemic": {
                    "valid": True,
                    "used_convention_hint": False,
                    "epistemic_choice_correct": True,
                },
                "both": {
                    "valid": True,
                    "used_convention_hint": False,
                    "epistemic_choice_correct": True,
                },
            },
            "sender_intervention_enabled": True,
            "sender_intervention_valid": True,
            "sender_intervention_used_convention_hint": False,
            "sender_intervention_epistemic_choice_correct": True,
        },
    ]

    result = aggregate_pair_samples(samples)
    arms = result["sender_intervention_by_arm"]

    assert arms["fresh"]["epistemic_choice_accuracy"] == 0.0
    assert arms["mechanical"]["epistemic_choice_accuracy"] == 0.5
    assert arms["epistemic"]["epistemic_choice_accuracy"] == 1.0
    assert arms["both"]["epistemic_choice_accuracy"] == 1.0
    assert arms["fresh"]["baseline_wrong_intervention_rescue_rate"] == 0.0
    assert arms["epistemic"]["baseline_wrong_intervention_rescue_rate"] == 1.0
    assert (
        arms["both"][
            "joint_correct_baseline_wrong_intervention_rescue_rate"
        ]
        == 1.0
    )



def test_pairwise_metrics_builder_preserves_condition_and_arm_comparisons():
    samples = [
        {
            "condition": "ck2_shared",
            "repetition": 0,
            "valid": True,
            "sender_used_convention_hint": True,
            "sender_epistemic_choice_correct": False,
            "sender_request_payload_hash": "ck2-action",
            "sender_probe_valid": True,
            "sender_probe_identified_convention_hint": True,
            "sender_probe_request_payload_hash": "ck2-probe",
            "sender_mechanical_probe_valid": True,
            "sender_mechanical_probe_exact_correct": True,
            "sender_mechanical_probe_request_payload_hash": "mechanical",
            "sender_intervention_valid": True,
            "sender_intervention_used_convention_hint": False,
            "sender_intervention_epistemic_choice_correct": True,
            "sender_interventions": {
                "fresh": {
                    "valid": True,
                    "used_convention_hint": True,
                    "epistemic_choice_correct": False,
                },
                "mechanical": {
                    "valid": True,
                    "used_convention_hint": False,
                    "epistemic_choice_correct": True,
                },
            },
        },
        {
            "condition": "ck3_mutual",
            "repetition": 0,
            "valid": True,
            "sender_used_convention_hint": True,
            "sender_epistemic_choice_correct": True,
            "sender_request_payload_hash": "ck3-action",
            "sender_probe_valid": True,
            "sender_probe_identified_convention_hint": True,
            "sender_probe_request_payload_hash": "ck3-probe",
            "sender_mechanical_probe_valid": True,
            "sender_mechanical_probe_exact_correct": True,
            "sender_mechanical_probe_request_payload_hash": "mechanical",
            "sender_intervention_valid": True,
            "sender_intervention_used_convention_hint": True,
            "sender_intervention_epistemic_choice_correct": True,
            "sender_interventions": {
                "fresh": {
                    "valid": True,
                    "used_convention_hint": True,
                    "epistemic_choice_correct": True,
                },
                "mechanical": {
                    "valid": True,
                    "used_convention_hint": True,
                    "epistemic_choice_correct": True,
                },
            },
        },
    ]

    result = build_pairwise_metrics(
        samples,
        ["ck2_shared", "ck3_mutual"],
        sender_only=True,
        epistemic_reliance_test=True,
        sender_probe=True,
        sender_mechanical_probe=True,
        sender_intervention_arms=["fresh", "mechanical"],
    )

    assert (
        result[
            "paired_sender_mechanical_probe_request_hash_comparisons"
        ]["ck2_shared__vs__ck3_mutual"]["hash_match_rate"]
        == 1.0
    )
    ck2_arms = result[
        "paired_sender_intervention_arm_comparisons_by_condition"
    ]["ck2_shared"]["epistemic_choice"]["fresh__vs__mechanical"]
    assert ck2_arms["left_only"] == 0
    assert ck2_arms["right_only"] == 1
