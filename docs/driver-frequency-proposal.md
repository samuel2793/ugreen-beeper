# Proposal: a frequency-capable `ug_beep` driver

This is a design proposal, not an installation guide or production patch. It
is based on the module inspected in [hardware.md](hardware.md).

## Goal

Add a documented `freq <hz>` command (or a dedicated sysfs attribute) to the
driver which already owns the PWM. It should atomically update the desired
state using `pwm_apply_state()` with `period = NSEC_PER_SEC / frequency_hz`
and approximately 50% duty, while retaining `rep` for finite playback.

## Required safeguards

1. Use per-device data and a mutex to serialize frequency changes and playback.
2. Parse an exact, documented command; do not overload `rep`.
3. Reject invalid values and select a range only after physical tests at 500,
   1000 and 2000 Hz. Do not claim a range beforehand.
4. Define changes during playback: reject with `-EBUSY` or apply at a safe
   edge. Check every `pwm_apply_state()` error and preserve prior state.
5. Keep `febe0010.pwm` and `febe0020.pwm` completely out of scope.

This uses the standard PWM API already used by `ug_beep`; it requires neither
unbind/rebind, PWM export nor register writes.

## Build and physical-validation gate

Only an administrator with the exact build tree/config for `6.1.84
#d64bed19bdfd`, recovery access, and a saved original module should build or
install it. This repository never loads, unloads or replaces modules.

Before one finite test, record:

```sh
uname -a
sha256sum /lib/modules/"$(uname -r)"/kernel/drivers/ugreen/ug_beep.ko
sudo cat /sys/kernel/debug/pwm
```

Start at the existing 950 Hz, then test one `rep 1 100 0` per candidate. Check
debugfs after each test and listen for the result. If the PWM stays enabled,
stop testing and use the driver's documented off path or reboot in a
maintenance window; never touch either fan PWM. Restore the original module
only through an approved maintenance procedure.

## Why not Device Tree or an independent PWM backend?

The driver overwrites the DT period during probe, so DT can at most affect an
initial value, not runtime changes. A second consumer conflicts with the
existing owner. A narrow extension to that owner is safer and maintainable.
