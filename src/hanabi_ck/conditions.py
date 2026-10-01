from __future__ import annotations

from dataclasses import dataclass


DEFAULT_CONVENTION = (
    "If a player gives a rank hint that touches the receiver's newest card, "
    "the receiver should interpret that newest card as intended to be played "
    "as soon as it is safe to do so."
)


@dataclass(frozen=True)
class Condition:
    name: str
    description: str

    def private_instruction(
        self,
        *,
        player_id: int,
        num_players: int,
        convention: str = DEFAULT_CONVENTION,
    ) -> str:
        del player_id, num_players

        if self.name == "ck0":
            return (
                "No extra team convention is supplied. Coordinate using only the Hanabi rules "
                "and the observed game history."
            )

        if self.name == "ck1_private":
            return (
                f"Private experimental convention:\n{convention}\n\n"
                "You are NOT told whether any other player received this convention. "
                "Do not assume that they did."
            )

        if self.name == "ck2_shared":
            return (
                f"Experimental convention:\n{convention}\n\n"
                "Use this convention. You receive no explicit information about what the "
                "other players were told."
            )

        if self.name == "ck3_mutual":
            return (
                f"Experimental convention:\n{convention}\n\n"
                "Every player was given this same convention, and you are explicitly told "
                "that every player was given it."
            )

        if self.name == "ck_inf_common":
            return (
                f"PUBLIC TEAM CONVENTION:\n{convention}\n\n"
                "This statement was publicly supplied to every player. Every player knows "
                "that every other player received it, everyone knows that everyone knows "
                "this, and the experiment declares the convention to be common knowledge."
            )

        raise KeyError(f"Unknown condition: {self.name}")


CONDITIONS = {
    "ck0": Condition("ck0", "No supplied convention."),
    "ck1_private": Condition("ck1_private", "Convention supplied privately."),
    "ck2_shared": Condition("ck2_shared", "Convention supplied to all, no meta-information."),
    "ck3_mutual": Condition("ck3_mutual", "Everyone is told everyone received it."),
    "ck_inf_common": Condition("ck_inf_common", "Convention explicitly declared common knowledge."),
}


def get_condition(name: str) -> Condition:
    try:
        return CONDITIONS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown condition {name!r}. Choose from {sorted(CONDITIONS)}") from exc
