# Tenant My Offerings — UI Quality Report

## Structure delivered

1. Breadcrumb (Tenant Portal / Setup / My Offerings)
2. Enterprise header with Enable Offering / Validate Offerings / Refresh Catalog actions
   (permission-aware)
3. Offering Readiness hero (tenant name, vertical, available/enabled/bookable/issues counts)
4. 8 KPI cards (Available, Enabled, Bookable, Readiness Issues, Coverage Configured, Pricing
   Ready, Assigned Technicians, Service Areas Linked)
5. 4 tabs: Available Offerings, My Enabled Offerings, Readiness Issues, Catalog Diagnostics —
   each with a real backend-data-driven count, or "Unavailable" (not `0`) on API failure
6. Available Offerings catalog — search filter, enterprise cards with service group, type
   badges, pricing, requirement warnings, Enable/View Enabled Offering CTA
7. My Enabled Offerings — enterprise table (Offering, Status, Readiness, Coverage, Emergency,
   Pricing, Blockers, Updated, Actions)
8. Readiness Issues panel — per-offering blocker cards with reason/rule/CTA
9. Catalog Diagnostics tab — 4 live pass/fail checks plus a historical-bug note
10. Enable/Edit wizard (drawer) — real catalog-sourced type/brand/issue/option coverage, real
    service-area and technician panels, real backend pricing note
11. Activity timeline — real audit-log-backed, ticket-matching empty-state copy

## No longer looks basic

Old page: title "My Offerings", flat tabs with `0` counts, one-line generic empty state ("No
offerings available in your category."). New page: breadcrumb, hero, 8 KPI cards, 4 tabs with
real/Unavailable counts, enterprise catalog cards, enriched enabled-offerings table, dedicated
readiness and diagnostics tabs, activity timeline — materially different, enterprise-grade.

## Empty state upgraded

Replaced with the ticket's exact required copy: "No eligible offerings found" / "No
platform-approved services are currently available for your tenant vertical/package. This may
be a setup issue." + Refresh Catalog / Run Catalog Diagnostics actions. (In practice this state
no longer triggers for the certified tenant since the catalog-mapping bug is fixed — but the
enterprise empty state exists and is tested for the case where it legitimately would.)

## Error states

Every section (Available, Enabled, Readiness, Activity) has its own `SectionError` render with
title, message, failing section name, `request_id`, Retry, and Copy Request ID — partial
rendering confirmed (one section's failure doesn't blank the header, hero, KPI cards, or other
tabs).

## Duplicate offering guard

`is_already_enabled` drives the card CTA to "View Enabled Offering" instead of re-enabling,
opening the existing enabled record in the same drawer rather than creating a duplicate.

## Responsive layout

KPI cards and available-offering cards both use `repeat(auto-fit, minmax(...))` grids (collapse
naturally on tablet/mobile). Tabs row scrolls horizontally (`overflow-x: auto`) on narrow
viewports. Enabled-offerings table wraps in `overflow-x: auto`.
