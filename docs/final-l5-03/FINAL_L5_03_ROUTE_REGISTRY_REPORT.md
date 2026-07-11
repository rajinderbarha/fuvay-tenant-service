# FINAL-L5-03 — Route Configuration Standardization

`lib/page-registry.ts` and `lib/nav-config.ts` already exist per-app (super-admin, tenant-portal) from prior sprints (established pre-FINAL-L5-03). Confirmed present, not restructured this sprint per the mission's own explicit instruction: "Do not fully redesign menus yet; that belongs to FINAL-L5-04 and FINAL-L5-05."

## What this sprint verified (not changed)
- Both registries exist and are the source for navigation rendering in `AdminLayout`/`TenantLayout`.
- No route definitions were found duplicated between the registry and ad-hoc hardcoded nav arrays during this sprint's file reads (`TenantLayout.tsx` does have some inline `NavItem`-shaped arrays for specific sub-sections — not restructured, out of scope per the mission's deferral).

## Result
Registry-based routing already exists; full conformance to the mission's suggested `RouteDefinition` shape (with `permission`/`moduleKey`/`categoryScoped` fields) is explicitly deferred to FINAL-L5-04/05 per the mission's own text, not attempted here.
