import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ugreen_beeper.cli import main
from ugreen_beeper.events import EventConfigError, load_event


class CLITests(unittest.TestCase):
    def test_dry_run_no_hardware(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["beep", "-t", "2", "-l", "400", "-i", "500", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "rep 2 400 500\n")

    def test_cli_writes_to_fake_device(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "beeper"
            path.touch()
            self.assertEqual(main(["beep", "--device", str(path), "-t", "3"]), 0)
            self.assertEqual(path.read_text(), "rep 3 400 500\n")

    def test_named_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "events.json"
            config_path.write_text(json.dumps({"events": {
                "done": {"count": 2, "duration_ms": 150, "interval_ms": 200}
            }}))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["event", "done", "--config", str(config_path), "--dry-run"])
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue(), "rep 2 150 200\n")
            with self.assertRaisesRegex(EventConfigError, "unknown event"):
                load_event(config_path, "missing")

    def test_invalid_event_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "events.json"
            path.write_text('{"events": {"x": {"count": "1"}}}')
            with self.assertRaises(EventConfigError):
                load_event(path, "x")

    def test_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fake"
            path.write_text("booton\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["status", "--device", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("writable: yes", out.getvalue())

    def test_missing_device(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(["beep", "--device", str(Path(temp_dir) / "missing")])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
