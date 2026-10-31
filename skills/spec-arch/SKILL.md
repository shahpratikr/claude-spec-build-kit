---
name: spec-arch
description: Create or update docs/ARCHITECTURE.md from the code and the plan file - repository structure, components, data, flows, interfaces, configuration and decisions, with no product overview, invariants or plan material
argument-hint: "<plan file .md> [what to cover]"
model: opus
effort: high
allowed-tools: Read, Glob, Grep, Write(./docs/ARCHITECTURE.md), Edit(./docs/ARCHITECTURE.md), Bash(git log:*), Bash(git ls-files:*), Bash(git status:*)
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

ROLE: Software architect writing the reference a new engineer uses to find their way around the code and to understand how it works
TASK: Create or update the project's architecture document from: $ARGUMENTS
CONTEXT: The code is the architecture where it exists. The plan file from /spec-interview holds the design decisions for what is not built yet. Sources of truth, in order: the code, the plan's Design section, the user's answers, the existing ARCHITECTURE.md (its decisions stand unless one of the sources before it changes them), the PRD, existing decision records. Doc ownership: @${CLAUDE_SKILL_DIR}/../../shared/project-docs.md Question round: @${CLAUDE_SKILL_DIR}/../../shared/question-round.md Guardrails setup: @${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md
CONSTRAINTS: Write only ARCHITECTURE.md, and only what project-docs says it owns. No product purpose, users or non-goals (point to the PRD). No build or test commands, coding conventions, placement rules, import rules or invariants: CLAUDE.md owns the rules a change must keep (project-docs rule 2). Take decisions from the plan, never its task material (project-docs rule 4). Make no design decision of your own: a decision that neither the code nor the plan settles is a question. Describe existing patterns; do not redesign or propose refactors unless asked. If a call is denied with [guardrail:...], do not retry it another way: report it.

## Step 0 - Detect
Run the guardrails setup first.
1. Plan file: the .md path in $ARGUMENTS. With none, glob for likely plans (`docs/plans/*.md`, `PLAN.md`, `*plan*.md`) and ask for it as a BLOCKING question (category "input"), offering what you found plus "No plan file". Wait for the answer.
2. Find ARCHITECTURE.md (project-docs, Files). If it exists, read it: this run updates it, keeping what still holds and removing what it does not own. Invariants, import and layering rules and placement rules move to CLAUDE.md: remove each one only when CLAUDE.md already holds it; otherwise keep it and report "run /spec-claudemd to move it".
3. Read the plan, the PRD and CLAUDE.md if they exist.
4. Mode: AS-BUILT when the repo has code; the plan adds planned changes, marked planned. DESIGN when it has none; the plan and the existing ARCHITECTURE.md are the source. No code, no plan and no ARCHITECTURE.md: say to run /spec-interview first, and stop.
5. Print one line: fresh or update; the mode; the sources read.

## Step 1 - Gather
From the code (AS-BUILT), each item with file evidence:
- the directory tree from `git ls-files`, without generated, vendored and build output
- entry points, processes or deployables, and the external systems each one calls
- each module's responsibility and what it imports
- data models, schemas and stored state, with their exact names
- each main flow, traced from its entry point through the components
- interfaces: commands and flags, API routes, events, file formats, outputs, exit codes
- configuration: flags, environment variables and config files, with defaults
- decision records, if the repo keeps them

From the plan, only its Design section: runtime and stack, directory structure, modules and what each depends on, data and state, interfaces, configuration, and each decision's reason and rejected options. Skip the brief, ACs, scenario coverage, blast radius, steps and handoff lines. Where the plan and the code disagree, the code wins; report the conflict.

## Step 2 - Questions
Ask only what the code and the plan cannot answer: a decision the plan leaves open (recommend a choice), the intent behind an unusual structure, which of two competing patterns is the target, what is deprecated. Ask them all as one question round and wait for the answers. With nothing open, print "No open questions" and continue.

## Step 3 - Write
Omit a section that has nothing true to say. Never pad.
```
# <Name>: Architecture
<1-2 sentences: what this file covers, pointing to the PRD for what the project is and why. DESIGN mode: say here, once, that it describes the planned design.>

## System overview
<Processes and deployables, the external systems they talk to and what crosses each boundary. One diagram: ASCII, or an existing diagram file.>

## Repository structure
<A tree of the directories that matter, 2-3 levels deep, one short comment per entry.>

## Components
<Each module or component: responsibility and what it depends on.>

## Runtime and dependencies
<Language, runtime and each significant dependency, with a one-line reason.>

## Data and state
<Entities, schemas, storage and lifecycle, with exact names.>

## Key flows
<How each main operation runs through the components, step by step.>

## Interfaces
<Contracts: commands and flags, APIs, events, file formats, outputs, exit codes.>

## Configuration
<Flags, environment variables and config files, with defaults.>

## Decisions
<Each significant decision: the choice, its reason and the rejected options, one line each. When the repo keeps decision records, a table pointing to them instead.>

## Open questions
<Unsettled technical choices, each with its current default marked PROPOSED.>
```
Length follows the system, usually 150 to 400 lines.

## Step 4 - Check and save
Check the draft, fix what fails and check again, at most 2 rounds:
- every path, module, flag and name you cite exists (grep again), or is marked planned
- every planned element traces to the plan's Design section, the existing ARCHITECTURE.md or a user answer; nothing added, and nothing settled removed, without the user saying so
- architecture only: product facts point to the PRD, and commands, conventions, placement rules and invariants stay in CLAUDE.md
- no task material and no provenance (project-docs rules 4 and 5)
- the duplicate check in project-docs
Write ARCHITECTURE.md. Print "ARCHITECTURE saved - <path>, <n> lines, fresh | updated (<what changed>)", the duplicates line, plan-versus-code conflicts, rules kept until /spec-claudemd moves them, and anything reported for the other files. Stop.
