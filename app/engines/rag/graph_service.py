"""RAG Engine — GraphRAG-lite service.

MODULE-L5-51 scope (honest, bounded):
  - For each ingested chunk, extract named entities + pairwise relationships
    via a real LLM call (DeepSeekClientService — the same client already
    backing the customer-facing AI chat assistant and the inventory PDF
    extraction engine). Structured-JSON-extraction prompt, same
    "LLM call -> parse JSON -> store rows" pattern as
    app/engines/inventory/extraction_service.py.
  - Entities + relationships + chunk-entity links are stored in
    kb_entities / kb_entity_relationships / kb_chunk_entities.
  - At query time, given the top hybrid-ranked chunks, find the entities
    they mention, then find OTHER chunks that mention any of those same
    entities (or an entity directly related to one) and pull those in as
    additional context.

This is SINGLE-HOP entity co-occurrence expansion — not full community
detection / hierarchical summarization as in the original Microsoft
GraphRAG paper. It is a real, working retrieval augmentation, just a
deliberately bounded one.
"""
from __future__ import annotations

import json
import uuid

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.ai_conversation.deepseek_client import DeepSeekClientService
from app.engines.rag.constants import GRAPH_MAX_ENTITIES_PER_CHUNK, GRAPH_MAX_EXPANSION_CHUNKS
from app.engines.rag.models import DocumentChunk, KBEntity, KBEntityRelationship, KBChunkEntity

logger = structlog.get_logger("rag.graph")

GRAPH_EXTRACTION_SYSTEM_PROMPT = """You extract a knowledge graph from a short passage of text.
Return STRICT JSON only — no prose, no markdown fences — matching exactly this shape:

{"entities": [{"name": "string", "type": "string (person, organization, product, location, concept, or other)", "description": "short string or null"}],
 "relationships": [{"source": "entity name", "target": "entity name", "relationship": "short verb phrase, e.g. 'requires', 'is part of', 'is used with'"}]}

Rules:
- Extract at most 8 of the most important/distinct entities from the passage.
- Only include a relationship if BOTH its source and target are in the entities list.
- If the passage has no meaningfully extractable entities, return {"entities": [], "relationships": []}.
- Output ONLY the JSON object, nothing else."""


def _parse_graph_json(raw_content: str) -> dict:
    content = (raw_content or "").strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"entities": [], "relationships": []}
    if not isinstance(parsed, dict):
        return {"entities": [], "relationships": []}
    return {
        "entities": parsed.get("entities") if isinstance(parsed.get("entities"), list) else [],
        "relationships": parsed.get("relationships") if isinstance(parsed.get("relationships"), list) else [],
    }


async def extract_graph_for_chunk(db: AsyncSession, kb_id: uuid.UUID, tenant_id: uuid.UUID,
                                   chunk: DocumentChunk, request_id: str = "—") -> dict:
    """Real LLM-driven entity/relationship extraction for one chunk.
    Never raises — a failed/unavailable LLM call just means this chunk
    contributes no graph data (degrades to pure hybrid search), it must not
    break ingestion."""
    try:
        llm = DeepSeekClientService(db=db, request_id=request_id)
        response = await llm.chat(messages=[
            {"role": "system", "content": GRAPH_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": chunk.content[:4000]},
        ])
        raw_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = _parse_graph_json(raw_content)
    except Exception as e:
        logger.warning("rag.graph_extraction_failed", chunk_id=str(chunk.id), error=str(e))
        return {"entities": 0, "relationships": 0}

    entities = parsed["entities"][:GRAPH_MAX_ENTITIES_PER_CHUNK]
    name_to_id: dict[str, uuid.UUID] = {}

    for raw in entities:
        name = (raw.get("name") or "").strip()
        if not name:
            continue
        etype = (raw.get("type") or "other").strip().lower()[:50]
        existing = await db.execute(select(KBEntity).where(
            KBEntity.kb_id == kb_id, KBEntity.name == name, KBEntity.entity_type == etype))
        entity = existing.scalar_one_or_none()
        if entity:
            entity.mention_count += 1
        else:
            entity = KBEntity(kb_id=kb_id, tenant_id=tenant_id, name=name,
                               entity_type=etype, description=raw.get("description"),
                               mention_count=1)
            db.add(entity)
            await db.flush()
        name_to_id[name] = entity.id

        link_exists = await db.execute(select(KBChunkEntity).where(
            KBChunkEntity.chunk_id == chunk.id, KBChunkEntity.entity_id == entity.id))
        if not link_exists.scalar_one_or_none():
            db.add(KBChunkEntity(chunk_id=chunk.id, entity_id=entity.id, kb_id=kb_id))

    rel_count = 0
    for rel in parsed["relationships"]:
        src_name = (rel.get("source") or "").strip()
        tgt_name = (rel.get("target") or "").strip()
        if src_name not in name_to_id or tgt_name not in name_to_id or src_name == tgt_name:
            continue
        db.add(KBEntityRelationship(
            kb_id=kb_id, tenant_id=tenant_id,
            source_entity_id=name_to_id[src_name], target_entity_id=name_to_id[tgt_name],
            relationship=(rel.get("relationship") or "related_to")[:200],
            source_chunk_id=chunk.id,
        ))
        rel_count += 1

    await db.flush()
    return {"entities": len(name_to_id), "relationships": rel_count}


async def expand_via_graph(db: AsyncSession, kb_id: uuid.UUID,
                            seed_chunk_ids: list[uuid.UUID]) -> list[DocumentChunk]:
    """Single-hop expansion: entities mentioned in seed_chunk_ids -> other
    chunks mentioning the SAME entity, or an entity directly related to it
    via kb_entity_relationships. Returns extra DocumentChunk rows not
    already in seed_chunk_ids, ranked by how many distinct graph paths lead
    to them (more shared/related entities = higher relevance)."""
    if not seed_chunk_ids:
        return []

    seed_entities_r = await db.execute(
        select(KBChunkEntity.entity_id).where(KBChunkEntity.chunk_id.in_(seed_chunk_ids)).distinct())
    seed_entity_ids = [row[0] for row in seed_entities_r.all()]
    if not seed_entity_ids:
        return []

    related_r = await db.execute(
        select(KBEntityRelationship.target_entity_id).where(
            KBEntityRelationship.source_entity_id.in_(seed_entity_ids)).union(
        select(KBEntityRelationship.source_entity_id).where(
            KBEntityRelationship.target_entity_id.in_(seed_entity_ids))))
    related_entity_ids = {row[0] for row in related_r.all()}
    all_entity_ids = list(set(seed_entity_ids) | related_entity_ids)

    candidates_r = await db.execute(
        select(KBChunkEntity.chunk_id, func.count(KBChunkEntity.entity_id).label("hits"))
        .where(KBChunkEntity.entity_id.in_(all_entity_ids),
               KBChunkEntity.chunk_id.notin_(seed_chunk_ids))
        .group_by(KBChunkEntity.chunk_id)
        .order_by(func.count(KBChunkEntity.entity_id).desc())
        .limit(GRAPH_MAX_EXPANSION_CHUNKS))
    ranked_chunk_ids = [row[0] for row in candidates_r.all()]
    if not ranked_chunk_ids:
        return []

    chunks_r = await db.execute(select(DocumentChunk).where(
        DocumentChunk.id.in_(ranked_chunk_ids), DocumentChunk.is_active == True))
    chunks_by_id = {c.id: c for c in chunks_r.scalars().all()}
    # Preserve rank order.
    return [chunks_by_id[cid] for cid in ranked_chunk_ids if cid in chunks_by_id]
