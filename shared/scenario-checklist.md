# Scenario Coverage Checklist

Used for test planning (build), gap hunting (validate), and question generation (interview).

RULE: every category below must end as APPLICABLE (concrete scenarios, each mapped to a named test)
or N/A (a one-line reason grounded in the code or task, e.g. "no persistence touched: no DB imports in diff").
A blank, or an N/A without a reason, counts as a failure.
Choose the lowest test level (unit, then integration, then e2e) that can actually catch the scenario.
Mirror the repo's existing test layout, naming, fixtures and helpers.

1. Behavior - each acceptance criterion; alternative valid inputs; documented examples.
2. Inputs and boundaries - empty/null/missing; min/max/off-by-one; wrong type/format/encoding; unicode; very large; duplicates; ordering.
3. Errors and failure - invalid-input handling; dependency failure, timeout, partial failure; retries and idempotency; error messages/status codes; resource cleanup on failure.
4. State and data - persistence round-trip; migrations and pre-existing rows/data; transactions/rollback; concurrency/races; caching/invalidation; time (timezones, DST, expiry, clock).
5. Security and permissions - authn/authz per role; user/tenant isolation; injection/escaping at trust boundaries; secrets or PII in logs and errors.
6. Integration and contracts - every caller of changed code (grep, do not guess); public API/schema/CLI/flag compatibility; event/queue payloads; config, env and feature-flag defaults.
7. Non-functional - realistic-size performance (N+1, unbounded loops); memory; logging/metrics; UI/i18n/a11y if UI is touched.
8. Regression and test quality - full suite vs baseline; characterization tests for untested legacy code being modified; every new test can fail (mutation spot-check); no dependence on order, wall-clock time, network or shared state; tests touching async/time/random run 3x.
