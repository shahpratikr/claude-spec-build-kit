#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook: stop prompts that contain credentials before any model sees them.

Limits worth knowing (from the hooks docs): the blocked prompt can still land in local
transcript and history files, so this protects the model provider and your context window,
not your disk. suppressOriginalPrompt keeps it out of the on-screen block message.

Try it without Claude:   python3 guard_prompt.py --dry-run "my key is AKIAIOSFODNN7EXAMPLE"
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _guardrail_common import find_secret_kinds, log_decision, read_payload


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--dry-run":
        kinds = find_secret_kinds(" ".join(sys.argv[2:]))
        print(f"block secret-in-prompt: {', '.join(kinds)}" if kinds else "pass  (no secret found)")
        return 0
    try:
        payload = read_payload()
        kinds = find_secret_kinds(payload.get("prompt", ""))
        if not kinds:
            log_decision("guard_prompt", payload, "pass")
            return 0
        log_decision("guard_prompt", payload, "block", "secret-in-prompt", ", ".join(kinds))
        print(json.dumps({
            "decision": "block",
            "reason": f"[guardrail:secret-in-prompt] Your prompt contains a credential ({', '.join(kinds)}). "
                      "Remove it, rotate it, and send the prompt again.",
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "suppressOriginalPrompt": True},
        }))
        return 0
    except Exception as exc:
        print(f"guard_prompt.py failed ({exc!r}); blocking the prompt to stay safe.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
