from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


COLORS = ("R", "G", "B", "Y", "W")
RANKS = (1, 2, 3, 4, 5)


@dataclass
class CardKnowledge:
    possible_colors: set[str] = field(default_factory=lambda: set(COLORS))
    possible_ranks: set[int] = field(default_factory=lambda: set(RANKS))

    def apply_color_hint(self, color: str, matches: bool) -> None:
        if matches:
            self.possible_colors.intersection_update({color})
        else:
            self.possible_colors.discard(color)

    def apply_rank_hint(self, rank: int, matches: bool) -> None:
        if matches:
            self.possible_ranks.intersection_update({rank})
        else:
            self.possible_ranks.discard(rank)

    def to_dict(self) -> dict[str, Any]:
        return {
            "possible_colors": sorted(self.possible_colors),
            "possible_ranks": sorted(self.possible_ranks),
        }


@dataclass(frozen=True)
class PlayerObservation:
    player_id: int
    current_player: int
    other_hands: dict[int, list[dict[str, Any]]]
    own_knowledge: list[dict[str, Any]]
    stacks: dict[str, int]
    discards: list[dict[str, Any]]
    information_tokens: int
    life_tokens: int
    deck_size: int
    final_turns_remaining: int | None
    history: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "current_player": self.current_player,
            "other_hands": self.other_hands,
            "own_knowledge": self.own_knowledge,
            "stacks": self.stacks,
            "discards": self.discards,
            "information_tokens": self.information_tokens,
            "life_tokens": self.life_tokens,
            "deck_size": self.deck_size,
            "final_turns_remaining": self.final_turns_remaining,
            "history": self.history,
        }
