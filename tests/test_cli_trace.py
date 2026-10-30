import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.trace import TraceRecorder

ROOT = Path(__file__).resolve().parents[1]


class TraceTests(unittest.TestCase):
    def test_trace_redacts_credentials_and_reasoning_recursively(self):
        trace = TraceRecorder("test", secrets=("known-secret",))
        event = trace.emit(1, "action", observation={"api_key": "known-secret", "reasoning_content": "private", "message": "known-secret sk-abcdefgh1234"})
        serialized = json.dumps(event)
        for value in ["known-secret", "sk-abcdefgh1234", "private", "api_key", "reasoning_content"]:
            self.assertNotIn(value, serialized)

    def test_trace_file_is_append_only_and_existing_file_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.jsonl"
            trace = TraceRecorder("test", path)
            trace.emit(1, "action", action="search_materials")
            trace.emit(2, "terminal", status="incomplete")
            self.assertEqual([json.loads(line)["sequence"] for line in path.read_text().splitlines()], [1, 2])
            with self.assertRaises(FileExistsError):
                TraceRecorder("new", path)


@unittest.skipUnless(importlib.util.find_spec("langgraph"), "CLI integration requires LangGraph")
class CliTests(unittest.TestCase):
    def test_mock_file_input_writes_outputs_without_api_key(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = subprocess.run([sys.executable, "-m", "src.main", "--mode", "mock", "--input", "examples/normal/input.json",
                                     "--output-dir", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads((output / "result.json").read_text())["mode"], "mock")
            for name in ["checks.json", "script.md", "history.json", "run.json", "trace.jsonl"]:
                self.assertTrue((output / name).is_file(), name)
            again = subprocess.run([sys.executable, "-m", "src.main", "--input", "examples/normal/input.json", "--output-dir", str(output)],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(again.returncode, 2)

    def test_interactive_json_and_missing_input_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-m", "src.main", "--interactive", "--mode", "mock", "--output-dir", str(Path(directory) / "run")],
                                    input='{"audience":"新手"}\nEND\n', cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads((Path(directory) / "run/result.json").read_text())
            self.assertEqual(payload["status"], "needs_input")
            self.assertTrue(payload["questions"])


if __name__ == "__main__":
    unittest.main()
