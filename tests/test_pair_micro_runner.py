from hanabi_ck.actions import Action
from hanabi_ck.pair_micro_runner import aggregate_pair_samples


def _sample(
    *,
    sender_trigger: bool,
    receiver_index: int,
    receiver_safe: bool,
    safe_success: bool,
    chain_success: bool,
):
    return {
        "valid": True,
        "sender_used_convention_hint": sender_trigger,
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
    assert result["receiver_newest_given_convention_hint_rate"] == 0.5
