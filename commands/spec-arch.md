---
description: Plan a multi-step change in an existing codebase - design, blast radius, overengineering audit, step breakdown
argument-hint: "<task description or Task Brief>"
model: opus
allowed-tools: Read, Glob, Grep, Bash(git log:*), Bash(git status:*), Bash(git ls-files:*)
---

ROLE: Software architect making ONE committed design decision inside a codebase that already exists
TASK: Produce a change plan for: $ARGUMENTS
CONTEXT: No ARCHITECTURE.md is assumed - the existing code IS the architecture. If a Task Brief is in the arguments or conversation, use its ACs. Otherwise derive a minimal one (ACs + out of scope) and get confirmation before continuing. Checklist: @.claude/shared/scenario-checklist.md
CONSTRAINTS: No implementation code. No package installation. Commit to one option before finishing; "Rejected Options" is required. Existing patterns beat new patterns - any deviation needs a stated reason. No refactoring of unrelated code.

## Step 0 - Recon (as-built architecture)
Extract from the code, with file paths as evidence:
- Module boundaries and layering direction (from imports, lint/import-boundary configs)
- Data models/schemas the task touches, with EXACT field names as they exist
- How the most similar existing feature is built (cite the files)
- Test layout and what already covers the area
- Public contracts: API, CLI, events, schema, config, flags
- How migrations/deploys work here
State the current architecture in at most 8 lines.

## Step 1 - Blast radius
For each file/symbol likely to change, a table row:
| symbol/file | callers (grep) | tests covering it | contracts affected | data affected |
Untested callers or untested changed code are risks - mark them.

## Step 2 - Design (one choice per decision)
Each decision gets a one-line justification tied to an AC or a repo constraint:
- Where the change lives (existing home first; new files only if no home exists)
- Reused helpers/patterns (name them)
- Data change: migration, backward compatibility with existing rows/data, rollback
- Rollout: flag or direct

## Step 3 - Overengineering audit (mandatory)
For every new dependency, abstraction, file, config key, or pattern: REQUIRED (cite AC) or SPECULATIVE. Ask the user: keep or cut each SPECULATIVE item. Wait for the answer before continuing.

## Step 4 - Step plan
Each step must be independently buildable, testable and committable, and must leave the suite green. Order lowest-dependency first. If untested code will be modified, Step 1 is a safety net (characterization tests only, no behavior change).
Per step: goal | files | ACs covered | scenarios/tests (from the checklist) | risk | rollback.
If a step needs more than ~10 files or cannot be described in 3 lines, split it.

## Step 5 - Decision record
- Decision (what and how)
- Rationale (cite ACs and repo evidence)
- Rejected Options (each rejected against a specific AC or constraint)
- Risks

Print the plan. Do not save it unless asked. End with one paste-ready line per step:
`/build-phase Step N of M: <goal> - ACs: ...`
Stop.
