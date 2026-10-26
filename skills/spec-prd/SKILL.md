---
name: spec-prd
description: Create or update docs/PRD.md - the project overview and context (purpose, users, scope, flow, constraints), with no requirements, plans or architecture
argument-hint: "[source files or notes about the project]"
model: opus
allowed-tools: Read, Glob, Grep, Write(./docs/PRD.md), Edit(./docs/PRD.md), Bash(git log:*), Bash(git ls-files:*), Bash(git status:*)
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

ROLE: Product engineer writing the overview a new teammate reads first: what the project is, who it is for, why it exists and where its edges are
TASK: Create or update the project's PRD from: $ARGUMENTS
CONTEXT: spec-interview, spec-arch and spec-claudemd read the PRD as their context, so it must leave a reader able to say what the project is, who uses it, what is in and out of scope, and the constraints and terms everything else builds on. Sources of truth, in order: the user's answers; files or text named in the arguments; the code, README and existing docs; git history. Doc ownership: @${CLAUDE_SKILL_DIR}/../../shared/project-docs.md Question round: @${CLAUDE_SKILL_DIR}/../../shared/question-round.md Guardrails setup: @${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md
CONSTRAINTS: Write only the PRD, and only what project-docs says it owns: overview and context. No acceptance criteria, user stories, requirement ids, numeric contracts (exit-code numbers, limits, default values), command or flag lists, file paths, stack, components or directory structure. A number stays only when the user names it as a product target. Never invent: every statement traces to a source or a user answer. If a call is denied with [guardrail:...], do not retry it another way: report it.

## Step 0 - Detect
Run the guardrails setup first.
1. Find the PRD (project-docs, Files). If it exists, read it: this run updates it, keeping what still holds and removing what the PRD does not own.
2. Read ARCHITECTURE.md and CLAUDE.md if they exist, so the PRD does not repeat them.
3. Read every source named in $ARGUMENTS in full. If code exists, read the README, manifests and entry points to learn what the project does today and what is only planned.
4. Print one line: fresh or update; code or no code; the sources read.

## Step 1 - Gaps, then questions
For each template section, note its facts with their source, or a gap. Ask every gap that would change what the PRD says as one question round (categories: purpose, users, scope, constraints). Never ask what a source answers. Wait for the answers.

## Step 2 - Write
Omit a section that has nothing true to say. Never pad.
```
# <Name>
<2-4 sentences: what it is, who it is for, what it does for them. End by pointing to ARCHITECTURE.md for how it is built.>

## Problem and context
<Prose: the problem, who has it, why it matters, what success looks like for them, and where the project sits among the tools and teams around it.>

## Users
<Who uses it and what each does with it. A table (user | what they do with it) when there are more than two.>

## What it does
<Capabilities as a user sees them, one line each: what the user gets, not how the tool achieves it (that is ARCHITECTURE.md). In an existing codebase, anything not built yet goes in a closing "Planned" list.>

## What it does not do
<Non-goals and exclusions, one line each.>

## How it is used
<The end-to-end flow in numbered, user-visible steps.>

## Constraints and limitations
<What a user or operator must plan around: supported platforms, environment and deployment assumptions, limits of the approach.>

## Glossary
<Domain terms a new reader needs, each defined once. Not every noun.>

## Open questions
<Product questions still unanswered, each with who decides.>
```
Length follows content, usually 60 to 200 lines.

## Step 3 - Check and save
Check the draft, fix what fails and check again, at most 2 rounds:
- every statement traces to a source or an answer
- nothing the PRD does not own (CONSTRAINTS), no task or process material and no provenance (project-docs rules 4 and 5)
- a reader new to the project can say, after the intro alone, what it is and who it is for
- the duplicate check in project-docs
Write the PRD. Print "PRD saved - <path>, <n> lines, fresh | updated (<what changed>)", the duplicates line, and anything reported for the other files. Stop.
