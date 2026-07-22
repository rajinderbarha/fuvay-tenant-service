# Breadcrumb Reconciliation — Slice 2B

## Before this slice
- **Tenant-owner shell**: had breadcrumbs (`TenantLayout` renders `<Breadcrumbs/>`), but resolution was purely static-registry/prefix-based (`lib/page-registry.ts`) with no way to inject a real entity name — a specific job's execution page showed the same generic "Jobs > Service Jobs" breadcrumb regardless of which job was open.
- **Technician/staff shell**: `StaffLayout` never rendered a `Breadcrumbs` component at all — zero breadcrumb trail on any of its 12 pages.

## What was implemented

### 1. Technician shell now has breadcrumbs
Added `<Breadcrumbs crumbs={...}/>` to `StaffLayout.tsx` with a technician-specific static map (`STAFF_BREADCRUMBS`), matching the brief's examples:
- Today → (Dashboard, single-item, no trail rendered — matches existing single-item suppression behavior already used by the tenant-owner Breadcrumbs component)
- My Work → "My Work"
- My Jobs → "My Jobs" (list) / "My Jobs → {job_number}" (contextual detail, see below)

### 2. Contextual, entity-aware breadcrumbs (the "reconstruct context for direct deep links" requirement)
Two pages now show the real record name instead of a generic label:
- **`/staff/jobs/[job_id]`** — passes `crumbs={[{label:"My Jobs",href:"/staff/jobs"},{label: job.job_number}]}` directly as a prop (StaffLayout is rendered per-page here, so a direct prop works).
- **`/(tenant)/service-jobs/[id]/execution`** — this page is wrapped by an *automatically-mounted* `TenantLayout` (via `app/(tenant)/layout.tsx`), so it has no direct prop channel to the shell several levels above it. Added a new `useBreadcrumbOverride()` context hook (in the shared `Breadcrumbs.tsx`) that lets any page inside `TenantLayout`'s children override the auto-resolved breadcrumb. This page now calls it once the job loads: `Jobs → Service Job {job_number} → Inspection and Quote`, falling back to the static registry entry while the job is still loading (never showing an empty or wrong entity name).

This second mechanism is reusable — any other tenant-portal contextual detail page can call `useBreadcrumbOverride()` the same way in a future slice, without needing its own layout wrapper.

## Requirements checklist

| Requirement | Status |
|---|---|
| Do not expose engine names | Yes — labels are "Service Job", "Inspection and Quote", "My Jobs", never "ServiceJob", "execution", "home_service_assignment" etc. |
| Use user-facing entity labels | Yes — real `job_number` (e.g. "JOB-abc12345") shown, not internal UUIDs |
| Include useful record reference | Yes — job number included |
| Reconstruct breadcrumb context for direct deep links | Yes — both contextual pages compute their breadcrumb from the loaded record, so a bookmarked/shared URL opened fresh still produces the correct trail once the record loads |
| Respect role-specific navigation | Yes — technician's map (`STAFF_BREADCRUMBS`) is separate from the tenant-owner registry (`TENANT_PAGE_REGISTRY`); not shared or assumed identical |
| Do not assume the same parent navigation for every role | Yes — technician's job breadcrumb says "My Jobs → {job}"; tenant-owner's says "Jobs → Service Job {job} → Inspection and Quote" — same underlying `ServiceJob` record, different parent context per role, exactly per the brief's own examples |
| Provide valid back navigation | Yes — every non-final crumb has a real `href` |
| Avoid misleading breadcrumbs for hidden/contextual pages | Yes — the 4 `ADVANCED_SETTINGS`-disposition technician pages (documents, activity, sessions) still get a correct "Profile > X" trail, not a fabricated primary-nav-looking one |

## Not done this slice
- Super-admin breadcrumbs — untouched (Slice 2 confirmed its existing `Breadcrumbs.tsx` derives from the URL path automatically; not re-verified against the 6 newly-added nav items this slice, since no code change was needed there).
- Extending `useBreadcrumbOverride()` to other tenant-portal contextual pages (e.g. `/customers/[id]`, `/(tenant)/service-jobs/[id]/quotes`) — only the one page named in the brief's examples was updated; others remain on the static registry fallback.
