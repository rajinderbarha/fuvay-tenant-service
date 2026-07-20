# Manual Job Creation Policy

## Who may create manual Jobs

**Security rule** (enforced, unchanged this slice): `require_tenant_mutation_permission(P.TENANT_UPDATE)`
— `tenant_owner` and `super_admin` (per `ROLE_PERMISSIONS`'s existing `TENANT_UPDATE` grant,
unmodified). `staff`/`technician` do **not** hold `TENANT_UPDATE` and are denied by the existing
permission grant (re-confirmed, not modified — see Slice 2F-14D's own regression, which re-runs
the full Slice 2F-14B authorization suite).

- **Canonical staff may create them**: **No** — not supported by current permission policy.
- **Technician may create them**: **No** — same reasoning.

## How customer is selected

**Proven operational policy**: an existing `customer`-role account's `customer_id` may be
supplied directly by the creating `tenant_owner`/`super_admin` — see customer-authority.md
(`PROVIDER_SELECTED_EXISTING_CUSTOMER`). No search/lookup UI exists or was built (out of scope);
the caller is assumed to already know the customer's ID (e.g. from an out-of-band phone
call/walk-in, or from a booking/parent-job reference, in which case it's cross-checked, not
independently selected).

## Whether customer consent is recorded

**Not recorded** — no consent field or workflow exists anywhere in `Job`/`create_job`. This is a
**product decision**, not a security gap; no consent infrastructure was built (explicitly out of
scope: "Build a new manual-customer onboarding flow").

## Whether an existing booking is required

**No** — `booking_id` is optional (see supported-creation-modes.md's `MANUAL_PROVIDER_JOB` mode).

## Whether service type is required

**Yes** — `service_type_id` is a required field in the request contract (though an empty string
is technically accepted and bypasses ownership validation — see known-limitations.md).

## Whether address is free-form

**Yes** — `address` is an unvalidated JSONB dict (city/pincode/lat/long), not a normalized
`address_id` reference (confirmed in Slice 2F-14C, unchanged). No address normalization was
built (explicitly out of scope).

## Initial status / assignment / duplicate behavior / audit actor / customer notification

- **Initial status**: always `JS.DRAFT`, regardless of creation mode (see create-job-contract.md).
- **Assignment behavior**: none — assignment happens exclusively via the separate `assign_job`
  route.
- **Duplicate behavior**: not applicable to the pure-manual mode (no source record to duplicate
  from); see duplicate-idempotency-policy.md for the booking/parent-sourced modes.
- **Audit actor**: `JobStatusHistory.changed_by`/`changed_by_role` are always server-derived from
  `self.actor_id`/`self.actor_role` (the authenticated principal) — never client-supplied,
  unchanged from pre-existing `_write_history` behavior.
- **Customer notification**: none fires from `create_job` itself (only a domain event,
  `job.created`, is published — not a directly observed user-facing notification in this
  codebase).

## Separation of security rules vs. product decisions

| Rule | Type |
|---|---|
| Only `tenant_owner`/`super_admin` may create | Security rule (enforced) |
| Any real customer account may be selected, no prior relationship required | Proven operational policy (see customer-authority.md) |
| No consent recording | Product decision (not built, out of scope) |
| No address normalization | Product decision (not built, out of scope) |
| Booking/parent optional | Proven operational policy (multiple creation modes coexist) |
