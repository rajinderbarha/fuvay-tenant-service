"""Chat Engine — Router (13 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.chat.service import ChatService
from app.schemas.base import ApiResponse, ok
logger = structlog.get_logger("chat.router")
router = APIRouter(prefix="/v1/chat", tags=["Chat Engine"])
ENGINE_ID = "chat"
def _svc(r: Request, db: AsyncSession=Depends(get_db), u: UserContext=Depends(get_current_user)):
    return ChatService(db=db, request_id=getattr(r.state,"request_id","—"),
                        actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Chat Engine", "version": "11.0.0",
            "endpoint_count": 13, "status": "active",
            "capabilities": ["tenant_scoped_queries","typing_redis_only",
                             "message_idempotency","soft_delete_audit","cursor_pagination",
                             "read_receipts","system_messages"]}

@router.post("/conversations", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_conversation(r: Request, u: UserContext=Depends(get_current_user),
                               s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.get_or_create_conversation(uuid.UUID(body["tenant_id"]),
              body["entity_type"], body["entity_id"], body.get("participants",[])), _rid(r), ENGINE_ID)

@router.get("/conversations/{conversation_id}", response_model=ApiResponse[dict])
async def get_conversation(conversation_id: uuid.UUID, r: Request,
                            tenant_id: uuid.UUID=Query(...),
                            u: UserContext=Depends(get_current_user),
                            s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_conversation(conversation_id, tenant_id), _rid(r), ENGINE_ID)

@router.get("/conversations", response_model=ApiResponse[dict])
async def list_conversations(r: Request, tenant_id: uuid.UUID=Query(...),
                              entity_type: str|None=Query(None),
                              limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                              u: UserContext=Depends(get_current_user),
                              s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_conversations(tenant_id, entity_type, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/conversations/{conversation_id}/participants", response_model=ApiResponse[dict])
async def list_participants(conversation_id: uuid.UUID, r: Request,
                             tenant_id: uuid.UUID=Query(...),
                             u: UserContext=Depends(get_current_user),
                             s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_participants(conversation_id, tenant_id), _rid(r), ENGINE_ID)

@router.post("/conversations/{conversation_id}/messages",
             summary="Send message — idempotent on X-Idempotency-Key",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def send_message(conversation_id: uuid.UUID, r: Request,
                        tenant_id: uuid.UUID=Query(...),
                        u: UserContext=Depends(get_current_user),
                        s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.send_message(conversation_id, tenant_id,
              uuid.UUID(u.user_id) if u.user_id else None, u.role or "user",
              body.get("message_type","text"), body.get("content",""),
              uuid.UUID(body["media_id"]) if body.get("media_id") else None,
              r.headers.get("X-Idempotency-Key")), _rid(r), ENGINE_ID)

@router.get("/conversations/{conversation_id}/messages", response_model=ApiResponse[dict])
async def list_messages(conversation_id: uuid.UUID, r: Request,
                         tenant_id: uuid.UUID=Query(...),
                         limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                         u: UserContext=Depends(get_current_user),
                         s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_messages(conversation_id, tenant_id, limit, cursor), _rid(r), ENGINE_ID)

@router.post("/conversations/{conversation_id}/messages/read", response_model=ApiResponse[dict])
async def mark_read(conversation_id: uuid.UUID, r: Request,
                     tenant_id: uuid.UUID=Query(...),
                     u: UserContext=Depends(get_current_user),
                     s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    reader_id = uuid.UUID(u.user_id) if u.user_id else uuid.uuid4()
    return ok(await s.mark_messages_read(conversation_id, tenant_id, reader_id), _rid(r), ENGINE_ID)

@router.get("/conversations/{conversation_id}/unread", response_model=ApiResponse[dict])
async def get_unread(conversation_id: uuid.UUID, r: Request,
                      tenant_id: uuid.UUID=Query(...),
                      u: UserContext=Depends(get_current_user),
                      s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    user_id = uuid.UUID(u.user_id) if u.user_id else uuid.uuid4()
    return ok(await s.get_unread_count(conversation_id, tenant_id, user_id), _rid(r), ENGINE_ID)

@router.post("/conversations/{conversation_id}/typing",
             summary="Set typing indicator — pure Redis, zero DB writes", response_model=ApiResponse[dict])
async def set_typing(conversation_id: uuid.UUID, r: Request,
                      u: UserContext=Depends(get_current_user),
                      s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    user_id = uuid.UUID(u.user_id) if u.user_id else uuid.uuid4()
    return ok(await s.set_typing(conversation_id, user_id), _rid(r), ENGINE_ID)

@router.get("/conversations/{conversation_id}/typing",
            summary="Get typing indicators — pure Redis, zero DB reads", response_model=ApiResponse[dict])
async def get_typing(conversation_id: uuid.UUID, r: Request,
                      tenant_id: uuid.UUID=Query(...),
                      u: UserContext=Depends(get_current_user),
                      s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_typing(conversation_id, tenant_id), _rid(r), ENGINE_ID)

@router.put("/messages/{message_id}", response_model=ApiResponse[dict])
async def edit_message(message_id: uuid.UUID, r: Request,
                        tenant_id: uuid.UUID=Query(...),
                        u: UserContext=Depends(get_current_user),
                        s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.edit_message(message_id, tenant_id, body["content"]), _rid(r), ENGINE_ID)

@router.delete("/messages/{message_id}",
               summary="Soft-delete — content replaced, row kept for audit", response_model=ApiResponse[dict])
async def delete_message(message_id: uuid.UUID, r: Request,
                          tenant_id: uuid.UUID=Query(...),
                          u: UserContext=Depends(get_current_user),
                          s: ChatService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_message(message_id, tenant_id), _rid(r), ENGINE_ID)
