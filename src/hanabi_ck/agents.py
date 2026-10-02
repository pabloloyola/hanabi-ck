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
    action_index: int | None = None
    raw_response: str | None = None
    response_channel: str | None = None
    api_response: dict[str, Any] | None = None
    parse_error: str | None = None
    fallback_used: bool = False


@dataclass
class IntentionProbeDecision:
    intended_card_index: int | None
    raw_response: str | None = None
    response_channel: str | None = None
    api_response: dict[str, Any] | None = None
    parse_error: str | None = None


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


def _select_response_text(message: dict[str, Any]) -> tuple[str, str]:
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content, "content"

    reasoning = message.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning, "reasoning_content"

    return "", "none"


def _action_from_index_object(
    data: dict[str, Any],
    legal_actions: list[Action],
) -> tuple[int, Action]:
    if set(data) != {"action_index"}:
        raise ValueError(
            "Model response must contain exactly one field: action_index"
        )

    action_index = data["action_index"]
    if isinstance(action_index, bool) or not isinstance(action_index, int):
        raise ValueError("action_index must be an integer")
    if not 0 <= action_index < len(legal_actions):
        raise ValueError(
            f"action_index {action_index} is outside legal range "
            f"[0, {len(legal_actions) - 1}]"
        )
    return action_index, legal_actions[action_index]


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
        max_tokens: int | None = None,
        extra_body: dict[str, Any] | None = None,
        structured_output: bool = False,
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
        self.max_tokens = max_tokens
        self.extra_body = dict(extra_body or {})
        self.structured_output = structured_output

    def _prompt(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> list[dict[str, str]]:
        system = """You are a Hanabi-playing research agent.
Choose exactly one action from the indexed legal_actions list.

BASE HANABI SEMANTICS:
- Your own cards are hidden. Use own_knowledge; never infer hidden cards from researcher state.
- A play succeeds only when rank == stacks[color] + 1.
- If rank <= stacks[color], that card is already obsolete and playing it is a misplay.
- A normal hint reveals information; it is not automatically a command to play.
- provably_playable_indices is computed only from your legal hint-derived knowledge
  and the public stacks. A normal play should use only an index in that list.
- provably_obsolete_indices contains cards that are certainly already played and
  should not be played.
- An experimental convention can tell you which card is intended, but intention
  does not make an unsafe card safe. If the convention says to play a card "as soon
  as it is safe", wait until that card is in provably_playable_indices.
- If no card is provably playable, prefer a legal hint or discard rather than an
  unjustified play.
- hand_order is oldest_to_newest. newest_card_index gives the newest current slot
  for every player.

The public_knowledge field records hint-derived knowledge visible to all players.
Never infer hidden state from the research setup.
Return ONLY JSON of the form {"action_index": N}. Do not explain your choice."""
        user = {
            "private_experimental_instruction": private_instruction,
            "observation": observation.to_dict(),
            "legal_actions": [
                {
                    "action_index": index,
                    "action": action.to_dict(),
                }
                for index, action in enumerate(legal_actions)
            ],
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ]

    def _request_payload(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._prompt(
                observation,
                legal_actions,
                private_instruction,
            ),
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        if self.structured_output:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "hanabi_action_selection",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "action_index": {
                                "type": "integer",
                                "enum": list(range(len(legal_actions))),
                            }
                        },
                        "required": ["action_index"],
                        "additionalProperties": False,
                    },
                },
            }

        reserved = {
            "model",
            "messages",
            "temperature",
            "max_tokens",
            "response_format",
        }
        collisions = reserved.intersection(self.extra_body)
        if collisions:
            names = ", ".join(sorted(collisions))
            raise ValueError(
                f"extra_body cannot override reserved request fields: {names}"
            )

        # Match OpenAI SDK extra_body semantics: vendor-specific values are
        # merged into the JSON request body, rather than sent under a literal
        # "extra_body" key.
        payload.update(self.extra_body)
        return payload

    def _intention_probe_prompt(
        self,
        observation: PlayerObservation,
        private_instruction: str,
        trigger_hint: dict[str, Any],
        candidate_card_indices: list[int],
    ) -> list[dict[str, str]]:
        system = """You are a shadow epistemic probe for a Hanabi experiment.
Infer which candidate card index the partner intended with the immediately
preceding hint. Do not choose a Hanabi action and do not explain your answer.
Use only the supplied observation, public history, and experimental instruction.
Return ONLY JSON of the form {"intended_card_index": N}."""
        user = {
            "private_experimental_instruction": private_instruction,
            "observation": observation.to_dict(),
            "trigger_hint": trigger_hint,
            "candidate_card_indices": candidate_card_indices,
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ]

    def _intention_probe_payload(
        self,
        observation: PlayerObservation,
        private_instruction: str,
        trigger_hint: dict[str, Any],
        candidate_card_indices: list[int],
    ) -> dict[str, Any]:
        if not candidate_card_indices:
            raise ValueError("candidate_card_indices must be non-empty")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._intention_probe_prompt(
                observation,
                private_instruction,
                trigger_hint,
                candidate_card_indices,
            ),
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        if self.structured_output:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "hanabi_intention_probe",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "intended_card_index": {
                                "type": "integer",
                                "enum": candidate_card_indices,
                            }
                        },
                        "required": ["intended_card_index"],
                        "additionalProperties": False,
                    },
                },
            }

        reserved = {
            "model",
            "messages",
            "temperature",
            "max_tokens",
            "response_format",
        }
        collisions = reserved.intersection(self.extra_body)
        if collisions:
            names = ", ".join(sorted(collisions))
            raise ValueError(
                f"extra_body cannot override reserved request fields: {names}"
            )

        payload.update(self.extra_body)
        return payload

    def probe_intended_card(
        self,
        observation: PlayerObservation,
        private_instruction: str,
        trigger_hint: dict[str, Any],
        candidate_card_indices: list[int],
    ) -> IntentionProbeDecision:
        raw = ""
        data: dict[str, Any] | None = None
        try:
            payload = self._intention_probe_payload(
                observation,
                private_instruction,
                trigger_hint,
                candidate_card_indices,
            )
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            message = data["choices"][0]["message"]
            raw, response_channel = _select_response_text(message)
            parsed = _extract_json_object(raw)

            if set(parsed) != {"intended_card_index"}:
                raise ValueError(
                    "Probe response must contain exactly intended_card_index"
                )
            intended = parsed["intended_card_index"]
            if isinstance(intended, bool) or not isinstance(intended, int):
                raise ValueError("intended_card_index must be an integer")
            if intended not in candidate_card_indices:
                raise ValueError(
                    f"intended_card_index {intended} is not a candidate"
                )

            return IntentionProbeDecision(
                intended_card_index=intended,
                raw_response=raw,
                response_channel=response_channel,
                api_response=data,
            )
        except Exception as exc:
            return IntentionProbeDecision(
                intended_card_index=None,
                raw_response=raw or None,
                response_channel=(
                    response_channel
                    if "response_channel" in locals()
                    else None
                ),
                api_response=data,
                parse_error=f"{type(exc).__name__}: {exc}",
            )

    def act(
        self,
        observation: PlayerObservation,
        legal_actions: list[Action],
        private_instruction: str,
    ) -> AgentDecision:
        payload = self._request_payload(
            observation,
            legal_actions,
            private_instruction,
        )
        headers = {"Authorization": f"Bearer {self.api_key}"}

        raw = ""
        data: dict[str, Any] | None = None
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            message = data["choices"][0]["message"]
            raw, response_channel = _select_response_text(message)

            parsed = _extract_json_object(raw)
            action_index, action = _action_from_index_object(
                parsed,
                legal_actions,
            )
            return AgentDecision(
                action=action,
                action_index=action_index,
                raw_response=raw,
                response_channel=response_channel,
                api_response=data,
            )
        except Exception as exc:
            return AgentDecision(
                action=None,
                raw_response=raw or None,
                response_channel=(
                    response_channel
                    if "response_channel" in locals()
                    else None
                ),
                api_response=data,
                parse_error=f"{type(exc).__name__}: {exc}",
                fallback_used=False,
            )
