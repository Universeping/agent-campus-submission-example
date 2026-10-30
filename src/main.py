"""CLI：读取 JSON，运行单 Agent，保存结果、检查、历史及实际 Trace。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

from .agent import AgentLimits, AgentRunner, SYSTEM_PROMPT
from .model import DeepSeekModel, MockModel, ModelConfig, ROOT, strict_json
from .schemas import RunMode, TaskResult, ToolError
from .tools import load_brand_rules, load_materials
from .trace import TraceRecorder
from .profiles import load_profile, list_profiles


def render_script(result: TaskResult, source_metadata=None) -> str:
    lines = ["# 短视频脚本", "", f"状态：{result.status.value}；模式：{result.mode.value}", ""]
    if result.script:
        script = result.script
        lines += [f"## {script.title}", "", f"版本：{script.version}；指纹：{script.fingerprint}", "",
                  "| 分镜 | 画面 | 旁白 | 预计秒数 | 来源 |", "| --- | --- | --- | --- | --- |"]
        durations = {item.shot_id: item.duration_seconds for item in result.duration_result.shot_durations} if result.duration_result else {}

        def cell(value):
            return str(value).replace("|", "\\|").replace("\n", "<br>")

        for shot in script.shots:
            lines.append("| " + " | ".join(cell(value) for value in (
                shot.id, shot.visual, shot.narration, durations.get(shot.id, "未检查"), ", ".join(shot.source_ids) or "创意衔接"
            )) + " |")
        if result.duration_result:
            lines += ["", f"预计总时长：{result.duration_result.total_duration_seconds:g} 秒。"]
    if result.reason:
        lines += ["", "说明：" + result.reason]
    if result.questions:
        lines += ["", "待补充：", "", *("- " + question for question in result.questions)]
    if result.risks:
        lines += ["", "风险与限制：", "", *("- " + risk for risk in result.risks)]
    if result.script and source_metadata:
        lines += ["", "素材来源：", ""]
        for key in result.script.source_ids:
            if key in source_metadata:
                info = source_metadata[key]
                lines.append(f"- {key}：{info['source_title']}（核验：{info['verified_on']}；适用端：{', '.join(info['surfaces'])}） {info['source_url']}")
    return "\n".join(lines) + "\n"


def write_outputs(directory: Path, result: TaskResult, trace: TraceRecorder, state=None, metadata=None):
    def save(name, value):
        (directory / name).write_text(json.dumps(trace.sanitize(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    save("result.json", result.to_dict())
    save("checks.json", {
        "duration_result": result.duration_result.to_dict() if result.duration_result else None,
        "rule_check_result": result.rule_check_result.to_dict() if result.rule_check_result else None,
    })
    provenance = (metadata or {}).get("material_provenance", {})
    (directory / "script.md").write_text(trace.sanitize(render_script(result, provenance)), encoding="utf-8")
    if "data_profile" in (metadata or {}):
        save("sources.json", {key: provenance[key] for key in (result.script.source_ids if result.script else ()) if key in provenance})
    state = state or {}
    save("history.json", {
        "scripts": {str(key): value.to_dict() for key, value in state.get("scripts", {}).items()},
        "duration_results": {str(key): value.to_dict() for key, value in state.get("duration_results", {}).items()},
        "rule_results": {str(key): value.to_dict() for key, value in state.get("rule_results", {}).items()},
        "error_history": state.get("error_history", []),
        "step_count": state.get("step_count", 0), "tool_call_count": state.get("tool_call_count", 0),
    })
    save("run.json", metadata or {})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--input", type=Path, help="需求 JSON 文件；- 表示标准输入")
    inputs.add_argument("--interactive", action="store_true", help="粘贴多行 JSON，以单独一行 END 提交")
    parser.add_argument("--mode", choices=["real", "mock"], default="mock")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--materials", type=Path)
    parser.add_argument("--brand-rules", type=Path)
    parser.add_argument("--profile", help="审阅后的产品/客户端配置；省略 --input 时使用其输入样例")
    parser.add_argument("--list-profiles", action="store_true", help="列出可用配置，不调用模型")
    parser.add_argument("--output-dir", type=Path, help="新建输出目录；拒绝覆盖已有目录")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--max-tool-calls", type=int, default=8)
    parser.add_argument("--max-transport-retries", type=int, default=1)
    parser.add_argument("--mock-scenario", choices=["normal", "over-duration", "unsupported-claim", "early-finish"], default="normal")
    parser.add_argument("--simulate-search-failure", action="store_true", help="测试用：显式注入一次检索失败")
    args = parser.parse_args(argv)
    if args.list_profiles:
        try:
            print(json.dumps(list_profiles(), ensure_ascii=False, indent=2))
            return 0
        except (OSError, ValueError, TypeError, KeyError):
            print("资料配置无效，请检查数据包与审阅文件。", file=sys.stderr)
            return 2
    if not args.input and not args.interactive and not args.profile:
        parser.error("需要 --input、--interactive 或 --profile")
    if args.profile and (args.materials is not None or args.brand_rules is not None):
        parser.error("--profile 不能与 --materials/--brand-rules 混用，以免绕过配置范围和必需规则")
    run_id = uuid4().hex
    directory = args.output_dir or ROOT / "outputs" / run_id
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except OSError:
        print("无法创建输出目录；目录可能已存在，未覆盖任何文件。", file=sys.stderr)
        return 2
    trace = TraceRecorder(run_id, directory / "trace.jsonl")
    state = None
    metadata = {"run_id": run_id, "mode": args.mode, "command": ["python", "-m", "src.main", *(argv if argv is not None else sys.argv[1:])],
                "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
                "mock_scenario": args.mock_scenario if args.mode == "mock" else None,
                "simulate_search_failure": args.simulate_search_failure, "sha256": {}}
    try:
        if args.mode == "real":
            config = ModelConfig.from_env(args.env_file)
            trace.secrets = (config.api_key,)
            model = DeepSeekModel(config)
            metadata["model"] = config.model
            metadata["timeout_seconds"] = config.timeout_seconds
            metadata["use_proxy"] = config.use_proxy
        else:
            model = MockModel(args.mock_scenario)
            metadata["model"] = "offline-mock"
        profile = load_profile(args.profile) if args.profile else None
        if profile:
            materials, rules = profile.materials, profile.brand_rules
            evidence_files = profile.evidence_files
            metadata["data_profile"] = {**profile.scope, "material_ids": [m.id for m in materials],
                                        "excluded_material_ids": list(profile.excluded_material_ids)}
            metadata["material_provenance"] = profile.material_metadata
        else:
            material_path = args.materials or ROOT / "data/materials.json"
            rule_path = args.brand_rules or ROOT / "data/brand_rules.json"
            materials, rules = load_materials(material_path), load_brand_rules(rule_path)
            evidence_files = (material_path, rule_path)
        if args.interactive:
            print("粘贴任务 JSON，以单独一行 END 提交：", file=sys.stderr)
            lines = []
            for line in sys.stdin:
                if line.strip() == "END":
                    break
                lines.append(line)
            text = "".join(lines)
        elif args.input is None:
            text = json.dumps(profile.default_input, ensure_ascii=False)
        elif str(args.input) == "-":
            text = sys.stdin.read()
        else:
            text = args.input.read_text(encoding="utf-8")
        raw_input = strict_json(text)
        limits = AgentLimits(args.max_steps, args.max_tool_calls, args.max_transport_retries)
        runner = AgentRunner(model, materials, rules, limits=limits, simulate_search_failure=args.simulate_search_failure,
                             data_scope=profile.scope if profile else None,
                             material_metadata=profile.material_metadata if profile else None)
        for path in [*evidence_files, *(ROOT / "src").glob("*.py")]:
            metadata["sha256"][str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        metadata["input_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        metadata["limits"] = {"max_steps": limits.max_steps, "max_tool_calls": limits.max_tool_calls,
                              "max_transport_retries": limits.max_transport_retries}
        run = runner.run(raw_input, trace=trace)
        result, state = run.result, run.state
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        if isinstance(exc, ImportError):
            code, message = "missing_dependency", "缺少依赖，请使用项目虚拟环境安装 requirements.txt。"
        elif args.mode == "real" and isinstance(exc, ValueError) and "DEEPSEEK" in str(exc):
            code, message = "model_configuration", str(exc)
        else:
            code, message = "invalid_input_or_configuration", "输入文件、资料或配置无效，请检查 JSON 和参数。"
        error = ToolError("runtime", code, message)
        result = TaskResult(run_id, RunMode(args.mode), "failed", reason=message, errors=[error])
        trace.emit(0, "terminal", status="failed", error=error.to_dict())
    write_outputs(directory, result, trace, state, metadata)
    print(trace.sanitize(render_script(result, metadata.get("material_provenance"))))
    print(f"结果目录：{directory}")
    return 0 if result.status.value == "completed" else 1 if result.status.value in ("needs_input", "incomplete") else 2


if __name__ == "__main__":
    raise SystemExit(main())
