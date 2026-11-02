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

PASSWORD_WORDS = r"(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)"
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})")),
    ("anthropic_api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai_api_key", re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{20,}")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}")),
    ("gitlab_token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}")),
    ("sendgrid_key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")),
    ("azure_ad_client_secret", re.compile(r"(?<![A-Za-z0-9_~.])[A-Za-z0-9_~.]{3}\dQ~[A-Za-z0-9_~.-]{30,}")),
    ("azure_storage_account_key", re.compile(r"(?i)\bAccountKey=[A-Za-z0-9+/]{40,}={0,2}")),
    ("azure_sas_signature", re.compile(r"(?i)[?&;]sig=[A-Za-z0-9%+/=]{20,}")),
    ("private_key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    # Group 1 is the opening quote, group 2 the value. The prefix lets names such as client_secret and OPENAI_API_KEY match.
    ("password_assignment", re.compile(r"(?i)[a-z0-9_]*" + PASSWORD_WORDS + r"\b\s*[:=]\s*(['\"]?)([^\s'\"]{6,})")),
]
PLACEHOLDER_HINTS = ("<", "your", "xxx", "***", "example", "changeme", "placeholder", "redacted")
MAX_LOG_BYTES = 1_000_000


def is_placeholder(value: str) -> bool:
    return value.startswith("$") or any(h in value.lower() for h in PLACEHOLDER_HINTS)


def is_secret_literal(quote: str, value: str) -> bool:
    """A quoted string, or a bare token that mixes letters and digits. Calls, attribute paths (var.db_password),
    indexes and variables are code that reads a secret, not a secret."""
    if is_placeholder(value):
        return False
    if quote:
        return True
    if re.search(r"[(){}\[\]]", value) or re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", value):
        return False
    return bool(re.search(r"[A-Za-z]", value) and re.search(r"\d", value))


def find_secret_kinds(text: str) -> list[str]:
    kinds = []
    for kind, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            if kind == "password_assignment":
                if not is_secret_literal(m.group(1), m.group(2)):
                    continue
            elif kind != "private_key" and "EXAMPLE" in m.group(0):
                continue  # the documented example credentials, such as the AWS example key
            kinds.append(kind)
            break
    return kinds


def mask_secrets(text: str) -> str:
    """Logs are a classic leak path, so secrets are masked before anything is written."""
    for kind, pattern in SECRET_PATTERNS:
        text = pattern.sub(f"[MASKED:{kind}]", text)
    return text


def read_payload() -> dict:
    return json.load(sys.stdin)


def log_decision(hook: str, payload: dict, decision: str, rule: str = "", detail: str = "") -> None:
    """Append one JSON line per deny, ask or block. Passes are logged only when GUARDRAIL_LOG_PASS is set, because the
    command text of every call would otherwise pile up. The file is capped at about 1 MB with one rotated copy.
    Logging must never break the guard, so errors are ignored."""
    if decision == "pass" and not os.environ.get("GUARDRAIL_LOG_PASS"):
        return
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
        if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
            os.replace(path, path.with_name(path.name + ".1"))
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
