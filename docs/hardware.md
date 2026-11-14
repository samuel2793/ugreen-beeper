# Hardware support and protocol

## Confirmed on the inspected DH4300 Plus

| Device | OS | Kernel | Driver | Procfs interface |
|---|---|---|---|---|
| UGREEN DH4300 Plus (RK3588C) | Debian 12 (aarch64) | 6.1.84 | `ug-beep` | `/proc/nas/beeper` |

The machine exposed the following PWM consumers in debugfs (observed before
this repository change):

- `febe0000.pwm`: `ug-beep` (buzzer; observed 1,052,631 ns period, ~950 Hz)
- `febe0010.pwm`: `fan-speed` — **do not touch**
- `febe0020.pwm`: `fan-det` — **do not touch**

The vendor `/usr/sbin/ugbeep` shell script writes the following text into
`/proc/nas/beeper`:

```text
rep <count> <duration_ms> <interval_ms>
```

The stock `ugbeep` shell script accepts `-f` but does not pass a frequency
to the driver. Its source writes exactly `rep ${times} ${long} ${interval}`.
The previously observed procfs value `booton` is not treated as a playback
command or documented API.

### Why the carrier is approximately 950 Hz

This is confirmed by static inspection, not inferred only from debugfs. On
2026-11-14, the exact installed module was copied read-only and inspected:

| Item | Confirmed value |
|---|---|
| Module | `/lib/modules/6.1.84/kernel/drivers/ugreen/ug_beep.ko` |
| ELF | ARM64 relocatable, not stripped; Build ID `e2cf4c4962fa070f3b38b8beaf1276366fe3bb4c` |
| Load state | `ug_beep` is a loaded GPLv2 module, not a built-in driver |
| DT compatible | `ug-pwm-beep` |
| PWM consumer | `febe0000.pwm`, channel 0 (`ug-beep`) |
| Probe state | period **1,052,631 ns**, duty cycle **526,315 ns** |

`ug_beep_probe` constructs those constants and calls the standard Linux
`pwm_apply_state()` API. `1_000_000_000 / 1_052_631` is **950.00095 Hz** and
the duty cycle is effectively 50%. This agrees with the live debugfs state.

The live DT `pwms` property is phandle `0x1ae`, channel 0, period `0x0fa0`
(4,000 ns), flags 0. The driver replaces that state at probe, so the DT does
not set the running 950 Hz. No DT change was made.

### Procfs surface and conclusion

The unstripped module establishes command families `booton`, `bootoff`, `on`,
`off`, `one`, `timer <...>`, and `rep <count> <duration> <interval>`.
Only `rep` is used here. `beeper_write` has no frequency parsing path; its
normal playback calls copy the configured PWM state and toggle enablement.
No unknown procfs command was sent.

Dynamic frequency changes are **not available through the installed vendor
procfs driver**. Direct PWM access would conflict with the `ug_beep` owner;
unbind/rebind is not a supported approach.

An experimental clean-room replacement is now available under
[`kernel/ug_beep_frequency`](../kernel/ug_beep_frequency). It owns only the
existing buzzer PWM and exposes a sysfs frequency contract; it is loaded from
`/tmp` for testing and is not installed persistently. On the DH4300 Plus it
was verified to change the disabled PWM from 950 Hz to 1000 Hz (1,000,000 ns
period), preserve `sata_sw`, and automatically disable after a finite 100 ms
beep. See its README for the exact validation boundary. It remains experimental
until it is built from the vendor source tree and independently reviewed.

## Not yet verified

Other UGREEN models, other operating systems, upstream kernels and non-UGREEN
hardware. The command names above are only confirmed for this module build. A
missing `/proc/nas/beeper` cannot be fixed by installing this Python package:
the kernel driver/interface must exist.

## Limitations

The vendor-kernel protocol was verified by inspecting the installed helper and
hearing the buzzer. Exact internal scheduling and simultaneous-command behavior
have **not** been verified. Independent processes may interfere with one
another. No locking, queue or daemon is provided. Avoid alarm floods.
