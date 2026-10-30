"""数据契约单元测试；人工构造检查结果，不是 Agent 或工具运行证据。"""

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import unittest

from src.schemas import (
    BrandRule, DurationResult, Material, RuleCheckResult, RuleIssue, RunMode,
    Script, SearchResult, Shot, ShotDuration, TaskInput, TaskResult, TaskStatus, ToolError,
)

ROOT = Path(__file__).resolve().parents[1]


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.request = TaskInput(**json.loads((ROOT / "examples/normal/input.json").read_text()))
        self.script = Script(1, "给视频加字幕", [Shot("S01", "字幕示意画面", "支持为视频添加字幕", ["P01"])])
        self.duration = DurationResult(1, self.script.fingerprint, [ShotDuration("S01", 8)], 30, "unit-test fixture")
        self.rules = RuleCheckResult(1, self.script.fingerprint, ["B01"])

    def result(self, **changes):
        values = dict(
            run_id="schema-unit-test", mode=RunMode.MOCK, status=TaskStatus.COMPLETED,
            task_input=self.request, script=self.script,
            duration_result=self.duration, rule_check_result=self.rules,
        )
        values.update(changes)
        return TaskResult(**values)

    def test_existing_json_fixtures_fit_contracts(self):
        material = Material(**json.loads((ROOT / "data/materials.json").read_text())[0])
        rule = BrandRule(**json.loads((ROOT / "data/brand_rules.json").read_text())[0])
        self.assertEqual(material, Material("P01", "支持为视频添加字幕"))
        self.assertEqual(rule.id, "B01")
        self.assertEqual(self.request.target_duration_seconds, 30)

    def test_completed_result_serializes_computed_checks_and_sources(self):
        data = json.loads(json.dumps(self.result().to_dict(), ensure_ascii=False))
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["mode"], "mock")
        self.assertEqual(data["script"]["source_ids"], ["P01"])
        self.assertEqual(data["duration_result"]["total_duration_seconds"], 8)
        self.assertTrue(data["duration_result"]["passed"])
        self.assertTrue(data["rule_check_result"]["passed"])

    def test_revision_rejects_old_duration_and_old_rules_independently(self):
        revised = replace(self.script, version=2)
        fresh_duration = replace(self.duration, script_version=2)
        fresh_rules = replace(self.rules, script_version=2)
        for changes in [
            dict(script=revised, rule_check_result=fresh_rules),
            dict(script=revised, duration_result=fresh_duration),
        ]:
            with self.subTest(changes=tuple(changes)):
                with self.assertRaisesRegex(ValueError, "version and content"):
                    self.result(**changes)
        self.assertEqual(self.result(script=revised, duration_result=fresh_duration,
                                     rule_check_result=fresh_rules).script.version, 2)

    def test_changed_content_cannot_reuse_checks_even_with_same_version(self):
        changes = [
            replace(self.script, title="修改后的标题"),
            replace(self.script, shots=[replace(self.script.shots[0], narration="现在来添加字幕")]),
            replace(self.script, shots=[replace(self.script.shots[0], visual="另一幅示意画面")]),
            replace(self.script, shots=[replace(self.script.shots[0], source_ids=["P02"])]),
        ]
        for changed in changes:
            with self.subTest(script=changed):
                self.assertNotEqual(changed.fingerprint, self.script.fingerprint)
                with self.assertRaisesRegex(ValueError, "version and content"):
                    self.result(script=changed)

    def test_script_and_nested_collections_cannot_change_after_check(self):
        source_ids = ["P01"]
        shots = [Shot("S01", "画面", "旁白", source_ids)]
        script = Script(1, "标题", shots)
        source_ids.append("P02")
        shots.clear()
        self.assertEqual(script.source_ids, ("P01",))
        self.assertEqual(len(script.shots), 1)
        with self.assertRaises(FrozenInstanceError):
            script.title = "另一个标题"

    def test_fingerprint_is_reproducible(self):
        self.assertEqual(replace(self.script).fingerprint, self.script.fingerprint)

    def test_both_checks_required_for_completion(self):
        for name in ["duration_result", "rule_check_result", "script", "task_input"]:
            with self.subTest(field=name), self.assertRaises(ValueError):
                self.result(**{name: None})

    def test_duration_total_and_pass_are_derived(self):
        over = replace(self.duration, shot_durations=[ShotDuration("S01", 31)])
        self.assertEqual(over.total_duration_seconds, 31)
        self.assertFalse(over.passed)
        with self.assertRaisesRegex(ValueError, "passing checks"):
            self.result(duration_result=over)
        with self.assertRaises(TypeError):
            replace(over, passed=True)

    def test_check_cannot_relax_requested_duration_limit(self):
        relaxed = replace(self.duration, target_duration_seconds=60)
        with self.assertRaisesRegex(ValueError, "requested time limit"):
            self.result(duration_result=relaxed)

    def test_duration_must_cover_exact_script_shots(self):
        for timings in [
            [ShotDuration("S99", 8)],
            [ShotDuration("S01", 8), ShotDuration("S02", 8)],
        ]:
            with self.subTest(timings=timings), self.assertRaisesRegex(ValueError, "exactly"):
                self.result(duration_result=replace(self.duration, shot_durations=timings))

    def test_rule_issues_block_completion_and_locate_failures(self):
        issue = RuleIssue("B01", "unsupported_claim", "无依据的效果数据", "S01")
        failed = replace(self.rules, issues=[issue])
        self.assertFalse(failed.passed)
        with self.assertRaisesRegex(ValueError, "passing checks"):
            self.result(rule_check_result=failed)
        with self.assertRaisesRegex(ValueError, "unknown shot"):
            self.result(rule_check_result=replace(failed, issues=[replace(issue, shot_id="S99")]))
        with self.assertRaisesRegex(ValueError, "not checked"):
            replace(failed, checked_rule_ids=["B02"])

    def test_needs_input_and_failures_allow_absent_script_but_require_reason(self):
        for status in [TaskStatus.NEEDS_INPUT, TaskStatus.INCOMPLETE, TaskStatus.FAILED]:
            with self.subTest(status=status):
                result = TaskResult("test", RunMode.MOCK, status, reason="缺少必要信息")
                self.assertIsNone(result.script)
                with self.assertRaisesRegex(ValueError, "requires a reason"):
                    TaskResult("test", RunMode.MOCK, status)

    def test_completed_result_rejects_missing_sources_errors_or_missing_fields(self):
        no_sources = replace(self.script, shots=[replace(self.script.shots[0], source_ids=[])])
        with self.assertRaisesRegex(ValueError, "material references"):
            self.result(script=no_sources,
                        duration_result=replace(self.duration, script_fingerprint=no_sources.fingerprint),
                        rule_check_result=replace(self.rules, script_fingerprint=no_sources.fingerprint))
        for changes in [dict(errors=[ToolError("search_materials", "unavailable", "检索失败")]),
                        dict(missing_fields=["topic"])]:
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "unresolved"):
                self.result(**changes)

    def test_empty_search_is_distinct_from_tool_failure(self):
        self.assertIsNone(SearchResult("字幕").error)
        error = ToolError("search_materials", "unavailable", "检索失败", True)
        self.assertEqual(SearchResult("字幕", error=error).error, error)
        with self.assertRaisesRegex(ValueError, "failed search"):
            SearchResult("字幕", [Material("P01", "支持字幕")], error)

    def test_invalid_numbers_versions_and_duplicate_ids_are_rejected(self):
        for value in [0, -1, float("nan"), float("inf"), True, "30"]:
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                replace(self.request, target_duration_seconds=value)
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                ShotDuration("S01", value)
        for value in [0, -1, True, 1.5]:
            with self.subTest(version=value), self.assertRaises(ValueError):
                replace(self.script, version=value)
        with self.assertRaisesRegex(ValueError, "unique"):
            replace(self.script, shots=[self.script.shots[0], self.script.shots[0]])
        with self.assertRaisesRegex(ValueError, "unique"):
            replace(self.duration, shot_durations=[ShotDuration("S01", 2), ShotDuration("S01", 3)])


if __name__ == "__main__":
    unittest.main()
