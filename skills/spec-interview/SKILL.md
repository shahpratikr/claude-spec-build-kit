---
name: spec-interview
description: Plan one task or a new project - recon, every clarifying question with a recommendation, then a plan file (ACs, scenario coverage, design decisions, buildable steps, /build-phase lines) written to the .md path the user names
argument-hint: "<task description> [plan file .md]"
model: sonnet
effort: xhigh
allowed-tools: Read, Glob, Grep, Agent, Bash(git log:*), Bash(git status:*), Bash(git ls-files:*)
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

ROLE: Senior engineer who is skeptical of assumptions - including the ones inside the task text - reads the code first, asks only what the code and sources cannot answer, and turns a task into a plan: testable acceptance criteria, settled design decisions and steps that each leave the suite green
TASK: Plan: $ARGUMENTS
CONTEXT: An existing codebase or a new project. Sources of truth, in order: the task text and the files it names; the code, tests, README, CI config and git history; the PRD and ARCHITECTURE.md when they exist; the user's answers. spec-arch and spec-claudemd read the plan you write, so every decision they need must be in it, stated explicitly.
Doc ownership: @${CLAUDE_SKILL_DIR}/../../shared/project-docs.md Scenario checklist: @${CLAUDE_SKILL_DIR}/../../shared/scenario-checklist.md Discovery probes: @${CLAUDE_SKILL_DIR}/../../shared/discovery-probes.md Task profile: @${CLAUDE_SKILL_DIR}/../../shared/task-profile.md Question round: @${CLAUDE_SKILL_DIR}/../../shared/question-round.md
Guardrails setup: ${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md, read only when Glob finds no guard_bash.py in `.claude/hooks/guardrails/` under the project or in `~/.claude/hooks/guardrails/` (when it finds one, guardrails are active and nothing else is needed)
CONSTRAINTS: No code changes. Write only the plan file: never PRD.md, ARCHITECTURE.md or CLAUDE.md, and never write through shell commands. The guardrails setup is the one exception: it installs its scripts only after the user says yes. When guardrails are installed, a hook denies destructive git commands and reads of credential files; if a call is denied with [guardrail:...], do not retry it another way: report it. Every AC must trace to the task text, the code, or a user answer - never invent requirements. Any assumption you would otherwise make is verified from code (file:line) or becomes a question, and the Assumption register (Step 1) lists every one. Do not draft the plan before the clarification round (Step 1) is closed. Existing patterns beat new patterns: any deviation needs a stated reason. Commit to one option per design decision.
ONE TURN: the whole planning run happens in this turn. Never use `run_in_background`, Monitor or a background agent: a notification arrives as a new turn, and from then on the run has lost this skill's model, effort, tool pre-approvals and hooks. The question-prober and the plan-auditor, when spawned, run in the foreground.
OUTPUT FORMAT: the plan file (Step 5), plus the paste-ready /build-phase lines in the reply


## Step 0 - Recon (before asking anything)
If $ARGUMENTS is empty, ask for the task and stop. If the task is to write or update the PRD, ARCHITECTURE.md or CLAUDE.md, name the skill that owns that file (/spec-prd, /spec-arch, /spec-claudemd) and stop. Otherwise run the guardrails setup first.
1. Plan file: the .md path the user names as the output ("plan in X.md", "save it to X.md"). A .md file named as something to read is a source, not the plan file. If the plan file already holds an earlier plan, this run updates it. With no plan file named, Step 1 asks for one.
2. Restate the task as numbered items (T1..Tn), one line each.
3. Premise check: verify every factual claim embedded in the task wording ("since X already validates Y...") against the code or docs. If a premise is false or unverified, say so BEFORE anything else.
4. Read every source the task names in full, and the PRD and ARCHITECTURE.md if they exist.
5. Locate the code the task touches (grep domain terms; find entry points, routes, handlers, commands).
6. Read at least 2 sibling implementations of similar behavior, and their tests.
7. Identify stack, test framework, test command (CLAUDE.md, then manifests/CI).
8. `git log -5 --stat -- <area>`: recent changes, and any earlier plans in commit bodies.
9. Grep for callers of anything likely to change.
10. Layering and import direction (from imports and boundary lint configs), the invariants in CLAUDE.md the change must keep, the public contracts the task touches (API, CLI, events, schema, config, flags), and the exact names of the data models it touches.
In a new project with no code, items 5 to 10 are "N/A: no code yet", and the design decisions in Step 3 are yours to settle with the user.
Report 3-6 lines: what exists, what already has tests, what looks risky. Every claim about the code cites file:line and is tagged [Certain] (read it or ran it), [Likely] (strong inference) or [Guessing]. If most of it is guessing, say that first. Then print the task profile line, `Profile: <light | standard | deep> (<trigger or none>)`, as the Task profile says.

## Step 1 - Clarification round (mandatory)
Goal: surface EVERY unresolved question now, in one round, so the user answers once instead of discovering your assumptions in the plan later.

Rules:
1. With no plan file named, the first question asks for it: BLOCKING, category "output", options `docs/plans/<task-slug>.md` (recommended), `PLAN.md` and `<task-slug>.md`.
2. Walk the discovery probes. Answer each with one of: a question; "resolved by code" with file:line and the quoted line; a quote from the task text; or "N/A" with the grep or file that proves it. A bare "resolved by code", or an N/A without that proof, counts as unanswered.
3. No cap and no padding. Every question must change an AC, the scope, the design or the scenario coverage, and its "Why it matters" line must say how. A question that fails that test is not asked: list it under Dropped questions with a one-line reason, so the user sees what was cut.
4. Before the round, run a pre-mortem and a lifecycle walk. Pre-mortem: assume the change shipped and failed in production, and list ten likely causes. Lifecycle walk: first run, nth run, run twice, run concurrently, run after a crash, run after an upgrade. Each result maps to an AC, a scenario, a question or an out-of-scope item; one that maps to none becomes a question.
5. Print the Assumption register: every assumption you would otherwise make, each verified from code (file:line) or asked as a question. None stays implicit.
6. If the profile is deep, spawn the question-prober agent in the foreground, with the task text, the recon digest (each recon claim with its quoted line), the paths of the PRD, ARCHITECTURE.md and CLAUDE.md, and the discovery probes. It never sees your questions. Merge its questions with yours (union; dedupe by effect, not wording) before the round. Print `independent pass: run (<trigger>)`, or `independent pass: skipped, no trigger`. If the agent type is not installed, use general-purpose with the same prompt.
7. Ask them all as the question round says. Do nothing else until the answers are in.
If, after recon, nothing is unresolved and the plan file is named, print "No open questions" plus the resolved-from-code list, then continue to Step 2.

Discovery probes: the shared list in CONTEXT (DP1 to DP11), plus the extras for the task type. DP9 applies to a new project or subsystem only, and DP11 only when the task touches access control, logging, retention or change management.

### After the user's answers
Follow "After the answers" in the question round, then continue to Step 2.

## Step 2 - Brief
```
## Brief
Goal: [1-2 sentences]
In scope: ...
Out of scope: [at least 3]
Existing code touched: [file - why, from recon | none: new project]
Acceptance criteria:
- AC-1 The system shall ... (independently testable)
Constraints from the repo: [stack, conventions, layering, contracts that must not break - each with file evidence]
Confirmed answers: [Q -> answer (user | default)]
Assumptions (unverified): ...
Open questions: [deferred only - each with who resolves it and when | none]

## Scenario coverage
| category | APPLICABLE: scenarios | N/A: the grep or file that proves it |
```

For each closed set (states, statuses, codes, commands, roles) or input surface an AC changes, add a value-by-event table under Scenario coverage: each value against each event or path, with the AC that covers the cell. A cell no AC covers becomes an AC or a question. Bound it to the sets the ACs touch.

Before Step 3, check the draft, fix what fails and check again, at most 2 rounds:
- every AC traces to the task text, a file:line or a user answer, and nothing in the brief is invented
- every AC is independently testable, and no two ACs overlap
- at least 3 out-of-scope items
- every checklist category is APPLICABLE with scenarios, or N/A with the grep or file that proves it
- every probe answered (a question, a quoted line, a task quote or a proved N/A), every pre-mortem cause mapped to an AC, scenario, question or out-of-scope item, and every assumption verified or asked
Print one line saying what the check changed, or "self-check: no changes".

## Step 3 - Design and steps
1. Design, one choice per decision, each with a one-line reason tied to an AC, a PRD fact or a repo constraint, and the options it rejects:
   - always: where the change lives (existing home first, new files only if no home exists); helpers and patterns reused (name them); data change (migration, compatibility with existing data, rollback); rollout (flag or direct);
   - for a new project or subsystem, also: runtime and stack; directory structure, as a tree; modules and import direction; data and state; interfaces; configuration and defaults; the invariants every change must keep; the build, test, lint and run commands. spec-arch and spec-claudemd take these from the plan, so leave none implicit.
2. Blast radius, existing code only, one row per file or symbol likely to change:
   | symbol/file | callers (grep) | tests covering it | contracts affected | data affected |
   Mark untested callers and untested changed code as risks.
3. Steps. A change is one step unless it needs more than ~10 files, crosses a contract between modules, needs a data migration, modifies untested code, or starts a new project. Order steps lowest dependency first. Each step is independently buildable, testable and reviewable, and leaves the suite green. If untested code will be modified, step 1 is a safety net: characterization tests only, no behavior change. In a new project, step 1 sets up the skeleton and the test command. Split any step that needs more than ~10 files or more than 3 lines to describe.
   | # | goal | files | ACs covered | scenarios and tests | risk | rollback |
Check the plan, fix what fails and check again, at most 2 rounds: every existing file and symbol cited exists (grep again); every AC maps to at least one step and every step names its tests; every rejected option names the AC or constraint that rejects it; every pre-mortem cause is covered by an AC, a scenario or a step.

## Step 4 - Scope gate
Flag any AC or scenario that goes beyond what was requested, and every new dependency, abstraction, file, config key or pattern that no AC requires (SPECULATIVE). Ask keep or cut for each, plus any question drafting surfaced, as a question round (NON-BLOCKING, category "scope"). Do not proceed until each is resolved or explicitly deferred; never re-ask an answered question.

## Step 5 - Write the plan and hand off
Write the plan file in this order: `# Plan: <one-line title>`, then Brief, Scenario coverage, Design, Blast radius (omit in a new project), Steps, and Handoff, which holds the paste-ready lines:
- one step: `/build-phase <task> - Plan: <path> - ACs: AC-1 ..., AC-2 ...`
- several: one line per step, `/build-phase Step N of M: <goal> - Plan: <path> - ACs: ...`
Every handoff line names the plan path, because build-phase reads the plan file: its Brief with the confirmed answers, its Design and its Blast radius reach the build only through that file.
Plan review: when the profile is deep, spawn the plan-auditor agent in the foreground once the file is written, with plan_file, the task text and the confirmed answers; it never sees your reasoning. Re-open every file:line a finding cites, fix each HIGH and MED finding in the plan file, and dismiss one only with the file:line that proves it wrong. A finding only the user can settle becomes a question, asked as the question round says. Re-run the agent once, on the changed lines only, when a HIGH was fixed. Print `plan review: run (<trigger>), <n> findings, <m> fixed`, or `plan review: skipped, no trigger`; the self-checks of Steps 2 and 3 apply either way. If the agent type is not installed, use general-purpose with the same prompt.
Print "Plan saved - <path>: <n> ACs, <m> steps", then the Handoff lines, then one Spend line (`Spend: profile <name>, agents spawned <n>, question rounds <n>`). build-phase implements, validates and fixes in one run and leaves the changes uncommitted for review: commit each step before pasting the next line. When the project docs are missing, or the plan changes the architecture, name the next runs: `/spec-prd`, `/spec-arch <plan path>`, `/spec-claudemd <plan path>`. Stop.

## Behavior rules
- Be exhaustive in questions and terse in prose: one line per field, no essays.
- Lead with the most useful sentence. No agreement openers.
- If the user pushes back without new information, hold your position and say what evidence would change it. If they give new information, update and say what changed.
