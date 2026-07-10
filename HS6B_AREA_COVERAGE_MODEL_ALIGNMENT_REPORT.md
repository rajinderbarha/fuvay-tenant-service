# HS6B — Area Coverage Model Alignment Report

## Fix
`_passes_full_eligibility_gate` now checks coverage via a real join:
```sql
SELECT count(*) FROM tenant_service_area_services tsas
JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id
WHERE tsas.tenant_id=:tid AND tsas.service_id=:oid
  AND tsas.is_available=true AND tsa.is_active=true
  AND tsa.zipcode=:zip                    -- when zipcode given
  AND tsas.service_type_id=:stid          -- when type given
  AND tsas.brand_id=:bid                  -- when brand given
```
This is HS5B's normalized coverage table (extended with
`service_type_id`/`brand_id` in migration 121), joined to the real
service-area zipcode. The old `provider_enabled_offerings.
supported_type_ids`/`supported_brand_ids` JSON arrays are no longer
read anywhere in the matching path.

## Live verification (real DB, real function calls)
1. Real tenant with real Split AC + LG coverage configured (via the
   real `PUT .../service-areas/{id}/coverage` endpoint, HS5B) at
   zipcode 141001 → **included** in matching for `AC Repair + Split AC
   + LG + 141001`.
2. Same tenant, same request but with a **fake brand ID** (no coverage
   row exists for it) → **excluded** (`excluded_count: 1, signals:
   None`) — confirms the brand-coverage check is real and enforced, not
   a no-op.

## No legacy fallback implemented
Per the ticket's explicit instruction not to silently maintain two
competing sources, no JSON-array fallback path was added. See
`HS6B_MATCHING_DATA_MODEL_ALIGNMENT_REPORT.md` §7 for the reasoning and
the resulting migration consideration for any hypothetical
legacy-JSON-only tenant (none exist in this dev DB).

## Verdict
Area coverage alignment: **complete**. Matching now genuinely consumes
the same per-area service/type/brand coverage a tenant configures in
Service Areas — live-verified to both include a correctly-covered
combination and exclude an uncovered one.
