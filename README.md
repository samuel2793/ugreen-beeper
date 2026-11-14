# ugreen-beeper

Control the physical beeper in supported **UGREEN NAS** devices from Linux,
scripts, automation systems, systemd services, or Python. No long-running daemon
or external runtime dependencies.

**Status: experimental v0.1.0.** Tested on a UGREEN DH4300 Plus with Debian 12,
kernel 6.1.84 and the vendor `ug-beep` driver. Other models are **not** yet
confirmed. Not affiliated with UGREEN.

[Español](README.es.md) · [Hardware/protocol](docs/hardware.md)

## How it works

The working vendor helper on the tested NAS sends:

```text
rep <count> <duration_ms> <interval_ms>
```

to `/proc/nas/beeper`. This package validates arguments and sends the same
command. It does **not** directly manipulate PWM, unbind kernel drivers or
change the kernel/device tree. Frequency is not supported because the tested
`ugbeep` helper ignores `-f`.

## Requirements

- Linux and Python 3.11+ (Debian 12's default Python is suitable).
- A supported vendor driver exposing writable `/proc/nas/beeper`.
- Permission to write to that path. `sudo` is not required on the tested device.

## Try directly from the checkout (no install)

```sh
./ugreen-beep status
./ugreen-beep beep --dry-run -t 2 -l 400 -i 500
./ugreen-beep beep -t 2 -l 400 -i 500
./ugreen-beep event backup-success --config examples/events.json
```

The launcher uses only the standard Python library and GNU `readlink` (available
on Debian). You can also run `PYTHONPATH=src python3 -m ugreen_beeper ...`.

## Make the command available to other processes (without pip)

For a system-wide installation, copy the trusted source and launcher into an
administrator-managed directory on the NAS (from the project directory):

```sh
sudo mkdir -p /opt/ugreen-beeper
sudo cp -r src /opt/ugreen-beeper/
sudo cp ugreen-beep /opt/ugreen-beeper/
sudo chmod +x /opt/ugreen-beeper/ugreen-beep
sudo ln -s /opt/ugreen-beeper/ugreen-beep /usr/local/bin/ugreen-beep
ugreen-beep status
```

If `/usr/local/bin/ugreen-beep` already exists, remove or rename it yourself
after verifying its origin; the installation command deliberately does not
overwrite it. Services should use `/usr/local/bin/ugreen-beep` explicitly.

## Alternative: install with an isolated Python environment

On Debian, install `python3-venv` if it is not available. From the project
folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ugreen-beep status
.venv/bin/ugreen-beep beep -t 2 -l 400 -i 500
```

If you want multiple local programs or systemd services to use the tool,
install it in a shared, administrator-managed location and invoke the full
executable path. Avoid depending on a service's `PATH` setting.

## CLI

```sh
ugreen-beep beep -t 1 -l 150                   # one short beep
ugreen-beep beep -t 3 -l 200 -i 250            # repeated alarm
ugreen-beep beep --dry-run -t 3 -l 200 -i 250  # show protocol command only
ugreen-beep status                             # procfs accessibility
ugreen-beep event disk-warning --config /etc/ugreen-beeper/events.json
```

Parameters: `-t/--count` (1–20), `-l/--duration-ms` (10–5000), and
`-i/--interval-ms` (0–10000). Estimated total duration is limited to 120 s
as an accidental-alarm guard. Exit status is `0` on accepted write, `1` for
a hardware/configuration error, `2` for bad CLI syntax. A successful write
does not prove the sound was physically audible.

## Named events

Copy `examples/events.json` to a suitable location such as
`/etc/ugreen-beeper/events.json` and edit the values:

```json
{
  "events": {
    "backup-success": {"count": 2, "duration_ms": 120, "interval_ms": 180},
    "backup-failed": {"count": 4, "duration_ms": 350, "interval_ms": 220}
  }
}
```

```sh
ugreen-beep event backup-failed --config /etc/ugreen-beeper/events.json
```

This gives applications a stable semantic name, even if the sound profile
changes later. Each event maps to one vendor `rep` command in 0.1.0.

## Python API

```python
from ugreen_beeper import Beeper

Beeper().beep(count=2, duration_ms=150, interval_ms=200)
```

The `Beeper` class accepts any object with a `send(Beep)` method, so future
hardware backends do not require replacing application-level calls.

## Run a notification after another command

`examples/notify-command.sh` preserves the exit code of the wrapped command:

```sh
UGREEN_BEEPER_EVENTS="$PWD/examples/events.json" \
  ./examples/notify-command.sh /usr/local/bin/my-backup-script
```

For scheduled jobs, call the CLI by absolute path in your service/timer/cron
configuration. Only the built-in helper's return code and the procfs write
status are known; this project cannot currently guarantee playback order when
several unrelated processes emit commands simultaneously.

## Test

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Unit tests write to temporary files, **not** to a real beeper. Hardware tests
must be performed deliberately on a supported NAS.

## Security and constraints

- The tested `/proc/nas/beeper` is writable by unprivileged users: access
  control is inherited from the device and is **not** managed by this project.
- A local user or process with device write permissions can make audible
  sounds. Do not treat this as an authenticated alert delivery system.
- No frequency control, playback queue, concurrent-writer arbitration,
  confirmation of physical sound, or support for unsupported kernels yet.
- Input is validated as integers; no shell is used to send device commands.

See [hardware and compatibility notes](docs/hardware.md).

## Roadmap (not in v0.1.0)

- Hardware verification on more UGREEN models.
- Optional queue/serialization for competing producers.
- Pattern sequences, callback integrations and pluggable transports.
- Packaging and service integration examples.

MIT licensed. Contributions welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
