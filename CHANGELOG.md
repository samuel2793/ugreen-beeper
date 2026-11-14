# Changelog

## 0.2.0 — Frequency capability boundary

- Added explicit backend capabilities and optional `frequency_hz` API parameter.
- Added `--frequency`; the verified procfs backend rejects it instead of silently
  accepting a value it cannot apply.
- Documented static reverse-engineering of the installed DH4300 Plus `ug_beep.ko`.
- Added a separate, non-deployable driver-change proposal and coverage for the
  capability contract.

## 0.1.0 — Initial release

- Linux procfs backend for the confirmed UGREEN `rep` protocol.
- Zero runtime dependencies; Python CLI and importable API.
- Named events with JSON configuration.
- Input validation, dry-run, status checks and unit tests.
- Hardware notes, examples, MIT license and CI.
