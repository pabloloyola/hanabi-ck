"""Model identity disclosure, independent of convention knowledge treatments."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from .metrics import aggregate_games

MODES = {"hidden", "named"}


def identity_instruction(specs: list[dict[str, Any]], player: int, mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"identity_disclosure must be one of {sorted(MODES)}")
    if len(specs) != 2 or any(not s.get("model") for s in specs):
        raise ValueError("Identity disclosure requires two agents with explicit model IDs")
    own, partner = specs[player]["model"], specs[1 - player]["model"]
    text = f"Model identity information:\nYour underlying model is {own}.\n"
    if mode == "hidden":
        text += "Your teammate's underlying model identity is not disclosed."
    else:
        text += f"Your teammate's underlying model is {partner}."
    return text + "\nNo statement is made about what identity information your teammate received."


def prepare_identity_suite(config_path: str | Path, output: str | Path) -> dict[str, Any]:
    cfg = yaml.safe_load(Path(config_path).read_text())
    models = cfg["models"]
    if set(models) != {"A", "B"}:
        raise ValueError("Identity suite requires models A and B")
    if any(not s.get("model") for s in models.values()):
        raise ValueError("Both models require explicit model IDs")
    if models["A"]["model"] == models["B"]["model"]:
        raise ValueError("Models A and B must have different model IDs")
    if any(s.get("api_key") for s in models.values()):
        raise ValueError("Use environment API keys; generated configs must not contain credentials")
    seeds = cfg.get("seeds", [0])
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("Provide nonempty unique seeds")
    root = Path(output)
    if root.exists() and any(root.iterdir()):
        raise ValueError("Output directory must be empty to preserve previous setups")
    common = deepcopy(cfg.get("game", {}))
    common.update(num_players=2, conditions=["ck0"], agent_error_policy="abort")
    common.setdefault("mechanical_scaffold", "derived")
    for key in ("log_private_instructions", "log_raw_model_responses", "log_request_payloads"):
        common[key] = True
    cells = []
    root.mkdir(parents=True, exist_ok=True)
    for pairing in ("AA", "BB", "AB", "BA"):
        for mode in ("hidden", "named"):
            cell = f"{pairing}_{mode}"
            game = deepcopy(common)
            game.update(
                experiment=f"{cfg['experiment']}_{cell}",
                seeds=seeds,
                identity_disclosure=mode,
                agents=[
                    dict(deepcopy(models[m]), name=f"player_{p}") for p, m in enumerate(pairing)
                ],
            )
            path = root / f"{cell}.yaml"
            path.write_text(yaml.safe_dump(game, sort_keys=False))
            cells.append(
                {
                    "cell": cell,
                    "pairing": pairing,
                    "disclosure": mode,
                    "config_path": str(path.resolve()),
                    "config_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "summary_path": str(
                        (
                            Path(game.get("output_dir", "runs"))
                            / game["experiment"]
                            / "summary.json"
                        ).resolve()
                    ),
                }
            )
    manifest = {
        "experiment": cfg["experiment"],
        "seeds": seeds,
        "n_games_planned": 8 * len(seeds),
        "cells": cells,
        "models": {m: s["model"] for m, s in models.items()},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def analyze_identity_suite(manifest_path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(manifest_path).read_text())
    cells, valid_by_cell, missing = {}, {}, []
    for cell in manifest["cells"]:
        path = Path(cell["summary_path"])
        if not path.exists():
            missing.append(cell["cell"])
            continue
        summary = json.loads(path.read_text())
        if summary.get("identity_config_sha256") != cell["config_sha256"]:
            raise ValueError(f"Summary config hash mismatch: {path}")
        games = summary["games"]
        expected = {
            "mode": cell["disclosure"],
            "agent_models": [manifest["models"][m] for m in cell["pairing"]],
        }
        if summary.get("identity_setup") != expected or summary["conditions"] != ["ck0"]:
            raise ValueError(f"Summary identity setup mismatch: {path}")
        seen = set()
        for g in games:
            if g["seed"] in seen or g["seed"] not in manifest["seeds"]:
                raise ValueError(f"Unexpected or duplicate game seed: {path}")
            seen.add(g["seed"])
        valid = [
            g
            for g in games
            if g.get("valid") and not g.get("agent_error_count") and not g.get("fallback_count")
        ]
        cells[cell["cell"]] = {
            "aggregate": aggregate_games(games),
            "n_eligible": len(valid),
            "missing_seeds": sorted(set(manifest["seeds"]) - seen),
        }
        valid_by_cell[cell["cell"]] = {g["seed"]: g for g in valid}
    paired = {}
    for pairing in ("AA", "BB", "AB", "BA"):
        hidden = valid_by_cell.get(f"{pairing}_hidden", {})
        named = valid_by_cell.get(f"{pairing}_named", {})
        seeds = sorted(hidden.keys() & named.keys())
        differences = [
            {
                "seed": s,
                **{
                    metric: named[s][metric] - hidden[s][metric]
                    for metric in ("score", "hints", "misplays", "turns")
                },
            }
            for s in seeds
        ]
        paired[pairing] = {
            "n_valid_pairs": len(seeds),
            "differences_named_minus_hidden": differences,
            "mean_score_difference": mean(d["score"] for d in differences) if differences else None,
        }
    return {
        "cells": cells,
        "missing_cells": missing,
        "paired": paired,
        "interpretation": "Descriptive identity-disclosure pilot; no CK or significance claim.",
    }
