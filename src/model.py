"""DeepSeek Chat Completions 接入、六动作声明及明确标记的离线模型。

传输只使用标准库，不自动重试；重试计数由 Agent 统一控制。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import socket
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .schemas import RunMode, ToolError

ROOT = Path(__file__).resolve().parents[1]


def _object(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required, "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1}
STRINGS = {"type": "array", "items": TEXT, "uniqueItems": True}
REASON = {**TEXT, "description": "一句简短行动依据，不输出内部思维过程。"}
SHOT = _object({"id": TEXT, "visual": TEXT, "narration": TEXT, "source_ids": STRINGS})
ACTION_PARAMETERS = {
    "search_materials": _object({"query": TEXT, "material_ids": STRINGS, "reason": REASON}, ["query", "reason"]),
    "save_script": _object({"title": TEXT, "shots": {"type": "array", "items": SHOT, "minItems": 1}, "reason": REASON}),
    "estimate_duration": _object({"script_version": {"type": "integer", "minimum": 1}, "reason": REASON}),
    "check_rules": _object({"script_version": {"type": "integer", "minimum": 1}, "reason": REASON}),
    "request_input": _object({"missing_fields": {**STRINGS, "minItems": 1}, "questions": {**STRINGS, "minItems": 1}, "reason": REASON}),
    "finish": _object({"status": {"type": "string", "enum": ["completed", "incomplete"]}, "reason": REASON}),
}
ACTION_DESCRIPTIONS = {
    "search_materials": "按关键词检索允许范围内的产品事实；空结果时可改写查询或请求补充。省略范围使用允许全集。",
    "save_script": "提交完整新稿或修订稿。程序分配版本和指纹，新稿必须重新估时和检查规则。不能自报检查结果。",
    "estimate_duration": "对当前稿执行真实估时，反馈各镜头、总时长及是否超限；目标上限由程序注入。",
    "check_rules": "对当前稿检查事实原文、引用、受控表达和品牌规则；资料和规则由程序注入。",
    "request_input": "缺少必要信息或可用素材且需要用户补充时使用；输出具体问题并结束为 needs_input。",
    "finish": "申请完成或说明无法完成。completed 必须有当前稿的两类通过检查，否则程序拒绝并反馈缺项。",
}


def tool_specs() -> list[dict]:
    return json.loads(json.dumps([
        {"type": "function", "function": {"name": name, "description": ACTION_DESCRIPTIONS[name], "parameters": schema}}
        for name, schema in ACTION_PARAMETERS.items()
    ], ensure_ascii=False))


def _validate(value, schema: dict, path: str = "arguments") -> None:
    kind = schema["type"]
    if kind == "object":
        if not isinstance(value, dict) or set(value) - set(schema["properties"]):
            raise ValueError(f"{path}: 对象类型错误或存在未允许字段")
        missing = set(schema["required"]) - set(value)
        if missing:
            raise ValueError(f"{path}: 缺少字段 {', '.join(sorted(missing))}")
        for key, item in value.items():
            _validate(item, schema["properties"][key], f"{path}.{key}")
    elif kind == "array":
        if not isinstance(value, list) or len(value) < schema.get("minItems", 0):
            raise ValueError(f"{path}: 数组类型或长度错误")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            raise ValueError(f"{path}: 不允许重复项")
        for item in value:
            _validate(item, schema["items"], path + "[]")
    elif kind == "string":
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{path}: 必须是非空字符串")
    elif kind == "integer":
        if type(value) is not int or value < schema.get("minimum", 0):
            raise ValueError(f"{path}: 必须是正整数")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: 不允许的枚举值")


@dataclass(frozen=True)
class ModelAction:
    call_id: str
    name: str
    arguments: dict

    def validate(self) -> None:
        if self.name not in ACTION_PARAMETERS:
            raise ValueError("未知动作名称")
        _validate(self.arguments, ACTION_PARAMETERS[self.name])


@dataclass(frozen=True)
class ModelReply:
    message: dict | None = None
    action: ModelAction | None = None
    error: ToolError | None = None


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def strict_json(text: str):
    def reject_constant(value):
        raise ValueError("non-finite JSON number")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite JSON number")
        return number

    return json.loads(text, object_pairs_hook=_json_object, parse_constant=reject_constant, parse_float=finite_float)


def parse_reply(payload: dict) -> ModelReply:
    """仅保留普通协议字段；不记录或展示 reasoning_content。"""
    try:
        choice = payload["choices"][0]
        if choice.get("finish_reason") in ("length", "content_filter"):
            raise ValueError("响应被截断或未完整生成")
        raw = choice["message"]
        calls = raw.get("tool_calls")
        if not isinstance(calls, list) or not calls:
            raise ValueError("需要通过函数调用选择一个动作")
        normalized = []
        ids = set()
        for call in calls:
            identifier = call["id"]
            function = call["function"]
            if (not isinstance(identifier, str) or not identifier.strip() or identifier in ids
                    or call.get("type") != "function" or not isinstance(function["name"], str)
                    or not isinstance(function["arguments"], str)):
                raise ValueError("工具调用协议字段无效")
            ids.add(identifier)
            normalized.append({"id": identifier, "type": "function", "function": {
                "name": function["name"], "arguments": function["arguments"]}})
        message = {"role": "assistant", "content": None, "tool_calls": normalized}
        if len(normalized) != 1:
            return ModelReply(message=message, error=ToolError("model", "multiple_actions", "每轮只允许一个动作，本轮未执行任何动作"))
        call = normalized[0]
        try:
            arguments = strict_json(call["function"]["arguments"])
            if not isinstance(arguments, dict):
                raise ValueError("参数必须是 JSON 对象")
        except (ValueError, TypeError):
            return ModelReply(message=message, error=ToolError("model", "invalid_arguments_json", "动作参数必须是有效且字段唯一的 JSON 对象"))
        return ModelReply(message, ModelAction(call["id"], call["function"]["name"], arguments))
    except (KeyError, IndexError, TypeError, ValueError):
        return ModelReply(error=ToolError("model", "invalid_response", "响应无效、被截断或缺少合法的函数调用"))


class ModelClient(Protocol):
    mode: RunMode

    def next_turn(self, messages: list[dict], tools: list[dict]) -> ModelReply: ...


@dataclass(frozen=True)
class ModelConfig:
    api_key: str = field(repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"
    timeout_seconds: float = 60
    use_proxy: bool = False

    def __post_init__(self):
        if not self.api_key.strip() or self.api_key == "your_deepseek_api_key_here":
            raise ValueError("请在本地 .env 或进程环境中配置 DEEPSEEK_API_KEY")
        parsed = urlsplit(self.base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("DEEPSEEK_BASE_URL 必须是有效 HTTPS API 地址")
        if not self.model.strip() or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("模型名称或超时配置无效")
        if type(self.use_proxy) is not bool:
            raise ValueError("DEEPSEEK_USE_PROXY 必须为布尔值")

    @classmethod
    def from_env(cls, env_file: Path = ROOT / ".env", environ: dict | None = None):
        from dotenv import dotenv_values
        values = {**dotenv_values(env_file, interpolate=False), **(os.environ if environ is None else environ)}
        proxy = (values.get("DEEPSEEK_USE_PROXY", "false") or "false").strip().lower()
        if proxy not in ("true", "false"):
            raise ValueError("DEEPSEEK_USE_PROXY 必须为 true 或 false")
        return cls(
            values.get("DEEPSEEK_API_KEY", "") or "",
            values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "",
            values.get("DEEPSEEK_MODEL", "deepseek-v4-pro") or "",
            float(values.get("DEEPSEEK_TIMEOUT_SECONDS", "60") or "60"),
            proxy == "true",
        )


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DeepSeekModel:
    mode = RunMode.REAL

    def __init__(self, config: ModelConfig, transport=None):
        self.config = config
        # 不把认证头带到重定向目标；测试可注入模拟 HTTP 响应。
        if transport is None:
            handlers = [_NoRedirect()] if config.use_proxy else [ProxyHandler({}), _NoRedirect()]
            transport = build_opener(*handlers).open
        self.transport = transport

    def next_turn(self, messages, tools):
        body = {"model": self.config.model, "messages": messages, "tools": tools,
                "thinking": {"type": "disabled"}, "max_tokens": 4096, "stream": False}
        request = Request(self.config.base_url.rstrip("/") + "/chat/completions",
                          data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
                          headers={"Authorization": "Bearer " + self.config.api_key, "Content-Type": "application/json"})
        try:
            with self.transport(request, timeout=self.config.timeout_seconds) as response:
                payload = strict_json(response.read().decode("utf-8"))
            return parse_reply(payload)
        except HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            exc.close()
            return ModelReply(error=ToolError("model", f"http_{exc.code}", f"模型服务 HTTP {exc.code}", retryable))
        except (TimeoutError, socket.timeout):
            return ModelReply(error=ToolError("model", "timeout", "模型请求超时", True))
        except (URLError, OSError):
            return ModelReply(error=ToolError("model", "connection_error", "无法连接模型服务", True))
        except (ValueError, UnicodeError, TypeError):
            return ModelReply(error=ToolError("model", "invalid_response", "模型服务返回了无法解析的响应"))


def mock_reply(name: str, arguments: dict, call_id: str) -> ModelReply:
    return parse_reply({"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [{
        "id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}
    }]}}]})


class MockModel:
    """按实际状态选择预设动作，只证明离线流程，不证明真实模型决策。"""

    mode = RunMode.MOCK

    def __init__(self, scenario: str = "normal"):
        if scenario not in ("normal", "over-duration", "unsupported-claim", "early-finish"):
            raise ValueError("unknown mock scenario")
        self.scenario = scenario

    def next_turn(self, messages, tools):
        view = strict_json(messages[1]["content"].split("\n", 1)[1])
        step = view["step_count"]

        def reply(name, **arguments):
            return mock_reply(name, arguments, f"mock-{step}")

        if self.scenario == "early-finish" and step == 1:
            return reply("finish", status="completed", reason="测试程序是否拒绝未经检查的完成申请")
        observation = view.get("last_observation") or {}
        if not view["retrieved_materials"]:
            if observation.get("error"):
                if view["tool_call_count"] >= 2:
                    return reply("finish", status="incomplete", reason="检索持续失败，无法取得事实依据")
            elif observation.get("materials") == []:
                return reply("request_input", missing_fields=["materials"], questions=["请补充可支持主题的产品事实。"], reason="没有检索到可用事实")
            query = (view.get("data_scope") or {}).get("product_name", "字幕")
            return reply("search_materials", query=query, reason="先查找当前授权范围内有依据的产品事实")
        script = view["current_script"]
        duration = view["duration_result"]
        rules = view["rule_check_result"]
        if script is None or duration and not duration["passed"] or rules and not rules["passed"]:
            if script and view["task_input"]["target_duration_seconds"] < 2:
                return reply("finish", status="incomplete", reason="目标短于单镜最短展示时长")
            if script and script["version"] >= 3:
                return reply("finish", status="incomplete", reason="多次修订后仍无法通过检查")
            material = view["retrieved_materials"][0]
            narration = material["fact"].rstrip("。") + "。"
            if script is None and self.scenario == "over-duration":
                narration *= 12
            if script is None and self.scenario == "unsupported-claim":
                narration = "效率提升80%。"
            return reply("save_script", title=material["fact"] if view.get("data_scope") else "给视频加字幕", shots=[{
                "id": "S01", "visual": "展示视频画面" if view.get("data_scope") else "字幕示意画面", "narration": narration, "source_ids": [material["id"]]
            }], reason="根据可用事实生成草稿，或依据实际检查反馈修订")
        if duration is None:
            return reply("estimate_duration", script_version=script["version"], reason="检查当前稿是否满足用户时长上限")
        if rules is None:
            return reply("check_rules", script_version=script["version"], reason="核对当前稿的事实、引用和品牌规则")
        return reply("finish", status="completed", reason="当前稿已通过估时和规则检查")
