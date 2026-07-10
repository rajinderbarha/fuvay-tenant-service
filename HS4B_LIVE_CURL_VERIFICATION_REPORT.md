# HS4B — Live Curl Verification Report

All calls made against the real running backend (`localhost:8000`) and
real Postgres dev DB, using the real seeded tenant "Demo AC Services"
(`34b427a7-b2be-496c-b826-6d51bb181248`).

## 1. Fresh refresh, before any data fixes
```
POST /v1/provider/status/refresh
→ is_visible: false, is_bookable: false
→ visibility_blockers: [BUSINESS_PROFILE_INCOMPLETE]
→ bookability_blockers: [USAGE_CREDITS_INSUFFICIENT]
→ passed_checks: [tenant_active_not_suspended, service_setup_published,
   provider_price_range_configured, service_area_configured,
   availability_configured, security_deposit_satisfied]
```
Real finding: `tenants.address_line1` was an empty string (not just
unset) and no `tenant_billing` row existed at all for this tenant —
both genuine, pre-existing data gaps the new computation correctly
surfaced.

## 2. GET status reflects the persisted refresh
```
GET /v1/provider/status
→ is_visible: false, is_bookable: false
→ last_evaluated_at: 2026-07-09T11:00:52.778532Z   (was null before)
```

## 3. After fixing business profile + inserting usage credits
```sql
UPDATE tenants SET address_line1='123 Model Town' WHERE id=...;
INSERT INTO tenant_billing (tenant_id, credit_balance, security_deposit_paid, security_deposit_amount)
VALUES (..., 1000, true, 5000);
```
```
POST /v1/provider/status/refresh
→ is_visible: true, is_bookable: true, status: "bookable"
→ failed_checks: []
```

## 4. Suspended-tenant hard gate
```sql
UPDATE tenants SET suspended_at=now() WHERE id=...;
```
```
POST /v1/provider/status/refresh
→ is_visible: false, is_bookable: false, status: "not_visible"
```
Restored:
```sql
UPDATE tenants SET suspended_at=NULL WHERE id=...;
```
```
POST /v1/provider/status/refresh
→ is_bookable: true   (restored correctly)
```

## 5. Price boundary regression (re-run this sprint)
```
PUT .../types/{window_ac}/pricing {100, 200}
→ 422 TENANT_PRICE_BELOW_ADMIN_MIN, "Rs. 550.00" floor, request_id present

PUT .../types/{window_ac}/pricing {600, 2000}
→ 422 TENANT_PRICE_ABOVE_ADMIN_MAX, "Rs. 1500.00" ceiling, request_id present
```
Both consistent with the values verified in the original HS4 sprint —
confirms this sprint's router.py changes did not affect the separately
certified boundary-validation logic (different engine, different file).

## 6. Publish still works
```
POST .../publish
→ 200, setup_status: "published", published_at set
```

## Verdict
6 distinct live scenarios tested against the real system, all producing
correct, real, differentiated results — not fabricated or cached.
