#!/bin/sh
# Wrap any command; preserve its exit status even if the buzzer fails.
# Requires ugreen-beep on PATH and an accessible events config.
set -u

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 command [args...]" >&2
    exit 2
fi

CONFIG=${UGREEN_BEEPER_EVENTS:-/etc/ugreen-beeper/events.json}
"$@"
status=$?
if [ "$status" -eq 0 ]; then
    ugreen-beep event backup-success --config "$CONFIG" || true
else
    ugreen-beep event backup-failed --config "$CONFIG" || true
fi
exit "$status"
