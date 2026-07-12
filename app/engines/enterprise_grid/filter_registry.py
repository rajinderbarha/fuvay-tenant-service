"""Sprint 26 — Enterprise Filter Registry.

Each resource config defines:
  allowed_filters, allowed_sort_fields, default_sort,
  search_fields, available_columns, sensitive_fields,
  scope_type, allowed_export_fields
"""
from __future__ import annotations
from app.engines.enterprise_grid.constants import (
    SCOPE_ADMIN_GLOBAL, SCOPE_PROVIDER,
    ERR_GRID_RESOURCE_NOT_FOUND,
)

# ── Column helper ──────────────────────────────────────────────────────────────
def col(key: str, label: str, order: int, visible: bool = True, width: int = 160) -> dict:
    return {"key": key, "label": label, "visible": visible, "order": order, "width": width}


# ── FINAL-L5-05O — Export permission mapping ────────────────────────────────
# create_export_job() previously had zero domain-permission gating (only
# get_current_user) -- ANY authenticated role could export ANY of the 33
# registered resources, including Finance/Security-sensitive ones. This maps
# the Finance/Security/Operations-sensitive resources to a real, existing
# backend export-shaped permission (never a read permission -- read must not
# imply export, per rule 9). Resources not listed here remain reachable by
# any authenticated admin (a documented, bounded-scope residual gap for the
# ~25 lower-sensitivity catalog/operational resources not covered this
# sprint -- see FINAL_L5_05O bug register).
RESOURCE_EXPORT_PERMISSIONS: dict[str, str] = {
    "admin_finance_deposits":     "finance:hub:export",
    "admin_finance_topups":       "finance:hub:export",
    "admin_finance_claims":       "finance:hub:export",
    "admin_finance_payouts":      "finance:hub:export",
    "admin_finance_wallets":      "finance:hub:export",
    "admin_security_threats":     "security:audit:export",
    "admin_security_sessions":    "security:audit:export",
    "admin_ip_blocklist":         "security:audit:export",
    "admin_api_keys":             "security:audit:export",
    "admin_audit_logs":           "security:audit:export",
    "admin_setting_audit_logs":   "security:audit:export",
    "admin_service_jobs":         "field_ops:jobs:export",
}


# ── Resource configurations ───────────────────────────────────────────────────
_RESOURCE_CONFIGS: dict[str, dict] = {

    # ── ADMIN resources ────────────────────────────────────────────────────────

    "admin_tenants": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "category_id", "search", "created_from", "created_to"],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "business_name"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["business_name", "contact_email", "subdomain"],
        "available_columns": [
            col("business_name", "Business Name", 1),
            col("status", "Status", 2, width=120),
            col("contact_email", "Email", 3),
            col("subdomain", "Subdomain", 4, visible=False),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": ["internal_admin_notes", "billing_info"],
        "allowed_export_fields": ["business_name", "status", "contact_email", "subdomain", "created_at"],
    },

    "admin_categories": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "search", "created_from", "created_to"],
        "allowed_sort_fields": ["created_at", "updated_at", "name", "status"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["name", "slug"],
        "available_columns": [
            col("name", "Category Name", 1),
            col("slug", "Slug", 2),
            col("status", "Status", 3, width=120),
            col("created_at", "Created", 4, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["name", "slug", "status", "created_at"],
    },

    "admin_engines": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "search", "can_disable"],
        "allowed_sort_fields": ["created_at", "engine_key", "status"],
        "default_sort": {"sort_by": "engine_key", "sort_direction": "asc"},
        "search_fields": ["engine_key", "engine_name"],
        "available_columns": [
            col("engine_key", "Engine Key", 1),
            col("engine_name", "Name", 2),
            col("status", "Status", 3, width=120),
            col("can_disable", "Can Disable", 4, width=120),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["engine_key", "engine_name", "status"],
    },

    "admin_offerings": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "category_id", "tenant_id", "search", "created_from", "created_to"],
        "allowed_sort_fields": ["created_at", "updated_at", "name", "status"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["name", "offering_code"],
        "available_columns": [
            col("name", "Offering Name", 1),
            col("offering_code", "Code", 2),
            col("status", "Status", 3, width=120),
            col("category_id", "Category", 4),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["name", "offering_code", "status", "created_at"],
    },

    "admin_service_bookings": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "tenant_id", "category_id", "offering_id", "customer_id",
            "search", "date_from", "date_to", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "booking_number", "scheduled_date"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["booking_number"],
        "available_columns": [
            col("booking_number", "Booking #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("scheduled_date", "Scheduled", 3),
            col("category_id", "Category", 4, visible=False),
            col("tenant_id", "Tenant", 5),
            col("created_at", "Created", 6, width=140),
        ],
        "sensitive_fields": ["customer_private_notes", "internal_notes"],
        "allowed_export_fields": ["booking_number", "status", "scheduled_date", "created_at"],
    },

    "admin_service_jobs": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "assignment_status", "tenant_id", "category_id", "offering_id",
            "search", "date_from", "date_to", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "job_number"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["job_number", "booking_number"],
        "available_columns": [
            col("job_number", "Job #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("assignment_status", "Assignment", 3, width=140),
            col("tenant_id", "Tenant", 4),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": ["internal_admin_notes"],
        "allowed_export_fields": ["job_number", "status", "assignment_status", "created_at"],
    },

    "admin_coaching_appointments": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "tenant_id", "category_id", "customer_id",
            "search", "date_from", "date_to", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "appointment_number", "scheduled_at"],
        "default_sort": {"sort_by": "scheduled_at", "sort_direction": "desc"},
        "search_fields": ["appointment_number"],
        "available_columns": [
            col("appointment_number", "Appointment #", 1, width=160),
            col("status", "Status", 2, width=120),
            col("scheduled_at", "Scheduled", 3),
            col("tenant_id", "Tenant", 4),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": ["session_notes"],
        "allowed_export_fields": ["appointment_number", "status", "scheduled_at", "created_at"],
    },

    "admin_real_estate_leads": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "tenant_id", "customer_id",
            "search", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "lead_number"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["lead_number"],
        "available_columns": [
            col("lead_number", "Lead #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("tenant_id", "Tenant", 3),
            col("created_at", "Created", 4, width=140),
        ],
        "sensitive_fields": ["private_agent_notes", "customer_phone"],
        "allowed_export_fields": ["lead_number", "status", "created_at"],
    },

    "admin_service_invoices": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "payment_status", "tenant_id", "customer_id",
            "search", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "invoice_number", "total_amount"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["invoice_number"],
        "available_columns": [
            col("invoice_number", "Invoice #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("payment_status", "Payment", 3, width=120),
            col("total_amount", "Amount", 4, width=120),
            col("tenant_id", "Tenant", 5),
            col("created_at", "Created", 6, width=140),
        ],
        "sensitive_fields": ["internal_finance_notes"],
        "allowed_export_fields": ["invoice_number", "status", "payment_status", "total_amount", "created_at"],
    },

    "admin_payments": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "tenant_id", "payment_method",
            "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "amount"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["payment_reference", "gateway_transaction_id"],
        "available_columns": [
            col("payment_reference", "Reference", 1),
            col("status", "Status", 2, width=120),
            col("amount", "Amount", 3, width=120),
            col("payment_method", "Method", 4),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": ["raw_gateway_response"],
        "allowed_export_fields": ["payment_reference", "status", "amount", "payment_method", "created_at"],
    },

    "admin_commission_records": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "commission_status", "tenant_id",
            "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "commission_amount"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["commission_reference"],
        "available_columns": [
            col("commission_reference", "Reference", 1),
            col("status", "Status", 2, width=120),
            col("commission_amount", "Amount", 3, width=120),
            col("tenant_id", "Tenant", 4),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": ["internal_commission_rule"],
        "allowed_export_fields": ["commission_reference", "status", "commission_amount", "created_at"],
    },

    "admin_reviews": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "review_status", "tenant_id", "customer_id",
            "record_type", "search", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "overall_rating"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["review_number"],
        "available_columns": [
            col("review_number", "Review #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("overall_rating", "Rating", 3, width=100),
            col("record_type", "Record Type", 4),
            col("tenant_id", "Tenant", 5),
            col("created_at", "Created", 6, width=140),
        ],
        "sensitive_fields": ["internal_moderation_notes"],
        "allowed_export_fields": ["review_number", "status", "overall_rating", "record_type", "created_at"],
    },

    "admin_complaints": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "complaint_status", "priority", "tenant_id", "customer_id",
            "record_type", "search", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "priority", "complaint_number"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["complaint_number"],
        "available_columns": [
            col("complaint_number", "Complaint #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("priority", "Priority", 3, width=100),
            col("complaint_type", "Type", 4),
            col("tenant_id", "Tenant", 5),
            col("created_at", "Created", 6, width=140),
        ],
        "sensitive_fields": ["internal_admin_notes"],
        "allowed_export_fields": ["complaint_number", "status", "priority", "complaint_type", "created_at"],
    },

    "admin_refund_requests": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "tenant_id", "customer_id",
            "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "requested_amount"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": [],
        "available_columns": [
            col("status", "Status", 1, width=120),
            col("refund_type", "Type", 2),
            col("requested_amount", "Requested", 3, width=120),
            col("approved_amount", "Approved", 4, width=120),
            col("tenant_id", "Tenant", 5),
            col("created_at", "Created", 6, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["status", "refund_type", "requested_amount", "approved_amount", "created_at"],
    },

    "admin_rework_requests": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "status", "tenant_id",
            "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": [],
        "available_columns": [
            col("status", "Status", 1, width=120),
            col("rework_reason", "Reason", 2),
            col("scheduled_date", "Scheduled", 3),
            col("tenant_id", "Tenant", 4),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": ["admin_notes"],
        "allowed_export_fields": ["status", "rework_reason", "scheduled_date", "created_at"],
    },

    "admin_pricing_tiers": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "is_active", "q", "used_in_rules", "has_city_mapping", "has_zipcode_mapping",
            "date_from", "date_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "name", "code"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["name", "code"],
        "available_columns": [
            col("name", "Tier", 1),
            col("tier_type", "Type", 2, width=120),
            col("base_multiplier", "Multiplier", 3, width=120),
            col("platform_fee_percent", "Platform Fee", 4, width=120),
            col("default_sla_minutes", "Default SLA", 5, width=120),
            col("is_active", "Status", 6, width=100),
            col("updated_at", "Updated", 7, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["name", "code", "tier_type", "base_multiplier",
                                  "platform_fee_percent", "default_sla_minutes", "is_active"],
    },

    "admin_tier_locations": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "tier_id", "q", "state", "district", "city", "zipcode", "is_active", "has_conflict",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "city", "zipcode", "priority"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["city", "zipcode", "state", "district"],
        "available_columns": [
            col("city", "Location", 1),
            col("zipcode", "Zipcode", 2, width=120),
            col("district", "District", 3),
            col("state", "State", 4),
            col("country", "Country", 5, width=100),
            col("tier_name", "Tier", 6, width=140),
            col("zone_name", "Zone", 7, width=120),
            col("conflict_status", "Conflict Status", 8, width=140),
            col("is_active", "Status", 9, width=100),
            col("updated_at", "Updated", 10, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["city", "zipcode", "district", "state", "country",
                                  "tier_name", "zone_name", "conflict_status", "is_active"],
    },

    "admin_pricing_rules": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "master_service_id", "is_active", "q", "brand_id", "service_type_id", "tier_id",
            "city", "zipcode", "pricing_model", "expiring_within_days", "rule_status",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "priority", "base_price"],
        "default_sort": {"sort_by": "priority", "sort_direction": "desc"},
        "search_fields": ["rule_name", "rule_code"],
        "available_columns": [
            col("rule_name", "Rule", 1),
            col("pricing_model", "Pricing Model", 2, width=140),
            col("base_price", "Price", 3, width=120),
            col("bargain_floor", "Bargain Floor", 4, width=130),
            col("priority", "Priority", 5, width=100),
            col("effective_to", "Validity", 6, width=140),
            col("is_active", "Status", 7, width=100),
            col("updated_at", "Updated", 8, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["rule_name", "rule_code", "pricing_model", "base_price",
                                  "bargain_floor", "priority", "effective_from", "effective_to", "is_active"],
    },

    "admin_finance_deposits": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "vertical", "state", "city", "q"],
        "allowed_sort_fields": ["created_at", "required_amount"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["tenant_name"],
        "available_columns": [
            col("tenant_name", "Tenant", 1),
            col("required_amount", "Required Amount", 2, width=140),
            col("received_amount", "Received Amount", 3, width=140),
            col("pending_amount", "Pending Amount", 4, width=140),
            col("status", "Status", 5, width=140),
            col("hold_state", "Hold State", 6, width=120),
            col("created_at", "Created", 7, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["tenant_name", "required_amount", "received_amount", "status", "created_at"],
    },

    "admin_finance_topups": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["payment_status", "tenant_id", "q"],
        "allowed_sort_fields": ["created_at", "amount_paid"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["order_ref", "tenant_name"],
        "available_columns": [
            col("tenant_name", "Tenant", 1),
            col("order_ref", "Order Ref", 2, width=160),
            col("credits_purchased", "Credits Purchased", 3, width=150),
            col("amount_paid", "Amount Paid", 4, width=130),
            col("payment_method", "Payment Method", 5, width=140),
            col("payment_status", "Payment Status", 6, width=140),
            col("wallet_credit_status", "Wallet Credit Status", 7, width=150),
            col("created_at", "Created", 8, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["tenant_name", "order_ref", "credits_purchased", "amount_paid", "payment_status", "created_at"],
    },

    "admin_finance_claims": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "category", "q"],
        "allowed_sort_fields": ["created_at", "amount_requested"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["job_id", "tenant_name"],
        "available_columns": [
            col("tenant_name", "Tenant", 1),
            col("job_id", "Booking / Job", 2, width=140),
            col("claim_type", "Issue Type", 3, width=140),
            col("amount_requested", "Claim Amount", 4, width=130),
            col("status", "Status", 5, width=140),
            col("assigned_reviewer_id", "Assigned Reviewer", 6, width=160),
            col("created_at", "Raised On", 7, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["tenant_name", "job_id", "claim_type", "amount_requested", "status", "created_at"],
    },

    "admin_finance_payouts": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "tenant_id", "q"],
        "allowed_sort_fields": ["created_at", "amount"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["payout_number", "tenant_name"],
        "available_columns": [
            col("payout_number", "Payout Ref", 1, width=140),
            col("tenant_name", "Tenant / Beneficiary", 2),
            col("payout_type", "Payout Type", 3, width=140),
            col("requested_amount", "Requested Amount", 4, width=150),
            col("approved_amount", "Approved Amount", 5, width=150),
            col("status", "Status", 6, width=140),
            col("requested_on", "Requested On", 7, width=140),
            col("processed_on", "Processed On", 8, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["payout_number", "tenant_name", "payout_type", "requested_amount", "status", "requested_on"],
    },

    "admin_finance_wallets": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["health_band", "q"],
        "allowed_sort_fields": ["available_balance"],
        "default_sort": {"sort_by": "available_balance", "sort_direction": "asc"},
        "search_fields": ["tenant_name"],
        "available_columns": [
            col("tenant_name", "Tenant", 1),
            col("available_balance", "Available Balance", 2, width=150),
            col("reserved_balance", "Reserved Balance", 3, width=150),
            col("health_band", "Health Band", 4, width=130),
            col("last_transaction_at", "Last Transaction", 5, width=150),
            col("is_active", "Status", 6, width=100),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["tenant_name", "available_balance", "reserved_balance", "health_band"],
    },

    "admin_audit_logs": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": [
            "record_type", "tenant_id", "customer_id",
            "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": [],
        "available_columns": [
            col("event_type", "Event", 1),
            col("record_type", "Record Type", 2),
            col("actor_type", "Actor", 3),
            col("tenant_id", "Tenant", 4),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": ["raw_payload"],
        "allowed_export_fields": ["event_type", "record_type", "actor_type", "created_at"],
    },

    "admin_security_threats": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "threat_level", "activity_type", "search"],
        "allowed_sort_fields": ["created_at", "risk_score", "threat_level"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["threat_number", "description", "ip_address"],
        "available_columns": [
            col("threat_number", "Threat #", 1, width=120),
            col("activity_type", "Type", 2),
            col("threat_level", "Level", 3, width=100),
            col("risk_score", "Risk Score", 4, width=100),
            col("ip_address", "IP Address", 5, width=140),
            col("status", "Status", 6, width=120),
            col("created_at", "Detected", 7, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["threat_number", "activity_type", "threat_level", "risk_score",
                                   "ip_address", "status", "created_at"],
    },

    "admin_security_sessions": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["role", "active_only", "search"],
        "allowed_sort_fields": ["last_active_at"],
        "default_sort": {"sort_by": "last_active_at", "sort_direction": "desc"},
        "search_fields": ["user_email", "user_name", "ip_address"],
        "available_columns": [
            col("user_email", "User", 1),
            col("user_role", "Role", 2, width=120),
            col("device_name", "Device", 3),
            col("ip_address", "IP Address", 4, width=140),
            col("status", "Status", 5, width=100),
            col("last_active_at", "Last Active", 6, width=150),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["user_email", "user_role", "device_name", "ip_address",
                                   "status", "last_active_at"],
    },

    "admin_ip_blocklist": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "scope", "search"],
        "allowed_sort_fields": ["created_at", "hit_count"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["ip_or_cidr"],
        "available_columns": [
            col("ip_or_cidr", "IP / CIDR", 1, width=160),
            col("threat_level", "Threat Level", 2, width=120),
            col("scope", "Scope", 3, width=120),
            col("status", "Status", 4, width=100),
            col("hit_count", "Hits", 5, width=80),
            col("created_at", "Blocked", 6, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["ip_or_cidr", "threat_level", "scope", "status", "hit_count", "created_at"],
    },

    "admin_api_keys": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["tenant_id", "status", "search"],
        "allowed_sort_fields": ["created_at", "use_count"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["name"],
        "available_columns": [
            col("name", "Name", 1),
            col("key_prefix", "Key Prefix", 2, width=160),
            col("environment", "Environment", 3, width=120),
            col("status", "Status", 4, width=100),
            col("use_count", "Uses", 5, width=80),
            col("created_at", "Created", 6, width=140),
        ],
        "sensitive_fields": ["key_hash"],
        "allowed_export_fields": ["name", "key_prefix", "environment", "status", "use_count", "created_at"],
    },

    "admin_customers": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["health_band", "city", "state", "zipcode", "has_complaints",
                             "has_reviews", "booking_count_min", "booking_count_max", "search"],
        "allowed_sort_fields": ["created_at", "last_booking_at", "total_bookings", "full_name"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["full_name", "phone", "email"],
        "available_columns": [
            col("full_name", "Customer", 1),
            col("phone", "Phone", 2, width=130),
            col("email", "Email", 3),
            col("city", "City", 4, width=120),
            col("health_band", "Health", 5, width=120),
            col("total_bookings", "Bookings", 6, width=100),
            col("complaints_count", "Issues", 7, width=90),
            col("last_booking_at", "Last Booking", 8, width=150),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["full_name", "phone", "email", "city", "state", "zipcode",
                                   "health_band", "total_bookings", "completed_bookings",
                                   "cancelled_bookings", "complaints_count", "reviews_count",
                                   "average_rating", "last_booking_at", "created_at"],
    },

    "admin_settings": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["category", "is_secret", "status", "search"],
        "allowed_sort_fields": ["key", "category", "risk_level"],
        "default_sort": {"sort_by": "key", "sort_direction": "asc"},
        "search_fields": ["key", "label", "description"],
        "available_columns": [
            col("label", "Setting", 1),
            col("key", "Key", 2, width=180),
            col("category", "Category", 3, width=160),
            col("type", "Type", 4, width=100),
            col("risk_level", "Risk", 5, width=100),
            col("status", "Status", 6, width=100),
        ],
        "sensitive_fields": ["value"],
        "allowed_export_fields": ["key", "label", "category", "type", "risk_level", "status"],
    },

    "admin_feature_flags": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["status", "rollout_type", "search"],
        "allowed_sort_fields": ["flag_key", "status"],
        "default_sort": {"sort_by": "flag_key", "sort_direction": "asc"},
        "search_fields": ["flag_key", "label"],
        "available_columns": [
            col("label", "Flag", 1),
            col("flag_key", "Key", 2, width=180),
            col("status", "Status", 3, width=100),
            col("rollout_type", "Rollout", 4, width=120),
            col("rollout_percent", "Percent", 5, width=90),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["flag_key", "label", "status", "rollout_type", "rollout_percent"],
    },

    "admin_setting_audit_logs": {
        "scope_type": SCOPE_ADMIN_GLOBAL,
        "allowed_filters": ["key", "tenant_id", "risk_level", "action_type"],
        "allowed_sort_fields": ["created_at"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["key"],
        "available_columns": [
            col("key", "Setting", 1),
            col("tier", "Scope", 2, width=100),
            col("action_type", "Action", 3, width=120),
            col("risk_level", "Risk", 4, width=100),
            col("created_at", "Changed", 5, width=150),
        ],
        "sensitive_fields": ["old_value", "new_value"],
        "allowed_export_fields": ["key", "tier", "action_type", "risk_level", "created_at"],
    },

    # ── PROVIDER resources ─────────────────────────────────────────────────────

    "provider_service_jobs": {
        "scope_type": SCOPE_PROVIDER,
        "allowed_filters": [
            "status", "assignment_status", "offering_id", "staff_member_id",
            "search", "date_from", "date_to", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "job_number"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["job_number"],
        "available_columns": [
            col("job_number", "Job #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("assignment_status", "Assignment", 3, width=140),
            col("offering_id", "Offering", 4),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["job_number", "status", "assignment_status", "created_at"],
    },

    "provider_service_invoices": {
        "scope_type": SCOPE_PROVIDER,
        "allowed_filters": [
            "status", "payment_status",
            "search", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "invoice_number", "total_amount"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["invoice_number"],
        "available_columns": [
            col("invoice_number", "Invoice #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("payment_status", "Payment", 3, width=120),
            col("total_amount", "Amount", 4, width=120),
            col("created_at", "Created", 5, width=140),
        ],
        "sensitive_fields": ["internal_finance_notes"],
        "allowed_export_fields": ["invoice_number", "status", "payment_status", "total_amount", "created_at"],
    },

    "provider_wallet_ledger": {
        "scope_type": SCOPE_PROVIDER,
        "allowed_filters": [
            "type", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "amount", "type"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["reference"],
        "available_columns": [
            col("reference", "Reference", 1),
            col("type", "Type", 2, width=120),
            col("amount", "Amount", 3, width=120),
            col("balance_after", "Balance After", 4, width=140),
            col("created_at", "Date", 5, width=140),
        ],
        "sensitive_fields": ["internal_wallet_metadata"],
        "allowed_export_fields": ["reference", "type", "amount", "balance_after", "created_at"],
    },

    "provider_reviews": {
        "scope_type": SCOPE_PROVIDER,
        "allowed_filters": [
            "status", "record_type",
            "search", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "overall_rating"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["review_number"],
        "available_columns": [
            col("review_number", "Review #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("overall_rating", "Rating", 3, width=100),
            col("record_type", "Record Type", 4),
            col("created_at", "Date", 5, width=140),
        ],
        "sensitive_fields": [],
        "allowed_export_fields": ["review_number", "status", "overall_rating", "record_type", "created_at"],
    },

    "provider_complaints": {
        "scope_type": SCOPE_PROVIDER,
        "allowed_filters": [
            "status", "priority", "record_type",
            "search", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status", "priority"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["complaint_number"],
        "available_columns": [
            col("complaint_number", "Complaint #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("priority", "Priority", 3, width=100),
            col("complaint_type", "Type", 4),
            col("created_at", "Date", 5, width=140),
        ],
        "sensitive_fields": ["internal_admin_notes"],
        "allowed_export_fields": ["complaint_number", "status", "priority", "complaint_type", "created_at"],
    },

    "provider_coaching_appointments": {
        "scope_type": SCOPE_PROVIDER,
        "allowed_filters": [
            "status",
            "date_from", "date_to", "created_from", "created_to",
        ],
        "allowed_sort_fields": ["scheduled_at", "created_at", "status"],
        "default_sort": {"sort_by": "scheduled_at", "sort_direction": "desc"},
        "search_fields": ["appointment_number"],
        "available_columns": [
            col("appointment_number", "Appointment #", 1, width=160),
            col("status", "Status", 2, width=120),
            col("scheduled_at", "Scheduled", 3),
            col("created_at", "Created", 4, width=140),
        ],
        "sensitive_fields": ["session_notes"],
        "allowed_export_fields": ["appointment_number", "status", "scheduled_at", "created_at"],
    },

    "provider_real_estate_leads": {
        "scope_type": SCOPE_PROVIDER,
        "allowed_filters": [
            "status",
            "created_from", "created_to",
        ],
        "allowed_sort_fields": ["created_at", "updated_at", "status"],
        "default_sort": {"sort_by": "created_at", "sort_direction": "desc"},
        "search_fields": ["lead_number"],
        "available_columns": [
            col("lead_number", "Lead #", 1, width=140),
            col("status", "Status", 2, width=120),
            col("created_at", "Created", 3, width=140),
        ],
        "sensitive_fields": ["private_agent_notes", "customer_phone"],
        "allowed_export_fields": ["lead_number", "status", "created_at"],
    },
}


class EnterpriseFilterRegistry:
    """Central registry for all enterprise grid resource configs."""

    @classmethod
    def get_config(cls, resource_key: str) -> dict:
        cfg = _RESOURCE_CONFIGS.get(resource_key)
        if not cfg:
            raise ValueError(ERR_GRID_RESOURCE_NOT_FOUND)
        return cfg

    @classmethod
    def resource_exists(cls, resource_key: str) -> bool:
        return resource_key in _RESOURCE_CONFIGS

    @classmethod
    def all_resource_keys(cls) -> list[str]:
        return list(_RESOURCE_CONFIGS.keys())

    @classmethod
    def required_export_permission(cls, resource_key: str) -> str | None:
        """FINAL-L5-05O: returns the export-shaped permission required to
        export this resource, or None if the resource has no explicit
        export gate (documented residual scope, not an oversight)."""
        return RESOURCE_EXPORT_PERMISSIONS.get(resource_key)

    @classmethod
    def validate_filter(cls, resource_key: str, filter_key: str) -> bool:
        cfg = cls.get_config(resource_key)
        return filter_key in cfg["allowed_filters"]

    @classmethod
    def validate_sort(cls, resource_key: str, sort_by: str) -> bool:
        cfg = cls.get_config(resource_key)
        return sort_by in cfg["allowed_sort_fields"]

    @classmethod
    def validate_columns(cls, resource_key: str, column_keys: list[str]) -> list[str]:
        cfg     = cls.get_config(resource_key)
        allowed = {c["key"] for c in cfg["available_columns"]}
        blocked = cfg.get("sensitive_fields", [])
        return [k for k in column_keys if k not in allowed or k in blocked]

    @classmethod
    def is_sensitive(cls, resource_key: str, field: str) -> bool:
        cfg = cls.get_config(resource_key)
        return field in cfg.get("sensitive_fields", [])

    @classmethod
    def get_scope_type(cls, resource_key: str) -> str:
        return cls.get_config(resource_key)["scope_type"]

    @classmethod
    def get_default_sort(cls, resource_key: str) -> dict:
        return cls.get_config(resource_key)["default_sort"]

    @classmethod
    def get_available_columns(cls, resource_key: str) -> list[dict]:
        return cls.get_config(resource_key)["available_columns"]

    @classmethod
    def get_allowed_export_fields(cls, resource_key: str) -> list[str]:
        return cls.get_config(resource_key).get("allowed_export_fields", [])
