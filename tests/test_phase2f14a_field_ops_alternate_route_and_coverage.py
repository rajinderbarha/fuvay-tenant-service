"""Phase 2A Slice 2F-14A — field_ops alternate-route, JobNote/JobMedia and
coverage reconciliation.

Findings and fixes (continuation of Slice 2F-14, whose SECURITY_CLOSED /
PRIVACY_CLOSED / coverage claims were not approved):

1. **JobNote/JobMedia had zero access control.** `add_note`/`list_notes`/
   `add_media`/`list_media` on `field_ops.router` accepted a client-supplied
   `tenant_id` query param with no verification against the job's actual
   tenant, and performed no job-ownership check at all -- any authenticated
   user (a customer, an unassigned technician, a staff member from a
   different tenant) could read or write notes/media on any job by ID, and
   `list_notes` returned `is_internal=True` provider-only notes to
   customers. Fixed: `tenant_id` is now always derived server-side from the
   job row; `_assert_can_access_job` (the same existing ownership check used
   for job reads) is enforced before any note/media read or write; customers
   are denied write access to both; `list_notes` filters `is_internal=True`
   notes out of customer reads. JobMedia has no internal/customer-visible
   column, so no equivalent read-side filtering could be added without
   inventing new schema -- documented as a product decision, not silently
   assumed.

2. **`void_job` had a genuine cross-tenant IDOR.** It loaded the job by ID
   with no tenant-ownership check at all -- any actor holding the
   platform-wide `TENANT_UPDATE` permission could void a job belonging to a
   different tenant. Fixed by reusing `_get_job_for_assignment` (the
   existing tenant_owner-own-tenant/super_admin helper already used by
   `assign_staff`/`convert_to_repair`).

3. **`start_assessment`/`complete_assessment` had no named role dependency**
   (same assigned-technician execution class as `accept_job`, fixed in
   2F-14) -- `_get_job_for_staff_action` already made this safe via
   ID-equality, but for tool-visibility/defense-in-depth consistency both
   now require `require_staff_or_technician_only`.

4. **`close_job`/`generate_invoice`/`record_payment`/`deduct_commission`/
   `financial_close` were `PERMISSION_ONLY_NOT_SCOPE_AWARE`** (same access-
   scope gap class already fixed for `assign_job`/`update_status`) -- all 5
   upgraded to `require_tenant_mutation_permission`. Object-ownership via
   `_get_job_for_billing` was already correct and unmodified.

5. **Exact route-count reconciliation**: `field_ops.staff_router` has
   exactly 6 mounted mutations (unchanged). `field_ops.router` has exactly
   28 mounted mutations; the "7 vs 9" discrepancy in Slice 2F-14's own
   documentation is resolved as: 7 = the count of routes using
   `require_staff_or_technician_only` specifically; 9 = that same 7 plus the
   2 routes (`assign_job`, `update_status`) fixed with
   `require_tenant_mutation_permission` -- both figures were correct
   descriptions of different subsets, not a contradiction. This slice's
   fixes bring the router's tool-verified-protected count from 9 to 17 of
   28 (accept_job, reject_assignment, start_checklist, update_checklist_item,
   complete_checklist, submit_findings, legacy update_checklist,
   start_assessment, complete_assessment = 9 STAFF_EXECUTION_ROLE_SCOPE_AWARE;
   assign_job, update_status, close_job, generate_invoice, record_payment,
   deduct_commission, financial_close, void_job = 8
   TENANT_MUTATION_PERMISSION_SCOPE_AWARE).

6. **Global coverage discrepancy resolved.** The master
   `tenant-mutation-endpoint-inventory.csv` contained 2 exact-duplicate rows
   (`home_service_assignment.staff_router`'s `accept_job`/`reject_job`,
   double-appended in an earlier slice) and 1 false-positive row
   (`admin_catalog.tenant_router`'s `preview_tenant_price_options`, a preview/
   read endpoint mis-tagged as a mutation in an earlier slice) -- removing
   these 3 rows takes the total from 213 to the previously-expected 210.
   Separately, `FULLY_PROTECTED` rows (9 of them, all pre-existing) had been
   omitted from every prior slice's "protected" recount set -- correcting
   this raises the numerator. Canonical result: **158 protected of 210
   tenant-facing mutation routes**, superseding both of 2F-14's conflicting
   figures (146/210 and 143/213).
"""
from __future__ import annotations

import csv
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.field_ops.constants import JS
from app.engines.field_ops.service import FieldOpsService
from app.engines.field_ops.models import JobNote, JobMedia
from app.exceptions import ServiceOSException, NotFoundException

ROOT = os.path.dirname(os.path.dirname(__file__))
ROUTER = os.path.join(ROOT, "app", "engines", "field_ops", "router.py")
SERVICE = os.path.join(ROOT, "app", "engines", "field_ops", "service.py")
INVENTORY_CSV = os.path.join(ROOT, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                              "tenant-mutation-endpoint-inventory.csv")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _job(**overrides):
    j = MagicMock()
    j.id = overrides.get("id", uuid.uuid4())
    j.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    j.assigned_staff_id = overrides.get("assigned_staff_id", uuid.uuid4())
    j.customer_id = overrides.get("customer_id", uuid.uuid4())
    j.status = overrides.get("status", "assigned")
    return j


def _db_returning(*results):
    import datetime
    db = MagicMock()
    rs = []
    for res in results:
        r = MagicMock()
        r.scalar_one_or_none.return_value = res
        rs.append(r)
    db.execute = AsyncMock(side_effect=rs)

    def _add(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.datetime(2026, 1, 1)
    db.add = MagicMock(side_effect=_add)
    db.flush = AsyncMock()
    return db


# ── JobNote access control ────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestJobNoteAccessControl:
    async def test_tenant_owner_own_tenant_can_add_note(self):
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.add_note(job.id, "note body", "staff_note", True)
        assert result["content"] == "note body"

    async def test_assigned_technician_can_add_note(self):
        me = uuid.uuid4()
        job = _job(assigned_staff_id=me)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="technician")
        result = await svc.add_note(job.id, "note body", "staff_note", True)
        assert result["content"] == "note body"

    async def test_unassigned_technician_denied_add_note(self):
        job = _job(assigned_staff_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.add_note(job.id, "note body", "staff_note", True)

    async def test_cross_tenant_owner_denied_add_note(self):
        job = _job(tenant_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=uuid.uuid4())
        with pytest.raises(NotFoundException):
            await svc.add_note(job.id, "note body", "staff_note", True)

    async def test_customer_denied_add_note(self):
        me = uuid.uuid4()
        job = _job(customer_id=me)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="customer")
        with pytest.raises(ServiceOSException) as ei:
            await svc.add_note(job.id, "note body", "staff_note", True)
        assert ei.value.error_code == "NOTE_ACCESS_DENIED"

    async def test_foreign_job_add_note_rejected(self):
        db = _db_returning(None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.add_note(uuid.uuid4(), "note body", "staff_note", True)

    async def test_customer_read_excludes_internal_notes(self):
        me = uuid.uuid4()
        job = _job(customer_id=me)
        internal = MagicMock(id=uuid.uuid4(), content="internal", note_type="staff_note",
                              author_role="staff", status_at="assigned", is_internal=True,
                              created_at=MagicMock(isoformat=lambda: "x"))
        public = MagicMock(id=uuid.uuid4(), content="public", note_type="staff_note",
                            author_role="staff", status_at="assigned", is_internal=False,
                            created_at=MagicMock(isoformat=lambda: "x"))
        db = MagicMock()
        job_r = MagicMock(); job_r.scalar_one_or_none.return_value = job
        notes_r = MagicMock(); notes_r.scalars.return_value.all.return_value = [internal, public]
        db.execute = AsyncMock(side_effect=[job_r, notes_r])
        svc = FieldOpsService(db=db, actor_id=me, actor_role="customer")
        result = await svc.list_notes(job.id)
        contents = [n["content"] for n in result["notes"]]
        assert "internal" not in contents
        assert "public" in contents

    async def test_staff_read_includes_internal_notes(self):
        me = uuid.uuid4()
        job = _job(assigned_staff_id=me)
        internal = MagicMock(id=uuid.uuid4(), content="internal", note_type="staff_note",
                              author_role="staff", status_at="assigned", is_internal=True,
                              created_at=MagicMock(isoformat=lambda: "x"))
        db = MagicMock()
        job_r = MagicMock(); job_r.scalar_one_or_none.return_value = job
        notes_r = MagicMock(); notes_r.scalars.return_value.all.return_value = [internal]
        db.execute = AsyncMock(side_effect=[job_r, notes_r])
        svc = FieldOpsService(db=db, actor_id=me, actor_role="technician")
        result = await svc.list_notes(job.id)
        assert result["notes"][0]["content"] == "internal"

    async def test_unassigned_technician_denied_list_notes(self):
        job = _job(assigned_staff_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.list_notes(job.id)

    async def test_no_mutation_on_denied_add_note(self):
        job = _job(assigned_staff_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.add_note(job.id, "x", "staff_note", True)
        db.add.assert_not_called()


# ── JobMedia access control ───────────────────────────────────────────────────

@pytest.mark.asyncio
class TestJobMediaAccessControl:
    async def test_assigned_technician_can_attach_media(self):
        me = uuid.uuid4()
        job = _job(assigned_staff_id=me)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="technician")
        result = await svc.add_media(job.id, None, "photo", "cap", "key")
        assert result["job_id"] == str(job.id)

    async def test_foreign_job_add_media_rejected(self):
        db = _db_returning(None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.add_media(uuid.uuid4(), None, "photo", None, None)

    async def test_unassigned_technician_denied_add_media(self):
        job = _job(assigned_staff_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.add_media(job.id, None, "photo", None, None)

    async def test_cross_tenant_denied_add_media(self):
        job = _job(tenant_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=uuid.uuid4())
        with pytest.raises(NotFoundException):
            await svc.add_media(job.id, None, "photo", None, None)

    async def test_customer_denied_add_media(self):
        me = uuid.uuid4()
        job = _job(customer_id=me)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="customer")
        with pytest.raises(ServiceOSException) as ei:
            await svc.add_media(job.id, None, "photo", None, None)
        assert ei.value.error_code == "MEDIA_ACCESS_DENIED"

    async def test_unassigned_technician_denied_list_media(self):
        job = _job(assigned_staff_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.list_media(job.id)

    async def test_no_mutation_on_denied_add_media(self):
        job = _job(assigned_staff_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.add_media(job.id, None, "photo", None, None)
        db.add.assert_not_called()


# ── void_job cross-tenant IDOR fix ────────────────────────────────────────────

@pytest.mark.asyncio
class TestVoidJobOwnership:
    async def test_cross_tenant_owner_denied_void(self):
        job = _job(tenant_id=uuid.uuid4(), status=JS.ASSIGNED)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=uuid.uuid4())
        with pytest.raises(ServiceOSException) as ei:
            await svc.void_job(job.id, "reason")
        assert ei.value.error_code == "JOB_NOT_FOUND"
        assert job.status == JS.ASSIGNED  # unchanged

    async def test_own_tenant_owner_can_void(self):
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id, status=JS.ASSIGNED)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        await svc.void_job(job.id, "reason")
        assert job.status == JS.VOIDED

    async def test_super_admin_can_void_any_tenant(self):
        job = _job(tenant_id=uuid.uuid4(), status=JS.ASSIGNED)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
        await svc.void_job(job.id, "reason")
        assert job.status == JS.VOIDED


# ── Source-level guard verification for router-level fixes ──────────────────

class TestRouterGuardSources:
    def test_assessment_routes_use_named_dependency(self):
        src = _read(ROUTER)
        body = src.split("async def start_assessment")[1].split("\n@router")[0]
        assert "require_staff_or_technician_only" in body
        body2 = src.split("async def complete_assessment")[1].split("\n@router")[0]
        assert "require_staff_or_technician_only" in body2

    def test_void_job_uses_tenant_mutation_permission(self):
        src = _read(ROUTER)
        decorator_and_body = src.split('@router.post("/{job_id}/void"')[1].split("\n@router")[0]
        assert "require_tenant_mutation_permission(P.TENANT_UPDATE)" in decorator_and_body

    def test_financial_routes_use_tenant_mutation_permission(self):
        src = _read(ROUTER)
        for fn in ("close_job", "generate_invoice", "record_payment", "deduct_commission", "financial_close"):
            body = src.split(f"async def {fn}")[1].split("\n@router")[0]
            assert "require_tenant_mutation_permission" in body, fn

    def test_add_note_add_media_no_longer_take_client_tenant_id(self):
        src = _read(ROUTER)
        note_body = src.split("async def add_note")[1].split("\n@router")[0]
        media_body = src.split("async def add_media")[1].split("\n@router")[0]
        assert "tenant_id: uuid.UUID = Query" not in note_body
        assert "tenant_id: uuid.UUID = Query" not in media_body

    def test_service_derives_tenant_id_from_job(self):
        src = _read(SERVICE)
        add_note_body = src.split("async def add_note")[1].split("\n    async def ")[0]
        add_media_body = src.split("async def add_media")[1].split("\n    async def ")[0]
        assert "_assert_can_access_job" in add_note_body
        assert "_assert_can_access_job" in add_media_body
        assert "tenant_id=job.tenant_id" in add_note_body
        assert "tenant_id=job.tenant_id" in add_media_body

    def test_void_job_service_uses_assignment_ownership_helper(self):
        src = _read(SERVICE)
        body = src.split("async def void_job")[1].split("\n    async def ")[0]
        assert "_get_job_for_assignment" in body


# ── Canonical global coverage recount ─────────────────────────────────────────

class TestCanonicalCoverageRecount:
    VERIFIED = {
        "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
        "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
        "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
    }

    def _rows(self):
        with open(INVENTORY_CSV, encoding="utf-8") as f:
            rows = list(csv.reader(f))
        return rows[1:]

    def test_no_duplicate_rows(self):
        rows = self._rows()
        keys = [(r[0], r[1], r[3]) for r in rows]
        assert len(keys) == len(set(keys))

    def test_no_false_positive_rows(self):
        rows = self._rows()
        assert not any("FALSE_POSITIVE" in r[6] for r in rows)

    def test_canonical_totals(self):
        # Slice 2F-16 reconciliation: added 11 new app.engines.quote_checklist
        # tenant/provider mutation rows (staff_create_quote, staff_add_item,
        # staff_update_item, staff_remove_item, staff_send_to_customer,
        # staff_mark_revised, staff_cancel_quote, provider_cancel_quote,
        # staff_create_checklist, staff_update_checklist_item,
        # staff_complete_checklist) -- all previously AUTHENTICATED_ONLY_NO_PERMISSION_CHECK
        # (get_current_user only, zero persona/permission check), now
        # require_owner_or_office_staff_mutation, all protected. The 3
        # customer-decision routes (approve/reject/request-revision) and the
        # 2 platform-only admin-template routes are correctly excluded from
        # this tenant-only CSV (Design A) -- see
        # docs/workflow-rearchitecture/phase-02a-slice-02f16/canonical-coverage-update.md.
        # Denominator 216 -> 227 (+11); protected 175 -> 186 (+11).
        #
        # Slice 2F-17 reconciliation (inventory-only, no authorization code
        # changed): row-level runtime recount of the 41 rows previously
        # counted as unprotected found:
        #   - 1 confirmed false positive (preview_matching_inputs, already in
        #     the runtime tool's CONFIRMED_FALSE_POSITIVE_ROUTES exemption set
        #     since Slice 2F-2, but the CSV row was never removed) -- removed
        #     from the canonical CSV entirely (denominator -1).
        #   - 4 rows already fixed in Slice 2F-6A (provider_issue_invoice,
        #     provider_record_payment, staff_create_invoice,
        #     staff_add_invoice_item -- app.engines.invoice_payment.provider_router,
        #     runtime-confirmed 0 unverified) but the CSV guard_status was
        #     never updated to reflect it -- reclassified to VERIFIED
        #     (numerator +4).
        #   - The remaining 36 rows are genuinely still unprotected (runtime
        #     re-confirmed PERMISSION_ONLY_NOT_SCOPE_AWARE /
        #     AUTHENTICATED_ONLY_NO_PERMISSION_CHECK) -- unchanged.
        # Denominator 227 -> 226 (-1); protected 186 -> 190 (+4).
        # Current canonical prior to 2F-18: 190/226. See
        # docs/workflow-rearchitecture/phase-02a-slice-02f17/.
        #
        # Slice 2F-18: app.engines.platform_notifications.provider_router's
        # 10 mutation routes (provider_mark_read, provider_mark_all_read,
        # provider_update_pref, provider_create_thread, provider_send_message,
        # provider_mark_thread_read -- require_owner_or_office_staff_mutation;
        # staff_mark_read, staff_mark_all_read, staff_send_message,
        # staff_mark_thread_read -- require_staff_or_technician_only) were all
        # previously AUTHENTICATED_ONLY_NO_PERMISSION_CHECK (get_current_user
        # only) and are now protected. Denominator unchanged (226); protected
        # 190 -> 200 (+10). See
        # docs/workflow-rearchitecture/phase-02a-slice-02f18/canonical-coverage-update.md.
        #
        # Slice 2F-20: app.engines.compliance.provider_router's 6 mutation
        # routes (withdraw_consent, customer_tenant_response,
        # create_my_request, cancel_my_request, generate_export,
        # staff_tenant_response -- all require_tenant_owner_mutation) were
        # previously ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE (require_tenant_owner,
        # no readonly-access-scope check) and are now protected. Denominator
        # unchanged (226); protected 200 -> 206 (+6). See
        # docs/workflow-rearchitecture/phase-02a-slice-02f20/canonical-coverage-update.md.
        rows = self._rows()
        total = len(rows)
        protected = sum(1 for r in rows if r[6] in self.VERIFIED)
        # Slice 2F-25 discovered three genuine tenant mutations on the
        # legacy review engine (/v1/reviews/*) that the prefix-based
        # sweep never considered, added them to the canonical CSV by
        # exact route evidence, and protected all three in the same
        # slice: denominator 226 -> 229, numerator 209 -> 212.
        # Slice 2F-26 application-wide persona sweep: 28 tenant mutations
        # on generic prefixes (/v1/auth, /v1/media, /v1/me, /v1/bookings,
        # /v1/commerce, /v1/enterprise, /v1/rag) had never been counted --
        # the prefix-based sweep never considered them. Denominator
        # 229 -> 257, numerator 212 -> 214 (26 of the 28 are unprotected),
        # unprotected 17 -> 43.
        # Slice 2F-35 critical destructive/security batch: denominator
        # 264 -> 273 (+9 held routes), numerator 241 -> 252 (+2 Set A +9 Set B).
        # Slice 2F-36: denominator 273 -> 297, numerator 252 -> 294.
        # Slice 2F-37: denominator 297 -> 313, numerator 294 -> 313.
        assert total == 313
        assert protected == 313

    def test_field_ops_subtotal(self):
        # Superseded by Slice 2F-14C: 38 -> 40 of 40 (full field_ops.router
        # closure, see phase-02a-slice-02f14c/).
        rows = self._rows()
        fo = [r for r in rows if "field_ops" in r[3]]
        protected = sum(1 for r in fo if r[6] in self.VERIFIED)
        assert len(fo) == 40
        assert protected == 40
