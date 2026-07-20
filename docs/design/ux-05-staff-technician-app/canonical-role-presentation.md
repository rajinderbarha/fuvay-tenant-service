# Canonical Role Presentation

Canonical roles for this app's users: `staff` | `technician`. No other role name is used, aliased, or invented
(no dispatcher/field_agent/branch_manager/etc.).

## Real-evidence gap found
`StaffUser` (`src/lib/api.ts`) has **no live role field today** — the backend returns `specialisations`, `status`,
`working_hours`, `performance_score`, but nothing that distinguishes "staff" from "technician" as this app's own
concept. This is documented as `product_decision_required` / `api_contract_required` (see
`backend-contract-blockers.md`), not silently assumed.

## Fail-closed default
`src/lib/ux05/permissions.ts`'s `deriveRole()` defaults every authenticated user to `technician` (the more
restrictive presentation) unless an explicit `role: "staff"` value is present. This is a deliberate fail-closed
choice — the alternative (fail-open, defaulting to `staff`) would risk showing tenant-operational UI to a user the
backend never actually elevated. Frontend role presentation is **never** the authorization boundary regardless of
which way this defaults; the backend's own StaffPermission/role check remains the real gate.

## Designation vs authorization
`ProfileView.designation` (e.g. "Senior AC Technician") is descriptive display text pulled from
`specialisations`/profile copy only — it is never read for any permission or nav-visibility decision. Tested
implicitly by `deriveRole` never reading `specialisations`.
