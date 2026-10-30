"""读取审阅过的独立资料配置；产品、客户端、来源元数据由本地配置提供。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from .schemas import BrandRule, Material, TaskInput
from .tools import load_brand_rules, load_materials

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/data_pack/short_video_data_pack"
REVIEW = ROOT / "data/pack_review.json"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _index(items, key="id"):
    if not isinstance(items, list) or any(not isinstance(x, dict) or not isinstance(x.get(key), str) or not x[key] for x in items):
        raise ValueError("配置索引格式无效")
    result = {x[key]: x for x in items}
    if len(result) != len(items):
        raise ValueError("配置索引 ID 重复")
    return result


@dataclass(frozen=True)
class DataProfile:
    name: str
    materials: tuple[Material, ...]
    brand_rules: tuple[BrandRule, ...]
    default_input: dict
    scope: dict
    material_metadata: dict
    excluded_material_ids: tuple[str, ...]
    evidence_files: tuple[Path, ...]


def list_profiles(pack=PACK, review=REVIEW):
    result = []
    for entry in _index(_read(Path(pack) / "profiles/index.json"), "name").values():
        profile = load_profile(entry["name"], pack=pack, review=review)
        result.append({"name": profile.name, **profile.scope,
                       "facts": len(profile.materials), "rules": len(profile.brand_rules),
                       "excluded_material_ids": list(profile.excluded_material_ids)})
    return result


def load_profile(name: str, *, pack=PACK, review=REVIEW) -> DataProfile:
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError("profile 名称无效")
    pack, review = Path(pack).resolve(), Path(review).resolve()
    index = _index(_read(pack / "profiles/index.json"), "name")
    if name not in index:
        raise ValueError("未知 profile；使用 --list-profiles 查看")
    folder = pack / "profiles" / name
    # 保持配置和摘要依赖在数据包中，禁止符号链接跳出资料范围。
    paths = [pack / "profiles/index.json", pack / "data/materials.json", pack / "data/material_metadata.json",
             pack / "data/products.json", pack / "data/sources.json", pack / "data/brand_rules.json",
             pack / "data/scope_rules.json", pack / "data/rule_metadata.json",
             folder / "manifest.json", folder / "input.json", folder / "materials.json", folder / "brand_rules.json"]
    if any(not p.resolve().is_relative_to(pack) for p in paths):
        raise ValueError("profile 文件超出数据包目录")
    manifest = _read(folder / "manifest.json")
    item = index[name]
    for key, expected in (("profile", name), ("product_id", item["product_id"]), ("surface", item["surface"])):
        if manifest.get(key) != expected:
            raise ValueError("profile 范围与索引不一致")
    products = _index(_read(pack / "data/products.json"))
    product = products[manifest["product_id"]]
    if manifest["surface"] not in product["surfaces"]:
        raise ValueError("profile 客户端不属于产品范围")
    materials = load_materials(folder / "materials.json")
    rules = load_brand_rules(folder / "brand_rules.json")
    global_materials = {m.id: m for m in load_materials(pack / "data/materials.json")}
    global_rules = {r.id: r for r in (*load_brand_rules(pack / "data/brand_rules.json"), *load_brand_rules(pack / "data/scope_rules.json"))}
    if ([m.id for m in materials] != manifest["material_ids"] or len(materials) != item["facts"]
            or any(global_materials.get(m.id) != m for m in materials)):
        raise ValueError("profile 素材与总表或清单不一致")
    if ([r.id for r in rules] != manifest["brand_rule_ids"] or len(rules) != item["rules"]
            or any(global_rules.get(r.id) != r for r in rules)):
        raise ValueError("profile 规则与总表或清单不一致")
    # 单产品/单端规则必须随配置完整加载，不能由模型检索或绕过。
    scope_rule = {"capcut": "B_SCOPE_CAPCUT", "canva": "B_SCOPE_CANVA",
                  "adobe_express": "B_SCOPE_ADOBE_EXPRESS", "bcut": "B_SCOPE_BCUT"}[product["id"]]
    surface_rule = {"web": "B_SURFACE_WEB", "desktop": "B_SURFACE_DESKTOP", "ios": "B_SURFACE_IOS"}[manifest["surface"]]
    required = {"B01", scope_rule, surface_rule, *[r.id for r in load_brand_rules(pack / "data/brand_rules.json")]}
    if name == "canva_web_view_only":
        required.add("B_CAN_VIEW_ONLY")
    if not required.issubset(r.id for r in rules):
        raise ValueError("profile 缺少必需规则")
    metadata = _index(_read(pack / "data/material_metadata.json")["materials"])
    sources = _index(_read(pack / "data/sources.json")["sources"])
    if set(metadata) != set(global_materials):
        raise ValueError("素材元数据未完整覆盖总表")
    rule_metadata = _index(_read(pack / "data/rule_metadata.json")["rules"])
    if any(r.id not in rule_metadata for r in rules):
        raise ValueError("规则缺少来源类型与检查边界")
    decision = _read(review)
    if decision.get("schema_version") != "1.0" or not isinstance(decision.get("excluded_materials"), dict):
        raise ValueError("资料审阅配置无效")
    excluded = decision["excluded_materials"]
    if set(excluded) - set(global_materials) or any(not isinstance(v, str) or not v.strip() for v in excluded.values()):
        raise ValueError("排除素材无效")
    selected = {}
    for material in materials:
        info = metadata[material.id]
        source = sources[info["source_id"]]
        if (info["approved_text"] != material.fact or info["product_id"] != product["id"]
                or manifest["surface"] not in info["surfaces"] or info["source_url"] != source["url"]
                or not source["url"].startswith("https://") or info["source_id"] not in manifest["source_ids"]):
            raise ValueError("素材事实、范围或来源不一致")
        date.fromisoformat(info["verified_on"])
        if material.id not in excluded:
            selected[material.id] = {**info, "source_title": source["title"], "source_publisher": source["publisher"],
                                     "rule_origin": "project_authored_demo_policy"}
    if not selected:
        raise ValueError("profile 没有审阅后可使用的素材")
    default_input = _read(folder / "input.json")
    TaskInput(**default_input)
    scope = {"profile": name, "product_id": product["id"], "product_name": product["name"],
             "surface": manifest["surface"], "feature_scopes": sorted({x["feature_scope"] for x in selected.values()}),
             "rule_origin": "project_authored_demo_policy", "conditions": product["note"]}
    return DataProfile(name, tuple(m for m in materials if m.id in selected), rules, default_input, scope,
                       selected, tuple(m.id for m in materials if m.id in excluded), tuple([*paths, review]))
