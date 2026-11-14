"""Safe command construction and hardware backends for UGREEN beepers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

DEFAULT_DEVICE = Path("/proc/nas/beeper")
MAX_TOTAL_MS = 120_000


class BeeperError(RuntimeError):
    """A beeper operation could not be completed."""


@dataclass(frozen=True)
class Beep:
    """A single vendor `rep` operation; all durations are milliseconds."""

    count: int = 1
    duration_ms: int = 400
    interval_ms: int = 500

    def __post_init__(self) -> None:
        limits = (
            ("count", self.count, 1, 20),
            ("duration_ms", self.duration_ms, 10, 5_000),
            ("interval_ms", self.interval_ms, 0, 10_000),
        )
        for name, value, minimum, maximum in limits:
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(
                    f"{name} must be an integer between {minimum} and {maximum}"
                )
        estimated_ms = self.count * self.duration_ms + (self.count - 1) * self.interval_ms
        if estimated_ms > MAX_TOTAL_MS:
            raise ValueError(f"estimated signal duration exceeds {MAX_TOTAL_MS} ms")

    def command(self) -> str:
        return f"rep {self.count} {self.duration_ms} {self.interval_ms}"


class Backend(Protocol):
    """Interface for future hardware transports."""

    def send(self, beep: Beep) -> None:
        ...


@dataclass
class ProcfsBackend:
    """UGREEN vendor-kernel `/proc/nas/beeper` transport."""

    path: Path = DEFAULT_DEVICE

    def send(self, beep: Beep) -> None:
        if not self.path.exists():
            raise BeeperError(f"device {self.path} does not exist; check kernel support")
        try:
            # /proc entries implement writes; this file is not an ordinary file.
            with self.path.open("w", encoding="ascii") as stream:
                stream.write(beep.command() + "\n")
        except OSError as exc:
            raise BeeperError(
                f"unable to write to {self.path}: {exc}. "
                "Check kernel support and device permissions."
            ) from exc


class Beeper:
    """Public Python API; callers may supply their own Backend."""

    def __init__(self, backend: Optional[Backend] = None) -> None:
        self.backend = backend if backend is not None else ProcfsBackend()

    def beep(
        self,
        count: int = 1,
        duration_ms: int = 400,
        interval_ms: int = 500,
    ) -> Beep:
        operation = Beep(
            count=count,
            duration_ms=duration_ms,
            interval_ms=interval_ms,
        )
        self.backend.send(operation)
        return operation
