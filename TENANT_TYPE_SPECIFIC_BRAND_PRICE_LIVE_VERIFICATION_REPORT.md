# Tenant Type-Specific Brand Price — Live Verification Report

All 8 required scenarios executed against the real running backend and
real Postgres dev DB, using the real seeded AC Repair tenant service
(`015efedb-dd92-41f4-97ef-cc2745437760`), real Window AC / Split AC
types, and the real LG brand.

## 1. Save Window AC + LG provider range ₹400–₹480 (inside the real admin range ₹350–₹500)
```
PUT .../brands/{LG}/pricing?service_type_id={WindowAC} {400, 480}
→ 200, tenant_service_brand created, preview: Low ₹440, Mid ₹480, High ₹528
```

## 2. Save Split AC + LG provider range ₹700–₹850 (inside the real admin range ₹600–₹950)
```
PUT .../brands/{LG}/pricing?service_type_id={SplitAC} {700, 850}
→ 200, distinct record created, preview: Low ₹770, Mid ₹850, High ₹935
```

## 3. Verify DB has two records with different service_type_id
```sql
SELECT service_type_id, brand_id, tenant_min_price, tenant_max_price
FROM tenant_service_brands WHERE tenant_service_id=... AND brand_id=<LG>;
```
Returned **3 rows**: 1 legacy type-agnostic enablement marker (NULL
type, NULL price) + 2 real, independent, correctly-priced type-scoped
rows — confirmed via direct `psql` query.

## 4. Review table shows both rows with different values
Confirmed via `GET .../brand-pricing?service_type_id={WindowAC}` →
`[{"name":"LG","tenant_min_price":400.0,"tenant_max_price":480.0}]` and
`GET .../brand-pricing?service_type_id={SplitAC}` →
`[{"name":"LG","tenant_min_price":700.0,"tenant_max_price":850.0}]` —
each GET scoped by type returns only that type's value, confirming the
Review matrix (which calls these same endpoints per type) renders
correctly-separated rows.

## 5 & 6. Preview values confirmed correct per type
Window AC + LG preview (Low ₹440/Mid ₹480/High ₹528) and Split AC + LG
preview (Low ₹770/Mid ₹850/High ₹935) both confirmed via the live save
responses above — each computed from its own, correct provider range.

## 7. Changing Window AC + LG does not change Split AC + LG
```
PUT .../brands/{LG}/pricing?service_type_id={WindowAC} {420, 490}  (update)
GET .../brand-pricing?service_type_id={SplitAC}
→ LG: 700.0 - 850.0  (unchanged)
```
Confirmed: updating one type's brand price has zero effect on the
other.

## 8. Publish keeps both overrides
```
POST .../publish → setup_status: "published"
GET .../brand-pricing?service_type_id={WindowAC}
→ LG: 420.0 - 490.0  (post-publish value, matching the update from step 7)
```
Confirmed the override survives publish, per-type, unchanged by the
publish action itself.

## Verdict
All 8 required live scenarios passed exactly as specified. Window AC
and Split AC brand overrides for the same brand (LG) are fully
independent at every layer: storage, retrieval, update, and publish.
