---
name: build-phase
description: Implement one task in an existing codebase end to end - recon, brief, tests first, implement, then validate with independent reviewers, fix and re-validate until clean. Never commits.
argument-hint: "<task description | Task Brief>"
model: sonnet
effort: high
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
CONTEXT: No PRD or architecture doc is assumed. "Done" is defined by the task text, the existing code and tests, and the Task Brief you derive. Scenario checklist: @${CLAUDE_SKILL_DIR}/../../shared/scenario-checklist.md Validation loop: @${CLAUDE_SKILL_DIR}/../../shared/validation-loop.md Question round: @${CLAUDE_SKILL_DIR}/../../shared/question-round.md Task profile: @${CLAUDE_SKILL_DIR}/../../shared/task-profile.md Guardrails setup: ${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md, read only when Glob finds no guard_bash.py in `.claude/hooks/guardrails/` under the project or in `~/.claude/hooks/guardrails/` (when it finds one, guardrails are active and nothing else is needed)
CONSTRAINTS: This task only. No drive-by refactors or reformatting. No new dependencies unless the task cannot be done without one and the user approves it. No destructive git commands (reset --hard, checkout --, restore, clean, stash drop, force push). Never stage, commit, push or switch branches: every change stays uncommitted in the working tree for the user to review. Files that were already modified or untracked before you started are off-limits unless the task requires them; say so when it does.
QUESTIONS: Ask only BLOCKING questions: ones the task, code and tests cannot answer, where a wrong guess would change an AC or a public contract. Ask them as the question round says, so the build continues in this turn. Every other open point becomes an assumption with your recommended default, listed in the report.
GUARDRAILS: When guardrails are installed, hooks deny destructive git commands, force pushes and credentials in written files, and commits and new dependencies wait for a human click. The rules above apply either way. If a call is denied with [guardrail:...], do not retry it another way: record it in the report.
ONE TURN: the whole build runs in this turn. Never use `run_in_background`, Monitor or a background agent: a notification arrives as a new turn, and from then on the build has lost this skill's model, effort, tool pre-approvals and hooks. Give a long command the maximum timeout, or split it.
CONTEXT BUDGET: everything you read or print stays in context for the rest of the build and is paid for again on every call. Grep before you read. For a file over about 300 lines, Read with offset and limit around the hits. Never print a whole file through Bash. Run tests and checks as the validation loop's SHORT OUTPUT says. Use Edit for a change at one site; use a patch script only for many mechanical edits in one file.

Live state (verify these render; if they appear as literal text, run the git commands yourself):
- Branch: !`git branch --show-current 2>/dev/null || echo "not a git repository"`
- Last commit: !`git log --oneline -1 2>/dev/null || echo "not a git repository"`
- Uncommitted: !`git status --short 2>/dev/null || echo "not a git repository"`

## Step 0 - Preconditions and snapshot
- If $ARGUMENTS is empty, ask for the task and stop.
- If the live state says "not a git repository" and the task names a repository (a path, or a plan whose files sit in one), warn in one line: "This session started outside <repo>, so Claude Code did not load its CLAUDE.md, settings or memory, and hooks see <cwd> as the project. Start Claude Code in the repository root next time." Then read `<repo>/CLAUDE.md` yourself, run every git command as `git -C <repo> ...` and continue. With no repository named, ask for it as a BLOCKING question.
- If the task is to write or update the PRD, ARCHITECTURE.md or CLAUDE.md, name the skill that owns that file (/spec-prd, /spec-arch, /spec-claudemd) and stop.
- If $ARGUMENTS names a plan file (a `/spec-interview` handoff carries `Plan: <path>`), read the plan file: its Brief with the confirmed answers, its Design, its Blast radius and the row of the named step. Those decisions bind the build.
- Run the guardrails setup before anything else.
- Snapshot the starting state so the change can be validated without a commit. Run `git stash create`: it prints a hash that records the tracked files as they are now, without touching the working tree or index. BASE is that hash, or the output of `git rev-parse HEAD` when it prints nothing. Record BASE and the output of `git status --porcelain --untracked-files=all`.
- Find commands: CLAUDE.md (Commands + Testing) first, then package scripts / Makefile / CI config. An unknown test command is a BLOCKING question. Never substitute a guess. When CLAUDE.md and CI name no test command, read ${CLAUDE_SKILL_DIR}/../../shared/verification-profiles.md and ask the question with a recommended option from its table.

## Step 1 - Recon (read-only)
1. Locate the code involved. Read the relevant functions of at least 2 sibling implementations and of their tests, not whole files (CONTEXT).
2. Grep for callers of everything you may change.
3. Identify layering/import direction, naming and placement patterns, error-handling and logging style, public contracts touched. The invariants in CLAUDE.md bind the change.
4. `git log -5 -- <area>`: recent changes and any earlier Task Briefs in commit bodies.
5. If ARCHITECTURE.md exists, read the sections that cover the code you will change (CLAUDE.md, Project docs, says which).

## Step 2 - Baseline
Run the full test command (plus lint/typecheck if they exist) BEFORE editing. Record pass/fail counts and the names of failing tests: these are pre-existing failures and are NOT yours to fix. If any overlap the area you will change, note it in the brief. If the suite is very slow, run the area subset and say so.

## Step 3 - Task Brief + Test Plan (no approval gate)
Write these in your reply before creating any file, so the user can follow the build:
1. Task Brief: goal, in/out of scope (at least 3 out), ACs (AC-1..n, "The system shall ..."), assumptions with the default you chose, blocking questions. If $ARGUMENTS already contains ACs from /spec-interview, reuse them verbatim. When a plan was read, reuse the plan's confirmed answers and scenario coverage, and derive only what the plan lacks.
2. Test Plan: apply the checklist. One row per category: APPLICABLE (scenarios -> test name -> level -> file) or N/A (the grep or file that proves it).
3. File tree: files to create/modify, each marked new/modified and "mirrors <existing file>".
4. Anything beyond the ACs is SPECULATIVE: do not build it; list it in the report.
5. Variant table and pre-mortem, before any test:
   - For every input surface the change accepts or emits (strings, paths, formats, markup, CLI arguments, closed sets), list its syntactic variants from checklist category 2. Mark each one handled, with the test that will cover it, or N/A, with a reason grounded in the code.
   - Per AC, the two most likely ways the implementation could be wrong, each mapped to a test.
   The table is your reasoning: it feeds the test plan and the validation loop's fix plans, and never goes to a reviewer.
6. Size gate. Every review round re-reads the whole change, so one run builds at most about 10 production files. When the file tree has more, or the repository has no code yet and the task is more than its skeleton, ask one BLOCKING question (category "scope"), even though it is not about intent. The options are "Split it with /spec-interview (Recommended)", described with the file count, and "Build it all in one run", described as taking hours of review. On split, print the count and a ready line, `/spec-interview <task> docs/plans/<task-slug>.md`, and stop. A "Step N of M" task from a plan is gated the same way.
7. Profile: print `Profile: <light | standard | deep> (<trigger or none>)` as the Task profile says, and pass it to the validation loop (a deep profile adds criteria-auditor at size tier S).
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
Run `git diff <BASE>` and read it, plus every new file (in parts when it is over about 300 lines), and check:
- Only planned files changed; every hunk maps to an AC; no unrelated formatting or renames; no off-limits file touched
- No debug output, commented-out code, secrets
- Every comment and docstring in the diff, and any unchanged one the change made wrong, is accurate and follows the Step 5 comment rules
- Error paths and resource cleanup handled as surrounding code does
- Callers of any changed signature updated (grep again)
- Checklist category 9 holds claim by claim: each statement matches the code and the sources, none contradicts another, every closed set is complete. The reviewers check this next
- Each problem you find here is fixed everywhere it occurs: grep for its siblings before moving on
- Public contracts, schemas, config remain backward compatible; migrations reversible
- Docs, types, changelog, API specs updated if the repo maintains them
- Lint, format and type checks pass
Fix problems before testing.

## Step 7 - Verify
a. New tests pass.
b. Full suite + lint + typecheck (+ build if it exists). Compare with the Step 2 baseline: no NEW failures. Pre-existing failures are reported, not fixed.
c. If new tests involve time, async, concurrency or randomness, run them 3 times.
d. Can-fail pass: run it on every changed production line, as the validation loop defines it, once. Kill each survivor with a test, or record why it cannot change behavior. A task with no unit tests (infrastructure, scripts, configuration, docs) is not executable-verified: the can-fail pass is N/A with that reason, and each AC is verified by the output of a validation command that exits non-zero when the AC is violated (the rules in verification-profiles.md).
e. If coverage tooling exists, check changed lines. Test each uncovered line or justify it.
f. Failures caused by this change: fix now. Do not proceed with new failures.

## Step 8 - Validate, fix, re-validate
Run the validation loop with TASK = $ARGUMENTS verbatim, the brief's ACs, the confirmed answers (the plan's, the brief's and this run's), the sources (spec or source files the task or brief names, and the plan path), BASE, the file lists, the commands, the Step 2 baseline and the Step 7 results as the facts, and the Step 3 variant table. Round 1 reuses the facts, the can-fail pass included. The loop sets the size tier. Before each fix round, write and check the loop's fix plan; no edit starts before its check line. Then fix every MUST-FIX finding by following Steps 4-6, and re-check as the loop says. Round 3 runs only when the loop's triggers hold. After the last review, make no production edit.

## Step 9 - Report and stop
Print exactly:
```
Build complete. Nothing was staged or committed.
Verdict: [PASS | NEEDS REVIEW] after [N] validation round(s)
Files: created [...] / modified [...]
Size gate: [n production files | over the gate, built in one run at the user's choice]
AC -> tests: AC-1 -> [test names] ...
Scenario categories: APPLICABLE n / N/A n  (list each N/A with its reason)
Variant table: [n surfaces, n rows: handled n / N/A n]
Tests: baseline [pass/fail] -> now [pass/fail]; pre-existing failures untouched: [names]; lint/typecheck/build: [results | none]
Can-fail: [per round: breaks run, killed, survivors left open with the reason | none]
Validation: [one line per round, from the validation loop, plus the R3 skip line when round 3 did not run]
Fix plans: [per round: path and its fix-plan check line | none]
Dismissed findings: [finding -> evidence file:line | none]
Needs your decision: [open items | none]
Assumptions applied: [point -> default chosen | none]
Not built (speculative): [items | none]
Spend: profile [light | standard | deep], agents spawned [n], validation rounds [n], full-suite runs [n]
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
