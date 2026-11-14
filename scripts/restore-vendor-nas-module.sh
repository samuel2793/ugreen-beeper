#!/bin/sh
# Restore the vendor ug_beep module without waiting for a reboot.
set -eu

host=${1:-nas}

ssh "$host" "sudo -n sh -c '
set -eu
rmmod ug_beep
modprobe ug_beep
test ! -e /sys/devices/platform/ug-beep/frequency_hz
test -e /proc/nas/beeper
test -e /proc/nas/sata_sw
echo \"vendor ug_beep module restored\"
cat /sys/kernel/debug/pwm
'"
