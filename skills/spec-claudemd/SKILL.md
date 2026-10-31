---
name: spec-claudemd
description: Generate or refresh a lean CLAUDE.md from the code, the plan file, the PRD and ARCHITECTURE.md - enough to make a change on its own (commands, test rules, conventions, invariants, constraints), pointing to the docs instead of importing them
argument-hint: "<plan file .md>"
model: opus
effort: high
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
CONTEXT: CLAUDE.md must be dense and actionable, not a summary. It loads into every session, and every skill reads it to find commands and rules instead of guessing (table in Step 1), so a missing or vague line costs every later run. It must be enough to make a change on its own: commands, test rules, conventions, the invariants every change must keep, and hard constraints. It imports nothing. An `@` import would load the whole PRD and ARCHITECTURE.md into every session, and no skill needs them on every call. Instead, it names them by plain path and says which section to read for what. Evidence priority: existing CLAUDE.md (hand-written lines) > CI config (what really runs) > package manifests / Makefile / scripts > lint, format and type configs > tests and validation code that enforce a rule > sampled code > the plan's Design section (for what is not built yet) > invariants and layering rules an existing ARCHITECTURE.md still holds > README. Doc ownership: @${CLAUDE_SKILL_DIR}/../../shared/project-docs.md Question round: @${CLAUDE_SKILL_DIR}/../../shared/question-round.md Before Step 0, run the guardrails setup: @${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md
CONSTRAINTS: Include only commands, conventions Claude would otherwise get wrong, invariants and hard constraints. Every convention needs evidence: at least 2 code examples (file:line), one enforcing config rule, or, before the code exists, a decision in the plan. Every invariant names what enforces it (a test, a lint rule, validation code) or says "not enforced". No evidence means omit it or ask the user. Every command must be verified, or marked planned when the code it needs does not exist yet. No feature descriptions, rationale, or aspirations. Never restate what the PRD or ARCHITECTURE.md hold (product facts, structure, components, flows, interfaces, configuration, decisions): name the section instead. No `@` imports (project-docs rule 9). Take decisions from the plan, never its task material, and never name the plan (project-docs rule 4). Target under 150 lines. Write only CLAUDE.md, and never a real credential into it. If a call is denied with [guardrail:...], do not retry it another way: list it with the commands you could not verify.

## Step 0 - Detect current state
- Plan file: the .md path in $ARGUMENTS. With none, glob for likely plans (`docs/plans/*.md`, `PLAN.md`, `*plan*.md`) and ask for it as a BLOCKING question (category "input"), offering what you found plus "No plan file". Wait for the answer.
- Does CLAUDE.md exist? If yes, read it first. Preserve hand-written lines that still hold; merge rather than overwrite.
- Find the PRD and ARCHITECTURE.md (project-docs, Files). Read them and the plan: CLAUDE.md points to the two docs and must not repeat them. If CLAUDE.md `@`-imports either doc, this run replaces the import with the Project docs map. Invariants, import and layering rules, and placement rules that ARCHITECTURE.md still holds move here; report them for /spec-arch to remove (project-docs rule 8).

## Step 1 - Gather evidence
- Commands: install, build, dev/run, lint, format, typecheck, test (all), test (single file), test (single test), coverage, generate. CI config is the source of truth for what really runs. With no code yet, take them from the plan's Design section.
- Test layout: where tests live, naming, fixtures/helpers, mocking style, unit vs integration split, how services (DB etc.) are provided.
- Conventions: naming, file placement, error-handling and logging patterns.
- Invariants: the import and layering rules first (from imports, boundary tests and lint configs), then every rule a change must keep. Sources are tests, validation code and comments, the plan's design decisions, and the invariants an existing ARCHITECTURE.md lists. For each one, record what enforces it (a test name, a lint rule, a validation file:line), or "not enforced".
- Docs map: for each code area a change would touch, the ARCHITECTURE.md section that explains it.
- Hard constraints: generated files never hand-edited, migration rules, protected dirs, secrets handling.
- Speed: suites or targets that take minutes, and the faster subset to run while iterating.
Sample at least 3 files per area before claiming a convention. If two competing conventions exist in the code, which one is the target is a question. Ask every question from this step as one question round before Step 2.

What the skills read from CLAUDE.md; each must be present, or stated as "none":
| Reader | Needs |
|---|---|
| build-phase | test (all), test (single file), test (single test), lint, typecheck, build; test layout, naming, fixtures and mocking; known baseline failures; conventions; invariants; off-limits and generated files; the docs map |
| validation loop reviewers | the same commands; conventions, invariants and constraints, each with evidence, because a broken CLAUDE.md rule is BLOCKING |
| followup | the build, test and generate commands; conventions; invariants; the docs map |
| spec-interview | the test framework and command; invariants |

## Step 2 - Verify
Run each command once (use --help or a dry run for anything slow or destructive, and say so). Record pass/fail. A command whose code does not exist yet is not run: it is written with "(planned)". If the baseline test suite fails, list the failing tests under "Known baseline failures". Do NOT fix them here.

## Step 3 - Write using this template
```
# [App name]

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
- [one rule per line, 10-20 lines max, each evidence-backed; where new files go]

## Invariants
- Imports: [the direction, e.g. cli -> commands -> services]; [what never imports what] (enforced by [test | lint rule] | not enforced)
- [what must stay true, one line] (enforced by [test name | file:line] | not enforced)
(rules every change must keep; the structure and reasons behind them stay in ARCHITECTURE.md)

## Constraints
- [absolute prohibitions, 5-10 lines max]
- A change that makes the PRD or ARCHITECTURE.md wrong updates it in the same change   <- only if either exists

## Project docs   <- only if either exists; plain paths, never @ imports
- `<PRD path>`: what the project is, for whom, and its scope. Read it before planning a task.
- `<ARCHITECTURE path>`: how it is built. Read the section for the area you change:
  - [code area or path] -> [section]
```

## Self-check (mandatory before saving)
1. Count lines. 150 is a target; the only valid reason to exceed it is structural (e.g. N independently deployed services each needing a command block). State that reason in one line.
2. If over 150 without such a reason, cut the least actionable lines and list what you cut and why.
3. Every line must be a command, a convention Claude would get wrong, an invariant, a hard constraint or a docs-map entry. Remove the rest.
4. Every reader in the Step 1 table finds what it needs, or an explicit "none".
5. Enough to act alone: a session that reads only CLAUDE.md can run the tests, place a new file, and name every invariant its change must keep.
6. No `@` import. Every invariant names what enforces it or says "not enforced". Every docs-map section exists in the doc it names.
7. Run the duplicate check in project-docs, and confirm no task material from the plan.
8. If any check fails, fix it and run all checks again. Save only when every check passes, at most 3 rounds.

## Save
Write CLAUDE.md. Print "CLAUDE.md saved - [N] lines", whether it was a fresh write or a merge/update (with what changed), the duplicates line, what moved here from ARCHITECTURE.md ("run /spec-arch to remove it there"), and a list of any commands you could not verify or marked planned. Stop.
