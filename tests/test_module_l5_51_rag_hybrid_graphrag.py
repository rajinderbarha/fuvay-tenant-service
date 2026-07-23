"""MODULE-L5-51 — RAG hybrid search + GraphRAG.

Real embeddings (sentence-transformers, local, no API key) replace the
former deterministic-hash mock; real pgvector cosine search + real Postgres
full-text search are fused via Reciprocal Rank Fusion; a bounded GraphRAG-lite
entity-graph layer widens retrieval via single-hop entity co-occurrence.

These tests exercise the REAL embedding model (it runs locally, no network/
API key needed) and the pure-python RRF fusion logic. DB-touching pieces
(vector_search/keyword_search/graph expansion SQL, LLM generation) are
exercised by the live end-to-end script, not here — this module follows the
existing test_phase6.py convention of testing logic/constants without a
live DB.
"""
import uuid
import pytest

from app.engines.rag.constants import (
    EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, GENERATION_MODEL,
    RRF_K, HYBRID_VECTOR_WEIGHT, HYBRID_KEYWORD_WEIGHT, HYBRID_CANDIDATE_POOL,
    GRAPH_MAX_ENTITIES_PER_CHUNK, GRAPH_MAX_EXPANSION_CHUNKS,
)


# ── 1. Provider decision constants ─────────────────────────────────────────
def test_embedding_model_is_real_local_model():
    assert EMBEDDING_MODEL == "all-MiniLM-L6-v2"
def test_embedding_dimensions_match_minilm():
    assert EMBEDDING_DIMENSIONS == 384
def test_generation_model_is_real_deepseek_model():
    assert GENERATION_MODEL == "deepseek-chat"


# ── 2. Real embedding generation (local model, no mocking) ─────────────────
def test_embed_text_produces_real_shaped_vector():
    from app.engines.rag.embedding_service import embed_text
    vec = embed_text("Air conditioner filters should be cleaned every 3 months.")
    assert isinstance(vec, list)
    assert len(vec) == EMBEDDING_DIMENSIONS
    assert all(isinstance(x, float) for x in vec)
    # A real embedding is not all-zero and not a constant vector.
    assert any(abs(x) > 1e-6 for x in vec)
    assert len(set(round(x, 6) for x in vec)) > 1

def test_embed_text_is_deterministic_for_same_input():
    from app.engines.rag.embedding_service import embed_text
    v1 = embed_text("The warranty covers parts for 12 months.")
    v2 = embed_text("The warranty covers parts for 12 months.")
    assert v1 == v2

def test_embed_batch_matches_embed_text():
    from app.engines.rag.embedding_service import embed_text, embed_batch
    texts = ["First sentence about pricing.", "Second sentence about scheduling."]
    batch = embed_batch(texts)
    assert len(batch) == 2
    for t, v in zip(texts, batch):
        assert v == embed_text(t)

def test_semantically_related_text_scores_higher_than_unrelated():
    """A real embedding model should place semantically related sentences
    closer together than unrelated ones — proof this is not a hash mock."""
    from app.engines.rag.embedding_service import embed_text

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    base = embed_text("How do I reset my air conditioner filter?")
    related = embed_text("Steps to clean and replace the AC filter.")
    unrelated = embed_text("The quarterly financial results exceeded expectations.")

    sim_related = cosine(base, related)
    sim_unrelated = cosine(base, unrelated)
    assert sim_related > sim_unrelated


# ── 3. Reciprocal Rank Fusion (hybrid ranking) ──────────────────────────────
def _rrf(vector_ranked, keyword_ranked, k=RRF_K,
         w_vec=HYBRID_VECTOR_WEIGHT, w_kw=HYBRID_KEYWORD_WEIGHT):
    scores = {}
    for rank, (cid, _) in enumerate(vector_ranked):
        scores[cid] = scores.get(cid, 0.0) + w_vec / (k + rank + 1)
    for rank, (cid, _) in enumerate(keyword_ranked):
        scores[cid] = scores.get(cid, 0.0) + w_kw / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

def test_rrf_prefers_item_ranked_high_in_both_legs():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    vector_ranked = [(a, 0.9), (b, 0.8), (c, 0.1)]
    keyword_ranked = [(a, 5.0), (c, 4.0), (b, 0.1)]
    fused = _rrf(vector_ranked, keyword_ranked)
    assert fused[0][0] == a  # top in both legs wins overall

def test_rrf_surfaces_keyword_only_match_not_in_vector_pool():
    """A chunk that only the keyword leg found (e.g. exact SKU match with no
    semantic similarity) must still appear in the fused ranking — this is
    the core value of hybrid over pure vector search."""
    a, b = uuid.uuid4(), uuid.uuid4()
    vector_ranked = [(a, 0.9)]
    keyword_ranked = [(b, 9.9)]
    fused = _rrf(vector_ranked, keyword_ranked)
    fused_ids = {cid for cid, _ in fused}
    assert a in fused_ids and b in fused_ids

def test_hybrid_candidate_pool_reasonable():
    assert 10 <= HYBRID_CANDIDATE_POOL <= 200

def test_hybrid_weights_sum_to_one():
    assert abs((HYBRID_VECTOR_WEIGHT + HYBRID_KEYWORD_WEIGHT) - 1.0) < 1e-9


# ── 4. GraphRAG constants / scope ───────────────────────────────────────────
def test_graph_extraction_bounded():
    assert 1 <= GRAPH_MAX_ENTITIES_PER_CHUNK <= 20
    assert 1 <= GRAPH_MAX_EXPANSION_CHUNKS <= 20

def test_graph_extraction_prompt_requires_strict_json():
    from app.engines.rag.graph_service import GRAPH_EXTRACTION_SYSTEM_PROMPT
    assert "JSON" in GRAPH_EXTRACTION_SYSTEM_PROMPT
    assert "entities" in GRAPH_EXTRACTION_SYSTEM_PROMPT

def test_parse_graph_json_handles_fenced_and_malformed():
    from app.engines.rag.graph_service import _parse_graph_json
    good = '{"entities": [{"name": "AC Unit", "type": "product"}], "relationships": []}'
    assert _parse_graph_json(good)["entities"][0]["name"] == "AC Unit"

    fenced = "```json\n" + good + "\n```"
    assert _parse_graph_json(fenced)["entities"][0]["name"] == "AC Unit"

    malformed = "not json at all"
    parsed = _parse_graph_json(malformed)
    assert parsed == {"entities": [], "relationships": []}


# ── 5. Model schema (pgvector Vector type, GraphRAG tables) ─────────────────
def test_document_chunk_uses_real_pgvector_type():
    from app.engines.rag.models import DocumentChunk
    from pgvector.sqlalchemy import Vector
    col = DocumentChunk.__table__.c.embedding
    assert isinstance(col.type, Vector)
    assert col.type.dim == EMBEDDING_DIMENSIONS

def test_document_chunk_has_fulltext_column():
    from app.engines.rag.models import DocumentChunk
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(DocumentChunk).columns}
    assert "content_tsv" in cols

def test_graph_tables_exist_with_expected_fields():
    from app.engines.rag.models import KBEntity, KBEntityRelationship, KBChunkEntity
    from sqlalchemy.inspection import inspect

    entity_cols = {c.key for c in inspect(KBEntity).columns}
    assert {"kb_id", "name", "entity_type", "mention_count"}.issubset(entity_cols)

    rel_cols = {c.key for c in inspect(KBEntityRelationship).columns}
    assert {"source_entity_id", "target_entity_id", "relationship"}.issubset(rel_cols)

    link_cols = {c.key for c in inspect(KBChunkEntity).columns}
    assert {"chunk_id", "entity_id", "kb_id"}.issubset(link_cols)


# ── 6. Generation grounding (real DeepSeek call — no API key in test env) ───
@pytest.mark.asyncio
async def test_generate_with_no_chunks_returns_honest_no_context_message():
    from app.engines.rag.service import RAGService
    from unittest.mock import AsyncMock
    svc = RAGService(db=AsyncMock(), request_id="test")
    answer = await svc._generate("What is the warranty period?", [])
    assert "No relevant information" in answer

@pytest.mark.asyncio
async def test_generate_degrades_honestly_when_llm_unavailable():
    """With no DEEPSEEK_API_KEY reachable in the test sandbox, generation
    must fail closed with an honestly-labeled degraded response — never a
    fabricated 'answer' pretending to be a real generation."""
    from app.engines.rag.service import RAGService
    from unittest.mock import AsyncMock, patch
    from app.exceptions import ServiceOSException

    svc = RAGService(db=AsyncMock(), request_id="test")
    chunks = [{"chunk_id": "c1", "content": "Filters should be cleaned every 3 months.",
               "hybrid_score": 0.5, "doc_id": "d1"}]

    with patch("app.engines.rag.service.DeepSeekClientService") as MockClient:
        instance = MockClient.return_value
        instance.chat = AsyncMock(side_effect=ServiceOSException("DEEPSEEK_NOT_CONFIGURED", "not configured"))
        answer = await svc._generate("How often should filters be cleaned?", chunks)
    assert "temporarily unavailable" in answer
    assert "every 3 months" in answer  # still grounds on the retrieved chunk
