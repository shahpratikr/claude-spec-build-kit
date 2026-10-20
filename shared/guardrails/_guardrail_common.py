"""Helpers shared by the guardrail hook scripts in this folder.

Copy the whole folder when you install the hooks (for example to ~/.claude/hooks/guardrails/).
Stdlib only, on purpose: a hook must start fast and never depend on a virtualenv.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})")),
    ("anthropic_api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private_key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    (
        "password_assignment",
        re.compile(
            r"(?i)\b(?:[a-z0-9_]*password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b"
            r"\s*[:=]\s*['\"]?([^\s'\"]{6,})"
        ),
    ),
]
PLACEHOLDER_HINTS = ("<", "your", "xxx", "***", "example", "changeme", "placeholder", "redacted")


def is_placeholder(value: str) -> bool:
    return value.startswith("$") or any(h in value.lower() for h in PLACEHOLDER_HINTS)


def find_secret_kinds(text: str) -> list[str]:
    kinds = []
    for kind, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            if kind == "password_assignment" and is_placeholder(m.group(1)):
                continue
            kinds.append(kind)
            break
    return kinds


def mask_secrets(text: str) -> str:
    """Logs are a classic leak path, so secrets are masked before anything is written."""
    for kind, pattern in SECRET_PATTERNS:
        text = pattern.sub(f"[SECRET:{kind}]", text)
    return text


def read_payload() -> dict:
    return json.load(sys.stdin)


def log_decision(hook: str, payload: dict, decision: str, rule: str = "", detail: str = "") -> None:
    """Append one JSON line per decision. Logging must never break the guard, so errors are ignored."""
    path = Path(os.environ.get("GUARDRAIL_LOG") or Path(__file__).resolve().parent / "logs" / "guardrail-hooks.jsonl")
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "hook": hook,
        "session": payload.get("session_id", ""),
        "tool": payload.get("tool_name", payload.get("hook_event_name", "")),
        "decision": decision,
        "rule": rule,
        "detail": mask_secrets(detail)[:300],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def emit_pretooluse(decision: str, reason: str) -> None:
    """Print a PreToolUse decision: "deny" blocks the call, "ask" forces a human confirmation prompt."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
