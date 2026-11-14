# Changelog

## 0.2.0 — Frequency capability boundary

- Added explicit backend capabilities and optional `frequency_hz` API parameter.
- Added `--frequency`; the verified procfs backend rejects it instead of silently
  accepting a value it cannot apply.
- Added `SysfsFrequencyProcfsBackend` for the documented, opt-in `ug_beep`
  driver extension. It reads driver-published limits before applying a frequency.
- Added an experimental clean-room ARM64 `ug_beep` replacement for the DH4300
  Plus, including finite playback, sysfs frequency attributes and rollback
  documentation. It is not installed automatically or persistently.
- Documented static reverse-engineering of the installed DH4300 Plus `ug_beep.ko`.
- Added a separate, non-deployable driver-change proposal and coverage for the
  capability contract.

## 0.1.0 — Initial release

- Linux procfs backend for the confirmed UGREEN `rep` protocol.
- Zero runtime dependencies; Python CLI and importable API.
- Named events with JSON configuration.
- Input validation, dry-run, status checks and unit tests.
- Hardware notes, examples, MIT license and CI.
