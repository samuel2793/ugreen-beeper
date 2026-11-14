# Experimental `ug_beep` replacement

This source is a clean-room replacement based on the observed DH4300 Plus
interface and static analysis of its installed `ug_beep.ko`. It is not derived
from unavailable UGREEN source code. It preserves the only protocol used by
this project, `rep <count> <duration_ms> <interval_ms>`, and adds:

```text
/sys/devices/platform/ug-beep/frequency_hz
/sys/devices/platform/ug-beep/frequency_min_hz
/sys/devices/platform/ug-beep/frequency_max_hz
```

The frequency range is deliberately limited to 500–2000 Hz. It starts at 950
Hz, matching the installed vendor module. Do not install it until it has been
compiled against the target kernel and reviewed with the deployment checklist.

This module is intentionally scoped to `febe0000.pwm` through the existing
`ug-pwm-beep` Device Tree node. It has no references to either fan PWM.

`/proc/nas` is shared with UGREEN's `sata_sw` entry. The module looks up and
reuses that directory, creates/removes only its `beeper` entry, and never
removes the shared directory.

## DH4300 Plus validation, 2026-11-14

The module compiled with the official Linux 6.1.84 headers was loaded
temporarily from `/tmp` on the target kernel. It published all three sysfs
attributes, preserved `/proc/nas/sata_sw`, and left both fan PWMs unchanged.
With PWM disabled, setting 1000 Hz changed `febe0000.pwm` to a 1,000,000 ns
period and 500,000 ns duty cycle. It was then returned to 950 Hz. One finite
`rep 1 100 0` operation at 1000 Hz completed and debugfs no longer reported
the buzzer as enabled after one second. This confirms PWM configuration and
automatic stop behavior, not an independent oscilloscope measurement or a
subjective audible-tone comparison.

## Reproducible build

The repository deliberately does not ship a `.ko`. Obtain the exact UGREEN
6.1.84 build tree, prepare it using its matching configuration, then build
without deploying:

```sh
scripts/build-ug-beep-module.sh /path/to/prepared/linux-6.1.84 ./dist
```

The script requires a generated `include/config/kernel.release`, insists on
release `6.1.84`, checks the resulting ARM64 vermagic, and writes only to the
selected output directory. It does not SSH, copy, load, unload or install a
module. Building against upstream Linux 6.1.84 was sufficient for the initial
experimental validation but is not a substitute for the vendor build tree.

## Temporary NAS activation

After building, activation is one explicit command from the development host:

```sh
scripts/activate-temporary-nas-module.sh --yes ./dist/ug_beep.ko nas
```

It copies the module only to `/tmp/ugreen-beeper`, checks the target kernel,
preserves `/proc/nas/sata_sw`, and automatically reloads the vendor module if
probe verification fails. It emits no beep. The module disappears after a
reboot. To revert immediately without rebooting:

```sh
scripts/restore-vendor-nas-module.sh nas
```

Both commands require SSH access and passwordless `sudo` for the relevant
module commands. Do not run activation during active writes, RAID work, or
when physical recovery is unavailable.
