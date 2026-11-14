"""Command-line interface for scripting and automation."""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from .core import DEFAULT_DEVICE, Beep, Beeper, BeeperError, ProcfsBackend
from .events import EventConfigError, load_event


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ugreen-beep",
        description="Control a supported UGREEN NAS hardware beeper.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.0")
    commands = parser.add_subparsers(dest="command", required=True)

    def add_transport(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--device", type=Path, default=DEFAULT_DEVICE,
            help=f"procfs device path (default: {DEFAULT_DEVICE})",
        )
        subparser.add_argument(
            "--dry-run", action="store_true",
            help="print the vendor command without writing to the device",
        )

    beep_cmd = commands.add_parser("beep", help="emit one vendor repeat command")
    beep_cmd.add_argument("-t", "--count", type=int, default=1, help="number of beeps (1–20)")
    beep_cmd.add_argument("-l", "--duration-ms", type=int, default=400, help="on-time in ms (10–5000)")
    beep_cmd.add_argument("-i", "--interval-ms", type=int, default=500, help="pause in ms (0–10000)")
    beep_cmd.add_argument(
        "-f", "--frequency", dest="frequency_hz", type=int,
        help="physical frequency in Hz (only on a backend that explicitly supports it)",
    )
    add_transport(beep_cmd)

    event_cmd = commands.add_parser("event", help="emit a configured named event")
    event_cmd.add_argument("name", help="name in the JSON events object")
    event_cmd.add_argument("--config", required=True, type=Path, help="JSON configuration file")
    add_transport(event_cmd)

    status_cmd = commands.add_parser("status", help="check whether the device is writable")
    status_cmd.add_argument("--device", type=Path, default=DEFAULT_DEVICE)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = make_parser().parse_args(argv)

    if args.command == "status":
        exists = args.device.exists()
        writable = exists and os.access(args.device, os.W_OK)
        print(f"device: {args.device}")
        print(f"exists: {'yes' if exists else 'no'}")
        print(f"writable: {'yes' if writable else 'no'}")
        return 0 if writable else 1

    try:
        if args.command == "beep":
            operation = Beep(
                args.count, args.duration_ms, args.interval_ms, args.frequency_hz
            )
        else:
            operation = load_event(args.config, args.name)

        beeper = Beeper(ProcfsBackend(args.device))
        beeper.validate(operation)
        if args.dry_run:
            print(operation.command())
        else:
            beeper.backend.send(operation)
        return 0
    except (ValueError, EventConfigError, BeeperError) as exc:
        print(f"ugreen-beep: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
