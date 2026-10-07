from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .actions import Action
from .agents import AgentDecision, OpenAICompatibleAgent, RandomAgent, SimpleAgent
from .backends import BACKEND_NAMES, create_backend
from .conditions import DEFAULT_CONVENTION, get_condition
from .logging import JsonlLogger
from .metrics import aggregate_games, summarize_game
from .scaffolds import normalize_mechanical_scaffold


ERROR_POLICIES = {"abort", "safe_baseline"}


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
            temperature=(
                None
                if spec.get("temperature", 0.0) is None
                else float(spec.get("temperature", 0.0))
            ),
            timeout_s=float(spec.get("timeout_s", 60.0)),
            max_tokens=(
                int(spec["max_tokens"])
                if spec.get("max_tokens") is not None
                else None
            ),
            extra_body=dict(spec.get("extra_body") or {}),
            structured_output=bool(spec.get("structured_output", False)),
            mechanical_scaffold=normalize_mechanical_scaffold(
                spec.get("mechanical_scaffold", "derived")
            ),
        )
    raise ValueError(f"Unknown agent type: {typ}")


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("Config must be a YAML mapping")
    return cfg


def _resolve_agent_decision(
    decision: AgentDecision,
    *,
    error_policy: str,
    observation,
    legal_actions: list[Action],
) -> tuple[Action | None, bool]:
    """Return the executable action and whether a runner fallback was used."""
    if decision.action is not None and decision.parse_error is None:
        return decision.action, False

    if error_policy == "abort":
        return None, False

    if error_policy == "safe_baseline":
        fallback = SimpleAgent(name="safe_fallback").act(
            observation,
            legal_actions,
            "",
        )
        if fallback.action is None:
            raise RuntimeError("Safe baseline unexpectedly returned no action")
        return fallback.action, True

    raise ValueError(
        f"Unknown agent_error_policy {error_policy!r}; "
        f"choose from {sorted(ERROR_POLICIES)}"
    )


def run_experiment(config_path: str | Path) -> dict[str, Any]:
    cfg = load_config(config_path)
    experiment = cfg.get("experiment", "hanabi_ck")
    output_root = Path(cfg.get("output_dir", "runs")) / experiment
    output_root.mkdir(parents=True, exist_ok=True)

    num_players = int(cfg.get("num_players", 2))
    seeds = [int(s) for s in cfg.get("seeds", [0])]
    conditions = list(cfg.get("conditions", ["ck0"]))
    convention = str(cfg.get("convention", DEFAULT_CONVENTION))
    ck1_informed_players = {
        int(p) for p in cfg.get("ck1_informed_players", [0])
    }
    backend_name = str(cfg.get("backend", "native")).strip().lower()
    if backend_name not in BACKEND_NAMES:
        raise ValueError(
            f"backend must be one of {sorted(BACKEND_NAMES)}"
        )

    mechanical_scaffold = normalize_mechanical_scaffold(
        cfg.get("mechanical_scaffold", "derived")
    )

    error_policy = str(cfg.get("agent_error_policy", "abort"))
    if error_policy not in ERROR_POLICIES:
        raise ValueError(
            f"agent_error_policy must be one of {sorted(ERROR_POLICIES)}"
        )

    agent_specs = [dict(spec) for spec in cfg["agents"]]
    for spec in agent_specs:
        spec.setdefault("mechanical_scaffold", mechanical_scaffold)
    if len(agent_specs) != num_players:
        raise ValueError("Number of agent specs must equal num_players")

    all_summaries: list[dict[str, Any]] = []

    for condition_name in conditions:
        condition = get_condition(condition_name)
        for seed in seeds:
            game = create_backend(
                backend_name,
                num_players=num_players,
                seed=seed,
            )
            agents = [
                _build_agent(spec, seed=(seed * 1000 + p))
                for p, spec in enumerate(agent_specs)
            ]

            log_path = output_root / condition_name / f"seed_{seed:06d}.jsonl"
            if log_path.exists():
                log_path.unlink()
            logger = JsonlLogger(log_path)
            turns: list[dict[str, Any]] = []
            aborted = False
            abort_reason: str | None = None
            agent_error_count = 0

            while not game.done:
                p = game.current_player
                observation = game.observe(p)
                legal = game.legal_actions(p)
                private_instruction = condition.private_instruction(
                    player_id=p,
                    num_players=num_players,
                    convention=convention,
                    informed_players=ck1_informed_players,
                )

                decision = agents[p].act(
                    observation,
                    legal,
                    private_instruction,
                )

                executable_action, runner_fallback_used = _resolve_agent_decision(
                    decision,
                    error_policy=error_policy,
                    observation=observation,
                    legal_actions=legal,
                )

                if decision.parse_error is not None:
                    agent_error_count += 1

                if executable_action is None:
                    aborted = True
                    abort_reason = decision.parse_error or "Agent returned no action"
                    logger.write(
                        {
                            "event_kind": "agent_error",
                            "experiment": experiment,
                            "backend": backend_name,
                            "mechanical_scaffold": mechanical_scaffold,
                            "condition": condition_name,
                            "condition_description": condition.description,
                            "seed": seed,
                            "turn": len(turns),
                            "player": p,
                            "agent": {
                                "name": agents[p].name,
                                "type": agent_specs[p]["type"],
                                "model": agent_specs[p].get("model"),
                                "response_error": True,
                                "response_channel": decision.response_channel,
                                "error": abort_reason,
                            },
                            "agent_error_policy": error_policy,
                            "private_instruction_hash": _hash_text(
                                private_instruction
                            ),
                            "private_instruction": (
                                private_instruction
                                if cfg.get("log_private_instructions", True)
                                else None
                            ),
                            "observation": observation.to_dict(),
                            "legal_actions": [a.to_dict() for a in legal],
                            "raw_response": (
                                decision.raw_response
                                if cfg.get("log_raw_model_responses", True)
                                else None
                            ),
                            "api_response": (
                                decision.api_response
                                if cfg.get("log_raw_model_responses", True)
                                else None
                            ),
                            "researcher_true_state_before": game.true_state(),
                            "model_action_index": decision.action_index,
                            "executed_action_index": None,
                            "epistemically_safe_play": None,
                            "epistemic_play_status": None,
                            "action": None,
                            "outcome": None,
                            "probes": {},
                        }
                    )
                    break

                true_state_before = game.true_state()
                executed_action_index = legal.index(executable_action)
                epistemically_safe_play: bool | None = None
                epistemic_play_status: str | None = None
                if executable_action.type == "play":
                    assert executable_action.card_index is not None
                    card_index = executable_action.card_index
                    epistemically_safe_play = (
                        card_index in observation.provably_playable_indices
                    )
                    epistemic_play_status = observation.play_safety[card_index]

                result = game.step(executable_action)

                record = {
                    "event_kind": "turn",
                    "experiment": experiment,
                    "backend": backend_name,
                    "mechanical_scaffold": mechanical_scaffold,
                    "condition": condition_name,
                    "condition_description": condition.description,
                    "seed": seed,
                    "turn": len(turns),
                    "player": p,
                    "agent": {
                        "name": agents[p].name,
                        "type": agent_specs[p]["type"],
                        "model": agent_specs[p].get("model"),
                        "response_error": decision.parse_error is not None,
                        "response_channel": decision.response_channel,
                        "error": decision.parse_error,
                        "fallback_used": runner_fallback_used,
                        "fallback_policy": (
                            error_policy if runner_fallback_used else None
                        ),
                    },
                    "agent_error_policy": error_policy,
                    "private_instruction_hash": _hash_text(private_instruction),
                    "private_instruction": (
                        private_instruction
                        if cfg.get("log_private_instructions", True)
                        else None
                    ),
                    "observation": observation.to_dict(),
                    "legal_actions": [a.to_dict() for a in legal],
                    "model_action_index": decision.action_index,
                    "executed_action_index": executed_action_index,
                    "epistemically_safe_play": epistemically_safe_play,
                    "epistemic_play_status": epistemic_play_status,
                    "action": executable_action.to_dict(),
                    "raw_response": (
                        decision.raw_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                    "api_response": (
                        decision.api_response
                        if cfg.get("log_raw_model_responses", True)
                        else None
                    ),
                    "researcher_true_state_before": true_state_before,
                    "outcome": result.outcome,
                    "probes": {},
                }
                logger.write(record)
                turns.append(record)

            game_summary = summarize_game(turns, game.true_state())
            game_summary.update(
                {
                    "experiment": experiment,
                    "condition": condition_name,
                    "seed": seed,
                    "backend": backend_name,
                    "mechanical_scaffold": mechanical_scaffold,
                    "valid": not aborted,
                    "aborted": aborted,
                    "abort_reason": abort_reason,
                    "agent_error_count": agent_error_count,
                    "agent_error_policy": error_policy,
                    "log_path": str(log_path),
                }
            )
            all_summaries.append(game_summary)

    by_condition: dict[str, Any] = {}
    for condition_name in conditions:
        subset = [
            g
            for g in all_summaries
            if g["condition"] == condition_name
        ]
        by_condition[condition_name] = aggregate_games(subset)

    summary = {
        "experiment": experiment,
        "config_path": str(config_path),
        "num_players": num_players,
        "backend": backend_name,
        "mechanical_scaffold": mechanical_scaffold,
        "seeds": seeds,
        "conditions": conditions,
        "agent_error_policy": error_policy,
        "ck1_informed_players": sorted(ck1_informed_players),
        "games": all_summaries,
        "aggregate_by_condition": by_condition,
    }
    summary_path = output_root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary
