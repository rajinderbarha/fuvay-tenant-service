# HS2 — Catalog UI Report

## Route / title / subtitle
`/admin/home-services/service-catalog` — real route, confirmed working.
Title changed to "Home Services Catalog" (was "Home Services Catalog
Setup"). Subtitle changed to the ticket's exact required copy: "Manage
platform-approved Home Services, service types, brands, customer
questions, options, and provider setup rules."

## Layout vs. ticket's required layout
| Ticket requirement | Status |
|---|---|
| Breadcrumb | Present (unchanged, pre-existing) |
| Page title + short subtitle | Fixed to match ticket exactly |
| Primary actions | Partial — "Refresh" and "Add Service" present; "Add Service Group", "Export Catalog", "View Audit" **not added** (see blockers) |
| Catalog health cards | **Added this sprint** — 8 cards, computed from real, already-fetched service data (not mock) |
| Service groups as clean cards | **Not built** — left panel is still a grouped list (label + rows), not the ticket's "cards" visual treatment |
| Services grouped under each group | Present (pre-existing, real) |
| Selected service configuration (drawer/side panel) | Present (pre-existing, real — right-side detail panel) |
| Bottom catalog activity/audit | Present as a tab, not a persistent bottom section (pre-existing structure, not moved this sprint) |

## UI rules
| Rule | Status |
|---|---|
| Cards first, table second | Partial — health cards now appear first; the service list below is still a compact row-list, not literally cards; the Types tab still uses a table (now catalog-only columns, no pricing) |
| Clear next action | Health cards show a "Review Services" CTA when the metric indicates a gap |
| Friendly labels | Existing `PRICING_MODEL_LABELS` mapping already converts `fixed`/`range`/`post_assessment`/`hourly` to friendly labels — unchanged, confirmed present |
| No raw backend enum | Confirmed — pricing model and status always pass through label maps or explicit Active/Inactive text |
| No raw JSON | Confirmed — no `JSON.stringify` or raw object rendering found |
| No duplicate pricing pages | Fixed this sprint — pricing forms removed from catalog, single link to Pricing Rules instead |
| No NaN/null/undefined | `safeText`/`safeNum`/`safeCurrency`/`safePercent`/`safeDate` formatters already existed and are used throughout; not removed or weakened this sprint |
| No confusing technical words | Partial — service list rows still show `is_type_required`-derived internal-ish phrasing in places; not fully audited word-by-word this sprint |

## Service card "8 questions" checklist
The ticket requires every service card to answer 8 specific questions
(active? customer visible? provider selectable? has types/brands/
questions? what's missing? next action?). The current `ServiceRow`
(left-panel row) and the detail panel's General tab together answer most
of these (name, status, pricing model, types/brands counts), but:
- **Not shown per-card**: explicit "what is missing" / "what should
  admin do next" — this exists in aggregate on the new health cards, not
  per individual service card.
- **Not shown**: a distinct "Setup Status" badge (Ready/Needs Types/
  Needs Questions/Needs Brands/Inactive/Draft/Blocked) as the ticket
  specifies — the row only shows a green/gray active dot today.

## Verdict
Core scope violation (pricing mixed into catalog) is fixed. Health cards
added with real data. Full "cards-first" visual redesign of the service
list and per-card setup-status badges were **not completed** this
sprint — documented as remaining UI polish, not a scope violation.
