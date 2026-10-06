from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..actions import Action
from ..engine import StepResult
from ..observations import PlayerObservation


@runtime_checkable
class HanabiBackend(Protocol):
    """Minimal game-engine contract used by full-game experiment runners.

    Backends own physical Hanabi state and mechanical card knowledge only.
    Epistemic treatments (CK0/CK1/CK2/CK3/CK∞) remain outside this interface.
    """

    num_players: int
    seed: int

    @property
    def current_player(self) -> int:
        """Player to act while done is False.

        Backends may retain different internal cursors after terminal state;
        callers must not treat current_player as meaningful once done is True.
        """
        ...

    @property
    def done(self) -> bool:
        ...

    @property
    def score(self) -> int:
        ...

    def observe(self, player: int) -> PlayerObservation:
        ...

    def legal_actions(self, player: int | None = None) -> list[Action]:
        ...

    def step(self, action: Action) -> StepResult:
        ...

    def true_state(self) -> dict:
        ...
