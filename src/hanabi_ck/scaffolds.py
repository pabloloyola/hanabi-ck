from __future__ import annotations

from typing import Any

from .observations import PlayerObservation


MECHANICAL_SCAFFOLDS = {"raw", "derived"}


def normalize_mechanical_scaffold(name: str | None) -> str:
    normalized = (name or "derived").strip().lower()
    if normalized not in MECHANICAL_SCAFFOLDS:
        raise ValueError(
            "mechanical_scaffold must be one of "
            f"{sorted(MECHANICAL_SCAFFOLDS)}"
        )
    return normalized


def render_observation(
    observation: PlayerObservation,
    scaffold: str = "derived",
) -> dict[str, Any]:
    """Render the player-visible observation for an LLM scaffold.

    derived preserves the historical hanabi-ck prompt exactly: in addition
    to hint-derived card constraints it includes deterministic safety summaries.

    raw keeps the backend-normalized Hanabi observation and hint-derived card
    constraints, but removes hanabi-ck's synthetic playability/obsolescence
    summaries. The model must derive those consequences itself.

    Neither mode exposes hidden cards from the acting player's own hand.
    """
    scaffold = normalize_mechanical_scaffold(scaffold)
    data = observation.to_dict()

    if scaffold == "raw":
        data.pop("provably_playable_indices", None)
        data.pop("provably_obsolete_indices", None)
        data.pop("play_safety", None)

    return data


def render_hint_effects(
    effects: list[dict[str, Any]],
    scaffold: str = "derived",
) -> list[dict[str, Any]]:
    """Render sender-side mechanical hint annotations.

    The derived scaffold keeps touched-card and post-hint safety annotations.
    The raw scaffold exposes only the indexed legal hint itself, requiring the
    model to infer its mechanical effect from the visible receiver hand.
    """
    scaffold = normalize_mechanical_scaffold(scaffold)
    if scaffold == "derived":
        return [dict(effect) for effect in effects]

    return [
        {
            "action_index": effect["action_index"],
            "action": dict(effect["action"]),
        }
        for effect in effects
    ]
