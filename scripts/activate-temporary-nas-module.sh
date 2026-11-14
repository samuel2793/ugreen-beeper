#!/bin/sh
# Copy and activate the experimental driver on a NAS until its next reboot.
set -eu

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ] || [ "$1" != "--yes" ]; then
    echo "usage: $0 --yes <path-to-ug_beep.ko> [ssh-host]" >&2
    echo "This unloads the active buzzer driver temporarily; reboot restores it." >&2
    exit 2
fi

module=$2
host=${3:-nas}
remote_module=/tmp/ugreen-beeper/ug_beep.ko

if [ ! -f "$module" ]; then
    echo "error: module does not exist: $module" >&2
    exit 1
fi

vermagic=$(modinfo -F vermagic "$module")
case "$vermagic" in
    "6.1.84 "*" aarch64") ;;
    *)
        echo "error: refusing module with unexpected vermagic: $vermagic" >&2
        exit 1
        ;;
esac

ssh "$host" 'mkdir -p /tmp/ugreen-beeper'
scp -O "$module" "$host:$remote_module"

ssh "$host" "sudo -n sh -c '
set -eu
test \"\$(uname -r)\" = 6.1.84
test -e /proc/nas/sata_sw
restore() {
    rmmod ug_beep 2>/dev/null || true
    modprobe ug_beep
}
rmmod ug_beep
if ! insmod $remote_module; then
    echo \"experimental module failed to load; restoring vendor module\" >&2
    restore
    exit 1
fi
if ! test -e /sys/devices/platform/ug-beep/frequency_hz ||
   ! test -e /sys/devices/platform/ug-beep/frequency_min_hz ||
   ! test -e /sys/devices/platform/ug-beep/frequency_max_hz ||
   ! test -e /proc/nas/beeper || ! test -e /proc/nas/sata_sw; then
    echo \"experimental module contract incomplete; restoring vendor module\" >&2
    restore
    exit 1
fi
echo \"temporary frequency module active\"
cat /sys/devices/platform/ug-beep/frequency_hz
cat /sys/kernel/debug/pwm
'"
