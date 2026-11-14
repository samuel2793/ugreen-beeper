"""UGREEN NAS hardware buzzer control."""

from .core import Beep, Beeper, BeeperError, ProcfsBackend

__all__ = ["Beep", "Beeper", "BeeperError", "ProcfsBackend"]
__version__ = "0.1.0"
