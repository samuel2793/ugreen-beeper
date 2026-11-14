# Contributing

Run the tests without touching hardware:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Hardware reports are welcome. Please include model, OS, kernel, existence and
permissions of `/proc/nas/beeper`, the output of
`sudo cat /sys/kernel/debug/pwm` if available, and results of a short test.
Do not post serial numbers, IP addresses, SSH keys or other secrets.

New backends should implement `send(Beep)` without shell invocation, preserve
reasonable error reporting and include tests using a fake transport. Do not
claim hardware support without verification on the target model.
