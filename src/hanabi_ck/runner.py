from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .agents import OpenAICompatibleAgent, RandomAgent, SimpleAgent
from .conditions import DEFAULT_CONVENTION, get_condition
from .engine import HanabiGame
from .logging import JsonlLogger
from .metrics import aggregate_games, summarize_game


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _build_agent(spec: dict[str, Any], *, seed: int):
    typ = spec["type"]
    name = spec.get("name", typ)
    if typ == "random":
        return RandomAgent(name=name, seed=seed)
    if typ == "simple":
        return SimpleAgent(name=name)
    if typ == "openai_compatible":
        return OpenAICompatibleAgent(
            name=name,
            model=spec["model"],
            base_url=spec.get("base_url"),
            api_key=spec.get("api_key"),
            temperature=float(spec.get("temperature", 0.0)),
            timeout_s=float(spec.get("timeout_s", 60.0)),
        )
    raise ValueError(f"Unknown agent type: {typ}")


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("Config must be a YAML mapping")
    return cfg


def run_experiment(config_path: str | Path) -> dict[str, Any]:
    cfg = load_config(config_path)
    experiment = cfg.get("experiment", "hanabi_ck")
    output_root = Path(cfg.get("output_dir", "runs")) / experiment
    output_root.mkdir(parents=True, exist_ok=True)

    num_players = int(cfg.get("num_players", 2))
    seeds = [int(s) for s in cfg.get("seeds", [0])]
    conditions = list(cfg.get("conditions", ["ck0"]))
    convention = str(cfg.get("convention", DEFAULT_CONVENTION))
    agent_specs = list(cfg["agents"])
    if len(agent_specs) != num_players:
        raise ValueError("Number of agent specs must equal num_players")

    all_summaries: list[dict[str, Any]] = []

    for condition_name in conditions:
        condition = get_condition(condition_name)
        for seed in seeds:
            game = HanabiGame(num_players=num_players, seed=seed)
            agents = [
                _build_agent(spec, seed=(seed * 1000 + p))
                for p, spec in enumerate(agent_specs)
            ]

            log_path = output_root / condition_name / f"seed_{seed:06d}.jsonl"
            if log_path.exists():
                log_path.unlink()
            logger = JsonlLogger(log_path)
            turns: list[dict[str, Any]] = []

            while not game.done:
                p = game.current_player
                observation = game.observe(p)
                legal = game.legal_actions(p)
                private_instruction = condition.private_instruction(
                    player_id=p,
                    num_players=num_players,
                    convention=convention,
                )

                decision = agents[p].act(observation, legal, private_instruction)
                true_state_before = game.true_state()
                result = game.step(decision.action)

                record = {
                    "experiment": experiment,
                    "condition": condition_name,
                    "condition_description": condition.description,
                    "seed": seed,
                    "turn": len(turns),
                    "player": p,
                    "agent": {
                        "name": agents[p].name,
                        "type": agent_specs[p]["type"],
                        "model": agent_specs[p].get("model"),
                        "fallback_used": decision.fallback_used,
                        "parse_error": decision.parse_error,
                    },
                    "private_instruction_hash": _hash_text(private_instruction),
                    "private_instruction": private_instruction
                        if cfg.get("log_private_instructions", True)
                        else None,
                    "observation": observation.to_dict(),
                    "legal_actions": [a.to_dict() for a in legal],
                    "action": decision.action.to_dict(),
                    "raw_response": decision.raw_response
                        if cfg.get("log_raw_model_responses", True)
                        else None,
                    "researcher_true_state_before": true_state_before,
                    "outcome": result.outcome,
                    "probes": {},
                }
                logger.write(record)
                turns.append(record)

            game_summary = summarize_game(turns, game.true_state())
            game_summary.update({
                "experiment": experiment,
                "condition": condition_name,
                "seed": seed,
                "log_path": str(log_path),
            })
            all_summaries.append(game_summary)

    by_condition: dict[str, Any] = {}
    for condition_name in conditions:
        subset = [g for g in all_summaries if g["condition"] == condition_name]
        by_condition[condition_name] = aggregate_games(subset)

    summary = {
        "experiment": experiment,
        "config_path": str(config_path),
        "num_players": num_players,
        "seeds": seeds,
        "conditions": conditions,
        "games": all_summaries,
        "aggregate_by_condition": by_condition,
    }
    summary_path = output_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
