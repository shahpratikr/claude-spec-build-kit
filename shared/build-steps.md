# Build Steps

Used by build-task and followup implement. It is the one build flow: recon, brief, tests first, implement, verify, validate, report.

In followup implement, TASK is the follow-up message verbatim, the I-items are the ACs (written "The system shall ..."),
and a question the follow-up's clarification round already answered is not asked again.
In build-task, TASK is the task text or the `/plan-task` handoff line. Files named below without a folder (scenario-checklist.md, validation-loop.md, verification-profiles.md, question-round.md,
task-profile.md) sit in this file's folder.

QUESTIONS: ask only BLOCKING questions: ones the task, code and tests cannot answer, where a wrong guess would change an AC or a public contract.
Ask them as the question round says, so the build continues in this turn. Every other open point becomes an assumption with your recommended default, listed in the report.

## Step 0 - Preconditions and snapshot
- If TASK is empty, ask for it and stop.
- If the task is to write or update the PRD, ARCHITECTURE.md or CLAUDE.md, name the skill that owns that file (/docs-prd, /docs-arch, /docs-claudemd) and stop.
- First action, before anything else: find the repo.
  - Use the git toplevel of the first path the task names that sits in a repo (the plan file, a file or a folder): `git -C <dir of that path> rev-parse --show-toplevel`.
  - If the task names no path, use the toplevel of the current folder.
  - If neither finds a repo, ask for it as a BLOCKING question.
- Then read `<repo>/CLAUDE.md`. Skip the Read when it is already in context as nested memory. When the repo has no CLAUDE.md, say nothing about it and go on.
- Run every git command as `git -C <repo> ...` and every test, lint and build command from `<repo>`.
- Run `git -C <repo> branch --show-current`, `git -C <repo> log --oneline -1` and `git -C <repo> status --short`, unless the repo is the current folder and the live state above already shows them.
- If TASK names a plan file (a `/plan-task` handoff carries `Plan: <path>`), read it by section:
  - Handoff line: `Step N of M: <goal> - Plan: <path> - ACs: ... - Rules: ...`. The `- Rules:` part is optional, and so is a line with no step (a one-step plan).
  - Grep the plan for `^#{2,3} ` to list its headings and line numbers.
  - New format (it has `## Summary`): Read Summary, Design and the named step's block (its `### Step N` heading up to the next heading) with offset and limit. Never Read the whole plan.
  - Old format (no `## Summary`): Read Brief, Design, Blast radius and the named step's row, as before.
  - Those decisions bind the build.
- Snapshot the starting state so the change can be validated without a commit. Run `git -C <repo> stash create`: it prints a hash that records the tracked files as they are now,
  without touching the working tree or index.
  BASE is that hash, or the output of `git -C <repo> rev-parse HEAD` when it prints nothing. Record BASE and the output of `git -C <repo> status --porcelain --untracked-files=all`.
- Find commands: CLAUDE.md (Commands + Testing) first, then package scripts / Makefile / CI config. An unknown test command is a BLOCKING question. Never substitute a guess.
  When CLAUDE.md and CI name no test command, read verification-profiles.md and ask the question with a recommended option from its table.

## Step 1 - Recon (read-only)
1. Locate the code involved. Read the relevant functions of at least 2 sibling implementations and of their tests, not whole files (CONTEXT BUDGET).
2. Grep for callers of everything you may change. A new-format plan has no caller list,
   so this grep is the only one: a caller outside the step's files that the change could break is in scope or a risk in the brief.
3. Identify layering/import direction, naming and placement patterns, error-handling and logging style, public contracts touched. The invariants in CLAUDE.md bind the change.
4. `git -C <repo> log -5 -- <area>`: recent changes and any earlier Task Briefs in commit bodies.
5. If ARCHITECTURE.md exists, read the sections that cover the code you will change (CLAUDE.md, Project docs, says which).

## Step 2 - Baseline
Run the full test command (plus lint/typecheck if they exist) BEFORE editing. Record pass/fail counts and the names of failing tests: these are pre-existing failures and are NOT yours to fix.
If any overlap the area you will change, note it in the brief. If the suite is very slow, run the area subset and say so.

## Step 3 - Task Brief + Test Plan (no approval gate)
Write these in your reply before creating any file, so the user can follow the build:
1. Task Brief: goal, in/out of scope (at least 3 out), ACs (AC-1..n, "The system shall ..."), assumptions with the default you chose, blocking questions.
   - A plan step: copy the step's ACs verbatim from its table. Each R-id in its `Keeps:` line becomes `RULE-Rn The change shall keep: <rule> (enforced by <what>)` next to the ACs,
     so ac-auditor checks it.
   - An old-format plan: reuse the plan's ACs, confirmed answers and scenario coverage, and derive only what the plan lacks.
   - A new-format plan holds no confirmed answers: they sit in its ACs, rules and Design rows. Add to the brief only the answers of this run.
2. Test Plan: apply the checklist (scenario-checklist.md). One row per category: APPLICABLE (scenarios -> test name -> level -> file) or N/A (the grep or file that proves it).
3. File tree: files to create/modify, each marked new/modified and "mirrors <existing file>".
4. Anything beyond the ACs is SPECULATIVE: do not build it; list it in the report.
5. Variant table and pre-mortem, before any test:
   - For every input surface the change accepts or emits (strings, paths, formats, markup, CLI arguments, closed sets), list its syntactic variants from checklist category 2. Mark each one handled,
     with the test that will cover it, or N/A, with a reason grounded in the code.
   - Per AC, the two most likely ways the implementation could be wrong, each mapped to a test.
   The table is your reasoning: it feeds the test plan and the validation loop's fix plans, and never goes to a reviewer.
6. Size gate. Every review round re-reads the whole change, so one run builds at most about 10 production files.
   When the file tree has more, or the repository has no code yet and the task is more than its skeleton, ask one BLOCKING question (category "scope"), even though it is not about intent.
   The options are "Split it with /plan-task (Recommended)", described with the file count, and "Build it all in one run", described as taking hours of review.
   On split, print the count and a ready line, `/plan-task <task> docs/plans/<task-slug>.md`, and stop. A "Step N of M" task from a plan is gated the same way.
7. Profile: print `Profile: <light | standard | deep> (<trigger or none>)` as the Task profile says, and pass it to the validation loop (a deep profile adds ac-auditor at size tier S).
Ask any BLOCKING question now (see QUESTIONS), then continue. Do not wait for approval. A contract change the task and the answers leave unsettled is a BLOCKING question.

## Step 4 - Tests first
- Bug fix: write a failing repro test first. Run it. It must fail for the stated reason. Show the output.
- Feature: write tests for every AC and every APPLICABLE scenario. Run them. They must fail for the right reason (not an import or syntax error).
- Untested legacy code you will modify: first write characterization tests that pin current behavior. They must pass on the unmodified code.
Test rules: mirror the repo's layout, naming, fixtures and helpers. Put the AC id in the test name (or a JS describe() title), never in a docstring or comment.
Assert behavior, not implementation. No sleeps, no network, no order dependence. Do not mock what is cheap to run for real.
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
  - No AC, task or ticket ids and no wording relative to this change ("as before", "same as the old one", "parity", "new", "rewrites the old test").
    If CLAUDE.md declares a requirement-citation convention, follow it exactly (one line max). Otherwise trace via test names.
  - Every claim must match the code as written: the real caller, mock or behavior, not the intended one.
- A design decision that the brief, the code and the tests do not settle is a BLOCKING question. Never decide it silently.

## Step 6 - Self-review (read your own diff)
Run `git -C <repo> diff <BASE>` and read it, plus every new file (in parts when it is over about 300 lines), and check:
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
d. Can-fail pass: run it on every changed production line, as the validation loop defines it, once. Kill each survivor with a test, or record why it cannot change behavior.
   A task with no unit tests (infrastructure, scripts, configuration, docs) is not executable-verified: the can-fail pass is N/A with that reason,
   and each AC is verified by the output of a validation command that exits non-zero when the AC is violated (the rules in verification-profiles.md).
e. If coverage tooling exists, check changed lines. Test each uncovered line or justify it.
f. Failures caused by this change: fix now. Do not proceed with new failures.

## Step 8 - Validate, fix, re-validate
Run the validation loop (validation-loop.md) with TASK verbatim, the brief's ACs and RULE lines, the confirmed answers (the plan's, the brief's and this run's),
the sources (spec or source files the task or brief names, and the plan path),
BASE, the file lists, the commands, the Step 2 baseline and the Step 7 results as the facts, and the Step 3 variant table. Round 1 reuses the facts, the can-fail pass included.
The loop sets the size tier.
Before each fix round, write and check the loop's fix plan; no edit starts before its check line. Then fix every MUST-FIX finding by following Steps 4-6, and re-check as the loop says.
Round 3 runs only when the loop's triggers hold. After the last review, make no production edit.

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
  [imperative title, at most 72 characters, names what changed]

  [one paragraph of 1 to 3 lines, wrapped at 76: what it does, in plain words]
```
Commit message rules:
| Part     | Rule                                                                         |
| -------- | ---------------------------------------------------------------------------- |
| Title    | Imperative ("Add", "Fix", "Move"), at most 72 characters, names what changed |
| Body     | One paragraph of 1 to 3 lines, wrapped at 76: what it does, in plain words   |
| Never    | AC ids, test lists, baseline counts, file lists, bullets                     |
| Tiny fix | Title only, for a test-only or one-line change                               |

Example:
```
Add backup and export commands

finadvisor backup writes a consistent online-backup copy and finadvisor export
writes every table as JSON, both created 0600 in 0700 directories.
```
Do NOT start another task.
