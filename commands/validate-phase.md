---
description: Validate a completed phase against spec, conventions, and tests, at any project stage
argument-hint: "<phase-num>"
model: haiku
allowed-tools: Agent, Bash(git diff:*), Bash(git log:*)
---

ROLE: QA orchestrator — spawn agents, collect results, report only
TASK: Validate Phase $ARGUMENTS against spec, conventions, and tests
CONTEXT: This command may run right after a phase is committed, or later against an older phase, on any project. It does not assume build-phase.md's commit message format. Validation checks three independent concerns in parallel: spec compliance, convention adherence, and test passage.
OUTPUT FORMAT: Structured report using the exact template below
STOP CONDITIONS: Do not read files yourself. Do not fix anything. Report only. Do not start Phase $ARGUMENTS+1.

## Step 0 — Preconditions
- If docs/PRD.md is missing → stop and tell the user to run /spec-interview first.
- If docs/ARCHITECTURE.md is missing → stop and tell the user to run /spec-arch first.
- If docs/ARCHITECTURE.md has no section numbered $ARGUMENTS → stop and tell the user the valid phase range, and ask which they meant.
- If CLAUDE.md is missing, proceed but note in the final report that convention checking ran without a CLAUDE.md and its results may be unreliable.

## Step 1 — Locate the phase's commit range
```
Recent commits:   !git log --oneline -20
```
Find the commit(s) belonging to Phase $ARGUMENTS. Try, in order:
1. A commit message whose title matches the phase's name/title as given in docs/ARCHITECTURE.md's Phase $ARGUMENTS section.
2. A commit message starting with "Phase $ARGUMENTS" or "Phase $ARGUMENTS:" (older commit convention).
3. If neither is found, list the recent commits to the user and ask them to identify which commit(s) implement Phase $ARGUMENTS.

If the phase spans multiple commits, diff from the commit immediately before the first matching commit through HEAD. If exactly one commit matches, diff that commit against its parent. Then run:
```
Changed files:    !git diff --name-only <range-determined-above>
```

Collect the changed files list into a variable — pass it explicitly to each agent rather than re-running the git command inside agent prompts.

## Step 2 — Spawn these 3 agents in parallel

### Agent 1 — spec-validator
```
phase_number: $ARGUMENTS
changed_files: [list from git diff above]
instruction: >
  ROLE: QA engineer verifying spec compliance
  TASK: Check whether Phase $ARGUMENTS acceptance criteria from docs/PRD.md are satisfied by the changed files
  CONTEXT: Changed files are listed above. Read each file and map its implementation to the corresponding PRD acceptance criteria for Phase $ARGUMENTS.
  OUTPUT FORMAT: Markdown table — criterion | YES/PARTIAL/NO | one-line evidence
  STOP CONDITIONS: Do not check conventions or run tests. Spec compliance only.
```

### Agent 2 — convention-checker
```
changed_files: [list from git diff above]
instruction: >
  ROLE: Senior engineer enforcing code conventions
  TASK: Check whether all changed files comply with the conventions in CLAUDE.md
  CONTEXT: Changed files are listed above. If CLAUDE.md exists, read it for the full convention list, then check each changed file. If CLAUDE.md does not exist, report that no conventions file was found and skip this check.
  OUTPUT FORMAT: List violations as "file:line — rule violated — fix". If no violations, output "no violations". If no CLAUDE.md, output "no CLAUDE.md found — skipped".
  STOP CONDITIONS: Do not check spec compliance or run tests. Conventions only.
```

### Agent 3 — test-reporter
```
phase_number: $ARGUMENTS
instruction: >
  ROLE: QA engineer running the test suite
  TASK: Run the project test suite and return a structured pass/fail report for Phase $ARGUMENTS
  CONTEXT: Read CLAUDE.md for the exact test command, if CLAUDE.md exists. If it doesn't, infer the standard test command for the project's stack (e.g. from package manifests) or ask the user for it.
  OUTPUT FORMAT: Total tests | Passed | Failed | list of failing test names (if any)
  STOP CONDITIONS: Run tests only. Do not fix failures.
```

Wait for ALL 3 agents to complete before printing anything.

## Output format
Print this exact structure — no extra commentary:

```
================================================
PHASE $ARGUMENTS VALIDATION REPORT
================================================

SPEC COMPLIANCE
---------------
[paste spec-validator output verbatim]

CONVENTION CHECK
----------------
[paste convention-checker output verbatim]

TEST RESULTS
------------
[paste test-reporter output verbatim]

================================================
OVERALL: [PASS / FAIL / NEEDS REVIEW]
  PASS         = all criteria YES, no violations, tests green
  NEEDS REVIEW = any PARTIAL or minor violations, tests green
  FAIL         = any NO criteria, tests red, or blocking violations
================================================

NEXT STEP: [one sentence — "safe to start Phase N+1" or "fix [specific items] before proceeding"]
================================================
```

Stop here. Do not start Phase $ARGUMENTS+1.
