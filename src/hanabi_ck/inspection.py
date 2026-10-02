from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _card(card: dict[str, Any]) -> str:
    return f"{card['color']}{card['rank']}"


def _hand(cards: list[dict[str, Any]]) -> str:
    return " ".join(
        f"{index}:{_card(card)}"
        for index, card in enumerate(cards)
    )


def _knowledge(card_knowledge: dict[str, Any]) -> str:
    colors = card_knowledge["possible_colors"]
    ranks = card_knowledge["possible_ranks"]
    color_text = (
        colors[0]
        if len(colors) == 1
        else "{" + "".join(colors) + "}"
    )
    rank_text = (
        str(ranks[0])
        if len(ranks) == 1
        else "{" + ",".join(str(rank) for rank in ranks) + "}"
    )
    return f"{color_text}/{rank_text}"


def _knowledge_row(
    knowledge: list[dict[str, Any]],
) -> str:
    return " ".join(
        f"{index}:{_knowledge(card_knowledge)}"
        for index, card_knowledge in enumerate(knowledge)
    )


def _action(action: dict[str, Any] | None) -> str:
    if action is None:
        return "<none>"
    if action["type"] in {"play", "discard"}:
        return f"{action['type']} card[{action['card_index']}]"
    return (
        f"hint P{action['target']} "
        f"{action['attribute']}={action['value']}"
    )


def _outcome(record: dict[str, Any]) -> str:
    action = record["action"]
    outcome = record["outcome"]

    if action["type"] == "play":
        card = _card(outcome["card"])
        status = "SUCCESS" if outcome["play_success"] else "MISPLAY"
        return f"{status} {card}; score={outcome['score_after']}"

    if action["type"] == "discard":
        card = _card(outcome["card"])
        return f"discarded {card}; info={outcome['information_tokens_after']}"

    touched = outcome.get("touched_indices", [])
    return (
        f"touched={touched}; "
        f"info={outcome['information_tokens_after']}"
    )


def inspect_log(
    path: str | Path,
    *,
    limit: int | None = None,
    show_true_state: bool = False,
    show_raw: bool = False,
) -> None:
    log_path = Path(path)
    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records:
        print(f"{log_path}: empty log")
        return

    first = records[0]
    print(
        f"experiment={first.get('experiment')} "
        f"condition={first.get('condition')} "
        f"seed={first.get('seed')}"
    )
    print(f"log={log_path}")
    print()

    shown = 0
    for record in records:
        if limit is not None and shown >= limit:
            print(f"... truncated after {limit} records")
            break
        shown += 1

        event_kind = record.get("event_kind", "turn")
        turn = record.get("turn")
        player = record.get("player")
        agent = record.get("agent", {})
        model = agent.get("model") or agent.get("name")

        if event_kind == "agent_error":
            print(
                f"TURN {turn:02d}  P{player}  {model}  AGENT ERROR"
            )
            print(f"  error: {agent.get('error')}")
            if agent.get("response_channel"):
                print(
                    f"  response_channel: {agent['response_channel']}"
                )
            if show_raw:
                if record.get("raw_response"):
                    print(f"  raw: {record['raw_response']}")
                if record.get("api_response"):
                    print(
                        "  api_response: "
                        + json.dumps(
                            record["api_response"],
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
            print("  game aborted; no Hanabi action executed")
            print()
            continue

        observation = record["observation"]
        stacks = observation["stacks"]
        score = sum(stacks.values())
        print(
            f"TURN {turn:02d}  P{player}  {model}  "
            f"score={score} info={observation['information_tokens']} "
            f"lives={observation['life_tokens']} "
            f"deck={observation['deck_size']}"
        )

        if observation.get("hand_order"):
            print(f"  hand_order: {observation['hand_order']}")
        if observation.get("newest_card_index") is not None:
            print(
                "  newest_card_index: "
                + json.dumps(
                    observation["newest_card_index"],
                    sort_keys=True,
                )
            )

        for other_player, cards in observation["other_hands"].items():
            print(f"  sees P{other_player}: {_hand(cards)}")

        print(
            "  own knowledge: "
            + _knowledge_row(observation["own_knowledge"])
        )
        print(
            "  provably playable: "
            + json.dumps(
                observation.get("provably_playable_indices", [])
            )
        )
        print(
            "  provably obsolete: "
            + json.dumps(
                observation.get("provably_obsolete_indices", [])
            )
        )

        for other_player, knowledge in observation["public_knowledge"].items():
            if int(other_player) == int(player):
                continue
            print(
                f"  public knowledge P{other_player}: "
                f"{_knowledge_row(knowledge)}"
            )

        if show_true_state:
            true_hands = record["researcher_true_state_before"]["hands"]
            print(
                f"  TRUE own hand: {_hand(true_hands[int(player)])}"
            )

        if agent.get("response_channel"):
            print(
                f"  response_channel: {agent['response_channel']}"
            )
        if record.get("executed_action_index") is not None:
            print(
                f"  action_index: {record['executed_action_index']}"
            )
        print(f"  action: {_action(record['action'])}")
        if record["action"]["type"] == "play":
            print(
                "  epistemic_play_status: "
                f"{record.get('epistemic_play_status')}"
            )
            print(
                "  epistemically_safe_play: "
                f"{record.get('epistemically_safe_play')}"
            )
        print(f"  outcome: {_outcome(record)}")

        if agent.get("response_error"):
            print(f"  model error: {agent.get('error')}")
        if agent.get("fallback_used"):
            print(
                "  FALLBACK: "
                f"{agent.get('fallback_policy', 'unknown')}"
            )
        if show_raw:
            if record.get("raw_response"):
                print(f"  raw: {record['raw_response']}")
            if record.get("api_response"):
                print(
                    "  api_response: "
                    + json.dumps(
                        record["api_response"],
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
        print()
