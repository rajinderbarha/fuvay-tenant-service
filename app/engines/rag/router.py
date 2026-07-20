"""RAG Engine — Router (18 endpoints). Zero inline imports. Zero business logic."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission, require_mutation_access_scope
from app.core.security import get_client_ip, rate_limiter
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.rag.service import RAGService
from app.schemas.base import ApiResponse, Links, Link, ok

logger = structlog.get_logger("rag.router")
router = APIRouter(prefix="/v1/rag", tags=["RAG Engine"])
ENGINE_ID = "rag"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> RAGService:
    # Phase 2A Slice 2F-35: actor_tenant_id is now passed so RAGService can
    # independently enforce tenant authority on query/delete_kb/
    # ingest_document/delete_document/reindex_document, rather than
    # trusting kb_id/doc_id alone.
    return RAGService(db=db, request_id=getattr(r.state, "request_id", "—"),
                       actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                       actor_role=u.role,
                       actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Engine Meta ───────────────────────────────────────────────────────────────
@router.get("/meta", summary="RAG engine introspection", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {
        "engine_id": ENGINE_ID, "name": "RAG Engine", "version": "6.0.0",
        "endpoint_count": 18, "status": "active",
        "embedding_model": "text-embedding-3-small",
        "generation_model": "gpt-4o-mini",
        "pipeline": ["embed_question", "vector_search", "token_budget",
                     "generate_answer", "store_trace"],
        "capabilities": ["knowledge_base_management", "document_ingestion",
                         "vector_search", "rag_generation", "citation_tracking",
                         "query_history", "health_signal", "idempotent_ingestion"],
    }


# ── Knowledge Base CRUD (5 endpoints) ────────────────────────────────────────
@router.post("/knowledge-bases",
             summary="Create knowledge base for a tenant",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_kb(r: Request,
                     u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                     s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.create_kb(
        tenant_id=uuid.UUID(body["tenant_id"]),
        name=body["name"],
        description=body.get("description"),
        vertical=body.get("vertical"),
        chunk_size=body.get("chunk_size", 512),
        chunk_overlap=body.get("chunk_overlap", 64),
        top_k=body.get("top_k", 5),
    )
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[Link(
                  href=f"/v1/rag/knowledge-bases/{data['kb_id']}/documents",
                  method="POST", rel="ingest_document",
                  description="Add documents to start building your knowledge base")]))


@router.get("/knowledge-bases/{kb_id}",
            summary="Get knowledge base detail",
            response_model=ApiResponse[dict])
async def get_kb(kb_id: uuid.UUID, r: Request,
                  u: UserContext = Depends(get_current_user),
                  s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_kb(kb_id)
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id}/knowledge-bases",
            summary="List all knowledge bases for a tenant (cursor-paginated)",
            response_model=ApiResponse[dict])
async def list_kbs(tenant_id: uuid.UUID, r: Request,
                    limit: int = Query(20, ge=1, le=100),
                    cursor: str | None = Query(None),
                    u: UserContext = Depends(get_current_user),
                    s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_tenant_kbs(tenant_id, limit, cursor)
    return ok(data, _rid(r), ENGINE_ID)


@router.put("/knowledge-bases/{kb_id}",
            summary="Update KB settings (chunk size, overlap, top-k)",
            response_model=ApiResponse[dict])
async def update_kb(kb_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                     s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.update_kb(kb_id, body)
    return ok(data, _rid(r), ENGINE_ID)


@router.delete("/knowledge-bases/{kb_id}",
               summary="Soft-delete KB — deactivates all chunks",
               response_model=ApiResponse[dict])
async def delete_kb(kb_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                     s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.delete_kb(kb_id)
    return ok(data, _rid(r), ENGINE_ID)


# ── Document Management (5 endpoints) ────────────────────────────────────────
@router.post("/knowledge-bases/{kb_id}/documents",
             summary="Ingest document — idempotent on content hash, returns status for polling",
             status_code=status.HTTP_202_ACCEPTED,
             response_model=ApiResponse[dict])
async def ingest_document(kb_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                           s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.ingest_document(
        kb_id=kb_id,
        file_name=body["file_name"],
        mime_type=body.get("mime_type", "text/plain"),
        content=body["content"],
        source_url=body.get("source_url"),
        tags=body.get("tags", []),
    )
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[Link(
                  href=f"/v1/rag/documents/{data['doc_id']}",
                  method="GET", rel="poll_status")]))


@router.get("/knowledge-bases/{kb_id}/documents",
            summary="List documents in a KB with status filter",
            response_model=ApiResponse[dict])
async def list_documents(kb_id: uuid.UUID, r: Request,
                          doc_status: str | None = Query(None, alias="status"),
                          limit: int = Query(50, ge=1, le=200),
                          cursor: str | None = Query(None),
                          u: UserContext = Depends(get_current_user),
                          s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_documents(kb_id, doc_status, limit, cursor)
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/documents/{doc_id}",
            summary="Get document detail with chunk count and indexing status",
            response_model=ApiResponse[dict])
async def get_document(doc_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_document(doc_id)
    return ok(data, _rid(r), ENGINE_ID)


@router.delete("/documents/{doc_id}",
               summary="Delete document — soft-deletes all chunks from vector store",
               response_model=ApiResponse[dict])
async def delete_document(doc_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                           s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.delete_document(doc_id)
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/documents/{doc_id}/reindex",
             summary="Reindex — soft-deletes old chunks, re-chunks and re-embeds",
             response_model=ApiResponse[dict])
async def reindex_document(doc_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                            s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.reindex_document(doc_id)
    return ok(data, _rid(r), ENGINE_ID)


# ── Chunk Management (2 endpoints) ────────────────────────────────────────────
@router.get("/knowledge-bases/{kb_id}/chunks",
            summary="List active chunks with embedding metadata (for quality inspection)",
            response_model=ApiResponse[dict])
async def list_chunks(kb_id: uuid.UUID, r: Request,
                       doc_id: uuid.UUID | None = Query(None),
                       limit: int = Query(50, ge=1, le=200),
                       cursor: str | None = Query(None),
                       u: UserContext = Depends(get_current_user),
                       s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_chunks(kb_id, doc_id, limit, cursor)
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/chunks/{chunk_id}",
            summary="Get single chunk with full content and embedding status",
            response_model=ApiResponse[dict])
async def get_chunk(chunk_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(get_current_user),
                     s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_chunk(chunk_id)
    return ok(data, _rid(r), ENGINE_ID)


# ── Query & Retrieval (4 endpoints) ───────────────────────────────────────────
@router.post("/query",
             summary="Full RAG pipeline — embed → search → generate → store trace. Rate limited.",
             response_model=ApiResponse[dict])
async def query(r: Request,
                # Phase 2A Slice 2F-35: scope-only guard -- preserves every
                # previously-admitted role (mixed persona), adds only the
                # read-only mutation-access-scope rejection.
                u: UserContext = Depends(require_mutation_access_scope),
                s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(
        f"rag_query:{u.tenant_id}", "auth:password_reset",
        str(u.tenant_id or "platform"))
    body = await r.json()
    data = await s.query(
        kb_id=uuid.UUID(body["kb_id"]),
        question=body["question"],
        top_k=body.get("top_k"),
        plan_type=body.get("plan_type"),
        idempotency_key=r.headers.get("X-Idempotency-Key"),
    )
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[Link(
                  href=f"/v1/rag/queries/{data['query_id']}",
                  method="GET", rel="query_detail")]))


@router.post("/search",
             summary="Vector search only — no LLM generation. Returns ranked chunks.",
             response_model=ApiResponse[dict])
async def search(r: Request,
                  u: UserContext = Depends(get_current_user),
                  s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.search_only(
        kb_id=uuid.UUID(body["kb_id"]),
        question=body["question"],
        top_k=body.get("top_k", 5),
    )
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/queries/{query_id}",
            summary="Get stored query result with full pipeline trace",
            response_model=ApiResponse[dict])
async def get_query(query_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(get_current_user),
                     s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_query(query_id)
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id}/queries",
            summary="Query history for a tenant — cursor-paginated",
            response_model=ApiResponse[dict])
async def list_queries(tenant_id: uuid.UUID, r: Request,
                        kb_id: uuid.UUID | None = Query(None),
                        limit: int = Query(50, ge=1, le=200),
                        cursor: str | None = Query(None),
                        u: UserContext = Depends(get_current_user),
                        s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_queries(tenant_id, kb_id, limit, cursor)
    return ok(data, _rid(r), ENGINE_ID)


# ── Platform Admin (1 endpoint) ───────────────────────────────────────────────
@router.get("/platform/usage",
            summary="[Admin] Platform-wide RAG usage — tokens, queries, KB coverage",
            response_model=ApiResponse[dict])
async def platform_usage(r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: RAGService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_platform_usage()
    return ok(data, _rid(r), ENGINE_ID)
