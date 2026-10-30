"""每步实际动作与观察的 JSONL 记录，不保存模型内部思维或认证信息。"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re


class TraceRecorder:
    def __init__(self, run_id: str, path: Path | None = None, secrets: tuple[str, ...] = ()):
        self.run_id = run_id
        self.path = path
        self.secrets = tuple(secret for secret in secrets if secret)
        self.events = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.open("x", encoding="utf-8").close()

    def sanitize(self, value):
        if isinstance(value, dict):
            return {key: self.sanitize(item) for key, item in value.items()
                    if key.lower() not in {"api_key", "authorization", "password", "reasoning_content"}}
        if isinstance(value, (list, tuple)):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            return re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[REDACTED]", value)
        return value

    def emit(self, step: int, event: str, **details) -> dict:
        record = self.sanitize({"run_id": self.run_id, "sequence": len(self.events) + 1,
                               "timestamp": datetime.now(timezone.utc).isoformat(),
                               "step": step, "event": event, **details})
        self.events.append(record)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        return record
