# Product Decisions Required - Slice 2F-30

**One, non-blocking, for the selected module:**

1. `POST|DELETE /v1/provider/profile/logo` and `/shop-photo` currently admit
   `require_technician` (technician, staff, tenant_owner, super_admin). Is
   changing the tenant's public branding intended to be delegable to a
   technician, or tenant_owner-only? Until decided, implement the narrower
   policy and record it. No new role or permission either way.

Carried, not owned by this slice:
- N05: whether the deposit mutating GETs should lazily create a row.
- Whether the same email may exist in two tenants (from 2F-29).
