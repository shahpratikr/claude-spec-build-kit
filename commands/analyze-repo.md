---
description: Evaluate a repo's structure, testing landscape and risk hotspots; flag files for deep review. Adaptive depth by repo size.
argument-hint: [optional path, defaults to current directory]
model: opus
allowed-tools: Read, Glob, Grep, Write, Bash(git ls-files:*), Bash(git log:*), Bash(git rev-parse:*)
---

# Repo Evaluation

ROLE: Senior software developer (10+ years) evaluating an unfamiliar repo, skeptical of surface-level tidiness as a proxy for good code
TASK: Produce a written report covering structure, the purpose of each file/directory, the testing landscape, a shortlist of files that warrant deep review, a deep dive on that shortlist, and concrete next steps
CONTEXT: Target is `$ARGUMENTS` (default: current working directory; if the path does not exist, say so and stop). Output is saved to `REPO_ANALYSIS.md` in the repo root. Depth is adaptive: repo size decides how much gets a full read versus a skim.
CONSTRAINTS: Never skip Phase 1. Never deep-dive beyond Phase 3's shortlist; if scope must expand, say so explicitly. No filler observations a junior could produce from the file tree alone - every claim must require having read the code. Call out contradictions and rot directly (docs vs code, dead code, stale patterns). Tag every finding [Verified: read code] or [Inferred]. Only run commands that are the documented test/build/lint commands and are non-destructive; if one needs services or credentials, mark it NOT RUN.

Start the report with: `Analyzed at commit <hash> on <date>`.

## Phase 1 - Skim (always run)
1. Get the file list with `git ls-files` (respect .gitignore; exclude node_modules, .git, build artifacts, lockfiles from the tree view but note their existence).
2. Count files and bucket by SOURCE files = tracked files excluding tests, generated, vendored and fixtures:
   - Small (<50), Medium (50-500), Large (500+)
3. Identify the tech stack from manifests/config (package.json, pyproject.toml, Cargo.toml, go.mod, pom.xml, Gemfile, *.csproj, Dockerfiles, CI configs). State language(s), framework(s), package manager, build tool, test framework.
4. Read README, CONTRIBUTING and any docs/ entry point. Extract stated purpose, how to run, how to test. Note if missing or stale.
5. Identify the architectural shape: monolith, monorepo (list workspaces), microservices, library, CLI, etc.
6. Git signals: commit count and age; the 15 most-changed files in the last 12 months (`git log --since=12.months --name-only --pretty=format:` then count); author spread (bus factor).
7. Verification: run the documented test command once and record pass/fail counts (baseline), or mark NOT RUN with the reason. Label every "how to run/test" claim as Verified-by-running or Read-only.

## Phase 1b - Testing landscape (always run)
- Framework(s), test layout, naming, fixtures/helpers, mocking style
- How to run all tests and a single test (verified or not)
- Test-to-source file ratio; unit vs integration vs e2e presence
- Skipped/disabled/only-focused tests (grep for skip, xfail, .only, @Ignore)
- Coverage tooling and any threshold; CI stages that run tests
- Which core modules have NO tests (map modules to tests by naming and imports)
- Flakiness markers: retries, sleeps, order-dependent setup

## Phase 2 - Purpose map (always run; depth scales with size)
Table: | Path | Type | Purpose | for every top-level directory and root file.
- Small repos: extend to every file.
- Medium/Large: top-level plus one level for core-logic directories. List generated/vendored/fixture directories as "not expanded" rather than omitting them.

## Phase 3 - Flag files for deep dive
State which criterion triggered each flag:
- Entry points (main/index, bootstrap, CLI entry, server startup)
- Core domain logic (breaks the product if deleted)
- High blast-radius files (imported/used across many files)
- Risk signals: unusual complexity, auth/security code, payment or deletion logic, dense TODO/FIXME/HACK, secrets or credentials in tracked files
- Hotspots: high churn (Phase 1 step 6) combined with size or complexity
- Core but untested (Phase 1b)
- Inconsistency signals: contradicts docs, looks abandoned, dead paths
Shortlist size: Small up to ~10, Medium up to ~15, Large up to ~20 (state honestly that this is a sample and what was excluded).

## Phase 4 - Deep dive on flagged files only
For each file: what it does and why; key functions/classes; dependencies in and out; anything concerning (unclear logic, missing error handling, tight coupling, outdated patterns); test coverage of this file (which tests, or none).
Do not deep-dive outside the list. If something else turns out to matter, add it explicitly with the reason.
Before writing Phase 5, re-count the files deep-dived against the Phase 3 shortlist. If they do not match 1:1, list additions under "Scope expansions" with a trigger reason and confirm no file was covered without appearing on a list. This check is mandatory.

## Phase 5 - Next steps
Ordered and concrete: files/directories needing a follow-up pass and why; open questions the repo does not answer; a suggested onboarding order.
Then add a section **Recon facts for downstream commands**: verified commands, conventions with file evidence, baseline test status, modules with no tests. (/build-phase and /spec-claudemd can use this instead of re-discovering it.)

## Output
Write the report to `REPO_ANALYSIS.md` in the repo root, with headers matching the phases above. Then print a short summary: tech stack, size bucket, baseline test status, number of files flagged, and the report path.
