# Remediation Decision Register

## Account 1 — manager@demo-ac-services.local (role: `tenant_manager`)

**Disposition: MANUAL_ROLE_CONFIRMATION_REQUIRED**

Why not `SAFE_AUTOMATIC_REMAP`: the only available evidence is the account's `full_name` ("Tenant Manager") and email local-part ("manager"). The brief explicitly states "do not map tenant_manager automatically to staff" and "do not make a replacement based only on the string containing 'role'" (extended here to include name-similarity generally) — this account's evidence is *exactly* that prohibited category and nothing else. No login, no session, no audit record, no team-member profile, no assigned work exists to corroborate or contradict a `staff` mapping. Automatic remapping would be a decision made purely on naming convention, which is precisely what this slice is instructed not to do.

Why not `DISABLE_PENDING_REVIEW`: the account presents no security risk (zero logins, zero sessions, zero permissions already) — disabling an already-completely-inert account adds no safety benefit and is itself a data mutation not clearly justified by risk.

Why not `NO_ACTION_PENDING_EVIDENCE`: unlike account 2, there IS a plausible, low-risk candidate mapping (`staff`) once a human confirms intent — the situation is "needs one human decision," not "structurally unmappable." `MANUAL_ROLE_CONFIRMATION_REQUIRED` reflects that a decision is pending, not permanently blocked.

**Recommended path forward (not executed):** if a repository administrator confirms this demo account is intended as a non-owner tenant staff user (consistent with its `full_name`), running the remediation script with `--mapping 72640932-ef3c-4ce5-92a1-6609bff35ee0=staff --allow 72640932-ef3c-4ce5-92a1-6609bff35ee0 --apply --confirm` would be safe per the tool's own validation (tenant-scoped account, `staff` is a valid tenant-scoped role) — but that confirmation must come from a human with actual knowledge of this demo tenant's intended setup, not from this investigation.

## Account 2 — readonly@demo-ac-services.local (role: `tenant_readonly`)

**Disposition: MANUAL_ROLE_CONFIRMATION_REQUIRED**

Why not `SAFE_AUTOMATIC_REMAP`: no canonical role represents "tenant-side read-only user" — the brief explicitly forbids mapping to `admin_readonly` (a platform-scoped role; the remediation script would independently reject this as a scope violation even if attempted) and forbids inventing new aliases. There is no safe target.

Why not `NO_ACTION_PENDING_EVIDENCE` alone: this disposition would suggest simply waiting for more evidence to appear, but the missing piece isn't evidence about this specific account — it's a missing canonical role in the RBAC registry itself. More investigation of this account cannot produce a role that doesn't exist. `MANUAL_ROLE_CONFIRMATION_REQUIRED` more accurately frames this as needing a product/architecture decision (does ServiceOS need a tenant-side read-only role at all?), not merely more digging.

Why not `DISABLE_PENDING_REVIEW`: unlike account 1, this account has **real, repeated, currently-active usage** (7 logins, 7 unrevoked sessions) — disabling it would cut off whoever is using it without any communication, which is a real operational action that itself needs a decision, not just a mechanical safety default. Given the brief's own guidance ("restrict or disable only if the account presents a security risk and existing policy supports that action") and this account currently has *zero* effective permissions (it cannot do anything harmful even while active), there is no security risk that would justify unilaterally disabling it as part of a documentation-only slice.

**Recommended path forward (not executed):** requires a product decision first — either (a) accept mapping this account to `staff` (broader access than "read only" implies, but the only real option among the 10 canonical roles), or (b) build a genuine tenant-side read-only role in a future architecture change, or (c) deactivate the account and have its user re-request access properly. None of these can be decided by this investigation alone.

## Cross-account note
Both accounts share the same demo tenant (`demo-ac-services`) and the same creation batch — this is very likely one developer's demo-environment setup, not two independent incidents. Whoever owns `demo-ac-services` should be the one confirming intent for account 1 at minimum.
