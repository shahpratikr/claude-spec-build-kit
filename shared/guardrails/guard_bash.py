#!/usr/bin/env python3
"""Claude Code PreToolUse hook: deny or ask before risky Bash commands.

How it plugs in: Claude Code runs this script before every Bash tool call and
sends the pending call as JSON on stdin. The script prints a decision:
  - nothing      -> no opinion, the normal permission flow continues
  - "deny"       -> the call is blocked and Claude reads the reason
  - "ask"        -> a human must confirm, even in auto mode
If the script itself crashes it exits 2, which blocks the call (fail closed).
Register it with "onFailure": "block" too, so a missing script also blocks.

Two kinds of rule run. Text rules match the normalized command (secret files, a download piped to an interpreter,
new dependencies). Argument rules split the command into shell segments and read the arguments of git, rm, cloud and
infrastructure tools, so a commit message, a grep pattern or the body of a quoted heredoc that merely mentions a command
is not mistaken for that command. Command substitutions, `bash -c` strings and `eval` are followed.

Try a command without Claude:   python3 guard_bash.py --dry-run "git push -f origin main"
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _guardrail_common import emit_pretooluse, log_decision, read_payload

DENY, ASK = "deny", "ask"
Hit = tuple  # (decision, rule_id, message)

RULES: list[tuple[str, str, str, str]] = [
    ("pipe-to-interpreter",
     r"\b(?:curl|wget)\b[^|;&]*\|\s*(?:sudo\s+)?(?:(?:ba|z|da|k)?sh|python3?|perl|ruby|node)\b"
     r"|\b(?:(?:ba|z|da|k)?sh|source)\s+<\(\s*(?:curl|wget)\b"
     r"|\b(?:ba|z|da|k)?sh\s+-c\s+\$\(\s*(?:curl|wget)\b",
     DENY, "Piping a download straight into an interpreter runs unreviewed remote code."),
    ("read-secret-file",
     r"(?:^|[\s/=(])\.env(?:\.(?!example\b|sample\b|template\b)[\w.-]+)?(?=$|[\s)])"
     r"|\bid_(?:rsa|ed25519|ecdsa)\b(?!\.pub)|\.aws/credentials\b"
     r"|\.azure/(?:msal_token_cache|accesstokens|service_principal_entries|tokencache)"
     r"|\.kube/config\b|(?:^|[\s/=(])\.netrc\b|\.docker/config\.json\b|\.(?:pfx|p12)(?=$|[\s)])",
     DENY, "That command touches a secrets file (.env, an SSH private key, cloud or cluster credentials, .netrc, a .pfx or .p12 certificate store)."),
    ("add-dependency",
     r"\bnpm\s+(?:install|i|add)\b(?:\s+-\S+)*\s+[^-\s&|;]"
     r"|\bpnpm\s+(?:install|i)\b(?:\s+-\S+)*\s+[^-\s&|;]"
     r"|\b(?:yarn|pnpm|poetry|cargo|uv|bundle)\s+add\b"
     r"|\bpip3?\s+install\b(?!\s+(?:-r|--requirement)\s)(?!\s+-e\s+\.(?:\s|$))(?!\s+\.(?:\s|$))(?!\s+--upgrade\s+pip\b)\s+\S"
     r"|\bgo\s+get\b|\bgo\s+install\s+\S+@"
     r"|\bgem\s+install\b|\bcomposer\s+require\b"
     r"|\b(?:brew|apt|apt-get|yum|dnf|apk)\s+(?:install|add)\b"
     r"|\binstall-(?:module|psresource)\b|\bdotnet\s+add\b(?:\s+\S+)?\s+package\b|\baz\s+extension\s+add\b"
     r"|\b(?:nuget|pipx|conda|mamba|winget|choco)\s+install\b",
     ASK, "Adding a dependency or package needs a human click."),
]

CATASTROPHIC_TARGETS = {"/", "/*", "~", "~/", "~/*", "$home", "${home}", ".", "./", "./*", "..", "../", "*"}
WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "xargs", "export"}
WRAPPER_VALUE_FLAGS = {"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-U", "-n", "-I", "-P", "-L", "-s", "-d", "-E"}
KEYWORDS = {"!", "{", "}", "then", "do", "else", "elif", "if", "while", "until"}
SHELLS = {"sh", "bash", "zsh", "dash"}
POWERSHELL = {"pwsh", "powershell", "pwsh-preview"}
SQL_CLIENTS = {"psql", "sqlcmd", "mysql", "mariadb", "sqlite3"}
READERS = {"cat", "less", "more", "head", "tail", "bat", "grep", "egrep", "fgrep", "rg", "sed", "awk", "cp", "mv", "scp",
           "rsync", "base64", "xxd", "od", "strings", "type", "get-content", "gc", "select-string"}
SENSITIVE_FILE = re.compile(r"(?i)(?:^|/)(?:terraform\.tfstate(?:\.backup)?|local\.settings\.json|\.npmrc)$|\.(?:tfvars|pem|key)$")
SECRET_NAME = re.compile(r"(?i)secret|token|key|pass|pwd|credential")
REMOTE_PATH = re.compile(r"^(?:[\w.-]+@)?[\w][\w.-]*:(?!//)")
PS_IEX_WEB = re.compile(r"(?i)\b(?:iex|invoke-expression)\b[^;]*\b(?:irm|iwr|invoke-restmethod|invoke-webrequest|downloadstring)\b"
                        r"|\b(?:irm|iwr|invoke-restmethod|invoke-webrequest)\b[^;]*\|\s*(?:iex|invoke-expression)\b")
PS_CLOUD_DELETE = re.compile(r"(?i)\bRemove-(?:Az|Mg|Entra|AzureAD|Msol|AD|Mailbox|SPO|PnP)\w*")
SQL_DESTRUCTIVE = re.compile(r"(?i)\b(?:drop|truncate)\b")
ASSIGNMENT = re.compile(r"^([A-Za-z_]\w*)=(.*)$", re.S)
VARIABLE = re.compile(r"\$(?:\{(\w+)\}|(\w+))")
GIT_OPTS_WITH_ARG = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"}


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
    import tempfile  # only an rm needs it
    for root in {os.path.realpath(tempfile.gettempdir()), os.path.realpath("/tmp")}:
        rel = os.path.relpath(path, root)
        if rel != ".." and not rel.startswith(".." + os.sep) and len(rel.split(os.sep)) >= 2:
            return True
    return False


def is_catastrophic(path: str) -> bool:
    home = os.path.realpath(os.path.expanduser("~"))
    return path == "/" or home == path or home.startswith(path.rstrip("/") + "/")


def _git(cwd: str, *args: str):
    import subprocess  # only an rm of an ignored folder needs it
    try:
        return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None


def ignored_untracked(paths: list[str], cwd: str | None) -> bool:
    """True when every path is inside the project's repository, ignored by git and not tracked: a build folder, not work."""
    if not cwd or not paths:
        return False
    top = _git(cwd, "rev-parse", "--show-toplevel")
    if not top or top.returncode != 0:
        return False
    root = os.path.realpath(top.stdout.strip())
    for p in paths:
        real = os.path.realpath(p)
        if real == root or not real.startswith(root + os.sep):
            return False
        rel = os.path.relpath(real, root)
        ignored = _git(root, "check-ignore", "-q", "--", rel)
        tracked = _git(root, "ls-files", "--", rel)
        if not ignored or ignored.returncode != 0 or not tracked or tracked.returncode != 0 or tracked.stdout.strip():
            return False
    return True


def scan_subst(text: str, i: int) -> int:
    """text[i:i+2] is '$('. Return the index after the matching ')' (or the end of the text)."""
    depth, quote, j = 0, "", i + 1
    while j < len(text):
        c = text[j]
        if quote:
            if c == "\\" and quote == '"':
                j += 2
                continue
            if c == quote:
                quote = ""
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return len(text)


def substitutions(text: str) -> list[str]:
    out, i = [], 0
    while i < len(text):
        if text[i:i + 2] == "$(":
            k = scan_subst(text, i)
            out.append(text[i + 2:k - 1] if text[k - 1:k] == ")" else text[i + 2:k])
            i = k
        elif text[i] == "`":
            j = text.find("`", i + 1)
            j = len(text) if j == -1 else j
            out.append(text[i + 1:j])
            i = j + 1
        else:
            i += 1
    return out


def lex(command: str) -> list[list[tuple[str, bool]]]:
    """Split a command into shell segments of tokens. A token is (text, expands): expands is False when the whole token
    was single-quoted, so it cannot hold a command substitution. Bodies of heredocs with a quoted delimiter are dropped."""
    segments: list[list[tuple[str, bool]]] = []
    seg: list[tuple[str, bool]] = []
    buf: list[str] = []
    st = {"in": False, "exp": False}
    pending: list[str] = []
    i, n = 0, len(command)

    def end_token() -> None:
        if st["in"]:
            seg.append(("".join(buf), st["exp"]))
        buf.clear()
        st["in"] = st["exp"] = False

    def end_segment() -> None:
        nonlocal seg
        end_token()
        if seg:
            segments.append(seg)
        seg = []

    def add(text: str, expands: bool = True) -> None:
        buf.append(text)
        st["in"] = True
        st["exp"] = st["exp"] or expands

    while i < n:
        c = command[i]
        if c in " \t":
            end_token()
            i += 1
        elif c == "\n":
            end_segment()
            i += 1
            while pending:
                tag = pending.pop(0)
                while i < n:
                    nl = command.find("\n", i)
                    line = command[i:] if nl == -1 else command[i:nl]
                    i = n if nl == -1 else nl + 1
                    if line.strip() == tag:
                        break
        elif c == "#" and not st["in"]:
            nl = command.find("\n", i)
            i = n if nl == -1 else nl
        elif c == "\\" and i + 1 < n:
            if command[i + 1] == "\n":
                i += 2
            else:
                add(command[i + 1])
                i += 2
        elif c == "'":
            j = command.find("'", i + 1)
            j = n if j == -1 else j
            add(command[i + 1:j], expands=False)
            i = j + 1
        elif c == '"':
            j, part = i + 1, []
            while j < n and command[j] != '"':
                if command[j] == "\\" and j + 1 < n:
                    part.append(command[j + 1])
                    j += 2
                elif command[j:j + 2] == "$(":
                    k = scan_subst(command, j)
                    part.append(command[j:k])
                    j = k
                else:
                    part.append(command[j])
                    j += 1
            add("".join(part))
            i = j + 1
        elif command[i:i + 2] == "$(":
            k = scan_subst(command, i)
            add(command[i:k])
            i = k
        elif c == "`":
            j = command.find("`", i + 1)
            j = n - 1 if j == -1 else j
            add(command[i:j + 1])
            i = j + 1
        elif command[i:i + 2] in ("&&", "||"):
            end_segment()
            i += 2
        elif c == "<" and command[i:i + 2] == "<<" and command[i:i + 3] != "<<<":
            j = i + 2 + (1 if command[i + 2:i + 3] == "-" else 0)
            while j < n and command[j] in " \t":
                j += 1
            if j < n and command[j] in "'\"":
                k = command.find(command[j], j + 1)
                k = n - 1 if k == -1 else k
                if command[j + 1:k]:
                    pending.append(command[j + 1:k])
                i = k + 1
            else:
                i = j
        elif c in ";|()" or (c == "&" and command[i + 1:i + 2] != ">" and command[i - 1:i] != ">"):
            end_segment()
            i += 1
        else:
            add(c)
            i += 1
    end_segment()
    return segments


def _short(args: list[str], letter: str) -> bool:
    return any(a.startswith("-") and not a.startswith("--") and letter in a[1:] for a in args)


def git_hits(tokens: list[str]) -> list[Hit]:
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in GIT_OPTS_WITH_ARG else 1
    if i >= len(tokens):
        return []
    sub, args = tokens[i], tokens[i + 1:]
    force = "--force" in args or _short(args, "f")
    if sub == "reset" and "--hard" in args:
        return [(DENY, "git-reset-hard", "git reset --hard throws away uncommitted work. Ask the user to run it themselves if it is really needed.")]
    if sub == "clean" and force and "--dry-run" not in args and not _short(args, "n"):
        return [(DENY, "git-clean-force", "git clean -f permanently deletes untracked files.")]
    if sub == "checkout" and ("--" in args or "." in args or force):
        return [(DENY, "git-checkout-discard", "git checkout -- / git checkout . / git checkout -f discards uncommitted changes.")]
    if sub == "switch" and (force or "--discard-changes" in args):
        return [(DENY, "git-switch-discard", "git switch -f / --discard-changes discards uncommitted changes.")]
    if sub == "restore" and (not ("--staged" in args or _short(args, "S")) or "--worktree" in args or _short(args, "W")):
        return [(DENY, "git-restore-worktree", "git restore without --staged, or with --worktree, discards uncommitted changes.")]
    if sub == "stash" and args[:1] and args[0] in ("drop", "clear"):
        return [(DENY, "git-stash-drop", "Dropping stashes loses work permanently.")]
    if sub == "add" and any(a in ("-A", "--all", ".") for a in args):
        return [(DENY, "git-add-all", "Stage files by explicit path, never with git add -A, --all or '.'.")]
    if sub == "commit":
        return [(ASK, "git-commit-needs-human", "Commits need a human click.")]
    if sub == "push":
        if force or any(a.startswith("--force-with-lease") or (a.startswith("+") and len(a) > 1) for a in args):
            return [(DENY, "git-push-force", "Force-pushing rewrites shared history. Push normally, or ask the user to do it.")]
        if "--delete" in args or _short(args, "d") or any(a.startswith(":") and len(a) > 1 for a in args):
            return [(ASK, "git-remote-delete", "Deleting a remote branch or tag changes shared state: a human must confirm.")]
        return [(ASK, "git-push-needs-human", "Pushing publishes commits: a human must confirm.")]
    if sub == "branch" and (_short(args, "D") or ("--delete" in args and force)):
        return [(ASK, "git-branch-force-delete", "Force-deleting a branch can lose unmerged commits: a human must confirm.")]
    if (sub == "reflog" and args[:1] and args[0] in ("expire", "delete")) or sub == "prune" or (sub == "gc" and any(a.startswith("--prune") for a in args)):
        return [(ASK, "git-history-prune", "Pruning the reflog or unreachable objects makes lost commits unrecoverable: a human must confirm.")]
    return []


def rm_hit(args: list[str], env: dict, cwd: str | None, from_stdin: bool) -> Hit | None:
    split = args.index("--") if "--" in args else len(args)
    flags = [t for t in args[:split] if t.startswith("-")]
    targets = [t for t in args[:split] if not t.startswith("-")] + args[split + 1:]
    if not any(f == "--recursive" or (not f.startswith("--") and "r" in f.lower()) for f in flags):
        return None
    if (not targets and not from_stdin) or any(t.lower() in CATASTROPHIC_TARGETS for t in targets):
        return (DENY, "rm-recursive-catastrophic", f"Refusing recursive delete of {' '.join(targets) or '(nothing)'}.")
    paths = [resolve(t, env, cwd) for t in targets]
    if any(p is not None and is_catastrophic(p) for p in paths):
        return (DENY, "rm-recursive-catastrophic", f"Refusing recursive delete of {' '.join(targets)}: it reaches / or your home folder.")
    if from_stdin or any(p is None or not inside_temp(p) for p in paths):
        if not from_stdin and all(p is not None for p in paths) and ignored_untracked(paths, cwd):
            return None
        return (ASK, "rm-recursive", f"Recursive delete of {' '.join(targets) or 'paths read from stdin'}: a human must confirm.")
    return None


def ps_hits(tokens: list[str], cwd: str | None) -> list[Hit]:
    """PowerShell run as `pwsh -c "..."`: the string is PowerShell, not Bash, so it is read with its own patterns."""
    import shlex
    hits: list[Hit] = []
    low = [t.lower() for t in tokens]
    if any(t in ("-e", "-enc", "-encodedcommand") for t in low):
        hits.append((ASK, "powershell-encoded", "An encoded PowerShell command cannot be inspected: a human must confirm."))
    inner = next((" ".join(tokens[i + 1:]) for i, t in enumerate(low) if t in ("-c", "-command", "-commandwithargs") and i + 1 < len(tokens)), None)
    if inner is None:
        return hits
    if PS_IEX_WEB.search(inner):
        hits.append((DENY, "pipe-to-interpreter", "Running downloaded PowerShell with iex or Invoke-Expression runs unreviewed remote code."))
    if PS_CLOUD_DELETE.search(inner):
        hits.append((ASK, "cloud-delete", "That PowerShell command removes cloud or tenant objects: a human must confirm."))
    if re.search(r"(?i)\bRemove-Item\b", inner) and re.search(r"(?i)\s-recurse\b|\s-r\b", inner):
        try:
            parts = shlex.split(inner)
        except ValueError:
            parts = inner.split()
        after = parts[[p.lower() for p in parts].index("remove-item") + 1:] if "remove-item" in [p.lower() for p in parts] else []
        targets = [t for i, t in enumerate(after) if not t.startswith("-") or (i and after[i - 1].lower() in ("-path", "-literalpath"))]
        targets = [t for t in targets if not t.startswith("-")]
        paths = [resolve(t, {}, cwd) for t in targets]
        if not targets or any(t.lower() in CATASTROPHIC_TARGETS for t in targets) or any(p is not None and is_catastrophic(p) for p in paths):
            hits.append((DENY, "rm-recursive-catastrophic", f"Refusing recursive Remove-Item of {' '.join(targets) or '(nothing)'}."))
        elif any(p is None or not inside_temp(p) for p in paths):
            hits.append((ASK, "rm-recursive", f"Recursive Remove-Item of {' '.join(targets)}: a human must confirm."))
    return hits


def _upload_flag(args: list[str]) -> bool:
    flag_with_value = {"-d", "--data", "--data-binary", "--data-ascii", "--data-urlencode", "-F", "--form"}
    for i, a in enumerate(args):
        if a in ("-T", "--upload-file"):
            return True
        if a in flag_with_value and i + 1 < len(args) and "@" in args[i + 1]:
            return True
        if re.match(r"^(?:-d@|-F.*@|--(?:data(?:-binary|-urlencode|-ascii)?|form)=.*@)", a):
            return True
    return False


def tool_hits(head: str, args: list[str], tokens: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    words = set(args)
    if head == "az" and (words & {"delete", "purge"} or any(a.lower() == "--mode=complete" for a in args)
                         or any(a.lower() == "--mode" and i + 1 < len(args) and args[i + 1].lower() == "complete" for i, a in enumerate(args))):
        hits.append((ASK, "cloud-delete", "That az command deletes or purges cloud resources (or deploys in Complete mode): a human must confirm."))
    elif head in ("terraform", "tofu") and ("destroy" in words or ("apply" in words and words & {"-auto-approve", "--auto-approve"})):
        hits.append((ASK, "iac-destroy", "terraform destroy, or apply with -auto-approve, changes real infrastructure: a human must confirm."))
    elif head in ("kubectl", "oc") and "delete" in words:
        hits.append((ASK, "cluster-delete", "kubectl delete removes cluster objects: a human must confirm."))
    elif head == "helm" and words & {"uninstall", "delete"}:
        hits.append((ASK, "cluster-delete", "helm uninstall removes a release: a human must confirm."))
    elif head in ("docker", "podman") and ("prune" in words or args[:2] == ["volume", "rm"]):
        hits.append((ASK, "container-prune", "Pruning or removing volumes deletes data: a human must confirm."))
    elif head in SQL_CLIENTS:
        text = " ".join(args)
        if SQL_DESTRUCTIVE.search(text) or (re.search(r"(?i)\bdelete\s+from\b", text) and not re.search(r"(?i)\bwhere\b", text)):
            hits.append((ASK, "sql-destructive", "That SQL drops, truncates or deletes without a filter: a human must confirm."))
    elif head == "curl" and _upload_flag(args):
        hits.append((ASK, "outward-upload", "That curl uploads a file or request body from disk to a remote host: a human must confirm."))
    elif head == "wget" and any(a.startswith(("--post-file", "--body-file")) for a in args):
        hits.append((ASK, "outward-upload", "That wget uploads a file to a remote host: a human must confirm."))
    elif head in ("scp", "rsync") and any(not a.startswith("-") and (REMOTE_PATH.match(a) or a.startswith("rsync://")) for a in args):
        hits.append((ASK, "outward-copy", "Copying to or from a remote host moves data off this machine: a human must confirm."))
    elif head == "gh" and args[:2] == ["gist", "create"]:
        hits.append((ASK, "outward-publish", "gh gist create publishes content: a human must confirm."))
    elif head == "printenv" and (not args or any(SECRET_NAME.search(a) for a in args)):
        hits.append((ASK, "env-dump", "Dumping the environment can print secrets: a human must confirm."))
    if head in READERS and any(SENSITIVE_FILE.search(a) for a in args):
        hits.append((ASK, "sensitive-file", "That command reads a file that often holds secrets (.pem, .key, .tfvars, terraform state, local.settings.json, .npmrc): a human must confirm."))
    return hits


def _bare_env(tokens: list[str]) -> bool:
    """`env` with no command after its options and assignments prints the whole environment."""
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if ASSIGNMENT.match(t):
            i += 1
        elif t.startswith("-"):
            i += 2 if t in ("-u", "-C", "-S") else 1
        else:
            return False
    return True


def analyze(command: str, cwd: str | None, depth: int = 0) -> list[Hit]:
    hits: list[Hit] = []
    if depth > 4:
        return hits
    env: dict[str, str | None] = {}
    for tokens in lex(command):
        texts = [t for t, _ in tokens]
        for text, expands in tokens:
            if expands and ("$(" in text or "`" in text):
                for inner in substitutions(text):
                    hits += analyze(inner, cwd, depth + 1)
        if texts and os.path.basename(texts[0]) == "env" and _bare_env(texts):
            hits.append((ASK, "env-dump", "Dumping the environment can print secrets: a human must confirm."))
        from_stdin = after_wrapper = False
        while texts:
            head = os.path.basename(texts[0]).lower()
            assignment = ASSIGNMENT.match(texts[0])
            if assignment:
                env[assignment.group(1)] = expand(assignment.group(2), env)
                texts = texts[1:]
            elif head in KEYWORDS:
                texts = texts[1:]
            elif head in WRAPPERS:
                after_wrapper = True
                from_stdin = from_stdin or head == "xargs"
                texts = texts[1:]
            elif after_wrapper and texts[0].startswith("-"):
                texts = texts[2:] if texts[0] in WRAPPER_VALUE_FLAGS and len(texts) > 1 else texts[1:]
            else:
                break
        if from_stdin:
            names = [os.path.basename(t).lower() for t in texts]
            texts = texts[names.index("rm"):] if "rm" in names else texts
        if not texts:
            continue
        head, args = os.path.basename(texts[0]).lower(), texts[1:]
        if head == "cd":
            target = expand(args[0], env) if args else os.path.expanduser("~")
            if target is None or target == "-" or (cwd is None and not os.path.isabs(target)):
                cwd = None
            else:
                cwd = os.path.normpath(os.path.join(cwd or "/", target))
        elif head in SHELLS and "-c" in texts:
            at = texts.index("-c")
            for inner in texts[at + 1:at + 2]:
                hits += analyze(inner, cwd, depth + 1)
        elif head == "eval":
            hits += analyze(" ".join(args), cwd, depth + 1)
        elif head in POWERSHELL:
            hits += ps_hits(texts, cwd)
        elif head == "git":
            hits += git_hits(texts)
        elif head == "rm":
            hit = rm_hit(args, env, cwd, from_stdin)
            if hit:
                hits.append(hit)
        else:
            hits += tool_hits(head, args, texts)
    return hits


def decide(command: str, cwd: str | None = None) -> Hit | None:
    """Return (decision, rule_id, message) for the strictest matching rule, or None."""
    norm = normalize(command)
    hits = [(decision, rule_id, msg) for rule_id, rx, decision, msg in RULES if re.search(rx, norm)]
    hits += analyze(command, cwd)
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
