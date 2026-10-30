"""实际调用本地工具；脚本为人工测试输入，不代表模型生成。"""

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from src.schemas import BrandRule, Material, Script, Shot, TaskInput, TaskResult, ToolError
from src.tools import (
    check_rules, estimate_duration, load_brand_rules, load_materials, load_script,
    search_materials,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "examples/tool-validation/input-script.json"


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.materials = load_materials()
        self.rules = load_brand_rules()
        self.script = load_script(SCRIPT_PATH)

    def changed_narration(self, text, source_ids=("P01",)):
        shot = replace(self.script.shots[1], narration=text, source_ids=source_ids)
        return replace(self.script, shots=[self.script.shots[0], shot])

    def issues(self, script):
        result = check_rules(script, self.materials, self.rules)
        self.assertNotIsInstance(result, ToolError)
        self.assertFalse(result.passed)
        return {issue.code for issue in result.issues}

    def test_search_returns_original_fact_and_honors_id_filter(self):
        found = search_materials("字幕", ["P01"])
        self.assertEqual(found.materials, self.materials)
        self.assertEqual(found.materials[0].fact, "支持为视频添加字幕")
        self.assertEqual(search_materials("字幕", []).materials, ())
        self.assertEqual(search_materials("翻译", ["P01"]).materials, ())
        self.assertEqual(search_materials("字幕", ["missing"]).error.code, "unknown_material_id")

    def test_search_uses_case_insensitive_whitespace_separated_or_keywords(self):
        corpus = [Material("EN01", "Supports video captions")]
        self.assertEqual(search_materials("unknown CAPTIONS", materials=corpus).materials, tuple(corpus))
        # 首版不做分词或语义检索，长句不匹配时应由模型调整查询。
        self.assertEqual(search_materials("请帮我查找字幕相关功能").materials, ())

    def test_empty_result_and_unreadable_corpus_are_distinct(self):
        empty = search_materials("翻译")
        self.assertIsNone(empty.error)
        with patch("src.tools.load_materials", side_effect=OSError("unavailable")):
            failed = search_materials("字幕")
        self.assertEqual(failed.materials, ())
        self.assertEqual(failed.error.code, "data_unavailable")

    def test_search_rejects_invalid_query_and_malformed_corpus(self):
        for query in ["", " ", None]:
            with self.subTest(query=query):
                self.assertIsInstance(search_materials(query), ToolError)
        self.assertEqual(search_materials("!!!").error.code, "invalid_arguments")
        duplicate = [self.materials[0], self.materials[0]]
        self.assertEqual(search_materials("字幕", materials=duplicate).error.code, "invalid_data")

    def test_estimate_accounts_for_speech_pauses_and_transitions(self):
        script = Script(3, "标题不朗读", [
            Shot("A", "画面不朗读", "甲乙丙丁，戊己庚辛。"),
            Shot("B", "画面不朗读", "甲乙丙丁戊己庚辛壬"),
        ])
        result = estimate_duration(script, 30)
        self.assertEqual([item.duration_seconds for item in result.shot_durations], [2.6, 2.55])
        self.assertAlmostEqual(result.total_duration_seconds, 5.15)
        self.assertEqual(result.script_version, 3)
        self.assertEqual(result.script_fingerprint, script.fingerprint)
        self.assertIn("4 字符/秒", result.method)

    def test_estimate_has_minimum_shot_time_and_excludes_title_visual(self):
        script = Script(1, "很长的标题" * 100, [Shot("A", "很长的画面" * 100, "甲"), Shot("B", "画面", "乙")])
        result = estimate_duration(script, 30)
        self.assertEqual([item.duration_seconds for item in result.shot_durations], [2, 2.3])

    def test_exact_30_seconds_passes_and_overshoot_fails(self):
        script = Script(1, "标题", [Shot("A", "画面", "字" * 120)])
        self.assertEqual(estimate_duration(script, 30).total_duration_seconds, 30)
        self.assertTrue(estimate_duration(script, 30).passed)
        longer = replace(script, version=2, shots=[replace(script.shots[0], narration="字" * 121)])
        result = estimate_duration(longer, 30)
        self.assertEqual(result.total_duration_seconds, 30.25)
        self.assertFalse(result.passed)
        self.assertTrue(result.matches(longer))

    def test_estimate_rejects_invalid_target(self):
        for value in [0, -1, True, "30", float("inf"), float("nan"), 10**400]:
            with self.subTest(value=repr(value)):
                self.assertIsInstance(estimate_duration(self.script, value), ToolError)

    def test_controlled_script_passes_real_rule_check(self):
        result = check_rules(self.script, self.materials, self.rules)
        self.assertTrue(result.passed)
        self.assertTrue(result.matches(self.script))
        self.assertIn("B01", result.checked_rule_ids)
        self.assertEqual(result.issues, ())

    def test_citation_does_not_support_new_function_metrics_or_negation(self):
        for text in ["支持自动识别字幕", "支持翻译字幕", "效率提升80%", "不支持为视频添加字幕"]:
            with self.subTest(text=text):
                self.assertIn("unsupported_expression", self.issues(self.changed_narration(text)))

    def test_unknown_citation_and_uncited_fact_are_reported(self):
        self.assertIn("unknown_source", self.issues(self.changed_narration("支持为视频添加字幕", ["P99"])))
        self.assertIn("missing_source", self.issues(self.changed_narration("支持为视频添加字幕", [])))

    def test_citation_in_another_shot_cannot_support_this_shot(self):
        intro = replace(self.script.shots[0], source_ids=["P01"])
        fact = replace(self.script.shots[1], source_ids=[])
        script = replace(self.script, shots=[intro, fact])
        self.assertIn("missing_source", self.issues(script))

    def test_title_and_visual_are_checked_too(self):
        self.assertIn("unsupported_expression", self.issues(replace(self.script, title="效率提升80%")))
        shot = replace(self.script.shots[1], visual="展示自动翻译功能")
        self.assertIn("unsupported_expression", self.issues(replace(self.script, shots=[shot])))

    def test_unknown_creative_expression_is_unverified_not_silently_accepted(self):
        result = check_rules(self.changed_narration("字幕像星星一样闪亮"), self.materials, self.rules)
        self.assertFalse(result.passed)
        self.assertIn("无法核验", result.issues[0].message)

    def test_numeric_fact_requires_its_own_source_not_blanket_numeric_ban(self):
        corpus = [*self.materials, Material("P02", "效率提升80%")]
        script = self.changed_narration("效率提升80%", ["P02"])
        self.assertTrue(check_rules(script, corpus, self.rules).passed)
        self.assertFalse(check_rules(self.changed_narration("效率提升80%", ["P01"]), corpus, self.rules).passed)

    def test_structured_brand_ban_is_enforced_even_with_valid_source(self):
        ban = BrandRule("B02", "禁用词列表", ["字幕"])
        result = check_rules(self.script, self.materials, [*self.rules, ban])
        self.assertFalse(result.passed)
        self.assertTrue(any(issue.rule_id == "B02" and issue.code == "forbidden_term" for issue in result.issues))

    def test_unknown_brand_rule_is_tool_error_not_a_passing_report(self):
        result = check_rules(self.script, self.materials, [BrandRule("B02", "必须介绍全部功能")])
        self.assertIsInstance(result, ToolError)
        self.assertEqual(result.code, "unsupported_rule")

    def test_malformed_rule_context_is_tool_error(self):
        self.assertIsInstance(check_rules(self.script, [self.materials[0]] * 2, self.rules), ToolError)
        self.assertIsInstance(check_rules(self.script, self.materials, [BrandRule("FACT-REF", "禁用", ["字幕"])]), ToolError)
        with self.assertRaises(ValueError):
            BrandRule("B02", "禁用", ["字幕", "字幕"])

    def test_new_tool_reports_allow_completion_and_old_reports_do_not(self):
        request = TaskInput(**json.loads((ROOT / "examples/normal/input.json").read_text()))
        duration = estimate_duration(self.script, request.target_duration_seconds)
        rules = check_rules(self.script, self.materials, self.rules)
        result = TaskResult("tool-unit-test", "mock", "completed", request, self.script, duration, rules)
        self.assertEqual(result.status, "completed")
        revised = replace(self.script, version=2)
        with self.assertRaisesRegex(ValueError, "version and content"):
            replace(result, script=revised)

    def test_script_loader_checks_read_only_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "script.json"
            data = self.script.to_dict()
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(load_script(path), self.script)
            data["fingerprint"] = "0" * 64
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                load_script(path)

    def cli(self, *arguments):
        result = subprocess.run(["python3", "-m", "src.tools", *arguments], cwd=ROOT, capture_output=True, text=True)
        self.assertFalse(result.stderr, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_three_tools_run_as_cli_commands(self):
        self.assertEqual(self.cli("search", "--query", "字幕", "--material-ids", "P01")[0], 0)
        code, duration = self.cli("estimate", "--script", str(SCRIPT_PATH), "--target-seconds", "30")
        self.assertEqual(code, 0)
        self.assertTrue(duration["passed"])
        code, rules = self.cli("check", "--script", str(SCRIPT_PATH))
        self.assertEqual(code, 0)
        self.assertTrue(rules["passed"])

    def test_cli_distinguishes_rejection_and_tool_error(self):
        code, duration = self.cli("estimate", "--script", str(SCRIPT_PATH), "--target-seconds", "1")
        self.assertEqual(code, 1)
        self.assertFalse(duration["passed"])
        code, failure = self.cli("search", "--query", "字幕", "--materials", "/missing/materials.json")
        self.assertEqual(code, 2)
        self.assertEqual(failure["code"], "data_unavailable")


if __name__ == "__main__":
    unittest.main()
