"""Named notifications stored in a deliberately small JSON schema."""

import json
from pathlib import Path

from .core import Beep


class EventConfigError(ValueError):
    """An event definition is absent or malformed."""


def load_event(config_file: Path, name: str) -> Beep:
    """Load a single beep operation from {"events": {"name": {...}}}."""
    try:
        with config_file.open("r", encoding="utf-8") as stream:
            config = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EventConfigError(f"cannot read event configuration {config_file}: {exc}") from exc

    if not isinstance(config, dict) or not isinstance(config.get("events"), dict):
        raise EventConfigError("configuration must contain an 'events' object")

    events = config["events"]
    if name not in events:
        available = ", ".join(sorted(events)) or "(none)"
        raise EventConfigError(f"unknown event '{name}'; available events: {available}")

    settings = events[name]
    allowed = {"count", "duration_ms", "interval_ms"}
    if not isinstance(settings, dict) or not settings or not set(settings).issubset(allowed):
        raise EventConfigError(
            f"event '{name}' must contain only count, duration_ms and interval_ms"
        )
    try:
        return Beep(**settings)
    except (ValueError, TypeError) as exc:
        raise EventConfigError(f"invalid event '{name}': {exc}") from exc
