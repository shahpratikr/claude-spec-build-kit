#!/usr/bin/env python3
"""Install the guardrail hook scripts and point the guarded skills and agents at them.

Run by the guardrails setup step (shared/guardrails-setup.md) after the user answers:
  configure.py --dir DIR   copy the hook scripts into DIR, check that they run, and use them
  configure.py --off       the user declined: stop asking and run without guardrails

The hooks sections find scripts in <project>/.claude/hooks/guardrails and ~/.claude/hooks/guardrails
on their own, so choosing one of those leaves the hooks sections unconfigured. Any other folder is
written into every hooks section as GR_DIR='<folder>'.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ("_guardrail_common.py", "guard_bash.py", "guard_write.py", "guard_prompt.py")
MARKER = re.compile(r"GR_DIR=[^;\n]*;")


def standard_dirs(project: str | None) -> list[Path]:
    dirs = [Path.home() / ".claude" / "hooks" / "guardrails"]
    if project:
        dirs.append(Path(project) / ".claude" / "hooks" / "guardrails")
    return [d.resolve() for d in dirs]


def hook_files(root: Path) -> list[Path]:
    """Skills and agents under root whose hooks sections carry the GR_DIR marker."""
    candidates = [*root.glob("skills/*/SKILL.md"), *root.glob("agents/*.md")]
    return [f for f in candidates if MARKER.search(f.read_text())]


def set_marker(files: list[Path], value: str) -> None:
    for f in files:
        f.write_text(MARKER.sub(f"GR_DIR={value};", f.read_text()))


def install(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in SCRIPTS:
        shutil.copy2(HERE / name, dest / name)
    check = subprocess.run([sys.executable, str(dest / "guard_bash.py"), "--dry-run", "git push --force origin main"],
                           capture_output=True, text=True, timeout=30)
    if not check.stdout.startswith("deny"):
        raise SystemExit(f"check failed in {dest}: {check.stdout or check.stderr}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--dir", help="folder to install the hook scripts into")
    choice.add_argument("--off", action="store_true", help="run without guardrails and stop asking")
    parser.add_argument("--root", default=str(HERE.parent.parent),
                        help="folder that holds skills/ and agents/ (default: this installation)")
    parser.add_argument("--project", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(),
                        help="project root, for the <project>/.claude/hooks/guardrails location")
    args = parser.parse_args()

    files = hook_files(Path(args.root).expanduser().resolve())
    if not files:
        raise SystemExit(f"no hooks sections with GR_DIR found under {args.root}")

    if args.off:
        set_marker(files, "off")
        print(f"Guardrails off. {len(files)} hooks section(s) updated; the setup step will not ask again.")
        return 0

    dest = Path(args.dir).expanduser().resolve()
    if "'" in str(dest):
        raise SystemExit("Choose a folder without single quotes in its path.")
    install(dest)
    if dest in standard_dirs(args.project):
        set_marker(files, "UNSET")
        print(f"Guardrails installed in {dest}. The hooks sections find this standard location on their own.")
    else:
        set_marker(files, f"'{dest}'")
        print(f"Guardrails installed in {dest}. {len(files)} hooks section(s) now point there.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
