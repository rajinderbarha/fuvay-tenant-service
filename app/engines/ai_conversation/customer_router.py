"""Sprint 15 — Customer AI Chat API (session-based, persistent)."""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user_optional, UserContext
from app.dependencies.db import get_db
from app.engines.ai_conversation.service import AIConversationService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/customer/ai-chat", tags=["Customer AI Chat"])


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> AIConversationService:
    return AIConversationService(db=db, request_id=getattr(r.state, "request_id", "—"))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ══════════════════════════════════════════════════════════════════════════════
# SESSION LIFECYCLE
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/sessions",
    response_model=ApiResponse[dict],
    summary="Start a new AI conversation session",
)
async def create_session(
    r: Request,
    svc: AIConversationService = Depends(_svc),
    user: UserContext | None = Depends(get_current_user_optional),
):
    """
    Create a new AI conversation session.
    Optionally accepts category_id to pre-seed the context.
    Returns session_key used to continue the conversation.
    """
    body = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    category_id = None
    context_data = {}

    if isinstance(body, dict):
        raw_cat = body.get("category_id")
        if raw_cat:
            try:
                category_id = uuid.UUID(raw_cat)
            except ValueError:
                pass
        context_data = body.get("context", {}) or {}

    customer_id = user.user_id if user else None
    data = await svc.create_session(
        customer_id=customer_id,
        category_id=category_id,
        context_data=context_data,
    )
    return ok(data, _rid(r), "ai_conversation")


@router.get(
    "/sessions",
    response_model=ApiResponse[dict],
    summary="List my conversation sessions",
)
async def list_my_sessions(
    r: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    svc: AIConversationService = Depends(_svc),
    user: UserContext = Depends(get_current_user_optional),
):
    """List all AI conversation sessions for the authenticated customer."""
    if not user:
        return ok({"sessions": [], "total": 0, "page": 1, "page_size": page_size},
                  _rid(r), "ai_conversation")
    data = await svc.list_customer_sessions(
        customer_id=user.user_id, page=page, page_size=page_size
    )
    return ok(data, _rid(r), "ai_conversation")


@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[dict],
    summary="Get session details",
)
async def get_session(
    session_id: uuid.UUID,
    r: Request,
    svc: AIConversationService = Depends(_svc),
):
    """Get AI conversation session details by ID."""
    data = await svc.get_session(session_id)
    return ok(data, _rid(r), "ai_conversation")


@router.post(
    "/sessions/{session_id}/close",
    response_model=ApiResponse[dict],
    summary="Close a session",
)
async def close_session(
    session_id: uuid.UUID,
    r: Request,
    svc: AIConversationService = Depends(_svc),
):
    """Mark an AI conversation session as completed/closed."""
    data = await svc.close_session(session_id)
    return ok(data, _rid(r), "ai_conversation")


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGES
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/sessions/{session_id}/messages",
    response_model=ApiResponse[dict],
    summary="Send a message in a session",
)
async def send_message(
    session_id: uuid.UUID,
    r: Request,
    svc: AIConversationService = Depends(_svc),
    user: UserContext | None = Depends(get_current_user_optional),
):
    """
    Send a user message to the AI assistant.
    DeepSeek processes the message, executes backend tools if needed,
    and returns the assistant reply.

    Body:
        message (str, required) — the user's text message
    """
    body = await r.json()
    message = (body.get("message") or "").strip()
    if not message:
        from app.exceptions import ServiceOSException
        raise ServiceOSException("AI_MESSAGE_EMPTY", "message is required.", status_code=422)

    customer_id = user.user_id if user else None
    data = await svc.send_message(
        session_id=session_id,
        user_message=message,
        customer_id=customer_id,
    )
    return ok(data, _rid(r), "ai_conversation")


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ApiResponse[dict],
    summary="Get session message history",
)
async def get_messages(
    session_id: uuid.UUID,
    r: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    svc: AIConversationService = Depends(_svc),
):
    """Get paginated message history for a session."""
    data = await svc.get_messages(session_id=session_id, page=page, page_size=page_size)
    return ok(data, _rid(r), "ai_conversation")
