"""程序交换的数据约定；检查同时绑定版本和内容，完成状态必须有匹配的检查。

这里只校验数据及检查结果的一致性，不执行估时、事实判断或模型调用。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
import re


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _positive(value: float, name: str) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")


def _items(value, item_type: type, name: str, *, required: bool = False) -> tuple:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{name} must be a list or tuple")
    items = tuple(value)
    if required and not items:
        raise ValueError(f"{name} must not be empty")
    if any(not isinstance(item, item_type) for item in items):
        raise ValueError(f"{name} contains an invalid item type")
    return items


def _ids(value, name: str, *, required: bool = False) -> tuple[str, ...]:
    items = _items(value, str, name, required=required)
    for item in items:
        _text(item, name)
    if len(set(items)) != len(items):
        raise ValueError(f"{name} must be unique")
    return items


def _unique_ids(items: tuple, attribute: str, name: str) -> None:
    values = [getattr(item, attribute) for item in items]
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must be unique")


def _version(value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("script version must be a positive integer")


class JsonRecord:
    def to_dict(self) -> dict:
        """输出 JSON 兼容字典，包括派生字段；列表在内部保存为不可变 tuple。"""
        return json.loads(json.dumps(asdict(self), ensure_ascii=False, allow_nan=False))


@dataclass(frozen=True)
class TaskInput(JsonRecord):
    topic: str
    audience: str
    platform: str
    target_duration_seconds: float
    style: str

    def __post_init__(self) -> None:
        for name in ("topic", "audience", "platform", "style"):
            _text(getattr(self, name), name)
        _positive(self.target_duration_seconds, "target_duration_seconds")


@dataclass(frozen=True)
class Material(JsonRecord):
    id: str
    fact: str

    def __post_init__(self) -> None:
        _text(self.id, "material id")
        _text(self.fact, "fact")


@dataclass(frozen=True)
class BrandRule(JsonRecord):
    id: str
    rule: str
    forbidden_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.id, "rule id")
        _text(self.rule, "rule")
        object.__setattr__(self, "forbidden_terms", _ids(self.forbidden_terms, "forbidden_terms"))


@dataclass(frozen=True)
class Shot(JsonRecord):
    id: str
    visual: str
    narration: str
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("id", "visual", "narration"):
            _text(getattr(self, name), name)
        object.__setattr__(self, "source_ids", _ids(self.source_ids, "source_ids"))


@dataclass(frozen=True)
class Script(JsonRecord):
    version: int
    title: str
    shots: tuple[Shot, ...]
    source_ids: tuple[str, ...] = field(init=False)
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        _version(self.version)
        _text(self.title, "title")
        shots = _items(self.shots, Shot, "shots", required=True)
        _unique_ids(shots, "id", "shot IDs")
        object.__setattr__(self, "shots", shots)
        sources = tuple(dict.fromkeys(source for shot in shots for source in shot.source_ids))
        object.__setattr__(self, "source_ids", sources)
        content = {"title": self.title, "shots": [shot.to_dict() for shot in shots]}
        canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        object.__setattr__(self, "fingerprint", hashlib.sha256(canonical.encode("utf-8")).hexdigest())


@dataclass(frozen=True)
class CheckBinding(JsonRecord):
    script_version: int
    script_fingerprint: str

    def __post_init__(self) -> None:
        _version(self.script_version)
        if not isinstance(self.script_fingerprint, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.script_fingerprint
        ):
            raise ValueError("script_fingerprint must be a SHA-256 hex digest")

    def matches(self, script: Script) -> bool:
        return self.script_version == script.version and self.script_fingerprint == script.fingerprint


@dataclass(frozen=True)
class ShotDuration(JsonRecord):
    shot_id: str
    duration_seconds: float

    def __post_init__(self) -> None:
        _text(self.shot_id, "shot_id")
        _positive(self.duration_seconds, "duration_seconds")


@dataclass(frozen=True)
class DurationResult(CheckBinding):
    shot_durations: tuple[ShotDuration, ...]
    target_duration_seconds: float
    method: str
    total_duration_seconds: float = field(init=False)
    passed: bool = field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        _positive(self.target_duration_seconds, "target_duration_seconds")
        _text(self.method, "duration method")
        durations = _items(self.shot_durations, ShotDuration, "shot_durations", required=True)
        _unique_ids(durations, "shot_id", "duration shot IDs")
        object.__setattr__(self, "shot_durations", durations)
        try:
            total = math.fsum(item.duration_seconds for item in durations)
        except OverflowError as exc:
            raise ValueError("total duration must be finite") from exc
        _positive(total, "total_duration_seconds")
        object.__setattr__(self, "total_duration_seconds", total)
        object.__setattr__(self, "passed", total <= self.target_duration_seconds)


@dataclass(frozen=True)
class RuleIssue(JsonRecord):
    rule_id: str
    code: str
    message: str
    shot_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("rule_id", "code", "message"):
            _text(getattr(self, name), name)
        if self.shot_id is not None:
            _text(self.shot_id, "shot_id")


@dataclass(frozen=True)
class RuleCheckResult(CheckBinding):
    checked_rule_ids: tuple[str, ...]
    issues: tuple[RuleIssue, ...] = ()
    passed: bool = field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        rules = _ids(self.checked_rule_ids, "checked_rule_ids", required=True)
        issues = _items(self.issues, RuleIssue, "issues")
        if any(issue.rule_id not in rules for issue in issues):
            raise ValueError("issue refers to a rule that was not checked")
        object.__setattr__(self, "checked_rule_ids", rules)
        object.__setattr__(self, "issues", issues)
        object.__setattr__(self, "passed", not issues)


@dataclass(frozen=True)
class ToolError(JsonRecord):
    tool: str
    code: str
    message: str
    retryable: bool = False

    def __post_init__(self) -> None:
        for name in ("tool", "code", "message"):
            _text(getattr(self, name), name)
        if type(self.retryable) is not bool:
            raise ValueError("retryable must be a boolean")


@dataclass(frozen=True)
class SearchResult(JsonRecord):
    query: str
    materials: tuple[Material, ...] = ()
    error: ToolError | None = None

    def __post_init__(self) -> None:
        _text(self.query, "query")
        materials = _items(self.materials, Material, "materials")
        _unique_ids(materials, "id", "material IDs")
        object.__setattr__(self, "materials", materials)
        if self.error is not None:
            if not isinstance(self.error, ToolError) or materials:
                raise ValueError("failed search must contain a ToolError and no materials")


class TaskStatus(str, Enum):
    COMPLETED = "completed"
    NEEDS_INPUT = "needs_input"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class RunMode(str, Enum):
    REAL = "real"
    MOCK = "mock"


@dataclass(frozen=True)
class TaskResult(JsonRecord):
    run_id: str
    mode: RunMode
    status: TaskStatus
    task_input: TaskInput | None = None
    script: Script | None = None
    duration_result: DurationResult | None = None
    rule_check_result: RuleCheckResult | None = None
    risks: tuple[str, ...] = ()
    reason: str | None = None
    missing_fields: tuple[str, ...] = ()
    errors: tuple[ToolError, ...] = ()

    def __post_init__(self) -> None:
        _text(self.run_id, "run_id")
        object.__setattr__(self, "mode", RunMode(self.mode))
        object.__setattr__(self, "status", TaskStatus(self.status))
        for name, kind in (
            ("task_input", TaskInput), ("script", Script),
            ("duration_result", DurationResult), ("rule_check_result", RuleCheckResult),
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, kind):
                raise ValueError(f"{name} has an invalid type")
        risks = _items(self.risks, str, "risks")
        for risk in risks:
            _text(risk, "risk")
        object.__setattr__(self, "risks", risks)
        object.__setattr__(self, "missing_fields", _ids(self.missing_fields, "missing_fields"))
        object.__setattr__(self, "errors", _items(self.errors, ToolError, "errors"))
        if self.reason is not None:
            _text(self.reason, "reason")
        for report in (self.duration_result, self.rule_check_result):
            if report is not None and (self.script is None or not report.matches(self.script)):
                raise ValueError("check result does not match the final script version and content")
        if self.script is not None:
            shot_ids = {shot.id for shot in self.script.shots}
            if self.duration_result is not None and shot_ids != {
                item.shot_id for item in self.duration_result.shot_durations
            }:
                raise ValueError("duration results must cover exactly the final script shots")
            if self.rule_check_result is not None and any(
                issue.shot_id is not None and issue.shot_id not in shot_ids
                for issue in self.rule_check_result.issues
            ):
                raise ValueError("rule issue refers to an unknown shot")
        if self.status is TaskStatus.COMPLETED:
            if any(value is None for value in (
                self.task_input, self.script, self.duration_result, self.rule_check_result
            )):
                raise ValueError("completed task requires input, script and both check results")
            if not self.duration_result.passed or not self.rule_check_result.passed:
                raise ValueError("completed task requires passing checks")
            if self.duration_result.target_duration_seconds != self.task_input.target_duration_seconds:
                raise ValueError("duration check must use the requested time limit")
            if not self.script.source_ids:
                raise ValueError("completed task requires material references")
            if self.errors or self.missing_fields:
                raise ValueError("completed task cannot have unresolved errors or missing fields")
        elif self.reason is None:
            raise ValueError("non-completed task requires a reason")
