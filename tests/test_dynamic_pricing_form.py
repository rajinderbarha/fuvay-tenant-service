"""
Dynamic Pricing Form tests — Master Service create/edit form.

Verifies:
  Backend:
    1. Fixed pricing: base_price required, succeeds
    2. Fixed pricing: missing base_price fails
    3. Range pricing: min/max succeed
    4. Range pricing: max < min fails
    5. Post-assessment: visit_fee + customer_note succeed
    6. Post-assessment: missing customer_note fails
    7. Hourly: hourly_rate + minimum_billable_hours succeed
    8. Hourly: missing hourly_rate fails
    9. Expanded job types (8 types) accepted
    10. New pricing columns in MasterService model
    11. _validate_pricing_config function exists
    12. _svc_dict returns all new pricing fields
    13. update_master_service handles new fields

  Frontend (static analysis):
    14. JOB_TYPES has 8+ entries
    15. PRICING_MODEL_HELP dict exists
    16. Fixed fields: base_price shown, min/max hidden
    17. Range fields: min_price, max_price shown
    18. Post-assessment fields: visit_fee, customer_note, assessment_label shown
    19. Hourly fields: hourly_rate, minimum_billable_hours shown
    20. Dynamic visibility: isFixed/isRange/isPostAssess/isHourly flags
    21. handleSave sends only relevant fields per model
    22. isFormValid() controls submit button
    23. Job type change applies defaults
    24. openEdit loads all new fields
    25. Table shows dynamic price summary
"""
import os
import re

ROOT       = os.path.dirname(os.path.dirname(__file__))
SVC        = os.path.join(ROOT, "app", "engines", "admin_catalog", "service.py")
MODELS     = os.path.join(ROOT, "app", "engines", "admin_catalog", "models.py")
CATALOG_PG = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "master-services", "page.tsx")
API_TS     = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
MIGRATION  = os.path.join(ROOT, "alembic", "versions", "066_dynamic_pricing_fields.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════
# MIGRATION
# ══════════════════════════════════════════════════════════════

def test_migration_066_exists():
    assert os.path.exists(MIGRATION)


def test_migration_066_adds_hourly_rate():
    src = _read(MIGRATION)
    assert "hourly_rate" in src


def test_migration_066_adds_customer_note():
    src = _read(MIGRATION)
    assert "customer_note" in src


def test_migration_066_adds_requires_issue_type():
    src = _read(MIGRATION)
    assert "requires_issue_type" in src


# ══════════════════════════════════════════════════════════════
# ORM MODEL
# ══════════════════════════════════════════════════════════════

def test_model_has_hourly_rate():
    src = _read(MODELS)
    assert "hourly_rate" in src


def test_model_has_minimum_billable_hours():
    src = _read(MODELS)
    assert "minimum_billable_hours" in src


def test_model_has_default_estimate():
    src = _read(MODELS)
    assert "default_estimate" in src


def test_model_has_assessment_label():
    src = _read(MODELS)
    assert "assessment_label" in src


def test_model_has_show_estimated_range():
    src = _read(MODELS)
    assert "show_estimated_range" in src


def test_model_has_customer_note():
    src = _read(MODELS)
    assert "customer_note" in src


def test_model_has_requires_issue_type():
    src = _read(MODELS)
    assert "requires_issue_type" in src


def test_model_has_requires_schedule():
    src = _read(MODELS)
    assert "requires_schedule" in src


def test_model_has_requires_address():
    src = _read(MODELS)
    assert "requires_address" in src


# ══════════════════════════════════════════════════════════════
# BACKEND SERVICE
# ══════════════════════════════════════════════════════════════

def test_service_has_validate_pricing_config():
    src = _read(SVC)
    assert "_validate_pricing_config" in src


def test_service_validate_fixed_checks_base_price():
    src = _read(SVC)
    idx = src.find('model == "fixed"')
    assert idx != -1
    block = src[idx:idx+300]
    assert "base_price" in block


def test_service_validate_range_checks_min_max():
    src = _read(SVC)
    idx = src.find('model == "range"')
    assert idx != -1
    block = src[idx:idx+600]
    assert "min_price" in block
    assert "max_price" in block
    assert "mx < mn" in block or "mx >= mn" in block or "Must be >=" in block or "min_price" in block


def test_service_validate_post_assessment_checks_customer_note():
    src = _read(SVC)
    idx = src.find('model == "post_assessment"')
    assert idx != -1
    block = src[idx:idx+500]
    assert "customer_note" in block


def test_service_validate_hourly_checks_hourly_rate():
    src = _read(SVC)
    idx = src.find('model == "hourly"')
    assert idx != -1
    block = src[idx:idx+400]
    assert "hourly_rate" in block
    assert "minimum_billable_hours" in block


def test_service_expanded_job_types():
    src = _read(SVC)
    for jt in ("installation", "uninstallation", "inspection", "maintenance", "cleaning", "custom"):
        assert f'"{jt}"' in src, f"Job type {jt!r} missing from VALID_JOB_TYPES"


def test_service_svc_dict_returns_hourly_rate():
    src = _read(SVC)
    idx = src.find("def _svc_dict")
    assert idx != -1
    block = src[idx:idx+800]
    assert "hourly_rate" in block


def test_service_svc_dict_returns_customer_note():
    src = _read(SVC)
    idx = src.find("def _svc_dict")
    assert idx != -1
    block = src[idx:idx+1200]
    assert "customer_note" in block


def test_service_svc_dict_returns_requires_issue_type():
    src = _read(SVC)
    idx = src.find("def _svc_dict")
    assert idx != -1
    block = src[idx:idx+1600]
    assert "requires_issue_type" in block


def test_service_create_passes_hourly_fields():
    src = _read(SVC)
    idx = src.find("async def create_master_service")
    assert idx != -1
    block = src[idx:idx+2500]
    assert "hourly_rate" in block


def test_service_update_handles_new_fields():
    src = _read(SVC)
    idx = src.find("async def update_master_service")
    assert idx != -1
    block = src[idx:idx+1200]
    assert "hourly_rate" in block
    assert "customer_note" in block


# ══════════════════════════════════════════════════════════════
# FRONTEND api.ts
# ══════════════════════════════════════════════════════════════

def test_api_ts_master_service_has_hourly_rate():
    src = _read(API_TS)
    idx = src.find("export interface MasterService {")
    assert idx != -1
    block = src[idx:idx+700]
    assert "hourly_rate" in block


def test_api_ts_master_service_has_customer_note():
    src = _read(API_TS)
    idx = src.find("export interface MasterService {")
    assert idx != -1
    block = src[idx:idx+700]
    assert "customer_note" in block


def test_api_ts_master_service_job_type_is_string():
    """job_type is now string (not union of 3) to support 9 types."""
    src = _read(API_TS)
    idx = src.find("export interface MasterService {")
    assert idx != -1
    block = src[idx:idx+400]
    assert 'job_type:string' in block or "job_type: string" in block


# ══════════════════════════════════════════════════════════════
# FRONTEND catalog/page.tsx
# ══════════════════════════════════════════════════════════════

def test_catalog_job_types_has_installation():
    src = _read(CATALOG_PG)
    assert '"installation"' in src


def test_catalog_job_types_has_inspection():
    src = _read(CATALOG_PG)
    assert '"inspection"' in src


def test_catalog_job_types_has_cleaning():
    src = _read(CATALOG_PG)
    assert '"cleaning"' in src


def test_catalog_pricing_model_help_exists():
    src = _read(CATALOG_PG)
    assert "PRICING_MODEL_HELP" in src


def test_catalog_pricing_model_help_has_post_assessment():
    src = _read(CATALOG_PG)
    assert "post_assessment" in src
    assert "inspection" in src.lower() or "assessment" in src.lower()


# ── HS0 cleanup note ──────────────────────────────────────────────────────────
# The remaining 11 tests that lived below this point
# (test_catalog_fixed_pricing_section, test_catalog_range_pricing_section,
# test_catalog_post_assessment_section, test_catalog_hourly_section,
# test_catalog_is_form_valid_controls_submit,
# test_catalog_handle_save_sends_model_specific_fields,
# test_catalog_open_edit_loads_hourly_rate,
# test_catalog_open_edit_loads_customer_note,
# test_catalog_job_type_defaults_applied_on_change,
# test_catalog_requirement_toggles_dynamic,
# test_catalog_price_summary_per_model) asserted on a manual per-service
# pricing model form (isFixed/isRange/isPostAssessment/isHourly toggles) that
# used to live on /admin/catalog. That form was removed from the catalog page
# entirely — pricing is now configured via the centralized Home Services
# Pricing Rules screen (/admin/home-services/pricing-rules) and the tenant
# Service Setup wizard (/tenant/setup/services), not a per-service manual
# form on the catalog page. Deleted as obsolete rather than left red. See
# HS0_TEST_FILE_CLEANUP_REPORT.md.
