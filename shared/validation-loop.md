# Validation Loop

Used by build-phase (Step 8) and followup (IMPLEMENT). It validates uncommitted changes, so nothing has to be committed first.

RULE: intent comes from TASK, the ACs and the user's confirmed answers, never from the diff. A validator that infers the spec from the implementation will approve the implementation. Reviewers receive intent, sources and file lists, never the author's reasoning or notes. From round 2 they also get the findings ledger, and may challenge the evidence in it.

GOAL: round 1 finds nearly everything, and later rounds only confirm the fixes and review what the fixes changed. A fresh full review every round samples new findings every time, so the loop never converges.

## Inputs (from the calling skill)
- TASK: the user's request, verbatim.
- ACs: the acceptance criteria, verbatim.
- Confirmed answers: the user's answers from earlier question rounds (Q -> answer), or none. They are intent: without them, reviewers report the ACs those answers produced as ungrounded.
- Sources: files the change must stay faithful to, such as specs, source documents and files the task names, or none.
- BASE: the snapshot taken before the first edit. `git stash create` prints a hash that records the tracked files without touching the working tree or index; when it prints nothing, BASE is `git rev-parse HEAD`. `git diff <BASE>` then shows exactly this change, even when the tree already held other uncommitted work.
- Files: changed production files, changed test files, and new untracked files (compare `git status --porcelain --untracked-files=all` with the list recorded at the snapshot).
- Commands: test, lint, typecheck and build, plus the baseline failing tests.

## Round 1: full review
1. Facts first. Run the full test command, plus lint, typecheck and build where they exist. If the calling skill ran them after its last edit, reuse those results instead. Mark each failure new or pre-existing (baseline). Re-run new or changed tests 3 times when they involve time, async, concurrency or randomness.
2. Spawn three reviewers in parallel with the Agent tool, by subagent type, in the foreground: wait for all three reports in this turn. A background reviewer's report arrives as a new turn, and that ends the calling skill's tool pre-approvals and model override. Each prompt is self-contained: TASK, ACs, confirmed answers, sources, BASE, the file lists, and the line "Read-only: never create, edit or delete files." gap-hunter also gets the scenario checklist path. If a type is not installed, use general-purpose with the same prompt.
   - criteria-auditor: per AC, the implementing code and a test that would fail if it broke (YES / PARTIAL / NO); requirements in TASK that no AC covers; ACs not grounded in TASK, the confirmed answers, the sources or the code; ACs no finite check can verify; unrequested changes.
   - gap-hunter: every uncovered scenario and defect, ranked HIGH / MED / LOW, with every location of each one. No cap.
   - convention-checker: changed files and BASE; violations of CLAUDE.md, or of sibling files when CLAUDE.md is missing, each marked BLOCKING or MINOR. When the calling skill requires AC ids in test names, say so in the prompt so they are not reported.
3. Wait for all three, then triage every finding:
   - MUST-FIX: an AC that is NO or PARTIAL; a TASK requirement no AC covers (add the AC, then build it); a HIGH or MED gap; a defect; a new test, lint, typecheck or build failure; a BLOCKING convention violation; an unrequested change (revert it).
   - OPTIONAL: LOW gaps and MINOR conventions. Fix them when the fix is small and in scope; otherwise list them.
   - DISMISS: only when the finding is factually wrong, citing the file:line that proves it. Never dismiss a failing test.
   - NEEDS DECISION: a correct finding whose fix would widen scope, change a public contract or add a dependency, and an AC no finite check can verify ("all corner cases"): ask the user to bound it. It is never a DISMISS. Ask it as a BLOCKING question, as the question round says; if it stays unanswered, leave it open.
4. Write every finding into the ledger: id (`R1-A2` for the auditor, `G` for gap-hunter, `C` for convention-checker), one-line finding, class, status.
5. Nothing MUST-FIX: the loop ends with PASS.
6. Otherwise fix:
   a. Snapshot the change set first, so the next round can see what the fixes changed. PREV is a new folder `prev-r<n>` in your scratchpad directory, where reviewers can read (`mktemp -d` when there is no scratchpad): `mkdir -p "$PREV" && tar cf - <every existing file in the file lists> | tar xf - -C "$PREV"`.
   b. Fix the cause, not the instance. Before editing, search for every other place with the same pattern (the same term, code shape, enumerated value, contradiction or test weakness) and fix them all in this pass. A sibling left unfixed comes back as next round's finding.
   c. Fix each item the way the calling skill builds: a failing test first for each defect or gap, then the smallest change, then the narrowest tests. Never fix pre-existing failures.
   d. Update the ledger: fixed at file:line, or open with the reason.

## Round 2 and later: re-check
1. Facts. Refresh the file lists and run the full suite, lint, typecheck and build again, because a fix can break something else.
2. Spawn only the reviewers the fixes need, in parallel and in the foreground as in round 1:
   - each reviewer that had a MUST-FIX finding last round, to confirm its items;
   - gap-hunter whenever the fixes changed behavior or content, because fixes are where new defects come from;
   - criteria-auditor whenever an AC was added or changed;
   - convention-checker whenever the fixes created a file.
   Record each skipped reviewer with its reason.
3. Each prompt: the round 1 inputs, the ledger, PREV, and this scope:
   - For each ledger item from your reviewer type marked MUST-FIX, report fixed or not fixed, with file:line.
   - Review the delta, with your full method: `git diff --no-index "$PREV/<file>" <file>` for each file, and files that are not in PREV in full. Include the code that calls or depends on the changed lines.
   - Outside the delta, report only HIGH findings.
   - Do not report a DISMISS or OPTIONAL ledger item again unless its evidence is wrong; then say why.
4. Triage as in round 1, with one difference: a new MED or LOW finding outside the delta is OPTIONAL. List it; do not loop on it.
5. Then steps 4 to 6 of round 1.

## Stop conditions
- At most 3 rounds. MUST-FIX items still open after round 3 make the verdict NEEDS REVIEW.
- Stop early with NEEDS REVIEW when a finding comes back unchanged after a fix, and say what you tried.

## Verdict
PASS = every AC YES, no TASK requirement uncovered, no HIGH or MED gap left inside the scope, no BLOCKING violation, no new failure, and nothing critical NOT RUN. Open NEEDS DECISION items don't block PASS, but they are always listed. Anything else is NEEDS REVIEW, with the open items listed.

## Record (one line per round, for the report)
`R<n>: tests [pass/fail], reviewers [run | skipped: reason], ACs [YES/PARTIAL/NO counts], gaps [H/M/L], conventions [blocking/minor] -> fixed [...], dismissed [...], open [...]`
