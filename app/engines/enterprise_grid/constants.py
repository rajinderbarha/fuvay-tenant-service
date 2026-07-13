"""Sprint 26 — Enterprise Grid error codes and constants."""

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_GRID_RESOURCE_NOT_FOUND       = "GRID_RESOURCE_NOT_FOUND"
ERR_GRID_FILTER_NOT_ALLOWED       = "GRID_FILTER_NOT_ALLOWED"
ERR_GRID_SORT_NOT_ALLOWED         = "GRID_SORT_NOT_ALLOWED"
ERR_GRID_INVALID_PAGE             = "GRID_INVALID_PAGE"
ERR_GRID_INVALID_PAGE_SIZE        = "GRID_INVALID_PAGE_SIZE"
ERR_GRID_INVALID_DATE_RANGE       = "GRID_INVALID_DATE_RANGE"
ERR_GRID_SEARCH_TOO_LONG          = "GRID_SEARCH_TOO_LONG"
ERR_GRID_ACCESS_DENIED            = "GRID_ACCESS_DENIED"

ERR_SAVED_VIEW_NOT_FOUND          = "SAVED_VIEW_NOT_FOUND"
ERR_SAVED_VIEW_ACCESS_DENIED      = "SAVED_VIEW_ACCESS_DENIED"
ERR_SAVED_VIEW_INVALID_FILTER     = "SAVED_VIEW_INVALID_FILTER"
ERR_SAVED_VIEW_INVALID_COLUMNS    = "SAVED_VIEW_INVALID_COLUMNS"
ERR_SAVED_VIEW_DUPLICATE_NAME     = "SAVED_VIEW_DUPLICATE_NAME"

ERR_COLUMN_PREFERENCE_INVALID     = "COLUMN_PREFERENCE_INVALID"
ERR_COLUMN_PREFERENCE_ACCESS      = "COLUMN_PREFERENCE_ACCESS_DENIED"

ERR_EXPORT_NOT_ALLOWED            = "EXPORT_NOT_ALLOWED"
ERR_EXPORT_FIELD_NOT_ALLOWED      = "EXPORT_FIELD_NOT_ALLOWED"
ERR_EXPORT_TOO_LARGE              = "EXPORT_TOO_LARGE"
ERR_EXPORT_ASYNC_REQUIRED         = "EXPORT_ASYNC_REQUIRED"
ERR_EXPORT_JOB_NOT_FOUND          = "EXPORT_JOB_NOT_FOUND"
ERR_EXPORT_JOB_ACCESS_DENIED      = "EXPORT_JOB_ACCESS_DENIED"
ERR_EXPORT_GENERATION_FAILED      = "EXPORT_GENERATION_FAILED"

# ── FINAL-L5-05AA: export abuse-protection error codes ──────────────────────
ERR_EXPORT_RATE_LIMITED           = "EXPORT_RATE_LIMITED"
ERR_EXPORT_CONCURRENT_JOB_LIMIT   = "EXPORT_CONCURRENT_JOB_LIMIT"
ERR_EXPORT_TENANT_CONCURRENT_LIMIT = "EXPORT_TENANT_CONCURRENT_JOB_LIMIT"
ERR_EXPORT_IDEMPOTENCY_CONFLICT   = "EXPORT_IDEMPOTENCY_CONFLICT"
ERR_EXPORT_FIELD_LIMIT            = "EXPORT_FIELD_LIMIT"
ERR_EXPORT_SELECTED_ID_LIMIT      = "EXPORT_SELECTED_ID_LIMIT"
ERR_EXPORT_DATE_RANGE_EXCEEDED    = "EXPORT_DATE_RANGE_EXCEEDED"

# ── Scope types ───────────────────────────────────────────────────────────────
SCOPE_ADMIN_GLOBAL   = "admin_global"
SCOPE_PROVIDER       = "provider_tenant"
SCOPE_CUSTOMER       = "customer_own"
SCOPE_STAFF          = "staff_assigned"
SCOPE_PUBLIC         = "public_safe"

# ── Visibility ────────────────────────────────────────────────────────────────
VIS_PRIVATE       = "private"
VIS_TENANT_SHARED = "tenant_shared"
VIS_ADMIN_SHARED  = "admin_shared"

# ── Export statuses ───────────────────────────────────────────────────────────
EXPORT_PENDING    = "pending"
EXPORT_PROCESSING = "processing"
EXPORT_COMPLETED  = "completed"
EXPORT_FAILED     = "failed"
EXPORT_EXPIRED    = "expired"
EXPORT_CANCELLED  = "cancelled"  # FINAL-L5-05S

# ── Density options ───────────────────────────────────────────────────────────
DENSITY_COMPACT     = "compact"
DENSITY_COMFORTABLE = "comfortable"
DENSITY_SPACIOUS    = "spacious"

# ── Max page size ─────────────────────────────────────────────────────────────
MAX_PAGE_SIZE                  = 100
MAX_EXPORT_ROWS                = 5000
ENTERPRISE_SYNC_EXPORT_ROW_LIMIT = 5000   # synchronous exports blocked above this
MAX_SEARCH_LENGTH              = 256
EXPORT_EXPIRY_HOURS            = 24

# ── FINAL-L5-05AA: export abuse-protection limits ───────────────────────────
# Configurable, centralized (mission rule: "do not hardcode magic numbers
# throughout services"). Reuses the platform's existing api:export rate
# limit config (app/core/security.py RATE_LIMITS["api:export"] = 5/hour)
# as the request-rate control; the limits below are the additional
# payload/concurrency bounds this sprint adds.
EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR  = 3   # PENDING+PROCESSING jobs, atomic via advisory lock
EXPORT_MAX_CONCURRENT_JOBS_PER_TENANT = 10
EXPORT_MAX_COLUMNS                    = 50
EXPORT_MAX_SELECTED_IDS                = 500  # for filters carrying an "ids"/"selected_ids" array
EXPORT_MAX_DATE_RANGE_DAYS             = 366
EXPORT_IDEMPOTENCY_KEY_MAX_LEN         = 128
