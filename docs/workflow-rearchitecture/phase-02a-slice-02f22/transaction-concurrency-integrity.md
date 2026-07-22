# Transaction and Concurrency Integrity — Slice 2F-22

## Traced sequence

| # | Step | Location | Writes? |
|---|---|---|---|
| 1 | Package lookup | `_load_package` | no |
| 2 | Tenant validation | `_tenant_id(user)` (JWT) | no |
| 3 | Price calculation | read of `pkg.*` fields | no |
| 4 | Payment-authority gate (2F-22) | `create_package_assignment` | no |
| 5 | Existing-purchase lookup | duplicate guard SELECT | no |
| 6 | Assignment creation | `db.add()` + `flush()` | **yes** |
| 7 | Payment-state assignment | `status` / `paid_at` set in constructor | yes (same row) |
| 8 | Credit / entitlement issuance | **not in this path** — activation only | n/a |
| 9 | Ledger update | **not in this path** | n/a |
| 10 | Commit | handler `await db.commit()` | yes |
| 11 | Notification / event dispatch | **none emitted by this route** | n/a |

## Verification against each requirement

- **One coherent transaction** — yes. Service flushes; handler commits. No
  intermediate commit exists inside the service method.
- **No credit issued before payment state is valid** — vacuous here and
  therefore safe: this route issues no credit at all. Credits are gated on
  admin activation.
- **Concurrent requests cannot issue duplicate credits** — confirmed via two
  independent guards: activation selects `LIMIT 1`, and `verify_tenant` is
  one-shot per tenant, so activation cannot run twice.
- **Commit failure leaves no active entitlement** — yes; nothing in this path
  activates, and an uncommitted transaction leaves no row.
- **Ledger failure rolls back balance changes** — not applicable to this path
  (no ledger write). Unchanged in the activation path, where `credit_wallet`
  participates in the caller's transaction.
- **Notification not emitted before persistence** — vacuous: this route emits
  no notification.
- **No partial paid purchase without corresponding state** — a paid row can
  now only be created by an authoritative caller, and its status/`paid_at`
  are set in the same constructor call as the rest of the row, so the row is
  never half-paid.

## Known concurrency gap (honest disclosure)

The duplicate guard is SELECT-then-INSERT with no unique constraint and no
lockable row, so two simultaneous identical requests can both create a
`pending_review` assignment. Full analysis, blast radius, and why it cannot
duplicate benefits: `duplicate-idempotency-policy.md`.

Not fixed here — the correct fix is a partial unique index, which requires a
migration this slice is prohibited from adding.

## Live two-session integration testing

**Environment exclusion.** Two-session concurrency tests require a live
PostgreSQL instance, which is unavailable in this environment (every
DB-backed test in the repository fails with `ConnectionRefusedError` /
`httpx.ConnectError` — the long-standing baseline). Instead, the concurrency
behaviour is established by deterministic source-level reasoning above and
recorded as a residual limitation rather than claimed as verified. No
concurrency claim in this slice rests on an unrun test.
