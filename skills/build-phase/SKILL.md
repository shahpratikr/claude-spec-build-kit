---
description: Implement one task in an existing codebase - recon, brief, tests first, implement, verify, commit
argument-hint: "<task description | Task Brief>"
model: sonnet
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Glob, Grep
---

ROLE: Senior engineer making one change in an existing codebase, with tests that would catch a regression
TASK: Implement: $ARGUMENTS
CONTEXT: No PRD or architecture doc is assumed. "Done" is defined by the task text, the existing code and tests, and the Task Brief you derive and the user approves at Gate 1. Scenario checklist: @${CLAUDE_SKILL_DIR}/../../shared/scenario-checklist.md
CONSTRAINTS: This task only. No drive-by refactors or reformatting. No new dependencies unless approved at Gate 1. No destructive git commands (reset --hard, checkout --, clean, stash drop, force push). Output is working code plus tests, committed with approval, plus the Step 9 report.

Live state (verify these render; if they appear as literal text, run the git commands yourself):
- Branch: !`git branch --show-current 2>/dev/null || echo "not a git repository"`
- Last commit: !`git log --oneline -1 2>/dev/null || echo "not a git repository"`
- Uncommitted: !`git status --short 2>/dev/null || echo "not a git repository"`

## Step 0 - Preconditions
- If $ARGUMENTS is empty, ask for the task and stop.
- If there are uncommitted changes, list them and ask: proceed (they will never be staged), stash, or stop.
- If on the default branch (main/master/develop), ask whether to create a branch and suggest a name.
- Find commands: CLAUDE.md (Commands + Testing) first, then package scripts / Makefile / CI config. If test command is still unknown, ask. Never substitute a guess.
- If REPO_ANALYSIS.md exists and its recorded commit matches or is close to HEAD, use it for recon. Otherwise ignore it.

## Step 1 - Recon (read-only)
1. Locate the code involved. Read at least 2 sibling implementations and their tests.
2. Grep for callers of everything you may change.
3. Identify layering/import direction, naming and placement patterns, error-handling and logging style, public contracts touched.
4. `git log -5 -- <area>`: recent changes and any earlier Task Briefs in commit bodies.

## Step 2 - Baseline
Run the full test command (plus lint/typecheck if they exist) BEFORE editing. Record pass/fail counts and the names of failing tests: these are pre-existing failures and are NOT yours to fix. If any overlap the area you will change, tell the user. If the suite is very slow, run the area subset and say so.

## Step 3 - Task Brief + Test Plan + Scaffold (GATE 1)
Produce, without writing any file:
1. Task Brief: goal, in/out of scope (at least 3 out), ACs (AC-1..n, "The system shall ..."), assumptions, blocking questions. If $ARGUMENTS already contains ACs from /spec-interview, reuse them.
2. Test Plan: apply the checklist. One row per category: APPLICABLE (scenarios -> test name -> level -> file) or N/A (reason grounded in the code).
3. File tree: files to create/modify, each marked new/modified and "mirrors <existing file>".
4. Anything beyond the ACs marked SPECULATIVE: ask keep or cut.
Ask blocking questions (batch of at most 3). List non-blocking ones as assumptions.
STOP. Wait for explicit approval. Only then create the files.

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
  - No AC, task or ticket ids and no wording relative to this change ("as today", "parity", "new", "rewrites the old test"). If CLAUDE.md declares a requirement-citation convention, follow it exactly (one line max). Otherwise trace via test names and the commit body.
  - Every claim must match the code as written: the real caller, mock or behavior, not the intended one.
- If unsure about a design decision: STOP and ask. Never assume.

## Step 6 - Self-review (read your own diff)
Run `git diff` and check:
- Only planned files changed; every hunk maps to an AC; no unrelated formatting or renames
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

## Step 8 - Commit (GATE 2, requires approval)
Stage only the files this task created or modified, by explicit path. Never `git add -A`. Never stage files listed as pre-existing uncommitted changes. Do not commit yet.
Draft the message:
```
[imperative title, max 72 chars]

[1-2 sentences: what and why]

Acceptance criteria:
- AC-1 ...
- AC-2 ...
Tests: [files/names added]. Baseline: [N pre-existing failures unchanged | none]
Not covered: [known gaps, and N/A categories worth knowing]
```
Show it and ask for explicit approval.
- Declined: do not commit; report "skipped (user declined)".
- Approved: commit via HEREDOC:
```
git commit -m "$(cat <<'EOF'
[title]

[body]
EOF
)"
```

## Step 9 - Report and stop
Print exactly:
```
Task complete.
Files: created [...] / modified [...]
AC -> tests: AC-1 -> [test names] ...
Scenario categories: APPLICABLE n / N/A n  (list each N/A with its reason)
Baseline vs now: before [pass/fail] -> after [pass/fail]; pre-existing failures untouched: [names]
Can-fail check: [results]
Assumptions / known gaps: [...]
Commit: [hash | skipped (user declined)]
```
Do NOT start another task. Suggest: run /clear, then /validate-phase <hash> for an independent review.
