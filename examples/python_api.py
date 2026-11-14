"""Run this after installing the package into your Python environment."""

from ugreen_beeper import Beeper

Beeper().beep(count=2, duration_ms=150, interval_ms=200)
