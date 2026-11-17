---
name: build-task
description: Implement one task in an existing codebase end to end - recon, brief, tests first, implement, then validate with independent reviewers, fix and re-validate until clean. Never commits.
argument-hint: "<task description | Task Brief>"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: >-
            GR_DIR=UNSET;
            for d in "$GUARDRAILS_HOOKS_DIR" "$GR_DIR" "${CLAUDE_PROJECT_DIR}/.claude/hooks/guardrails" "$HOME/.claude/hooks/guardrails";
            do [ -n "$d" ] && [ -f "$d/guard_bash.py" ] && exec python3 "$d/guard_bash.py"; done;
            case "$GR_DIR" in UNSET|off) exit 0 ;; esac;
            echo "guardrails: guard_bash.py not found in $GR_DIR. Reinstall it or re-run the guardrails setup." >&2; exit 2
          timeout: 10
          onFailure: block
    - matcher: "Write|Edit|MultiEdit|NotebookEdit"
      hooks:
        - type: command
          command: >-
            GR_DIR=UNSET;
            for d in "$GUARDRAILS_HOOKS_DIR" "$GR_DIR" "${CLAUDE_PROJECT_DIR}/.claude/hooks/guardrails" "$HOME/.claude/hooks/guardrails";
            do [ -n "$d" ] && [ -f "$d/guard_write.py" ] && exec python3 "$d/guard_write.py"; done;
            case "$GR_DIR" in UNSET|off) exit 0 ;; esac;
            echo "guardrails: guard_write.py not found in $GR_DIR. Reinstall it or re-run the guardrails setup." >&2; exit 2
          timeout: 10
          onFailure: block
---

ROLE: Senior engineer making one change in an existing codebase, with tests that would catch a regression. The change is done when independent reviewers find nothing left to fix, not when it compiles
TASK: Implement: $ARGUMENTS
CONTEXT: No PRD or architecture doc is assumed. "Done" is defined by the task text, the existing code and tests, and the Task Brief you derive.
Build steps: @${CLAUDE_SKILL_DIR}/../../shared/build-steps.md Scenario checklist: @${CLAUDE_SKILL_DIR}/../../shared/scenario-checklist.md Validation loop: @${CLAUDE_SKILL_DIR}/../../shared/validation-loop.md
Question round: @${CLAUDE_SKILL_DIR}/../../shared/question-round.md Task profile: @${CLAUDE_SKILL_DIR}/../../shared/task-profile.md
Verification profiles: ${CLAUDE_SKILL_DIR}/../../shared/verification-profiles.md, read only when CLAUDE.md and CI name no test command
Guardrails setup: ${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md,
read only when Glob finds no guard_bash.py in `.claude/hooks/guardrails/` under the project or in `~/.claude/hooks/guardrails/` (when it finds one, guardrails are active and nothing else is needed)
CONSTRAINTS: This task only. No drive-by refactors or reformatting. No new dependencies unless the task cannot be done without one and the user approves it. No destructive git commands (reset --hard,
checkout --, restore, clean, stash drop, force push).
Never stage, commit, push or switch branches: every change stays uncommitted in the working tree for the user to review.
Files that were already modified or untracked before you started are off-limits unless the task requires them; say so when it does.
GUARDRAILS: When guardrails are installed, hooks deny destructive git commands, force pushes and credentials in written files, and commits and new dependencies wait for a human click.
The rules above apply either way.
If a call is denied with [guardrail:...], do not retry it another way: record it in the report.
ONE TURN: the whole build runs in this turn. Never use `run_in_background`, Monitor or a background agent: a notification arrives as a new turn,
and from then on the build has lost this skill's tool pre-approvals and hooks.
Give a long command the maximum timeout, or split it.
CONTEXT BUDGET: everything you read or print stays in context for the rest of the build and is paid for again on every call. Grep before you read. For a file over about 300 lines,
Read with offset and limit around the hits.
Never print a whole file through Bash. Run tests and checks as the validation loop's SHORT OUTPUT says. Use Edit for a change at one site;
use a patch script only for many mechanical edits in one file.

Live state (verify these render; if they appear as literal text, run the git commands yourself). It shows the session folder, which may not be the repository:
- Branch: !`git branch --show-current 2>/dev/null || echo "not a git repository"`
- Last commit: !`git log --oneline -1 2>/dev/null || echo "not a git repository"`
- Uncommitted: !`git status --short 2>/dev/null || echo "not a git repository"`

## Flow
Run the guardrails setup first. Then follow the build steps (Step 0 to Step 9) with TASK = $ARGUMENTS, and print the Step 9 report.
