# Tenant Business Hours & Availability — UI Report

## Route
`/tenant/setup/availability`

## Canonical File
`frontend/tenant-portal/app/(tenant)/tenant/setup/availability/page.tsx`

## Old Route
`/provider/availability` — now redirects to `/tenant/setup/availability` via `router.replace()`

## Page Structure

| Section | Status |
|---|---|
| Breadcrumb: Tenant Portal > Setup > Business Hours & Availability | ✅ |
| Page title: Business Hours & Availability | ✅ |
| Status badge: Configured / Not Configured / Needs Attention | ✅ |
| Top actions: Add Working Hours, Add Holiday, Refresh | ✅ |
| Availability Status hero panel (colored left border) | ✅ |
| Quick Presets card (4 presets with icons + confirmation modal) | ✅ |
| Weekly Schedule card (grid layout with 7 rows) | ✅ |
| Booking Slot Preview (AM/PM formatted tabs) | ✅ |
| Bottom 2-column: All Working Hour Rules + Holidays & Exceptions | ✅ |
| Bottom 2-column: Availability Checks + Recent Activity | ✅ |

## Visual Design
- Card-first layout — all content in `var(--surface)` bordered panels with `border-radius:12`
- Status hero uses colored left border (green=configured, amber=unconfigured)
- Preset cards have emoji icons, monospace preview text
- Weekly schedule uses CSS grid (90px / 90px / 1fr / 140px columns)
- Slot preview uses 12-hour AM/PM format via `fmt12()` helper
- Bottom content in 2-column `display:grid; grid-template-columns:1fr 1fr`

## Sidebar
- `activeNav="provider-availability"` — highlights "Business Hours" in nav
- TenantLayout nav updated: href `/tenant/setup/availability`, label "Business Hours"
- Setup checklist step also updated to point to new route

## Preset Cards
| Preset | Icon | Days | Hours |
|---|---|---|---|
| Standard Hours | 🕘 | Mon–Sat | 09:00–19:00 |
| Weekdays Only | 📅 | Mon–Fri | 09:00–18:00 |
| Emergency Service | 🚨 | All days | 08:00–22:00 |
| Custom Schedule | ✏️ | (opens wizard) | — |

Standard/Weekdays/Emergency show a confirmation modal before applying.
Custom opens the Add Working Hours wizard directly.

## TypeScript: 0 errors ✅
## Tests: 43/43 passed ✅
