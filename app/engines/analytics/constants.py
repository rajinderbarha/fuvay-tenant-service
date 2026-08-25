"""Sprint 28 — Analytics + Reports constants."""

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_ANALYTICS_ACCESS_DENIED        = "ANALYTICS_ACCESS_DENIED"
ERR_ANALYTICS_INVALID_DATE_RANGE   = "ANALYTICS_INVALID_DATE_RANGE"
ERR_ANALYTICS_FILTER_NOT_ALLOWED   = "ANALYTICS_FILTER_NOT_ALLOWED"
ERR_ANALYTICS_RESOURCE_NOT_FOUND   = "ANALYTICS_RESOURCE_NOT_FOUND"
ERR_ANALYTICS_COMPUTE_FAILED       = "ANALYTICS_COMPUTE_FAILED"
ERR_ANALYTICS_CACHE_FAILED         = "ANALYTICS_CACHE_FAILED"

ERR_REPORT_NOT_FOUND               = "REPORT_NOT_FOUND"
ERR_REPORT_ACCESS_DENIED           = "REPORT_ACCESS_DENIED"
ERR_REPORT_FILTER_NOT_ALLOWED      = "REPORT_FILTER_NOT_ALLOWED"
ERR_REPORT_EXPORT_NOT_ALLOWED      = "REPORT_EXPORT_NOT_ALLOWED"
ERR_REPORT_RUN_FAILED              = "REPORT_RUN_FAILED"
ERR_REPORT_ASYNC_REQUIRED          = "REPORT_ASYNC_REQUIRED"
ERR_REPORT_TOO_LARGE               = "REPORT_TOO_LARGE"
ERR_REPORT_FORMAT_UNSUPPORTED      = "REPORT_FORMAT_UNSUPPORTED"

# ── Report keys — Admin ───────────────────────────────────────────────────────
RPT_ADMIN_PLATFORM_SUMMARY         = "admin_platform_summary_report"
RPT_ADMIN_CATEGORY_PERFORMANCE     = "admin_category_performance_report"
RPT_ADMIN_PROVIDER_PERFORMANCE     = "admin_provider_performance_report"
RPT_ADMIN_FINANCIAL                = "admin_financial_report"
RPT_ADMIN_COMMISSION               = "admin_commission_report"
RPT_ADMIN_WALLET                   = "admin_wallet_report"
RPT_ADMIN_QUALITY                  = "admin_quality_report"
RPT_ADMIN_COMPLAINT                = "admin_complaint_report"
RPT_ADMIN_STAFF_PERFORMANCE        = "admin_staff_performance_report"
RPT_ADMIN_AUDIT_ACTIVITY           = "admin_audit_activity_report"

# ── Report keys — Provider ────────────────────────────────────────────────────
RPT_PROVIDER_DASHBOARD             = "provider_dashboard_report"
RPT_PROVIDER_FINANCIAL             = "provider_financial_report"
RPT_PROVIDER_STAFF_PERFORMANCE     = "provider_staff_performance_report"
RPT_PROVIDER_REVIEWS               = "provider_reviews_report"
RPT_PROVIDER_COMPLAINTS            = "provider_complaints_report"
RPT_PROVIDER_WALLET_LEDGER         = "provider_wallet_ledger_report"
RPT_PROVIDER_JOBS                  = "provider_jobs_report"
RPT_PROVIDER_APPOINTMENTS          = "provider_appointments_report"
RPT_PROVIDER_LEADS                 = "provider_leads_report"

# ── Report statuses ───────────────────────────────────────────────────────────
REPORT_STATUS_PENDING   = "pending"
REPORT_STATUS_RUNNING   = "running"
REPORT_STATUS_COMPLETED = "completed"
REPORT_STATUS_FAILED    = "failed"

# ── Scope ─────────────────────────────────────────────────────────────────────
SCOPE_ADMIN    = "admin"
SCOPE_PROVIDER = "provider"

# ── Export limits ─────────────────────────────────────────────────────────────
EXPORT_SYNC_ROW_LIMIT  = 5_000
EXPORT_MAX_ROW_LIMIT   = 100_000

# ── Default date range (days) ─────────────────────────────────────────────────
DEFAULT_DATE_RANGE_DAYS = 30
MAX_DATE_RANGE_DAYS     = 365
