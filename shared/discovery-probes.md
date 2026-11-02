# Discovery Probes

Used by plan-task. Every probe gets an answer from one of four sources: a question for the user; "resolved by code" with file:line and the quoted line; a quote from the task text; or "N/A" with the grep or file that proves it. A bare "resolved by code", or an N/A without that proof, counts as unanswered. The DP prefix keeps these numbers apart from the scenario checklist's.

## Core probes
- DP1 Intent and scope: outcome per consumer in one sentence; what must not change; explicit non-goals; who is affected that the task does not name; how success is measured; deadline or rollout constraint.
- DP2 Behavior and edge cases: invalid, empty, absent, duplicate and oversized input; ordering; first run, nth run, run twice, run concurrently, run after a crash; partial completion; clocks and time zones; every closed set against every event.
- DP3 Contracts: every public surface touched; required versus optional; defaults; versioning; backward and forward compatibility; mixed versions during rollout; error shape; docs and examples.
- DP4 Data and state: what is stored; existing data in old shapes; migration and backfill; reversibility; references between objects; deletion and retention; caches; transactions.
- DP5 Dependencies and sequencing: later tasks that rely on this; external systems and their limits, outages and versions; flags; rollout order; owner of each dependency.
- DP6 Non-functional: realistic data size; latency and cost; permissions per role; tenant isolation; secrets and PII in logs; observability for failure and success.
- DP7 Verification: how each AC is proven; test level; data and environments; untestable parts and the substitute check (a validation command whose exit code fails when the AC is violated; see verification-profiles.md); the command that proves done.
- DP8 Conventions and constraints: two sibling patterns to follow, named; files not to touch; style and comment rules; generated files; dependencies not allowed.
- DP9 Design, for a new project or subsystem only: stack, structure, modules, import direction, interfaces, configuration, invariants, build and test commands.
- DP10 Operations and rollout: deploy order; flag and default; rollback path and its test; partial deploy; config drift; runbook and alerting; who is paged.
- DP11 Compliance and audit, only when the task touches access control, logging, retention or change management: least privilege; audit trail; retention; change evidence for SOC 2 Type II; framework alignment through CIS Controls or NIST CSF.

## Extras by task type
- Bug fix: reproduce first; root cause versus symptom; sibling sites by every spelling of the pattern; a regression test that fails before the fix; data already damaged by the bug.
- Data migration: dry run; batching and locks; backfill order; dual-write window; rollback and its test; row counts before and after; downtime.
- Contract change: deprecation path; auth; pagination; idempotency keys; rate limits; consumers outside the repo.
- New project: stack constraints; the test command first; CI; ownership; what the skeleton step contains.
- Tenant or cloud change: report-only or pilot group first; break-glass exclusions; licence prerequisites; per-tenant blast radius; audit log evidence; rollback.

## Answers, valid and invalid
- Valid: "DP4 existing rows: resolved by code, src/db/models.py:41 `email = Column(String, nullable=True)`, so old rows can hold NULL and AC-3 must cover it" (the line, the quote and the effect).
- Invalid: "DP4 existing rows: resolved by code, see models" (no line, no quote, no effect).
- Valid: "DP6 secrets in logs: N/A, no logging touched: grep `logger` over the changed area returns 0 hits" (names the proof).
- Invalid: "DP6 secrets in logs: N/A, not relevant" (no proof).
