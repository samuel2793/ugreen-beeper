"""Safe command construction and hardware backends for UGREEN beepers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

DEFAULT_DEVICE = Path("/proc/nas/beeper")
DEFAULT_FREQUENCY_DEVICE = Path("/sys/devices/platform/ug-beep/frequency_hz")
DEFAULT_FREQUENCY_MIN_DEVICE = Path("/sys/devices/platform/ug-beep/frequency_min_hz")
DEFAULT_FREQUENCY_MAX_DEVICE = Path("/sys/devices/platform/ug-beep/frequency_max_hz")
MAX_TOTAL_MS = 120_000


class BeeperError(RuntimeError):
    """A beeper operation could not be completed."""


class UnsupportedFrequencyError(BeeperError):
    """The selected transport cannot change the physical PWM frequency."""


@dataclass(frozen=True)
class BackendCapabilities:
    """Explicit hardware features exposed by one backend."""

    supports_frequency: bool = False
    frequency_range_hz: tuple[int, int] | None = None


@dataclass(frozen=True)
class Beep:
    """A single vendor `rep` operation; all durations are milliseconds."""

    count: int = 1
    duration_ms: int = 400
    interval_ms: int = 500
    frequency_hz: int | None = None

    def __post_init__(self) -> None:
        limits = (
            ("count", self.count, 1, 20),
            # The inspected vendor driver rejects either field below 20 ms,
            # even when count is one and the interval is not played.
            ("duration_ms", self.duration_ms, 20, 5_000),
            ("interval_ms", self.interval_ms, 20, 10_000),
        )
        for name, value, minimum, maximum in limits:
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(
                    f"{name} must be an integer between {minimum} and {maximum}"
                )
        if self.frequency_hz is not None and (
            type(self.frequency_hz) is not int or self.frequency_hz <= 0
        ):
            raise ValueError("frequency_hz must be a positive integer or None")
        estimated_ms = self.count * self.duration_ms + (self.count - 1) * self.interval_ms
        if estimated_ms > MAX_TOTAL_MS:
            raise ValueError(f"estimated signal duration exceeds {MAX_TOTAL_MS} ms")

    def command(self) -> str:
        return f"rep {self.count} {self.duration_ms} {self.interval_ms}"


class Backend(Protocol):
    """Interface for future hardware transports."""

    capabilities: BackendCapabilities

    def send(self, beep: Beep) -> None:
        ...


@dataclass
class ProcfsBackend:
    """UGREEN vendor-kernel `/proc/nas/beeper` transport."""

    path: Path = DEFAULT_DEVICE
    capabilities = BackendCapabilities()

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


@dataclass
class SysfsFrequencyProcfsBackend(ProcfsBackend):
    """Frequency-capable extension for a patched ``ug_beep`` driver.

    The driver, not this userspace library, remains the exclusive PWM owner.
    It must expose the three documented sysfs attributes.  Their absence is
    treated as no frequency support, which keeps this backend safe on stock
    UGREEN kernels.
    """

    frequency_path: Path = DEFAULT_FREQUENCY_DEVICE
    frequency_min_path: Path = DEFAULT_FREQUENCY_MIN_DEVICE
    frequency_max_path: Path = DEFAULT_FREQUENCY_MAX_DEVICE

    @property
    def capabilities(self) -> BackendCapabilities:
        try:
            minimum = self._read_limit(self.frequency_min_path)
            maximum = self._read_limit(self.frequency_max_path)
        except BeeperError:
            return BackendCapabilities()
        if minimum <= 0 or maximum < minimum or not self.frequency_path.exists():
            return BackendCapabilities()
        return BackendCapabilities(True, (minimum, maximum))

    @staticmethod
    def _read_limit(path: Path) -> int:
        try:
            text = path.read_text(encoding="ascii").strip()
        except OSError as exc:
            raise BeeperError(f"cannot read frequency capability {path}: {exc}") from exc
        try:
            value = int(text)
        except ValueError as exc:
            raise BeeperError(f"invalid frequency capability in {path}: {text!r}") from exc
        return value

    def send(self, beep: Beep) -> None:
        if beep.frequency_hz is not None:
            capabilities = self.capabilities
            if not capabilities.supports_frequency:
                raise UnsupportedFrequencyError(
                    "frequency sysfs interface is unavailable; install the compatible "
                    "ug_beep driver extension before requesting a frequency"
                )
            try:
                with self.frequency_path.open("w", encoding="ascii") as stream:
                    stream.write(f"{beep.frequency_hz}\n")
            except OSError as exc:
                raise BeeperError(
                    f"unable to write frequency to {self.frequency_path}: {exc}"
                ) from exc
        super().send(beep)


class Beeper:
    """Public Python API; callers may supply their own Backend."""

    def __init__(self, backend: Optional[Backend] = None) -> None:
        self.backend = backend if backend is not None else ProcfsBackend()

    @property
    def capabilities(self) -> BackendCapabilities:
        """Capabilities of the selected backend.

        Legacy third-party backends without this attribute are treated
        conservatively as supporting no optional features.
        """
        return getattr(self.backend, "capabilities", BackendCapabilities())

    def validate(self, operation: Beep) -> None:
        """Reject requests that the selected backend would ignore."""
        frequency_hz = operation.frequency_hz
        if frequency_hz is None:
            return
        capabilities = self.capabilities
        if not capabilities.supports_frequency:
            raise UnsupportedFrequencyError(
                "frequency control is not supported by this backend; "
                "the UGREEN procfs driver only accepts count, duration and interval"
            )
        if capabilities.frequency_range_hz is not None:
            minimum, maximum = capabilities.frequency_range_hz
            if not minimum <= frequency_hz <= maximum:
                raise UnsupportedFrequencyError(
                    f"frequency {frequency_hz} Hz is outside this backend's "
                    f"supported range ({minimum}–{maximum} Hz)"
                )

    def beep(
        self,
        count: int = 1,
        duration_ms: int = 400,
        interval_ms: int = 500,
        frequency_hz: int | None = None,
    ) -> Beep:
        operation = Beep(
            count=count,
            duration_ms=duration_ms,
            interval_ms=interval_ms,
            frequency_hz=frequency_hz,
        )
        self.validate(operation)
        self.backend.send(operation)
        return operation
