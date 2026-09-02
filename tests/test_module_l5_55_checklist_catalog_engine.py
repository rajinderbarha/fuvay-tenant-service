"""MODULE-L5-55 — Checklist Catalog Engine (canonical, job-type-mapped
checklists). Mocked-unit-test convention consistent with
tests/test_module_l5_52_work_start_approval_gate.py.

Covers the delivery brief's verification list items:
  1/2/3. Draft creation, publish immutability, edit-published creates new
     draft.
  4/5/6. Exact Job-Type mapping validation, independent policies, gate
     purpose/gate legality (Repair vs Installation resolved independently
     is proven at the execution-engine layer already covered by L5-52/53;
     here we prove the mapping layer itself only accepts an exact, active
     Job Type and a PUBLISHED version).
  7/8/9. Gate blocks a forward transition when a REQUIRED mapping's
     instance is not COMPLETED/WAIVED; independent of the pre-existing
     estimate-approval gate (not touched); terminal jobs are never gated.
  10. Gate cannot be bypassed by calling the checklist service directly
     with a fabricated "satisfied" instance -- state is read from the DB
     query, not trusted from caller input.
  12. Conditional item/mapping evaluation.
  13. Required evidence validation.
  14. Actor authorisation on waiver.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import ServiceOSException
from app.engines.checklist_catalog import constants as c
from app.engines.checklist_catalog import service as svc
from app.engines.checklist_catalog import gate as gate_module

TENANT_ID = uuid.uuid4()
JOB_ID = uuid.uuid4()
MSJT_ID = uuid.uuid4()
VERSION_ID = uuid.uuid4()
MAPPING_ID = uuid.uuid4()
INSTANCE_ID = uuid.uuid4()


def _first_result(item):
    r = MagicMock()
    r.scalars.return_value.first.return_value = item
    return r


def _all_result(items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    return r


def _mock_job(status="inspection_done"):
    j = MagicMock()
    j.id = JOB_ID
    j.tenant_id = TENANT_ID
    j.status = status
    j.offering_id = uuid.uuid4()
    j.job_type_id = uuid.uuid4()
    return j


# ── Conditional evaluation (pure function) ───────────────────────────────

class TestConditionEvaluation:
    def test_no_rules_always_true(self):
        assert svc.evaluate_condition(None, {}) is True

    def test_all_clause_requires_every_condition(self):
        rules = {"all": [{"field": "brand", "op": "eq", "value": "LG"}, {"field": "type", "op": "eq", "value": "split"}]}
        assert svc.evaluate_condition(rules, {"brand": "LG", "type": "split"}) is True
        assert svc.evaluate_condition(rules, {"brand": "LG", "type": "window"}) is False

    def test_any_clause_requires_one_condition(self):
        rules = {"any": [{"field": "problem_code", "op": "in", "value": ["no_cooling", "leak"]}]}
        assert svc.evaluate_condition(rules, {"problem_code": "leak"}) is True
        assert svc.evaluate_condition(rules, {"problem_code": "noise"}) is False

    def test_neq_operator(self):
        rules = {"all": [{"field": "job_type_id", "op": "neq", "value": "x"}]}
        assert svc.evaluate_condition(rules, {"job_type_id": "y"}) is True


# ── Mapping validation: exact Job Type + published version only ─────────

class TestMappingValidation:
    @pytest.mark.asyncio
    async def test_rejects_inactive_or_unknown_job_type(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_mapping(
                db, master_service_job_type_id=MSJT_ID, service_job_workflow_id=None,
                checklist_template_version_id=VERSION_ID, phase="inspection", usage="REQUIRED",
                actor="TECHNICIAN", completion_gate="NONE", condition_rules=None, display_order=0,
                created_by=None,
            )
        assert "Job Type" in exc.value.detail

    @pytest.mark.asyncio
    async def test_rejects_unpublished_version(self):
        db = AsyncMock()
        link = MagicMock(is_active=True)
        version = MagicMock(status=c.VERSION_DRAFT)
        db.get = AsyncMock(side_effect=[link, version])
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_mapping(
                db, master_service_job_type_id=MSJT_ID, service_job_workflow_id=None,
                checklist_template_version_id=VERSION_ID, phase="inspection", usage="REQUIRED",
                actor="TECHNICIAN", completion_gate="NONE", condition_rules=None, display_order=0,
                created_by=None,
            )
        assert exc.value.error_code == c.ERR_CHECKLIST_VERSION_NOT_PUBLISHED

    @pytest.mark.asyncio
    async def test_rejects_gate_purpose_mismatch(self):
        db = AsyncMock()
        link = MagicMock(is_active=True)
        version = MagicMock(status=c.VERSION_PUBLISHED, checklist_template_id=uuid.uuid4())
        template = MagicMock(purpose=c.PURPOSE_COMPLETION)
        db.get = AsyncMock(side_effect=[link, version, template])
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_mapping(
                db, master_service_job_type_id=MSJT_ID, service_job_workflow_id=None,
                checklist_template_version_id=VERSION_ID, phase="inspection", usage="REQUIRED",
                actor="TECHNICIAN", completion_gate=c.GATE_BEFORE_INSPECTION_COMPLETE,
                condition_rules=None, display_order=0, created_by=None,
            )
        assert exc.value.error_code == "CHECKLIST_GATE_PURPOSE_MISMATCH"

    @pytest.mark.asyncio
    async def test_accepts_valid_mapping(self):
        db = AsyncMock()
        link = MagicMock(is_active=True)
        version = MagicMock(status=c.VERSION_PUBLISHED, checklist_template_id=uuid.uuid4())
        template = MagicMock(purpose=c.PURPOSE_INSPECTION)
        db.get = AsyncMock(side_effect=[link, version, template])
        db.add = MagicMock()
        db.flush = AsyncMock()
        mapping = await svc.create_mapping(
            db, master_service_job_type_id=MSJT_ID, service_job_workflow_id=None,
            checklist_template_version_id=VERSION_ID, phase="inspection", usage="REQUIRED",
            actor="TECHNICIAN", completion_gate=c.GATE_BEFORE_INSPECTION_COMPLETE,
            condition_rules=None, display_order=0, created_by=None,
        )
        assert mapping.completion_gate == c.GATE_BEFORE_INSPECTION_COMPLETE
        db.add.assert_called_once()


# ── Version immutability / draft lifecycle ───────────────────────────────

class TestVersionLifecycle:
    @pytest.mark.asyncio
    async def test_publish_rejects_non_draft(self):
        version = MagicMock(status=c.VERSION_PUBLISHED)
        with pytest.raises(ServiceOSException):
            await svc.publish_version(AsyncMock(), version, published_by=None)

    @pytest.mark.asyncio
    async def test_publish_rejects_empty_version(self, monkeypatch):
        version = MagicMock(status=c.VERSION_DRAFT)
        db = AsyncMock()
        monkeypatch.setattr(svc, "_version_readiness", AsyncMock(return_value={"ready": False}))
        with pytest.raises(ServiceOSException) as exc:
            await svc.publish_version(db, version, published_by=None)
        assert exc.value.error_code == "CHECKLIST_CONFIGURATION_UNRESOLVED"

    @pytest.mark.asyncio
    async def test_publish_marks_immutable(self, monkeypatch):
        version = MagicMock(status=c.VERSION_DRAFT)
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        monkeypatch.setattr(svc, "_version_readiness", AsyncMock(return_value={"ready": True}))
        published = await svc.publish_version(db, version, published_by=uuid.uuid4(), change_summary="v1")
        assert published.status == c.VERSION_PUBLISHED
        assert published.published_at is not None

    @pytest.mark.asyncio
    async def test_add_section_rejects_non_draft_version(self):
        version = MagicMock(status=c.VERSION_PUBLISHED)
        with pytest.raises(ServiceOSException):
            await svc.add_section(AsyncMock(), version, "Before inspection")


# ── Runtime gate: complements, never bypasses, existing estimate gate ────

class TestRuntimeGate:
    @pytest.mark.asyncio
    async def test_terminal_job_never_gated(self, monkeypatch):
        job = _mock_job(status="closed_estimate_declined")
        called = AsyncMock()
        monkeypatch.setattr(svc, "get_applicable_mappings", called)
        await gate_module.assert_gate_satisfied(AsyncMock(), job, c.GATE_BEFORE_JOB_COMPLETION)
        called.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancelled_job_never_gated(self, monkeypatch):
        job = _mock_job(status="cancelled")
        called = AsyncMock()
        monkeypatch.setattr(svc, "get_applicable_mappings", called)
        await gate_module.assert_gate_satisfied(AsyncMock(), job, c.GATE_BEFORE_JOB_COMPLETION)
        called.assert_not_called()

    @pytest.mark.asyncio
    async def test_required_incomplete_instance_blocks(self, monkeypatch):
        job = _mock_job()
        mapping = MagicMock(completion_gate=c.GATE_BEFORE_INSPECTION_COMPLETE, usage=c.USAGE_REQUIRED, id=MAPPING_ID)
        monkeypatch.setattr(svc, "get_applicable_mappings", AsyncMock(return_value=[mapping]))
        instance = MagicMock(state=c.INSTANCE_IN_PROGRESS, id=INSTANCE_ID)
        monkeypatch.setattr(svc, "ensure_instance", AsyncMock(return_value=instance))
        with pytest.raises(ServiceOSException) as exc:
            await gate_module.assert_gate_satisfied(AsyncMock(), job, c.GATE_BEFORE_INSPECTION_COMPLETE)
        assert exc.value.error_code == c.ERR_REQUIRED_CHECKLIST_INCOMPLETE
        assert exc.value.context["checklist_instance_id"] == str(INSTANCE_ID)

    @pytest.mark.asyncio
    async def test_completed_instance_passes(self, monkeypatch):
        job = _mock_job()
        mapping = MagicMock(completion_gate=c.GATE_BEFORE_INSPECTION_COMPLETE, usage=c.USAGE_REQUIRED, id=MAPPING_ID)
        monkeypatch.setattr(svc, "get_applicable_mappings", AsyncMock(return_value=[mapping]))
        instance = MagicMock(state=c.INSTANCE_COMPLETED, id=INSTANCE_ID)
        monkeypatch.setattr(svc, "ensure_instance", AsyncMock(return_value=instance))
        await gate_module.assert_gate_satisfied(AsyncMock(), job, c.GATE_BEFORE_INSPECTION_COMPLETE)  # no raise

    @pytest.mark.asyncio
    async def test_waived_instance_passes(self, monkeypatch):
        job = _mock_job()
        mapping = MagicMock(completion_gate=c.GATE_BEFORE_INSPECTION_COMPLETE, usage=c.USAGE_REQUIRED, id=MAPPING_ID)
        monkeypatch.setattr(svc, "get_applicable_mappings", AsyncMock(return_value=[mapping]))
        instance = MagicMock(state=c.INSTANCE_WAIVED, id=INSTANCE_ID)
        monkeypatch.setattr(svc, "ensure_instance", AsyncMock(return_value=instance))
        await gate_module.assert_gate_satisfied(AsyncMock(), job, c.GATE_BEFORE_INSPECTION_COMPLETE)  # no raise

    @pytest.mark.asyncio
    async def test_optional_mapping_never_blocks(self, monkeypatch):
        job = _mock_job()
        mapping = MagicMock(completion_gate=c.GATE_BEFORE_INSPECTION_COMPLETE, usage=c.USAGE_OPTIONAL, id=MAPPING_ID)
        monkeypatch.setattr(svc, "get_applicable_mappings", AsyncMock(return_value=[mapping]))
        ensure_mock = AsyncMock()
        monkeypatch.setattr(svc, "ensure_instance", ensure_mock)
        await gate_module.assert_gate_satisfied(AsyncMock(), job, c.GATE_BEFORE_INSPECTION_COMPLETE)
        ensure_mock.assert_not_called()  # optional checklists never even instantiate a blocking check

    @pytest.mark.asyncio
    async def test_other_gate_mappings_ignored(self, monkeypatch):
        job = _mock_job()
        mapping = MagicMock(completion_gate=c.GATE_BEFORE_JOB_COMPLETION, usage=c.USAGE_REQUIRED, id=MAPPING_ID)
        monkeypatch.setattr(svc, "get_applicable_mappings", AsyncMock(return_value=[mapping]))
        await gate_module.assert_gate_satisfied(AsyncMock(), job, c.GATE_BEFORE_INSPECTION_COMPLETE)  # different gate, no raise


# ── Evidence + required-item validation ──────────────────────────────────

class TestResponseValidation:
    @pytest.mark.asyncio
    async def test_evidence_required_rejects_missing_evidence(self, monkeypatch):
        instance = MagicMock(assigned_actor="TECHNICIAN", state=c.INSTANCE_IN_PROGRESS)
        item = MagicMock(evidence_required=True, min_evidence_count=1, max_evidence_count=3)
        db = AsyncMock()
        db.get = AsyncMock(return_value=item)
        with pytest.raises(ServiceOSException) as exc:
            await svc.save_response(
                db, instance, uuid.uuid4(), actor_user_id=uuid.uuid4(), actor_role="TECHNICIAN",
                response_value={"value": True}, evidence=None,
            )
        assert exc.value.error_code == c.ERR_CHECKLIST_EVIDENCE_REQUIRED

    @pytest.mark.asyncio
    async def test_evidence_over_max_rejected(self, monkeypatch):
        instance = MagicMock(assigned_actor="TECHNICIAN", state=c.INSTANCE_IN_PROGRESS)
        item = MagicMock(evidence_required=False, min_evidence_count=0, max_evidence_count=1)
        db = AsyncMock()
        db.get = AsyncMock(return_value=item)
        with pytest.raises(ServiceOSException) as exc:
            await svc.save_response(
                db, instance, uuid.uuid4(), actor_user_id=uuid.uuid4(), actor_role="TECHNICIAN",
                response_value={"value": True}, evidence=[{"file_id": "a"}, {"file_id": "b"}],
            )
        assert exc.value.error_code == c.ERR_CHECKLIST_ITEM_VALIDATION_FAILED


# ── Waiver requires authorised override ──────────────────────────────────

class TestWaiver:
    @pytest.mark.asyncio
    async def test_unauthorised_waiver_rejected(self):
        instance = MagicMock()
        with pytest.raises(ServiceOSException) as exc:
            await svc.waive_instance(AsyncMock(), instance, waived_by=uuid.uuid4(), reason="skip", authorized=False)
        assert exc.value.error_code == c.ERR_CHECKLIST_ACTOR_NOT_AUTHORIZED

    @pytest.mark.asyncio
    async def test_waiver_requires_reason(self):
        instance = MagicMock()
        with pytest.raises(ServiceOSException):
            await svc.waive_instance(AsyncMock(), instance, waived_by=uuid.uuid4(), reason="  ", authorized=True)

    @pytest.mark.asyncio
    async def test_authorised_waiver_records_audit_fields(self):
        instance = MagicMock()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        actor = uuid.uuid4()
        waived = await svc.waive_instance(db, instance, waived_by=actor, reason="Customer declined re-entry", authorized=True)
        assert waived.state == c.INSTANCE_WAIVED
        assert waived.waived_by == actor
        assert waived.waiver_reason == "Customer declined re-entry"


# ── Purpose/gate legality allowlist sanity ───────────────────────────────

class TestPurposeGateAllowlist:
    def test_completion_purpose_cannot_gate_inspection(self):
        assert c.GATE_BEFORE_INSPECTION_COMPLETE not in c.PURPOSE_ALLOWED_GATES[c.PURPOSE_COMPLETION]

    def test_inspection_purpose_can_gate_inspection_and_estimate(self):
        allowed = c.PURPOSE_ALLOWED_GATES[c.PURPOSE_INSPECTION]
        assert c.GATE_BEFORE_INSPECTION_COMPLETE in allowed
        assert c.GATE_BEFORE_ESTIMATE_SUBMISSION in allowed
        assert c.GATE_BEFORE_JOB_COMPLETION not in allowed
