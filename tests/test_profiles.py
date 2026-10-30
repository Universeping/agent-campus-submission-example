"""真实资料配置的契约、隔离和本地工具测试；不证明真实模型效果。"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from src.agent import AgentRunner
from src.model import MockModel
from src.profiles import PACK, REVIEW, list_profiles, load_profile
from src.schemas import Script, Shot, RuleCheckResult
from src.tools import check_rules, estimate_duration, load_script, search_materials

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False))


class ProfileTests(unittest.TestCase):
    def test_registry_keeps_eight_profiles_and_excludes_one_ambiguous_fact(self):
        profiles = list_profiles()
        self.assertEqual(len(profiles), 8)
        self.assertEqual(sum(p["facts"] for p in profiles), 39)
        self.assertEqual({p["product_id"] for p in profiles}, {"capcut", "canva", "adobe_express", "bcut"})
        self.assertEqual(load_profile("canva_web_view_only").excluded_material_ids, ("P_CAN_010",))

    def test_all_accepted_facts_have_matching_sources_and_pass_actual_tools(self):
        for entry in list_profiles():
            profile = load_profile(entry["name"])
            for material in profile.materials:
                with self.subTest(material=material.id):
                    info = profile.material_metadata[material.id]
                    self.assertEqual(info["approved_text"], material.fact)
                    self.assertEqual(info["product_id"], profile.scope["product_id"])
                    self.assertIn(profile.scope["surface"], info["surfaces"])
                    self.assertTrue(info["source_url"].startswith("https://"))
                    script = Script(1, material.fact, [Shot("S1", "展示视频画面", material.fact, [material.id])])
                    result = check_rules(script, profile.materials, profile.brand_rules)
                    self.assertIsInstance(result, RuleCheckResult)
                    self.assertTrue(result.passed)
                    self.assertTrue(estimate_duration(script, 30).passed)

    def test_eight_original_hand_authored_fixtures_pass_with_reviewed_profiles(self):
        for entry in list_profiles():
            with self.subTest(profile=entry["name"]):
                profile = load_profile(entry["name"])
                script = load_script(PACK / "examples" / profile.name / "script.json")
                self.assertTrue(check_rules(script, profile.materials, profile.brand_rules).passed)
                self.assertTrue(estimate_duration(script, profile.default_input["target_duration_seconds"]).passed)

    def test_unknown_name_and_path_traversal_are_rejected(self):
        for name in ("missing", "../bcut_ios", "/tmp/bcut_ios"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                load_profile(name)

    def tamper(self, change):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / "pack"
            shutil.copytree(PACK, pack)
            change(pack)
            with self.assertRaises((ValueError, KeyError)):
                load_profile("capcut_web_captions", pack=pack)

    def test_wrong_product_metadata_is_rejected(self):
        def change(pack):
            p = pack / "data/material_metadata.json"
            data = read(p); data["materials"][0]["product_id"] = "canva"; write(p, data)
        self.tamper(change)

    def test_wrong_source_url_is_rejected(self):
        def change(pack):
            p = pack / "data/material_metadata.json"
            data = read(p); data["materials"][0]["source_url"] = "https://example.invalid"; write(p, data)
        self.tamper(change)

    def test_duplicate_source_metadata_id_is_rejected(self):
        def change(pack):
            p = pack / "data/material_metadata.json"
            data = read(p); data["materials"].append(data["materials"][0]); write(p, data)
        self.tamper(change)

    def test_removing_mandatory_rule_cannot_be_hidden_by_editing_manifest(self):
        def change(pack):
            folder = pack / "profiles/capcut_web_captions"
            p = folder / "brand_rules.json"; write(p, [r for r in read(p) if r["id"] != "B02"])
            p = folder / "manifest.json"; data = read(p); data["brand_rule_ids"].remove("B02"); write(p, data)
            p = pack / "profiles/index.json"; data = read(p)
            next(x for x in data if x["name"] == "capcut_web_captions")["rules"] -= 1; write(p, data)
        self.tamper(change)

    def test_profile_rule_cannot_silently_clear_forbidden_terms(self):
        def change(pack):
            p = pack / "profiles/capcut_web_captions/brand_rules.json"
            data = read(p); data[1]["forbidden_terms"] = []; write(p, data)
        self.tamper(change)

    def test_quarantined_fact_cannot_be_retrieved(self):
        profile = load_profile("canva_web_view_only")
        result = search_materials("Canva", materials=profile.materials)
        self.assertNotIn("P_CAN_010", {m.id for m in result.materials})
        rejected = search_materials("Canva", ["P_CAN_010"], materials=profile.materials)
        self.assertEqual(rejected.error.code, "unknown_material_id")

    def test_canva_caption_modes_have_disjoint_fact_sets(self):
        editable = load_profile("canva_web_editable")
        view = load_profile("canva_web_view_only")
        self.assertFalse({m.id for m in editable.materials} & {m.id for m in view.materials})
        fact = editable.materials[0]
        script = Script(1, fact.fact, [Shot("S1", "展示视频画面", fact.fact, [fact.id])])
        result = check_rules(script, view.materials, view.brand_rules)
        self.assertFalse(result.passed)
        self.assertTrue(any(i.rule_id == "B_CAN_VIEW_ONLY" for i in result.issues))

    def test_cross_product_and_client_fact_cannot_pass_selected_profile(self):
        web = load_profile("capcut_web_captions")
        for other in ("canva_web_editable", "capcut_desktop_captions"):
            fact = load_profile(other).materials[0]
            script = Script(1, fact.fact, [Shot("S1", "展示视频画面", fact.fact, [fact.id])])
            result = check_rules(script, web.materials, web.brand_rules)
            self.assertFalse(result.passed)
            self.assertTrue(any(i.code == "unknown_source" for i in result.issues))

    def test_provenance_only_enters_model_snapshot_after_actual_search(self):
        profile = load_profile("capcut_web_captions")
        runner = AgentRunner(MockModel(), profile.materials, profile.brand_rules,
                             data_scope=profile.scope, material_metadata=profile.material_metadata)
        from src.trace import TraceRecorder
        trace = TraceRecorder("profile-snapshot")
        state = runner._prepare(runner.initial_state(profile.default_input), trace)
        self.assertEqual(runner.snapshot(state)["retrieved_material_metadata"], [])
        observation = runner._execute(state, trace, "search_materials", {"query": "字幕"})
        self.assertEqual({m["id"] for m in observation["material_metadata"]}, {m.id for m in profile.materials})
        self.assertEqual(len(runner.snapshot(state)["retrieved_material_metadata"]), 3)
        profile.scope["product_id"] = "tampered"
        self.assertEqual(runner.snapshot(state)["data_scope"]["product_id"], "capcut")

    def test_mismatched_provenance_cannot_be_injected_into_runner(self):
        profile = load_profile("bcut_ios")
        metadata = deepcopy(profile.material_metadata)
        metadata["P_BCT_001"]["approved_text"] = "invented"
        with self.assertRaises(ValueError):
            AgentRunner(MockModel(), profile.materials, profile.brand_rules, material_metadata=metadata)


@unittest.skipUnless(importlib.util.find_spec("langgraph"), "profile integration requires LangGraph")
class ProfileIntegrationTests(unittest.TestCase):
    def test_all_profiles_complete_mock_loop_with_actual_tools_and_all_rules(self):
        for entry in list_profiles():
            with self.subTest(profile=entry["name"]):
                profile = load_profile(entry["name"])
                run = AgentRunner(MockModel(), profile.materials, profile.brand_rules,
                                  data_scope=profile.scope, material_metadata=profile.material_metadata).run(profile.default_input)
                self.assertEqual(run.result.status.value, "completed")
                self.assertTrue(set(run.result.script.source_ids).issubset(profile.material_metadata))
                self.assertTrue({r.id for r in profile.brand_rules}.issubset(run.result.rule_check_result.checked_rule_ids))

    def test_cli_list_does_not_require_input_or_model_configuration(self):
        run = subprocess.run([sys.executable, "-m", "src.main", "--list-profiles", "--env-file", "/not/existing"],
                             cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(len(json.loads(run.stdout)), 8)

    def test_cli_profile_default_input_exports_only_cited_source_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            run = subprocess.run([sys.executable, "-m", "src.main", "--profile", "bcut_ios", "--mode", "mock",
                                  "--output-dir", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = read(output / "result.json"); sources = read(output / "sources.json"); metadata = read(output / "run.json")
            self.assertEqual(set(sources), set(result["script"]["source_ids"]))
            self.assertEqual(metadata["data_profile"]["surface"], "ios")
            self.assertTrue(sources["P_BCT_001"]["source_url"].startswith("https://apps.apple.com/"))
            self.assertIn(sources["P_BCT_001"]["source_url"], (output / "script.md").read_text())
            self.assertIn("data/pack_review.json", metadata["sha256"])

    def test_cli_profile_cannot_be_combined_with_material_or_rule_overrides(self):
        for flag, path in (("--materials", "data/materials.json"), ("--brand-rules", "data/brand_rules.json")):
            run = subprocess.run([sys.executable, "-m", "src.main", "--profile", "bcut_ios", flag, path],
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("不能", run.stderr)


if __name__ == "__main__":
    unittest.main()
