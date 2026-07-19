# Super Admin Dashboard Specification

Component: `frontend/super-admin/components/ux02/widgets/RoleDashboard.tsx`
Showcase: `/dev/ux-02/dashboard` (all 5 canonical roles).
Readiness: `MOCK_DESIGN_ONLY` (fixture-backed; no live analytics wiring yet).

## Sections (in render order)
1. **Platform Snapshot** — active tenants, open compliance cases, (finance roles) total package
   credit, (security roles) security observation count. Card grid, `auto-fit minmax(160px,1fr)`.
2. **Action Center** — tenants pending verification, rendered as actionable cards with a status badge.
3. **Activity (last 7 days)** — Recharts `BarChart` (already a project dependency) over 7 days of
   fixture activity counts.
4. **Risk Overview** (admin_security/super_admin only) — security observations with careful status
   language (see `security-operations-pattern.md`) — never a raw "incident" claim.
5. **System Notices** — platform notices (info/warning/critical) from `FIXTURE_PLATFORM_NOTICES`.

## Role configuration
See `canonical-admin-role-presentation.md` — one composition, per-role section visibility, not
five dashboards.

## Data model
`lib/ux02/fixtures.ts`: `FIXTURE_TENANTS`, `FIXTURE_COMPLIANCE_CASES`,
`FIXTURE_SECURITY_OBSERVATIONS`, `FIXTURE_PLATFORM_NOTICES`. See `dashboard-widget-inventory.csv`
for the widget-by-widget backend-capability mapping.
