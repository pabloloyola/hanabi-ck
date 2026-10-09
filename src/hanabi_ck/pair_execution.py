"""Execute shadow probes and intervention arms for pair micro experiments.

The orchestrator controls when each helper is called and the execution order.
These helpers preserve the request payloads and normalized diagnostic results.
"""
from __future__ import annotations

from typing import Any, NamedTuple

from .actions import Action
from .agents import OpenAICompatibleAgent
from .micro_runner import _agent_spec_for_sample, _payload_hash
from .micro_scenarios import PairMicroScenario
from .pair_interventions import _self_derived_intervention_instruction
from .runner import _build_agent, _hash_text, _resolve_agent_decision


def _hint_label(action: Action) -> str:
    if action.type != "hint":
        return action.type
    return f"{action.attribute}={action.value}"


class MechanicalProbeResult(NamedTuple):
    sender_mechanical_probe_seed: int | None
    sender_mechanical_probe_request_hash: str | None
    sender_mechanical_probe_valid: bool
    sender_mechanical_probe_error: str | None
    sender_mechanical_probe_effects: list[dict[str, Any]] | None
    sender_mechanical_probe_exact_correct: bool | None
    sender_mechanical_probe_robust_effect_correct: bool | None
    sender_mechanical_probe_convention_effect_correct: bool | None
    sender_mechanical_probe_raw_response: str | None
    sender_mechanical_probe_response_channel: str | None
    sender_mechanical_probe_api_response: dict[str, Any] | None


class EpistemicProbeResult(NamedTuple):
    sender_probe_seed: int | None
    sender_probe_request_hash: str | None
    sender_probe_valid: bool
    sender_probe_error: str | None
    sender_probe_convention_hint_index: int | None
    sender_probe_receiver_knowledge: str | None
    sender_probe_raw_response: str | None
    sender_probe_response_channel: str | None
    sender_probe_api_response: dict[str, Any] | None


def _run_sender_intervention_arm(
    *,
    intervention_arm: str,
    sender_mechanical_probe_valid: bool,
    sender_probe_valid: bool,
    sender_instruction: str,
    sender_mechanical_probe_effects: list[dict[str, Any]] | None,
    sender_probe_convention_hint_index: int | None,
    sender_probe_receiver_knowledge: str | None,
    sender_intervention_seed_offset: int,
    arm_seed_slot: dict[str, int],
    sender_seed: int,
    sender_spec_base: dict[str, Any],
    vary_api_seed: bool,
    scenario: PairMicroScenario,
    sender_actions: list[Action],
    error_policy: str,
    expected_sender_hint: Action | None,
) -> dict[str, Any]:
    """Execute one arm; the caller owns deterministic execution order."""
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

    return arm_result


def _run_sender_mechanical_probe(
    *,
    sender_mechanical_probe: bool,
    sender_mechanical_probe_seed_offset: int,
    sender_seed: int,
    sender_spec_base: dict[str, Any],
    vary_api_seed: bool,
    scenario: PairMicroScenario,
    mechanical_probe_candidates: list[dict[str, Any]],
    mechanical_probe_expected_effects: list[dict[str, Any]],
    robust_hint_index: int | None,
    sender_convention_hint_index: int,
) -> MechanicalProbeResult:
    """Run an optional mechanical shadow probe and normalize its result."""
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

    return MechanicalProbeResult(
        sender_mechanical_probe_seed,
        sender_mechanical_probe_request_hash,
        sender_mechanical_probe_valid,
        sender_mechanical_probe_error,
        sender_mechanical_probe_effects,
        sender_mechanical_probe_exact_correct,
        sender_mechanical_probe_robust_effect_correct,
        sender_mechanical_probe_convention_effect_correct,
        sender_mechanical_probe_raw_response,
        sender_mechanical_probe_response_channel,
        sender_mechanical_probe_api_response,
    )


def _run_sender_epistemic_probe(
    *,
    sender_probe: bool,
    sender_probe_seed_offset: int,
    sender_seed: int,
    sender_spec_base: dict[str, Any],
    vary_api_seed: bool,
    scenario: PairMicroScenario,
    sender_condition_instruction: str,
    sender_hint_effects_for_prompt: list[dict[str, Any]],
) -> EpistemicProbeResult:
    """Run an optional epistemic shadow probe and normalize its result."""
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

    return EpistemicProbeResult(
        sender_probe_seed,
        sender_probe_request_hash,
        sender_probe_valid,
        sender_probe_error,
        sender_probe_convention_hint_index,
        sender_probe_receiver_knowledge,
        sender_probe_raw_response,
        sender_probe_response_channel,
        sender_probe_api_response,
    )

