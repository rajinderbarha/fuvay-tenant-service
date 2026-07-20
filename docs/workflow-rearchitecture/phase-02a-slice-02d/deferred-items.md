# Deferred Items — Slice 2D

## Architecture completion work (the two real gaps this slice identified)
1. **Wire `StaffPermission` overrides into live authorization** — either JWT-embedding at login (consistent with existing `role`/`access_scope` patterns) or a per-request DB lookup (adds latency). This unblocks the manager persona.
2. **Extend `require_tenant_mutation_permission` coverage** from 2 to all ~16 tenant mutation routers, with per-file review to distinguish true mutations from read/preview endpoints. This unblocks the read-only persona.

## Account remediation
`readonly@demo-ac-services.local` — pending the product decision described in `affected-account-final-disposition.md`. The remediation script is ready; only a decision is needed.

## Migration 144
Apply once `readonly@` is resolved. No further migration engineering needed — proven correct twice now (Slice 2C with 2 blockers, Slice 2D with 1).

## Session revocation completeness
Add Redis revocation-key writing to the remediation script before it's ever used on an account with live sessions.

## Intelligence KB
Frontend label update ("Allowed Roles" → something explicitly non-authoritative) — low-risk, cosmetic, deferred to a frontend-focused slice.

## Health/integrity guard
Consider whether a lightweight, count-only version of `check_role_integrity.py`'s check belongs in an existing health/readiness endpoint — not investigated this slice.

## Not in scope for any future slice unless separately approved
Admin My Work, Tenant My Work, Next-Action aggregation, guided workflows, booking-pipeline work, page redesign, visual redesign — none touched, consistent with every prior slice.

## Recommended next slice
Given this slice found the manager/read-only blockers are both real, bounded, engineering-completion gaps (not open product questions), the highest-value next slice is likely: **close the `StaffPermission` wiring gap** (smaller of the two — one code path, the auth dependency chain) and re-run this slice's `TestEffectiveAccessBaseStaffBundle` regression guards, which are deliberately designed to fail loudly the moment that gap closes, prompting an update to `tenant-access-model.md` and potentially unblocking a real manager-persona remediation for a *future* demo/real account (not necessarily `manager@demo-ac-services.local`, which was already resolved by disabling).
