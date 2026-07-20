# Manual Role Decision Request

Formal decision request per Workstream 9. **Migration 144 must not be
executed against any database containing these two rows until a human
approves a mapping (or explicit deactivation) for each, recorded in a
committed decision artifact.**

## Account 1

- **Account:** `manager@demo-ac-services.local`
- **User ID:** `72640932-ef3c-4ce5-92a1-6609bff35ee0`
- **Current invalid role:** `tenant_manager`
- **Tenant:** demo-ac-services (`5209ef33-a53e-4fc0-b3f6-006335b8d712`)
- **Observed use case:** none (zero logins/sessions/audit activity ever) —
  appears to be an inert demo-seed artifact, not an in-use account
- **Candidate canonical roles:**
  - `staff` — plausible given `full_name`, no elevated risk (staff is the
    lowest-privilege tenant-scoped operational role); **recommended if
    confirmed**
  - Deactivate instead (no role assignment needed if the account is
    simply retired)
- **Privileges of `staff`:** tenant-scoped operational permissions per
  `ROLE_PERMISSIONS['staff']`; no platform-admin or cross-tenant capability
- **Security risk of `staff` mapping:** low — matches the apparent intent,
  and the account has never logged in, so no behavior change for any real
  user
- **Recommended mapping:** `staff`, **contingent on human confirmation**
  that this demo account is intended as a non-owner tenant staff user
- **Evidence strength:** weak (name-similarity only) — insufficient to
  execute without confirmation
- **Exact human decision required:** "Confirm `manager@demo-ac-services.local`
  is intended as a `staff`-role demo account for tenant demo-ac-services,
  or specify it should be deactivated instead."

## Account 2

- **Account:** `readonly@demo-ac-services.local`
- **User ID:** `05deaee8-03f2-40f9-8af6-2f21892c075f`
- **Current invalid role:** `tenant_readonly`
- **Tenant:** demo-ac-services (same tenant as Account 1)
- **Observed use case:** 7 real logins, 7 currently-unrevoked sessions,
  zero mutation/action of any kind ever recorded (consistent with a role
  that grants no permissions)
- **Candidate canonical roles:**
  - `staff` — the only real option among the 10 canonical roles, but
    grants materially broader access than "read only" implies
  - No mapping; build a genuine tenant-side read-only role in a future
    architecture change
  - Deactivate the account and have its user re-request access properly
- **Privileges of `staff`:** as above — a real capability grant, not a
  no-op, for an account with 7 real logins
- **Security risk of `staff` mapping:** **moderate** — unlike Account 1,
  this account is actively used by someone; granting `staff` would be a
  real, immediate capability increase for a real (if unidentified) user,
  based only on the assumption that "whoever logs in as readonly@ would be
  fine with staff-level access" — not evidenced
- **Recommended mapping:** none — this is a product-architecture question,
  not a mapping decision this investigation can responsibly recommend
- **Evidence strength:** none for any specific role (usage proves the
  account matters to someone; it proves nothing about which role they need)
- **Exact human decision required:** "Does ServiceOS need a genuine
  tenant-side read-only role? If yes, that role does not exist today and
  must be designed separately (out of this slice's scope — no new roles
  may be added here). If no, specify whether `readonly@demo-ac-services.local`
  should be mapped to `staff` (accepting broader access than the name
  implies) or deactivated (with its real user notified/re-onboarded)."

## Slice 2F-38's own action

**None.** No mapping was applied to either account, seed file, or fixture.
Both remain `MANUAL_ROLE_CONFIRMATION_REQUIRED`. This slice's role
migration readiness stops at `ROLE_REMEDIATION_POLICY_BLOCKED`.
