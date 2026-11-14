#!/usr/bin/env python3
"""Finite buzzer patterns for the experimental frequency-capable driver.

List patterns:  PYTHONPATH=src python3 examples/patterns.py
Play one:       sudo env PYTHONPATH=src python3 examples/patterns.py siren --play
"""

import argparse
import sys
import time

from ugreen_beeper import Beeper, BeeperError, SysfsFrequencyProcfsBackend


# Each tuple is (frequency_hz, on_time_ms, pause_after_ms). All pitches are in
# the tested 500–2000 Hz range. The patterns are deliberately finite.
PATTERNS = {
    "sos": (
        "International Morse SOS at 1000 Hz",
        ((1000, 120, 120),) * 3
        + ((1000, 360, 120),) * 3
        + ((1000, 120, 120),) * 3,
    ),
    "siren": (
        "Two ascending/descending alert sweeps",
        tuple((hz, 140, 20) for hz in (500, 700, 900, 1100, 1300, 1500,
                                        1300, 1100, 900, 700, 500) * 2),
    ),
    "frere-jacques": (
        "Traditional public-domain melody, first section",
        tuple((hz, duration, 55) for hz, duration in (
            (1047, 220), (1175, 220), (1319, 220), (1047, 220),
            (1047, 220), (1175, 220), (1319, 220), (1047, 220),
            (1319, 220), (1397, 220), (1568, 440),
            (1319, 220), (1397, 220), (1568, 440),
        )),
    ),
}


def play(pattern: tuple[tuple[int, int, int], ...]) -> None:
    beeper = Beeper(SysfsFrequencyProcfsBackend())
    for frequency_hz, duration_ms, pause_ms in pattern:
        beeper.beep(
            count=1,
            duration_ms=duration_ms,
            interval_ms=pause_ms,
            frequency_hz=frequency_hz,
        )
        time.sleep((duration_ms + pause_ms) / 1000)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pattern", nargs="?", choices=sorted(PATTERNS))
    parser.add_argument("--play", action="store_true", help="emit the selected pattern")
    args = parser.parse_args()

    if args.pattern is None:
        for name, (description, pattern) in PATTERNS.items():
            total_ms = sum(duration + pause for _, duration, pause in pattern)
            print(f"{name}: {description} ({len(pattern)} notes, ~{total_ms / 1000:.1f}s)")
        return 0
    if not args.play:
        print(f"{args.pattern}: {PATTERNS[args.pattern][0]}")
        print("Add --play to emit this finite pattern.")
        return 0

    try:
        play(PATTERNS[args.pattern][1])
    except BeeperError as exc:
        print(f"patterns: {exc}", file=sys.stderr)
        print("Try with sudo; frequency sysfs is administrator-writable.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
