---
description: Distill PRD + ARCHITECTURE into a lean CLAUDE.md, at any project stage
model: haiku
---

ROLE: Technical writer who produces actionable developer reference docs
TASK: Distill docs/PRD.md and docs/ARCHITECTURE.md into a lean CLAUDE.md
CONTEXT: CLAUDE.md is loaded into every future Claude session for this project. It must be dense and actionable — not a summary of the docs. The docs are already referenced via @imports and will be read separately. CLAUDE.md may not exist yet, or may already exist from an earlier phase — detect which before writing.
CONSTRAINTS: Do not duplicate content from PRD.md or ARCHITECTURE.md. Do not include feature descriptions, rationale, or aspirations. Reference the docs via @imports instead. Target under 150 lines.

## Step 0 — Detect current state
Check if CLAUDE.md already exists.
- If it does, read it first. Preserve any hand-written conventions or constraints it has that still hold true — merge and update rather than blindly overwriting. Note in your output what changed.
- If it doesn't, this is a fresh write.

Read docs/PRD.md and docs/ARCHITECTURE.md.

## Rules for CLAUDE.md content
Include ONLY:
- Commands — exact shell commands, copy-paste ready, for whichever of build/test/lint/dev-server/run/install actually apply to the chosen stack. Skip any that don't exist for this project (e.g. a library has no dev server; a script has no build step).
- Conventions Claude would otherwise get wrong (naming patterns, file placement, layer rules) — derive these from ARCHITECTURE.md's actual stack and layering, not from any fixed example.
- Hard constraints (e.g. "never import X in Y layer") specific to this project's architecture.
- @docs/PRD.md and @docs/ARCHITECTURE.md as imports (reference, don't duplicate)

Exclude:
- Feature descriptions (already in PRD.md)
- Architecture rationale (already in ARCHITECTURE.md)
- Anything Claude can derive from reading the code itself
- Aspirations, goals, or explanatory prose

## Template to fill
```
# [App name]
@docs/PRD.md
@docs/ARCHITECTURE.md

## Commands
- [label]: [command]   ← one line per command that actually exists for this stack

## Conventions
- [one hard rule per line, 10–20 lines max]

## Constraints
- [absolute prohibitions only, 5–10 lines max]
```

## Self-check (mandatory before saving)
1. Count lines in the draft.
2. 150 lines is a target, not a hard wall. The ONLY valid justification for exceeding it is a structural one tied to the stack itself (e.g. "N independently-deployed services each need their own command block") — never "there was more to say" or "the project is complex." State the justification in one line before saving.
3. If over 150 with no such structural justification: cut the least actionable lines until under 150. List what you cut and why.
4. Verify every line is either a command, a convention Claude would get wrong, or a hard constraint. Remove anything else.

## Save
Write to CLAUDE.md. Print "CLAUDE.md saved — [N] lines" and whether it was a fresh write or a merge/update. Stop.
