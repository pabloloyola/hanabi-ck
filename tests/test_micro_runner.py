from hanabi_ck.actions import Action
from hanabi_ck.micro_runner import (
    _agent_spec_for_sample,
    _all_pairwise_hash_comparisons,
    _ordered_actions,
    _paired_binary_comparison,
    _payload_hash,
    _wilson_interval,
    aggregate_micro_samples,
    run_micro_experiment,
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


def test_run_micro_experiment_with_simple_agent(tmp_path):
    config = tmp_path / "micro.yaml"
    config.write_text(
        "\n".join(
            [
                "experiment: micro_test",
                f"output_dir: {tmp_path.as_posix()}",
                "scenario: newest_rank1_three_safe",
                "conditions: [ck0, ck_inf_common]",
                "repetitions: 2",
                "shuffle_legal_actions: true",
                "action_order_seed: 7",
                "ck1_informed_players: [1]",
                "agent:",
                "  type: simple",
                "  name: baseline",
                "agent_error_policy: abort",
                "log_raw_model_responses: false",
            ]
        ),
        encoding="utf-8",
    )

    summary = run_micro_experiment(config)

    assert summary["repetitions"] == 2
    for condition in ("ck0", "ck_inf_common"):
        aggregate = summary["aggregate_by_condition"][condition]
        assert aggregate["n_samples"] == 2
        assert aggregate["n_valid_samples"] == 2
        assert aggregate["n_error_samples"] == 0

        log_path = (
            tmp_path
            / "micro_test"
            / "micro"
            / "newest_rank1_three_safe"
            / f"{condition}.jsonl"
        )
        assert log_path.exists()
        assert len(log_path.read_text(encoding="utf-8").splitlines()) == 2


def test_wilson_interval_contains_observed_rate():
    interval = _wilson_interval(6, 20)

    assert interval is not None
    assert interval[0] < 0.3 < interval[1]
    assert 0.0 <= interval[0] <= interval[1] <= 1.0


def test_paired_comparison_counts_directional_switches():
    left = [
        {"repetition": 0, "valid": True, "selected_newest_target": False},
        {"repetition": 1, "valid": True, "selected_newest_target": True},
        {"repetition": 2, "valid": True, "selected_newest_target": False},
        {"repetition": 3, "valid": True, "selected_newest_target": False},
    ]
    right = [
        {"repetition": 0, "valid": True, "selected_newest_target": True},
        {"repetition": 1, "valid": True, "selected_newest_target": True},
        {"repetition": 2, "valid": True, "selected_newest_target": False},
        {"repetition": 3, "valid": True, "selected_newest_target": True},
    ]

    result = _paired_binary_comparison(
        left,
        right,
        field="selected_newest_target",
        valid_field="valid",
        left_condition="ck0",
        right_condition="ck3_mutual",
    )

    assert result["n_paired"] == 4
    assert result["both_positive"] == 1
    assert result["neither_positive"] == 1
    assert result["left_only"] == 0
    assert result["right_only"] == 2
    assert result["delta_right_minus_left"] == 0.5


def test_micro_aggregation_includes_shadow_probe_recognition_behavior():
    samples = [
        {
            "valid": True,
            "agent_error": False,
            "selected_action": Action.play(4).to_dict(),
            "selected_card_index": 4,
            "selected_newest_target": True,
            "selected_safe_candidate_play": True,
            "selected_epistemically_safe_play": True,
            "probe_enabled": True,
            "probe_valid": True,
            "probe_inferred_newest_target": True,
            "probe_intended_card_index": 4,
        },
        {
            "valid": True,
            "agent_error": False,
            "selected_action": Action.play(1).to_dict(),
            "selected_card_index": 1,
            "selected_newest_target": False,
            "selected_safe_candidate_play": True,
            "selected_epistemically_safe_play": True,
            "probe_enabled": True,
            "probe_valid": True,
            "probe_inferred_newest_target": True,
            "probe_intended_card_index": 4,
        },
    ]

    result = aggregate_micro_samples(samples)

    assert result["probe_valid_count"] == 2
    assert result["probe_newest_rate"] == 1.0
    assert result["action_matches_probe_rate"] == 0.5
    assert result["coindexed_action_newest_when_probe_newest_rate"] == 0.5
    assert result["recognition_behavior_gap"] == 0.5
    assert result["recognition_behavior_table"] == {
        "both_newest": 1,
        "probe_newest_action_not": 1,
        "action_newest_probe_not": 0,
        "neither_newest": 0,
    }


def test_payload_hash_is_stable_for_key_order():
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}

    assert _payload_hash(left) == _payload_hash(right)


def test_pairwise_hash_comparison_detects_identical_requests():
    samples = [
        {
            "condition": "ck1_private",
            "repetition": 0,
            "valid": True,
            "request_payload_hash": "same",
        },
        {
            "condition": "ck2_shared",
            "repetition": 0,
            "valid": True,
            "request_payload_hash": "same",
        },
        {
            "condition": "ck1_private",
            "repetition": 1,
            "valid": True,
            "request_payload_hash": "left",
        },
        {
            "condition": "ck2_shared",
            "repetition": 1,
            "valid": True,
            "request_payload_hash": "right",
        },
    ]

    result = _all_pairwise_hash_comparisons(
        samples,
        ["ck1_private", "ck2_shared"],
        field="request_payload_hash",
        valid_field="valid",
    )["ck1_private__vs__ck2_shared"]

    assert result["n_paired"] == 2
    assert result["hash_match_count"] == 1
    assert result["hash_match_rate"] == 0.5
