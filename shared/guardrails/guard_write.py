#!/usr/bin/env python3
"""Claude Code PreToolUse hook for file-writing tools (Write, Edit, NotebookEdit).

Always denies:
  - writing a credential into any file
  - writing to protected paths: .env files, private keys, .git internals, and Claude Code's own
    settings and hooks (an agent that can edit its guardrails can switch them off)
Optional arguments narrow it further:
  --only GLOB      allow writes only to paths matching GLOB (repeatable), e.g. --only NOTES.md
  --deny-all       allow no writes at all (read-only skills)

Try it without Claude:   python3 guard_write.py --dry-run NOTES.md --only NOTES.md
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _guardrail_common import emit_pretooluse, find_secret_kinds, log_decision, read_payload

PROTECTED = [".env", ".env.*", "*.pem", "*.key", "id_rsa*", "id_ed25519*", ".git/*", "*/.git/*",
             ".claude/settings*.json", "*/.claude/settings*.json", ".claude/hooks/*", "*/.claude/hooks/*"]
TEMPLATE_SUFFIXES = (".example", ".sample", ".template")


def _protected(path: str, rel: str) -> bool:
    """Lowercased on purpose: macOS file systems are case-insensitive, so .ENV is the same file as .env."""
    candidates = (rel.lower(), os.path.basename(path).lower(), path.lower())
    return any(fnmatch.fnmatchcase(c, g.lower()) for c in candidates for g in PROTECTED)


def _allowed(path: str, rel: str, globs: list[str]) -> bool:
    """--only globs match paths relative to the project; anything outside the project never matches."""
    return not os.path.isabs(rel) and not rel.startswith("..") and any(fnmatch.fnmatchcase(rel, g) for g in globs)


def _written_text(tool_input: dict) -> str:
    """Collect every string the tool would write: content, new_string, edits[].new_string, new_source."""
    parts: list[str] = []

    def walk(value):
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for k, v in value.items():
                if k not in ("file_path", "old_string", "notebook_path"):
                    walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(tool_input)
    return "\n".join(parts)


def decide(path: str, cwd: str, written: str, only: list[str], deny_all: bool) -> tuple[str, str] | None:
    rel = os.path.relpath(path, cwd) if cwd and (path + "/").startswith(cwd.rstrip("/") + "/") else path
    if deny_all:
        return "read-only-skill", "This skill is read-only: no file writes are allowed."
    if _protected(path, rel) and not path.lower().endswith(TEMPLATE_SUFFIXES):
        return "protected-path", f"{rel} is a protected file (secrets, git internals or guardrail config)."
    if only and not _allowed(path, rel, only):
        return "outside-allowlist", f"Writes are limited to {', '.join(only)} inside the project; {rel} is not allowed."
    kinds = find_secret_kinds(written)
    if kinds:
        return "secret-in-content", f"The content contains a credential ({', '.join(kinds)}). Use a placeholder or an environment variable."
    return None


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--deny-all", action="store_true")
    parser.add_argument("--dry-run", metavar="PATH")
    parser.add_argument("--content", default="")
    args = parser.parse_args()

    if args.dry_run:
        path = os.path.abspath(args.dry_run)
        result = decide(path, os.getcwd(), args.content, args.only, args.deny_all)
        print(f"deny  {result[0]}: {result[1]}" if result else "pass  (no rule matched)")
        return 0
    try:
        payload = read_payload()
        tool_input = payload.get("tool_input") or {}
        path = (tool_input.get("file_path") or tool_input.get("notebook_path") or "").replace("\\", "/")
        result = decide(path, (payload.get("cwd") or "").replace("\\", "/"), _written_text(tool_input), args.only, args.deny_all)
        if result is None:
            log_decision("guard_write", payload, "pass", detail=path)
            return 0
        rule_id, message = result
        log_decision("guard_write", payload, "deny", rule_id, path)
        emit_pretooluse("deny", f"[guardrail:{rule_id}] {message}")
        return 0
    except Exception as exc:
        print(f"guard_write.py failed ({exc!r}); blocking the write to stay safe.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
