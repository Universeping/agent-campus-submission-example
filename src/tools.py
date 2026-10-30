"""可独立运行的确定性工具；规则检查仅覆盖明确声明的受控表达。"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import unicodedata

from .schemas import (
    BrandRule, DurationResult, Material, RuleCheckResult, RuleIssue,
    Script, SearchResult, Shot, ShotDuration, ToolError,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
FACT_RULE = "不得虚构功能或效果数据"
REFERENCE_RULE_ID = "FACT-REF"
SUPPORT_RULE_ID = "FACT-SUPPORT"

# 项目自定的受控表达，不是平台规定，也不是真实产品事实。
ALLOWED_TITLES = ("给视频加字幕", "视频字幕小课堂", "新手字幕入门", "字幕功能介绍")
ALLOWED_VISUALS = ("字幕示意画面", "展示视频画面", "展示字幕示意画面", "片尾提示画面", "标题卡片")
ALLOWED_NARRATION = (
    "今天聊聊视频字幕", "先看看示意画面", "我们开始吧",
    "你会给视频加字幕吗", "给视频加字幕",
)

TIMING_METHOD = (
    "timing-v1：旁白中每个字母或数字（含汉字）按 4 字符/秒计；"
    "逗号/顿号/分号/冒号每个停顿 0.2 秒，句号/问号/感叹号每个 0.4 秒；"
    "每镜至少 2 秒，第二镜起每镜另加转场 0.3 秒；每镜向上取整至 0.01 秒。"
    "标题和画面描述不朗读，数字和外语逐字符估算；不是实际配音时长。"
)


def _normalize(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def _clause(text: str) -> str:
    return _normalize(text).strip("，,。.!！?？；;：:、")


def _records(items, kind: type, name: str) -> tuple:
    if not isinstance(items, (list, tuple)) or any(not isinstance(item, kind) for item in items):
        raise ValueError(f"{name} must be a list or tuple of {kind.__name__}")
    records = tuple(items)
    if len({item.id for item in records}) != len(records):
        raise ValueError(f"{name} IDs must be unique")
    return records


def _load_records(path: str | Path, kind: type) -> tuple:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ValueError("data file must contain an array of objects")
    return _records([kind(**item) for item in data], kind, "records")


def load_materials(path: str | Path = DATA_DIR / "materials.json") -> tuple[Material, ...]:
    return _load_records(path, Material)


def load_brand_rules(path: str | Path = DATA_DIR / "brand_rules.json") -> tuple[BrandRule, ...]:
    return _load_records(path, BrandRule)


def load_script(path: str | Path) -> Script:
    """读取原始脚本 JSON，也可读取含派生字段的 Script.to_dict() 输出。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) - {"version", "title", "shots", "source_ids", "fingerprint"}:
        raise ValueError("invalid script object or unknown fields")
    if not isinstance(data.get("shots"), list) or any(not isinstance(shot, dict) for shot in data["shots"]):
        raise ValueError("shots must be an array of objects")
    script = Script(data["version"], data["title"], [Shot(**shot) for shot in data["shots"]])
    for name in ("source_ids", "fingerprint"):
        if name in data and data[name] != script.to_dict()[name]:
            raise ValueError(f"supplied {name} does not match the script")
    return script


def search_materials(
    query: str, material_ids: list[str] | tuple[str, ...] | None = None,
    *, materials: list[Material] | tuple[Material, ...] | None = None,
) -> SearchResult | ToolError:
    """对空白分隔的关键词做 OR 子串匹配；material_ids 是可选 ID 白名单。"""
    if not isinstance(query, str) or not query.strip():
        return ToolError("search_materials", "invalid_arguments", "query 必须是非空字符串")
    terms = [_normalize(term) for term in query.split()]
    if not any(any(char.isalnum() for char in term) for term in terms):
        return SearchResult(query, error=ToolError("search_materials", "invalid_arguments", "查询需包含有效关键词"))
    try:
        corpus = load_materials() if materials is None else _records(materials, Material, "materials")
        if material_ids is not None:
            if not isinstance(material_ids, (list, tuple)) or any(
                not isinstance(item, str) or not item.strip() for item in material_ids
            ):
                raise ValueError("material_ids 必须是 ID 列表；None 表示全部，空列表表示不允许任何素材")
            if len(set(material_ids)) != len(material_ids):
                raise ValueError("material_ids 不得重复")
            unknown = set(material_ids) - {material.id for material in corpus}
            if unknown:
                return SearchResult(query, error=ToolError(
                    "search_materials", "unknown_material_id", "未知素材 ID：" + ", ".join(sorted(unknown))
                ))
            corpus = tuple(material for material in corpus if material.id in material_ids)
        matches = tuple(material for material in corpus if any(
            term in _normalize(material.id + " " + material.fact) for term in terms
        ))
        return SearchResult(query, matches)
    except OSError:
        return SearchResult(query, error=ToolError("search_materials", "data_unavailable", "素材文件不可读"))
    except (ValueError, TypeError) as exc:
        return SearchResult(query, error=ToolError("search_materials", "invalid_data", str(exc)))


def estimate_duration(script: Script, target_seconds: float) -> DurationResult | ToolError:
    if not isinstance(script, Script):
        return ToolError("estimate_duration", "invalid_arguments", "script 必须是 Script")
    try:
        valid_target = type(target_seconds) in (int, float) and math.isfinite(target_seconds) and target_seconds > 0
    except OverflowError:
        valid_target = False
    if not valid_target:
        return ToolError("estimate_duration", "invalid_arguments", "target_seconds 必须是有限正数")
    timings = []
    for index, shot in enumerate(script.shots):
        text = unicodedata.normalize("NFKC", shot.narration)
        characters = sum(char.isalnum() for char in text)
        short_pauses = sum(char in ",、;:" for char in text)
        long_pauses = sum(char in ".。!?" for char in text)
        # 用整数百分秒累计，避免浮点舍入改变分镜时长。
        centiseconds = max(200, characters * 25 + short_pauses * 20 + long_pauses * 40)
        centiseconds += 30 if index else 0
        timings.append(ShotDuration(shot.id, centiseconds / 100))
    return DurationResult(script.version, script.fingerprint, timings, target_seconds, TIMING_METHOD)


def check_rules(
    script: Script, materials: list[Material] | tuple[Material, ...],
    brand_rules: list[BrandRule] | tuple[BrandRule, ...],
) -> RuleCheckResult | ToolError:
    """事实句匹配所引素材原文；其余表达仅允许声明的封闭列表。"""
    if not isinstance(script, Script):
        return ToolError("check_rules", "invalid_arguments", "script 必须是 Script")
    try:
        corpus = _records(materials, Material, "materials")
        rules = _records(brand_rules, BrandRule, "brand_rules")
    except ValueError as exc:
        return ToolError("check_rules", "invalid_arguments", str(exc))
    reserved = {REFERENCE_RULE_ID, SUPPORT_RULE_ID}
    for rule in rules:
        if rule.id in reserved:
            return ToolError("check_rules", "invalid_rules", "品牌规则 ID 与内置事实规则冲突")
        if not rule.forbidden_terms and _clause(rule.rule) != _clause(FACT_RULE):
            return ToolError("check_rules", "unsupported_rule", f"规则 {rule.id} 未实现；请提供 forbidden_terms 或支持的事实约束")
    by_id = {material.id: material for material in corpus}
    all_facts = {_clause(material.fact) for material in corpus}
    issues = []
    grounded_facts = set()

    def check_text(text: str, sources: tuple[str, ...], allowed: tuple[str, ...], location: str, shot_id=None):
        supported = {_clause(by_id[source].fact) for source in sources if source in by_id}
        neutral = {_clause(item) for item in allowed}
        for part in re.split(r"[。！？!?；;\n]+", text):
            value = _clause(part)
            if not value:
                continue
            if value in supported:
                grounded_facts.add(value)
                continue
            if value in neutral:
                continue
            code = "missing_source" if value in all_facts else "unsupported_expression"
            issues.append(RuleIssue(
                SUPPORT_RULE_ID, code,
                f"{location}“{part.strip()}”无法核验；事实句需逐句使用所引素材原文，创意表达需使用首版允许列表。",
                shot_id,
            ))

    check_text(script.title, script.source_ids, ALLOWED_TITLES, "标题")
    for shot in script.shots:
        for source in shot.source_ids:
            if source not in by_id:
                issues.append(RuleIssue(REFERENCE_RULE_ID, "unknown_source", f"素材 {source} 不存在", shot.id))
        check_text(shot.visual, shot.source_ids, ALLOWED_VISUALS, "画面", shot.id)
        check_text(shot.narration, shot.source_ids, ALLOWED_NARRATION, "旁白", shot.id)
    if script.source_ids and not grounded_facts:
        issues.append(RuleIssue(SUPPORT_RULE_ID, "no_grounded_fact", "引用了素材但未实际表达任何有依据的事实，请使用所引素材原文。"))
    fields = [(None, "标题", script.title)] + [
        (shot.id, name, value)
        for shot in script.shots
        for name, value in (("画面", shot.visual), ("旁白", shot.narration))
    ]
    for rule in rules:
        for shot_id, location, text in fields:
            for term in rule.forbidden_terms:
                if _normalize(term) in _normalize(text):
                    issues.append(RuleIssue(rule.id, "forbidden_term", f"{location}包含禁用表达“{term}”", shot_id))
    checked_ids = [REFERENCE_RULE_ID, SUPPORT_RULE_ID, *(rule.id for rule in rules)]
    return RuleCheckResult(script.version, script.fingerprint, checked_ids, issues)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="关键词检索")
    search.add_argument("--query", required=True)
    search.add_argument("--material-ids", nargs="*")
    search.add_argument("--materials", type=Path, default=DATA_DIR / "materials.json")
    estimate = commands.add_parser("estimate", help="估算脚本时长")
    estimate.add_argument("--script", required=True, type=Path)
    estimate.add_argument("--target-seconds", required=True, type=float)
    check = commands.add_parser("check", help="检查来源和受控表达")
    check.add_argument("--script", required=True, type=Path)
    check.add_argument("--materials", type=Path, default=DATA_DIR / "materials.json")
    check.add_argument("--brand-rules", type=Path, default=DATA_DIR / "brand_rules.json")
    args = parser.parse_args(argv)
    tool_name = {"search": "search_materials", "estimate": "estimate_duration", "check": "check_rules"}[args.command]
    try:
        if args.command == "search":
            result = search_materials(args.query, args.material_ids, materials=load_materials(args.materials))
        elif args.command == "estimate":
            result = estimate_duration(load_script(args.script), args.target_seconds)
        else:
            result = check_rules(load_script(args.script), load_materials(args.materials), load_brand_rules(args.brand_rules))
    except OSError:
        result = ToolError(tool_name, "data_unavailable", "输入文件不可读")
    except (ValueError, TypeError, KeyError) as exc:
        result = ToolError(tool_name, "invalid_data", str(exc))
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    if isinstance(result, ToolError) or isinstance(result, SearchResult) and result.error is not None:
        return 2
    return 1 if hasattr(result, "passed") and not result.passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
