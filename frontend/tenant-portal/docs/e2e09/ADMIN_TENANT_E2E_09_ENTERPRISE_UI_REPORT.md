# E2E-09 Enterprise UI Classification Report

## Page Classifications

### `/provider/service-coverage` — PASS_ENTERPRISE_LEVEL
- 4 KPI stat cards with real computed values
- Service card grid with setup progress bars
- Active services table with status badges
- Slide-over config panel with 4 tabs (Types & Brands, Service Options, Service Areas, Readiness)
- Right sidebar: Coverage Rules, Needs Attention, Bookability checklist, Need Help
- Search + status filter row
- Design-token CSS via inline styles + CSS class strings
- No className= patterns (uses custom CSS classes via `<style>` tag)
- Responsive layout with `display:grid`

### `/tenant/setup/services` — PASS_ENTERPRISE_LEVEL
- Left-panel step navigator with completion states
- 5-step wizard: Service → Types → Pricing → Brands → Review
- Type pricing card with range slider visual, min/max inputs, price preview
- Brand override section grouped per type (type-scoped brand pricing)
- Review pricing matrix table with Low/Mid/High customer price display
- Post-publish bookability status panel (real API check)
- Read-only mode support for limited-access users
- Error banners with request ID copy + retry for each section
- Uses shared `Card`, `Btn`, `Badge`, `Skeleton`, `EmptyState`, `Modal` components

### `/provider/service-setup` (deprecated) — NEEDS_MINOR_UI_FIX
- Shows deprecation banner correctly
- Old 10-step wizard still renders (with real APIs)
- Recommend eventual removal; for now the deprecation banner is sufficient
- No broken UI elements; just legacy code

## Summary
- 2/3 pages: PASS_ENTERPRISE_LEVEL
- 1/3 pages: deprecated (NEEDS_MINOR_UI_FIX — should eventually be removed)
- 0 pages: FAIL
