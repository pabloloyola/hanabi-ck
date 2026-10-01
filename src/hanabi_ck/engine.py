from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .actions import Action
from .observations import COLORS, CardKnowledge, PlayerObservation


@dataclass(frozen=True)
class Card:
    color: str
    rank: int

    def to_dict(self) -> dict[str, Any]:
        return {"color": self.color, "rank": self.rank}


@dataclass(frozen=True)
class StepResult:
    action: Action
    outcome: dict[str, Any]
    done: bool


def standard_deck() -> list[Card]:
    multiplicity = {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}
    return [
        Card(color, rank)
        for color in COLORS
        for rank, count in multiplicity.items()
        for _ in range(count)
    ]


class HanabiGame:
    def __init__(self, num_players: int = 2, seed: int = 0):
        if not 2 <= num_players <= 5:
            raise ValueError("num_players must be in [2, 5]")
        self.num_players = num_players
        self.seed = seed
        self.rng = random.Random(seed)

        self.deck = standard_deck()
        self.rng.shuffle(self.deck)

        self.hand_size = 5 if num_players <= 3 else 4
        self.hands: list[list[Card]] = [[] for _ in range(num_players)]
        self.knowledge: list[list[CardKnowledge]] = [[] for _ in range(num_players)]
        for _ in range(self.hand_size):
            for p in range(num_players):
                self._draw(p)

        self.stacks = {c: 0 for c in COLORS}
        self.discards: list[Card] = []
        self.information_tokens = 8
        self.life_tokens = 3
        self.current_player = 0
        self.history: list[dict[str, Any]] = []
        self.final_turns_remaining: int | None = None
        self.done = False

    @property
    def score(self) -> int:
        return sum(self.stacks.values())

    def _draw(self, player: int) -> Card | None:
        if not self.deck:
            return None
        card = self.deck.pop()
        self.hands[player].append(card)
        self.knowledge[player].append(CardKnowledge())
        if not self.deck and self.final_turns_remaining is None:
            # The action that draws the final card does not itself consume one
            # of the final turns. Each player gets one more turn afterward.
            self.final_turns_remaining = self.num_players
        return card

    def observe(self, player: int) -> PlayerObservation:
        other_hands = {
            p: [c.to_dict() for c in hand]
            for p, hand in enumerate(self.hands)
            if p != player
        }
        public_knowledge = {
            p: [k.to_dict() for k in hand_knowledge]
            for p, hand_knowledge in enumerate(self.knowledge)
        }
        return PlayerObservation(
            player_id=player,
            current_player=self.current_player,
            other_hands=other_hands,
            own_knowledge=public_knowledge[player],
            public_knowledge=public_knowledge,
            stacks=dict(self.stacks),
            discards=[c.to_dict() for c in self.discards],
            information_tokens=self.information_tokens,
            life_tokens=self.life_tokens,
            deck_size=len(self.deck),
            final_turns_remaining=self.final_turns_remaining,
            history=list(self.history),
        )

    def true_state(self) -> dict[str, Any]:
        return {
            "hands": [[c.to_dict() for c in hand] for hand in self.hands],
            "deck": [c.to_dict() for c in self.deck],
            "stacks": dict(self.stacks),
            "discards": [c.to_dict() for c in self.discards],
            "information_tokens": self.information_tokens,
            "life_tokens": self.life_tokens,
            "current_player": self.current_player,
            "final_turns_remaining": self.final_turns_remaining,
            "score": self.score,
        }

    def legal_actions(self, player: int | None = None) -> list[Action]:
        if self.done:
            return []
        if player is None:
            player = self.current_player
        if player != self.current_player:
            return []

        actions: list[Action] = []
        for i in range(len(self.hands[player])):
            actions.append(Action.play(i))
            if self.information_tokens < 8:
                actions.append(Action.discard(i))

        if self.information_tokens > 0:
            for target in range(self.num_players):
                if target == player:
                    continue
                colors = sorted({c.color for c in self.hands[target]})
                ranks = sorted({c.rank for c in self.hands[target]})
                actions.extend(Action.hint(target, "color", c) for c in colors)
                actions.extend(Action.hint(target, "rank", r) for r in ranks)
        return actions

    def _validate(self, action: Action) -> None:
        if action not in self.legal_actions():
            raise ValueError(f"Illegal action: {action.to_dict()}")

    def _remove_and_draw(self, player: int, card_index: int) -> Card:
        card = self.hands[player].pop(card_index)
        self.knowledge[player].pop(card_index)
        self._draw(player)
        return card

    def step(self, action: Action) -> StepResult:
        if self.done:
            raise RuntimeError("Game is already over")
        self._validate(action)
        actor = self.current_player
        final_round_was_already_active = self.final_turns_remaining is not None

        outcome: dict[str, Any] = {
            "actor": actor,
            "score_before": self.score,
            "life_tokens_before": self.life_tokens,
            "information_tokens_before": self.information_tokens,
        }

        if action.type == "play":
            assert action.card_index is not None
            card = self._remove_and_draw(actor, action.card_index)
            playable = self.stacks[card.color] + 1 == card.rank
            outcome["card"] = card.to_dict()
            outcome["play_success"] = playable
            if playable:
                self.stacks[card.color] = card.rank
                if card.rank == 5 and self.information_tokens < 8:
                    self.information_tokens += 1
            else:
                self.discards.append(card)
                self.life_tokens -= 1

        elif action.type == "discard":
            assert action.card_index is not None
            card = self._remove_and_draw(actor, action.card_index)
            self.discards.append(card)
            self.information_tokens = min(8, self.information_tokens + 1)
            outcome["card"] = card.to_dict()

        elif action.type == "hint":
            assert action.target is not None
            assert action.attribute is not None
            target = action.target
            self.information_tokens -= 1
            touched: list[int] = []
            for i, card in enumerate(self.hands[target]):
                if action.attribute == "color":
                    matches = card.color == action.value
                    self.knowledge[target][i].apply_color_hint(str(action.value), matches)
                else:
                    matches = card.rank == int(action.value)
                    self.knowledge[target][i].apply_rank_hint(int(action.value), matches)
                if matches:
                    touched.append(i)
            outcome["touched_indices"] = touched

        event = {
            "turn": len(self.history),
            "actor": actor,
            "action": action.to_dict(),
            "outcome": dict(outcome),
        }
        self.history.append(event)

        if self.score == 25:
            self.done = True
            outcome["terminal_reason"] = "perfect"
        elif self.life_tokens <= 0:
            self.done = True
            outcome["terminal_reason"] = "lives_exhausted"
        else:
            if final_round_was_already_active and self.final_turns_remaining is not None:
                self.final_turns_remaining -= 1
                if self.final_turns_remaining <= 0:
                    self.done = True
                    outcome["terminal_reason"] = "deck_exhausted"
            if not self.done:
                self.current_player = (self.current_player + 1) % self.num_players

        outcome.update(
            {
                "score_after": self.score,
                "life_tokens_after": self.life_tokens,
                "information_tokens_after": self.information_tokens,
            }
        )
        return StepResult(action=action, outcome=outcome, done=self.done)
