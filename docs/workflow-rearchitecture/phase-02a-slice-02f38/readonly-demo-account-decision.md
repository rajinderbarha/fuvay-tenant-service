# readonly@demo-ac-services.local — Decision

**Disposition: `MANUAL_ROLE_CONFIRMATION_REQUIRED`. Role migration readiness
stops with `ROLE_REMEDIATION_POLICY_BLOCKED` for this account.**

No canonical role in the 10-role registry represents "tenant-side
read-only user." `admin_readonly` is platform-scoped and would be rejected
by `scripts/workflow_rearchitecture/remediate_invalid_roles.py`'s own
validation (platform roles cannot be assigned to a tenant-scoped account,
and this account has a non-null `tenant_id`). No alias may be invented.

This is a genuine product/architecture gap (does ServiceOS need a
tenant-side read-only role at all?), not an evidence gap that more
investigation could close — re-confirmed from `remediation-decision-register.md`
(Slice 2C), unchanged through every subsequent slice including this one.

**7 real logins and 7 currently-unrevoked sessions exist.** This is a real
operational fact this slice does not act on unilaterally: the account has
zero effective permissions today regardless (role absent from
`ROLE_PERMISSIONS`), so no active security exposure results from leaving
it as-is pending a human product decision. See
`manual-role-confirmation-request.md` for the decision request this
account requires before Migration 144 can safely run against any database
containing this row.
