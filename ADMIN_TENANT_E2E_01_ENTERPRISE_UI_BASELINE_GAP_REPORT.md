# ADMIN_TENANT_E2E_01 — Enterprise UI Baseline Gap Report

Based on real screenshots captured in Parts 9–10 (`frontend/e2e-admin-tenant/evidence/*.png`).

## Observed (both apps)
1. **First-load onboarding tour modal ("STEP 1 OF 7")** appears over every fresh page load on both
   admin (`/admin/home-services/service-catalog` → "Command Center" tour) and tenant
   (`/dashboard` → "Your Daily Command" tour), dimming the underlying content and skeleton-loading
   placeholders behind it. This is by design (a first-run tour) but means every automated screenshot in
   this sprint's evidence captures the tour overlay rather than the underlying page — a real E2E
   friction point for future page-by-page sprints, which will need to dismiss/skip the tour
   deterministically (e.g. via a "skip tour" click or a `localStorage` flag) before asserting on page
   content. **Flagged, not fixed** — out of scope for this foundation sprint.
2. **Sidebar active-state item is "Dashboard" even on `/admin/home-services/service-catalog`** — the
   admin sidebar highlight did not move to a Home Services item, only "Dashboard" is highlighted.
   Genuine active-state gap. **Flagged, not fixed.**
3. Tenant dashboard header correctly reads "Demo AC Services" / "Demo Provider" after the Part 7 fix —
   no gap here anymore (previously would have shown "Your Business").
4. Both screenshots show clean skeleton-loading placeholders (grey bars) rather than raw JSON or crash
   states — no "raw backend enum visible" or "confusing status labels" observed in the two closely
   examined screenshots. Status badges ("Not Bookable", "Setup 100%") on tenant dashboard use readable
   English labels, not raw enum values.
5. No debug-looking pages, no unlabeled buttons, no giant empty spaces observed in the examined
   screenshots.

## Not fixed (documented as gaps, per "only fix quick/safe issues" instruction)
- Onboarding tour intercepting every fresh session — needs a documented dismiss mechanism for E2E.
- Sidebar active-state highlight not reflecting the current Home Services sub-route.

## Result
Two real gaps found and documented; nothing here rose to the level of a blocker for foundation
certification. Both are good candidates for the first page-by-page Admin E2E sprint to fix.
