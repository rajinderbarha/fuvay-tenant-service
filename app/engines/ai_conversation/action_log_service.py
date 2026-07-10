"""Sprint 29 — AIActionLogService: write + query ai_action_logs."""
from __future__ import annotations
import uuid
from typing import Any

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.ai_conversation.sprint29_models import AIActionLog
from app.engines.ai_conversation.sprint29_constants import (
    AI_ACTION_REQUESTED, AI_ACTION_VALIDATED, AI_ACTION_EXECUTED,
    AI_ACTION_BLOCKED, AI_ACTION_FAILED,
)


def _mask(payload: dict | None) -> dict | None:
    """Remove sensitive customer PII from logged payloads."""
    if not payload:
        return payload
    MASK_KEYS = {
        "customer_phone", "customer_email", "student_phone",
        "student_email", "address_snapshot",
    }
    return {
        k: ("***" if k in MASK_KEYS else v)
        for k, v in payload.items()
    }


class AIActionLogService:
    """Writes and queries ai_action_logs table."""

    async def log_action(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        action: str,
        status: str,
        intent: str | None = None,
        flow_type: str | None = None,
        draft_type: str | None = None,
        draft_id: uuid.UUID | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        request_payload: dict | None = None,
        response_payload: dict | None = None,
    ) -> AIActionLog:
        """Create an ai_action_log record."""
        log = AIActionLog(
            session_id       = session_id,
            customer_id      = customer_id,
            action           = action,
            status           = status,
            intent           = intent,
            flow_type        = flow_type,
            draft_type       = draft_type,
            draft_id         = draft_id,
            failure_code     = failure_code,
            failure_message  = failure_message,
            request_payload  = _mask(request_payload),
            response_payload = _mask(response_payload),
        )
        db.add(log)
        await db.flush()
        return log

    async def log_blocked(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        action: str,
        failure_code: str,
        request_payload: dict | None = None,
    ) -> AIActionLog:
        return await self.log_action(
            db, session_id, customer_id,
            action=action, status=AI_ACTION_BLOCKED,
            failure_code=failure_code,
            request_payload=request_payload,
        )

    async def log_failed(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        action: str,
        failure_code: str,
        failure_message: str | None = None,
        request_payload: dict | None = None,
    ) -> AIActionLog:
        return await self.log_action(
            db, session_id, customer_id,
            action=action, status=AI_ACTION_FAILED,
            failure_code=failure_code,
            failure_message=failure_message,
            request_payload=request_payload,
        )

    async def list_failed_actions(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        session_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Return blocked or failed action logs for admin monitoring."""
        filters = [
            AIActionLog.status.in_([AI_ACTION_BLOCKED, AI_ACTION_FAILED])
        ]
        if session_id:
            filters.append(AIActionLog.session_id == session_id)
        if customer_id:
            filters.append(AIActionLog.customer_id == customer_id)

        result = await db.execute(
            select(AIActionLog)
            .where(and_(*filters))
            .order_by(desc(AIActionLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        return [r.to_dict() for r in result.scalars().all()]

    async def list_action_logs(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        session_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = []
        if session_id:
            filters.append(AIActionLog.session_id == session_id)
        if status:
            filters.append(AIActionLog.status == status)

        stmt = select(AIActionLog).order_by(desc(AIActionLog.created_at)).limit(limit).offset(offset)
        if filters:
            stmt = stmt.where(and_(*filters))

        result = await db.execute(stmt)
        return [r.to_dict() for r in result.scalars().all()]

    async def get_metrics(self, db: AsyncSession) -> dict[str, Any]:
        """Aggregate AI action metrics for admin dashboard."""
        from sqlalchemy import func, text
        result = await db.execute(
            text("""
                SELECT
                  COUNT(*) FILTER (WHERE status='executed')  AS executed_count,
                  COUNT(*) FILTER (WHERE status='blocked')   AS blocked_count,
                  COUNT(*) FILTER (WHERE status='failed')    AS failed_count,
                  COUNT(*) FILTER (WHERE status='validated') AS validated_count,
                  COUNT(DISTINCT session_id)                 AS unique_sessions,
                  COUNT(DISTINCT customer_id)                AS unique_customers,
                  COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') AS last_hour_count
                FROM ai_action_logs
            """)
        )
        row = result.mappings().first() or {}
        return {k: (int(v) if v is not None else 0) for k, v in row.items()}
