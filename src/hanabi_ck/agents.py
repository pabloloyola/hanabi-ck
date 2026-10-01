from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from .actions import Action
from .observations import PlayerObservation


@dataclass
class AgentDecision:
    action: Action | None
    raw_response: str | None = None
    parse_error: str | None = None
    fallback_used: bool = False


class Agent(Protocol):
    name: str

    def act(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> AgentDecision: ...


class RandomAgent:
    def __init__(self, name: str, seed: int = 0):
        self.name = name
        self.rng = random.Random(seed)

    def act(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> AgentDecision:
        del observation, private_instruction
        return AgentDecision(action=self.rng.choice(legal_actions))


def _candidate_count(knowledge: dict[str, Any]) -> int:
    return len(knowledge["possible_colors"]) * len(knowledge["possible_ranks"])


def _safe_to_play(knowledge: dict[str, Any], stacks: dict[str, int]) -> bool:
    colors = knowledge["possible_colors"]
    ranks = knowledge["possible_ranks"]
    return bool(colors and ranks) and all(
        stacks[color] + 1 == rank
        for color in colors
        for rank in ranks
    )


def _safe_to_discard(knowledge: dict[str, Any], stacks: dict[str, int]) -> bool:
    colors = knowledge["possible_colors"]
    ranks = knowledge["possible_ranks"]
    return bool(colors and ranks) and all(
        rank <= stacks[color]
        for color in colors
        for rank in ranks
    )


def _simulate_hint(
    cards: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
    action: Action,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for card, card_knowledge in zip(cards, knowledge):
        colors = set(card_knowledge["possible_colors"])
        ranks = set(card_knowledge["possible_ranks"])

        if action.attribute == "color":
            value = str(action.value)
            matches = card["color"] == value
            if matches:
                colors.intersection_update({value})
            else:
                colors.discard(value)
        else:
            value = int(action.value)
            matches = int(card["rank"]) == value
            if matches:
                ranks.intersection_update({value})
            else:
                ranks.discard(value)

        result.append(
            {
                "possible_colors": sorted(colors),
                "possible_ranks": sorted(ranks),
            }
        )

    return result


class SimpleAgent:
    """Deterministic epistemically-safe baseline for smoke tests.

    It uses only public hint knowledge about its own cards, never hidden state.
    Hints are selected using visible partner cards and the partner's public
    knowledge, which is legal information in Hanabi.
    """

    def __init__(self, name: str = "simple"):
        self.name = name

    def _best_hint(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        *,
        require_new_safe: bool,
    ) -> Action | None:
        best: Action | None = None
        best_score: tuple[int, int, int, int] | None = None

        for action in legal_actions:
            if action.type != "hint" or action.target is None:
                continue

            cards = observation.other_hands[action.target]
            before = observation.public_knowledge[action.target]
            after = _simulate_hint(cards, before, action)

            info_gain = (
                sum(_candidate_count(k) for k in before)
                - sum(_candidate_count(k) for k in after)
            )
            if info_gain <= 0:
                continue

            safe_before = [_safe_to_play(k, observation.stacks) for k in before]
            safe_after = [_safe_to_play(k, observation.stacks) for k in after]
            newly_safe = sum(
                (not was_safe) and is_safe
                for was_safe, is_safe in zip(safe_before, safe_after)
            )

            if action.attribute == "color":
                touched = [card["color"] == action.value for card in cards]
            else:
                touched = [
                    int(card["rank"]) == int(action.value)
                    for card in cards
                ]

            directly_new_safe = sum(
                (not was_safe) and is_safe and is_touched
                for was_safe, is_safe, is_touched in zip(
                    safe_before,
                    safe_after,
                    touched,
                )
            )

            if require_new_safe and newly_safe == 0:
                continue

            score = (
                directly_new_safe,
                newly_safe,
                info_gain,
                1 if action.attribute == "rank" else 0,
            )
            if best_score is None or score > best_score:
                best_score = score
                best = action

        return best

    def act(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> AgentDecision:
        del private_instruction

        # Play a card only when every identity consistent with the public hint
        # information is currently playable.
        for i, knowledge in enumerate(observation.own_knowledge):
            action = Action.play(i)
            if action in legal_actions and _safe_to_play(knowledge, observation.stacks):
                return AgentDecision(action)

        # Prefer hints that create at least one provably safe play.
        hint = self._best_hint(
            observation,
            legal_actions,
            require_new_safe=True,
        )
        if hint is not None:
            return AgentDecision(hint)

        # Prefer a provably useless card when discarding is legal.
        for i, knowledge in enumerate(observation.own_knowledge):
            action = Action.discard(i)
            if action in legal_actions and _safe_to_discard(knowledge, observation.stacks):
                return AgentDecision(action)

        # If discarding is allowed, cycle the oldest card rather than spending
        # hints that do not create an actionable safe play.
        oldest = Action.discard(0)
        if oldest in legal_actions:
            return AgentDecision(oldest)

        # At eight information tokens discard is illegal, so use the most
        # informative non-redundant hint available.
        hint = self._best_hint(
            observation,
            legal_actions,
            require_new_safe=False,
        )
        if hint is not None:
            return AgentDecision(hint)

        # Rare fallback: for example, every legal hint is redundant at max tokens.
        for action in legal_actions:
            if action.type == "hint":
                return AgentDecision(action)
        return AgentDecision(legal_actions[0])


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")
    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Response JSON is not an object")
    return obj


class OpenAICompatibleAgent:
    def __init__(
        self,
        *,
        name: str,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
        timeout_s: float = 60.0,
    ):
        self.name = name
        self.model = model
        self.base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "lm-studio")
        self.temperature = temperature
        self.timeout_s = timeout_s

    def _prompt(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> list[dict[str, str]]:
        system = """You are a Hanabi-playing research agent.
You must choose exactly one legal action.
You cannot see your own cards except through the supplied card-knowledge sets.
The public_knowledge field records hint-derived knowledge that every player can observe.
Never infer hidden state from the research setup.
Return ONLY one JSON object corresponding exactly to one legal action.
Do not include explanation."""
        user = {
            "private_experimental_instruction": private_instruction,
            "observation": observation.to_dict(),
            "legal_actions": [a.to_dict() for a in legal_actions],
            "output_examples": [
                {"type": "play", "card_index": 0},
                {"type": "discard", "card_index": 1},
                {"type": "hint", "target": 1, "attribute": "rank", "value": 2},
            ],
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ]

    def act(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> AgentDecision:
        payload = {
            "model": self.model,
            "messages": self._prompt(
                observation,
                legal_actions,
                private_instruction,
            ),
            "temperature": self.temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        raw = ""
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            raw = data["choices"][0]["message"]["content"]
            parsed = _extract_json_object(raw)
            action = Action.from_dict(parsed)
            if action not in legal_actions:
                raise ValueError(
                    f"Model returned illegal action: {action.to_dict()}"
                )
            return AgentDecision(action=action, raw_response=raw)
        except Exception as exc:
            return AgentDecision(
                action=None,
                raw_response=raw or None,
                parse_error=f"{type(exc).__name__}: {exc}",
                fallback_used=False,
            )
