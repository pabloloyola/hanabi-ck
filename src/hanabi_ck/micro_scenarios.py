from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .actions import Action
from .observations import COLORS, RANKS, PlayerObservation, play_safety_annotations


@dataclass(frozen=True)
class MicroScenario:
    name: str
    description: str
    num_players: int
    acting_player: int
    observation: PlayerObservation
    legal_actions: tuple[Action, ...]
    target_action: Action
    diagnostic_safe_card_indices: tuple[int, ...]
    trigger_hint: dict[str, Any]
    researcher_truth: dict[str, Any]

    def validate(self) -> None:
        if self.target_action not in self.legal_actions:
            raise ValueError("target_action must be legal")
        if self.target_action.type != "play":
            raise ValueError("starter micro scenario target must be a play")
        if self.target_action.card_index is None:
            raise ValueError("play target must have a card index")

        target = self.target_action.card_index
        if target != self.observation.newest_card_index[self.acting_player]:
            raise ValueError("target_action must play the acting player's newest card")
        if target not in self.observation.provably_playable_indices:
            raise ValueError("target newest card must be provably playable")

        candidates = set(self.diagnostic_safe_card_indices)
        if target not in candidates:
            raise ValueError("target must be one of the diagnostic safe cards")
        if len(candidates) < 2:
            raise ValueError("micro scenario needs at least two safe candidate plays")
        if not candidates.issubset(set(self.observation.provably_playable_indices)):
            raise ValueError("all diagnostic candidates must be provably playable")

        touched = set(self.trigger_hint["touched_indices"])
        if not candidates.issubset(touched):
            raise ValueError("all diagnostic candidates must be touched by the trigger hint")


def _knowledge(
    *,
    colors: tuple[str, ...] | list[str] = COLORS,
    ranks: tuple[int, ...] | list[int] = RANKS,
) -> dict[str, Any]:
    return {
        "possible_colors": sorted(colors),
        "possible_ranks": sorted(ranks),
    }


def _legal_actions_for_visible_hand(
    visible_hand: list[dict[str, Any]],
    *,
    target: int,
    information_tokens: int,
    hand_size: int,
) -> tuple[Action, ...]:
    actions: list[Action] = []
    for index in range(hand_size):
        actions.append(Action.play(index))
        if information_tokens < 8:
            actions.append(Action.discard(index))

    if information_tokens > 0:
        colors = sorted({str(card["color"]) for card in visible_hand})
        ranks = sorted({int(card["rank"]) for card in visible_hand})
        actions.extend(Action.hint(target, "color", color) for color in colors)
        actions.extend(Action.hint(target, "rank", rank) for rank in ranks)
    return tuple(actions)


def newest_rank1_three_safe() -> MicroScenario:
    """One-step receiver decision after a rank-1 hint touches three safe cards.

    This reproduces the clean decision pattern observed in the first full-game
    debug seed: the receiver has three cards known to be rank 1, including the
    newest card. All three are provably playable because every stack is at 0.
    The experimental convention, when available, designates the newest touched
    card as intended while holding physical safety constant.
    """
    acting_player = 1
    sender_hand = [
        {"color": "B", "rank": 2},
        {"color": "B", "rank": 3},
        {"color": "G", "rank": 3},
        {"color": "Y", "rank": 1},
        {"color": "G", "rank": 5},
    ]
    acting_hand_truth = [
        {"color": "W", "rank": 4},
        {"color": "R", "rank": 1},
        {"color": "Y", "rank": 1},
        {"color": "B", "rank": 3},
        {"color": "Y", "rank": 1},
    ]

    full = _knowledge()
    not_rank1 = _knowledge(ranks=(2, 3, 4, 5))
    rank1 = _knowledge(ranks=(1,))

    p0_knowledge = [dict(full) for _ in range(5)]
    p1_knowledge = [
        dict(not_rank1),
        dict(rank1),
        dict(rank1),
        dict(not_rank1),
        dict(rank1),
    ]
    public_knowledge = {
        0: p0_knowledge,
        1: p1_knowledge,
    }
    stacks = {color: 0 for color in COLORS}
    playable, obsolete, safety = play_safety_annotations(p1_knowledge, stacks)

    trigger_hint = {
        "actor": 0,
        "target": 1,
        "attribute": "rank",
        "value": 1,
        "touched_indices": [1, 2, 4],
    }
    history = [
        {
            "turn": 0,
            "actor": 0,
            "action": {
                "type": "hint",
                "target": 1,
                "attribute": "rank",
                "value": 1,
            },
            "outcome": {
                "actor": 0,
                "score_before": 0,
                "score_after": 0,
                "life_tokens_before": 3,
                "life_tokens_after": 3,
                "information_tokens_before": 8,
                "information_tokens_after": 7,
                "touched_indices": [1, 2, 4],
            },
        }
    ]

    observation = PlayerObservation(
        player_id=acting_player,
        current_player=acting_player,
        other_hands={0: sender_hand},
        own_knowledge=p1_knowledge,
        public_knowledge=public_knowledge,
        hand_order="oldest_to_newest",
        newest_card_index={0: 4, 1: 4},
        provably_playable_indices=playable,
        provably_obsolete_indices=obsolete,
        play_safety=safety,
        stacks=stacks,
        discards=[],
        information_tokens=7,
        life_tokens=3,
        deck_size=40,
        final_turns_remaining=None,
        history=history,
    )
    legal_actions = _legal_actions_for_visible_hand(
        sender_hand,
        target=0,
        information_tokens=7,
        hand_size=5,
    )

    scenario = MicroScenario(
        name="newest_rank1_three_safe",
        description=(
            "After P0 gives rank=1 touching P1 cards 1, 2, and newest card 4, "
            "all three touched cards are provably safe. The diagnostic target "
            "is whether P1 selects the newest safe card."
        ),
        num_players=2,
        acting_player=acting_player,
        observation=observation,
        legal_actions=legal_actions,
        target_action=Action.play(4),
        diagnostic_safe_card_indices=(1, 2, 4),
        trigger_hint=trigger_hint,
        researcher_truth={
            "acting_hand": acting_hand_truth,
            "sender_hand": sender_hand,
        },
    )
    scenario.validate()
    return scenario


SCENARIOS = {
    "newest_rank1_three_safe": newest_rank1_three_safe,
}


def get_micro_scenario(name: str) -> MicroScenario:
    try:
        return SCENARIOS[name]()
    except KeyError as exc:
        raise ValueError(
            f"Unknown micro scenario {name!r}. Choose from {sorted(SCENARIOS)}"
        ) from exc
