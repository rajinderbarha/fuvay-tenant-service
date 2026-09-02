"""Compliance Enterprise Service — DPDP Act 2023 full governance.

Extends the base ComplianceService with enterprise-grade request management:
  - Unified ComplianceRequest table (erasure / export / consent withdrawal / correction / etc.)
  - Data inventory scan with per-module item records
  - Approve / reject / process workflow with audit trail
  - SLA computation and risk flagging
  - Consent registry browsing + revocation
  - Retention policy management
  - Export generation and tracking
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import text

from app.engines.compliance.constants import ERASURE_EXEMPTIONS, ERASURE_SLA_HOURS
from app.engines.compliance.models import (
    ComplianceAuditLog,
    ComplianceExport,
    ComplianceRequest,
    ComplianceRequestItem,
    ConsentRecord,
    DataRetentionPolicy,
    DPDPPolicyVersion,
    DPDPSchedulerRun,
)
from app.engines.compliance.service import ComplianceService
from app.exceptions import NotFoundException, ServiceOSException

logger = structlog.get_logger("compliance.enterprise")
utcnow = lambda: datetime.now(timezone.utc)

# ── Request / SLA constants ────────────────────────────────────────────────
REQUEST_SLA_HOURS = 72

VALID_SUBJECT_TYPES = {
    "customer", "provider_owner", "tenant_staff", "platform_admin", "guest_user",
    # Slice 2F-20: provider_router.create_my_request has always constructed
    # subject_type as "tenant_business" or "tenant_owner" (see
    # app/engines/compliance/provider_router.py's create_my_request), but
    # neither value was ever a member of this set -- every tenant-created
    # compliance request has therefore always failed this validation and
    # 500'd. Added to make the route this slice hardens actually functional;
    # not a schema/behavior redesign, just correcting a stale allow-list to
    # match the vocabulary the router has used all along.
    "tenant_business", "tenant_owner",
}
VALID_REQUEST_TYPES = {
    "right_to_erasure", "data_export", "consent_withdrawal", "consent_update",
    "data_correction", "processing_objection", "grievance",
    # Slice 2F-20: same defect as VALID_SUBJECT_TYPES above --
    # provider_router.TENANT_ALLOWED_REQUEST_TYPES has always included these
    # six values, none of which were ever valid here.
    "business_data_export", "business_profile_erasure",
    "owner_data_export", "owner_data_erasure",
    "staff_data_export", "staff_data_erasure",
}
VALID_STATUSES = {
    "draft", "submitted", "identity_verification_pending", "under_review",
    "approved", "partially_approved", "rejected", "processing", "completed",
    "failed", "cancelled", "sla_breached",
}
VALID_SLA_STATUSES = {"on_track", "at_risk", "breached", "completed", "not_applicable"}
VALID_VERIFICATION_STATUSES = {"not_required", "pending", "verified", "failed", "expired"}

# Modules scanned during data inventory
DATA_MODULES = [
    {"module": "Customer Profile",    "record_type": "users",               "action": "anonymize"},
    {"module": "Provider Profile",    "record_type": "tenants",             "action": "anonymize"},
    {"module": "Staff Profile",       "record_type": "tenant_staff",        "action": "anonymize"},
    {"module": "Addresses",           "record_type": "addresses",           "action": "delete"},
    {"module": "Bookings",            "record_type": "bookings",            "action": "anonymize"},
    {"module": "Jobs",                "record_type": "jobs",                "action": "anonymize"},
    {"module": "Reviews",             "record_type": "customer_reviews",    "action": "anonymize"},
    {"module": "Complaints",          "record_type": "customer_complaints",  "action": "anonymize"},
    {"module": "Chat Messages",       "record_type": "messages",            "action": "delete"},
    {"module": "Media Files",         "record_type": "media_assets",        "action": "delete"},
    {"module": "Documents",           "record_type": "documents",           "action": "manual_review"},
    {"module": "Wallet Ledger",       "record_type": "wallet_ledger",       "action": "retain",
     "exemption": "Financial record — GST Act 7-year retention"},
    {"module": "Payments",            "record_type": "payment_records",     "action": "retain",
     "exemption": "GST Act — 7 year retention required"},
    {"module": "Invoices",            "record_type": "invoice_records",     "action": "retain",
     "exemption": "GST Act — 7 year retention required"},
    {"module": "Commission Records",  "record_type": "commission_records",  "action": "retain",
     "exemption": "GST Act — 7 year retention required"},
    {"module": "Audit Logs",          "record_type": "platform_audit_logs", "action": "retain",
     "exemption": "Security audit — 2 year retention required"},
    {"module": "Notifications",       "record_type": "notification_records","action": "delete"},
    {"module": "Consent Records",     "record_type": "consent_records",     "action": "retain",
     "exemption": "Legal compliance record — retain per DPDP Act 2023"},
]

# Only modules with a proven, subject-scoped query belong here. Every other
# module is disclosed as unwired instead of returning an ambiguous fake zero.
CUSTOMER_DISCOVERY_QUERIES = {
    "Customer Profile": "SELECT count(*) FROM users WHERE id = :subject_id",
    "Reviews": "SELECT count(*) FROM customer_reviews WHERE customer_id = :subject_id",
    "Complaints": "SELECT count(*) FROM customer_complaints WHERE customer_id = :subject_id",
    "Consent Records": "SELECT count(*) FROM consent_records WHERE user_id = :subject_id",
}


class ComplianceEnterpriseService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None,
                 actor_ip: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_ip = actor_ip
        self._base = ComplianceService(db=db, request_id=request_id,
                                       actor_id=actor_id, actor_role=actor_role,
                                       actor_ip=actor_ip)

    # ── Audit helper ──────────────────────────────────────────────────────────
    async def _audit(self, user_id: uuid.UUID | None, action: str,
                     reference_id: str | None = None, meta: dict | None = None):
        self.db.add(ComplianceAuditLog(
            user_id=user_id, tenant_id=None, action=action,
            purpose=action.replace(".", " "), legal_basis="dpdp_act_2023",
            actor_id=self.actor_id, actor_role=self.actor_role,
            actor_ip=self.actor_ip, reference_id=reference_id, meta=meta or {}))

    # ── Request number generator ──────────────────────────────────────────────
    async def _next_request_number(self) -> str:
        year = utcnow().year
        r = await self.db.execute(
            select(func.count(ComplianceRequest.id)).where(
                func.extract("year", ComplianceRequest.created_at) == year))
        count = (r.scalar_one_or_none() or 0) + 1
        return f"COMP-{year}-{count:06d}"

    # ─────────────────────────────────────────────────────────────────────────
    # ENTERPRISE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────

    async def get_enterprise_summary(self) -> dict:
        now = utcnow()

        async def _count(where_clause):
            r = await self.db.execute(
                select(func.count(ComplianceRequest.id)).where(where_clause))
            return r.scalar_one_or_none() or 0

        pending_erasure  = await _count(
            (ComplianceRequest.request_type == "right_to_erasure") &
            (ComplianceRequest.status.in_(["submitted", "under_review", "processing"])))
        pending_export   = await _count(
            (ComplianceRequest.request_type == "data_export") &
            (ComplianceRequest.status.in_(["submitted", "under_review", "processing"])))
        pending_consent  = await _count(
            (ComplianceRequest.request_type == "consent_withdrawal") &
            (ComplianceRequest.status.in_(["submitted", "under_review"])))
        pending_verify   = await _count(
            ComplianceRequest.verification_status == "pending")
        sla_breached     = await _count(
            (ComplianceRequest.sla_status == "breached") &
            (ComplianceRequest.status.notin_(["completed", "rejected", "cancelled"])))
        sla_at_risk      = await _count(
            (ComplianceRequest.sla_status == "at_risk") &
            (ComplianceRequest.status.notin_(["completed", "rejected", "cancelled"])))

        r_month = await self.db.execute(
            select(func.count(ComplianceRequest.id)).where(
                ComplianceRequest.status.in_(["completed", "partially_approved"]),
                ComplianceRequest.completed_at >= now - timedelta(days=30)))
        completed_month = r_month.scalar_one_or_none() or 0

        r_rej = await self.db.execute(
            select(func.count(ComplianceRequest.id)).where(
                ComplianceRequest.status == "rejected"))
        rejected_total = r_rej.scalar_one_or_none() or 0

        r_exempt = await self.db.execute(
            select(func.count(ComplianceRequestItem.id)).where(
                ComplianceRequestItem.planned_action == "retain"))
        exemptions = r_exempt.scalar_one_or_none() or 0

        r_consent = await self.db.execute(select(func.count(ConsentRecord.id)))
        consent_total = r_consent.scalar_one_or_none() or 0

        status = "BREACH_RISK" if sla_breached > 0 else (
            "ATTENTION_REQUIRED" if sla_at_risk > 0 else "COMPLIANT")

        return {
            "pending_erasure": pending_erasure,
            "pending_export": pending_export,
            "pending_consent_withdrawal": pending_consent,
            "pending_verification": pending_verify,
            "sla_breached": sla_breached,
            "sla_at_risk": sla_at_risk,
            "completed_this_month": completed_month,
            "rejected_total": rejected_total,
            "exemptions_applied": exemptions,
            "consent_records": consent_total,
            "compliance_status": status,
            "generated_at": now.isoformat(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # REQUEST MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────

    async def list_requests(self, request_type: str | None = None,
                             status: str | None = None,
                             sla_status: str | None = None,
                             subject_type: str | None = None,
                             subject_id: uuid.UUID | None = None,
                             verification_status: str | None = None,
                             search: str | None = None,
                             page: int = 1, limit: int = 50) -> dict:
        q = select(ComplianceRequest).order_by(ComplianceRequest.created_at.desc())
        if request_type:       q = q.where(ComplianceRequest.request_type == request_type)
        if status:             q = q.where(ComplianceRequest.status == status)
        if sla_status:         q = q.where(ComplianceRequest.sla_status == sla_status)
        if subject_type:       q = q.where(ComplianceRequest.subject_type == subject_type)
        if subject_id:         q = q.where(ComplianceRequest.subject_id == subject_id)
        if verification_status:q = q.where(ComplianceRequest.verification_status == verification_status)
        if search:
            q = q.where(
                ComplianceRequest.request_number.ilike(f"%{search}%") |
                ComplianceRequest.subject_email.ilike(f"%{search}%") |
                ComplianceRequest.subject_name.ilike(f"%{search}%"))

        total_r = await self.db.execute(
            select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one_or_none() or 0

        offset = (page - 1) * limit
        q = q.offset(offset).limit(limit)
        r = await self.db.execute(q)
        items = r.scalars().all()

        return {
            "items": [self._enrich_request(x) for x in items],
            "meta": {"total": total, "page": page, "limit": limit,
                     "total_pages": max(1, (total + limit - 1) // limit),
                     "has_next": (offset + limit) < total},
        }

    def _enrich_request(self, req: ComplianceRequest) -> dict:
        d = req.to_dict()
        # Compute hours until SLA
        if req.due_at and req.status not in ("completed", "rejected", "cancelled"):
            hours = (req.due_at - utcnow()).total_seconds() / 3600
            d["hours_until_sla"] = round(hours, 1)
            d["sla_overdue"] = hours < 0
        else:
            d["hours_until_sla"] = None
            d["sla_overdue"] = False
        return d

    async def get_request(self, request_id: uuid.UUID) -> dict:
        req = await self._load_request(request_id)
        d = self._enrich_request(req)

        # Load items
        r = await self.db.execute(
            select(ComplianceRequestItem).where(
                ComplianceRequestItem.request_id == request_id))
        items = r.scalars().all()
        d["items"] = [x.to_dict() for x in items]

        # Load audit trail
        r2 = await self.db.execute(
            select(ComplianceAuditLog).where(
                ComplianceAuditLog.reference_id == str(request_id)
            ).order_by(ComplianceAuditLog.created_at.asc()))
        logs = r2.scalars().all()
        d["audit_trail"] = [{"action": l.action, "actor_role": l.actor_role,
                              "purpose": l.purpose,
                              "created_at": l.created_at.isoformat()} for l in logs]
        return d

    async def create_request(self, data: dict) -> dict:
        if data.get("subject_type") not in VALID_SUBJECT_TYPES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Invalid subject_type: {data.get('subject_type')}")
        if data.get("request_type") not in VALID_REQUEST_TYPES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Invalid request_type: {data.get('request_type')}")

        req_num = await self._next_request_number()
        now = utcnow()
        due_at = now + timedelta(hours=REQUEST_SLA_HOURS)

        req = ComplianceRequest(
            request_number=req_num,
            subject_type=data["subject_type"],
            subject_id=uuid.UUID(str(data["subject_id"])),
            subject_email=data.get("subject_email"),
            subject_name=data.get("subject_name"),
            request_type=data["request_type"],
            status="submitted",
            sla_status="on_track",
            verification_status=data.get("verification_status", "not_required"),
            submitted_at=now,
            due_at=due_at,
            request_source=data.get("request_source", "admin_created"),
            reason=data.get("reason"),
            admin_notes=data.get("admin_notes"),
            # Slice 2F-20: metadata_json (which carries tenant ownership for
            # tenant-created requests, e.g. metadata_json["tenant_id"]) was
            # previously silently dropped here -- callers had to do a
            # separate, non-atomic post-creation UPDATE to attach it. Setting
            # it directly in the INSERT means a request is NEVER persisted
            # without its tenant-ownership metadata already in place.
            metadata_json=data.get("metadata_json") or {},
        )
        self.db.add(req)
        await self.db.flush()

        await self._audit(req.subject_id, "request.created",
                          reference_id=str(req.id),
                          meta={"request_type": req.request_type, "request_number": req_num})
        logger.info("compliance.request_created", number=req_num)
        return self._enrich_request(req)

    async def verify_identity(self, request_id: uuid.UUID, notes: str | None = None) -> dict:
        req = await self._load_request(request_id)
        req.verification_status = "verified"
        if req.status == "identity_verification_pending":
            req.status = "under_review"
        await self.db.flush()
        await self._audit(req.subject_id, "request.identity_verified",
                          reference_id=str(request_id),
                          meta={"notes": notes or ""})
        return self._enrich_request(req)

    async def scan_data(self, request_id: uuid.UUID) -> dict:
        """Create ComplianceRequestItem rows for each data module."""
        req = await self._load_request(request_id)

        # Remove existing items first
        r = await self.db.execute(
            select(ComplianceRequestItem).where(
                ComplianceRequestItem.request_id == request_id))
        for item in r.scalars().all():
            await self.db.delete(item)
        await self.db.flush()

        discovery_queries = (
            CUSTOMER_DISCOVERY_QUERIES if req.subject_type == "customer" else {}
        )
        counts_by_category: dict[str, int] = {}
        categories_with_data: list[str] = []
        unwired_modules: list[str] = []
        items = []
        for module in DATA_MODULES:
            action = module["action"]
            exemption = module.get("exemption")
            if req.request_type == "data_export":
                action = "export"
                exemption = None
            elif action == "retain" and exemption:
                pass  # keep retain + exemption as-is

            query = discovery_queries.get(module["module"])
            if query:
                count_result = await self.db.execute(
                    text(query), {"subject_id": req.subject_id})
                record_count = int(count_result.scalar_one())
                counts_by_category[module["module"]] = record_count
                if record_count > 0:
                    categories_with_data.append(module["module"])
            else:
                # The column remains non-null, while the API explicitly marks
                # this module as not covered by automated discovery.
                record_count = 0
                unwired_modules.append(module["module"])

            item = ComplianceRequestItem(
                request_id=request_id,
                module_name=module["module"],
                record_type=module["record_type"],
                record_count=record_count,
                planned_action=action,
                exemption_reason=exemption,
                status="exempted" if action == "retain" else "pending",
            )
            self.db.add(item)
            items.append(item)

        if req.status == "submitted":
            req.status = "under_review"
        await self.db.flush()

        await self._audit(req.subject_id, "request.data_scanned",
                          reference_id=str(request_id),
                          meta={
                              "modules_scanned": len(DATA_MODULES),
                              "modules_wired": len(discovery_queries),
                              "categories_with_data": categories_with_data,
                          })
        return {
            "request_id": str(request_id),
            "modules_scanned": len(DATA_MODULES),
            "modules_wired_for_automated_discovery": list(discovery_queries),
            "modules_not_wired_for_automated_discovery": unwired_modules,
            "counts_by_category": counts_by_category,
            "categories_with_data": categories_with_data,
            "items": [i.to_dict() for i in items],
        }

    async def approve_request(self, request_id: uuid.UUID, notes: str | None = None) -> dict:
        req = await self._load_request(request_id)
        if req.status in ("completed", "rejected", "cancelled"):
            raise ServiceOSException("CONFLICT", f"Cannot approve request in status: {req.status}")

        # Check if any items are retained (partial approval)
        r = await self.db.execute(
            select(ComplianceRequestItem).where(
                ComplianceRequestItem.request_id == request_id,
                ComplianceRequestItem.planned_action == "retain"))
        retained = r.scalars().all()

        req.status = "partially_approved" if retained else "approved"
        if notes:
            req.admin_notes = notes
        await self.db.flush()

        await self._audit(req.subject_id,
                          f"request.{'partially_' if retained else ''}approved",
                          reference_id=str(request_id),
                          meta={"notes": notes or "", "retained_count": len(retained)})
        return self._enrich_request(req)

    async def reject_request(self, request_id: uuid.UUID, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "Rejection reason is required.")
        req = await self._load_request(request_id)
        req.status = "rejected"
        req.rejection_reason = reason
        await self.db.flush()
        await self._audit(req.subject_id, "request.rejected",
                          reference_id=str(request_id),
                          meta={"reason": reason})
        return self._enrich_request(req)

    async def apply_exemption(self, request_id: uuid.UUID, item_id: uuid.UUID,
                               exemption_reason: str) -> dict:
        r = await self.db.execute(
            select(ComplianceRequestItem).where(
                ComplianceRequestItem.id == item_id,
                ComplianceRequestItem.request_id == request_id))
        item = r.scalar_one_or_none()
        if not item:
            raise NotFoundException("ComplianceRequestItem", str(item_id))
        item.planned_action = "retain"
        item.exemption_reason = exemption_reason
        item.status = "exempted"
        await self.db.flush()
        await self._audit(None, "request.exemption_applied",
                          reference_id=str(request_id),
                          meta={"item_id": str(item_id), "reason": exemption_reason})
        return item.to_dict()

    async def process_request(self, request_id: uuid.UUID) -> dict:
        """Execute the approved request — calls base service for erasure / export."""
        req = await self._load_request(request_id)
        if req.status not in ("approved", "partially_approved"):
            raise ServiceOSException("CONFLICT",
                f"Request must be approved before processing. Current status: {req.status}")

        if req.request_type in ("right_to_erasure", "data_export"):
            if req.verification_status not in ("verified", "waived_with_reason"):
                raise ServiceOSException("VALIDATION_ERROR",
                    "Identity verification is required before export or erasure can proceed.")
            hold = await self._active_legal_hold_for_subject(req.subject_id)
            if hold and req.request_type == "right_to_erasure":
                raise ServiceOSException("CONFLICT",
                    f"An active legal hold ({hold['hold_code']}) blocks erasure for this subject. "
                    "Release the hold before processing.")

        req.status = "processing"
        await self.db.flush()

        result_meta: dict = {}
        try:
            if req.request_type == "right_to_erasure":
                # Delegate to base service process_deletion via legacy table
                from app.engines.compliance.models import DataDeletionRequest
                legacy_r = await self.db.execute(
                    select(DataDeletionRequest).where(
                        DataDeletionRequest.user_id == req.subject_id,
                        DataDeletionRequest.status == "pending"))
                legacy = legacy_r.scalar_one_or_none()
                if legacy:
                    result = await self._base.process_deletion(legacy.id)
                    result_meta = {"tables_erased": result.get("tables_erased", []),
                                   "tables_exempted": result.get("tables_exempted", [])}
                else:
                    result_meta = {"note": "no_legacy_deletion_request_found"}

            elif req.request_type == "data_export":
                # Generate export
                export = ComplianceExport(
                    request_id=req.id,
                    subject_type=req.subject_type,
                    subject_id=req.subject_id,
                    export_format="json",
                    status="generating",
                    expires_at=utcnow() + timedelta(days=7),
                )
                self.db.add(export)
                await self.db.flush()
                # Mark as ready (actual file generation deferred to background task)
                export.status = "ready"
                export.generated_at = utcnow()
                export.download_url = f"/v1/admin/compliance/exports/{export.id}/download"
                await self.db.flush()
                result_meta = {"export_id": str(export.id)}

            # Mark items as processed
            r = await self.db.execute(
                select(ComplianceRequestItem).where(
                    ComplianceRequestItem.request_id == request_id,
                    ComplianceRequestItem.status == "pending"))
            for item in r.scalars().all():
                item.status = "processed"
                item.actual_action = item.planned_action

            req.status = "completed"
            req.completed_at = utcnow()
            req.sla_status = "completed"
            await self.db.flush()

        except Exception as e:
            req.status = "failed"
            req.admin_notes = (req.admin_notes or "") + f"\n[PROCESS_ERROR] {str(e)}"
            await self.db.flush()
            raise

        await self._audit(req.subject_id, "request.processed",
                          reference_id=str(request_id), meta=result_meta)
        return {**self._enrich_request(req), "process_result": result_meta}

    async def get_request_audit(self, request_id: uuid.UUID) -> dict:
        await self._load_request(request_id)
        r = await self.db.execute(
            select(ComplianceAuditLog).where(
                ComplianceAuditLog.reference_id == str(request_id)
            ).order_by(ComplianceAuditLog.created_at.asc()))
        logs = r.scalars().all()
        return {
            "request_id": str(request_id),
            "audit_trail": [{"log_id": str(l.id), "action": l.action,
                             "actor_role": l.actor_role, "purpose": l.purpose,
                             "created_at": l.created_at.isoformat()} for l in logs],
        }

    async def _load_request(self, request_id: uuid.UUID) -> ComplianceRequest:
        r = await self.db.execute(
            select(ComplianceRequest).where(ComplianceRequest.id == request_id))
        req = r.scalar_one_or_none()
        if not req:
            raise NotFoundException("ComplianceRequest", str(request_id))
        return req

    # ─────────────────────────────────────────────────────────────────────────
    # SLA MONITOR — updates sla_status on open requests
    # ─────────────────────────────────────────────────────────────────────────

    async def refresh_sla_statuses(self) -> dict:
        now = utcnow()
        open_q = select(ComplianceRequest).where(
            ComplianceRequest.status.notin_([
                "completed", "rejected", "cancelled", "failed"]))
        r = await self.db.execute(open_q)
        open_reqs = r.scalars().all()

        breached = at_risk = on_track = 0
        for req in open_reqs:
            if not req.due_at:
                continue
            hours = (req.due_at - now).total_seconds() / 3600
            if hours < 0:
                req.sla_status = "breached"
                req.status = "sla_breached"
                breached += 1
            elif hours < 24:
                req.sla_status = "at_risk"
                at_risk += 1
            else:
                req.sla_status = "on_track"
                on_track += 1
        await self.db.flush()
        return {"breached": breached, "at_risk": at_risk, "on_track": on_track,
                "checked_at": now.isoformat()}

    # ─────────────────────────────────────────────────────────────────────────
    # EXPORTS
    # ─────────────────────────────────────────────────────────────────────────

    async def list_exports(self, status: str | None = None, page: int = 1,
                            limit: int = 50) -> dict:
        q = select(ComplianceExport).order_by(ComplianceExport.created_at.desc())
        if status:
            q = q.where(ComplianceExport.status == status)
        total_r = await self.db.execute(
            select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one_or_none() or 0
        offset = (page - 1) * limit
        r = await self.db.execute(q.offset(offset).limit(limit))
        items = r.scalars().all()
        return {
            "items": [x.to_dict() for x in items],
            "meta": {"total": total, "page": page, "limit": limit,
                     "total_pages": max(1, (total + limit - 1) // limit),
                     "has_next": (offset + limit) < total},
        }

    async def get_export(self, export_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(ComplianceExport).where(ComplianceExport.id == export_id))
        exp = r.scalar_one_or_none()
        if not exp:
            raise NotFoundException("ComplianceExport", str(export_id))
        return exp.to_dict()

    async def expire_export(self, export_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(ComplianceExport).where(ComplianceExport.id == export_id))
        exp = r.scalar_one_or_none()
        if not exp:
            raise NotFoundException("ComplianceExport", str(export_id))
        exp.status = "expired"
        exp.download_url = None
        await self.db.flush()
        await self._audit(exp.subject_id, "export.expired",
                          reference_id=str(export_id))
        return exp.to_dict()

    # ─────────────────────────────────────────────────────────────────────────
    # CONSENT REGISTRY
    # ─────────────────────────────────────────────────────────────────────────

    async def list_consent_records(self, subject_id: uuid.UUID | None = None,
                                    consent_type: str | None = None,
                                    action: str | None = None,
                                    page: int = 1, limit: int = 50) -> dict:
        q = select(ConsentRecord).order_by(ConsentRecord.created_at.desc())
        if subject_id:    q = q.where(ConsentRecord.user_id == subject_id)
        if consent_type:  q = q.where(ConsentRecord.consent_type == consent_type)
        if action:        q = q.where(ConsentRecord.action == action)

        total_r = await self.db.execute(
            select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one_or_none() or 0

        offset = (page - 1) * limit
        r = await self.db.execute(q.offset(offset).limit(limit))
        items = r.scalars().all()
        return {
            "items": [{
                "id": str(c.id), "user_id": str(c.user_id),
                "consent_type": c.consent_type, "action": c.action,
                "policy_version": c.policy_version,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                "source": c.source, "created_at": c.created_at.isoformat(),
            } for c in items],
            "meta": {"total": total, "page": page, "limit": limit,
                     "total_pages": max(1, (total + limit - 1) // limit),
                     "has_next": (offset + limit) < total},
        }

    async def revoke_consent(self, user_id: uuid.UUID, consent_type: str,
                              notes: str | None = None,
                              tenant_id: uuid.UUID | None = None) -> dict:
        # Slice 2F-20: `tenant_id` was previously always hardcoded to None
        # here regardless of caller -- every consent-withdrawal row ever
        # written through this method (provider, customer, or admin router)
        # permanently lost tenant attribution on a legally significant DPDP
        # record. Callers now pass their own authoritative tenant_id
        # (server-derived, never client-supplied) explicitly; it remains
        # None only for callers that genuinely have none (e.g. a customer
        # withdrawing their own consent, or an admin acting platform-wide).
        result = await self._base.withdraw_consent(user_id, tenant_id, consent_type, "1.0")
        await self._audit(user_id, "consent.admin_revoked",
                          meta={"consent_type": consent_type, "notes": notes or ""})
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # RETENTION POLICIES
    # ─────────────────────────────────────────────────────────────────────────

    async def list_retention_policies(self) -> dict:
        return await self._base.get_retention_policies(None)

    async def create_retention_policy(self, data: dict) -> dict:
        return await self._base.set_retention_policy(
            data["table_name"], None, data["retention_days"], data.get("legal_basis"))

    async def update_retention_policy(self, table_name: str, data: dict) -> dict:
        return await self._base.set_retention_policy(
            table_name, None, data["retention_days"], data.get("legal_basis"))

    # ─────────────────────────────────────────────────────────────────────────
    # COMPLIANCE AUDIT LOG
    # ─────────────────────────────────────────────────────────────────────────

    async def list_audit_logs(self, user_id: uuid.UUID | None = None,
                               action: str | None = None,
                               page: int = 1, limit: int = 100) -> dict:
        q = select(ComplianceAuditLog).order_by(ComplianceAuditLog.created_at.desc())
        if user_id: q = q.where(ComplianceAuditLog.user_id == user_id)
        if action:  q = q.where(ComplianceAuditLog.action == action)

        total_r = await self.db.execute(
            select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one_or_none() or 0

        offset = (page - 1) * limit
        r = await self.db.execute(q.offset(offset).limit(limit))
        items = r.scalars().all()
        return {
            "items": [{
                "log_id": str(l.id), "action": l.action,
                "user_id": str(l.user_id) if l.user_id else None,
                "actor_role": l.actor_role, "purpose": l.purpose,
                "legal_basis": l.legal_basis,
                "reference_id": l.reference_id,
                "created_at": l.created_at.isoformat(),
            } for l in items],
            "meta": {"total": total, "page": page, "limit": limit,
                     "total_pages": max(1, (total + limit - 1) // limit),
                     "has_next": (offset + limit) < total},
        }

    # ─────────────────────────────────────────────────────────────────────────
    # HEALTH SCORE
    # ─────────────────────────────────────────────────────────────────────────

    async def list_dpdp_policy_versions(self) -> dict:
        """Return published DPDP policy metadata newest-first.

        The health calculation already resolves this table, so exposing the
        same source lets the admin command center explain which policy and SLA
        rules produced the displayed compliance state.
        """
        result = await self.db.execute(
            select(DPDPPolicyVersion)
            .order_by(
                DPDPPolicyVersion.is_active.desc(),
                DPDPPolicyVersion.effective_date.desc(),
                DPDPPolicyVersion.created_at.desc(),
            )
        )
        items = result.scalars().all()
        return {
            "items": [
                {
                    "id": str(policy.id),
                    "policy_name": policy.policy_name,
                    "policy_version": policy.policy_version,
                    "publication_date": policy.publication_date.isoformat(),
                    "effective_date": policy.effective_date.isoformat(),
                    "enforcement_phase": policy.enforcement_phase,
                    "applicable_request_types": policy.applicable_request_types or [],
                    "sla_policy": policy.sla_policy or {},
                    "retention_policy_version": policy.retention_policy_version,
                    "evidence_requirements": policy.evidence_requirements or {},
                    "last_policy_review": (
                        policy.last_policy_review.isoformat()
                        if policy.last_policy_review else None
                    ),
                    "approved_by": policy.approved_by,
                    "superseded_version": policy.superseded_version,
                    "is_active": policy.is_active,
                    "source_reference": policy.source_reference,
                }
                for policy in items
            ],
            "total": len(items),
        }

    async def get_dpdp_scheduler_status(self) -> dict:
        """Return health derived from the latest persisted evaluator run."""
        result = await self.db.execute(
            select(DPDPSchedulerRun)
            .where(DPDPSchedulerRun.job_name == "dpdp_sla_evaluator")
            .order_by(DPDPSchedulerRun.started_at.desc())
            .limit(1)
        )
        run = result.scalar_one_or_none()
        if run is None:
            return {
                "status": "never_run",
                "job_name": "dpdp_sla_evaluator",
                "last_run_at": None,
                "last_run_trigger": None,
            }

        health = "healthy" if run.status == "completed" else "failed"
        return {
            "status": health,
            "job_name": run.job_name,
            "scheduler_run_id": str(run.id),
            "last_run_status": run.status,
            "last_run_trigger": run.trigger,
            "last_run_at": run.started_at.isoformat(),
            "last_completed_at": (
                run.completed_at.isoformat() if run.completed_at else None
            ),
            "requests_evaluated": run.requests_evaluated,
            "due_soon_generated": run.due_soon_generated,
            "breaches_generated": run.breaches_generated,
            "error_message": run.error_message,
        }

    async def get_health(self) -> dict:
        summary = await self.get_enterprise_summary()
        r = await self.db.execute(
            select(func.count(ComplianceRequest.id)).where(
                ComplianceRequest.verification_status == "failed"))
        failed_verify = r.scalar_one_or_none() or 0

        now = utcnow()
        policy_result = await self.db.execute(
            select(DPDPPolicyVersion)
            .where(DPDPPolicyVersion.is_active.is_(True))
            .order_by(DPDPPolicyVersion.effective_date.desc())
            .limit(1)
        )
        active_policy = policy_result.scalar_one_or_none()

        retention_result = await self.db.execute(
            select(
                func.count(DataRetentionPolicy.id),
                func.count(DataRetentionPolicy.id).filter(
                    DataRetentionPolicy.legal_basis.is_(None),
                    DataRetentionPolicy.is_exempt.is_(False),
                ),
            )
        )
        retention_total, retention_without_basis = retention_result.one()
        retention_total = int(retention_total or 0)
        retention_without_basis = int(retention_without_basis or 0)

        consent_result = await self.db.execute(
            select(
                func.count(ConsentRecord.id),
                func.count(ConsentRecord.id).filter(ConsentRecord.policy_version == ""),
            )
        )
        consent_total, unversioned_consents = consent_result.one()
        consent_total = int(consent_total or 0)
        unversioned_consents = int(unversioned_consents or 0)

        audit_result = await self.db.execute(select(func.count(ComplianceAuditLog.id)))
        audit_count = int(audit_result.scalar_one_or_none() or 0)

        def control(key: str, label: str, evaluated: bool, passed: bool,
                    evidence: str, action: str) -> dict:
            status = (
                "passed" if evaluated and passed else
                "failed" if evaluated else
                "without_evidence"
            )
            return {
                "key": key,
                "label": label,
                "status": status,
                "evaluated": evaluated,
                "passed": evaluated and passed,
                "evidence": evidence,
                "recommended_action": action if status != "passed" else None,
            }

        policy_is_effective = bool(
            active_policy and active_policy.effective_date <= now
        )
        controls = [
            control(
                "active_policy", "Active DPDP policy", bool(active_policy),
                policy_is_effective,
                (f"Policy {active_policy.policy_version} effective "
                 f"{active_policy.effective_date.isoformat()}" if active_policy else
                 "No active policy version is published."),
                "Publish an approved DPDP policy version with an effective date.",
            ),
            control(
                "policy_evidence", "Policy evidence requirements", bool(active_policy),
                bool(active_policy and active_policy.evidence_requirements),
                ("Evidence requirements are configured."
                 if active_policy and active_policy.evidence_requirements else
                 "The active policy has no evidence requirements."),
                "Define the evidence required to prove every policy control.",
            ),
            control(
                "retention_governance", "Retention governance", retention_total > 0,
                retention_total > 0 and retention_without_basis == 0,
                (f"{retention_total} retention policies; "
                 f"{retention_without_basis} without a legal basis."
                 if retention_total else "No retention policies are configured."),
                "Configure retention policies and a legal basis or exemption for every governed table.",
            ),
            control(
                "request_sla", "Data-rights request SLA", True,
                summary["sla_breached"] == 0,
                f"{summary['sla_breached']} breached and {summary['sla_at_risk']} at-risk request(s).",
                "Resolve breached requests and triage requests at risk of breaching SLA.",
            ),
            control(
                "identity_verification", "Request identity verification", True,
                failed_verify == 0,
                f"{failed_verify} failed and {summary['pending_verification']} pending verification(s).",
                "Resolve failed identity checks before processing subject data.",
            ),
            control(
                "consent_versioning", "Versioned consent evidence", consent_total > 0,
                consent_total > 0 and unversioned_consents == 0,
                (f"{consent_total} consent event(s); "
                 f"{unversioned_consents} without a policy version."
                 if consent_total else "No consent evidence has been captured."),
                "Capture immutable, policy-versioned consent evidence.",
            ),
            control(
                "audit_evidence", "Compliance audit evidence", audit_count > 0,
                audit_count > 0,
                (f"{audit_count} append-only compliance audit event(s)."
                 if audit_count else "No compliance audit evidence has been recorded."),
                "Verify compliance actions write to the append-only audit ledger.",
            ),
        ]

        controls_total = len(controls)
        controls_evaluated = sum(1 for item in controls if item["evaluated"])
        controls_failed = sum(1 for item in controls if item["status"] == "failed")
        controls_without_evidence = sum(
            1 for item in controls if item["status"] == "without_evidence"
        )
        controls_passed = sum(1 for item in controls if item["status"] == "passed")
        score = round((controls_passed / controls_total) * 100)
        is_compliant = (
            controls_evaluated == controls_total
            and controls_failed == 0
            and controls_without_evidence == 0
        )
        band = (
            "compliant" if is_compliant else
            "attention_needed" if score >= 75 else
            "at_risk" if score >= 50 else
            "non_compliant"
        )
        state = (
            "verified_compliant" if is_compliant else
            "evidence_incomplete" if controls_without_evidence else
            "controls_failed"
        )
        top_risks = [
            item["evidence"] for item in controls if item["status"] != "passed"
        ]
        recommended_actions = [
            item["recommended_action"] for item in controls
            if item["recommended_action"]
        ]

        return {
            "score": score,
            "band": band,
            "status": band.replace("_", " ").title(),
            "state": state,
            "is_compliant": is_compliant,
            "controls_total": controls_total,
            "controls_evaluated": controls_evaluated,
            "controls_passed": controls_passed,
            "controls_failed": controls_failed,
            "controls_without_evidence": controls_without_evidence,
            "controls": controls,
            "calculation_method": "fixed_control_checklist_v1",
            "policy_version": active_policy.policy_version if active_policy else None,
            "top_risks": top_risks,
            "recommended_actions": (
                recommended_actions if recommended_actions else
                ["No action required - every fixed control has current evidence."]
            ),
            "last_sla_job_run": None,
            "last_retention_job_run": None,
            "generated_at": now.isoformat(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # ACTION QUEUE
    # ─────────────────────────────────────────────────────────────────────────

    async def get_action_queue(self, limit: int = 50) -> dict:
        q = select(ComplianceRequest).where(
            ComplianceRequest.status.notin_(["completed", "rejected", "cancelled"])
        ).order_by(ComplianceRequest.due_at.asc().nulls_last()).limit(limit)
        r = await self.db.execute(q)
        reqs = r.scalars().all()

        items = []
        for req in reqs:
            d = self._enrich_request(req)
            priority = ("critical" if d.get("sla_overdue") else
                        "high" if (d.get("hours_until_sla") is not None and d["hours_until_sla"] < 24) else
                        "medium")
            next_action = (
                "Verify Identity" if req.verification_status == "pending" else
                "Review Data Map" if req.status == "under_review" else
                "Approve Export" if req.request_type == "data_export" and req.status == "under_review" else
                "Approve Erasure" if req.request_type == "right_to_erasure" and req.status == "under_review" else
                "Send Response" if req.status in ("approved", "partially_approved") else
                "Close Request")
            items.append({
                **d, "priority": priority, "next_action": next_action,
            })
        return {"items": items, "count": len(items)}

    async def assign_action(self, request_id: uuid.UUID, assigned_to_user_id: uuid.UUID) -> dict:
        req = await self._load_request(request_id)
        req.assigned_to_admin_id = assigned_to_user_id
        await self.db.flush()
        await self._audit(req.subject_id, "request.assigned", reference_id=str(request_id),
                          meta={"assigned_to_user_id": str(assigned_to_user_id)})
        return self._enrich_request(req)

    async def escalate_action(self, request_id: uuid.UUID, reason: str) -> dict:
        req = await self._load_request(request_id)
        await self.db.execute(text("""
            INSERT INTO dpdp_action_states (request_id, priority, escalated, escalated_reason)
            VALUES (:rid, 'critical', true, :reason)
            ON CONFLICT (request_id) DO UPDATE SET
                escalated = true, escalated_reason = :reason, updated_at = now()
        """), {"rid": str(request_id), "reason": reason})
        await self._audit(req.subject_id, "request.escalated", reference_id=str(request_id),
                          meta={"reason": reason})
        return self._enrich_request(req)

    # ─────────────────────────────────────────────────────────────────────────
    # AFFECTED DATA MAP
    # ─────────────────────────────────────────────────────────────────────────

    async def get_data_map(self, request_id: uuid.UUID) -> dict:
        req = await self._load_request(request_id)
        r = await self.db.execute(
            select(ComplianceRequestItem).where(
                ComplianceRequestItem.request_id == request_id))
        items = r.scalars().all()
        if not items:
            scan_result = await self.scan_data(request_id)
            items_data = scan_result["items"]
        else:
            items_data = [i.to_dict() for i in items]

        hold = await self._active_legal_hold_for_subject(req.subject_id)
        for item in items_data:
            item["legal_hold"] = hold["hold_code"] if hold else None
        return {"request_id": str(request_id), "data_map": items_data,
                "active_legal_hold": hold}

    async def _active_legal_hold_for_subject(self, subject_id: uuid.UUID) -> dict | None:
        r = await self.db.execute(text("""
            SELECT id, hold_code, reason, expires_at FROM dpdp_legal_holds
            WHERE entity_id = :eid AND status = 'active'
            ORDER BY applied_at DESC LIMIT 1
        """), {"eid": str(subject_id)})
        row = r.mappings().first()
        return dict(row) if row else None

    # ─────────────────────────────────────────────────────────────────────────
    # LEGAL HOLDS / EXEMPTIONS
    # ─────────────────────────────────────────────────────────────────────────

    async def list_legal_holds(self, status: str | None = None, page: int = 1,
                                limit: int = 50) -> dict:
        where = "WHERE status = :status" if status else ""
        params: dict = {"status": status} if status else {}
        total_r = await self.db.execute(
            text(f"SELECT count(*) FROM dpdp_legal_holds {where}"), params)
        total = total_r.scalar_one_or_none() or 0
        offset = (page - 1) * limit
        r = await self.db.execute(text(f"""
            SELECT * FROM dpdp_legal_holds {where}
            ORDER BY applied_at DESC OFFSET :offset LIMIT :limit
        """), {**params, "offset": offset, "limit": limit})
        rows = [dict(row) for row in r.mappings().all()]
        for row in rows:
            for k in ("id", "entity_id", "applied_by_user_id", "released_by_user_id"):
                if row.get(k) is not None:
                    row[k] = str(row[k])
            for k in ("applied_at", "expires_at", "released_at", "created_at", "updated_at"):
                if row.get(k) is not None:
                    row[k] = row[k].isoformat()
        return {"items": rows, "meta": {"total": total, "page": page, "limit": limit,
                "total_pages": max(1, (total + limit - 1) // limit)}}

    async def apply_legal_hold(self, data: dict) -> dict:
        if not data.get("reason"):
            raise ServiceOSException("VALIDATION_ERROR", "Legal hold reason is required.")
        year = utcnow().year
        r = await self.db.execute(text(
            "SELECT count(*) FROM dpdp_legal_holds WHERE extract(year from applied_at) = :y"),
            {"y": year})
        seq = (r.scalar_one_or_none() or 0) + 1
        hold_code = f"HOLD-{year}-{seq:05d}"
        r2 = await self.db.execute(text("""
            INSERT INTO dpdp_legal_holds
                (hold_code, entity_type, entity_id, reason, evidence_json,
                 applied_by_user_id, expires_at)
            VALUES (:code, :etype, :eid, :reason, :evidence, :actor, :expires)
            RETURNING id
        """), {
            "code": hold_code, "etype": data["entity_type"], "eid": str(data["entity_id"]),
            "reason": data["reason"], "evidence": __import__("json").dumps(data.get("evidence", {})),
            "actor": str(self.actor_id) if self.actor_id else None,
            "expires": data.get("expires_at"),
        })
        hold_id = r2.scalar_one()
        await self._audit(None, "legal_hold.applied", reference_id=str(hold_id),
                          meta={"hold_code": hold_code, "entity_id": str(data["entity_id"])})
        return {"id": str(hold_id), "hold_code": hold_code, "status": "active"}

    async def release_legal_hold(self, hold_id: uuid.UUID, reason: str) -> dict:
        if not reason:
            raise ServiceOSException("VALIDATION_ERROR", "Release reason is required.")
        r = await self.db.execute(text("""
            UPDATE dpdp_legal_holds
            SET status = 'released', released_by_user_id = :actor,
                released_at = now(), release_reason = :reason, updated_at = now()
            WHERE id = :id AND status = 'active'
            RETURNING hold_code
        """), {"id": str(hold_id), "actor": str(self.actor_id) if self.actor_id else None,
               "reason": reason})
        row = r.scalar_one_or_none()
        if not row:
            raise NotFoundException("LegalHold (active)", str(hold_id))
        await self._audit(None, "legal_hold.released", reference_id=str(hold_id),
                          meta={"reason": reason})
        return {"id": str(hold_id), "hold_code": row, "status": "released"}

    # ─────────────────────────────────────────────────────────────────────────
    # EVIDENCE PACK
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_evidence_pack(self, request_id: uuid.UUID) -> dict:
        req_detail = await self.get_request(request_id)
        data_map = await self.get_data_map(request_id)
        exports_r = await self.db.execute(
            select(ComplianceExport).where(ComplianceExport.request_id == request_id))
        exports = [x.to_dict() for x in exports_r.scalars().all()]

        pack = {
            "request_summary": req_detail,
            "data_map": data_map["data_map"],
            "active_legal_hold": data_map["active_legal_hold"],
            "exports": exports,
            "audit_trail": req_detail.get("audit_trail", []),
            "generated_at": utcnow().isoformat(),
        }
        import json as _json
        r = await self.db.execute(text("""
            INSERT INTO dpdp_evidence_packs (request_id, pack_json, generated_by_user_id)
            VALUES (:rid, CAST(:pack AS JSONB), :actor)
            RETURNING id
        """), {"rid": str(request_id), "pack": _json.dumps(pack, default=str),
               "actor": str(self.actor_id) if self.actor_id else None})
        pack_id = r.scalar_one()
        await self._audit(req_detail.get("subject_id"), "evidence_pack.generated",
                          reference_id=str(request_id), meta={"pack_id": str(pack_id)})
        return {"pack_id": str(pack_id), "request_id": str(request_id),
                "generated_at": pack["generated_at"]}

    async def list_evidence_packs(self, request_id: uuid.UUID | None = None,
                                   page: int = 1, limit: int = 50) -> dict:
        where = "WHERE request_id = :rid" if request_id else ""
        params: dict = {"rid": str(request_id)} if request_id else {}
        total_r = await self.db.execute(
            text(f"SELECT count(*) FROM dpdp_evidence_packs {where}"), params)
        total = total_r.scalar_one_or_none() or 0
        offset = (page - 1) * limit
        r = await self.db.execute(text(f"""
            SELECT id, request_id, generated_by_user_id, created_at FROM dpdp_evidence_packs
            {where} ORDER BY created_at DESC OFFSET :offset LIMIT :limit
        """), {**params, "offset": offset, "limit": limit})
        rows = [{
            "id": str(row["id"]), "request_id": str(row["request_id"]),
            "generated_by_user_id": str(row["generated_by_user_id"]) if row["generated_by_user_id"] else None,
            "created_at": row["created_at"].isoformat(),
        } for row in r.mappings().all()]
        return {"items": rows, "meta": {"total": total, "page": page, "limit": limit}}
