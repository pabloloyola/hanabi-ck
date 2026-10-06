from __future__ import annotations

from .base import HanabiBackend
from .native import NativeHanabiBackend


BACKEND_NAMES = {"native", "hle"}


def create_backend(
    name: str,
    *,
    num_players: int,
    seed: int,
) -> HanabiBackend:
    """Construct a full-game Hanabi backend.

    The DeepMind HLE dependency is imported lazily so the default native
    backend remains dependency-free.
    """
    normalized = name.strip().lower()
    if normalized == "native":
        return NativeHanabiBackend(num_players=num_players, seed=seed)
    if normalized == "hle":
        from .hle import HLEHanabiBackend

        return HLEHanabiBackend(num_players=num_players, seed=seed)
    raise ValueError(
        f"Unknown backend {name!r}; choose from {sorted(BACKEND_NAMES)}"
    )


__all__ = [
    "BACKEND_NAMES",
    "HanabiBackend",
    "NativeHanabiBackend",
    "create_backend",
]
