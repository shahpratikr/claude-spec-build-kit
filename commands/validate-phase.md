---
description: Independently validate a committed change against its intent, scenario coverage, conventions and tests
argument-hint: "[commit or range, default HEAD] [optional task description]"
model: opus
allowed-tools: Agent, Bash(git diff:*), Bash(git log:*), Bash(git show:*), Bash(git rev-parse:*)
---

ROLE: QA orchestrator - spawn independent reviewers, collect results, report only
TASK: Validate: $ARGUMENTS
CONTEXT: No PRD is assumed. Intended behavior comes from, in order: (1) the "Acceptance criteria" list in the commit body, (2) the task description in the arguments, (3) the commit title/body prose, (4) the user. NEVER derive intended behavior from the diff itself - a validator that infers the spec from the implementation will approve the implementation. Reviewers receive intent and file lists, not the author's reasoning.
OUTPUT FORMAT: Structured report using the template below
STOP CONDITIONS: Do not fix anything. Do not read source files yourself. Do not start other work.

## Step 0 - Resolve what to validate
1. If the first token of $ARGUMENTS resolves with `git rev-parse --verify`, that is the commit or range; the rest is the task description. Otherwise use HEAD and treat all of $ARGUMENTS as the task description.
2. A single commit is diffed against its parent. If HEAD is a merge or the range is large, show `git log --oneline -20` and ask which commits to validate.
3. Run `git show --stat --format=%B <commit>` to read the message, and `git diff --name-only <parent>..<commit>` for changed files. Split them into production files and test files (by CLAUDE.md, else by common patterns: test/, tests/, __tests__, *_test.*, *.spec.*).
4. Extract intent using the priority order above. If none is available, STOP and ask the user for 2-5 lines of intended behavior. Do not proceed on a guess.
5. If CLAUDE.md is missing, note it; the convention agent will fall back to sibling-code patterns. If the working tree has uncommitted changes, note that validation covers the commit only.

## Step 1 - Spawn these 4 agents in parallel
Give each agent a self-contained prompt with: the intent (ACs verbatim), the commit/range, and the changed-file lists (production vs test). Subagents do not see this conversation.

### Agent 1 - criteria-auditor
ROLE: QA engineer verifying acceptance criteria
TASK: For each AC find (a) the implementing code (file:line) and (b) the test that would FAIL if that code broke (file:test name). YES = code plus a meaningful test. PARTIAL = code without a test, or a test that does not really assert the criterion. NO = missing. Also list any behavior in the diff that no AC asks for (scope creep).
OUTPUT: table - AC | YES/PARTIAL/NO | code evidence | test evidence; then "unrequested changes".

### Agent 2 - gap-hunter (adversarial)
ROLE: Skeptical reviewer who assumes the author missed something
TASK: Read `.claude/shared/scenario-checklist.md`. Read the production diff and the callers of changed code FIRST. For each checklist category, list the scenarios that ought to be tested. Then read the tests and mark each scenario covered or uncovered. Also scan the production diff for defects: off-by-one, null handling, swallowed errors, missing await, races, resource leaks, unsafe SQL/HTML/paths, authorization gaps, secrets in logs. For any category the author marked N/A, say whether the reason holds.
OUTPUT: only UNCOVERED items, max 15, ranked: category | scenario | concrete failure if untested | HIGH/MED/LOW | one-line suggested test. Then "N/A challenges".

### Agent 3 - convention-checker
ROLE: Senior engineer enforcing conventions
TASK: Check the changed files against CLAUDE.md. If CLAUDE.md is missing, compare against 2-3 sibling files instead. Check naming, file placement, layering (new imports crossing layers), error-handling and logging patterns, style, contract changes (public API/schema/config) without migration or docs, and unrelated changes.
OUTPUT: "file:line - rule violated - fix" per violation, or "no violations". State whether CLAUDE.md was used.

### Agent 4 - test-reporter
ROLE: QA engineer running the checks
TASK: Detect the test command (CLAUDE.md, then manifests/CI). Run tests, lint and typecheck. For each failure, decide whether it is pre-existing: run only that test in a temporary `git worktree` of the parent commit (never modify the main working tree; remove the worktree afterward). Re-run new/changed tests 3 times to detect flakiness. If coverage tooling exists, report coverage of changed lines. Anything that could not run (needs a DB or service, missing tool) is reported as NOT RUN with the reason - never as a pass.
OUTPUT: Total | Passed | Failed | Skipped | NOT RUN; failing test names marked new or pre-existing; flaky tests; uncovered changed lines.

Wait for ALL 4 agents to complete before printing anything.

## Output format
Print this exact structure - no extra commentary:

```
================================================
VALIDATION REPORT - [hash or range] - [commit title]
Intent source: [commit AC list | task argument | commit message | user-supplied]
================================================

ACCEPTANCE CRITERIA
-------------------
[agent 1 output verbatim]

UNCOVERED SCENARIOS
-------------------
[agent 2 output verbatim]

CONVENTIONS AND SCOPE
---------------------
[agent 3 output verbatim]

TEST RESULTS
------------
[agent 4 output verbatim]

NOT VERIFIED
------------
[anything not run or not checkable: integration tests needing services, manual UI paths, etc.]

================================================
OVERALL: [PASS / FAIL / NEEDS REVIEW]
  PASS         = every AC is YES, no HIGH gaps, no violations, suite green with no new failures, nothing critical NOT RUN
  NEEDS REVIEW = any PARTIAL, any MED gap, minor violations, or anything critical NOT RUN
  FAIL         = any NO, any HIGH gap, new failing tests, or a blocking violation
================================================
NEXT STEP: [one sentence - "safe to proceed" or "fix [specific items] first"]
================================================
```
Stop here.
