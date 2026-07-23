"""RAG Engine — RAGService. Full pipeline: ingest → chunk → embed → store → query → generate."""
from __future__ import annotations
import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.rag.constants import (
    DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, DEFAULT_TOP_K,
    EMBEDDING_MODEL, GENERATION_MODEL, LOW_CONFIDENCE_THRESHOLD,
    TOKEN_BUDGET, DEFAULT_TOKEN_BUDGET, DocStatus, QueryStatus,
    MIN_DOCS_BY_VERTICAL, REDIS_KB_CACHE, REDIS_DOC_STATUS,
    RRF_K, HYBRID_VECTOR_WEIGHT, HYBRID_KEYWORD_WEIGHT, HYBRID_CANDIDATE_POOL,
)
from app.engines.rag.embedding_service import embed_text, embed_batch
from app.engines.rag.graph_service import extract_graph_for_chunk, expand_via_graph
from app.engines.rag.models import KnowledgeBase, KBDocument, DocumentChunk, RAGQuery
from app.engines.ai_conversation.deepseek_client import DeepSeekClientService
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis, cache_set, cache_get, cache_delete
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("rag.service")
utcnow = lambda: datetime.now(timezone.utc)


class RAGService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        # Phase 2A Slice 2F-35: the authoritative tenant of the calling
        # principal, derived server-side from the token. The 5 mutation
        # methods closed this slice (query, delete_kb, ingest_document,
        # delete_document, reindex_document) MUST scope by this value.
        # _get_kb (below) is intentionally left untouched -- it backs
        # several Set C read routes (get_kb, list_documents, update_kb,
        # search_only) that remain frozen out of this slice's scope; a new
        # _get_kb_trusted() helper is used instead for the closed methods.
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self) -> uuid.UUID | None:
        """Returns the authoritative tenant to scope a mutation by (no
        client-supplied tenant exists on any of the 5 closed methods --
        kb_id/doc_id are the only path inputs). Fails closed unless the
        caller is platform staff or has a known tenant context."""
        if self.actor_role == "super_admin":
            return None
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="rag_mutation_requires_trusted_tenant_context")
        return self.actor_tenant_id

    async def _get_kb_trusted(self, kb_id: uuid.UUID) -> KnowledgeBase:
        """Tenant-scoped KB lookup for the 3 mutation methods that must
        close this slice (query, delete_kb, ingest_document). Does NOT
        replace _get_kb, which several frozen Set C read routes still use
        unmodified."""
        tenant_id = self._require_trusted_tenant()
        q = select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.is_active == True)
        if tenant_id is not None:
            q = q.where(KnowledgeBase.tenant_id == tenant_id)
        r = await self.db.execute(q)
        kb = r.scalar_one_or_none()
        if not kb:
            raise NotFoundException("KnowledgeBase", str(kb_id))
        return kb

    # ── Private helpers ───────────────────────────────────────────────────────
    async def _get_kb(self, kb_id: uuid.UUID) -> KnowledgeBase:
        r = await self.db.execute(select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id, KnowledgeBase.is_active == True))
        kb = r.scalar_one_or_none()
        if not kb:
            raise NotFoundException("KnowledgeBase", str(kb_id))
        return kb

    async def _publish(self, event_type: str, tenant_id: str, entity_id: str, payload: dict) -> None:
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="rag",
                tenant_id=tenant_id, entity_type="rag",
                entity_id=entity_id, payload=payload,
                actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("rag.event_failed", error=str(e))

    async def _write_health_signal(self, tenant_id: uuid.UUID, kb: KnowledgeBase) -> None:
        try:
            from app.engines.tenant_engine.health import write_health_signal
            vertical = kb.vertical or "default"
            min_docs = MIN_DOCS_BY_VERTICAL.get(vertical, MIN_DOCS_BY_VERTICAL["default"])
            coverage = min(100.0, (kb.indexed_count / min_docs) * 100) if min_docs > 0 else 100.0
            await write_health_signal(tenant_id, "rag_kb_coverage", coverage)
        except Exception as e:
            logger.warning("rag.health_signal_failed", error=str(e))

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Simple word-boundary chunking. Production uses tiktoken."""
        words = text.split()
        chunks = []
        step = max(1, chunk_size - overlap)
        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            if chunk_words:
                chunks.append(" ".join(chunk_words))
            if i + chunk_size >= len(words):
                break
        return chunks or [text[:500]]

    def _embed(self, text: str) -> list[float]:
        """Real embedding via sentence-transformers (all-MiniLM-L6-v2, local,
        no API key). See embedding_service.py for the provider decision."""
        return embed_text(text)

    async def _generate(self, question: str, chunks: list[dict]) -> str:
        """Real LLM generation via DeepSeekClientService — the platform's
        existing DeepSeek chat client — grounded on the retrieved (hybrid +
        graph expanded) chunks. Falls back to an honest no-context message
        when there is nothing to ground on; falls back to a clearly-labeled
        degraded response if the LLM call itself fails, rather than faking
        a generated answer."""
        if not chunks:
            return "No relevant information found in the knowledge base."

        context = "\n\n".join(
            f"[Source {i+1}]: {c['content']}" for i, c in enumerate(chunks))
        system_prompt = (
            "You are a knowledge-base assistant. Answer the user's question "
            "using ONLY the information in the provided sources. If the "
            "sources do not contain the answer, say so plainly. Be concise. "
            "Cite sources inline as [Source N] where relevant."
        )
        try:
            llm = DeepSeekClientService(db=self.db, request_id=self.request_id)
            response = await llm.chat(messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Sources:\n{context}\n\nQuestion: {question}"},
            ])
            answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return answer.strip() or "The AI assistant returned an empty response."
        except ServiceOSException as e:
            logger.warning("rag.generation_failed", error=str(e))
            top = chunks[0]
            return (f"AI generation is temporarily unavailable, showing the top matching "
                    f"source instead: {top['content'][:300]}")

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    # ── Hybrid retrieval (real vector + real keyword, fused via RRF) ──────────
    async def _vector_search(self, kb_id: uuid.UUID, query_embedding: list[float],
                              limit: int) -> list[tuple[uuid.UUID, float]]:
        """Real pgvector cosine-distance search using the `<=>` operator and
        the ivfflat index (migration 147). Returns (chunk_id, similarity)
        ranked best-first. Replaces the prior in-Python full-scan mock."""
        vec_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"
        rows = await self.db.execute(text(
            "SELECT id, 1 - (embedding <=> (:qvec)::vector) AS similarity "
            "FROM document_chunks "
            "WHERE kb_id = :kb_id AND is_active = true AND embedding IS NOT NULL "
            "ORDER BY embedding <=> (:qvec)::vector ASC LIMIT :limit"
        ), {"qvec": vec_literal, "kb_id": str(kb_id), "limit": limit})
        return [(row.id, float(row.similarity)) for row in rows.all()]

    async def _keyword_search(self, kb_id: uuid.UUID, question: str,
                               limit: int) -> list[tuple[uuid.UUID, float]]:
        """Real Postgres full-text search using ts_rank + plainto_tsquery
        against the content_tsv column (migration 147, kept in sync by a
        DB trigger). This is the real keyword-search leg of hybrid
        retrieval — not a substring/LIKE approximation."""
        rows = await self.db.execute(text(
            "SELECT id, ts_rank(content_tsv, plainto_tsquery('english', :q)) AS rank "
            "FROM document_chunks "
            "WHERE kb_id = :kb_id AND is_active = true "
            "AND content_tsv @@ plainto_tsquery('english', :q) "
            "ORDER BY rank DESC LIMIT :limit"
        ), {"q": question, "kb_id": str(kb_id), "limit": limit})
        return [(row.id, float(row.rank)) for row in rows.all()]

    def _reciprocal_rank_fusion(self, vector_ranked: list[tuple[uuid.UUID, float]],
                                 keyword_ranked: list[tuple[uuid.UUID, float]]
                                 ) -> list[tuple[uuid.UUID, float]]:
        """Standard Reciprocal Rank Fusion (Cormack et al. 2009):
        score(d) = sum_over_legs( weight / (RRF_K + rank_in_leg) ).
        Combines the two independently-ranked lists into one fused ranking
        without needing to normalize raw similarity/rank scores onto a
        common scale — RRF only uses each leg's rank position. Weights let
        the vector leg count for more than keyword by default (0.6 / 0.4),
        matching this being a semantic-search-first product."""
        scores: dict[uuid.UUID, float] = {}
        for rank, (chunk_id, _) in enumerate(vector_ranked):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + HYBRID_VECTOR_WEIGHT / (RRF_K + rank + 1)
        for rank, (chunk_id, _) in enumerate(keyword_ranked):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + HYBRID_KEYWORD_WEIGHT / (RRF_K + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    async def _hybrid_search(self, kb_id: uuid.UUID, question: str,
                              question_embedding: list[float], top_k: int
                              ) -> list[tuple[DocumentChunk, float]]:
        """Full hybrid pipeline: real vector search + real keyword search ->
        RRF fusion -> hydrate top chunk_ids -> optional GraphRAG expansion.
        Returns (chunk, fused_score) ranked best-first."""
        vector_ranked = await self._vector_search(kb_id, question_embedding, HYBRID_CANDIDATE_POOL)
        keyword_ranked = await self._keyword_search(kb_id, question, HYBRID_CANDIDATE_POOL)
        fused = self._reciprocal_rank_fusion(vector_ranked, keyword_ranked)
        top_ids = [cid for cid, _ in fused[:top_k]]
        if not top_ids:
            return []

        rows = await self.db.execute(select(DocumentChunk).where(
            DocumentChunk.id.in_(top_ids), DocumentChunk.is_active == True))
        chunks_by_id = {c.id: c for c in rows.scalars().all()}
        score_by_id = dict(fused)
        ranked = [(chunks_by_id[cid], score_by_id[cid]) for cid in top_ids if cid in chunks_by_id]

        # GraphRAG expansion: pull in graph-connected chunks the pure hybrid
        # search might have missed, scored just below the hybrid tail so
        # they never outrank a real hybrid match.
        try:
            expansion_chunks = await expand_via_graph(self.db, kb_id, top_ids)
            min_score = ranked[-1][1] if ranked else 0.0
            existing_ids = set(top_ids)
            for i, c in enumerate(expansion_chunks):
                if c.id not in existing_ids:
                    ranked.append((c, max(0.0, min_score - 0.001 * (i + 1))))
        except Exception as e:
            logger.warning("rag.graph_expansion_failed", kb_id=str(kb_id), error=str(e))

        return ranked

    def _kb_dict(self, kb: KnowledgeBase) -> dict:
        return {
            "kb_id": str(kb.id), "tenant_id": str(kb.tenant_id),
            "name": kb.name, "description": kb.description,
            "vertical": kb.vertical, "embedding_model": kb.embedding_model,
            "chunk_size": kb.chunk_size, "chunk_overlap": kb.chunk_overlap,
            "top_k": kb.top_k, "document_count": kb.document_count,
            "indexed_count": kb.indexed_count, "total_chunks": kb.total_chunks,
            "total_tokens_used": kb.total_tokens_used,
            "created_at": kb.created_at.isoformat(),
        }

    def _doc_dict(self, d: KBDocument) -> dict:
        return {
            "doc_id": str(d.id), "kb_id": str(d.kb_id),
            "file_name": d.file_name, "mime_type": d.mime_type,
            "content_hash": d.content_hash, "status": d.status,
            "status_message": d.status_message, "version": d.version,
            "char_count": d.char_count, "chunk_count": d.chunk_count,
            "token_count": d.token_count, "tags": d.tags,
            "indexed_at": d.indexed_at.isoformat() if d.indexed_at else None,
            "created_at": d.created_at.isoformat(),
        }

    def _query_dict(self, q: RAGQuery) -> dict:
        return {
            "query_id": str(q.id), "kb_id": str(q.kb_id),
            "tenant_id": str(q.tenant_id), "question": q.question,
            "answer": q.answer, "status": q.status,
            "citations": q.citations, "top_similarity": q.top_similarity,
            "low_confidence": q.low_confidence,
            "embedding_tokens": q.embedding_tokens,
            "completion_tokens": q.completion_tokens,
            "total_tokens": q.total_tokens, "latency_ms": q.latency_ms,
            "model_used": q.model_used, "created_at": q.created_at.isoformat(),
        }

    # ── Knowledge Base CRUD (5 methods) ───────────────────────────────────────
    async def create_kb(self, tenant_id: uuid.UUID, name: str, description: str | None,
                         vertical: str | None, chunk_size: int, chunk_overlap: int,
                         top_k: int) -> dict:
        trusted_tenant_id = self._require_trusted_tenant()
        if trusted_tenant_id is not None and tenant_id != trusted_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's knowledge bases.",
                blocking_rule="rag_mutation_cross_tenant_denied")
        kb = KnowledgeBase(
            tenant_id=tenant_id, name=name, description=description,
            vertical=vertical, chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            top_k=top_k, created_by=self.actor_id,
        )
        self.db.add(kb)
        await self.db.flush()
        await self._publish("rag.kb_created", str(tenant_id), str(kb.id),
                            {"name": name, "vertical": vertical})
        logger.info("rag.kb_created", kb_id=str(kb.id), tenant_id=str(tenant_id))
        return self._kb_dict(kb)

    async def get_kb(self, kb_id: uuid.UUID) -> dict:
        kb = await self._get_kb(kb_id)
        return self._kb_dict(kb)

    async def list_tenant_kbs(self, tenant_id: uuid.UUID,
                               limit: int, cursor: str | None) -> dict:
        q = select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant_id,
            KnowledgeBase.is_active == True,
        ).order_by(KnowledgeBase.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(KnowledgeBase.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        kbs = r.scalars().all()
        has_next = len(kbs) > limit
        kbs = kbs[:limit]
        nc = encode_cursor({"created_at": kbs[-1].created_at.isoformat()}) if has_next and kbs else None
        return {"knowledge_bases": [self._kb_dict(kb) for kb in kbs],
                "has_next": has_next, "next_cursor": nc}

    async def update_kb(self, kb_id: uuid.UUID, data: dict) -> dict:
        kb = await self._get_kb_trusted(kb_id)
        for field in ("name", "description", "chunk_size", "chunk_overlap", "top_k"):
            if field in data and data[field] is not None:
                setattr(kb, field, data[field])
        await cache_delete(REDIS_KB_CACHE.format(kb_id=kb_id))
        return self._kb_dict(kb)

    async def delete_kb(self, kb_id: uuid.UUID) -> dict:
        kb = await self._get_kb_trusted(kb_id)
        kb.is_active = False
        await self.db.execute(
            update(DocumentChunk).where(
                DocumentChunk.kb_id == kb_id
            ).values(is_active=False)
        )
        await cache_delete(REDIS_KB_CACHE.format(kb_id=kb_id))
        await self._publish("rag.kb_deleted", str(kb.tenant_id), str(kb_id), {})
        return {"kb_id": str(kb_id), "deleted": True}

    # ── Document Management (5 methods) ───────────────────────────────────────
    async def ingest_document(self, kb_id: uuid.UUID, file_name: str,
                               mime_type: str, content: str,
                               source_url: str | None, tags: list) -> dict:
        kb = await self._get_kb_trusted(kb_id)

        # Idempotency: SHA-256 of content
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        ex = await self.db.execute(select(KBDocument).where(
            KBDocument.kb_id == kb_id,
            KBDocument.content_hash == content_hash))
        existing = ex.scalar_one_or_none()
        if existing:
            logger.info("rag.doc_idempotent", doc_id=str(existing.id))
            return {**self._doc_dict(existing), "idempotent": True}

        doc = KBDocument(
            kb_id=kb_id, tenant_id=kb.tenant_id,
            file_name=file_name, mime_type=mime_type,
            content_hash=content_hash, raw_text=content,
            char_count=len(content), status=DocStatus.PENDING,
            uploaded_by=self.actor_id, source_url=source_url, tags=tags,
        )
        self.db.add(doc)
        await self.db.flush()
        kb.document_count += 1

        # Run pipeline synchronously (Celery in production)
        await self._run_indexing_pipeline(doc, kb)

        await self._write_health_signal(kb.tenant_id, kb)
        await self._publish("rag.document_indexed", str(kb.tenant_id), str(doc.id),
                            {"file_name": file_name, "chunk_count": doc.chunk_count})
        return {**self._doc_dict(doc), "idempotent": False}

    async def _run_indexing_pipeline(self, doc: KBDocument, kb: KnowledgeBase) -> None:
        """Chunk → embed (real, local model) → store → GraphRAG entity
        extraction. Celery task in production."""
        try:
            doc.status = DocStatus.CHUNKING
            chunks = self._chunk_text(doc.raw_text or "", kb.chunk_size, kb.chunk_overlap)

            doc.status = DocStatus.EMBEDDING
            embeddings = embed_batch(chunks)
            chunk_objects = []
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_objects.append(DocumentChunk(
                    kb_id=kb.id, doc_id=doc.id, tenant_id=kb.tenant_id,
                    chunk_index=i, content=chunk_text,
                    char_count=len(chunk_text),
                    token_count=len(chunk_text.split()),
                    embedding=embedding, is_active=True, version=doc.version,
                ))

            for obj in chunk_objects:
                self.db.add(obj)

            doc.chunk_count = len(chunks)
            doc.token_count = sum(c.token_count for c in chunk_objects)
            doc.status = DocStatus.INDEXED
            doc.indexed_at = utcnow()

            kb.indexed_count += 1
            kb.total_chunks += len(chunks)
            kb.total_tokens_used += doc.token_count

            await self.db.flush()
            logger.info("rag.indexed", doc_id=str(doc.id), chunks=len(chunks))

            # GraphRAG: extract entities/relationships per chunk. Best-effort
            # — a failure here degrades gracefully to pure hybrid search
            # (extract_graph_for_chunk never raises), it must not fail the
            # document's indexed status.
            for obj in chunk_objects:
                await extract_graph_for_chunk(self.db, kb.id, kb.tenant_id, obj,
                                               request_id=self.request_id)
            await self.db.flush()
        except Exception as e:
            doc.status = DocStatus.FAILED
            doc.status_message = str(e)[:500]
            logger.error("rag.indexing_failed", doc_id=str(doc.id), error=str(e))

    async def list_documents(self, kb_id: uuid.UUID, status: str | None,
                              limit: int, cursor: str | None) -> dict:
        q = select(KBDocument).where(KBDocument.kb_id == kb_id)            .order_by(KBDocument.created_at.desc())
        if status:
            q = q.where(KBDocument.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(KBDocument.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        docs = r.scalars().all()
        has_next = len(docs) > limit
        docs = docs[:limit]
        nc = encode_cursor({"created_at": docs[-1].created_at.isoformat()}) if has_next and docs else None
        return {"documents": [self._doc_dict(d) for d in docs],
                "has_next": has_next, "next_cursor": nc}

    async def get_document(self, doc_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(KBDocument).where(KBDocument.id == doc_id))
        d = r.scalar_one_or_none()
        if not d:
            raise NotFoundException("KBDocument", str(doc_id))
        return self._doc_dict(d)

    async def delete_document(self, doc_id: uuid.UUID) -> dict:
        # Phase 2A Slice 2F-35: previously queried WHERE id==doc_id ONLY --
        # zero tenant predicate, so any TENANT_UPDATE holder in ANY tenant
        # could delete another tenant's document. Now scoped server-side.
        tenant_id = self._require_trusted_tenant()
        q = select(KBDocument).where(KBDocument.id == doc_id)
        if tenant_id is not None:
            q = q.where(KBDocument.tenant_id == tenant_id)
        r = await self.db.execute(q)
        d = r.scalar_one_or_none()
        if not d:
            raise NotFoundException("KBDocument", str(doc_id))

        # Soft-delete all active chunks
        await self.db.execute(
            update(DocumentChunk).where(
                DocumentChunk.doc_id == doc_id,
                DocumentChunk.is_active == True,
            ).values(is_active=False)
        )

        # Update KB counts
        kb = await self._get_kb(d.kb_id)
        kb.total_chunks = max(0, kb.total_chunks - d.chunk_count)
        if d.status == DocStatus.INDEXED:
            kb.indexed_count = max(0, kb.indexed_count - 1)
        kb.document_count = max(0, kb.document_count - 1)

        await self.db.delete(d)
        await self._write_health_signal(d.tenant_id, kb)
        return {"doc_id": str(doc_id), "deleted": True,
                "chunks_deactivated": d.chunk_count}

    async def reindex_document(self, doc_id: uuid.UUID) -> dict:
        # Phase 2A Slice 2F-35: same cross-tenant fix as delete_document.
        tenant_id = self._require_trusted_tenant()
        q = select(KBDocument).where(KBDocument.id == doc_id)
        if tenant_id is not None:
            q = q.where(KBDocument.tenant_id == tenant_id)
        r = await self.db.execute(q)
        d = r.scalar_one_or_none()
        if not d:
            raise NotFoundException("KBDocument", str(doc_id))
        if d.status == DocStatus.REINDEXING:
            raise ServiceOSException("CONFLICT", "Document is already being reindexed.")

        # Soft-delete old chunks
        await self.db.execute(
            update(DocumentChunk).where(
                DocumentChunk.doc_id == doc_id,
                DocumentChunk.is_active == True,
            ).values(is_active=False)
        )

        d.status = DocStatus.REINDEXING
        d.version += 1
        d.chunk_count = 0

        kb = await self._get_kb(d.kb_id)
        await self._run_indexing_pipeline(d, kb)

        await self._publish("rag.document_reindexed", str(d.tenant_id), str(doc_id),
                            {"version": d.version, "chunk_count": d.chunk_count})
        return {**self._doc_dict(d), "reindexed": True}

    # ── Chunk Management (2 methods) ──────────────────────────────────────────
    async def list_chunks(self, kb_id: uuid.UUID, doc_id: uuid.UUID | None,
                           limit: int, cursor: str | None) -> dict:
        q = select(DocumentChunk).where(
            DocumentChunk.kb_id == kb_id,
            DocumentChunk.is_active == True,
        ).order_by(DocumentChunk.doc_id, DocumentChunk.chunk_index)
        if doc_id:
            q = q.where(DocumentChunk.doc_id == doc_id)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(DocumentChunk.chunk_index > int(c.get("chunk_index", 0)))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        chunks = r.scalars().all()
        has_next = len(chunks) > limit
        chunks = chunks[:limit]
        nc = encode_cursor({"chunk_index": chunks[-1].chunk_index}) if has_next and chunks else None
        return {
            "chunks": [{"chunk_id": str(c.id), "doc_id": str(c.doc_id),
                        "chunk_index": c.chunk_index, "content": c.content[:200] + "...",
                        "token_count": c.token_count, "version": c.version,
                        "has_embedding": c.embedding is not None} for c in chunks],
            "has_next": has_next, "next_cursor": nc,
        }

    async def get_chunk(self, chunk_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(DocumentChunk).where(DocumentChunk.id == chunk_id))
        c = r.scalar_one_or_none()
        if not c:
            raise NotFoundException("DocumentChunk", str(chunk_id))
        return {"chunk_id": str(c.id), "doc_id": str(c.doc_id), "kb_id": str(c.kb_id),
                "chunk_index": c.chunk_index, "content": c.content,
                "token_count": c.token_count, "version": c.version,
                "is_active": c.is_active, "has_embedding": c.embedding is not None}

    # ── Query & Retrieval (4 methods) ─────────────────────────────────────────
    async def query(self, kb_id: uuid.UUID, question: str,
                    top_k: int | None, plan_type: str | None,
                    idempotency_key: str | None) -> dict:
        """Full RAG pipeline: embed → search → budget → generate → store."""
        # Phase 2A Slice 2F-35: previously the KB lookup had zero tenant
        # predicate -- any authenticated user of ANY tenant could query
        # another tenant's knowledge base by supplying its kb_id, and the
        # idempotency lookup below could theoretically hand back another
        # tenant's cached answer on a colliding idempotency key. Both are
        # now scoped server-side.
        tenant_id = self._require_trusted_tenant()

        # Idempotency
        if idempotency_key:
            iq = select(RAGQuery).where(RAGQuery.idempotency_key == idempotency_key)
            if tenant_id is not None:
                iq = iq.where(RAGQuery.tenant_id == tenant_id)
            ex = await self.db.execute(iq)
            existing = ex.scalar_one_or_none()
            if existing:
                return {**self._query_dict(existing), "idempotent": True}

        kb = await self._get_kb_trusted(kb_id)
        start_ms = int(time.time() * 1000)

        # Check KB has indexed documents
        if kb.indexed_count == 0:
            rag_query = RAGQuery(
                kb_id=kb_id, tenant_id=kb.tenant_id,
                asked_by=self.actor_id, asked_by_role=self.actor_role,
                question=question, status=QueryStatus.FAILED,
                error_message="Knowledge base has no indexed documents.",
                idempotency_key=idempotency_key,
            )
            self.db.add(rag_query)
            await self.db.flush()
            return {
                **self._query_dict(rag_query),
                "allowed_transitions": [{
                    "action": "upload_document",
                    "label": "Add documents to knowledge base",
                    "endpoint": f"/v1/rag/knowledge-bases/{kb_id}/documents",
                    "method": "POST",
                    "reason": "Knowledge base is empty. Add documents before querying.",
                }],
                "idempotent": False,
            }

        effective_top_k = min(top_k or kb.top_k, 20)
        token_budget = TOKEN_BUDGET.get(plan_type or "starter", DEFAULT_TOKEN_BUDGET)

        # Step 1: Embed question (real local embedding — see embedding_service.py)
        question_embedding = self._embed(question)
        embedding_tokens = len(question.split())  # approximation

        # Step 2: Hybrid retrieval — real pgvector cosine search + real
        # Postgres full-text keyword search, fused via Reciprocal Rank
        # Fusion, then widened via single-hop GraphRAG entity expansion.
        hybrid_results = await self._hybrid_search(kb_id, question, question_embedding, effective_top_k)
        top_chunks = [(score, chunk) for chunk, score in hybrid_results]

        # Step 3: Token budget enforcement
        context_chunks = []
        context_tokens = 0
        for score, chunk in top_chunks:
            if context_tokens + chunk.token_count <= token_budget:
                context_chunks.append((score, chunk))
                context_tokens += chunk.token_count

        # top_similarity reported to the caller is the real cosine
        # similarity of the #1 context chunk (not the RRF fusion score,
        # which is on a different scale) — this is what LOW_CONFIDENCE_
        # THRESHOLD (a cosine-similarity threshold) is meant to compare
        # against.
        top_similarity = (self._cosine_similarity(question_embedding, context_chunks[0][1].embedding)
                           if context_chunks and context_chunks[0][1].embedding else 0.0)
        low_confidence = top_similarity < LOW_CONFIDENCE_THRESHOLD

        # Step 4: Generate answer — real DeepSeek call grounded on the
        # hybrid + graph retrieved context (see _generate()).
        chunk_dicts = [{"chunk_id": str(c.id), "content": c.content,
                        "hybrid_score": round(s, 6), "doc_id": str(c.doc_id)}
                       for s, c in context_chunks]

        answer = await self._generate(question, chunk_dicts)
        completion_tokens = len(answer.split())

        # Citations
        seen_docs = set()
        citations = []
        for s, c in context_chunks:
            if str(c.doc_id) not in seen_docs:
                citations.append({"doc_id": str(c.doc_id),
                                  "chunk_id": str(c.id),
                                  "hybrid_score": round(s, 6)})
                seen_docs.add(str(c.doc_id))

        latency_ms = int(time.time() * 1000) - start_ms

        rag_query = RAGQuery(
            kb_id=kb_id, tenant_id=kb.tenant_id,
            asked_by=self.actor_id, asked_by_role=self.actor_role,
            question=question, answer=answer,
            retrieved_chunks=chunk_dicts, citations=citations,
            top_similarity=top_similarity, low_confidence=low_confidence,
            status=QueryStatus.COMPLETED,
            embedding_tokens=embedding_tokens, completion_tokens=completion_tokens,
            total_tokens=embedding_tokens + completion_tokens,
            latency_ms=latency_ms, model_used=GENERATION_MODEL,
            idempotency_key=idempotency_key,
        )
        self.db.add(rag_query)
        kb.total_tokens_used += rag_query.total_tokens
        await self.db.flush()

        await self._publish("rag.query_completed", str(kb.tenant_id), str(rag_query.id),
                            {"latency_ms": latency_ms, "total_tokens": rag_query.total_tokens,
                             "low_confidence": low_confidence})

        result = {**self._query_dict(rag_query), "idempotent": False}
        if low_confidence:
            result["allowed_transitions"] = [{
                "action": "contact_staff",
                "label": "Ask a staff member",
                "reason": f"Answer confidence is low (similarity: {top_similarity:.2f}). A staff member can help.",
            }]
        return result

    async def search_only(self, kb_id: uuid.UUID, question: str, top_k: int) -> dict:
        """Hybrid search only — no LLM generation. Returns ranked chunks
        (real pgvector similarity + real full-text keyword search, fused
        via RRF, widened via single-hop GraphRAG expansion)."""
        kb = await self._get_kb(kb_id)
        question_embedding = self._embed(question)

        effective_top_k = min(top_k, 20)
        hybrid_results = await self._hybrid_search(kb_id, question, question_embedding, effective_top_k)

        return {
            "kb_id": str(kb_id), "question": question,
            "results": [{"chunk_id": str(c.id), "doc_id": str(c.doc_id),
                         "content": c.content[:300], "hybrid_score": round(s, 6),
                         "chunk_index": c.chunk_index} for c, s in hybrid_results],
            "total_searched": len(hybrid_results),
        }

    async def get_query(self, query_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(RAGQuery).where(RAGQuery.id == query_id))
        q = r.scalar_one_or_none()
        if not q:
            raise NotFoundException("RAGQuery", str(query_id))
        return self._query_dict(q)

    async def list_queries(self, tenant_id: uuid.UUID, kb_id: uuid.UUID | None,
                            limit: int, cursor: str | None) -> dict:
        q = select(RAGQuery).where(RAGQuery.tenant_id == tenant_id)            .order_by(RAGQuery.created_at.desc())
        if kb_id:
            q = q.where(RAGQuery.kb_id == kb_id)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(RAGQuery.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        queries = r.scalars().all()
        has_next = len(queries) > limit
        queries = queries[:limit]
        nc = encode_cursor({"created_at": queries[-1].created_at.isoformat()}) if has_next and queries else None
        return {"queries": [self._query_dict(q) for q in queries],
                "has_next": has_next, "next_cursor": nc}

    # ── Platform Admin (2 methods) ────────────────────────────────────────────
    async def get_platform_usage(self) -> dict:
        kb_r = await self.db.execute(
            select(func.count(KnowledgeBase.id), func.sum(KnowledgeBase.total_tokens_used))
            .where(KnowledgeBase.is_active == True))
        kb_row = kb_r.one()

        doc_r = await self.db.execute(
            select(func.count(KBDocument.id)).where(KBDocument.status == DocStatus.INDEXED))
        indexed_docs = doc_r.scalar_one_or_none() or 0

        query_r = await self.db.execute(
            select(func.count(RAGQuery.id), func.avg(RAGQuery.latency_ms),
                   func.sum(RAGQuery.total_tokens))
            .where(RAGQuery.status == QueryStatus.COMPLETED))
        q_row = query_r.one()

        return {
            "active_knowledge_bases": kb_row[0] or 0,
            "total_tokens_used": int(kb_row[1] or 0),
            "indexed_documents": indexed_docs,
            "total_queries_completed": q_row[0] or 0,
            "avg_query_latency_ms": round(float(q_row[1] or 0), 1),
            "total_query_tokens": int(q_row[2] or 0),
            "generated_at": utcnow().isoformat(),
        }
