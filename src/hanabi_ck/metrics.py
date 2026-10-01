from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any


def summarize_game(turns: list[dict[str, Any]], final_state: dict[str, Any]) -> dict[str, Any]:
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
    fallbacks = sum(1 for t in turns if t["agent"].get("fallback_used"))
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
        "successful_plays_per_hint": successful_plays / hints if hints else None,
        "fallback_count": fallbacks,
        "fallback_rate": fallbacks / len(turns) if turns else 0.0,
    }


def aggregate_games(games: list[dict[str, Any]]) -> dict[str, Any]:
    if not games:
        return {"n_games": 0}
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
    out: dict[str, Any] = {
        "n_games": len(games),
        "perfect_rate": mean(float(g["perfect"]) for g in games),
        "failure_rate": mean(float(g["failed"]) for g in games),
    }
    for k in numeric:
        out[f"mean_{k}"] = mean(float(g[k]) for g in games)
    vals = [g["successful_plays_per_hint"] for g in games if g["successful_plays_per_hint"] is not None]
    out["mean_successful_plays_per_hint"] = mean(vals) if vals else None
    return out
