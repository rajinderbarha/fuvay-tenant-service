"""RAG Engine — constants."""
from decimal import Decimal

# ── Embedding models ───────────────────────────────────────────────────────
EMBEDDING_MODEL         = "text-embedding-3-small"
EMBEDDING_DIMENSIONS    = 1536
GENERATION_MODEL        = "gpt-4o-mini"

# ── Chunking defaults ──────────────────────────────────────────────────────
DEFAULT_CHUNK_SIZE      = 512    # tokens
DEFAULT_CHUNK_OVERLAP   = 64     # tokens
MAX_CHUNK_SIZE          = 2048
MIN_CHUNK_SIZE          = 128

# ── Query / retrieval ──────────────────────────────────────────────────────
DEFAULT_TOP_K           = 5      # chunks retrieved per query
MAX_TOP_K               = 20
LOW_CONFIDENCE_THRESHOLD = 0.65  # cosine similarity below = low confidence

# ── Token budgets by plan (context window) ─────────────────────────────────
TOKEN_BUDGET = {
    "starter":    2000,
    "growth":     4000,
    "enterprise": 8000,
}
DEFAULT_TOKEN_BUDGET = 2000

# ── Rate limits ────────────────────────────────────────────────────────────
RATE_LIMIT_QUERIES_PER_HOUR_TENANT = 100
RATE_LIMIT_QUERIES_PER_HOUR_USER   = 20

# ── KB health signal ───────────────────────────────────────────────────────
MIN_DOCS_BY_VERTICAL = {
    "home_services": 5,
    "real_estate":   4,
    "salon":         3,
    "cafe":          2,
    "default":       3,
}

# ── Document status lifecycle ──────────────────────────────────────────────
class DocStatus:
    PENDING    = "pending"
    CHUNKING   = "chunking"
    EMBEDDING  = "embedding"
    INDEXED    = "indexed"
    FAILED     = "failed"
    REINDEXING = "reindexing"

# ── Query status ───────────────────────────────────────────────────────────
class QueryStatus:
    PENDING   = "pending"
    SEARCHING = "searching"
    GENERATING = "generating"
    COMPLETED  = "completed"
    FAILED     = "failed"

# ── Supported MIME types ───────────────────────────────────────────────────
SUPPORTED_MIME_TYPES = [
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/html",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

# ── Redis keys ─────────────────────────────────────────────────────────────
REDIS_RATE_QUERY_TENANT = "serviceos:rag:rate:query:tenant:{tenant_id}"
REDIS_RATE_QUERY_USER   = "serviceos:rag:rate:query:user:{user_id}"
REDIS_KB_CACHE          = "serviceos:rag:kb:{kb_id}"
REDIS_DOC_STATUS        = "serviceos:rag:doc:status:{doc_id}"
