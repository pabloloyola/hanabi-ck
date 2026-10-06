from __future__ import annotations

from ..engine import HanabiGame


class NativeHanabiBackend(HanabiGame):
    """The existing pure-Python engine exposed through the backend interface.

    Keeping this as a thin subclass is deliberate: current experiments retain
    exactly the existing engine behavior while runners gain a replaceable
    backend boundary.
    """

    pass
