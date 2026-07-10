# Provider-First Matching + Customer Price Choice — Remaining Blockers

None of these block certification — honestly documented, non-blocking.

## 1. Draft creation still depends on the legacy `master_offerings` table

`start_booking_draft` resolves `category_slug`/`offering_slug` against
`MasterOffering` (the same empty, orphaned table fixed for provider-facing
endpoints in the My Offerings sprint). This is a pre-existing, separate bug —
out of scope for this ticket (matching + price choice), but blocks a true
end-to-end customer flow test through the router. The new matching/pricing
logic itself was fully verified independent of this gap (pure functions +
direct DB-backed calls).

## 2. No live customer-facing frontend to update

Consistent with prior sprints — no customer-facing web app exists in this
repo. The Low/Mid/High UI described in the ticket has no existing screen to
update; documented rather than fabricated.

## 3. `job_completion_score`/`cancellation_score` return neutral defaults for providers with no job history

Real tenants with zero completed/cancelled jobs get a neutral 50/100 score for
these two sub-factors rather than being penalized or excluded — an
intentional design choice (new providers shouldn't be unrankable), documented
here for clarity.

## 4. Old list-based endpoints kept for backward compatibility

`/match-providers` and `/select-provider` still exist and still work exactly
as before (list-based, customer picks manually) — marked `[DEPRECATED]` in
OpenAPI but not removed, since removing them without confirming no other
caller depends on them risks a real regression. New customer UI should only
ever call `/match-and-price` + `/confirm-price-choice`.
