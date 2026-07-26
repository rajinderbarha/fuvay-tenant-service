"""Serviceability Engine — Constants."""
from __future__ import annotations


class CoverageType:
    CITY    = "city"
    ZIPCODE = "zipcode"
    ZONE    = "zone"
    RADIUS  = "radius"
    ALL     = [CITY, ZIPCODE, ZONE, RADIUS]


class MatchLevel:
    ZIPCODE = "zipcode"
    ZONE    = "zone"
    CITY    = "city"
    RADIUS  = "radius"


# Lower = higher priority rank
MATCH_LEVEL_PRIORITY: dict[str, int] = {
    MatchLevel.ZIPCODE: 1,
    MatchLevel.ZONE:    2,
    MatchLevel.CITY:    3,
    MatchLevel.RADIUS:  4,
}

# MODULE-L5-02 fix: this must stay aligned with the canonical catalog job types
# (app/engines/admin_catalog/service.py::VALID_JOB_TYPES). It was previously a
# stale 3-item subset (["repair","service","consultation"]), so a tenant could
# not create a service-area coverage mapping for any service whose canonical
# job_type was installation/uninstallation/inspection/maintenance/cleaning/
# custom — meaning those services could never be covered in an area and thus
# never became customer-bookable. Kept as a list (schema/description consumers)
# but now covering the full canonical set.
JOB_TYPES = ["repair", "installation", "uninstallation", "inspection",
             "maintenance", "cleaning", "consultation", "service", "custom"]

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_ADDRESS_NOT_FOUND  = "CUSTOMER_ADDRESS_NOT_FOUND"
ERR_ADDRESS_DENIED     = "CUSTOMER_ADDRESS_ACCESS_DENIED"
ERR_ADDRESS_REQUIRED   = "CUSTOMER_ADDRESS_REQUIRED"
ERR_DEFAULT_REQUIRED   = "DEFAULT_ADDRESS_REQUIRED"
ERR_INVALID_ZIPCODE    = "INVALID_ZIPCODE"
ERR_INVALID_CITY       = "INVALID_CITY"
ERR_SERVICE_NOT_FOUND  = "SERVICE_NOT_FOUND"
ERR_SERVICE_NOT_ACTIVE = "SERVICE_NOT_ACTIVE"
ERR_NOT_AVAILABLE      = "SERVICE_NOT_AVAILABLE_IN_AREA"
ERR_NO_TENANT          = "NO_ACTIVE_TENANT_FOR_AREA"
ERR_NO_STAFF           = "NO_STAFF_CAPACITY_FOR_AREA"
ERR_AREA_NOT_FOUND     = "TENANT_SERVICE_AREA_NOT_FOUND"
ERR_AREA_DENIED        = "TENANT_SERVICE_AREA_ACCESS_DENIED"
ERR_DUPLICATE_AREA     = "DUPLICATE_SERVICE_AREA"
ERR_INVALID_COVERAGE   = "INVALID_COVERAGE_TYPE"
ERR_ZIPCODE_REQUIRED   = "ZIPCODE_REQUIRED_FOR_ZIPCODE_COVERAGE"
ERR_CITY_REQUIRED      = "CITY_REQUIRED_FOR_CITY_COVERAGE"
ERR_ZONE_REQUIRED      = "ZONE_REQUIRED_FOR_ZONE_COVERAGE"
ERR_RADIUS_REQUIRED    = "RADIUS_FIELDS_REQUIRED"
ERR_MAPPING_NOT_FOUND  = "TENANT_SERVICE_AREA_SERVICE_NOT_FOUND"
ERR_DUPLICATE_MAPPING  = "DUPLICATE_SERVICE_AREA_SERVICE"
ERR_INVALID_JOB_TYPE   = "INVALID_JOB_TYPE"
ERR_INVALID_PRICE_RANGE= "INVALID_PRICE_RANGE"
ERR_INVALID_SLA        = "INVALID_SLA_MINUTES"

# ── Step 3 — Serviceability check / matching request validation ───────────────
ERR_CHECK_CITY_REQUIRED    = "CITY_REQUIRED"
ERR_CHECK_STATE_REQUIRED   = "STATE_REQUIRED"
ERR_CHECK_ZIPCODE_REQUIRED = "ZIPCODE_REQUIRED"
ERR_SERVICE_ID_REQUIRED    = "SERVICE_ID_REQUIRED"
ERR_LOCATION_REQUIRED      = "LOCATION_REQUIRED"
ERR_LAT_LNG_REQUIRED_RADIUS= "LAT_LNG_REQUIRED_FOR_RADIUS"
ERR_ZONE_MAPPING_MISSING   = "ZONE_MAPPING_NOT_CONFIGURED"
ERR_INVALID_REQUEST        = "INVALID_SERVICEABILITY_REQUEST"

ERR_LIMIT_REACHED      = "SERVICE_AREA_LIMIT_REACHED"

# ── Service-area coverage-approval workflow ────────────────────────────────────
ERR_REQUEST_NOT_FOUND       = "SERVICE_AREA_REQUEST_NOT_FOUND"
ERR_REQUEST_NOT_EDITABLE    = "SERVICE_AREA_REQUEST_NOT_EDITABLE"
ERR_REQUEST_EMPTY           = "SERVICE_AREA_REQUEST_EMPTY"
ERR_REQUEST_ITEM_NOT_FOUND  = "SERVICE_AREA_REQUEST_ITEM_NOT_FOUND"
ERR_DECISION_REASON_REQUIRED= "DECISION_REASON_REQUIRED"
ERR_INVALID_DECISION        = "INVALID_DECISION"
ERR_TENANT_SERVICE_NOT_FOUND= "TENANT_SERVICE_NOT_FOUND"
ERR_CATEGORY_MISMATCH       = "CATEGORY_MISMATCH"
ERR_COVERAGE_NOT_FOUND      = "TENANT_COVERAGE_NOT_FOUND"
ERR_ALREADY_REVIEWED        = "REQUEST_ALREADY_REVIEWED"

REQUEST_STATUSES = ("DRAFT", "SUBMITTED", "UNDER_REVIEW", "CHANGES_REQUESTED",
                     "PARTIALLY_APPROVED", "APPROVED", "REJECTED", "WITHDRAWN")
REQUEST_TENANT_EDITABLE_STATUSES = ("DRAFT", "CHANGES_REQUESTED")
ITEM_DECISION_STATUSES = ("PENDING", "APPROVED", "REJECTED", "CHANGES_REQUESTED")
COVERAGE_STATUSES = ("ACTIVE", "SUSPENDED", "EXPIRED", "REVOKED")

# Lightweight, deterministic pincode-prefix → (city, district, state, tier)
# lookup used only for the "validation preview" shown when adding a service
# area. This is a small heuristic table, not a full postal/geo database —
# any prefix not listed here resolves to Tier 2 with the submitted city/state
# echoed back unchanged. See TENANT_SERVICE_COVERAGE_REMAINING_BLOCKERS.md.
PINCODE_PREFIX_LOOKUP: dict[str, dict[str, str]] = {
    "141": {"city": "Ludhiana", "district": "Ludhiana", "state": "Punjab", "tier": "tier_2"},
    "160": {"city": "Chandigarh", "district": "Chandigarh", "state": "Chandigarh", "tier": "tier_1"},
    "110": {"city": "New Delhi", "district": "New Delhi", "state": "Delhi", "tier": "tier_1"},
    "400": {"city": "Mumbai", "district": "Mumbai", "state": "Maharashtra", "tier": "tier_1"},
    "560": {"city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "tier": "tier_1"},
    "600": {"city": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "tier": "tier_1"},
    "700": {"city": "Kolkata", "district": "Kolkata", "state": "West Bengal", "tier": "tier_1"},
    "500": {"city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "tier": "tier_1"},
    "380": {"city": "Ahmedabad", "district": "Ahmedabad", "state": "Gujarat", "tier": "tier_1"},
    "302": {"city": "Jaipur", "district": "Jaipur", "state": "Rajasthan", "tier": "tier_2"},
    "226": {"city": "Lucknow", "district": "Lucknow", "state": "Uttar Pradesh", "tier": "tier_2"},
}

ENGINE_ID = "serviceability"
