"""Settings Enterprise Upgrade — Fuvay default global settings (G1-G12).

Single source of truth for both SettingsService.seed_defaults() and its tests.
Every entry becomes one PlatformSetting row keyed by `key`.
"""

CATEGORY_GENERAL = "general_platform"
CATEGORY_ONBOARDING = "tenant_onboarding"
CATEGORY_BOOKING = "booking_and_jobs"
CATEGORY_PRICING = "pricing_and_bargain"
CATEGORY_CREDITS = "packages_and_usage_credits"
CATEGORY_DISPUTES = "disputes_and_customer_credits"
CATEGORY_MEDIA = "media_and_storage"
CATEGORY_NOTIFICATIONS = "notifications"
CATEGORY_COMPLIANCE = "compliance_dpdp"
CATEGORY_SECURITY = "security"
CATEGORY_AI = "ai_deepseek"
CATEGORY_AUDIT = "audit_and_retention"
CATEGORY_MAINTENANCE = "maintenance"
CATEGORY_FEATURE_FLAGS = "feature_flags"

ALL_CATEGORIES = [
    CATEGORY_GENERAL, CATEGORY_ONBOARDING, CATEGORY_BOOKING, CATEGORY_PRICING,
    CATEGORY_CREDITS, CATEGORY_DISPUTES, CATEGORY_MEDIA,
    CATEGORY_NOTIFICATIONS, CATEGORY_COMPLIANCE, CATEGORY_SECURITY, CATEGORY_AI,
    CATEGORY_AUDIT, CATEGORY_MAINTENANCE, CATEGORY_FEATURE_FLAGS,
]


def _s(key, label, value, category, setting_type="boolean", risk="low",
       is_secret=False, requires_approval=False, requires_restart=False,
       owner_module=None, description=None, allowed_values=None):
    return {
        "key": key, "label": label, "value": value, "category": category,
        "setting_type": setting_type, "risk_level": risk, "is_secret": is_secret,
        "requires_approval": requires_approval, "requires_restart": requires_restart,
        "owner_module": owner_module, "description": description,
        "allowed_values": allowed_values,
    }


SERVICEOS_DEFAULT_SETTINGS: list[dict] = [
    # ── G1. General Platform ─────────────────────────────────────────────────
    _s("platform_name", "Platform Name", "Fuvay", CATEGORY_GENERAL, "string"),
    _s("default_country", "Default Country", "India", CATEGORY_GENERAL, "string"),
    _s("default_currency", "Default Currency", "INR", CATEGORY_GENERAL, "currency"),
    _s("default_timezone", "Default Timezone", "Asia/Kolkata", CATEGORY_GENERAL, "string"),
    _s("supported_languages", "Supported Languages", ["en", "hi", "pa"], CATEGORY_GENERAL, "list"),
    _s("customer_login_required", "Customer Login Required", True, CATEGORY_GENERAL),
    _s("tenant_signup_enabled", "Tenant Signup Enabled", True, CATEGORY_GENERAL),
    _s("maintenance_mode_enabled", "Maintenance Mode Enabled", False, CATEGORY_MAINTENANCE,
       risk="critical", requires_approval=True, requires_restart=True),

    # ── G2. Tenant Onboarding ────────────────────────────────────────────────
    _s("tenant_self_registration_enabled", "Tenant Self-Registration Enabled", True, CATEGORY_ONBOARDING),
    _s("tenant_admin_approval_required", "Tenant Admin Approval Required", True, CATEGORY_ONBOARDING, risk="medium"),
    _s("tenant_profile_completion_required_percent", "Profile Completion Required %", 100, CATEGORY_ONBOARDING, "percentage"),
    _s("tenant_document_verification_required", "Document Verification Required", True, CATEGORY_ONBOARDING, risk="medium"),
    _s("tenant_package_starts_after_approval", "Package Starts After Approval", True, CATEGORY_ONBOARDING, risk="high"),
    _s("tenant_included_credits_added_after_approval", "Included Credits Added After Approval", True, CATEGORY_ONBOARDING, risk="high"),
    _s("tenant_bookable_only_after_approval", "Bookable Only After Approval", True, CATEGORY_ONBOARDING, risk="high"),

    # ── G3. Booking & Jobs ───────────────────────────────────────────────────
    _s("home_services_enabled", "Home Services Enabled", True, CATEGORY_BOOKING),
    _s("customer_pays_provider_directly", "Customer Pays Provider Directly", True, CATEGORY_BOOKING,
       risk="critical", description="Core Fuvay Home Services business model — customer pays tenant/provider on-site."),
    _s("payment_collection_enabled", "Payment Collection Enabled", False, CATEGORY_BOOKING,
       risk="critical", requires_approval=True,
       description="Must stay false for Home Services — platform does not collect service payment."),
    _s("tenant_payouts_enabled", "Tenant Payouts Enabled", False, CATEGORY_BOOKING,
       risk="critical", requires_approval=True,
       description="Blocked unless payment_collection_enabled=true — no payouts for direct-payment Home Services."),
    _s("job_credit_deduction_trigger", "Job Credit Deduction Trigger", "job_completed", CATEGORY_BOOKING, "enum",
       allowed_values=["job_completed", "job_assigned", "job_accepted"]),
    _s("booking_assignment_requires_provider_acceptance", "Assignment Requires Provider Acceptance", True, CATEGORY_BOOKING),
    _s("customer_cancellation_releases_reserved_credit", "Cancellation Releases Reserved Credit", True, CATEGORY_BOOKING),
    _s("provider_rejection_no_charge", "Provider Rejection = No Charge", True, CATEGORY_BOOKING),
    _s("max_service_sla_hours", "Max Service SLA (Hours)", 96, CATEGORY_BOOKING, "duration"),
    _s("allow_reschedule", "Allow Reschedule", True, CATEGORY_BOOKING),
    _s("allow_customer_photo_upload", "Allow Customer Photo Upload", True, CATEGORY_BOOKING),

    # ── G4. Pricing & Bargain ────────────────────────────────────────────────
    _s("zone_pricing_enabled", "Zone Pricing Enabled", True, CATEGORY_PRICING),
    _s("zipcode_tier_mapping_enabled", "Zipcode Tier Mapping Enabled", True, CATEGORY_PRICING),
    _s("provider_price_below_platform_min_blocked", "Block Price Below Platform Min", True, CATEGORY_PRICING, risk="medium"),
    _s("bargain_enabled", "Bargain Enabled", True, CATEGORY_PRICING),
    _s("bargain_floor_enforced", "Bargain Floor Enforced", True, CATEGORY_PRICING, risk="medium"),
    _s("bargain_floor_formula", "Bargain Floor Formula", "platform_min_price_plus_fee", CATEGORY_PRICING, "enum",
       allowed_values=["platform_min_price_plus_fee", "platform_min_price"]),

    # ── G5. Packages & Usage Credits ─────────────────────────────────────────
    _s("provider_usage_credits_enabled", "Provider Usage Credits Enabled", True, CATEGORY_CREDITS),
    _s("usage_credit_is_cash_wallet", "Usage Credit Is Cash Wallet", False, CATEGORY_CREDITS,
       risk="critical", description="Must stay false — provider usage credits are not real money."),
    _s("usage_credit_is_withdrawable", "Usage Credit Is Withdrawable", False, CATEGORY_CREDITS,
       risk="critical", description="Must stay false — provider usage credits are not withdrawable."),
    _s("included_job_credits_enabled", "Included Job Credits Enabled", True, CATEGORY_CREDITS),
    _s("completed_job_credit_deduction_enabled", "Completed Job Credit Deduction Enabled", True, CATEGORY_CREDITS),
    _s("credit_low_balance_alert_enabled", "Low Balance Alert Enabled", True, CATEGORY_CREDITS),
    _s("credit_low_balance_threshold", "Low Balance Threshold", 100, CATEGORY_CREDITS, "number"),
    _s("manual_credit_adjustment_requires_reason", "Manual Adjustment Requires Reason", True, CATEGORY_CREDITS, risk="medium"),

    # ── G6. Security Deposit ─────────────────────────────────────────────────

    # ── G7. Disputes & Customer Service Credits ──────────────────────────────
    _s("complaint_enabled", "Complaints Enabled", True, CATEGORY_DISPUTES),
    _s("tenant_dispute_response_window_hours", "Tenant Response Window (Hours)", 24, CATEGORY_DISPUTES, "duration"),
    _s("customer_service_credits_enabled", "Customer Service Credits Enabled", True, CATEGORY_DISPUTES),
    _s("customer_service_credit_is_cash_refund", "Credit Is Cash Refund", False, CATEGORY_DISPUTES,
       risk="critical", description="Must stay false — customer service credit is not a cash refund."),
    _s("customer_service_credit_expiry_days", "Credit Expiry (Days)", 180, CATEGORY_DISPUTES, "duration"),
    _s("settlement_deduction_priority", "Settlement Deduction Priority", "usage_credit",
       CATEGORY_DISPUTES, "enum", allowed_values=["usage_credit"]),
    _s("manual_customer_refund_enabled", "Manual Customer Refund Enabled", False, CATEGORY_DISPUTES, risk="high"),

    # ── G8. Media & Storage ──────────────────────────────────────────────────
    _s("media_vault_enabled", "Media Vault Enabled", True, CATEGORY_MEDIA),
    _s("private_media_signed_urls_enabled", "Signed URLs Enabled", True, CATEGORY_MEDIA),
    _s("signed_url_expiry_minutes", "Signed URL Expiry (Minutes)", 15, CATEGORY_MEDIA, "duration"),
    _s("max_upload_size_mb", "Max Upload Size (MB)", 25, CATEGORY_MEDIA, "number"),
    _s("allowed_image_types", "Allowed Image Types", ["jpg", "jpeg", "png", "webp"], CATEGORY_MEDIA, "list"),
    _s("allowed_document_types", "Allowed Document Types", ["pdf", "doc", "docx", "xls", "xlsx"], CATEGORY_MEDIA, "list"),
    _s("virus_scan_enabled", "Virus Scan Enabled", False, CATEGORY_MEDIA),
    _s("tenant_storage_quota_enabled", "Tenant Storage Quota Enabled", True, CATEGORY_MEDIA),

    # ── G9. Notifications ────────────────────────────────────────────────────
    _s("notifications_enabled", "Notifications Enabled", True, CATEGORY_NOTIFICATIONS),
    _s("email_notifications_enabled", "Email Notifications Enabled", True, CATEGORY_NOTIFICATIONS),
    _s("sms_notifications_enabled", "SMS Notifications Enabled", False, CATEGORY_NOTIFICATIONS),
    _s("push_notifications_enabled", "Push Notifications Enabled", True, CATEGORY_NOTIFICATIONS),
    _s("whatsapp_notifications_enabled", "WhatsApp Notifications Enabled", False, CATEGORY_NOTIFICATIONS),
    _s("booking_status_notifications_enabled", "Booking Status Notifications Enabled", True, CATEGORY_NOTIFICATIONS),
    _s("credit_low_balance_notifications_enabled", "Low Balance Notifications Enabled", True, CATEGORY_NOTIFICATIONS),
    _s("dispute_notifications_enabled", "Dispute Notifications Enabled", True, CATEGORY_NOTIFICATIONS),

    # ── G10. Compliance / DPDP ───────────────────────────────────────────────
    _s("dpdp_compliance_enabled", "DPDP Compliance Enabled", True, CATEGORY_COMPLIANCE, risk="high"),
    _s("data_export_enabled", "Data Export Enabled", True, CATEGORY_COMPLIANCE),
    _s("right_to_erasure_enabled", "Right To Erasure Enabled", True, CATEGORY_COMPLIANCE, risk="high"),
    _s("consent_management_enabled", "Consent Management Enabled", True, CATEGORY_COMPLIANCE),
    _s("financial_records_erasure_exempt", "Financial Records Erasure Exempt", True, CATEGORY_COMPLIANCE, risk="high"),
    _s("financial_record_retention_years", "Financial Record Retention (Years)", 7, CATEGORY_COMPLIANCE, "number"),
    _s("compliance_request_sla_hours", "Compliance Request SLA (Hours)", 72, CATEGORY_COMPLIANCE, "duration"),

    # ── G11. Security ────────────────────────────────────────────────────────
    _s("super_admin_mfa_required", "Super Admin MFA Required", True, CATEGORY_SECURITY, risk="critical"),
    _s("platform_admin_mfa_required", "Platform Admin MFA Required", True, CATEGORY_SECURITY, risk="high"),
    _s("fresh_mfa_for_sensitive_actions", "Fresh MFA For Sensitive Actions", True, CATEGORY_SECURITY, risk="high"),
    _s("session_idle_timeout_minutes", "Session Idle Timeout (Minutes)", 60, CATEGORY_SECURITY, "duration"),
    _s("session_max_lifetime_hours", "Session Max Lifetime (Hours)", 24, CATEGORY_SECURITY, "duration"),
    _s("login_rate_limit_enabled", "Login Rate Limit Enabled", True, CATEGORY_SECURITY),
    _s("ip_blocklist_enabled", "IP Blocklist Enabled", True, CATEGORY_SECURITY),
    _s("admin_ip_allowlist_enabled", "Admin IP Allowlist Enabled", False, CATEGORY_SECURITY, risk="medium"),

    # ── G12. AI / DeepSeek ───────────────────────────────────────────────────
    _s("deepseek_chat_enabled", "DeepSeek Chat Enabled", True, CATEGORY_AI, owner_module="ai_hardening"),
    _s("llm_can_invent_prices", "LLM Can Invent Prices", False, CATEGORY_AI, risk="critical",
       description="Must stay false — DeepSeek talks, backend decides, database validates, engines execute."),
    _s("llm_can_create_services", "LLM Can Create Services", False, CATEGORY_AI, risk="critical"),
    _s("backend_is_source_of_truth", "Backend Is Source Of Truth", True, CATEGORY_AI, risk="critical"),
    _s("rag_for_documents_enabled", "RAG For Documents Enabled", True, CATEGORY_AI),
    _s("ai_workflow_suggestion_enabled", "AI Workflow Suggestion Enabled", True, CATEGORY_AI),
]

SETTING_KEYS = [s["key"] for s in SERVICEOS_DEFAULT_SETTINGS]
