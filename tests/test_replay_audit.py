import json
from statistics import median

import pytest
import yaml

from hanabi_ck.replay_audit import (
    audit_game,
    audit_reference,
    compare_to_reference,
    select_replay,
)
from hanabi_ck.runner import run_experiment


def _batch(tmp_path):
    cfg = {
        "experiment": "reference",
        "output_dir": str(tmp_path),
        "seeds": [0, 1, 2],
        "conditions": ["ck0"],
        "agents": [{"type": "simple"}] * 2,
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    run_experiment(path)
    return tmp_path / "reference/summary.json"


def test_selection_matches_declared_rule_and_keeps_all_records(tmp_path):
    summary = _batch(tmp_path)
    ref = audit_reference(summary)
    scores = [g["metrics"]["score"] for g in ref["games"]]
    assert ref["medians"]["score"] == median(scores)
    assert ref["selected"]["eligible"] is True
    assert abs(ref["selected"]["metrics"]["score"] - median(scores)) == min(
        abs(score - median(scores)) for score in scores
    )
    out = select_replay(summary, tmp_path / "chosen.html")
    assert "selection_note" in (tmp_path / "chosen.html").read_text()
    saved = json.loads((tmp_path / "chosen.audit.json").read_text())
    assert len(saved["games"]) == 3
    assert out["n_eligible"] == 3
    report = compare_to_reference(out["selected"]["log_path"], summary)
    assert report["reference"]["settings_match"] is True


@pytest.mark.parametrize("damage", ["truncated", "continuity", "illegal", "fallback"])
def test_audit_excludes_broken_or_fallback_recordings(tmp_path, damage):
    summary = _batch(tmp_path)
    log = summary.parent / "ck0/seed_000000.jsonl"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    if damage == "truncated":
        records.pop()
    elif damage == "continuity":
        records[1]["researcher_true_state_before"]["deck_size"] += 1
    elif damage == "illegal":
        records[0]["action"]["type"] = "discard"
        records[0]["action"]["card_index"] = 999
    elif damage == "fallback":
        records[0]["agent"]["fallback_used"] = True
    log.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    assert audit_game(log)["eligible"] is False
    ref = audit_reference(summary)
    assert ref["n_excluded"] == 1
    assert ref["n_eligible"] == 2
    assert ref["selected"]["seed"] != 0


def test_reference_rejects_mixed_scaffolds(tmp_path):
    summary = _batch(tmp_path)
    log = summary.parent / "ck0/seed_000000.jsonl"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    for record in records:
        record["mechanical_scaffold"] = "raw"
    log.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    with pytest.raises(ValueError, match="different settings"):
        audit_reference(summary)


def test_comparison_does_not_claim_typicality_under_different_settings(tmp_path):
    summary = _batch(tmp_path)
    source = summary.parent / "ck0/seed_000000.jsonl"
    records = [json.loads(line) for line in source.read_text().splitlines()]
    for record in records:
        record["condition"] = "ck3_mutual"
    other = tmp_path / "different.jsonl"
    other.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    result = compare_to_reference(other, summary)
    assert result["reference"]["settings_match"] is False
    assert result["reference"]["delta_from_median"] == {}
