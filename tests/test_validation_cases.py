"""人工构造事件测试证据分类器，不能当作模型执行记录。"""

import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "examples/prompt-validation/run_cases.py"
SPEC = importlib.util.spec_from_file_location("validation_cases", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def event(sequence, action, observation):
    return {"sequence": sequence, "event": "action", "action": action, "observation": observation}


def completed(version=2):
    report = {"script_version": version, "script_fingerprint": "example-fingerprint", "passed": True}
    result = {"status": "completed", "script": {"version": version, "fingerprint": "example-fingerprint"},
              "task_input": {"target_duration_seconds": 5},
              "duration_result": {**report, "target_duration_seconds": 5, "total_duration_seconds": 2.65},
              "rule_check_result": report}
    events = [event(1, "save_script", {"saved": True, "script_version": version}),
              event(2, "estimate_duration", result["duration_result"]),
              event(3, "check_rules", result["rule_check_result"]),
              event(4, "finish", {"status": "completed"})]
    return result, events


class ValidationCaseTests(unittest.TestCase):
    def test_direct_short_success_does_not_cover_duration_repair(self):
        result, events = completed(1)
        self.assertEqual(MODULE.assess("over-duration", result, events)["verdict"], "not_covered")

    def test_actual_failure_followed_by_new_version_rechecks_covers_repair(self):
        result, events = completed()
        for item in events:
            item["sequence"] += 2
        events = [event(1, "save_script", {"saved": True, "script_version": 1}),
                  event(2, "estimate_duration", {"passed": False, "script_version": 1}), *events]
        self.assertEqual(MODULE.assess("over-duration", result, events)["verdict"], "passed")

    def test_stale_final_report_is_rejected(self):
        result, events = completed()
        result["duration_result"]["script_version"] = 1
        self.assertEqual(MODULE.assess("normal", result, events)["verdict"], "failed")

    def test_checks_after_finish_do_not_prove_valid_completion(self):
        result, events = completed()
        events[-1]["sequence"] = 2
        events[1]["sequence"] = 3
        events[2]["sequence"] = 4
        self.assertEqual(MODULE.assess("normal", result, events)["verdict"], "failed")

    def test_budget_stop_does_not_prove_model_chose_incomplete(self):
        result = {"status": "incomplete", "reason": "budget"}
        events = [event(1, "estimate_duration", {"passed": False, "script_version": 1})]
        self.assertEqual(MODULE.assess("over-duration", result, events)["verdict"], "failed")
        events.append(event(2, "finish", {"status": "incomplete"}))
        self.assertEqual(MODULE.assess("over-duration", result, events)["verdict"], "passed")

    def test_direct_request_and_observed_empty_search_are_distinct(self):
        result = {"status": "needs_input", "questions": ["请补充资料。"], "script": None}
        self.assertEqual(MODULE.assess("no-materials", result, [])["verdict"], "passed")
        self.assertEqual(MODULE.assess("unrelated-materials", result, [])["verdict"], "not_covered")
        events = [event(1, "search_materials", {"materials": [], "error": None})]
        self.assertEqual(MODULE.assess("unrelated-materials", result, events)["verdict"], "passed")

    def test_tool_failure_requires_subsequent_successful_search(self):
        result, events = completed()
        for item in events:
            item["sequence"] += 2
        failure = event(1, "search_materials", {"error": {"code": "simulated_failure"}})
        self.assertEqual(MODULE.assess("tool-failure", result, [failure, *events])["verdict"], "failed")
        success = event(2, "search_materials", {"materials": [{"id": "P01"}], "error": None})
        self.assertEqual(MODULE.assess("tool-failure", result, [failure, success, *events])["verdict"], "passed")

    def test_connection_failure_is_blocked_not_business_success(self):
        result = {"status": "failed", "reason": "connection", "errors": [{"tool": "model", "code": "connection_error"}]}
        self.assertEqual(MODULE.assess("normal", result, [])["verdict"], "blocked")


if __name__ == "__main__":
    unittest.main()
