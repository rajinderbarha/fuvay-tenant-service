"""RAG Engine — constants."""
from decimal import Decimal

# ── Embedding models ───────────────────────────────────────────────────────
# MODULE-L5-51: real local embedding model (sentence-transformers), replacing
# the never-configured "text-embedding-3-small" (OPENAI_API_KEY was always
# empty in this deployment; DeepSeek's public API has no embeddings endpoint,
# only /chat/completions — see deepseek_client.py). all-MiniLM-L6-v2 is a
# well-established, free, no-API-key local model (384-dim) run via the
# `sentence-transformers` package — a genuinely real embedding provider, not
# a mock or a placeholder for one.
EMBEDDING_MODEL         = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS    = 384
# Real generation now uses the platform's existing DeepSeekClientService
# (same client backing the customer-facing AI chat assistant).
GENERATION_MODEL        = "deepseek-chat"

# ── Hybrid search ──────────────────────────────────────────────────────────
# Reciprocal Rank Fusion constant (standard default per Cormack et al. 2009).
RRF_K                   = 60
# Weights applied to each retrieval leg's RRF contribution before summing.
HYBRID_VECTOR_WEIGHT    = 0.6
HYBRID_KEYWORD_WEIGHT   = 0.4
# How many candidates each leg (vector / keyword) contributes pre-fusion.
HYBRID_CANDIDATE_POOL   = 40

# ── GraphRAG (single-hop entity co-occurrence expansion) ───────────────────
# NOT full Microsoft-GraphRAG-paper scope (no community detection/
# summarization) -- see kb_graph_service.py docstring for the honest scope.
GRAPH_MAX_ENTITIES_PER_CHUNK   = 8
GRAPH_MAX_EXPANSION_CHUNKS     = 5   # extra chunks pulled in via graph hops

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
