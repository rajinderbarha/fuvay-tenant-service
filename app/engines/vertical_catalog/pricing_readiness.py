"""Shared provider-owned pricing check for published Home Services offerings.

Publication validates the complete blueprint and all selected combinations.
This readiness check must never substitute a legacy admin price, and must
recognize the single tenant settings fee for consultation-only providers.
"""

PUBLISHED_PRICED_SERVICES_SQL = """
SELECT count(*) FROM tenant_services ts
WHERE ts.tenant_id=:tid AND ts.setup_status='published'
  AND ts.is_enabled=true AND ts.is_active=true AND ts.deleted_at IS NULL
  AND CASE WHEN lower(ts.job_type) = 'consultation' THEN
    EXISTS (
      SELECT 1 FROM tenant_operational_settings settings WHERE settings.tenant_id=ts.tenant_id
      AND CASE
        WHEN (settings.extra->'home_services'->>'consultation_fee') ~ '^[0-9]+([.][0-9]+)?$'
        THEN (settings.extra->'home_services'->>'consultation_fee')::numeric > 0
        ELSE false
      END
    )
  ELSE (
    (ts.tenant_min_price > 0 AND ts.tenant_max_price >= ts.tenant_min_price)
    OR ts.tenant_visit_fee > 0
    OR EXISTS (
      SELECT 1 FROM tenant_service_types tst WHERE tst.tenant_service_id=ts.id
      AND tst.is_enabled=true
      AND tst.tenant_min_price > 0 AND tst.tenant_max_price >= tst.tenant_min_price
    )
    OR EXISTS (
      SELECT 1 FROM tenant_service_brands tsb WHERE tsb.tenant_service_id=ts.id
      AND tsb.is_enabled=true
      AND tsb.tenant_min_price > 0 AND tsb.tenant_max_price >= tsb.tenant_min_price
    )
  ) END
"""
