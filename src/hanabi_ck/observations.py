from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


COLORS = ("R", "G", "B", "Y", "W")
RANKS = (1, 2, 3, 4, 5)


def is_provably_playable(
    knowledge: dict[str, Any],
    stacks: dict[str, int],
) -> bool:
    """True iff every card identity consistent with knowledge is playable."""
    colors = knowledge["possible_colors"]
    ranks = knowledge["possible_ranks"]
    return bool(colors and ranks) and all(
        stacks[color] + 1 == rank
        for color in colors
        for rank in ranks
    )


def is_provably_obsolete(
    knowledge: dict[str, Any],
    stacks: dict[str, int],
) -> bool:
    """True iff every card identity consistent with knowledge is already played."""
    colors = knowledge["possible_colors"]
    ranks = knowledge["possible_ranks"]
    return bool(colors and ranks) and all(
        rank <= stacks[color]
        for color in colors
        for rank in ranks
    )


def play_safety_annotations(
    own_knowledge: list[dict[str, Any]],
    stacks: dict[str, int],
) -> tuple[list[int], list[int], dict[int, str]]:
    playable: list[int] = []
    obsolete: list[int] = []
    status: dict[int, str] = {}

    for index, knowledge in enumerate(own_knowledge):
        if is_provably_playable(knowledge, stacks):
            playable.append(index)
            status[index] = "provably_safe"
        elif is_provably_obsolete(knowledge, stacks):
            obsolete.append(index)
            status[index] = "provably_obsolete"
        else:
            status[index] = "not_proven_safe"

    return playable, obsolete, status


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
    public_knowledge: dict[int, list[dict[str, Any]]]
    hand_order: str
    newest_card_index: dict[int, int | None]
    provably_playable_indices: list[int]
    provably_obsolete_indices: list[int]
    play_safety: dict[int, str]
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
            "public_knowledge": self.public_knowledge,
            "hand_order": self.hand_order,
            "newest_card_index": self.newest_card_index,
            "provably_playable_indices": self.provably_playable_indices,
            "provably_obsolete_indices": self.provably_obsolete_indices,
            "play_safety": self.play_safety,
            "stacks": self.stacks,
            "discards": self.discards,
            "information_tokens": self.information_tokens,
            "life_tokens": self.life_tokens,
            "deck_size": self.deck_size,
            "final_turns_remaining": self.final_turns_remaining,
            "history": self.history,
        }
