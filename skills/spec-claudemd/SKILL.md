---
name: spec-claudemd
description: Generate or refresh a lean CLAUDE.md from the code, the plan file, the PRD and ARCHITECTURE.md - the commands, test rules, conventions and constraints every skill reads
argument-hint: "<plan file .md>"
model: opus
allowed-tools: Read, Glob, Grep, Write(./CLAUDE.md), Edit(./CLAUDE.md), Bash(git ls-files:*), Bash(git log:*)
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

ROLE: Technical writer producing an actionable developer reference that is loaded into every future Claude session
TASK: Create or update CLAUDE.md from what the repository contains and the plan decides: $ARGUMENTS
CONTEXT: CLAUDE.md must be dense and actionable, not a summary. Every skill reads it to find commands and rules instead of guessing (table in Step 1), so a missing or vague line costs every later run. Evidence priority: existing CLAUDE.md (hand-written lines) > CI config (what really runs) > package manifests / Makefile / scripts > lint, format and type configs > sampled code > the plan's Design section (for what is not built yet) > README. Doc ownership: @${CLAUDE_SKILL_DIR}/../../shared/project-docs.md Question round: @${CLAUDE_SKILL_DIR}/../../shared/question-round.md Before Step 0, run the guardrails setup: @${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md
CONSTRAINTS: Include only commands, conventions Claude would otherwise get wrong, and hard constraints. Every convention needs evidence: at least 2 code examples (file:line), one enforcing config rule, or, before the code exists, a decision in the plan. No evidence means omit it or ask the user. Every command must be verified, or marked planned when the code it needs does not exist yet. No feature descriptions, rationale, or aspirations. Never restate what the PRD or ARCHITECTURE.md hold (product facts, structure, components, invariants, decisions): point to the section instead. Take decisions from the plan, never its task material, and never import it (project-docs rule 4). Target under 150 lines. Write only CLAUDE.md, and never a real credential into it. If a call is denied with [guardrail:...], do not retry it another way: list it with the commands you could not verify.

## Step 0 - Detect current state
- Plan file: the .md path in $ARGUMENTS. With none, glob for likely plans (`docs/plans/*.md`, `PLAN.md`, `*plan*.md`) and ask for it as a BLOCKING question (category "input"), offering what you found plus "No plan file". Wait for the answer.
- Does CLAUDE.md exist? If yes, read it first. Preserve hand-written lines that still hold; merge rather than overwrite.
- Find the PRD and ARCHITECTURE.md (project-docs, Files). Read them and the plan: CLAUDE.md imports the two docs and must not repeat them.

## Step 1 - Gather evidence
- Commands: install, build, dev/run, lint, format, typecheck, test (all), test (single file), test (single test), coverage, generate. CI config is the source of truth for what really runs. With no code yet, take them from the plan's Design section.
- Test layout: where tests live, naming, fixtures/helpers, mocking style, unit vs integration split, how services (DB etc.) are provided.
- Conventions: naming, file placement, layering (from imports / boundary lint rules), error-handling and logging patterns.
- Hard constraints: generated files never hand-edited, migration rules, protected dirs, secrets handling.
- Speed: suites or targets that take minutes, and the faster subset to run while iterating.
Sample at least 3 files per area before claiming a convention. If two competing conventions exist in the code, which one is the target is a question. Ask every question from this step as one question round before Step 2.

What the skills read from CLAUDE.md; each must be present, or stated as "none":
| Reader | Needs |
|---|---|
| build-phase | test (all), test (single file), test (single test), lint, typecheck, build; test layout, naming, fixtures and mocking; known baseline failures; conventions; off-limits and generated files |
| validation loop reviewers | the same commands; conventions and constraints, each with evidence, because a broken CLAUDE.md rule is BLOCKING |
| followup | the build, test and generate commands; conventions |
| spec-interview | the test framework and command; layering, or the ARCHITECTURE.md section that has it |
| test-reporter agent | the `test (all):` line |

## Step 2 - Verify
Run each command once (use --help or a dry run for anything slow or destructive, and say so). Record pass/fail. A command whose code does not exist yet is not run: it is written with "(planned)". If the baseline test suite fails, list the failing tests under "Known baseline failures". Do NOT fix them here.

## Step 3 - Write using this template
```
# [App name]
@<PRD path>              <- only if it exists
@<ARCHITECTURE path>     <- only if it exists

## Commands
- install / build / dev / lint / format / typecheck / generate: [command]
- test (all): [command]
- test (single file): [command]
- test (single test): [command]
- coverage: [command]   <- only if it exists
- slow: [what takes minutes; the faster subset to run while iterating]   <- only if one exists

## Testing
- Layout, naming, fixtures, mocking rules, which level (unit/integration) for what
- Known baseline failures: [names, or none]
(build-phase and its validation loop read this section - keep it exact)

## Conventions
- [one rule per line, 10-20 lines max, each evidence-backed]

## Constraints
- [absolute prohibitions, 5-10 lines max]
- A change that makes the PRD or ARCHITECTURE.md wrong updates it in the same change   <- only if either exists
```

## Self-check (mandatory before saving)
1. Count lines. 150 is a target; the only valid reason to exceed it is structural (e.g. N independently deployed services each needing a command block). State that reason in one line.
2. If over 150 without such a reason, cut the least actionable lines and list what you cut and why.
3. Every line must be a command, a convention Claude would get wrong, or a hard constraint. Remove the rest.
4. Every reader in the Step 1 table finds what it needs, or an explicit "none".
5. Run the duplicate check in project-docs, and confirm no task material from the plan.
6. If any check fails, fix it and run all checks again. Save only when every check passes, at most 3 rounds.

## Save
Write CLAUDE.md. Print "CLAUDE.md saved - [N] lines", whether it was a fresh write or a merge/update (with what changed), the duplicates line, and a list of any commands you could not verify or marked planned. Stop.
