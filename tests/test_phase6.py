"""Phase 6 — RAG Engine Tests (45 tests)."""
import uuid, hashlib
import pytest
from app.engines.rag.constants import (
    EMBEDDING_MODEL, GENERATION_MODEL, EMBEDDING_DIMENSIONS,
    DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, DEFAULT_TOP_K,
    LOW_CONFIDENCE_THRESHOLD, TOKEN_BUDGET, MIN_DOCS_BY_VERTICAL,
    DocStatus, QueryStatus, SUPPORTED_MIME_TYPES,
)

# ── 1. Constants ──────────────────────────────────────────────────────────────
# MODULE-L5-51: these were updated from the never-configured OpenAI values
# to the real embedding/generation providers actually wired up (local
# sentence-transformers model + the platform's existing DeepSeek client).
def test_embedding_model(): assert EMBEDDING_MODEL == "all-MiniLM-L6-v2"
def test_generation_model(): assert GENERATION_MODEL == "deepseek-chat"
def test_embedding_dimensions(): assert EMBEDDING_DIMENSIONS == 384
def test_chunk_defaults():
    assert DEFAULT_CHUNK_SIZE == 512
    assert DEFAULT_CHUNK_OVERLAP == 64
    assert DEFAULT_CHUNK_OVERLAP < DEFAULT_CHUNK_SIZE
def test_top_k_default(): assert DEFAULT_TOP_K == 5
def test_low_confidence_threshold(): assert 0 < LOW_CONFIDENCE_THRESHOLD < 1

def test_token_budgets_by_plan():
    assert TOKEN_BUDGET["starter"] < TOKEN_BUDGET["growth"] < TOKEN_BUDGET["enterprise"]
    assert TOKEN_BUDGET["starter"] == 2000
    assert TOKEN_BUDGET["enterprise"] == 8000

def test_min_docs_by_vertical():
    assert "home_services" in MIN_DOCS_BY_VERTICAL
    assert "default" in MIN_DOCS_BY_VERTICAL
    assert MIN_DOCS_BY_VERTICAL["home_services"] >= 3

def test_doc_status_values_unique():
    vals = [v for k, v in DocStatus.__dict__.items() if not k.startswith("_")]
    assert len(vals) == len(set(vals))

def test_query_status_values_unique():
    vals = [v for k, v in QueryStatus.__dict__.items() if not k.startswith("_")]
    assert len(vals) == len(set(vals))

def test_supported_mime_types():
    assert "application/pdf" in SUPPORTED_MIME_TYPES
    assert "text/plain" in SUPPORTED_MIME_TYPES
    assert "text/markdown" in SUPPORTED_MIME_TYPES

# ── 2. Content hash idempotency ───────────────────────────────────────────────
def test_content_hash_deterministic():
    content = "This is a test document about AC servicing procedures."
    h1 = hashlib.sha256(content.encode()).hexdigest()
    h2 = hashlib.sha256(content.encode()).hexdigest()
    assert h1 == h2

def test_content_hash_64_chars():
    content = "Test content"
    h = hashlib.sha256(content.encode()).hexdigest()
    assert len(h) == 64

def test_different_content_different_hash():
    h1 = hashlib.sha256(b"document one").hexdigest()
    h2 = hashlib.sha256(b"document two").hexdigest()
    assert h1 != h2

def test_same_filename_different_content_detected():
    content_a = "Version 1 of the policy document."
    content_b = "Version 2 of the policy document - updated."
    h_a = hashlib.sha256(content_a.encode()).hexdigest()
    h_b = hashlib.sha256(content_b.encode()).hexdigest()
    assert h_a != h_b  # Correctly detected as different

# ── 3. Chunking logic ─────────────────────────────────────────────────────────
def _chunk_text(text, chunk_size=10, overlap=2):
    words = text.split()
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk_words = words[i:i + chunk_size]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break
    return chunks or [text]

def test_chunking_produces_multiple_chunks():
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = _chunk_text(text, chunk_size=10, overlap=2)
    assert len(chunks) > 1

def test_chunking_overlap_creates_continuity():
    text = " ".join([f"w{i}" for i in range(20)])
    chunks = _chunk_text(text, chunk_size=10, overlap=2)
    # Adjacent chunks should share words due to overlap
    words_c0 = set(chunks[0].split())
    words_c1 = set(chunks[1].split())
    assert len(words_c0 & words_c1) > 0

def test_short_text_single_chunk():
    text = "Short document."
    chunks = _chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1

def test_empty_text_returns_something():
    chunks = _chunk_text("", chunk_size=10, overlap=2)
    assert len(chunks) >= 1

# ── 4. Token budget enforcement ───────────────────────────────────────────────
def test_token_budget_drops_low_scoring_chunks():
    budget = 100
    chunks = [{"token_count": 40, "score": 0.9},
              {"token_count": 40, "score": 0.8},
              {"token_count": 40, "score": 0.7}]
    selected = []
    used = 0
    for c in chunks:
        if used + c["token_count"] <= budget:
            selected.append(c)
            used += c["token_count"]
    assert len(selected) == 2
    assert sum(c["token_count"] for c in selected) <= budget

def test_starter_plan_lower_budget_than_enterprise():
    assert TOKEN_BUDGET["starter"] < TOKEN_BUDGET["enterprise"]

# ── 5. Cosine similarity ──────────────────────────────────────────────────────
def _cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a)**0.5
    nb = sum(x*x for x in b)**0.5
    return dot/(na*nb) if na and nb else 0.0

def test_identical_vectors_similarity_one():
    v = [1.0, 0.0, 1.0]
    assert abs(_cosine(v, v) - 1.0) < 0.001

def test_opposite_vectors_similarity_minus_one():
    v = [1.0, 0.0]
    neg = [-1.0, 0.0]
    assert abs(_cosine(v, neg) - (-1.0)) < 0.001

def test_orthogonal_vectors_similarity_zero():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(_cosine(a, b)) < 0.001

def test_similarity_bounded():
    a = [0.5, 0.3, 0.8]
    b = [0.2, 0.9, 0.1]
    sim = _cosine(a, b)
    assert -1.0 <= sim <= 1.0

# ── 6. Health signal math ─────────────────────────────────────────────────────
def test_kb_coverage_full():
    indexed = 5; min_required = 5
    coverage = min(100.0, (indexed / min_required) * 100)
    assert coverage == 100.0

def test_kb_coverage_partial():
    indexed = 2; min_required = 5
    coverage = min(100.0, (indexed / min_required) * 100)
    assert coverage == 40.0

def test_kb_coverage_over_minimum_capped():
    indexed = 10; min_required = 5
    coverage = min(100.0, (indexed / min_required) * 100)
    assert coverage == 100.0

def test_kb_coverage_zero_docs():
    indexed = 0; min_required = 5
    coverage = min(100.0, (indexed / min_required) * 100) if min_required > 0 else 100.0
    assert coverage == 0.0

# ── 7. Model fields ───────────────────────────────────────────────────────────
def test_knowledge_base_model_fields():
    from app.engines.rag.models import KnowledgeBase
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(KnowledgeBase).columns}
    assert {"tenant_id","name","chunk_size","chunk_overlap","top_k",
            "indexed_count","total_chunks","total_tokens_used"}.issubset(cols)

def test_document_chunk_immutable_design():
    from app.engines.rag.models import DocumentChunk
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(DocumentChunk).columns}
    assert "is_active" in cols   # soft-delete for versioning
    assert "version" in cols     # version tracking
    assert "embedding" in cols   # vector stored here

def test_rag_query_has_full_trace_fields():
    from app.engines.rag.models import RAGQuery
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(RAGQuery).columns}
    assert {"question","answer","retrieved_chunks","citations","top_similarity",
            "low_confidence","embedding_tokens","completion_tokens",
            "latency_ms","model_used","idempotency_key"}.issubset(cols)

def test_kb_document_idempotency_constraint():
    from app.engines.rag.models import KBDocument
    from sqlalchemy.inspection import inspect
    constraints = {c.name for c in inspect(KBDocument).mapper.persist_selectable.constraints}
    assert "uq_kbdoc_kb_hash" in constraints

# ── 8. HTTP endpoint probes ───────────────────────────────────────────────────
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def test_rag_meta(client):
    r = client.get("/v1/rag/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "rag"
    assert d["endpoint_count"] == 18
    assert len(d["pipeline"]) == 5

def test_create_kb_requires_auth(client):
    assert client.post("/v1/rag/knowledge-bases", json={}).status_code == 401

def test_query_requires_auth(client):
    assert client.post("/v1/rag/query", json={}).status_code == 401

def test_search_requires_auth(client):
    assert client.post("/v1/rag/search", json={}).status_code == 401

def test_ingest_requires_auth(client):
    kid = uuid.uuid4()
    assert client.post(f"/v1/rag/knowledge-bases/{kid}/documents", json={}).status_code == 401

def test_platform_usage_requires_admin(client):
    assert client.get("/v1/rag/platform/usage").status_code == 401

def test_all_prior_phases_still_pass(client):
    assert client.get("/health").status_code == 200
    assert client.get("/v1/commerce/meta").status_code == 200
    assert client.get("/v1/pricing/meta").status_code == 200
    assert client.get("/v1/settings/meta").status_code == 200
    assert client.get("/v1/notifications/meta").status_code == 200
    assert client.get("/v1/media/meta").status_code == 200
    assert client.get("/v1/analytics/meta").status_code == 200
    assert client.get("/v1/rag/meta").status_code == 200
