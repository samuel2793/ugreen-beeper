"""UGREEN NAS hardware buzzer control."""

from .core import (
    BackendCapabilities,
    Beep,
    Beeper,
    BeeperError,
    ProcfsBackend,
    UnsupportedFrequencyError,
)

__all__ = [
    "BackendCapabilities", "Beep", "Beeper", "BeeperError", "ProcfsBackend",
    "UnsupportedFrequencyError",
]
__version__ = "0.2.0"
