# HS4 — Tenant Service Setup UI Report

## Route / title
`/tenant/setup/services` — real, working (1268 lines, confirmed real
across multiple prior sprints this session, not a stub).

## Literal "5-step wizard" requirement — not matched
The ticket asks for a step-indicator wizard (Step 1 Choose Service →
Step 2 Choose Type → Step 3 Price Range → Step 4 Brand Overrides →
Step 5 Review & Publish) with explicit step navigation. The real,
current page uses a **different, already-established layout** (per the
HS0 sprint's test-cleanup findings): a catalog card grid for service
selection, then a per-type/per-brand pricing table for the selected
service, with Review & Publish as a section within that same view —
functionally covering all 5 conceptual steps, but not as a literal
numbered wizard with a step indicator. This is a **known, pre-existing
architecture** (confirmed unchanged since the HS0 sprint), not something
this sprint altered.

## Functional coverage of the 5 steps
| Ticket step | Real equivalent |
|---|---|
| 1. Choose Service | Catalog card grid, admin-approved services only |
| 2. Choose Service Type | Per-service type selection (types tab equivalent) |
| 3. Set Provider Price Range | Per-type price range inputs with admin floor/ceiling shown |
| 4. Add Brand Overrides | Per-type brand override table (type-dependent, fixed in prior sprint) |
| 5. Review & Publish | "Review & publish" section (confirmed present, line ~680) with Publish Service CTA |

## Old duplicate pages — confirmed removed (HS0 sprint)
`/provider/pricing`, `/provider/customer-price-preview`,
`/provider/service-setup` all carry "moved" banners and are removed from
live nav — re-confirmed via grep this sprint, unchanged.

## No forbidden labels
0 matches for all 13 forbidden terms — re-confirmed this sprint via
grep.

## Verdict
UI: **functionally complete, safety-correct**, but does **not** match
the ticket's literal 5-step wizard presentation. This is a pre-existing
architectural choice (not introduced or worsened this sprint) —
documented as a real gap against this specific ticket's UI spec, not
fabricated as done.
