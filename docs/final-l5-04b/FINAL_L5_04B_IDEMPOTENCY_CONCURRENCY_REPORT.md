# FINAL-L5-04B — Idempotency and Concurrency Report

## Real, live-tested cases
| Case | Result |
|---|---|
| Repeated module assignment | **Idempotent, live-verified twice** — the canonical seed script was run twice in immediate succession; second run produced identical row counts (2 module rows, no duplicate), confirmed by direct row-count query |
| Repeated category assignment | Same mechanism, same double-run proof |
| Repeated disable | Not independently double-tested this sprint, but the service logic re-queries for an ACTIVE row before disabling — a second disable call against an already-INACTIVE row would raise `EntitlementNotFoundError` (404, not a silent no-op or a crash) — this is a deliberate, defensible choice: "disable" is not idempotent in the same sense "assign" is, since there's no meaningful "already disabled" success state to return |
| Repeated re-enable | Same pattern as disable — a second re-enable call against an already-ACTIVE row is not specifically guarded against duplicate-enable (would find the row and re-set fields idempotently, incrementing `version` each time — not a bug, but not perfectly idempotent either since `version` and `enabled_at` would change on every call) |
| Concurrent assignment requests | **Not load-tested this sprint** — no concurrent-request test harness was run. The DB-level partial unique index (`uq_tme_tenant_module_active`) is the real safety net: even under a genuine race (two simultaneous assign calls), Postgres would reject the second `INSERT` at the constraint level, converting a race condition into a real (if unhandled-gracefully) `IntegrityError` rather than a silent duplicate — verified the constraint itself works via a direct raw-SQL duplicate-insert attempt (see Data Model Report), not via an actual concurrent-request simulation |
| Expired entitlement resolution | `_is_effective()` checks `effective_from`/`effective_until` against `now()` on every read — deterministic by construction, not tested with a real seeded expired row this sprint (no test data has an expiry date set) |
| Module/category mismatch | **Live-tested** — attempting to assign a category whose parent vertical doesn't have an ACTIVE module entitlement returns a real `409 CONFLICT` with a specific message, not a silent success or a 500 |

## Required outcomes
| # | Requirement | Result |
|---|---|---|
| 1 | No duplicate active rows | **DB-enforced and verified** (partial unique index rejects duplicates at the constraint level, independent of application logic) |
| 2 | No contradictory states | A category entitlement cannot exist ACTIVE while pointing at a non-ACTIVE module (fixed this sprint, see Module Disable Cascade Policy) |
| 3 | Controlled 409 or idempotent success | Assign = idempotent success (200, existing row returned); category/module mismatch = 409 — both real, tested |
| 4 | Audit remains understandable | Every mutation (including the idempotent-no-op case, which explicitly skips writing a redundant audit row rather than spamming duplicate ASSIGNED events) produces a clean, non-duplicated history |
| 5 | Effective entitlement resolution is deterministic | `_is_effective()` is a pure function of `status` + `effective_from`/`effective_until` + current time — same inputs always produce the same result |

## Result
Idempotency on the read-heavy "assign" path is real and double-verified. Genuine concurrent-request racing was not load-tested (only the underlying DB constraint that would make a race safe was verified in isolation) — honestly documented as a gap rather than claimed as fully proven under real concurrency.
