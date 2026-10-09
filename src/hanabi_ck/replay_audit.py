"""Audit recordings and choose an illustrative game by a predeclared rule."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

from .replay import export_replay

METRICS = ("score", "turns", "hints", "discards", "misplays")


def audit_game(log: str | Path) -> dict[str, Any]:
    path = Path(log)
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not records or any(
        r.get("event_kind", "turn") not in {"turn", "agent_error"}
        or not isinstance(r.get("observation"), dict)
        for r in records
    ):
        raise ValueError("Expected a nonempty full-game JSONL log")
    if len({(r.get("experiment"), r.get("condition"), r.get("seed")) for r in records}) != 1:
        raise ValueError("Audit one game at a time")
    turns = [r for r in records if r.get("event_kind", "turn") == "turn"]
    counts = Counter(r.get("action", {}).get("type") for r in turns)
    checks: dict[str, bool | None] = {
        "turn_sequence": [r.get("turn") for r in records] == list(range(len(records))),
        "legal_actions": all(r.get("action") in r.get("legal_actions", []) for r in turns),
        "executed_indices": all(
            isinstance(r.get("executed_action_index"), int)
            and 0 <= r["executed_action_index"] < len(r["legal_actions"])
            and r["legal_actions"][r["executed_action_index"]] == r["action"]
            for r in turns
        ),
        "state_continuity": None,
        "observation_matches_board": None,
        "score_transitions": None,
    }
    snapshots = all(
        r.get("researcher_true_state_before") is not None
        and r.get("researcher_true_state_after") is not None
        for r in turns
    )
    if snapshots and turns:
        checks["state_continuity"] = all(
            a["researcher_true_state_after"] == b.get("researcher_true_state_before")
            for a, b in zip(records, records[1:])
            if a.get("event_kind", "turn") == "turn"
        )
        checks["observation_matches_board"] = all(
            r["observation"].get("stacks") == r["researcher_true_state_before"].get("stacks")
            and r.get("observation_after", {}).get("stacks")
            == r["researcher_true_state_after"].get("stacks")
            for r in turns
        )
        checks["score_transitions"] = all(
            r["researcher_true_state_after"]["score"] - r["researcher_true_state_before"]["score"]
            == int(
                r["action"]["type"] == "play" and r.get("outcome", {}).get("play_success") is True
            )
            for r in turns
        )
    checks["model_requests_recorded"] = all(
        r.get("agent", {}).get("type") != "openai_compatible"
        or r.get("request_payload") is not None
        for r in records
    )
    errors = sum(
        r.get("event_kind") == "agent_error" or bool(r.get("agent", {}).get("response_error"))
        for r in records
    )
    fallbacks = sum(bool(r.get("agent", {}).get("fallback_used")) for r in turns)
    complete = records[-1].get("event_kind", "turn") == "turn" and (
        records[-1].get("game_done") is True
        or bool(records[-1].get("outcome", {}).get("terminal_reason"))
    )
    final = records[-1].get("researcher_true_state_after")
    score = final.get("score") if final else None
    if score is None and complete:
        score = records[-1].get("outcome", {}).get("score_after")
    bookmarks = {
        "hint_knowledge_changes": [
            r["turn"]
            for r in turns
            if r["action"]["type"] == "hint"
            and r.get("observation_after") is not None
            and r["observation"].get("public_knowledge")
            != r["observation_after"].get("public_knowledge")
        ],
        "safe_plays": [r["turn"] for r in turns if r.get("epistemically_safe_play") is True],
        "discards": [r["turn"] for r in turns if r["action"]["type"] == "discard"],
        "misplays": [r["turn"] for r in turns if r.get("outcome", {}).get("play_success") is False],
    }
    # Compare call settings while excluding changing observations/legal-action schemas.
    settings: dict[str, list[str]] = {}
    for r in records:
        payload = r.get("request_payload")
        if payload:
            fixed = {k: v for k, v in payload.items() if k not in {"messages", "response_format"}}
            fixed["response_format_type"] = (payload.get("response_format") or {}).get("type")
            fingerprint = hashlib.sha256(json.dumps(fixed, sort_keys=True).encode()).hexdigest()
            settings.setdefault(str(r["player"]), [])
            if fingerprint not in settings[str(r["player"])]:
                settings[str(r["player"])].append(fingerprint)
    setup = {k: records[0].get(k) for k in ("condition", "backend", "mechanical_scaffold")}
    setup["players"] = sorted({r["player"] for r in records})
    setup["agent_models"] = {str(r["player"]): r.get("agent", {}).get("model") for r in records}
    setup["request_setting_hashes"] = {k: sorted(v) for k, v in settings.items()}
    instructions = {str(r["player"]): r.get("private_instruction_hash") for r in records}
    setup["instruction_hashes"] = instructions
    eligible = (
        complete and errors == 0 and fallbacks == 0 and all(v is True for v in checks.values())
    )
    return {
        "log_path": str(path),
        "seed": records[0].get("seed"),
        "setup": setup,
        "complete": complete,
        "agent_error_count": errors,
        "fallback_count": fallbacks,
        "integrity_checks": checks,
        "eligible": eligible,
        "metrics": {
            "score": score,
            "turns": len(turns),
            "hints": counts["hint"],
            "discards": counts["discard"],
            "misplays": len(bookmarks["misplays"]),
        },
        "teaching_coverage": {k: len(v) for k, v in bookmarks.items()},
        "teaching_examples": {k: v[:3] for k, v in bookmarks.items()},
        "request_recording_count": sum(r.get("request_payload") is not None for r in records),
        "interpretation": "Illustrative full game; does not establish a CK2/CK3 effect.",
    }


def audit_reference(summary_path: str | Path) -> dict[str, Any]:
    path = Path(summary_path)
    summary = json.loads(path.read_text())
    games = summary.get("games", [])
    if not games:
        raise ValueError("Expected a full-game summary containing games")
    identities = [(g.get("condition"), g.get("seed")) for g in games]
    if len(set(identities)) != len(identities):
        raise ValueError("Reference summary lists the same game more than once")
    reports = []
    for game in games:
        log = Path(game["log_path"])
        if not log.is_file():
            log = path.parent / game["condition"] / f"seed_{int(game['seed']):06d}.jsonl"
        reports.append(audit_game(log))
    eligible = [r for r in reports if r["eligible"]]
    if not eligible:
        raise ValueError("No complete, error-free, fully verified games in the reference batch")
    setups = {json.dumps(r["setup"], sort_keys=True) for r in eligible}
    if len(setups) != 1:
        raise ValueError("Eligible reference games have different settings; do not pool")
    medians = {k: median(r["metrics"][k] for r in eligible) for k in METRICS}
    ranges = {
        k: [min(r["metrics"][k] for r in eligible), max(r["metrics"][k] for r in eligible)]
        for k in METRICS
    }
    selected = min(
        eligible,
        key=lambda r: (
            abs(r["metrics"]["score"] - medians["score"]),
            abs(r["metrics"]["turns"] - medians["turns"]),
            -sum(
                bool(r["teaching_examples"][k])
                for k in ("hint_knowledge_changes", "safe_plays", "discards")
            ),
            r["seed"],
        ),
    )
    return {
        "n_recorded": len(reports),
        "n_eligible": len(eligible),
        "n_excluded": len(reports) - len(eligible),
        "setup": eligible[0]["setup"],
        "medians": medians,
        "ranges": ranges,
        "selected": selected,
        "games": reports,
        "selection_rule": (
            "Nearest median score, then nearest median turn count, "
            "then teaching coverage, then seed."
        ),
        "scope": (
            "Empirical reference among complete, error-free games; "
            "excluded runs remain reported."
        ),
    }


def compare_to_reference(log: str | Path, summary_path: str | Path) -> dict[str, Any]:
    report = audit_game(log)
    reference = audit_reference(summary_path)
    matched = report["setup"] == reference["setup"]
    report["reference"] = {
        "settings_match": matched,
        "n_eligible": reference["n_eligible"],
        "n_excluded": reference["n_excluded"],
        "medians": reference["medians"],
        "ranges": reference["ranges"],
        "delta_from_median": {
            k: report["metrics"][k] - reference["medians"][k]
            for k in METRICS
            if matched and report["metrics"][k] is not None
        },
    }
    return report


def select_replay(summary_path: str | Path, output: str | Path) -> dict[str, Any]:
    reference = audit_reference(summary_path)
    chosen = reference["selected"]
    note = (
        f"Illustrative game selected from {reference['n_recorded']} recorded runs "
        f"({reference['n_eligible']} eligible; {reference['n_excluded']} excluded). "
        f"Score {chosen['metrics']['score']}; median score {reference['medians']['score']}. "
        "Selected by proximity to median score and game length; not evidence of a CK effect."
    )
    export_replay(chosen["log_path"], output, selection_note=note)
    reference["html_path"] = str(Path(output).resolve())
    report_path = Path(output).with_suffix(".audit.json")
    reference["audit_path"] = str(report_path.resolve())
    report_path.write_text(json.dumps(reference, indent=2))
    return reference
