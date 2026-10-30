"""Read two repository modules into memory and validate this external data pack.

No .env, model client, repository imports, bytecode files or repository outputs.
Only the requested report directory is written, and it must be outside --repo.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import types

PACK = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_modules(repo):
    # A synthetic package prevents imports from executing src/__init__.py.
    name = "_readonly_campus_reference"
    package = types.ModuleType(name)
    package.__path__ = []
    sys.modules[name] = package
    loaded = {}
    for part in ("schemas", "tools"):
        path = repo / "src" / f"{part}.py"
        module = types.ModuleType(f"{name}.{part}")
        module.__package__ = name
        module.__file__ = str(path)
        sys.modules[module.__name__] = module
        # compile/exec from read-only bytes does not create __pycache__.
        exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
        loaded[part] = module
    return loaded["schemas"], loaded["tools"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--report-dir", type=Path, default=PACK / "verification")
    args = parser.parse_args()
    repo = args.repo.resolve()
    report_dir = args.report_dir.resolve()
    if report_dir == repo or report_dir.is_relative_to(repo):
        parser.error("report-dir must be outside the read-only repository")
    tracked = [repo / "src" / "schemas.py", repo / "src" / "tools.py",
               repo / "data" / "materials.json", repo / "data" / "brand_rules.json"]
    before = {str(p.relative_to(repo)): digest(p) for p in tracked}
    schemas, tools = source_modules(repo)
    records = []

    def record(name, passed, evidence=None, category="verification"):
        records.append({"name": name, "passed": bool(passed), "category": category, "evidence": evidence})

    def make_script(data):
        return schemas.Script(data["version"], data["title"], [schemas.Shot(**s) for s in data["shots"]])

    def one_fact(fact):
        return schemas.Script(1, fact.fact, [schemas.Shot("S01", "展示视频画面", fact.fact, [fact.id])])

    profiles = read_json(PACK / "profiles" / "index.json")
    metadata = read_json(PACK / "data" / "material_metadata.json")["materials"]
    sources = read_json(PACK / "data" / "sources.json")["sources"]
    source_ids = {s["id"] for s in sources}
    all_materials = tools.load_materials(PACK / "data" / "materials.json")
    all_rules = tools.load_brand_rules(PACK / "data" / "brand_rules.json")
    record("all_materials_load", len(all_materials) == 40, {"count": len(all_materials)})
    record("common_rules_load", len(all_rules) == 12, {"count": len(all_rules)})
    record("all_facts_have_source_metadata", len(metadata) == len(all_materials)
           and {m.id for m in all_materials} == {m["id"] for m in metadata}
           and all(m["source_id"] in source_ids and m["source_url"].startswith("https://") for m in metadata))

    loaded_profiles = {}
    for profile in profiles:
        name = profile["name"]
        folder = PACK / "profiles" / name
        materials = tools.load_materials(folder / "materials.json")
        rules = tools.load_brand_rules(folder / "brand_rules.json")
        manifest = read_json(folder / "manifest.json")
        loaded_profiles[name] = (materials, rules)
        expected = set(manifest["material_ids"])
        record(f"profile_load:{name}", len(materials) == profile["facts"]
               and len(rules) == profile["rules"] and {m.id for m in materials} == expected)
        for fact in materials:
            result = tools.check_rules(one_fact(fact), materials, rules)
            record(f"fact_accepted:{fact.id}", isinstance(result, schemas.RuleCheckResult) and result.passed,
                   result.to_dict())
        data = read_json(PACK / "examples" / name / "script.json")
        script = make_script(data)
        rule_result = tools.check_rules(script, materials, rules)
        duration = tools.estimate_duration(script, 30)
        record(f"example_checks:{name}", isinstance(rule_result, schemas.RuleCheckResult)
               and rule_result.passed and isinstance(duration, schemas.DurationResult) and duration.passed,
               {"rules": rule_result.to_dict(), "duration": duration.to_dict(),
                "provenance": "hand_authored_tool_fixture_not_model_generation"})

    materials, rules = loaded_profiles["capcut_web_captions"]
    base = read_json(PACK / "examples" / "capcut_web_captions" / "script.json")

    def negative(name, data, expected_rule=None, expected_code=None, context=None):
        mats, rs = context if context is not None else (materials, rules)
        result = tools.check_rules(make_script(data), mats, rs)
        found = isinstance(result, schemas.RuleCheckResult) and not result.passed and any(
            (expected_rule is None or issue.rule_id == expected_rule)
            and (expected_code is None or issue.code == expected_code) for issue in result.issues)
        record(name, found, result.to_dict())

    data = copy.deepcopy(base)
    data["shots"][0]["source_ids"] = ["P_DOES_NOT_EXIST"]
    negative("unknown_source_rejected", data, "FACT-REF", "unknown_source")

    data = copy.deepcopy(base)
    data["shots"][0]["source_ids"] = [materials[1].id]
    negative("wrong_existing_citation_rejected", data, "FACT-SUPPORT", "missing_source")

    data = copy.deepcopy(base)
    data["shots"][0]["narration"] = "它" + data["shots"][0]["narration"]
    negative("reasonable_paraphrase_is_out_of_scope", data, "FACT-SUPPORT", "unsupported_expression")

    data = copy.deepcopy(base)
    data["title"] = "给视频加字幕"
    for shot in data["shots"]:
        shot["narration"] = "今天聊聊视频字幕"
    negative("citations_without_expressed_fact_rejected", data, "FACT-SUPPORT", "no_grounded_fact")

    canva_fact = next(m for m in all_materials if m.id == "P_CAN_001")
    data = copy.deepcopy(base)
    data["shots"][0]["narration"] = canva_fact.fact
    data["shots"][0]["source_ids"] = [canva_fact.id]
    negative("cross_product_rejected_by_profile", data, "B_SCOPE_CAPCUT", "forbidden_term")

    desktop_fact = next(m for m in all_materials if m.id == "P_CAP_004")
    data = copy.deepcopy(base)
    data["shots"][0]["narration"] = desktop_fact.fact
    data["shots"][0]["source_ids"] = [desktop_fact.id]
    negative("wrong_surface_rejected_by_profile", data, "B_SURFACE_WEB", "forbidden_term")

    # Every listed literal must trigger its own rule, even if FACT-SUPPORT also fails.
    for rule in rules:
        for index, term in enumerate(rule.forbidden_terms):
            data = copy.deepcopy(base)
            data["shots"][0]["narration"] += term + "。"
            negative(f"literal:{rule.id}:{index}", data, rule.id, "forbidden_term")

    # Check scope rules not used by the first profile as well.
    for name in ("capcut_desktop_captions", "bcut_ios", "canva_web_view_only", "adobe_web_captions"):
        mats, rs = loaded_profiles[name]
        data = read_json(PACK / "examples" / name / "script.json")
        for rule in rs:
            if rule.id.startswith(("B_SCOPE_", "B_SURFACE_")) or rule.id == "B_CAN_VIEW_ONLY":
                changed = copy.deepcopy(data)
                changed["shots"][0]["narration"] += rule.forbidden_terms[0] + "。"
                negative(f"scope_literal:{name}:{rule.id}", changed, rule.id, "forbidden_term", (mats, rs))

    data = copy.deepcopy(base)
    data["shots"][0]["narration"] += "全 网 第 一。"
    negative("normalized_whitespace_forbidden_term", data, "B03", "forbidden_term")
    data = copy.deepcopy(base)
    data["shots"][0]["narration"] += "准确率９９％。"
    negative("normalized_fullwidth_forbidden_term", data, "B02", "forbidden_term")

    unknown_rule = schemas.BrandRule("B_FUTURE", "必须符合所有平台政策")
    result = tools.check_rules(make_script(base), materials, [unknown_rule])
    record("unsupported_natural_language_rule_returns_error",
           isinstance(result, schemas.ToolError) and result.code == "unsupported_rule", result.to_dict())

    first = tools.search_materials("请介绍字幕生成功能的完整业务流程", materials=materials)
    second = tools.search_materials("字幕", materials=materials)
    record("long_query_can_be_empty_then_keyword_retrieves", len(first.materials) == 0
           and len(second.materials) == len(materials), {"first": first.to_dict(), "second": second.to_dict(),
            "note": "人工调用的检索工具验证，不是模型自主改写查询的证据。"})
    empty = tools.search_materials("发票报销", materials=materials)
    record("unrelated_query_is_empty", len(empty.materials) == 0 and empty.error is None, empty.to_dict())

    # Document the real boundary: aggregating all brands removes product isolation.
    mixed = one_fact(canva_fact)
    result = tools.check_rules(mixed, all_materials, all_rules)
    record("known_boundary_unscoped_corpus_accepts_other_product", result.passed,
           {"result": result.to_dict(), "warning": "现有脚本契约没有目标产品字段；必须选择单产品 profile。"},
           category="documented_limitation")

    after = {str(p.relative_to(repo)): digest(p) for p in tracked}
    record("read_repository_files_unchanged", before == after, {"before": before, "after": after})
    report = {"verified_on": "2026-10-31", "python": sys.version,
              "scope": "data compatibility and deterministic tools only; no agent/model/network execution",
              "repository_read_only": True, "repository_source_sha256": before,
              "total_checks": len(records), "passed": sum(r["passed"] for r in records),
              "failed": sum(not r["passed"] for r in records), "checks": records}
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = (f"Checks: {report['total_checks']}; passed: {report['passed']}; failed: {report['failed']}\n"
               "Scope: data compatibility + existing deterministic tools; no model or Agent loop.\n"
               "Four read repository files have unchanged hashes. No repository file writes are performed.\n")
    (report_dir / "summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
