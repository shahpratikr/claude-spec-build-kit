# Validation Loop

Used by build-phase (Step 8) and followup (IMPLEMENT). It validates uncommitted changes, so nothing has to be committed first.

RULE: intent comes from TASK, the ACs and the user's confirmed answers, never from the diff. A validator that infers the spec from the implementation will approve the implementation. Reviewers receive intent, sources and file lists, never the author's reasoning, notes, variant table or fix plan. From round 2 they also get the findings ledger, and may challenge the evidence in it.

GOAL: round 1 finds nearly everything, round 2 closes what is left, and round 3 runs only when round 2 leaves a reason to. A fresh full review every round samples new findings every time, so the loop never converges. Most later-round findings come from fixes that handled only the reported instance, so every fix round starts with a checked fix plan.

FACTS ONCE: the calling skill runs the tests, checks and the can-fail pass, and reviewers read the results. A reviewer that runs the suite or a mutation sweep again spends minutes and learns nothing new. Never tell a reviewer to run them, and add nothing to a reviewer prompt that contradicts the reviewer's own instructions.

ONE TURN: the whole loop runs in the calling skill's turn. Spawn reviewers in the foreground and wait for them. Never use `run_in_background`, Monitor or a background Agent for tests, the can-fail pass or reviewers: each notification arrives as a new turn, and from then on the run has lost the skill's model, effort, tool pre-approvals and hooks. A command that may outlast the Bash timeout gets the maximum timeout, or is split into parts that each fit.

SHORT OUTPUT: everything a command prints stays in context for the rest of the run. Write full logs to the scratchpad and print only what the next decision needs: `<cmd> > "$SCR/<name>.log" 2>&1; echo "exit $?"; tail -n 40 "$SCR/<name>.log"`. Read a log further only for the failure you are fixing.

## Inputs (from the calling skill)
- TASK: the user's request, verbatim.
- ACs: the acceptance criteria, verbatim.
- Confirmed answers: the user's answers from earlier question rounds and the plan's Confirmed answers (Q -> answer), or none. They are intent: without them, reviewers report the ACs those answers produced as ungrounded.
- Sources: the plan file when one was named, and files the change must stay faithful to, such as specs, source documents and files the task names, or none.
- BASE: the snapshot taken before the first edit. `git stash create` prints a hash that records the tracked files without touching the working tree or index; when it prints nothing, BASE is `git rev-parse HEAD`. `git diff <BASE>` then shows exactly this change, even when the tree already held other uncommitted work.
- Files: changed production files, changed test files, and new untracked files (compare `git status --porcelain --untracked-files=all` with the list recorded at the snapshot).
- Commands: test, lint, typecheck and build, plus the baseline failing tests.
- Facts: the latest results of those commands, of the 3x runs, and of the can-fail pass.
- Variant table: the calling skill's table of input surfaces and their variants, each with its test or an N/A reason. It is the builder's reasoning: it feeds the fix plan, never a reviewer.

## Size tier
Set once, before round 1, from `git diff <BASE> --stat` plus the line counts of new files, production and test files together:
- S: at most 3 files and 80 changed lines. Round 1 spawns gap-hunter alone. The calling skill maps each AC to its code and its assertion line (file:line) itself, and puts that map into the facts. A deep profile (see the task profile) also spawns criteria-auditor at this tier.
- M: anything larger, up to the size gate. Round 1 spawns all three reviewers.
- L: over the size gate, built in one run at the user's choice. All three reviewers, and the record says so.

## Can-fail pass
Proves that the tests catch a break in the changed code. The calling skill runs it once per round, on the production lines that round changed: every changed line in round 1, and later only the lines the fixes changed (`git diff --no-index "$PREV/<file>" <file>`).
1. When the project has a mutation tool (manifests, CLAUDE.md), run it limited to those files or lines.
2. Otherwise script it. Break each changed condition, comparison and boundary (`>` against `>=`), boolean, early return, raised error, returned constant, and call to a lock, validation or cleanup, one at a time. Run the narrowest tests that cover the file and record killed or survived. Most important first, at most about 40 per pass.
3. Break the code in place, one break at a time. Save each file to the scratchpad first and restore it in a `finally` block. Afterwards confirm that `git status --porcelain` and `git diff <BASE> --stat` match what they were before the pass.
4. The script writes every result to `canfail-r<n>.txt` in the scratchpad and prints only the killed and survived counts, plus file:line and the break for each survivor. Run it in the foreground (ONE TURN).
5. Kill each survivor with a test, or record why it cannot change behavior. The survivors left open, each with that reason, go into the facts.
When the project has no tests, the pass is N/A with that reason: a validation command whose exit code fails when the AC is violated counts as the test, and an AC with neither stays PARTIAL, so the verdict is NEEDS REVIEW.
Do not run it again in the same round, or after the last round unless code changed since.

## Fix plan (every fix round, before any edit)
1. Snapshot the change set first, so the next round can see what the fixes changed. PREV is a new folder `prev-r<n>` in your scratchpad directory, where reviewers can read: `mkdir -p "$PREV" && tar cf - <every existing file in the file lists> | tar xf - -C "$PREV"`.
2. Write `fix-plan-r<n>.md` in the scratchpad, one entry per MUST-FIX ledger item:
   1. Root cause, in one line: the cause, not the reported instance.
   2. Siblings: the search commands run, and every hit marked fix or not-applicable, with a reason.
   3. Variants: the variant-table rows the fix must handle. The reviewer's example is one instance.
   4. Blast radius: the callers and dependents of the lines to change, and what each could break. Watch removed or added early returns, changed error types, and widened or narrowed conditions.
   5. Tests: one failing test per variant, each able to fail when the scenario is absent.
   6. Pre-mortem: the most likely way this fix is wrong, and the check that rules it out.
3. Verify the plan against the repository, not from memory. Check every entry:
   1. Complete: every MUST-FIX ledger item has an entry, and every entry has all six parts. A vague part ("fix similar places", "add tests") counts as missing.
   2. Locations: re-open every cited file:line. It exists and says what the entry claims.
   3. Siblings: re-run each search. The hits match the list and every hit is classified. Derive the search terms from the root cause, not the reviewer's wording, and add the pattern's other spellings. A new hit joins the entry.
   4. Variants: every variant-table row for the input surface the fix touches is in the entry or N/A with a reason. The reviewer's example is one of them.
   5. Blast radius: re-run the caller search and list every caller. For each early return, error type or condition the fix adds, removes or changes, name the code path that depends on it and what happens there.
   6. Tests: each is named, its file exists or is marked new, and it follows the repository's test naming. Each would fail without the fix, and fails when its scenario finds zero items.
   7. Root cause: the fix changes the cause, so it also closes every sibling. A fix that handles only the reported instance is incorrect.
   8. Consistency: no two entries conflict; entries that touch the same lines are merged; no entry contradicts an AC or a confirmed answer. An entry that changes a public contract or widens scope becomes NEEDS DECISION.
4. Correct the plan. An entry with a part missing, malformed (wrong format, or parts that do not fit together) or incorrect (wrong line, stale search, missed caller, a test that cannot fail) is fixed in `fix-plan-r<n>.md`. Then run all eight checks again on the entries that changed, at most 3 passes. An entry that still fails is not applied: the ledger marks it open with the failing check, or NEEDS DECISION when the failure is a scope question.
5. Print one line: `fix-plan check r<n>: <entries> entries, <c> corrected (missing <a>, malformed <b>, incorrect <d>), <h> held back, <p> passes`. No edit of this round starts before this line.
6. Apply the plan, entry by entry, the way the calling skill builds: the failing tests first, then the smallest change, then the narrowest tests. Never fix pre-existing failures. A plan problem found while editing (an unexpected caller, a hit the plan missed, a test that passes before the fix) stops that entry: correct it, run the eight checks on it, then continue.
7. Update the ledger: fixed at file:line, or open with the reason. Your own copy also names each item's plan entry. The copy that goes into a reviewer brief carries no plan entry and no plan path (RULE).

## Round 1: full review
1. Facts first. Run the full test command, plus lint, typecheck and build where they exist, and the can-fail pass. If the calling skill ran them after its last edit, reuse those results instead. Mark each failure new or pre-existing (baseline). Re-run new or changed tests 3 times when they involve time, async, concurrency or randomness.
2. Write the brief once: `round<n>-brief.md` in your scratchpad directory (`mktemp -d` when there is no scratchpad), holding TASK, ACs, confirmed answers, sources, BASE, the file lists, the commands and the facts. Never the variant table or a fix plan.
3. Spawn the reviewers the size tier names, in parallel with the Agent tool, by subagent type, in the foreground (ONE TURN). Each prompt gives the brief's path, the scratchpad path for probe scripts, and the line "Read-only: never create, edit or delete files in the repository. The facts in the brief are final: do not run the suite, lint, typecheck, build or a mutation sweep." gap-hunter also gets the scenario checklist path. If a type is not installed, use general-purpose with the same prompt.
   - criteria-auditor: per AC, the implementing code and a test that would fail if it broke (YES / PARTIAL / NO); requirements in TASK that no AC covers; ACs not grounded in TASK, the confirmed answers, the sources or the code; ACs no finite check can verify; unrequested changes.
   - gap-hunter: every uncovered scenario and defect, ranked HIGH / MED / LOW, with every location of each one. No cap. It may prove a suspected defect with a small probe script in the scratchpad.
   - convention-checker: changed files and BASE; violations of CLAUDE.md (conventions, invariants, constraints), or of sibling files when CLAUDE.md is missing, each marked BLOCKING or MINOR. When the calling skill requires AC ids in test names, say so in the prompt so they are not reported.
4. Wait for all of them, then triage every finding:
   - MUST-FIX: an AC that is NO or PARTIAL; a TASK requirement no AC covers (add the AC, then build it); a HIGH or MED gap; a defect; a new test, lint, typecheck or build failure; a BLOCKING convention violation; an unrequested change (revert it).
   - OPTIONAL: LOW gaps and MINOR conventions. Fix them when the fix is small and in scope; otherwise list them.
   - DISMISS: only when the finding is factually wrong, citing the file:line that proves it. Never dismiss a failing test.
   - NEEDS DECISION: a correct finding whose fix would widen scope, change a public contract or add a dependency, and an AC no finite check can verify ("all corner cases"): ask the user to bound it. It is never a DISMISS. Ask it as a BLOCKING question, as the question round says; if it stays unanswered, leave it open.
5. Write every finding into the ledger: id (`R1-A2` for the auditor, `G` for gap-hunter, `C` for convention-checker), one-line finding, class, status. Note each AC the auditor marked YES.
6. Nothing MUST-FIX: the loop ends with PASS.
7. Otherwise run the fix plan, including OPTIONAL items you chose to fix.

## Round 2: re-check
1. Facts. Refresh the file lists and run the full suite, lint, typecheck and build again, because a fix can break something else. Run the can-fail pass on the lines the fixes changed.
2. Confirm each fix yourself, with evidence, before spawning anyone. Re-open the file:line of every MUST-FIX ledger item:
   - a gap or defect is fixed when a named test covers it and passes;
   - an AC is fixed when its code exists and a test kills the can-fail breaks of that code;
   - a convention item is fixed when a search over the change finds the pattern nowhere.
   Mark each item fixed or not fixed in the ledger, with that evidence. An item you cannot confirm this way stays with its reviewer (step 3).
3. Spawn only the reviewers the round needs, in parallel and in the foreground (ONE TURN):
   - gap-rechecker whenever the fixes changed production code, tests or docs. Fixes are where new defects come from, and it reviews every changed line, each fix included. It also gets the scenario checklist path;
   - criteria-auditor whenever an AC was added, changed or removed, or one of its items could not be confirmed in step 2;
   - convention-checker whenever the fixes created a file, or one of its items could not be confirmed in step 2.
   Record each skipped reviewer with its reason.
4. Write `round<n>-brief.md` with everything the round 1 brief held (never the variant table or a fix plan), the new facts, the ledger with your confirmations, PREV, and this scope:
   - Challenge any confirmation in the ledger whose evidence does not hold, with file:line. Re-check the items you raised that are marked not confirmed.
   - Review the delta, with your full method: `git diff --no-index "$PREV/<file>" <file>` for each file, and files that are not in PREV in full. Include the code that calls or depends on the changed lines.
   - Outside the delta, report only HIGH findings.
   - Do not report a DISMISS or OPTIONAL ledger item again unless its evidence is wrong; then say why.
5. Triage as in round 1, with one difference: a new MED or LOW finding outside the delta is OPTIONAL. List it; do not loop on it. A challenged confirmation is MUST-FIX again. Count gap-rechecker's FIX and MISSED origins, and each round-1 auditor YES that this round shows was wrong, for the record.
6. Then steps 5 to 7 of round 1.

## Round 3: only when needed
After the round-2 fixes, run round 2's steps 1 and 2: the facts, then your own confirmation of every round-2 MUST-FIX item. Then round 3's reviewers run only when at least one of these holds:
- (a) round 2 had a HIGH finding;
- (b) a confirmation was challenged in round 2 and re-fixed;
- (c) a round-2 fix changed production logic (not only tests, docs or comments) for a MED or higher item, and you cannot confirm it with a named passing test plus killed can-fail breaks on the changed lines.
When you are unsure whether one holds, it holds. Otherwise skip round 3, record `R3: skipped: <each trigger and the evidence that rules it out>`, and go to the verdict. When round 3 runs, it is round 2's steps 3 to 6.
LOW and OPTIONAL findings never trigger a round.

## Stop conditions
- At most 3 rounds.
- The last review is the last round whose reviewers ran, or the round-2 confirmation when round 3 is skipped. After it, the only edits allowed are test-only or doc-only fixes of LOW and OPTIONAL items. Any other open item stays unfixed and is listed with a one-line suggested fix, so nothing reaches the user unreviewed.
- Stop early with NEEDS REVIEW when a finding comes back unchanged after a fix, and say what you tried.

## Verdict
PASS = every AC YES, no TASK requirement uncovered, no HIGH or MED gap left inside the scope, no BLOCKING violation, no new failure, and nothing critical NOT RUN. Open NEEDS DECISION items don't block PASS, but they are always listed. Anything else is NEEDS REVIEW, with the open items listed.

## Record (one line per round, for the report)
`R<n>: tier [S|M|L], tests [pass/fail], can-fail [killed/survived open], reviewers [run | skipped: reason], ACs [YES/PARTIAL/NO counts], gaps [H/M/L], origin [FIX n / MISSED n] (round 2+), auditor YES overturned [n] (round 2+), conventions [blocking/minor] -> fix-plan check [entries / corrected / held back], fixed [...], confirmed [...], dismissed [...], open [...]`
`R3: skipped: <reason>` when round 3 does not run.
