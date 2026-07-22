# Product Decisions Required - Slice 2F-28

**None block the selected module.** One question to confirm during the M01
implementation slice:

1. `POST /v1/auth/impersonate` - is impersonation restricted to `super_admin`
   only, or also `admin_security`? The permission `platform:impersonate` exists;
   the intended role grant must be confirmed rather than assumed. Until
   confirmed, implement the narrower policy (super_admin only) and record it.

Deferred product decisions belonging to other modules (not selected):
- M06 security-deposit lifecycle: whether the two mutating GETs should
  lazily create a deposit row at all.
- M02 media: whether provider logo/shop-photo deletion is owner-only or
  delegable to staff.
