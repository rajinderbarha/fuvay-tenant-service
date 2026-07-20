# Sensitive Capability Policy — Tenant Suspend / Reinstate / Terminate / Plan / Data-Delete

Workstream 3. Each capability below is described by what the **existing
code actually does today** (read directly from `app/engines/tenant_engine/service.py`),
not by what its name might imply. Where evidence is insufficient to assign a
canonical persona, the capability is marked `BLOCKED_PENDING_PRODUCT_DECISION`
rather than guessed at.

## TENANT SUSPEND

**What exists today:** exactly one implementation
(`TenantService.suspend_tenant`, lines 456–475). It sets
`tenant.status = "suspended"`, `is_discoverable = False`, broadcasts a
session-invalidation event, audits `tenant.suspended`, and publishes
`tenant.suspended`. There is no distinction in code between "tenant
voluntarily pausing," "platform compliance/risk suspension," "payment-failure
suspension," or "temporary marketplace unavailability" — it is a single
binary state transition with one `reason`/`reason_category` pair.

- **Tenant voluntarily pausing business operations** — no such feature exists
  anywhere in the codebase (searched `frontend/tenant-portal` for a
  pause/go-offline action; the only "pause" found is an unrelated webhook-pause
  feature in Settings, not a business-pause). **BLOCKED_PENDING_PRODUCT_DECISION**
  — this would be new product behavior, out of scope for this slice.
- **Platform suspension for compliance/risk/payment failure** — this IS what
  the existing endpoint implements. **PLATFORM_ADMIN_ONLY** (confirmed sole
  caller: `frontend/super-admin/lib/api.ts`'s `suspend()`, used from
  `admin/tenants/[id]/page.tsx` and `admin/customers` pages).
- **Temporary marketplace unavailability** — overlaps with `is_discoverable`,
  which this same endpoint also flips. No separate, narrower "hide from
  marketplace only" endpoint exists. **BLOCKED_PENDING_PRODUCT_DECISION** if a
  narrower capability is ever wanted.
- **Permanent account disablement** — that is `confirm_termination`, a
  separate endpoint (see TERMINATE below), not suspend.

**Initiator:** platform admin (via super-admin app). **Approver:** n/a (single
step). **Executor:** `TenantService.suspend_tenant`. **Confirmation:** a
`reason` string is required by the frontend call signature but not enforced
server-side as non-empty (unlike `reinstate_tenant`, which does require a
non-empty reason — an inconsistency worth noting, not fixing this slice).
**Audit:** yes (`tenant.suspended`). **Notification:** session invalidation
broadcast only; no customer/tenant-owner notification email/in-app message
found. **Reversibility:** yes, via `reinstate_tenant`. **Canonical endpoint:**
`POST /v1/tenants/{tenant_id}/suspend`. **Status:** implemented, working,
platform-admin-only in practice and in this slice's classification.

## TENANT REINSTATE

**What exists today:** `TenantService.reinstate_tenant` (line 477) reverses
suspension: requires the tenant to currently be `"suspended"`, requires a
non-empty `reason` (enforced in the router handler), sets status back to
`"active"`, restores `is_discoverable`. Only reverses the single suspend
mechanism above — there is no separate reinstatement path per suspension
"type" because no such types are distinguished in the suspend implementation
either. **PLATFORM_ADMIN_ONLY** (same caller evidence as suspend). Whoever
can suspend today is the only actor proven able to reinstate.

## TENANT TERMINATE

**What exists today:** a two-step pipeline, NOT a single action:
- `begin_termination` (line 492): sets a 14-day scheduled termination date in
  `tenant.meta`, does not change `tenant.status`, offers a data-export URL.
  Reversible in principle (nothing currently calls `confirm_termination`
  automatically — it requires the separate explicit second call).
- `confirm_termination` (line 508): sets `tenant.status = "terminated"`,
  `is_discoverable = False`. Docstring/response message states "Schema
  scheduled for deletion after 90-day backup" — **this scheduled deletion job
  was not found anywhere in the codebase** (searched for a Celery/cron task
  referencing tenant schema deletion; none exists). This is a genuine,
  pre-existing implementation gap, not something to fix this slice — see
  `known-limitations.md`.

Distinguishing the five behaviors the brief asks about:
- **Cancel plan** — is `downgrade_plan`/plan-cancellation, a different
  capability entirely (see PLAN MANAGEMENT below), not termination.
- **Close business account** / **Terminate platform tenancy** — this IS what
  `begin_termination`/`confirm_termination` implement (there is no separate
  "close business" vs. "terminate platform tenancy" distinction in code;
  they are the same action).
- **Deactivate marketplace listing** — overlaps with `is_discoverable`, same
  flag `suspend` also touches; no standalone listing-only deactivation route.
- **Permanently delete tenant data** — NOT implemented by `confirm_termination`
  itself (only sets a status flag; the "90-day backup then delete" language
  is aspirational/undelivered per the missing-job finding above). Actual data
  deletion, if it exists at all, is a separate, unconfirmed mechanism outside
  this router's scope.

**Disposition: PLATFORM_ADMIN_ONLY** for both `begin_termination` and
`confirm_termination` (sole caller: super-admin app). **The claimed 90-day
scheduled deletion is BLOCKED_PENDING_PRODUCT_DECISION / needs an engineering
gap-closure slice** — it is documented as a known limitation, not silently
assumed to work.

**Initiator:** platform admin. **Approver:** the second (`confirm`) call
itself functions as the approval gate for the first (`begin`). **Executor:**
`TenantService`. **Confirmation:** yes, two-step (begin → 14-day window →
confirm). **Audit:** yes, both steps. **Notification:** none found beyond the
audit log and the data-export URL surfaced in the `begin` response.
**Reversibility:** `begin` is implicitly reversible (nothing calls `confirm`
automatically); `confirm` is not reversible via this API surface (no
"un-terminate" endpoint exists). **Canonical endpoints:**
`POST /v1/tenants/{tenant_id}/terminate/begin`,
`POST /v1/tenants/{tenant_id}/terminate/confirm`.

## TENANT PLAN MANAGEMENT

**What exists today is exclusively platform-controlled tenant plan
administration** (`tenant.plan_type` + `PLAN_LIMITS` dict), NOT a
provider-facing package purchase flow. Confirmed by reading
`upgrade_plan`/`downgrade_plan`/`convert_trial` (lines 547–594): these
directly mutate `tenant.plan_type` and its associated hard limits
(`max_staff`, `max_active_jobs`, etc.) with no invoice, no payment gateway
call, no `TenantPackageAssignment` row created. This is a materially
different mechanism from the tenant/admin **package purchase** flow closed in
prior work (Slice L5-30, `TenantPackageAssignment`-based, invoiced,
duplicate-guarded) — the brief's instruction not to combine the two is
already true in the existing implementation; no code change was needed to
keep them separate.

- **View plan** — a separate, already-`TENANT_READ`-permission-gated GET
  endpoint, not touched, not ambiguous.
- **Purchase package** — the `TenantPackageAssignment` flow (Slice L5-30),
  entirely separate from this router.
- **Upgrade/downgrade platform-controlled tenant plan** — this IS what
  `upgrade_plan`/`downgrade_plan`/`convert_trial` implement.
  **PLATFORM_ADMIN_ONLY** (sole caller: super-admin app's `upgradePlan`/
  `downgradePlan`/`convertTrial`).
- **Cancel subscription** — no distinct cancel endpoint found; `downgrade_plan`
  can move a tenant to the lowest tier but does not cancel/terminate billing.
  **BLOCKED_PENDING_PRODUCT_DECISION** if a true cancellation flow is wanted.
- **Modify plan definitions** — the `PLAN_LIMITS` dict itself is a hardcoded
  Python constant, not modified by any of these endpoints or any admin UI
  found. Not in scope, no endpoint exists for it.

**Initiator:** platform admin. **Confirmation:** `upgrade_plan` requires a
non-empty `reason` string (enforced); `downgrade_plan`/`convert_trial` do
not. **Audit:** yes for all three. **Notification:** none found.
**Reversibility:** `upgrade`/`downgrade` are mutually reversible by calling
the other; `convert_trial` (trial → active) has no reverse endpoint.
**Canonical endpoints:** `POST /v1/tenants/{tenant_id}/plan/upgrade`,
`/plan/downgrade`, `/trial/convert`.

## TENANT DATA DELETE

**What exists today:** `TenantService.request_gdpr_deletion` (line 852) is a
**request-creation action only** — it writes one audit-log entry
(`data.gdpr_deletion_requested`) and returns a message claiming "PII will be
anonymized within 72 hours." **No anonymization job, scheduled task, or
execution mechanism was found anywhere in the codebase** that this request
triggers. This is a genuine, pre-existing implementation gap: the endpoint
records intent, nothing currently executes it.

Distinguishing the six behaviors the brief asks about:
- **DPDP erasure request creation** — this IS what the endpoint implements.
- **Approval of an erasure request** — no approval step exists; the request
  is unconditionally accepted and audited with no review gate.
- **Immediate destructive deletion** — NOT implemented; confirmed no
  synchronous deletion of any row occurs in this method.
- **Scheduled deletion** — claimed in the response message, NOT implemented
  (no job found).
- **Anonymization** — claimed in the response message, NOT implemented (no
  job found).
- **Platform-admin execution** — whatever execution eventually happens (if
  anything does) is not visible in this codebase; cannot be classified.

**Disposition: PLATFORM_ADMIN_ONLY** for the existing request-creation
endpoint (sole caller: super-admin app's `deleteRequest`-style call at
`frontend/super-admin/lib/api.ts:505`). **The actual anonymization/deletion
execution is BLOCKED_PENDING_PRODUCT_DECISION and separately
BLOCKED_PENDING_ENGINEERING (no implementation exists)** — this is the most
significant honest finding of this slice's Workstream 3 review and is
escalated in `product-decisions-required.md`. This slice does **not** grant
`tenant:data:delete` to `tenant_owner` — doing so would let a tenant self-
trigger a request-creation action whose downstream execution is unverified,
which is exactly the kind of ungrounded grant the brief prohibits.

**Initiator:** platform admin today (confirmed caller). **Approver:** none
(no approval step in code). **Executor:** unknown/unimplemented. **Required
confirmation:** a `reason` string, not enforced non-empty server-side.
**Audit:** yes, request-creation only. **Notification:** none found.
**Reversibility:** n/a (nothing executes yet). **Data-retention:** the
response message claims "Financial records retained 7 years for GST
compliance" but this is a static string, not a policy enforced by any
retention job found in this codebase. **Canonical endpoint:**
`POST /v1/tenants/{tenant_id}/data/delete-request`.

## Summary table

| Capability | Existing implementation scope | Disposition |
|---|---|---|
| Suspend (compliance/risk) | Single binary suspend | PLATFORM_ADMIN_ONLY |
| Suspend (voluntary pause) | Does not exist | BLOCKED_PENDING_PRODUCT_DECISION |
| Reinstate | Reverses the single suspend mechanism | PLATFORM_ADMIN_ONLY |
| Terminate (begin/confirm) | Status + schema-deletion claim (job missing) | PLATFORM_ADMIN_ONLY; scheduled-deletion job gap flagged |
| Cancel subscription | Does not exist distinctly from downgrade | BLOCKED_PENDING_PRODUCT_DECISION |
| Plan upgrade/downgrade/convert | Platform-controlled tenant.plan_type | PLATFORM_ADMIN_ONLY |
| Modify plan definitions | Hardcoded constant, no endpoint | N/A — not exposed |
| GDPR deletion request | Audit-log entry only, no execution | PLATFORM_ADMIN_ONLY; execution gap flagged (BLOCKED_PENDING_ENGINEERING) |
