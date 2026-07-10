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
