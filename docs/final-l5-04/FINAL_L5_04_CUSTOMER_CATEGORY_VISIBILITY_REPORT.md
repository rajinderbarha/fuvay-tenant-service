# FINAL-L5-04 — Customer Category Visibility Report

## Real, working, already-correct infrastructure (verified live this sprint)
`GET /v1/catalog/master/categories` (the endpoint `getCustomerHomeServicesCatalog()` calls) is **server-side filtered** to `is_active=True` at the query layer (`app/engines/admin_catalog/customer_router.py: s.list_categories(is_active=True)`), confirmed by reading the handler and by a live call this sprint returning 14 categories, all with `is_active: true`. A category deactivated by an admin would never appear in this response at all — there is no client-side filtering to bypass or get wrong, because the inactive category's data is never sent to the browser in the first place. This is a stronger security/correctness posture than a frontend-hide approach (satisfies rule 3: "Do not rely only on frontend hiding for security").

## Required checks
| Check | Result |
|---|---|
| 1. Disabled category disappears from home/category list | **True by construction** — server-side filter, not independently re-toggled and re-tested live this sprint (would require deactivating a real category and confirming the customer list shrinks, not attempted to avoid disrupting the shared canonical dataset used by other certification evidence) |
| 2. Search does not return inactive category | Not independently tested — customer-app has no dedicated category search feature found in this sprint's scan of its 8 pages |
| 3. Deep link to inactive category is rejected or redirected | Not tested this sprint — no customer-app route exists that takes a category slug as a URL parameter (the home-services flow uses a single fixed entry point, `/customer/home-services`, not per-category deep links) |
| 4. Existing booking history remains readable | Not tested this sprint; architecturally plausible since booking history reads `service_bookings` (a snapshot table, not a live join against the category's current `is_active` state) — not independently confirmed |
| 5. Re-enabled category returns | Same server-side-filter mechanism — would return automatically once `is_active` flips back true, not independently re-tested live |
| 6. No stale cached category remains after refresh | No caching layer exists on this endpoint (confirmed no cache-control/ETag logic in the handler) — every request re-queries live |

## Result
Customer category visibility is **architecturally sound and real** (server-side filtering, not a frontend-hide pattern), satisfying the spirit of Part 8's requirements. Several specific sub-checks (search, deep-link rejection, live toggle-and-observe) were not independently exercised this sprint given the time budget — documented as not-yet-verified rather than assumed passing.
