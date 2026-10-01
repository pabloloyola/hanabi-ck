from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any


def summarize_game(
    turns: list[dict[str, Any]],
    final_state: dict[str, Any],
) -> dict[str, Any]:
    counts = Counter(t["action"]["type"] for t in turns)
    misplays = sum(
        1
        for t in turns
        if t["action"]["type"] == "play"
        and t["outcome"].get("play_success") is False
    )
    successful_plays = sum(
        1
        for t in turns
        if t["action"]["type"] == "play"
        and t["outcome"].get("play_success") is True
    )
    fallbacks = sum(
        1 for t in turns if t["agent"].get("fallback_used")
    )
    hints = counts["hint"]

    return {
        "score": final_state["score"],
        "perfect": final_state["score"] == 25,
        "failed": final_state["life_tokens"] <= 0,
        "turns": len(turns),
        "plays": counts["play"],
        "successful_plays": successful_plays,
        "misplays": misplays,
        "discards": counts["discard"],
        "hints": hints,
        "successful_plays_per_hint": (
            successful_plays / hints if hints else None
        ),
        "fallback_count": fallbacks,
        "fallback_rate": (
            fallbacks / len(turns) if turns else 0.0
        ),
    }


def aggregate_games(games: list[dict[str, Any]]) -> dict[str, Any]:
    if not games:
        return {
            "n_games": 0,
            "n_valid_games": 0,
            "n_aborted_games": 0,
        }

    valid = [g for g in games if g.get("valid", True)]
    out: dict[str, Any] = {
        "n_games": len(games),
        "n_valid_games": len(valid),
        "n_aborted_games": len(games) - len(valid),
        "agent_error_count": sum(
            int(g.get("agent_error_count", 0))
            for g in games
        ),
    }

    if not valid:
        out.update(
            {
                "perfect_rate": None,
                "failure_rate": None,
                "mean_score": None,
                "mean_turns": None,
                "mean_plays": None,
                "mean_successful_plays": None,
                "mean_misplays": None,
                "mean_discards": None,
                "mean_hints": None,
                "mean_fallback_count": None,
                "mean_fallback_rate": None,
                "mean_successful_plays_per_hint": None,
            }
        )
        return out

    numeric = [
        "score",
        "turns",
        "plays",
        "successful_plays",
        "misplays",
        "discards",
        "hints",
        "fallback_count",
        "fallback_rate",
    ]
    out.update(
        {
            "perfect_rate": mean(
                float(g["perfect"]) for g in valid
            ),
            "failure_rate": mean(
                float(g["failed"]) for g in valid
            ),
        }
    )
    for key in numeric:
        out[f"mean_{key}"] = mean(
            float(g[key]) for g in valid
        )

    vals = [
        g["successful_plays_per_hint"]
        for g in valid
        if g["successful_plays_per_hint"] is not None
    ]
    out["mean_successful_plays_per_hint"] = (
        mean(vals) if vals else None
    )
    return out
