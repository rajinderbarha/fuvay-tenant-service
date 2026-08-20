"""Tenant-scoped, read-only tools for the assistant.

Isolation contract:
  * `tenant_id` is set once from the caller's JWT and is never a tool argument.
    The model cannot express "show me another business" because no tool takes
    a tenant id.
  * Every tool is read-only. Nothing here creates, updates or deletes; the one
    write path in the engine is raising a support ticket, which lives in
    service.py behind an explicit user action.
  * Results pass through `_scrub()` before they reach the model.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.tenant_assistant import constants as C
from app.engines.tenant_assistant import retrieval

logger = structlog.get_logger("tenant_assistant.tools")


class TenantAssistantTools:
    """Executes one tool call for exactly one tenant."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID,
                 allowed: list[str] | None = None,
                 product_areas: list[str] | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.allowed = set(allowed or C.TOOL_NAMES)
        self.product_areas = product_areas
        self.calls: list[str] = []
        self.citations: list[dict] = []

    # ── dispatch ─────────────────────────────────────────────────────────────
    async def execute(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        if name not in self.allowed:
            # Hallucinated or disabled tool — refuse rather than improvise.
            return json.dumps({"error": "tool_not_available", "tool": name})
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return json.dumps({"error": "unknown_tool", "tool": name})

        start = time.monotonic()
        try:
            result = await handler(**(arguments or {}))
            self.calls.append(name)
            return json.dumps(self._scrub(result), default=str)
        except Exception as exc:                                  # noqa: BLE001
            logger.warning("tenant_assistant.tool_failed", tool=name, error=str(exc))
            return json.dumps({"error": "tool_failed", "tool": name})
        finally:
            logger.info("tenant_assistant.tool", tool=name,
                        ms=int((time.monotonic() - start) * 1000))

    def _scrub(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self._scrub(v) for k, v in data.items()
                    if k not in C.FORBIDDEN_OUTPUT_KEYS}
        if isinstance(data, list):
            return [self._scrub(v) for v in data]
        return data

    # ── knowledge ────────────────────────────────────────────────────────────
    async def _tool_search_knowledge(self, query: str) -> dict:
        found = await retrieval.search(self.db, query, top_k=4,
                                       product_areas=self.product_areas)
        for p in found.passages:
            cite = p.as_citation()
            if cite not in self.citations:
                self.citations.append(cite)
        return {
            "found": len(found.passages),
            "articles": [
                {"slug": p.slug, "title": p.title,
                 "summary": p.summary, "content": p.body}
                for p in found.passages
            ],
        }

    # ── this tenant's own data ───────────────────────────────────────────────
    async def _tool_get_business_profile(self) -> dict:
        r = (await self.db.execute(text("""
            SELECT business_name, status, plan_type, health_score, health_band,
                   vertical, activated_at, created_at
            FROM tenants WHERE id = :tid
        """), {"tid": str(self.tenant_id)})).mappings().first()
        if not r:
            return {"error": "profile_unavailable"}
        return {
            "business_name": r["business_name"],
            "account_status": r["status"],
            "plan": r["plan_type"],
            "health_score": float(r["health_score"]) if r["health_score"] is not None else None,
            "health_band": r["health_band"],
            "vertical": r["vertical"],
            "activated_on": r["activated_at"].date().isoformat() if r["activated_at"] else None,
            "member_since": r["created_at"].date().isoformat() if r["created_at"] else None,
        }

    async def _tool_get_job_summary(self) -> dict:
        rows = (await self.db.execute(text("""
            SELECT status, count(*) AS n
            FROM service_jobs WHERE tenant_id = :tid
            GROUP BY status ORDER BY n DESC
        """), {"tid": str(self.tenant_id)})).mappings().all()
        upcoming = (await self.db.execute(text("""
            SELECT count(*) AS n FROM service_jobs
            WHERE tenant_id = :tid AND scheduled_date >= CURRENT_DATE
        """), {"tid": str(self.tenant_id)})).scalar() or 0
        by_status = {r["status"]: int(r["n"]) for r in rows}
        return {
            "total_jobs": sum(by_status.values()),
            "by_status": by_status,
            "scheduled_from_today": int(upcoming),
        }

    async def _tool_get_team_summary(self) -> dict:
        rows = (await self.db.execute(text("""
            SELECT role, count(*) FILTER (WHERE is_active) AS active,
                   count(*) AS total
            FROM users WHERE tenant_id = :tid
            GROUP BY role ORDER BY role
        """), {"tid": str(self.tenant_id)})).mappings().all()
        return {
            "members": [{"role": r["role"], "active": int(r["active"]),
                         "total": int(r["total"])} for r in rows],
            "total_active": sum(int(r["active"]) for r in rows),
        }

    async def _tool_get_readiness_snapshot(self) -> dict:
        """Composed from signals that genuinely exist, so it never claims a
        step is done when nothing was checked."""
        profile = await self._tool_get_business_profile()
        team    = await self._tool_get_team_summary()
        jobs    = await self._tool_get_job_summary()

        docs = (await self.db.execute(text("""
            SELECT count(*) FILTER (WHERE status = 'verified') AS verified,
                   count(*) AS total
            FROM tenant_documents
            WHERE tenant_id = :tid AND status <> 'superseded'
        """), {"tid": str(self.tenant_id)})).mappings().first()

        blockers: list[str] = []
        if profile.get("account_status") != "active":
            blockers.append(f"Account status is '{profile.get('account_status')}', not active")
        if not profile.get("plan"):
            blockers.append("No plan selected")
        if docs and int(docs["total"] or 0) == 0:
            blockers.append("No documents uploaded for verification")
        elif docs and int(docs["verified"] or 0) == 0:
            blockers.append("No document has been verified yet")
        if team.get("total_active", 0) <= 1:
            blockers.append("No staff or technicians added yet")

        return {
            "account_status": profile.get("account_status"),
            "plan": profile.get("plan"),
            "activated_on": profile.get("activated_on"),
            "documents_verified": int(docs["verified"]) if docs else None,
            "documents_total": int(docs["total"]) if docs else None,
            "active_team_members": team.get("total_active", 0),
            "total_jobs": jobs.get("total_jobs", 0),
            "blockers": blockers,
            "looks_ready": not blockers,
        }

    # ── support surface (already tenant-scoped by the support engine) ────────
    async def _tool_get_open_requests(self) -> dict:
        rows = (await self.db.execute(text("""
            SELECT ticket_number, subject, status, priority, created_at,
                   last_support_reply_at, tenant_unread_count
            FROM support_tickets
            WHERE tenant_id = :tid
              AND status NOT IN ('resolved', 'closed', 'withdrawn')
            ORDER BY created_at DESC LIMIT 5
        """), {"tid": str(self.tenant_id)})).mappings().all()
        return {
            "open_count": len(rows),
            "requests": [{
                "ticket_number": r["ticket_number"], "subject": r["subject"],
                "status": r["status"], "priority": r["priority"],
                "raised_on": r["created_at"].date().isoformat() if r["created_at"] else None,
                "unread_replies": int(r["tenant_unread_count"] or 0),
            } for r in rows],
        }

    async def _tool_get_platform_status(self) -> dict:
        incident = (await self.db.execute(text("""
            SELECT title, severity, started_at FROM support_platform_incidents
            WHERE resolved_at IS NULL ORDER BY started_at DESC LIMIT 1
        """))).mappings().first()
        if incident:
            return {"healthy": False, "incident": incident["title"],
                    "severity": incident["severity"],
                    "since": incident["started_at"].isoformat() if incident["started_at"] else None}
        return {"healthy": True, "incident": None}

    async def _tool_get_announcements(self) -> dict:
        rows = (await self.db.execute(text("""
            SELECT title, body, effective_from FROM support_announcements
            WHERE is_published = true
              AND (expires_at IS NULL OR expires_at > now())
            ORDER BY effective_from DESC NULLS LAST LIMIT 3
        """))).mappings().all()
        return {"announcements": [{
            "title": r["title"], "summary": (r["body"] or "")[:300],
            "published_on": r["effective_from"].date().isoformat() if r["effective_from"] else None,
        } for r in rows]}
