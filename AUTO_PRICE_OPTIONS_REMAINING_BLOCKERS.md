# Automatic Price Options — Remaining Blockers

None of these block certification — honestly documented, non-blocking notes.

## 1. Pricing Rules table not redesigned with Auto Low/Mid/High columns

`/admin/pricing-rules` was not updated to show the ticket's requested
Service/Type/Brand/Issue/Zipcode/Admin Range/Customer Range/Platform
Fee/Auto Low/Auto Mid/Auto High/Status/Actions table. The 3 new Home
Services pages (Customer Price Experience, Provider Matching, Matching
Diagnostics) plus the tenant Customer Price Preview page cover the ticket's
core "replace manual bargain setup with automatic price options" goal; the
Pricing Rules table redesign is a separate, additive UI enhancement that
would require touching an existing, unrelated admin page's table schema — 
deferred rather than rushed.

## 2. "Reset Defaults" on Provider Matching page is disabled

The scoring weights (20/20/15/15/10/10/5/5) are fixed platform constants in
`matching_engine.py` for this phase — there is no persisted per-deployment
override to reset. The button is honestly disabled with an explanatory
tooltip rather than wired to a fake action.

## 3. No customer-facing frontend exists to verify the actual Low/Mid/High cards

Consistent with every prior sprint — no customer-facing web app exists in
this repo. The ticket's "Customer UI Rule" section is satisfied structurally
(the already-certified `/match-and-price` endpoint from the Provider
Matching sprint never returns internal scores or admin ranges; this sprint
did not touch that endpoint's contract), but there is no screen to visually
confirm the exact card layout described in the ticket.

## 4. Deprecated Bargain Rules page still allows creating new manual rules

Per the instruction "keep backend evaluator... do not delete working
certified backend logic unless required," the deprecated page's create/edit
functionality was left intact (banner-only deactivation) rather than
disabled outright. An admin who directly navigates to the deprecated page
can still technically create a new manual `BargainRule`. If the product
decision requires *hard*-blocking new manual rule creation (not just hiding
the nav item and adding a banner), that would need an additional backend
validation gate — not implemented this sprint, since the ticket's wording
("Remove/hide from active navigation... Add deprecated banner... Keep API
backward compatible if needed") reads as navigation-level deactivation, not
a hard write-block.

## 5. Same pre-existing gaps carried over from prior sprints

No ESLint config, no `npm test` script, the `/service-jobs` build issue —
all previously documented, all confirmed untouched by this sprint.
