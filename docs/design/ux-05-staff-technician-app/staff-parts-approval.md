# Staff Parts Approval

`StaffPartsApprovalShowcaseScreen` (new this session, dev-only). Renders `PermissionRestrictedState` for **every
current real user** -- `deriveRole()` fails closed to `technician` for all real `StaffUser` data today (no live
role field), so `role !== "staff"` is true for every real account, and the screen shows the restriction reason
rather than a queue. This is intentional and matches the hard constraint (technician never gets approve/reject/
mark-installed authority) by construction, not by a screen-level role check that could be bypassed.

If role were ever `"staff"` AND `parts_request:approve` were granted (neither is possible with real data today --
`permissionsFor()` always returns `granted:false`), the screen would render an Approve/Reject queue acting on
local state only, clearly labeled `MOCK_DESIGN_ONLY` (no live parts-approval endpoint exists).

No mark-installed action was built (would be a provider-side action per the brief, not a staff one, and no
provider-side endpoint exists either).
