"""
AI Chat Engine — Router (2 endpoints).
POST /v1/ai/chat  — send a message to the DeepSeek-powered assistant
GET  /v1/ai/chat/meta — engine health + tool listing
"""
from __future__ import annotations
import uuid
import structlog
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.ai_chat.service import AIChatService
from app.engines.ai_chat.constants import DEEPSEEK_MODEL, TOOLS
from app.schemas.base import ApiResponse, ok

logger    = structlog.get_logger("ai_chat.router")
router    = APIRouter(prefix="/v1/ai", tags=["AI Chat Engine"])
ENGINE_ID = "ai_chat"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> AIChatService:
    customer_id = uuid.UUID(u.user_id) if u.user_id else uuid.uuid4()
    return AIChatService(
        db=db,
        customer_id=customer_id,
        request_id=getattr(r.state, "request_id", "—"),
    )


# ── Schemas ───────────────────────────────────────────────────────────────────
class MessageTurn(BaseModel):
    role:    str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=4096)

class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2048,
                         description="The customer's latest message.")
    history: list[MessageTurn] = Field(default_factory=list, max_length=20,
                                       description="Previous conversation turns.")

class AIChatResponse(BaseModel):
    reply:        str
    tools_called: list[str] = Field(default_factory=list)
    model:        str        = DEEPSEEK_MODEL


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/chat/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {
        "engine_id":      ENGINE_ID,
        "name":           "AI Chat Engine (DeepSeek)",
        "model":          DEEPSEEK_MODEL,
        "version":        "1.0.0",
        "endpoint_count": 2,
        "status":         "active",
        "capabilities": [
            "natural_language_chat",
            "tool_calling",
            "booking_lookup",
            "job_tracking",
            "price_estimation",
            "service_faqs",
            "conversation_history",
        ],
        "tools": [t["function"]["name"] for t in TOOLS],
    }


@router.post(
    "/chat",
    response_model=ApiResponse[AIChatResponse],
    status_code=status.HTTP_200_OK,
    summary="Chat with the AI assistant",
    description=(
        "Send a customer message to the DeepSeek LLM. "
        "The AI may call internal tools to fetch real data (bookings, jobs, prices) "
        "and returns a natural language response."
    ),
)
async def ai_chat(
    request: Request,
    body:    AIChatRequest,
    svc:     AIChatService = Depends(_svc),
) -> ApiResponse[AIChatResponse]:
    rid = getattr(request.state, "request_id", "—")
    logger.info("ai_chat.request", request_id=rid,
                message_len=len(body.message), history_len=len(body.history))

    result = await svc.chat(
        user_message=body.message,
        history=[t.model_dump() for t in body.history],
    )

    return ok(
        AIChatResponse(
            reply        = result["reply"],
            tools_called = result["tools_called"],
        ),
        request_id=rid,
        engine_id=ENGINE_ID,
    )
