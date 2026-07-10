# HS4 — Remaining Blockers

1. **Real bug found: `POST /v1/provider/status/refresh` is a complete
   stub.** `app/engines/provider_portal/router.py::refresh_provider_status`
   returns `{"refreshed": True}` without performing any computation —
   confirmed via source read and live verification (published a real
   service, called refresh, `GET /v1/provider/status` still showed
   `is_visible: false`, `is_bookable: false`, `last_evaluated_at: null`,
   unchanged from before the publish). No `compute_bookability`/
   `evaluate_status`-style function was found anywhere in the codebase
   for this specific tenant-level status object. A separate,
   offering-level table (`provider_offering_bookable_statuses`, read by
   `GET /status/offerings`) may be computed by a different mechanism
   (not investigated this sprint) — but the tenant-level summary this
   sprint's ticket cares about ("Bookability status must update only
   when all required checks pass") does not actually update. **Not
   fixed this sprint** — the real computation logic doesn't exist to
   wire up; building it is a larger task than this sprint's remaining
   budget.
2. **UI does not match the ticket's literal 5-step wizard
   presentation** — functionally equivalent (all 5 conceptual steps are
   covered) but not structured as a step-indicator wizard. Pre-existing
   architecture, not changed this sprint.
3. **Publish readiness covers only 4 of the ticket's 9 requirements**
   (types, type pricing, brand pricing completeness, service area) — no
   check for business profile, availability, usage credits, or security
   deposit at publish time.
4. **No permission-aware UI on the frontend** — backend enforces
   `P.TENANT_UPDATE`, but the wizard doesn't hide Publish/Save for
   read-only users.
5. **Setup checklist live-update not independently re-verified** —
   given finding #1, it's likely the checklist's bookability-dependent
   items also don't reflect a real publish, though this wasn't
   separately tested (the checklist page itself wasn't loaded this
   sprint).
6. **`npm run build`/`lint`/`test` not run** — established constraint,
   `tsc --noEmit` used as gate.

## What is solid (re-confirmed, not newly broken)
- Type-dependent brand pricing: fixed in a prior sprint, re-verified
  intact (29/29 tests passing).
- Provider price boundary validation: enforced server-side, live-
  verified with real 422 responses and correct `request_id`s this
  sprint.
- Publish itself works and updates `setup_status`/`published_at`
  correctly for the checks it does perform.
- 0 forbidden labels, 0 old duplicate pages/menu items, TypeScript
  clean, 142/142 existing tests passing.

## Why this sprint's finding matters
Bug #1 is the most significant discovery this sprint — it means the
tenant-facing bookability/visibility status shown after setup may be
silently stale, which could confuse business owners about whether their
service is actually live for customers, even though the underlying
`TenantService.setup_status` correctly says "published." This is a real,
previously-undocumented gap in the Home Services setup flow's
observable feedback loop.
