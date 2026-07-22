# Router vs. Service Authorization Boundary

## Before this slice

`add_note`/`add_media`'s service-level helper (`_assert_can_access_job` + inline customer
denial) enforced **only** object access: tenant identity, Job identity, and technician
assignment. It did **not** enforce:

- Canonical role membership as a named, tool-visible gate (customer denial was an inline
  `if self.actor_role == "customer": raise` inside the service method, not a router dependency).
- Mutation-capable tenant access scope (a `tenant_owner`/`staff` account with a read-only
  `access_scope` could still reach the service method and only be caught by... nothing — no
  access-scope check existed anywhere in this path before this slice).
- Explicit `StaffPermission` deny precedence (not applicable here — no such permission gates
  this capability, and none was added).

This was service-level object-access enforcement being relied on as a **replacement** for
router-level mutation-scope policy — exactly the anti-pattern this slice's mission instructs
against.

## After this slice

Router responsibilities (via `require_staff_or_above_mutation`): authentication, persona
(`tenant_owner`/`staff`/`technician`/`super_admin`, excludes `customer`), mutation-capable
access-scope (denies read-only tenant accounts).

Service responsibilities (unchanged): tenant ownership, Job ownership, assignment, state
validation (none applicable — no lifecycle gate on notes/media).

## Read-only tenant access-scope — now actually verified, not merely assumed

Before this slice, no test anywhere proved that a read-only-scoped `tenant_owner`/`staff`
account was denied from `add_note`/`add_media` — the service method simply never checked
`access_scope` at all. This was a real, previously-unverified gap, now closed by
`require_staff_or_above_mutation`.
