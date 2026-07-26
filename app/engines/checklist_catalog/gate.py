"""Runtime completion-gate check, called from the canonical execution state
machine (app/engines/execution/home_service_service.py) alongside the
existing estimate-approval gate. Complements it -- never replaces it.

Terminal outcomes (closed_estimate_declined, cancelled) must never be
blocked by a completion checklist: callers only invoke assert_gate_satisfied
for forward transitions, never for terminal ones, so this module does not
need its own terminal-state list to stay correct -- but as a second,
independent safeguard it still no-ops if asked to gate a job already in a
terminal-looking state string ending in _declined or _cancelled.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.checklist_catalog import constants as c, service as checklist_service
from app.exceptions import ServiceOSException

_TERMINAL_SUFFIXES = ("_declined", "cancelled")


async def assert_gate_satisfied(db: AsyncSession, job, gate_code: str, context: dict | None = None) -> None:
    status = str(getattr(job, "status", "") or "")
    if status.endswith(_TERMINAL_SUFFIXES):
        return

    mappings = await checklist_service.get_applicable_mappings(db, job, context=context)
    required = [m for m in mappings if m.completion_gate == gate_code and m.usage == c.USAGE_REQUIRED]
    for mapping in required:
        instance = await checklist_service.ensure_instance(db, job, mapping)
        if instance.state in (c.INSTANCE_COMPLETED, c.INSTANCE_WAIVED):
            continue
        raise ServiceOSException(
            c.ERR_REQUIRED_CHECKLIST_INCOMPLETE,
            "A required checklist must be completed before this step can proceed.",
            status_code=409,
            context={"checklist_instance_id": str(instance.id), "mapping_id": str(mapping.id)},
        )


async def get_gate_projection(db: AsyncSession, job, gate_code: str, context: dict | None = None) -> dict:
    """Read-only projection mirroring assert_gate_satisfied, for client
    status displays. Never a second source of truth for enforcement."""
    try:
        await assert_gate_satisfied(db, job, gate_code, context=context)
        return {"satisfied": True, "block_code": None, "instance_id": None}
    except ServiceOSException as exc:
        instance_id = (exc.context or {}).get("checklist_instance_id") if exc.context else None
        return {"satisfied": False, "block_code": exc.error_code, "instance_id": instance_id}
