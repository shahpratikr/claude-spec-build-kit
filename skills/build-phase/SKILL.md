---
name: build-phase
description: Implement one task in an existing codebase end to end - recon, brief, tests first, implement, then validate with independent reviewers, fix and re-validate until clean. Never commits.
argument-hint: "<task description | Task Brief>"
model: opus
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
CONTEXT: No PRD or architecture doc is assumed. "Done" is defined by the task text, the existing code and tests, and the Task Brief you derive. Scenario checklist: @${CLAUDE_SKILL_DIR}/../../shared/scenario-checklist.md Validation loop: @${CLAUDE_SKILL_DIR}/../../shared/validation-loop.md Guardrails setup: @${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md
CONSTRAINTS: This task only. No drive-by refactors or reformatting. No new dependencies unless the task cannot be done without one and the user approves it. No destructive git commands (reset --hard, checkout --, restore, clean, stash drop, force push). Never stage, commit, push or switch branches: every change stays uncommitted in the working tree for the user to review. Files that were already modified or untracked before you started are off-limits unless the task requires them; say so when it does.
QUESTIONS: Ask only BLOCKING questions: ones the task, code and tests cannot answer, where a wrong guess would change an AC or a public contract. Ask them with AskUserQuestion so the build continues in this turn; if that tool is unavailable or returns no answer, print them and stop. Every other open point becomes an assumption with your recommended default, listed in the report.
GUARDRAILS: When guardrails are installed, hooks deny destructive git commands, force pushes and credentials in written files, and commits and new dependencies wait for a human click. The rules above apply either way. If a call is denied with [guardrail:...], do not retry it another way: record it in the report.

Live state (verify these render; if they appear as literal text, run the git commands yourself):
- Branch: !`git branch --show-current 2>/dev/null || echo "not a git repository"`
- Last commit: !`git log --oneline -1 2>/dev/null || echo "not a git repository"`
- Uncommitted: !`git status --short 2>/dev/null || echo "not a git repository"`

## Step 0 - Preconditions and snapshot
- If $ARGUMENTS is empty, ask for the task and stop.
- Run the guardrails setup before anything else.
- Snapshot the starting state so the change can be validated without a commit. Run `git stash create`: it prints a hash that records the tracked files as they are now, without touching the working tree or index. BASE is that hash, or the output of `git rev-parse HEAD` when it prints nothing. Record BASE and the output of `git status --porcelain --untracked-files=all`.
- Find commands: CLAUDE.md (Commands + Testing) first, then package scripts / Makefile / CI config. An unknown test command is a BLOCKING question. Never substitute a guess.
- If REPO_ANALYSIS.md exists and its recorded commit matches or is close to HEAD, use it for recon. Otherwise ignore it.

## Step 1 - Recon (read-only)
1. Locate the code involved. Read at least 2 sibling implementations and their tests.
2. Grep for callers of everything you may change.
3. Identify layering/import direction, naming and placement patterns, error-handling and logging style, public contracts touched.
4. `git log -5 -- <area>`: recent changes and any earlier Task Briefs in commit bodies.

## Step 2 - Baseline
Run the full test command (plus lint/typecheck if they exist) BEFORE editing. Record pass/fail counts and the names of failing tests: these are pre-existing failures and are NOT yours to fix. If any overlap the area you will change, note it in the brief. If the suite is very slow, run the area subset and say so.

## Step 3 - Task Brief + Test Plan (no approval gate)
Write these in your reply before creating any file, so the user can follow the build:
1. Task Brief: goal, in/out of scope (at least 3 out), ACs (AC-1..n, "The system shall ..."), assumptions with the default you chose, blocking questions. If $ARGUMENTS already contains ACs from /spec-interview or /spec-arch, reuse them verbatim.
2. Test Plan: apply the checklist. One row per category: APPLICABLE (scenarios -> test name -> level -> file) or N/A (reason grounded in the code).
3. File tree: files to create/modify, each marked new/modified and "mirrors <existing file>".
4. Anything beyond the ACs is SPECULATIVE: do not build it; list it in the report.
Ask any BLOCKING question now (see QUESTIONS), then continue. Do not wait for approval.

## Step 4 - Tests first
- Bug fix: write a failing repro test first. Run it. It must fail for the stated reason. Show the output.
- Feature: write tests for every AC and every APPLICABLE scenario. Run them. They must fail for the right reason (not an import or syntax error).
- Untested legacy code you will modify: first write characterization tests that pin current behavior. They must pass on the unmodified code.
Test rules: mirror the repo's layout, naming, fixtures and helpers. Put the AC id in the test name (or a JS describe() title), never in a docstring or comment. Assert behavior, not implementation. No sleeps, no network, no order dependence. Do not mock what is cheap to run for real.
After each test file: 2-line summary (what it covers | which ACs/scenarios).

## Step 5 - Implement
Follow the import-direction seen in recon: lowest-level, most-depended-upon code first.
After EACH file: 2-line summary (does | exports/changes) plus the AC ids it serves. Run the narrowest relevant tests. Do not move on until they pass.
Rules:
- Mirror neighboring naming, placement and error handling. Grep for an existing helper before writing a new one.
- No new cross-layer imports. No debug leftovers. No TODOs without the user's OK.
- Comments and docstrings, tests included:
  - Write one only for what the code and names cannot say: a non-obvious constraint, a reason, a trap. Delete any that restates the code or the test name.
  - At most 2 sentences, summary line included. No :param/:return:/:raises: lists unless the file already uses them; put return and error meaning in the sentences.
  - No AC, task or ticket ids and no wording relative to this change ("as today", "parity", "new", "rewrites the old test"). If CLAUDE.md declares a requirement-citation convention, follow it exactly (one line max). Otherwise trace via test names.
  - Every claim must match the code as written: the real caller, mock or behavior, not the intended one.
- A design decision that the brief, the code and the tests do not settle is a BLOCKING question. Never decide it silently.

## Step 6 - Self-review (read your own diff)
Run `git diff <BASE>`, read every new file, and check:
- Only planned files changed; every hunk maps to an AC; no unrelated formatting or renames; no off-limits file touched
- No debug output, commented-out code, secrets
- Every comment and docstring in the diff, and any unchanged one the change made wrong, is accurate and follows the Step 5 comment rules
- Error paths and resource cleanup handled as surrounding code does
- Callers of any changed signature updated (grep again)
- Public contracts, schemas, config remain backward compatible; migrations reversible
- Docs, types, changelog, API specs updated if the repo maintains them
- Lint, format and type checks pass
Fix problems before testing.

## Step 7 - Verify
a. New tests pass.
b. Full suite + lint + typecheck (+ build if it exists). Compare with the Step 2 baseline: no NEW failures. Pre-existing failures are reported, not fixed.
c. If new tests involve time, async, concurrency or randomness, run them 3 times.
d. Can-fail check: if a mutation tool exists (from manifests/CLAUDE.md), run it on changed files. Otherwise pick the 2-3 most important branches, make a one-line temporary break via str_replace, confirm a test fails, revert that exact edit, and re-run to confirm green. Report each.
e. If coverage tooling exists, check changed lines. Test each uncovered line or justify it.
f. Failures caused by this change: fix now. Do not proceed with new failures.

## Step 8 - Validate, fix, re-validate
Run the validation loop with TASK = $ARGUMENTS verbatim, the brief's ACs, BASE, the file lists, the commands and the Step 2 baseline. Fix every MUST-FIX finding by following Steps 4-7, then re-validate. Stop when a round finds nothing to fix, or after 3 rounds.

## Step 9 - Report and stop
Print exactly:
```
Build complete. Nothing was staged or committed.
Verdict: [PASS | NEEDS REVIEW] after [N] validation round(s)
Files: created [...] / modified [...]
AC -> tests: AC-1 -> [test names] ...
Scenario categories: APPLICABLE n / N/A n  (list each N/A with its reason)
Tests: baseline [pass/fail] -> now [pass/fail]; pre-existing failures untouched: [names]; lint/typecheck/build: [results | none]
Can-fail check: [results]
Validation: [one line per round, from the validation loop]
Dismissed findings: [finding -> evidence file:line | none]
Needs your decision: [open items | none]
Assumptions applied: [point -> default chosen | none]
Not built (speculative): [items | none]
Review: git diff <BASE>   new files: [...]
Undo: git diff <BASE> -- [modified files] | git apply -R   then delete: [new files]
Suggested commit message (not committed):
  [imperative title, max 72 chars]

  [1-2 sentences: what and why]

  Acceptance criteria:
  - AC-1 ...
  Tests: [files/names added]. Baseline: [N pre-existing failures unchanged | none]
```
Do NOT start another task.
