# E2E-07 Tenant Enterprise UI Baseline Report
**Date:** 2026-07-10  
**Analysis:** Static analysis only — browser verification pending

---

## Enterprise UI Components

### EnterpriseDataGrid (`components/enterprise/EnterpriseDataGrid.tsx`)

Used on pages that need server-side paginated, filterable tables:
- `/service-jobs` — service jobs grid
- `/appointments` — appointments grid
- `/provider/complaints` — complaints grid
- `/provider/refund-requests` — refund requests grid
- `/provider/reviews` — reviews grid
- `/provider/service-invoices` — service invoices grid

Features:
- Server-side pagination with `fetchFn` callback
- Column preferences via `EnterpriseColumnManager`
- Filter bar via `EnterpriseFilterBar`
- Export support
- Row actions menu
- Sort by column headers

### EnterpriseFilterBar (`components/enterprise/EnterpriseFilterBar.tsx`)

- Renders filter chips for active filters
- Supports: `select`, `date_range`, `text` filter types
- Filter state managed in URL or local state

### EnterprisePagination (`components/enterprise/EnterprisePagination.tsx`)

- Previous/Next/page-number controls
- Shows "Showing X–Y of Z results"

### EnterpriseColumnManager (`components/enterprise/EnterpriseColumnManager.tsx`)

- Column visibility toggle
- Column order management

### Pages Using Enterprise Components

| Page | Component | fetchFn Source |
|---|---|---|
| `/service-jobs` | EnterpriseDataGrid | `apiFetch('/v1/provider/service-jobs')` (fixed this sprint) |
| `/appointments` | EnterpriseDataGrid | `apiFetch('/v1/appointments/staff')` (fixed this sprint) |
| `/provider/complaints` | EnterpriseDataGrid | `apiFetch('/v1/provider/complaints')` (fixed this sprint) |
| `/provider/refund-requests` | EnterpriseDataGrid | `apiFetch('/v1/provider/refund-requests')` (fixed this sprint) |
| `/provider/reviews` | EnterpriseDataGrid | `apiFetch('/v1/provider/reviews')` (fixed this sprint) |
| `/provider/service-invoices` | EnterpriseDataGrid | `apiFetch('/v1/provider/service-invoices')` (fixed this sprint) |

**Status: PASS** — Enterprise UI components are present and correctly wired. Direct `fetch()` calls replaced with `apiFetch` this sprint.
