# Product Decisions Required — Slice 2F-2

## 1. Should `create_member_login` actually be implemented?
Today it's a stub returning `{"credentials": None}` with no `users` row
created and no `provider_team_members.user_id` link established. If team
members are meant to get real login access through this flow, the
implementation needs to be built (password generation, `users` row
creation, linking `user_id`, initial-login flow). Not decided or built this
slice (new engineering behavior is out of scope for a mutation-enforcement
slice).

## 2. Should per-technician individual availability/schedules be a feature?
Confirmed: no such capability exists anywhere in `provider_portal.router`
today — all availability configuration is tenant-wide, `tenant_owner`-only.
If individual technician schedules (as opposed to business-wide hours) are
wanted, that's a new capability requiring a new table/column linking a rule
to a specific technician and a new self-service permission — not decided
here.

## 3. Should `provider_team_members` support duplicate-invitation
   detection?
`create_team_member` does not check for an existing row with the same
email/phone before inserting. Not a security gap (still correctly
tenant-scoped and owner-gated), but a data-quality question for product to
weigh in on. Not fixed this slice.

## 4. Should any provider-portal capability ever support delegated staff?
Every one of the 22 role-gated endpoints is currently `tenant_owner`-only
by design (no staff persona holds the underlying role check). If future
product direction wants e.g. an office-manager staff role to manage the
team roster or availability, that's a role-architecture decision — this
slice's `require_tenant_owner_mutation` guard would need a permission-based
sibling (like `require_tenant_mutation_permission`) applied instead, not a
broadening of `require_tenant_owner` itself. Not decided or built here.
