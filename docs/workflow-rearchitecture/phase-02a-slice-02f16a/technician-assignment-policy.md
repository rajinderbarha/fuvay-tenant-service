# Technician and Assignment Policy

## Classification: **TECHNICIAN_NOT_SUPPORTED**

## Evidence
1. **Callers**: `frontend-mobile-exposure-audit.md` (2F-16) confirmed no mobile/technician-facing application calls any `quote_checklist` route — only `frontend/tenant-portal` (web, staff/office) for provider routes and `frontend/customer-app` for customer routes.
2. **UI**: No technician-facing screen/component references any `/staff/quotes`, `/staff/checklists`, `/provider/quotes`, or `/customer/quotes` endpoint (confirmed by the same search).
3. **Tests**: No existing test in `tests/test_sprint22_quote_checklist.py` or elsewhere exercises a technician actor against any quote_checklist route.
4. **Permissions**: No `QUOTE_CHECKLIST_*`-style permission exists that is granted to `technician` in `ROLE_PERMISSIONS` (this module uses role-list dependencies, not a dedicated permission, so this is confirmatory rather than the primary evidence source).

## Confirmation: all technician calls fail
`require_owner_or_office_staff_mutation` (used by all 11 tenant/provider mutation routes) explicitly excludes `technician` from its allow-list — proven directly by `test_denies_technician_and_customer`. `require_customer` (used by all 3 customer routes) also excludes `technician`. There is no third dependency in this module a technician could reach.

## This is established capability policy, not an accidental helper-name consequence
2F-16 deliberately chose `require_owner_or_office_staff_mutation` OVER `require_staff_or_above_mutation` (which WOULD admit technician) specifically because no evidence supports technician involvement in quote/checklist administration — this was a considered choice based on caller evidence, not an incidental side-effect of reusing an existing dependency that happened to exclude technician. See `provider-quote-authorization.md` (2F-16) for the original reasoning, re-confirmed unchanged this slice.

## No technician access was invented
Per this slice's explicit instruction ("Do not invent technician access"), no assignment-limited composed guard was created, and no technician-specific route or capability was added.
