---
name: spec-claudemd
description: Generate or refresh a lean CLAUDE.md from evidence in the repo
model: opus
allowed-tools: Read, Glob, Grep, Edit(./CLAUDE.md), Bash(git ls-files:*), Bash(git log:*)
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
TASK: Create or update CLAUDE.md from what the repository actually contains
CONTEXT: CLAUDE.md must be dense and actionable, not a summary. Evidence priority: existing CLAUDE.md (hand-written lines) > CI config (what really runs) > package manifests / Makefile / scripts > lint, format and type configs > README > sampled code. If docs/PRD.md or docs/ARCHITECTURE.md exist, import them; if not, do not mention them. Before Step 0, run the guardrails setup: @${CLAUDE_SKILL_DIR}/../../shared/guardrails-setup.md
CONSTRAINTS: Include only commands, conventions Claude would otherwise get wrong, and hard constraints. Every convention needs evidence: at least 2 code examples (file:line) or one enforcing config rule. No evidence means omit it or ask the user. Every command must be verified. No feature descriptions, rationale, or aspirations. Target under 150 lines. Write only CLAUDE.md, and never a real credential into it. If a call is denied with [guardrail:...], do not retry it another way: list it with the commands you could not verify.

## Step 0 - Detect current state
- Does CLAUDE.md exist? If yes, read it first. Preserve hand-written lines that still hold; merge rather than overwrite.
- Do docs/PRD.md / docs/ARCHITECTURE.md exist? Note for the import lines.

## Step 1 - Gather evidence
- Commands: install, build, dev/run, lint, format, typecheck, test (all), test (single file), test (single test), coverage. CI config is the source of truth for what really runs.
- Test layout: where tests live, naming, fixtures/helpers, mocking style, unit vs integration split, how services (DB etc.) are provided.
- Conventions: naming, file placement, layering (from imports / boundary lint rules), error-handling and logging patterns.
- Hard constraints: generated files never hand-edited, migration rules, protected dirs, secrets handling.
Sample at least 3 files per area before claiming a convention. If two competing conventions exist in the code, ask the user which is the target.

## Step 2 - Verify
Run each command once (use --help or a dry run for anything slow or destructive, and say so). Record pass/fail. If the baseline test suite fails, list the failing tests under "Known baseline failures". Do NOT fix them here.

## Step 3 - Write using this template
```
# [App name]
@docs/PRD.md            <- only if it exists
@docs/ARCHITECTURE.md   <- only if it exists

## Commands
- install / build / dev / lint / format / typecheck: [command]
- test (all): [command]
- test (single file): [command]
- test (single test): [command]
- coverage: [command]   <- only if it exists

## Testing
- Layout, naming, fixtures, mocking rules, which level (unit/integration) for what
- Known baseline failures: [names, or none]
(build-phase and its validation loop read this section - keep it exact)

## Conventions
- [one rule per line, 10-20 lines max, each evidence-backed]

## Constraints
- [absolute prohibitions, 5-10 lines max]
```

## Self-check (mandatory before saving)
1. Count lines. 150 is a target; the only valid reason to exceed it is structural (e.g. N independently deployed services each needing a command block). State that reason in one line.
2. If over 150 without such a reason, cut the least actionable lines and list what you cut and why.
3. Every line must be a command, a convention Claude would get wrong, or a hard constraint. Remove the rest.
4. If any check fails, fix it and run all checks again. Save only when every check passes, at most 3 rounds.

## Save
Write CLAUDE.md. Print "CLAUDE.md saved - [N] lines", whether it was a fresh write or a merge/update (with what changed), and a list of any commands you could not verify. Stop.
