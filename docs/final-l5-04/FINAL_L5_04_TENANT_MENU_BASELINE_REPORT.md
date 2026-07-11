# FINAL-L5-04 — Tenant Menu Organization Baseline Report

## Real current groups (from live `TENANT_NAV_GROUPS`, 7 groups, 25 items)
Overview (Dashboard), Setup (6 items), Team (1 item), Finance (3 items), More (Documents/Notifications/Activity/Settings), Operations (Jobs/Bookings/Appointments/Dispatch), Engagement.

## Comparison against the mission's recommended baseline
| Mission's recommended group | Real equivalent |
|---|---|
| Get Ready (Setup Checklist/Business Profile/Service Areas/Business Hours/Services/Pricing/Coverage/Publish Readiness) | Real "Setup" group closely matches (Setup Checklist, Business Profile, Service Areas, Service Setup, Service Coverage, Availability) — "Business Hours" and "Publish Readiness" not present as distinct items (may be sub-sections of existing pages, not independently verified) |
| Operations (Jobs/Calendar/Assignments/Customers) | Real "Operations" group exists (Jobs, Bookings, Appointments, Dispatch) — "Calendar"/"Assignments"/"Customers" not present as distinct top-level items |
| Team (Staff/Technicians/Roles/Availability) | Real "Team" group exists but has only 1 item (Staff & Technicians) — Roles/Availability not present as separate Team items (Availability is under "Setup" instead) |
| Finance (Usage Credit Balance/Ledger/Deductions/Package/Security Deposit) | Real "Finance" group closely matches (Package & Credits, Usage Credit Ledger, Security Deposit) |
| Engagement (Notifications/Reviews/Complaints) | Notifications is under "More", not a dedicated "Engagement" group; Reviews/Complaints not confirmed present in top-level nav this sprint |
| Settings (Business/Security/Notifications/Preferences) | `/settings` exists under "More" as a single item, not broken into sub-sections |

## Menu visibility requirements — real status
"Menu visibility must respect: tenant module, tenant category, tenant role, route availability." **Only "tenant role" is partially respected** (via `isTenantReadOnly()`'s button-level gating, not menu-item-level hiding). Tenant module and tenant category are **not respected at all** — see Tenant Entitlement Navigation Report for the full root-cause analysis (the underlying data, `tenant.category_id`, is always null).

## Result
Real structural comparison performed, several real gaps found between the mission's suggested grouping and the live menu (Team/Engagement most notably thin). Full visual reorganization is out of this sprint's stated scope; the entitlement-visibility gap is the substantive, already-documented blocker.
