"""Controlled thinking/action-order probes of one recorded decision."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
import time
from pathlib import Path

from .actions import Action
from .observations import PlayerObservation
from .runner import _build_agent, load_config


def _normalized(payload):
    result = copy.deepcopy(payload)
    kwargs = result.get("chat_template_kwargs", {})
    kwargs.pop("enable_thinking", None)
    kwargs.pop("preserve_thinking", None)
    if not kwargs:
        result.pop("chat_template_kwargs", None)
    for message in result["messages"]:
        if message["role"] == "user":
            message["content"] = json.loads(message["content"])
    return result


def diagnose_turn(
    config_path, log_path, *, turn, output, repetitions=1, order_seed=0, output_mode="recorded"
):
    """Make four independent calls per repetition; never execute a game action."""
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    if output_mode not in {"recorded", "prompt-json"}:
        raise ValueError("output_mode must be recorded or prompt-json")
    records = [json.loads(line) for line in Path(log_path).read_text().splitlines() if line.strip()]
    matches = [
        r
        for r in records
        if r.get("turn") == turn and r.get("event_kind") in {"turn", "agent_error"}
    ]
    if len(matches) != 1:
        raise ValueError("Source must contain exactly one decision at the requested turn")
    record = matches[0]
    original = record.get("request_payload")
    instruction = record.get("private_instruction")
    if not original or instruction is None:
        raise ValueError("Source must record request_payload and private_instruction")
    cfg = load_config(config_path)
    spec = dict(cfg["agents"][record["player"]], http_max_retries=0)
    spec.setdefault("mechanical_scaffold", cfg.get("mechanical_scaffold", "derived"))
    if spec.get("type") != "openai_compatible" or spec.get("model") != original["model"]:
        raise ValueError("Config must use the recorded openai_compatible model")
    raw_obs = copy.deepcopy(record["observation"])
    for field in ("other_hands", "public_knowledge", "newest_card_index", "play_safety"):
        raw_obs[field] = {int(k): v for k, v in raw_obs[field].items()}
    obs = PlayerObservation(**raw_obs)
    legal = [Action.from_dict(a) for a in record["legal_actions"]]
    agent = _build_agent(spec, seed=0)
    agent.record_http_attempts = True
    if _normalized(original) != _normalized(agent._request_payload(obs, legal, instruction)):
        raise ValueError("Config differs from recorded request beyond thinking controls")
    user_positions = [i for i, m in enumerate(original["messages"]) if m["role"] == "user"]
    if len(user_positions) != 1:
        raise ValueError("Expected exactly one recorded user message")
    user_position = user_positions[0]
    user = json.loads(original["messages"][user_position]["content"])
    expected = [{"action_index": i, "action": a.to_dict()} for i, a in enumerate(legal)]
    if user.get("legal_actions") != expected or len(legal) < 2:
        raise ValueError("Recorded indexed actions do not match the legal action list")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    results = []
    rng = random.Random(order_seed)
    # Exclusive creation protects previous diagnostics and the source game.
    with destination.open("x") as stream:
        for repetition in range(repetitions):
            permutation = list(range(len(legal)))
            rng.shuffle(permutation)
            # Move every position so a repeated index is distinguishable.
            while any(i == value for i, value in enumerate(permutation)):
                rng.shuffle(permutation)
            arms = [
                (thinking, shuffled) for thinking in (False, True) for shuffled in (False, True)
            ]
            rng.shuffle(arms)
            for thinking, shuffled in arms:
                mapping = permutation if shuffled else list(range(len(legal)))
                presented = [legal[i] for i in mapping]
                payload = copy.deepcopy(original)
                if output_mode == "prompt-json":
                    payload.pop("response_format", None)
                payload.setdefault("chat_template_kwargs", {}).update(
                    enable_thinking=thinking, preserve_thinking=False
                )
                if shuffled:
                    changed_user = copy.deepcopy(user)
                    changed_user["legal_actions"] = [
                        {"action_index": i, "action": a.to_dict()} for i, a in enumerate(presented)
                    ]
                    payload["messages"][user_position]["content"] = json.dumps(
                        changed_user, ensure_ascii=False
                    )
                label = f"thinking={'on' if thinking else 'off'}, order={'shuffled' if shuffled else 'original'}"
                print(
                    f"Repetition {repetition + 1}: {label} | requesting…",
                    file=sys.stderr,
                    flush=True,
                )
                started = time.monotonic()
                decision = agent.act(obs, presented, instruction, prepared_payload=payload)
                result = {
                    "source": {"log": str(log_path), "turn": turn, "player": record["player"]},
                    "repetition": repetition + 1,
                    "thinking_requested": thinking,
                    "shuffled": shuffled,
                    "order_seed": order_seed,
                    "output_mode": output_mode,
                    "presented_index_to_original_index": mapping,
                    "presented_action_index": decision.action_index,
                    "original_action_index": (
                        mapping[decision.action_index]
                        if decision.action_index is not None
                        else None
                    ),
                    "action": decision.action.to_dict() if decision.action else None,
                    "ok": decision.action is not None and decision.parse_error is None,
                    "error": decision.parse_error,
                    "elapsed_s": round(time.monotonic() - started, 3),
                    "request_payload": payload,
                    "request_sha256": hashlib.sha256(
                        json.dumps(payload, sort_keys=True).encode()
                    ).hexdigest(),
                    "raw_response": decision.raw_response,
                    "response_channel": decision.response_channel,
                    "api_response": decision.api_response,
                    "http_attempts": decision.http_attempts,
                    "usage": (decision.api_response or {}).get("usage"),
                }
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
                results.append(
                    {
                        k: v
                        for k, v in result.items()
                        if k
                        in {
                            "repetition",
                            "thinking_requested",
                            "shuffled",
                            "presented_action_index",
                            "original_action_index",
                            "action",
                            "ok",
                            "error",
                            "elapsed_s",
                            "output_mode",
                            "response_channel",
                            "usage",
                        }
                    }
                )
                print(
                    f"{label} | {decision.raw_response} | error={decision.parse_error}",
                    file=sys.stderr,
                    flush=True,
                )
    return {
        "output": str(destination),
        "source_turn": turn,
        "results": results,
        "interpretation": "Controlled single-state diagnostic; requested thinking is not proof of actual reasoning.",
    }
