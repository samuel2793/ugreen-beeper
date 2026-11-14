# Hardware support and protocol

## Confirmed (user-tested)

| Device | OS | Kernel | Driver | Procfs interface |
|---|---|---|---|---|
| UGREEN DH4300 Plus (RK3588C) | Debian 12 (aarch64) | 6.1.84 | `ug-beep` | `/proc/nas/beeper` |

The machine exposed the following PWM consumers in debugfs:

- `febe0000.pwm`: `ug-beep` (buzzer; observed 1,052,631 ns period, ~950 Hz)
- `febe0010.pwm`: `fan-speed` — **do not touch**
- `febe0020.pwm`: `fan-det` — **do not touch**

The vendor `/usr/sbin/ugbeep` shell script writes the following text into
`/proc/nas/beeper`:

```text
rep <count> <duration_ms> <interval_ms>
```

The stock `ugbeep` shell script accepts `-f` but does not pass a frequency
to the driver. This project therefore does not expose frequency control.
The previously observed procfs value `booton` is not treated as a playback
command or documented API.

## Not yet verified

Other UGREEN models, other operating systems, upstream kernels and non-UGREEN
hardware. A missing `/proc/nas/beeper` cannot be fixed by installing this
Python package alone: the kernel driver/interface must exist.

## Limitations

The vendor-kernel protocol was verified by inspecting the installed helper and
hearing the buzzer. Exact internal scheduling and simultaneous-command behavior
have **not** been verified. Independent processes may interfere with one
another. No locking, queue or daemon is provided in 0.1.0. Avoid alarm floods.
