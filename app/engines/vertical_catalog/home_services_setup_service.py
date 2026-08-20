"""Home Services Setup Overview — readiness aggregator.

Backs the tenant-portal "Workspace Created / Setup Overview" onboarding
page. Every section's status is computed from the same real, live tables
already proven in `provider_portal.router._evaluate_provider_bookability`
(business profile fields, tenant_services, tenant_service_areas,
provider_availability_rules, tenant_billing) plus tenant_documents and
provider_team_members -- never a hardcoded percentage or status.

Vertical lifecycle (WORKSPACE/SETUP/ADMIN_REVIEW/ACTIVATION/GO_LIVE) is
projected from TenantVerticalEnrollment.status, the single canonical
per-vertical lifecycle field (app.engines.vertical_catalog.models).
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.vertical_catalog.service import VerticalCatalogService
from app.engines.vertical_catalog.document_requirements import (
    required_keys as _resolve_required_doc_keys,
    is_business_profile_complete,
)

HOME_SERVICES_VERTICAL_KEY = "home_services"

# Order matters -- this is the fixed "first incomplete required section wins"
# order used both for the checklist display and the next_action projection.
_SECTION_ORDER = [
    "BUSINESS_PROFILE", "DOCUMENTS", "SERVICES_PRICING",
    "COVERAGE_AVAILABILITY", "STAFF_TECHNICIANS", "FINANCE_READINESS",
    "REVIEW_SUBMIT",
]

_NEXT_ACTION_BY_SECTION = {
    "BUSINESS_PROFILE": "EDIT_BUSINESS_PROFILE",
    "DOCUMENTS": "EDIT_DOCUMENTS",
    "SERVICES_PRICING": "EDIT_SERVICES_PRICING",
    "COVERAGE_AVAILABILITY": "EDIT_COVERAGE_AVAILABILITY",
    "STAFF_TECHNICIANS": "EDIT_STAFF",
    "FINANCE_READINESS": "EDIT_FINANCE",
    "REVIEW_SUBMIT": "REVIEW_AND_SUBMIT",
}

_LIFECYCLE_STAGES = ["WORKSPACE", "SETUP", "ADMIN_REVIEW", "ACTIVATION", "GO_LIVE"]


def _project_lifecycle(enrollment_status: str) -> dict:
    if enrollment_status in ("draft_setup", "draft", "changes_requested"):
        current = "SETUP"
    elif enrollment_status in ("submitted", "under_review"):
        current = "ADMIN_REVIEW"
    elif enrollment_status in ("approved", "approved_pending_activation",
                                "activation_requirements_pending", "activating"):
        current = "ACTIVATION"
    elif enrollment_status == "active":
        current = "GO_LIVE"
    else:
        current = "SETUP"  # rejected/suspended still shown against the setup stage

    order = _LIFECYCLE_STAGES.index(current)
    stages = []
    for i, key in enumerate(_LIFECYCLE_STAGES):
        if i < order:
            status = "COMPLETED"
        elif i == order:
            status = "CURRENT"
        else:
            status = "UPCOMING"
        stages.append({"key": key, "status": status})
    return {"current_stage": current, "stages": stages}


async def get_setup_overview(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    tenant_row = (await db.execute(
        text("SELECT id, tenant_name, business_name, business_type, phone, email, "
             "address_line1, district, city, state, zipcode, status, vertical, country, "
             "verification_status, suspension_reason, owner_user_id FROM tenants WHERE id=:tid"),
        {"tid": str(tenant_id)},
    )).fetchone()

    svc = VerticalCatalogService()
    enrollment = await svc.get_or_create_enrollment(db, tenant_id, HOME_SERVICES_VERTICAL_KEY)

    # ── Business Profile ──────────────────────────────────────────────────
    # Mirrors the fields the real Business Profile onboarding page requires
    # (app/engines/profile/service.py's business-profile update surface).
    profile_complete = is_business_profile_complete(tenant_row)

    # ── Documents ─────────────────────────────────────────────────────────
    # Required doc types are resolved the same way the Verification Documents
    # step resolves them (document_requirements.required_keys) -- one
    # manifest, so this completion check can never drift from what the step
    # actually asked the tenant to upload.
    required_doc_types = _resolve_required_doc_keys(
        vertical=tenant_row.vertical if tenant_row else HOME_SERVICES_VERTICAL_KEY,
        business_type=tenant_row.business_type if tenant_row else None,
        country=tenant_row.country if tenant_row else "India",
    )
    doc_rows = (await db.execute(
        text("SELECT doc_type, status FROM tenant_documents WHERE tenant_id=:tid AND is_current=true"),
        {"tid": str(tenant_id)},
    )).fetchall()
    verified_types = {r.doc_type for r in doc_rows if r.status == "verified"}
    uploaded_types = {r.doc_type for r in doc_rows if r.status not in ("removed",)}
    docs_verified = all(t in verified_types for t in required_doc_types)
    docs_uploaded = all(t in uploaded_types for t in required_doc_types)

    # ── Services & Pricing ────────────────────────────────────────────────
    published_count = (await db.execute(
        text("SELECT count(*) FROM tenant_services WHERE tenant_id=:tid "
             "AND setup_status='published' AND is_active=true AND deleted_at IS NULL"),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    # A tenant_service is priced through any of the same fields
    # validate_for_publish (admin_catalog/tenant_service.py) actually
    # accepts: min/max range at the type, brand, or service level, OR the
    # inspection-workflow visit fee for a simple (no type/brand) service --
    # that visit-fee case was missing here, so any published visit-fee-only
    # Home Services offering (a very common Repair/inspection setup) was
    # permanently counted as "unpriced" and blocked Review & Submit.
    priced_count = (await db.execute(
        text("SELECT count(*) FROM tenant_services ts WHERE ts.tenant_id=:tid "
             "AND ts.setup_status='published' AND ts.is_active=true AND ts.deleted_at IS NULL "
             "AND (ts.tenant_min_price IS NOT NULL "
             "     OR ts.tenant_visit_fee IS NOT NULL "
             "     OR EXISTS (SELECT 1 FROM tenant_service_types tst WHERE tst.tenant_service_id=ts.id "
             "                AND tst.tenant_min_price IS NOT NULL) "
             "     OR EXISTS (SELECT 1 FROM tenant_service_brands tsb WHERE tsb.tenant_service_id=ts.id "
             "                AND tsb.tenant_min_price IS NOT NULL) "
             "     OR EXISTS (SELECT 1 FROM master_services ms WHERE ms.id = ts.master_service_id "
             "                AND ms.tenant_override_allowed = false "
             "                AND COALESCE(ms.base_price, ms.min_price) IS NOT NULL))"),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    # Every published service must be priced. Comparing only `> 0` let one
    # valid service hide any number of unpriced published services.
    services_ready = published_count > 0 and priced_count == published_count

    # ── Coverage & Availability ───────────────────────────────────────────
    active_areas = (await db.execute(
        text("SELECT count(*) FROM tenant_service_areas WHERE tenant_id=:tid AND is_active=true"),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    availability_count = (await db.execute(
        text("SELECT count(*) FROM provider_availability_rules WHERE tenant_id=:tid "
             "AND scope_type='provider' AND scope_id IS NULL AND is_active=true"),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    coverage_ready = active_areas > 0 and availability_count > 0

    # ── Staff & Technicians ───────────────────────────────────────────────
    from app.engines.home_service_assignment.team_readiness_service import (
        compute_service_coverage,
        compute_team_summary,
    )
    team_summary = await compute_team_summary(db, tenant_id)
    service_coverage = await compute_service_coverage(db, tenant_id)
    # Kept under the existing response key for API compatibility, but this is
    # now the count of genuinely ready members rather than active name-only rows.
    active_staff = int(team_summary["counts"]["ready"])
    # Required only once at least one service is published (nothing to staff
    # before then); optional_for_now is the honest state for a brand-new
    # workspace, matching the real absence of any assignable work yet.
    staff_required = published_count > 0
    # Zero staff is not "complete". It is optional only until a service is
    # published, then becomes required and incomplete until someone is ready.
    staff_ready = active_staff > 0 and all(
        row["ready_technician_count"] > 0 for row in service_coverage
    )

    # ── Finance Readiness ─────────────────────────────────────────────────
    billing_row = (await db.execute(
        text("SELECT credit_balance, security_deposit_paid, security_deposit_amount "
             "FROM tenant_billing WHERE tenant_id=:tid"),
        {"tid": str(tenant_id)},
    )).fetchone()
    deposit_amount = float(billing_row.security_deposit_amount) if billing_row and billing_row.security_deposit_amount else 0.0
    deposit_paid = bool(billing_row and billing_row.security_deposit_paid)
    # Deposit is only ever collected after admin approval -- its absence here
    # is never a blocker to submitting for review. Completion is instead the
    # tenant's own Finance Readiness step (direct payment methods + invoice
    # details) -- a tenant_billing row is created independently (activation/
    # package flows) and was never something this step's page writes, so
    # gating on it here made the section permanently "not started" no matter
    # what the tenant filled in on the actual Finance Readiness page.
    finance_row = (await db.execute(
        text("SELECT accepts_cash, accepts_upi, accepts_card_at_service_location, "
             "accepts_bank_transfer, invoice_business_name, invoice_prefix "
             "FROM tenant_finance_readiness WHERE tenant_id=:tid"),
        {"tid": str(tenant_id)},
    )).fetchone()
    finance_methods_selected = finance_row is not None and any([
        finance_row.accepts_cash, finance_row.accepts_upi,
        finance_row.accepts_card_at_service_location, finance_row.accepts_bank_transfer,
    ])
    finance_invoice_name = (finance_row.invoice_business_name if finance_row and finance_row.invoice_business_name
                             else (tenant_row.business_name if tenant_row else None))
    finance_invoice_complete = bool(finance_invoice_name) and bool(finance_row and finance_row.invoice_prefix)
    finance_ready = finance_methods_selected and finance_invoice_complete

    sections: list[dict] = []

    def _add(key: str, required: bool, complete: bool, label: str, description: str,
             extra: dict[str, Any] | None = None, blocking_reasons: list[dict] | None = None,
             warnings: list[dict] | None = None):
        status = "complete" if complete else ("optional" if not required else "not_started")
        sections.append({
            "key": key, "label": label, "description": description,
            "required": required, "status": status,
            "blocking_reasons": blocking_reasons or [],
            "warnings": warnings or [],
            "next_action": _NEXT_ACTION_BY_SECTION[key],
            **(extra or {}),
        })

    _add("BUSINESS_PROFILE", True, profile_complete,
         "Business profile", "Business identity and registered address",
         blocking_reasons=[] if profile_complete else
         [{"code": "PROFILE_INCOMPLETE", "message": "Required business profile fields are missing."}])
    # Completion is upload-based, not verification-based: a tenant may submit
    # for review while required documents are still pending Admin
    # verification (verification happens during the review itself). Only a
    # missing upload blocks submission -- pending/rejected verification does
    # not. `verified` is surfaced separately for display only.
    _add("DOCUMENTS", True, docs_uploaded,
         "Verification documents", "Business and address verification",
         extra={"uploaded": docs_uploaded, "verified": docs_verified,
                "required_count": len(required_doc_types), "uploaded_count": len(uploaded_types & required_doc_types)},
         blocking_reasons=[] if docs_uploaded else
         [{"code": "DOCUMENTS_MISSING", "message": "Not all required documents have been uploaded."}],
         warnings=[] if docs_verified else
         [{"code": "DOCUMENTS_PENDING_VERIFICATION", "message": "Required documents are uploaded but not yet verified by Admin."}])
    _add("SERVICES_PRICING", True, services_ready,
         "Services & pricing", "Choose services and set your own prices",
         extra={"published_count": published_count, "priced_count": priced_count},
         blocking_reasons=[] if services_ready else
         [{"code": "NO_PRICED_SERVICE", "message": "No published, priced service offering yet."}])
    _add("COVERAGE_AVAILABILITY", True, coverage_ready,
         "Coverage & availability", "Where and when your team works",
         extra={"active_areas": active_areas, "availability_rules": availability_count},
         blocking_reasons=[] if coverage_ready else
         [{"code": "NO_COVERAGE_OR_SCHEDULE", "message": "No active coverage area or business schedule yet."}])
    _add("STAFF_TECHNICIANS", staff_required, staff_ready,
         "Staff & technicians", "Add the people who deliver services",
         extra={"active_staff": active_staff},
         blocking_reasons=[] if staff_ready else
         [{"code": "NO_READY_STAFF", "message": "Published services need at least one active technician."}])
    _add("FINANCE_READINESS", True, finance_ready,
         "Finance readiness", "Deposit, credits and payment policy",
         extra={"security_deposit_amount": deposit_amount, "security_deposit_paid": deposit_paid,
                "security_deposit_due_after_approval": deposit_amount > 0 and not deposit_paid},
         blocking_reasons=[] if finance_ready else
         [{"code": "FINANCE_NOT_CONFIGURED", "message": "Finance readiness has not been configured yet."}])

    required_sections = [s for s in sections if s["required"]]
    completed_required = sum(1 for s in required_sections if s["status"] == "complete")
    total_required = len(required_sections)
    review_ready = total_required > 0 and completed_required == total_required

    from app.engines.vertical_catalog.declarations import get_declaration_status
    declarations = await get_declaration_status(db, tenant_id, uuid.UUID(enrollment["vertical_id"]))

    review_submit_complete = enrollment["status"] not in ("draft_setup", "draft", "changes_requested")
    _add("REVIEW_SUBMIT", False, review_submit_complete,
         "Review & submit", "Available after required sections are complete",
         extra={"locked": not review_ready and enrollment["status"] in ("draft_setup", "draft", "changes_requested"),
                "declarations_accepted": declarations["all_accepted"]},
         blocking_reasons=[])
    # Review is an action derived from the five/six setup sections, not an
    # additional required setup section. Give it an explicit action state so
    # clients never count it as a sixth blocker.
    sections[-1]["status"] = "complete" if review_submit_complete else ("ready" if review_ready else "locked")

    percentage = round((completed_required / total_required) * 100) if total_required else 0
    blocker_count = sum(len(s["blocking_reasons"]) for s in sections)
    warning_count = sum(len(s["warnings"]) for s in sections)

    next_action_key = "REVIEW_AND_SUBMIT"
    for s in sections:
        if s["key"] == "REVIEW_SUBMIT":
            continue
        if s["required"] and s["status"] != "complete":
            next_action_key = s["next_action"]
            break

    owner_verified = False
    if tenant_row and tenant_row.owner_user_id:
        owner_verified = bool((await db.execute(
            text("SELECT is_verified FROM users WHERE id=:uid"),
            {"uid": str(tenant_row.owner_user_id)},
        )).scalar())

    # BUG FIX (2026-08-04): the real admin reject/request-changes action
    # (provider_portal admin_router -> AdminTenantService.reject_verification/
    # request_changes) only ever writes Tenant.verification_status +
    # Tenant.suspension_reason -- it never touches TenantVerticalEnrollment
    # at all. This page was reading enrollment.rejection_reason/
    # changes_requested_note exclusively, which are therefore always null
    # for every real rejection/changes-requested decision that has ever
    # happened through the actual admin UI -- the tenant had no way to see
    # why their application was rejected. Tenant.verification_status is
    # checked first and wins when it disagrees with the (dead) enrollment
    # status; the reason text comes from the real in-app notification body
    # (the same one the provider was already notified with), since
    # Tenant has no dedicated changes-requested-reason column.
    vertical_status = enrollment["status"]
    rejection_reason = enrollment.get("rejection_reason")
    changes_requested_note = enrollment.get("changes_requested_note")
    if tenant_row and tenant_row.verification_status in ("rejected", "changes_requested"):
        vertical_status = tenant_row.verification_status
        latest_notif = (await db.execute(
            text("SELECT body FROM in_app_notifications "
                 "WHERE tenant_id = :tid AND notification_type = :ntype "
                 "ORDER BY created_at DESC LIMIT 1"),
            {"tid": str(tenant_id),
             "ntype": "tenant.verification_rejected" if tenant_row.verification_status == "rejected"
                      else "tenant.verification_changes_requested"},
        )).fetchone()
        reason_text = (latest_notif.body if latest_notif else None) or tenant_row.suspension_reason
        if tenant_row.verification_status == "rejected":
            rejection_reason = reason_text
        else:
            changes_requested_note = reason_text

    return {
        "tenant": {"id": str(tenant_id), "name": tenant_row.business_name or tenant_row.tenant_name if tenant_row else None},
        "vertical": {
            "key": HOME_SERVICES_VERTICAL_KEY, "status": vertical_status,
            "rejection_reason": rejection_reason,
            "changes_requested_note": changes_requested_note,
            "suspend_reason": enrollment.get("suspend_reason"),
        },
        "lifecycle": _project_lifecycle(vertical_status),
        "declarations": declarations,
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        # sections_ready reflects ONLY the required sections above -- never
        # gated on declarations. Declaration checkboxes are local, unsaved
        # UI state on the Review page until the tenant checks them there;
        # gating the Submit button's very first render on an already-stale
        # "declarations accepted in DB" snapshot meant checking all 3 boxes
        # in the browser never actually re-enabled the button (the real
        # accept() call only happens inside doSubmit itself, one click
        # later). can_submit is kept for other callers that legitimately
        # want the combined, server-authoritative check.
        "sections_ready": review_ready,
        "can_submit": review_ready and declarations["all_accepted"]
                      and enrollment["status"] in ("draft_setup", "draft", "changes_requested"),
        "progress": {
            "percentage": percentage,
            "completed_required": completed_required,
            "total_required": total_required,
            "calculation_version": "HS_SETUP_V1",
        },
        "sections": sections,
        "workspace_status": {
            "owner_account_verified": owner_verified,
            "business_profile_status": "complete" if profile_complete else "in_progress",
            "home_services_status": enrollment["status"],
            "admin_review_status": "submitted" if enrollment.get("submitted_at") else "not_submitted",
        },
        "next_action": {"key": next_action_key},
    }


# ── Application Status projection ───────────────────────────────────────────

_STATUS_LABEL = {
    "draft_setup": "Not submitted", "draft": "Not submitted",
    "submitted": "Submitted", "under_review": "Under review",
    "changes_requested": "Changes requested", "approved": "Approved",
    "approved_pending_activation": "Approved · Activation pending",
    "activation_requirements_pending": "Approved · Activation pending",
    "activating": "Activating",
    "active": "Active", "rejected": "Rejected", "suspended": "Suspended",
}
_STATUS_INSTRUCTION = {
    "submitted": "Your setup has been submitted.",
    "under_review": "Your setup is being reviewed.",
    "changes_requested": "Updates are required before review can continue.",
    "approved": "Your setup has been approved.",
    "approved_pending_activation": "Your setup has been approved. Complete the final requirements before your workspace goes live.",
    "activation_requirements_pending": "Your setup has been approved. Complete the final requirements before your workspace goes live.",
    "activating": "Your workspace is being activated.",
    "active": "Your Home Services workspace is live.",
    "rejected": "Your application was not approved.",
    "suspended": "Your Home Services access has been suspended.",
}
_ACTIONS_BY_STATUS = {
    "submitted": ["VIEW_SUBMITTED_SETUP", "CONTACT_SUPPORT"],
    "under_review": ["VIEW_SUBMITTED_SETUP", "CONTACT_SUPPORT"],
    "changes_requested": ["REVIEW_REQUESTED_CHANGES", "CONTINUE_CORRECTIONS", "CONTACT_SUPPORT"],
    "approved": ["VIEW_APPROVAL", "CONTACT_SUPPORT"],
    "approved_pending_activation": ["VIEW_ACTIVATION_CENTER", "CONTACT_SUPPORT"],
    "activation_requirements_pending": ["VIEW_ACTIVATION_CENTER", "CONTACT_SUPPORT"],
    "activating": ["VIEW_ACTIVATION_CENTER", "CONTACT_SUPPORT"],
    "active": ["GO_TO_WORKSPACE", "VIEW_APPROVED_SETUP"],
    "rejected": ["VIEW_DECISION", "CONTACT_SUPPORT"],
    "suspended": ["CONTACT_SUPPORT"],
}
# action_type -> whose action it was. Heuristic: every enrollment.submitted
# transition is written by the tenant's own submit_for_review() call; every
# other transition comes from the admin transition endpoint. There is no
# separate actor-role lookup table for VerticalAuditLog rows, so this mirrors
# the one real distinction the codebase actually enforces at the call sites.
_ACTOR_BY_ACTION = {"enrollment.submitted": "tenant"}

_SNAPSHOT_LABELS = {
    "BUSINESS_PROFILE": "Business profile", "DOCUMENTS": "Documents",
    "SERVICES_PRICING": "Services & pricing", "COVERAGE_AVAILABILITY": "Coverage & availability",
    "STAFF_TECHNICIANS": "Staff & technicians", "FINANCE_READINESS": "Finance readiness",
}


def _lifecycle_tracker(status: str, gates: list[dict] | None = None) -> list[dict]:
    """5-stage tracker: Submitted, Admin review, Decision, Activation
    requirements, Go live. Driven only by TenantVerticalEnrollment.status
    (and, once approved, the real activation gates from
    activation.evaluate_activation_gates) -- no loose string comparisons
    against frontend-local state, no fabricated gate."""
    stages = [
        {"key": "SUBMITTED", "label": "Submitted"},
        {"key": "ADMIN_REVIEW", "label": "Admin review"},
        {"key": "DECISION", "label": "Decision"},
        {"key": "ACTIVATION_REQUIREMENTS", "label": "Activation requirements"},
        {"key": "GO_LIVE", "label": "Go live"},
    ]
    required_gates = [g for g in (gates or []) if g["required"]]
    activation_required = any(g["state"] != "not_required" for g in required_gates)
    activation_clear = all(g["state"] in ("ready", "not_required") for g in required_gates) if required_gates else True
    statuses = {"SUBMITTED": "UPCOMING", "ADMIN_REVIEW": "UPCOMING",
                "DECISION": "UPCOMING",
                "ACTIVATION_REQUIREMENTS": "NOT_REQUIRED" if not activation_required else "UPCOMING",
                "GO_LIVE": "UPCOMING"}
    if status in ("draft_setup", "draft"):
        pass
    elif status in ("submitted", "under_review"):
        statuses["SUBMITTED"] = "COMPLETED"
        statuses["ADMIN_REVIEW"] = "CURRENT"
    elif status == "changes_requested":
        statuses["SUBMITTED"] = "COMPLETED"
        statuses["ADMIN_REVIEW"] = "CURRENT"
        statuses["DECISION"] = "BLOCKED"
    elif status in ("approved", "approved_pending_activation", "activation_requirements_pending", "activating"):
        statuses["SUBMITTED"] = "COMPLETED"
        statuses["ADMIN_REVIEW"] = "COMPLETED"
        statuses["DECISION"] = "COMPLETED"
        if activation_required and not activation_clear:
            statuses["ACTIVATION_REQUIREMENTS"] = "CURRENT"
        else:
            statuses["ACTIVATION_REQUIREMENTS"] = "COMPLETED" if activation_required else "NOT_REQUIRED"
            statuses["GO_LIVE"] = "CURRENT"
    elif status == "active":
        statuses = {k: "COMPLETED" if (k != "ACTIVATION_REQUIREMENTS" or activation_required) else "NOT_REQUIRED"
                    for k in statuses}
    elif status == "rejected":
        statuses["SUBMITTED"] = "COMPLETED"
        statuses["ADMIN_REVIEW"] = "COMPLETED"
        statuses["DECISION"] = "COMPLETED"
        statuses["ACTIVATION_REQUIREMENTS"] = "NOT_APPLICABLE"
        statuses["GO_LIVE"] = "NOT_APPLICABLE"
    for s in stages:
        s["status"] = statuses[s["key"]]
    return stages


async def get_application_status(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Authoritative Application Status projection for the post-submission
    tenant portal page. Reuses get_setup_overview's sections for the
    immutable submitted-setup snapshot and VerticalAuditLog for the review
    timeline -- never a second, drifting source of truth."""
    overview = await get_setup_overview(db, tenant_id)
    svc = VerticalCatalogService()
    enrollment = await svc.get_or_create_enrollment(db, tenant_id, HOME_SERVICES_VERTICAL_KEY)
    status = enrollment["status"]

    tenant_row = (await db.execute(
        text("SELECT business_name, tenant_name FROM tenants WHERE id=:tid"), {"tid": str(tenant_id)},
    )).fetchone()

    snapshot = []
    for s in overview["sections"]:
        if s["key"] not in _SNAPSHOT_LABELS:
            continue
        snapshot.append({
            "key": s["key"], "label": _SNAPSHOT_LABELS[s["key"]],
            "status": s["status"], "blocking_reasons": s["blocking_reasons"],
        })

    activity_rows = (await db.execute(
        text("SELECT action_type, notes, created_at, actor_id "
             "FROM vertical_audit_logs WHERE tenant_id=:tid AND vertical_id=:vid "
             "ORDER BY created_at ASC"),
        {"tid": str(tenant_id), "vid": enrollment["vertical_id"]},
    )).fetchall()
    review_activity = [
        {
            "action": r.action_type,
            "actor_type": _ACTOR_BY_ACTION.get(r.action_type, "admin" if r.actor_id else "system"),
            "note": r.notes if r.action_type in ("enrollment.changes_requested", "enrollment.rejected") else None,
            "occurred_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in activity_rows
    ]

    owner_name = None  # user-safe: submitted-by is the tenant owner account; name intentionally omitted here
    # to avoid a second, possibly-stale copy of user identity -- the frontend already has it from session context.

    gates: list[dict] = []
    if status in ("approved", "approved_pending_activation", "activation_requirements_pending", "activating", "active"):
        from app.engines.vertical_catalog.activation import evaluate_activation_gates
        gates = await evaluate_activation_gates(db, tenant_id, uuid.UUID(enrollment["vertical_id"]))

    return {
        "tenant": {"id": str(tenant_id), "name": tenant_row.business_name or tenant_row.tenant_name if tenant_row else None},
        "vertical": {"key": HOME_SERVICES_VERTICAL_KEY},
        "status": status,
        "status_label": _STATUS_LABEL.get(status, status),
        "status_instruction": _STATUS_INSTRUCTION.get(status, ""),
        "is_locked": status not in ("draft_setup", "draft", "changes_requested"),
        "submitted_at": enrollment.get("submitted_at"),
        "status_changed_at": enrollment.get("reviewed_at") or enrollment.get("submitted_at"),
        "rejection_reason": enrollment.get("rejection_reason"),
        "changes_requested_note": enrollment.get("changes_requested_note"),
        "activated_at": enrollment.get("activated_at"),
        "lifecycle": _lifecycle_tracker(status, gates),
        "snapshot": snapshot,
        "review_activity": review_activity,
        "activation_gates": gates,
        "available_actions": _ACTIONS_BY_STATUS.get(status, []),
        "submission_details": {
            "vertical": "Home Services",
            "submission_id": f"HS-ONB-{str(enrollment['id'])[:6].upper()}",
            "version": 1,
            "submitted_by": owner_name,
            "policy_versions": {"documents": "2026-07-01"},
        },
    }
