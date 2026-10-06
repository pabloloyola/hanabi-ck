from __future__ import annotations

from typing import Any

from ..actions import Action
from ..engine import StepResult
from ..observations import PlayerObservation, play_safety_annotations


def _load_pyhanabi():
    try:
        from hanabi_learning_environment import pyhanabi
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "The HLE backend requires DeepMind's hanabi-learning-environment. "
            "Install the optional reference engine as documented in README.md."
        ) from exc
    return pyhanabi


class HLEHanabiBackend:
    """Adapter around DeepMind's canonical pyhanabi implementation.

    This backend is intended for standard full-game trajectories and mechanical
    parity checks. It does not support arbitrary injected mid-game microstates;
    those remain a capability of the native experimental engine.
    """

    def __init__(self, num_players: int = 2, seed: int = 0):
        if not 2 <= num_players <= 5:
            raise ValueError("num_players must be in [2, 5]")

        self.num_players = num_players
        self.seed = seed
        self._pyhanabi = _load_pyhanabi()
        self._game = self._pyhanabi.HanabiGame(
            {
                "players": num_players,
                "seed": seed,
                "random_start_player": False,
                "observation_type": int(
                    self._pyhanabi.AgentObservationType.CARD_KNOWLEDGE
                ),
            }
        )
        self._state = self._game.new_initial_state()
        self.history: list[dict[str, Any]] = []
        self.final_turns_remaining: int | None = None
        self._resolve_chance()

    @property
    def current_player(self) -> int:
        return int(self._state.cur_player())

    @property
    def done(self) -> bool:
        return bool(self._state.is_terminal())

    @property
    def score(self) -> int:
        # HLE documents StateScore as undefined before terminal state and some
        # variants collapse score after life-out. Firework sum is the physical
        # score used by hanabi-ck throughout a trajectory.
        return sum(self._stacks().values())

    @property
    def hand_size(self) -> int:
        return int(self._game.hand_size())

    def _resolve_chance(self) -> None:
        while self._state.cur_player() == self._pyhanabi.CHANCE_PLAYER_ID:
            self._state.deal_random_card()

    def _card_to_dict(self, card) -> dict[str, Any]:
        return {
            "color": self._pyhanabi.color_idx_to_char(card.color()),
            "rank": int(card.rank()) + 1,
        }

    def _stacks(self) -> dict[str, int]:
        return {
            color: int(level)
            for color, level in zip(
                self._pyhanabi.COLOR_CHAR,
                self._state.fireworks(),
            )
        }

    def _own_knowledge(self, player: int) -> list[dict[str, Any]]:
        observation = self._state.observation(player)
        # HLE observations are relative to the observer, so slot 0 is always
        # the observing player's own hand.
        knowledge = observation.card_knowledge()[0]
        colors = list(self._pyhanabi.COLOR_CHAR)
        num_ranks = int(self._game.num_ranks())
        out: list[dict[str, Any]] = []
        for item in knowledge:
            out.append(
                {
                    "possible_colors": [
                        color
                        for color_index, color in enumerate(colors)
                        if item.color_plausible(color_index)
                    ],
                    "possible_ranks": [
                        rank_index + 1
                        for rank_index in range(num_ranks)
                        if item.rank_plausible(rank_index)
                    ],
                }
            )
        return out

    def _all_hands(self) -> list[list[dict[str, Any]]]:
        return [
            [self._card_to_dict(card) for card in hand]
            for hand in self._state.player_hands()
        ]

    def observe(self, player: int) -> PlayerObservation:
        if not 0 <= player < self.num_players:
            raise ValueError(f"player must be in [0, {self.num_players - 1}]")

        hands = self._all_hands()
        public_knowledge = {
            p: self._own_knowledge(p)
            for p in range(self.num_players)
        }
        own_knowledge = public_knowledge[player]
        stacks = self._stacks()
        playable, obsolete, safety = play_safety_annotations(
            own_knowledge,
            stacks,
        )

        return PlayerObservation(
            player_id=player,
            current_player=self.current_player,
            other_hands={
                p: hand
                for p, hand in enumerate(hands)
                if p != player
            },
            own_knowledge=own_knowledge,
            public_knowledge=public_knowledge,
            hand_order="oldest_to_newest",
            newest_card_index={
                p: (len(hand) - 1 if hand else None)
                for p, hand in enumerate(hands)
            },
            provably_playable_indices=playable,
            provably_obsolete_indices=obsolete,
            play_safety=safety,
            stacks=stacks,
            discards=[
                self._card_to_dict(card)
                for card in self._state.discard_pile()
            ],
            information_tokens=int(self._state.information_tokens()),
            life_tokens=int(self._state.life_tokens()),
            deck_size=int(self._state.deck_size()),
            final_turns_remaining=self.final_turns_remaining,
            history=list(self.history),
        )

    def _move_to_action(self, move) -> Action:
        typ = move.type()
        move_types = self._pyhanabi.HanabiMoveType
        if typ == move_types.PLAY:
            return Action.play(int(move.card_index()))
        if typ == move_types.DISCARD:
            return Action.discard(int(move.card_index()))
        if typ == move_types.REVEAL_COLOR:
            target = (self.current_player + int(move.target_offset())) % self.num_players
            return Action.hint(
                target,
                "color",
                self._pyhanabi.color_idx_to_char(move.color()),
            )
        if typ == move_types.REVEAL_RANK:
            target = (self.current_player + int(move.target_offset())) % self.num_players
            return Action.hint(target, "rank", int(move.rank()) + 1)
        raise ValueError(f"Unsupported HLE player move type: {typ}")

    def legal_actions(self, player: int | None = None) -> list[Action]:
        if self.done:
            return []
        if player is None:
            player = self.current_player
        if player != self.current_player:
            return []
        return [self._move_to_action(move) for move in self._state.legal_moves()]

    def _find_hle_move(self, action: Action):
        for move in self._state.legal_moves():
            if self._move_to_action(move) == action:
                return move
        raise ValueError(f"Illegal action: {action.to_dict()}")

    def true_state(self) -> dict[str, Any]:
        return {
            "backend": "hle",
            "hands": self._all_hands(),
            # pyhanabi exposes deck size but not the remaining deck identities.
            "deck": None,
            "deck_size": int(self._state.deck_size()),
            "stacks": self._stacks(),
            "discards": [
                self._card_to_dict(card)
                for card in self._state.discard_pile()
            ],
            "information_tokens": int(self._state.information_tokens()),
            "life_tokens": int(self._state.life_tokens()),
            "current_player": (
                None if self.done else self.current_player
            ),
            "final_turns_remaining": self.final_turns_remaining,
            "score": self.score,
        }

    def step(self, action: Action) -> StepResult:
        if self.done:
            raise RuntimeError("Game is already over")

        hle_move = self._find_hle_move(action)
        actor = self.current_player
        stacks_before = self._stacks()
        hands_before = self._all_hands()
        deck_size_before = int(self._state.deck_size())
        final_round_was_already_active = self.final_turns_remaining is not None

        outcome: dict[str, Any] = {
            "actor": actor,
            "score_before": self.score,
            "life_tokens_before": int(self._state.life_tokens()),
            "information_tokens_before": int(self._state.information_tokens()),
        }

        if action.type in {"play", "discard"}:
            assert action.card_index is not None
            card = hands_before[actor][action.card_index]
            outcome["card"] = dict(card)
            if action.type == "play":
                outcome["play_success"] = (
                    stacks_before[card["color"]] + 1 == card["rank"]
                )
        elif action.type == "hint":
            assert action.target is not None
            assert action.attribute is not None
            touched: list[int] = []
            for index, card in enumerate(hands_before[action.target]):
                if action.attribute == "color":
                    matches = card["color"] == str(action.value)
                else:
                    matches = card["rank"] == int(action.value)
                if matches:
                    touched.append(index)
            outcome["touched_indices"] = touched

        event = {
            "turn": len(self.history),
            "actor": actor,
            "action": action.to_dict(),
            "outcome": dict(outcome),
        }
        self.history.append(event)

        self._state.apply_move(hle_move)
        self._resolve_chance()

        if (
            deck_size_before > 0
            and self._state.deck_size() == 0
            and self.final_turns_remaining is None
        ):
            # The action that drew the final card does not consume one of the
            # final turns; each player gets one more turn afterward.
            self.final_turns_remaining = self.num_players
        elif (
            final_round_was_already_active
            and self.final_turns_remaining is not None
        ):
            self.final_turns_remaining -= 1

        if self.score == 25:
            outcome["terminal_reason"] = "perfect"
        elif self._state.life_tokens() <= 0:
            outcome["terminal_reason"] = "lives_exhausted"
        elif self.done:
            outcome["terminal_reason"] = "deck_exhausted"

        outcome.update(
            {
                "score_after": self.score,
                "life_tokens_after": int(self._state.life_tokens()),
                "information_tokens_after": int(
                    self._state.information_tokens()
                ),
            }
        )
        return StepResult(action=action, outcome=outcome, done=self.done)
