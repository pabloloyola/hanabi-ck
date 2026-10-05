from hanabi_ck.actions import Action
from hanabi_ck.pair_micro_runner import (
    _expected_receiver_convention_knowledge,
    aggregate_pair_samples,
)


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
