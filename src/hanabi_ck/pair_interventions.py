from __future__ import annotations

import json
from typing import Any


INTERVENTION_ARMS = ("fresh", "mechanical", "epistemic", "both")


def _self_derived_intervention_instruction(
    sender_instruction: str,
    *,
    mechanical_effects: list[dict[str, Any]] | None = None,
    convention_hint_index: int | None = None,
    receiver_convention_knowledge: str | None = None,
    arm: str = "both",
) -> str:
    """Build a fresh action prompt for one intervention ablation arm."""
    if arm not in INTERVENTION_ARMS:
        raise ValueError(
            f"Unknown intervention arm {arm!r}; expected one of "
            f"{list(INTERVENTION_ARMS)}"
        )
    if arm == "fresh":
        return sender_instruction

    self_derived: dict[str, Any] = {}
    if arm in {"mechanical", "both"}:
        if mechanical_effects is None:
            raise ValueError(f"{arm} intervention requires mechanical effects")
        self_derived["mechanical_hint_effects"] = mechanical_effects
    if arm in {"epistemic", "both"}:
        if (
            convention_hint_index is None
            or receiver_convention_knowledge is None
        ):
            raise ValueError(f"{arm} intervention requires epistemic facts")
        self_derived["epistemic_facts"] = {
            "convention_hint_index": convention_hint_index,
            "receiver_convention_knowledge": receiver_convention_knowledge,
        }

    return (
        sender_instruction
        + "\n\nSELF-DERIVED FACTS FROM INDEPENDENT SHADOW PROBES:\n"
        + "These are your own independently elicited derivations, not "
        + "researcher ground truth. Use them together with the visible Hanabi "
        + "state and the communication goal when selecting an action.\n"
        + json.dumps(self_derived, ensure_ascii=False)
    )
