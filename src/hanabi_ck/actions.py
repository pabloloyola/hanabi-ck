from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ActionType = Literal["play", "discard", "hint"]


@dataclass(frozen=True)
class Action:
    type: ActionType
    card_index: int | None = None
    target: int | None = None
    attribute: Literal["color", "rank"] | None = None
    value: str | int | None = None

    @staticmethod
    def play(card_index: int) -> "Action":
        return Action(type="play", card_index=card_index)

    @staticmethod
    def discard(card_index: int) -> "Action":
        return Action(type="discard", card_index=card_index)

    @staticmethod
    def hint(target: int, attribute: str, value: str | int) -> "Action":
        if attribute not in {"color", "rank"}:
            raise ValueError("attribute must be 'color' or 'rank'")
        return Action(type="hint", target=target, attribute=attribute, value=value)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type}
        if self.card_index is not None:
            out["card_index"] = self.card_index
        if self.target is not None:
            out["target"] = self.target
        if self.attribute is not None:
            out["attribute"] = self.attribute
        if self.value is not None:
            out["value"] = self.value
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        typ = data.get("type")
        if typ == "play":
            return cls.play(int(data["card_index"]))
        if typ == "discard":
            return cls.discard(int(data["card_index"]))
        if typ == "hint":
            return cls.hint(
                int(data["target"]),
                str(data["attribute"]),
                data["value"],
            )
        raise ValueError(f"Unknown action type: {typ!r}")
