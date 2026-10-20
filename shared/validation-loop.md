# Validation Loop

Used by build-phase (Step 8) and followup (IMPLEMENT). It validates uncommitted changes, so nothing has to be committed first.

RULE: intent comes from TASK and the ACs, never from the diff. A validator that infers the spec from the implementation will approve the implementation. Reviewers receive intent and file lists, never the author's reasoning or notes.

## Inputs (from the calling skill)
- TASK: the user's request, verbatim.
- ACs: the acceptance criteria, verbatim.
- BASE: the snapshot taken before the first edit. `git stash create` prints a hash that records the tracked files without touching the working tree or index; when it prints nothing, BASE is `git rev-parse HEAD`. `git diff <BASE>` then shows exactly this change, even when the tree already held other uncommitted work.
- Files: changed production files, changed test files, and new untracked files (compare `git status --porcelain --untracked-files=all` with the list recorded at the snapshot).
- Commands: test, lint, typecheck and build, plus the baseline failing tests.

## Each round
1. Facts first. Run the full test command, plus lint, typecheck and build where they exist. Mark each failure new or pre-existing (baseline). Re-run new or changed tests 3 times when they involve time, async, concurrency or randomness.
2. Spawn three reviewers in parallel with the Agent tool, by subagent type, in the foreground: wait for all three reports in this turn. A background reviewer's report arrives as a new turn, and that ends the calling skill's tool pre-approvals and model override. Each prompt is self-contained: TASK, ACs, BASE, the file lists, and the line "Read-only: never create, edit or delete files." gap-hunter also gets the scenario checklist path. If a type is not installed, use general-purpose with the same prompt.
   - criteria-auditor: per AC, the implementing code and a test that would fail if it broke (YES / PARTIAL / NO); requirements in TASK that no AC covers; ACs not grounded in TASK or the code; unrequested changes.
   - gap-hunter: uncovered scenarios and defects, ranked HIGH / MED / LOW.
   - convention-checker: changed files and BASE; violations of CLAUDE.md, or of sibling files when CLAUDE.md is missing. When the calling skill requires AC ids in test names, say so in the prompt so they are not reported.
3. Wait for all three, then triage every finding:
   - MUST-FIX: an AC that is NO or PARTIAL; a TASK requirement no AC covers (add the AC, then build it); a HIGH or MED gap; a defect; a new test, lint, typecheck or build failure; a blocking convention violation; an unrequested change (revert it).
   - OPTIONAL: LOW gaps and minor conventions. Fix them when the fix is small and in scope; otherwise list them.
   - DISMISS: only when the finding is factually wrong, citing the file:line that proves it. Never dismiss a failing test.
   - NEEDS DECISION: a correct finding whose fix would widen scope, change a public contract or add a dependency. It is never a DISMISS. Ask it as a blocking question; if it stays unanswered, leave it open.
4. Nothing MUST-FIX: the loop ends with PASS.
5. Otherwise fix each MUST-FIX item the way the calling skill builds: a failing test first for each defect or gap, then the smallest change, then the narrowest tests. Never fix pre-existing failures. Refresh the file lists and run the next round in full, because a fix can break something else.

## Stop conditions
- At most 3 rounds. MUST-FIX items still open after round 3 make the verdict NEEDS REVIEW.
- Stop early with NEEDS REVIEW when a finding comes back unchanged after a fix, and say what you tried.

## Verdict
PASS = every AC YES, no TASK requirement uncovered, no HIGH or MED gap left inside the scope, no blocking violation, no new failure, and nothing critical NOT RUN. Open NEEDS DECISION items don't block PASS, but they are always listed. Anything else is NEEDS REVIEW, with the open items listed.

## Record (one line per round, for the report)
`R<n>: tests [pass/fail], ACs [YES/PARTIAL/NO counts], gaps [H/M/L], conventions [n] -> fixed [...], dismissed [...], open [...]`
