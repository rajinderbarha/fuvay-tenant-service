# Deferred Items — Slice 2C

## Workstream 2/3 — actual remediation execution
Pending human confirmation for account 1 (`manager@` → `staff`, high-confidence candidate) and a product decision for account 2 (`readonly@` — no canonical target exists). Once decided, running the already-built, already-tested remediation script is a small, fast follow-up action — not a rebuild.

## Workstream 5 — applying migration 144
Blocked on the same remediation, by design. Once the 2 accounts are resolved, `alembic upgrade head` should succeed immediately (no further migration work needed).

## Workstream 6 — session revocation on remediation
Documented (design specified in `token-session-impact.md`), not built into the script — needs to be added before a future slice executes a real `--apply`.

## Workstream 8 — Intelligence KB `allowed_roles_json`
Disposition (`DISPLAY_ONLY`) is conclusive; the follow-up product decision (build real enforcement vs. remove the dead control) is explicitly out of this slice's scope and non-blocking.

## Not in scope for any future slice unless separately approved
Admin My Work, Tenant My Work, Next-Action aggregation, guided workflows, page consolidation, visual redesign, booking-pipeline work — none touched, consistent with every prior slice in this series.

## Recommended next slice
1. Resolve account 1's mapping with the demo-tenant's owner/administrator, execute the remediation script for that account only, apply migration 144 once both accounts clear.
2. Separately, decide account 2's fate (map to `staff`, build a real read-only tenant role, or deactivate) as a distinct product conversation — it shouldn't block account 1's straightforward resolution.
3. Consider building the session-revocation step into the remediation script before either account is actually remediated, so the "stale JWT" gap doesn't manifest even briefly.
