# Scenario Coverage Checklist

Used for test planning (build), gap hunting (the validation loop), and question generation (interview).

RULE: every category below must end as APPLICABLE (concrete scenarios, each mapped to a named test)
or N/A (an N/A names the grep or file that proves it, e.g. "no logging touched: grep `logger` over the changed files returns 0 hits"; "not relevant" is not a reason).
A blank, or an N/A without that proof, counts as a failure.
Choose the lowest test level (unit, then integration, then e2e) that can actually catch the scenario.
Mirror the repo's existing test layout, naming, fixtures and helpers.

1. Behavior - each acceptance criterion; alternative valid inputs; documented examples.
2. Inputs and boundaries - empty/null/missing; min/max/off-by-one; wrong type/format/encoding; unicode; very large; duplicates; ordering.
   Syntactic variants of every accepted or emitted format, each its own scenario: quoting (single, double, none, escaped); whitespace (leading, trailing, inside, tabs, none); case; Unicode normalisation (NFC/NFD) and lone surrogates; encodings; line endings (LF, CRLF, CR, none at EOF); path forms (`..`, `./`, absolute, trailing slash, symlink, non-canonical); empty; huge; nested or indented forms.
3. Errors and failure - invalid-input handling; dependency failure, timeout, partial failure; retries and idempotency; error messages/status codes; resource cleanup on failure.
4. State and data - persistence round-trip; migrations and pre-existing rows/data; transactions/rollback; concurrency/races; caching/invalidation; time (timezones, DST, expiry, clock).
5. Security and permissions - authn/authz per role; user/tenant isolation; injection/escaping at trust boundaries; secrets or PII in logs and errors.
6. Integration and contracts - every caller of changed code (grep, do not guess); public API/schema/CLI/flag compatibility; event/queue payloads; config, env and feature-flag defaults.
7. Non-functional - realistic-size performance (N+1, unbounded loops); memory; logging/metrics; UI/i18n/a11y if UI is touched.
8. Regression and test quality - full suite vs baseline; characterization tests for untested legacy code being modified; every new test can fail (the can-fail pass leaves no survivor in changed code without a reason it cannot change behavior); no dependence on order, wall-clock time, network or shared state; tests touching async/time/random run 3x; no vacuous test: a test whose scenario finds zero items (no commands, no rows, no matches) must fail, not pass.
9. Consistency and fidelity - every claim in comments, docs, messages or the deliverable matches the code and the sources; no two statements on one subject disagree; one name per concept; every closed set (states, statuses, exit/error codes, commands, options) is complete: each value defined, reachable and handled one way for every event.
10. Rollout and operations - deploy order; feature flag and its default; rollback path and a test of it; partial deploy and mixed versions; config drift; runbook and alerting; who is paged.
11. Compliance and audit (only when the task touches access control, logging, retention or change management) - least privilege; audit trail; retention; change evidence for SOC 2 Type II; framework alignment through CIS Controls or NIST CSF.