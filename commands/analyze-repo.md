---
description: Evaluate a repo's structure, file purposes, and flag high-priority files for deep review. Adaptive depth based on repo size.
argument-hint: [optional path, defaults to current directory]
model: sonnet
---

# Repo Evaluation

ROLE: Senior software developer (10+ years) evaluating an unfamiliar repo, skeptical of surface-level tidiness as a proxy for good code
TASK: Produce a written report covering overall structure, purpose of each file/directory, a shortlist of files that warrant deep review, a deep dive on that shortlist, and concrete next steps
CONTEXT: Target is `$ARGUMENTS` (default: current working directory). Output is saved to `REPO_ANALYSIS.md` in the repo root, not just chat output. Depth is adaptive — repo size determines how much gets a full read vs. a skim; do not apply uniform depth regardless of size.
CONSTRAINTS: Never skip Phase 1, even on a repo that looks small. Never deep-dive beyond Phase 3's shortlist — if scope needs to expand mid-analysis, say so explicitly rather than silently drifting into full coverage. No filler observations any competent junior could produce from the file tree alone — every claim must require having actually read the code. Call out contradictions and rot directly (docs vs. code, dead code, stale patterns) rather than describing the repo more charitably than it deserves.

## Phase 1 — Skim (always run, regardless of repo size)

1. Get a full file tree (respect `.gitignore`; exclude `node_modules`, `.git`, build artifacts, lockfiles from the tree view but note their existence).
2. Count total files and rough size buckets:
   - **Small** (<50 source files)
   - **Medium** (50–500)
   - **Large** (500+)
   This bucket determines how aggressively Phase 3's flagging filters.
3. Identify the tech stack from manifests/config (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`, `Gemfile`, `*.csproj`, Dockerfiles, CI configs, etc.). State language(s), framework(s), package manager, build tool, and test framework.
4. Read `README`, `CONTRIBUTING`, and any `docs/` entry point if present. Extract: stated purpose, how to run it, how to test it. Note explicitly if these are missing or stale (e.g. reference commands/files that no longer exist).
5. Identify the architectural shape: monolith, monorepo (list workspaces/packages), microservices, library/package, CLI tool, etc.

## Phase 2 — Purpose map (always run, but depth scales with size)

For every top-level directory, and every file directly at repo root, give a one-line purpose. Format as a table:

| Path | Type | Purpose |
|---|---|---|
| `src/` | dir | ... |
| `config.yaml` | file | ... |

- **Small repos**: extend this table to cover every file, not just top-level.
- **Medium/Large repos**: stop at top-level + one level deep for directories that look like core logic (skip generated/vendored/test-fixture directories — note them as "not expanded" rather than silently omitting).

## Phase 3 — Flag files for deep dive

Do not deep-dive everything. Select a shortlist using these criteria, and state which criterion triggered each flag:

- **Entry points**: main/index files, app bootstrap, CLI entry, server startup.
- **Core domain logic**: the files that would break the product if deleted — not utils, not config.
- **High blast-radius files**: anything imported/used across many other files (a shared types file, a central config, a base class many things extend).
- **Risk signals**: files with unusually high complexity (long, deeply nested, or many responsibilities), auth/security-related code, payment or data-deletion logic, files with dense `TODO`/`FIXME`/`HACK` comments.
- **Inconsistency signals**: files that contradict what the README/docs claim, or that look abandoned (stale patterns vs. rest of codebase, commented-out blocks, dead code paths).

Target shortlist size by bucket:
- Small: up to ~10 files
- Medium: up to ~15 files
- Large: up to ~20 files — be honest that this is a sample, not full coverage, and say what was excluded and why.

## Phase 4 — Deep dive on flagged files only

For each shortlisted file, cover:
- What it does and why it exists (not just a restatement of the filename).
- Key functions/classes and their responsibilities.
- Dependencies in and out (what it relies on, what relies on it).
- Anything concerning: unclear logic, missing error handling, untested paths, tight coupling, outdated patterns relative to the rest of the repo.

Do not deep-dive anything outside this list. If something outside the list turns out to matter while doing this phase, add it to the shortlist explicitly and say why, rather than quietly expanding scope.

Before writing Phase 5, re-count the files actually deep-dived against the Phase 3 shortlist. If they don't match 1:1, stop and reconcile: list any addition under "Scope expansions" with its trigger reason, and confirm no file was covered without appearing on either list. This check is mandatory, not optional.

## Phase 5 — Next steps

Give a concrete, ordered list (not generic advice) of what to explore next, e.g.:
- Specific files/directories not covered in Phase 4 that warrant a follow-up pass, and why.
- Open questions the repo doesn't answer (missing docs, unclear ownership of a module, ambiguous config).
- Suggested order of exploration if someone is onboarding to this codebase.

## Output

Write the full report to `REPO_ANALYSIS.md` in the repo root, structured with headers matching the phases above. After writing, print a short summary in chat: tech stack, size bucket, number of files flagged, and the file path to the saved report.
