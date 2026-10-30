"""运行实际 CLI 并核对关键 Trace 分支；不生成或改写模型动作。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    "normal": ("examples/normal/input.json", []),
    "tool-failure": ("examples/normal/input.json", ["--simulate-search-failure"]),
    "no-materials": ("examples/no-materials/input.json", ["--materials", "examples/no-materials/materials.json"]),
    "unrelated-materials": ("examples/unrelated-materials/input.json", ["--materials", "examples/unrelated-materials/materials.json"]),
    "over-duration": ("examples/over-duration/input.json", []),
}


def assess(name, result, events):
    """这里只判定记录中的分支覆盖；不评判开放域事实或文案质量。"""
    actions = [e for e in events if e.get("event") == "action"]
    observed = {
        "empty_search": any(e.get("action") == "search_materials" and e.get("observation", {}).get("materials") == []
                            and not e["observation"].get("error") for e in actions),
        "duration_failure": any(e.get("action") == "estimate_duration" and e.get("observation", {}).get("passed") is False for e in actions),
        "multiple_actions": sum(e.get("event") == "model_error" and e.get("error", {}).get("code") == "multiple_actions" for e in events),
    }
    if result["status"] == "failed":
        errors = result.get("errors", [])
        blocked = any(e.get("tool") == "model" and (e.get("code") in {"connection_error", "timeout"}
                      or e.get("code", "").startswith("http_")) for e in errors)
        return {"verdict": "blocked" if blocked else "failed", "reason": result.get("reason"), **observed}
    if name in {"no-materials", "unrelated-materials"}:
        valid = result["status"] == "needs_input" and bool(result.get("questions")) and result.get("script") is None
        verdict = "passed" if valid else "failed"
        if valid and name == "unrelated-materials" and not observed["empty_search"]:
            verdict = "not_covered"
        return {"verdict": verdict, "reason": "核对请求补资料；无关素材还须实际出现空检索结果。", **observed}

    completed = result["status"] == "completed"
    if completed:
        script = result.get("script") or {}
        for key in ("duration_result", "rule_check_result"):
            report = result.get(key) or {}
            if not (report.get("passed") is True and report.get("script_version") == script.get("version")
                    and report.get("script_fingerprint") == script.get("fingerprint")):
                return {"verdict": "failed", "reason": "最终检查未通过或版本/指纹不匹配。", **observed}
        duration = result["duration_result"]
        if not (duration["target_duration_seconds"] == result["task_input"]["target_duration_seconds"]
                and duration["total_duration_seconds"] <= duration["target_duration_seconds"]):
            return {"verdict": "failed", "reason": "最终时长超过用户上限或检查放宽了上限。", **observed}
        saves = [e for e in actions if e["action"] == "save_script" and e["observation"].get("saved")
                 and e["observation"].get("script_version") == script["version"]]
        finishes = [e for e in actions if e["action"] == "finish" and e["observation"].get("status") == "completed"]
        if not saves or not finishes:
            return {"verdict": "failed", "reason": "缺少最终稿保存或实际完成动作。", **observed}
        for action, key in (("estimate_duration", "duration_result"), ("check_rules", "rule_check_result")):
            if not any(e["action"] == action and saves[-1]["sequence"] < e["sequence"] < finishes[-1]["sequence"]
                       and e["observation"] == result[key] for e in actions):
                return {"verdict": "failed", "reason": "缺少最终稿保存后、完成前的实际匹配检查。", **observed}

    if name == "over-duration":
        failed_checks = [e for e in actions if e["action"] == "estimate_duration" and e["observation"].get("passed") is False]
        if not failed_checks:
            return {"verdict": "not_covered", "reason": "未发生真实估时不通过，不能证明超时长后的处理。", **observed}
        first = failed_checks[0]
        later = [e for e in actions if e["sequence"] > first["sequence"]]
        revised = any(e["action"] == "save_script" and e["observation"].get("saved")
                      and e["observation"]["script_version"] > first["observation"]["script_version"] for e in later)
        accepted_finish = any(e["action"] == "finish" and e["observation"].get("status") == result["status"] for e in later)
        if completed and revised and accepted_finish:
            version = result["script"]["version"]
            checked = all(any(e["action"] == action and e["observation"].get("passed") is True
                              and e["observation"].get("script_version") == version for e in later)
                          for action in ("estimate_duration", "check_rules"))
            if checked:
                return {"verdict": "passed", "reason": "实际超时→模型保存修订稿→两项重检→完成。", **observed}
        if result["status"] == "incomplete" and accepted_finish and result.get("reason"):
            return {"verdict": "passed", "reason": "超时后模型明确申请未完成；是否充分尝试修订仍需人工查看 reason/Trace。", **observed}
        return {"verdict": "failed", "reason": "出现超时，但未完成修订重检或明确申请无法满足。", **observed}

    if name == "tool-failure":
        failures = [e for e in actions if e["action"] == "search_materials"
                    and (e["observation"].get("error") or {}).get("code") == "simulated_failure"]
        recovered = bool(failures) and any(e["sequence"] > failures[0]["sequence"] and e["action"] == "search_materials"
                                         and e["observation"].get("materials") for e in actions)
        completed = completed and recovered
    return {"verdict": "passed" if completed else "failed", "reason": "核对最终完成条件与所需恢复分支。", **observed}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("real", "mock"), default="real")
    parser.add_argument("--case", choices=tuple(CASES), action="append", dest="cases")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    output = args.output_dir or ROOT / "outputs" / ("prompt-validation-" + uuid4().hex)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    blocked = False
    report = {"mode": args.mode, "created_at": datetime.now(timezone.utc).isoformat(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Trace branch checks only; Mock never proves real model behavior. Human review of claims/reasons is required.", "cases": rows}
    for name in dict.fromkeys(args.cases or CASES):
        if blocked:
            rows.append({"case": name, "verdict": "not_run", "reason": "前一案例模型服务不可用，停止相同连接尝试。"})
        else:
            input_path, extra = CASES[name]
            command = [sys.executable, "-m", "src.main", "--mode", args.mode, "--input", input_path,
                       *extra, "--output-dir", str(output / name)]
            if args.mode == "mock" and name == "over-duration":
                command += ["--mock-scenario", "over-duration"]
            process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            directory = output / name
            if (directory / "result.json").is_file() and (directory / "run.json").is_file():
                result = json.loads((directory / "result.json").read_text())
                events = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
                metadata = json.loads((directory / "run.json").read_text())
                row = {"case": name, "exit_code": process.returncode, "status": result["status"],
                       "system_prompt_sha256": metadata.get("system_prompt_sha256"),
                       "steps": max((e["step"] for e in events), default=0), **assess(name, result, events)}
                blocked = row["verdict"] == "blocked"
            else:
                row = {"case": name, "exit_code": process.returncode, "verdict": "failed", "reason": "CLI 未产生完整记录。"}
            rows.append(row)
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(f"{name}: {rows[-1]['verdict']}", flush=True)
    print(f"报告目录：{output}")
    return 0 if all(r["verdict"] == "passed" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
