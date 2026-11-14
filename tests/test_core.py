import tempfile
import unittest
from pathlib import Path

from ugreen_beeper import (
    BackendCapabilities,
    Beep,
    Beeper,
    BeeperError,
    ProcfsBackend,
    SysfsFrequencyProcfsBackend,
    UnsupportedFrequencyError,
)


class FakeBackend:
    def __init__(self):
        self.sent = []

    def send(self, beep):
        self.sent.append(beep)


class FrequencyBackend(FakeBackend):
    capabilities = BackendCapabilities(True, (500, 2_000))


class BeeperTests(unittest.TestCase):
    def test_exact_protocol_string(self):
        self.assertEqual(Beep(2, 400, 500).command(), "rep 2 400 500")

    def test_defaults(self):
        self.assertEqual(Beep().command(), "rep 1 400 500")

    def test_input_restrictions(self):
        invalid = [
            (0, 100, 100), (21, 100, 100),
            (1, 0, 100), (1, 19, 100), (1, 5001, 100),
            (1, 100, -1), (1, 100, 19), (1, 100, 10001),
            (True, 100, 100), (1, "100", 100),
            (20, 5000, 5000),
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                Beep(*values)

    def test_custom_backend(self):
        fake = FakeBackend()
        operation = Beeper(fake).beep(count=3, duration_ms=150, interval_ms=200)
        self.assertEqual(fake.sent, [operation])

    def test_procfs_rejects_frequency_instead_of_ignoring_it(self):
        with self.assertRaisesRegex(UnsupportedFrequencyError, "not supported"):
            Beeper(ProcfsBackend()).beep(frequency_hz=1_500)

    def test_sysfs_backend_applies_frequency_then_procfs_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            beeper_path = directory / "beeper"
            frequency_path = directory / "frequency_hz"
            minimum_path = directory / "frequency_min_hz"
            maximum_path = directory / "frequency_max_hz"
            for path, value in (
                (beeper_path, ""), (frequency_path, ""),
                (minimum_path, "500\n"), (maximum_path, "2000\n"),
            ):
                path.write_text(value)
            backend = SysfsFrequencyProcfsBackend(
                beeper_path, frequency_path, minimum_path, maximum_path
            )
            operation = Beeper(backend).beep(count=2, frequency_hz=1_500)
            self.assertEqual(operation.frequency_hz, 1_500)
            self.assertEqual(frequency_path.read_text(), "1500\n")
            self.assertEqual(beeper_path.read_text(), "rep 2 400 500\n")

    def test_sysfs_backend_does_not_claim_missing_driver_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = SysfsFrequencyProcfsBackend(Path(temp_dir) / "beeper")
            self.assertFalse(backend.capabilities.supports_frequency)
            with self.assertRaisesRegex(UnsupportedFrequencyError, "not supported"):
                Beeper(backend).beep(frequency_hz=1_500)

    def test_frequency_capable_backend_receives_requested_frequency(self):
        fake = FrequencyBackend()
        operation = Beeper(fake).beep(frequency_hz=1_500)
        self.assertEqual(operation.frequency_hz, 1_500)
        self.assertEqual(fake.sent, [operation])

    def test_frequency_validation_and_range(self):
        for value in (0, -1, True, "1500"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Beep(frequency_hz=value)
        with self.assertRaisesRegex(UnsupportedFrequencyError, "outside"):
            Beeper(FrequencyBackend()).beep(frequency_hz=2_001)

    def test_procfs_backend_writes_newline_terminated_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fake-beeper"
            path.touch()
            ProcfsBackend(path).send(Beep(2, 400, 500))
            self.assertEqual(path.read_text(), "rep 2 400 500\n")

    def test_procfs_missing_parent_returns_actionable_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing" / "device"
            with self.assertRaisesRegex(BeeperError, "does not exist"):
                ProcfsBackend(path).send(Beep())


if __name__ == "__main__":
    unittest.main()
