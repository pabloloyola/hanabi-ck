"""One real Hanabi decision, optionally reusing a failed recorded observation."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .actions import Action
from .backends import create_backend
from .conditions import DEFAULT_CONVENTION, get_condition
from .identity import identity_instruction
from .observations import PlayerObservation
from .runner import _build_agent, load_config


def check_hanabi_action(
    config_path: str | Path,
    *,
    log_path: str | Path | None = None,
    seed: int = 0,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    specs = [dict(s) for s in cfg["agents"]]
    for spec in specs:
        spec.setdefault("mechanical_scaffold", cfg.get("mechanical_scaffold", "derived"))
    original = None
    if log_path is not None:
        records = [
            json.loads(line) for line in Path(log_path).read_text().splitlines() if line.strip()
        ]
        if not records:
            raise ValueError("Source log is empty")
        record = records[-1]
        if record.get("event_kind") != "agent_error":
            raise ValueError("Source log must end with an agent_error record")
        player = record["player"]
        if specs[player].get("model") != record["agent"].get("model"):
            raise ValueError("Source and check must use the same model")
        if record.get("private_instruction") is None or not record.get("request_payload"):
            raise ValueError("Source must record private instruction and request payload")
        raw_obs = dict(record["observation"])
        for field in ("other_hands", "public_knowledge", "newest_card_index", "play_safety"):
            raw_obs[field] = {int(k): v for k, v in raw_obs[field].items()}
        observation = PlayerObservation(**raw_obs)
        legal = [Action.from_dict(a) for a in record["legal_actions"]]
        instruction = record["private_instruction"]
        original = record["request_payload"]
        source = {"log": str(log_path), "turn": record["turn"], "player": player}
    else:
        game = create_backend(
            cfg.get("backend", "native"), num_players=cfg.get("num_players", 2), seed=seed
        )
        player = game.current_player
        observation, legal = game.observe(player), game.legal_actions(player)
        instruction = get_condition(cfg.get("conditions", ["ck0"])[0]).private_instruction(
            player_id=player,
            num_players=len(specs),
            convention=cfg.get("convention", DEFAULT_CONVENTION),
            informed_players=set(cfg.get("ck1_informed_players", [0])),
        )
        if cfg.get("identity_disclosure") is not None:
            instruction += "\n\n" + identity_instruction(specs, player, cfg["identity_disclosure"])
        source = {"seed": seed, "turn": 0, "player": player}
    if specs[player].get("type") != "openai_compatible":
        raise ValueError("action-check requires an openai_compatible agent")
    # Exactly one HTTP attempt: no hidden retries or game execution.
    spec = dict(specs[player], http_max_retries=0)
    agent = _build_agent(spec, seed=seed)
    payload = agent._request_payload(observation, legal, instruction)
    if original is not None:
        def strip_provider(p):
            return {k: v for k, v in p.items() if k != "provider"}
        if strip_provider(original) != strip_provider(payload):
            raise ValueError("Check request differs from recorded request beyond provider routing")
    # Collect attempt telemetry without permitting retries.
    # act's telemetry is enabled independently of retries for this diagnostic.
    agent.record_http_attempts = True
    started = time.monotonic()
    decision = agent.act(observation, legal, instruction)
    data = decision.api_response or {}
    return {
        "config": str(config_path),
        "source": source,
        "model": spec["model"],
        "configured_provider": payload.get("provider"),
        "returned_model": data.get("model"),
        "returned_provider": data.get("provider"),
        "elapsed_s": round(time.monotonic() - started, 3),
        "ok": decision.action is not None and decision.parse_error is None,
        "error": decision.parse_error,
        "action": decision.action.to_dict() if decision.action else None,
        "http_attempts": decision.http_attempts,
        "request_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        "matches_original_except_provider": original is not None,
        "usage": data.get("usage"),
        "api_error": data.get("error"),
    }
