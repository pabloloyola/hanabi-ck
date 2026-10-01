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
    action: Action
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


class SimpleAgent:
    """Small deterministic baseline."""

    def __init__(self, name: str = "simple"):
        self.name = name

    def act(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> AgentDecision:
        del private_instruction

        for i, k in enumerate(observation.own_knowledge):
            colors = k["possible_colors"]
            ranks = k["possible_ranks"]
            if len(colors) == 1 and len(ranks) == 1:
                color, rank = colors[0], ranks[0]
                if observation.stacks[color] + 1 == rank:
                    candidate = Action.play(i)
                    if candidate in legal_actions:
                        return AgentDecision(candidate)

        for a in legal_actions:
            if a.type == "hint" and a.attribute == "rank":
                return AgentDecision(a)

        for a in legal_actions:
            if a.type == "discard" and a.card_index == 0:
                return AgentDecision(a)

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
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")).rstrip("/")
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
            "messages": self._prompt(observation, legal_actions, private_instruction),
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
                raise ValueError(f"Model returned illegal action: {action.to_dict()}")
            return AgentDecision(action=action, raw_response=raw)
        except Exception as exc:
            return AgentDecision(
                action=legal_actions[0],
                raw_response=raw or None,
                parse_error=f"{type(exc).__name__}: {exc}",
                fallback_used=True,
            )
