#!/usr/bin/env python3
"""Claude Code PreToolUse hook: deny or ask before risky Bash commands.

How it plugs in: Claude Code runs this script before every Bash tool call and
sends the pending call as JSON on stdin. The script prints a decision:
  - nothing      -> no opinion, the normal permission flow continues
  - "deny"       -> the call is blocked and Claude reads the reason
  - "ask"        -> a human must confirm, even in auto mode
If the script itself crashes it exits 2, which blocks the call (fail closed).
Register it with "onFailure": "block" too, so a missing script also blocks.

Try a command without Claude:   python3 guard_bash.py --dry-run "git push -f origin main"
"""
from __future__ import annotations

import os
import re
import shlex
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _guardrail_common import emit_pretooluse, log_decision, read_payload

DENY, ASK = "deny", "ask"

GIT = r"\bgit(?:\s+-c\s+\S+|\s+--[\w-]+(?:=\S+)?)*\s+"
RULES: list[tuple[str, str, str, str]] = [
    ("git-reset-hard", GIT + r"reset\b.*--hard", DENY,
     "git reset --hard throws away uncommitted work. Ask the user to run it themselves if it is really needed."),
    ("git-clean-force", GIT + r"clean\b.*\s-[a-z]*f", DENY,
     "git clean -f permanently deletes untracked files."),
    ("git-checkout-discard", GIT + r"checkout\b(?:.*\s)?(?:--|\.)(?:\s|$)", DENY,
     "git checkout -- / git checkout . discards uncommitted changes."),
    ("git-restore-worktree", GIT + r"restore\b(?!.*--staged)", DENY,
     "git restore without --staged discards uncommitted changes."),
    ("git-stash-drop", GIT + r"stash\s+(?:drop|clear)\b", DENY,
     "Dropping stashes loses work permanently."),
    ("git-add-all", GIT + r"add\s+(?:.*\s)?(?:-a|--all|\.)(?:\s|$)", DENY,
     "Stage files by explicit path, never with git add -A, --all or '.'."),
    ("pipe-to-interpreter", r"\b(?:curl|wget)\b[^|;&]*\|\s*(?:sudo\s+)?(?:(?:ba|z|da|k)?sh|python3?|perl|ruby|node)\b", DENY,
     "Piping a download straight into an interpreter runs unreviewed remote code."),
    ("git-commit-needs-human", GIT + r"commit\b", ASK,
     "Commits need a human click."),
    ("git-push-force", GIT + r"push\b.*(?:\s--force(?:-with-lease)?\b|\s-[a-z]*f\b|\s\+\S)", DENY,
     "Force-pushing rewrites shared history. Push normally, or ask the user to do it."),
    ("read-secret-file",
     r"(?:^|[\s/=(])\.env(?:\.(?!example\b|sample\b|template\b)[\w.-]+)?(?=$|[\s)])"
     r"|\bid_(?:rsa|ed25519|ecdsa)\b(?!\.pub)|\.aws/credentials\b",
     DENY, "That command touches a secrets file (.env, an SSH private key or cloud credentials)."),
    ("add-dependency",
     r"\bnpm\s+(?:install|i|add)\b(?:\s+-\S+)*\s+[^-\s&|;]"
     r"|\bpnpm\s+(?:install|i)\b(?:\s+-\S+)*\s+[^-\s&|;]"
     r"|\b(?:yarn|pnpm|poetry|cargo|uv|bundle)\s+add\b"
     r"|\bpip3?\s+install\b(?!\s+(?:-r|--requirement)\s)(?!\s+-e\s+\.(?:\s|$))(?!\s+\.(?:\s|$))(?!\s+--upgrade\s+pip\b)\s+\S"
     r"|\bgo\s+get\b|\bgo\s+install\s+\S+@"
     r"|\bgem\s+install\b|\bcomposer\s+require\b"
     r"|\b(?:brew|apt|apt-get|yum|dnf|apk)\s+(?:install|add)\b",
     ASK, "Adding a dependency or package needs a human click."),
]

CATASTROPHIC_TARGETS = {"/", "/*", "~", "~/", "~/*", "$home", "${home}", ".", "./", "./*", "..", "../", "*"}
WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "xargs", "export"}
SHELLS = {"sh", "bash", "zsh", "dash"}
ASSIGNMENT = re.compile(r"^([A-Za-z_]\w*)=(.*)$", re.S)
VARIABLE = re.compile(r"\$(?:\{(\w+)\}|(\w+))")


def normalize(command: str) -> str:
    """Strip quotes and backslashes so g"i"t and git 'push' look like git push, then collapse spaces."""
    text = command.replace("\\\n", " ")
    text = re.sub(r"[\"'`\\]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def expand(word: str, env: dict[str, str | None]) -> str | None:
    """Expand ~ and $VAR as the shell would, or return None when the value can't be known from the command text."""
    if "$(" in word or "`" in word:
        return None
    if word == "~" or word.startswith("~/"):
        word = os.path.expanduser("~") + word[1:]
    unknown = False

    def value(m: re.Match) -> str:
        nonlocal unknown
        name = m.group(1) or m.group(2)
        found = env.get(name) if name in env else (os.path.expanduser("~") if name == "HOME" else None)
        unknown = unknown or found is None
        return found or ""

    word = VARIABLE.sub(value, word)
    return None if unknown or "$" in word else word


def resolve(target: str, env: dict[str, str | None], cwd: str | None) -> str | None:
    word = expand(target, env)
    if word is None or ("{" in word and ".." in word):
        return None
    if not os.path.isabs(word):
        if cwd is None:
            return None
        word = os.path.join(cwd, word)
    return os.path.realpath(word)


def inside_temp(path: str) -> bool:
    """Two levels deep in a temp root (a scratchpad, a mktemp folder): the root and its direct children stay protected."""
    for root in {os.path.realpath(tempfile.gettempdir()), os.path.realpath("/tmp")}:
        rel = os.path.relpath(path, root)
        if rel != ".." and not rel.startswith(".." + os.sep) and len(rel.split(os.sep)) >= 2:
            return True
    return False


def is_catastrophic(path: str) -> bool:
    home = os.path.realpath(os.path.expanduser("~"))
    return path == "/" or home == path or home.startswith(path.rstrip("/") + "/")


def check_rm(command: str, cwd: str | None = None) -> tuple[str, str, str] | None:
    """Recursive rm: deny catastrophic targets, allow targets inside a temp folder, ask for everything else.

    Variables assigned and folders entered with cd earlier in the same command are followed, so
    `S=/tmp/x/scratchpad; rm -rf $S/out` and `cd /tmp/x/scratchpad && rm -rf out` resolve to real paths.
    """
    env: dict[str, str | None] = {}
    hits = []
    for segment in re.split(r"&&|\|\||;|\||\n", command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        from_stdin = False
        while tokens and (ASSIGNMENT.match(tokens[0]) or os.path.basename(tokens[0]).lower() in WRAPPERS):
            assignment = ASSIGNMENT.match(tokens[0])
            if assignment:
                env[assignment.group(1)] = expand(assignment.group(2), env)
            from_stdin = from_stdin or os.path.basename(tokens[0]) == "xargs"
            tokens = tokens[1:]
        if from_stdin:
            names = [os.path.basename(t).lower() for t in tokens]
            tokens = tokens[names.index("rm"):] if "rm" in names else []
        if not tokens:
            continue
        head = os.path.basename(tokens[0]).lower()
        if head == "cd":
            target = expand(tokens[1], env) if len(tokens) > 1 else os.path.expanduser("~")
            if target is None or target == "-" or (cwd is None and not os.path.isabs(target)):
                cwd = None
            else:
                cwd = os.path.normpath(os.path.join(cwd or "/", target))
            continue
        if head in SHELLS and "-c" in tokens:
            inner = tokens[tokens.index("-c") + 1:]
            nested = check_rm(" ".join(inner), cwd) if inner else None
            if nested:
                hits.append(nested)
            continue
        if head != "rm":
            continue
        args = tokens[1:]
        split = args.index("--") if "--" in args else len(args)
        flags = [t for t in args[:split] if t.startswith("-")]
        targets = [t for t in args[:split] if not t.startswith("-")] + args[split + 1:]
        if not any(f == "--recursive" or (not f.startswith("--") and "r" in f.lower()) for f in flags):
            continue
        if (not targets and not from_stdin) or any(t.lower() in CATASTROPHIC_TARGETS for t in targets):
            hits.append((DENY, "rm-recursive-catastrophic", f"Refusing recursive delete of {' '.join(targets) or '(nothing)'}."))
            continue
        paths = [resolve(t, env, cwd) for t in targets]
        if any(p is not None and is_catastrophic(p) for p in paths):
            hits.append((DENY, "rm-recursive-catastrophic", f"Refusing recursive delete of {' '.join(targets)}: it reaches / or your home folder."))
        elif from_stdin or any(p is None or not inside_temp(p) for p in paths):
            shown = " ".join(targets) or "paths read from stdin"
            hits.append((ASK, "rm-recursive", f"Recursive delete of {shown}: a human must confirm."))
    if not hits:
        return None
    hits.sort(key=lambda h: 0 if h[0] == DENY else 1)
    return hits[0]


def decide(command: str, cwd: str | None = None) -> tuple[str, str, str] | None:
    """Return (decision, rule_id, message) for the strictest matching rule, or None."""
    norm = normalize(command)
    hits = [(decision, rule_id, msg) for rule_id, rx, decision, msg in RULES if re.search(rx, norm)]
    rm_hit = check_rm(command, cwd)
    if rm_hit:
        hits.append(rm_hit)
    if not hits:
        return None
    hits.sort(key=lambda h: 0 if h[0] == DENY else 1)
    return hits[0]


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--dry-run":
        result = decide(" ".join(sys.argv[2:]), os.getcwd())
        print(f"{result[0]:<5} {result[1]}: {result[2]}" if result else "pass  (no rule matched; normal permission flow decides)")
        return 0
    try:
        payload = read_payload()
        command = (payload.get("tool_input") or {}).get("command", "")
        result = decide(command, payload.get("cwd") or None)
        if result is None:
            log_decision("guard_bash", payload, "pass", detail=command)
            return 0
        decision, rule_id, message = result
        log_decision("guard_bash", payload, decision, rule_id, command)
        emit_pretooluse(decision, f"[guardrail:{rule_id}] {message}")
        return 0
    except Exception as exc:
        print(f"guard_bash.py failed ({exc!r}); blocking the command to stay safe.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
