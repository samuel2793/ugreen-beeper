#!/usr/bin/env python3
"""Play the opening phrase of Beethoven's public-domain "Ode to Joy".

By default this program is a dry listing. Pass --play to emit the finite notes.
It requires the experimental ug_beep driver currently documented by this
project, because the stock UGREEN driver cannot change frequency.
"""

import argparse
import sys
import time

from ugreen_beeper import Beeper, BeeperError, SysfsFrequencyProcfsBackend


# (note name, frequency in Hz, duration in ms). All values remain within the
# experimentally validated 500–2000 Hz driver range.
ODE_TO_JOY = (
    ("E5", 1319, 220), ("E5", 1319, 220), ("F5", 1397, 220), ("G5", 1568, 220),
    ("G5", 1568, 220), ("F5", 1397, 220), ("E5", 1319, 220), ("D5", 1175, 220),
    ("C5", 1047, 220), ("C5", 1047, 220), ("D5", 1175, 220), ("E5", 1319, 220),
    ("E5", 1319, 330), ("D5", 1175, 330),
)
PAUSE_MS = 55


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--play", action="store_true", help="emit the melody")
    args = parser.parse_args()

    if not args.play:
        for note, frequency_hz, duration_ms in ODE_TO_JOY:
            print(f"{note}: {frequency_hz} Hz for {duration_ms} ms")
        print("Run again with --play to emit these finite notes.")
        return 0

    beeper = Beeper(SysfsFrequencyProcfsBackend())
    try:
        for note, frequency_hz, duration_ms in ODE_TO_JOY:
            print(f"playing {note} ({frequency_hz} Hz)")
            beeper.beep(
                count=1,
                duration_ms=duration_ms,
                interval_ms=PAUSE_MS,
                frequency_hz=frequency_hz,
            )
            # The driver schedules playback asynchronously; do not overwrite a
            # note before its finite on-time and pause have elapsed.
            time.sleep((duration_ms + PAUSE_MS) / 1000)
    except BeeperError as exc:
        print(f"ode-to-joy: {exc}", file=sys.stderr)
        print("Try: sudo env PYTHONPATH=src python3 examples/ode-to-joy.py --play", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
