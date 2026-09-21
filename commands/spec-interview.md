---
description: Clarify one task in an existing codebase and produce a Task Brief (ACs + scenario coverage)
argument-hint: "<task description>"
model: opus
allowed-tools: Read, Glob, Grep, Bash(git log:*), Bash(git status:*), Bash(git ls-files:*)
---

ROLE: Senior engineer who turns a vague task into testable acceptance criteria by reading the code first and asking only what the code cannot answer
TASK: Produce a Task Brief for: $ARGUMENTS
CONTEXT: Existing codebase. No PRD or architecture doc is assumed. Sources of truth, in order: the task text; the code, tests, README, CI config and git history; the user's answers. Scenario checklist: @.claude/shared/scenario-checklist.md
CONSTRAINTS: No code changes. Write no files unless the user asks. Every AC must trace to the task text, the code, or a user answer - never invent requirements. Ask; do not assume.
OUTPUT FORMAT: Task Brief (template in Step 2) plus one paste-ready handoff line


## Step 0 - Recon (before asking anything)
If $ARGUMENTS is empty, ask for the task and stop.
1. Locate the code the task touches (grep domain terms; find entry points, routes, handlers, commands).
2. Read at least 2 sibling implementations of similar behavior, and their tests.
3. Identify stack, test framework, test command (CLAUDE.md, then manifests/CI).
4. `git log -5 --stat -- <area>`: recent changes, and any earlier Task Briefs in commit bodies.
5. Grep for callers of anything likely to change.
Report 3-6 lines: what exists, what already has tests, what looks risky.

## Step 1 - Questions (one at a time; wait for each answer)
Ask only what recon could not answer. Maximum 5. For every question, give your recommended default and say what depends on the answer. Priority order:
1. Behavior on invalid input and on failure of dependencies
2. Scope edges - what must NOT change
3. Compatibility - public API, stored data, consumers, config
4. Non-functional - performance, security/permissions
5. Rollout - feature flag, migration, ordering
If recon left nothing ambiguous, say so and ask zero questions.

## Step 2 - Draft the Task Brief
```
TASK BRIEF - [one-line title]
Goal: [1-2 sentences]
In scope: ...
Out of scope: [at least 3]
Existing code touched: [file - why, from recon]
Acceptance criteria:
  AC-1  The system shall ... (independently testable)
Constraints from the repo: [stack, conventions, layering, contracts that must not break - each with file evidence]
Scenario coverage (one row per checklist category):
  [category] | APPLICABLE: scenarios  -or-  N/A: reason grounded in the code
Assumptions (unverified): ...
Open questions: ...
```

## Step 3 - Scope gate
Flag any AC or scenario that goes beyond what was requested. Ask keep or cut for each. Surface every open question; do not proceed until each is resolved or explicitly deferred.

## Step 4 - Handoff
Print the final brief, then one line the user can paste:
`/build-phase <task> - ACs: AC-1 ..., AC-2 ...`
Nothing was saved; the user can say "save it to <path>". Stop.
