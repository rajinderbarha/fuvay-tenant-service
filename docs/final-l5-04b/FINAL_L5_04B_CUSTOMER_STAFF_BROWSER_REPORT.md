# FINAL-L5-04B — Customer and Staff Browser E2E Report

## Not run this sprint — honest scope statement
No customer-facing or staff/technician browser E2E was executed for entitlement behavior, because neither Customer Category Availability nor Staff Entitlement Scope was implemented this sprint (see their respective reports for why — both are downstream of the also-not-implemented Matching Entitlement work).

## What would be tested once the underlying features exist
- **Customer**: verify active category discovery, disable a tenant's category entitlement, verify that tenant is removed from matching results, verify historical booking remains readable, re-enable and verify matching eligibility returns.
- **Staff**: login as a technician, verify category filters follow tenant entitlements, disable a category, verify no new assignment/filter uses it, verify historical job behavior unaffected, verify no duplicate `/v1/auth/me` requests (unrelated pre-existing concern, not touched this sprint).

## Result
Deferred, honestly, pending the Matching Entitlement Report's recommended follow-up sprint. Not fabricated as passing.
