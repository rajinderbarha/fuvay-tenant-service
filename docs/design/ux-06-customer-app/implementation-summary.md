# UX-06 Customer App — Implementation Summary (Round 1)

**Status: CUSTOMER_APP_DESIGN_PARTIAL — foundational audit + API/auth contract
correction round. Substantial screen/navigation/DeepSeek-UI work remains and is
honestly deferred (see deferred-items.md, known-limitations.md).**

## What this round did

1. Verified the worktree/branch lineage (`design/ux-06-customer-app` traces to
   `50840acc91622bad7729a02fc602a65a911f407b` on master) before starting — no
   concurrent-worktree interference detected.
2. Audited the existing `mobile/customer-app` scaffold in full
   (existing-customer-app-audit.md) rather than assuming the brief's description of
   the starting point was accurate — it wasn't (no i18n framework, no design-system
   tokens folder found).
3. Confirmed the backend (`http://localhost:8000`) is live and pulled its real
   `openapi.json`, then cross-checked every endpoint group in the existing
   `src/lib/api.ts` against it. Found the client called ~15 nonexistent endpoint
   paths (fake customer OTP auth, fake categories/addresses/settings/help/payments
   paths, the legacy dead `/v1/reviews` route).
4. Rewrote `src/lib/api.ts` to the real, verified endpoint surface
   (`/v1/customer/*`, `/v1/me/*`, `/v1/customers/me/addresses`, unified
   `/v1/auth/login`), keeping the Booking/field_ops.Job pipeline
   (`bookingsApi`) and ServiceBooking/ServiceJob pipeline (`serviceJobsApi`)
   as separate exports per the canonical domain rule.
5. Corrected `AuthContext.tsx` and rewrote `LoginScreen.tsx` to the real
   email/password contract, removing a two-endpoint fake phone/OTP flow rather
   than shipping a dead control.
6. Documented the DeepSeek AI-chat contract finding (two live session-based
   engines, only one's route shapes confirmed, full request schema unconfirmed) —
   no chat UI was built against an unverified schema, avoiding a repeat of the
   "claim without evidence" failure mode called out in the brief.
7. Confirmed zero changes to `app/`, `frontend/*`, and `mobile/staff-app`
   (`git diff --stat` against baseline is empty for those paths).
8. Committed the correction as a single, described commit
   (`0775bb5` at time of writing — see final hash below).

## What this round explicitly did not do (see deferred-items.md)

Screen rewiring for the six now-typecheck-broken screens, DeepSeek chat UI,
booking submission workflow, IA/navigation build-out, typed view-model/adapter
layer, theme/accessibility pass, fresh WSL install+typecheck+test+build
verification, and any live Playwright browser proof. This was a single,
narrowly-scoped foundational round given the size of the remaining brief;
subsequent rounds should build on the corrected `api.ts`/auth layer rather than
repeat this audit.

## Final state

- Branch: `design/ux-06-customer-app`
- Worktree: `G:\serviceos-ux06-customer-app`
- Files changed: `mobile/customer-app/src/lib/api.ts`,
  `mobile/customer-app/src/context/AuthContext.tsx`,
  `mobile/customer-app/src/screens/LoginScreen.tsx`,
  plus this `docs/design/ux-06-customer-app/` doc set.
- No backend, no other frontend app, touched.
