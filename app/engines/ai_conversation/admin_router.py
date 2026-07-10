"""Sprint 15 — Admin AI Chat API (session logs, prompt templates, test console)."""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.engines.ai_conversation.service import AIConversationService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/ai-chat", tags=["Admin AI Chat"])


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> AIConversationService:
    return AIConversationService(db=db, request_id=getattr(r.state, "request_id", "—"))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ══════════════════════════════════════════════════════════════════════════════
# SESSIONS (admin visibility)
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/sessions",
    response_model=ApiResponse[dict],
    summary="Admin: list all AI chat sessions",
)
async def admin_list_sessions(
    r: Request,
    workflow_status: str | None = Query(None, description="Filter: active/completed/abandoned"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: AIConversationService = Depends(_svc),
):
    """Admin view of all AI conversation sessions with optional status filter."""
    data = await svc.admin_list_sessions(
        workflow_status=workflow_status, page=page, page_size=page_size
    )
    return ok(data, _rid(r), "admin_ai_chat")


@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[dict],
    summary="Admin: get session detail",
)
async def admin_get_session(
    session_id: uuid.UUID,
    r: Request,
    svc: AIConversationService = Depends(_svc),
):
    """Admin: get full session detail by ID."""
    data = await svc.get_session(session_id)
    return ok(data, _rid(r), "admin_ai_chat")


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ApiResponse[dict],
    summary="Admin: get session messages",
)
async def admin_get_session_messages(
    session_id: uuid.UUID,
    r: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    svc: AIConversationService = Depends(_svc),
):
    """Admin: get all messages in a session."""
    data = await svc.get_messages(session_id=session_id, page=page, page_size=page_size)
    return ok(data, _rid(r), "admin_ai_chat")


# ══════════════════════════════════════════════════════════════════════════════
# LLM CALL LOGS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/logs",
    response_model=ApiResponse[dict],
    summary="Admin: list LLM call logs",
)
async def admin_list_logs(
    r: Request,
    session_id: uuid.UUID | None = Query(None, description="Filter by session"),
    response_status: str | None = Query(None, description="Filter: success/error/timeout"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: AIConversationService = Depends(_svc),
):
    """Admin: list all DeepSeek API call logs with token usage and latency."""
    data = await svc.admin_list_llm_logs(
        session_id=session_id,
        response_status=response_status,
        page=page,
        page_size=page_size,
    )
    return ok(data, _rid(r), "admin_ai_chat")


@router.get(
    "/logs/{log_id}",
    response_model=ApiResponse[dict],
    summary="Admin: get LLM call log detail",
)
async def admin_get_log(
    log_id: uuid.UUID,
    r: Request,
    svc: AIConversationService = Depends(_svc),
):
    """Admin: get a specific LLM call log including all associated tool calls."""
    data = await svc.admin_get_llm_log(log_id)
    return ok(data, _rid(r), "admin_ai_chat")


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/prompt-templates",
    response_model=ApiResponse[dict],
    summary="Admin: list prompt templates",
)
async def list_prompt_templates(
    r: Request,
    category: str | None = Query(None, description="Filter by category: system/workflow/safety"),
    active_only: bool = Query(True),
    svc: AIConversationService = Depends(_svc),
):
    """Admin: list all AI prompt templates."""
    data = await svc.list_prompt_templates(category=category, active_only=active_only)
    return ok(data, _rid(r), "admin_ai_chat")


@router.post(
    "/prompt-templates",
    response_model=ApiResponse[dict],
    summary="Admin: create prompt template",
    status_code=201,
)
async def create_prompt_template(
    r: Request,
    svc: AIConversationService = Depends(_svc),
):
    """
    Admin: create a new prompt template.

    Body:
        template_key (str, required, unique)
        name (str, required)
        description (str, optional)
        category (str: system/workflow/safety/context)
        template_content (str, required)
        variables (list[str], optional)
        is_active (bool, default true)
    """
    body = await r.json()
    data = await svc.create_prompt_template(body)
    return ok(data, _rid(r), "admin_ai_chat")


@router.get(
    "/prompt-templates/{template_key}",
    response_model=ApiResponse[dict],
    summary="Admin: get prompt template",
)
async def get_prompt_template(
    template_key: str,
    r: Request,
    svc: AIConversationService = Depends(_svc),
):
    """Admin: get a single prompt template by key."""
    data = await svc.get_prompt_template(template_key)
    return ok(data, _rid(r), "admin_ai_chat")


@router.put(
    "/prompt-templates/{template_key}",
    response_model=ApiResponse[dict],
    summary="Admin: update prompt template",
)
async def update_prompt_template(
    template_key: str,
    r: Request,
    svc: AIConversationService = Depends(_svc),
):
    """
    Admin: update a prompt template. Changing template_content increments version.
    """
    body = await r.json()
    data = await svc.update_prompt_template(template_key, body)
    return ok(data, _rid(r), "admin_ai_chat")


# ══════════════════════════════════════════════════════════════════════════════
# TEST CONSOLE
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/test-console",
    response_model=ApiResponse[dict],
    summary="Admin: test DeepSeek with a message",
)
async def admin_test_console(
    r: Request,
    svc: AIConversationService = Depends(_svc),
):
    """
    Admin test console — fire a single DeepSeek call without session persistence.
    Useful for testing prompt templates.

    Body:
        message (str, required)
        template_key (str, optional) — use this template's system prompt
        context (dict, optional) — extra context injected
    """
    body = await r.json()
    message      = (body.get("message") or "").strip()
    template_key = body.get("template_key")
    context      = body.get("context", {})

    if not message:
        from app.exceptions import ServiceOSException
        raise ServiceOSException("AI_MESSAGE_EMPTY", "message is required.", status_code=422)

    data = await svc.admin_test_console(
        message=message,
        template_key=template_key,
        context=context,
    )
    return ok(data, _rid(r), "admin_ai_chat")
