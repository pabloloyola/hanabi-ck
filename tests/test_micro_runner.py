from hanabi_ck.actions import Action
from hanabi_ck.micro_runner import (
    _agent_spec_for_sample,
    _ordered_actions,
    aggregate_micro_samples,
)
from hanabi_ck.micro_scenarios import get_micro_scenario


def _sample(action, *, newest, candidate, safe, valid=True, error=False):
    return {
        "valid": valid,
        "agent_error": error,
        "selected_action": action.to_dict() if action is not None else None,
        "selected_newest_target": newest,
        "selected_safe_candidate_play": candidate,
        "selected_epistemically_safe_play": safe,
    }


def test_micro_aggregation_reports_newest_selection_rate():
    samples = [
        _sample(Action.play(4), newest=True, candidate=True, safe=True),
        _sample(Action.play(1), newest=False, candidate=True, safe=True),
        _sample(Action.discard(0), newest=False, candidate=False, safe=None),
    ]

    result = aggregate_micro_samples(samples)

    assert result["n_valid_samples"] == 3
    assert result["newest_selection_count"] == 1
    assert result["newest_selection_rate"] == 1 / 3
    assert result["newest_given_safe_candidate_play_rate"] == 0.5
    assert result["play_rate"] == 2 / 3
    assert result["epistemically_safe_play_rate"] == 1.0


def test_micro_action_order_is_paired_by_repetition():
    scenario = get_micro_scenario("newest_rank1_three_safe")

    a = _ordered_actions(
        scenario,
        repetition=3,
        shuffle=True,
        action_order_seed=123,
    )
    b = _ordered_actions(
        scenario,
        repetition=3,
        shuffle=True,
        action_order_seed=123,
    )

    assert a == b
    assert set(a) == set(scenario.legal_actions)
    assert scenario.target_action in a


def test_micro_sample_seed_overrides_only_api_seed():
    spec = {
        "type": "openai_compatible",
        "model": "m",
        "extra_body": {
            "seed": 999,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    }

    sampled = _agent_spec_for_sample(
        spec,
        sample_seed=7,
        vary_api_seed=True,
    )

    assert sampled["extra_body"]["seed"] == 7
    assert sampled["extra_body"]["chat_template_kwargs"] == {
        "enable_thinking": False
    }
    assert spec["extra_body"]["seed"] == 999
