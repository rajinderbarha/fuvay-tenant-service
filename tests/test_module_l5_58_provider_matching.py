"""MODULE-L5-58 — Provider Matching consolidation.

Audit found production matching and diagnostics ALREADY call the identical
select_best_provider/_passes_full_eligibility_gate functions (no divergent
logic to consolidate) and weights were already hardcoded backend constants
(no DB-editable policy). Two real gaps were found and fixed here:
  1. matching_engine read Tenant.health_score/rating_average directly,
     bypassing the canonical trust_quality.HealthScore engine entirely.
  2. No exact Job-Type Blueprint gate existed (matched on master_service_id
     + type/brand columns only).
This suite proves the fixes, the new read-only policy manifest, the reused
audit trail (no new mutation-capable table), and tie-break determinism.
"""
from __future__ import annotations

import inspect
import os
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCanonicalHealthScoreLineage:
    @pytest.mark.asyncio
    async def test_fresh_canonical_score_is_used(self):
        from app.engines.home_service_booking.matching_engine import _canonical_health_score

        db = AsyncMock()
        row = MagicMock(score=87.5, band_key="gold", bookable_allowed=True,
                        calculated_at=datetime.now(timezone.utc))
        result_mock = MagicMock()
        result_mock.first.return_value = row
        db.execute = AsyncMock(return_value=result_mock)

        score, source, calc_at, bookable = await _canonical_health_score(db, uuid.uuid4(), legacy_fallback=60.0)
        assert score == 87.5
        assert source == "canonical"
        assert calc_at is not None
        assert bookable is True

    @pytest.mark.asyncio
    async def test_stale_canonical_score_uses_neutral_unassessed_prior(self):
        from app.engines.home_service_booking.matching_engine import (
            _canonical_health_score, HEALTH_SCORE_STALE_AFTER_DAYS,
            MISSING_HEALTH_SCORE_DEFAULT,
        )

        db = AsyncMock()
        stale_at = datetime.now(timezone.utc) - timedelta(days=HEALTH_SCORE_STALE_AFTER_DAYS + 1)
        row = MagicMock(score=99.0, band_key="platinum", calculated_at=stale_at)
        result_mock = MagicMock()
        result_mock.first.return_value = row
        db.execute = AsyncMock(return_value=result_mock)

        score, source, _, bookable = await _canonical_health_score(db, uuid.uuid4(), legacy_fallback=60.0)
        assert source == "unassessed_default"
        assert score == MISSING_HEALTH_SCORE_DEFAULT  # neither stale 99 nor legacy 60
        assert bookable is True

    @pytest.mark.asyncio
    async def test_missing_everything_uses_neutral_default_never_perfect(self):
        from app.engines.home_service_booking.matching_engine import (
            _canonical_health_score, MISSING_HEALTH_SCORE_DEFAULT,
        )
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.first.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        score, source, _, bookable = await _canonical_health_score(db, uuid.uuid4(), legacy_fallback=None)
        assert source == "unassessed_default"
        assert score == MISSING_HEALTH_SCORE_DEFAULT
        assert score != 100.0  # missing data must never be treated as perfect
        assert bookable is True

    @pytest.mark.asyncio
    async def test_admin_non_bookable_health_band_is_preserved(self):
        from app.engines.home_service_booking.matching_engine import _canonical_health_score
        db = AsyncMock()
        result = MagicMock()
        result.first.return_value = MagicMock(
            score=72.0, band_key="manual_hold", bookable_allowed=False,
            calculated_at=datetime.now(timezone.utc),
        )
        db.execute = AsyncMock(return_value=result)

        score, source, _, bookable = await _canonical_health_score(
            db, uuid.uuid4(), legacy_fallback=100,
        )
        assert (score, source, bookable) == (72.0, "canonical", False)

    def test_select_best_provider_no_longer_reads_tenant_health_score_directly(self):
        from app.engines.home_service_booking import matching_engine
        src = inspect.getsource(matching_engine.select_best_provider)
        assert "row.health_score if row.health_score" not in src
        assert "_canonical_health_score" in src


class TestExactJobTypeGate:
    @pytest.mark.asyncio
    async def test_gate_rejects_unsupported_job_type(self):
        from app.engines.home_service_booking.matching_engine import _passes_full_eligibility_gate

        db = AsyncMock()
        no_link = MagicMock()
        no_link.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_link)

        eligible, reason = await _passes_full_eligibility_gate(
            db, tenant_id=uuid.uuid4(), offering_id=uuid.uuid4(),
            offering_type_id=None, brand_id=None, job_type_id=uuid.uuid4(),
        )
        assert eligible is False
        assert reason == "EXACT_JOB_TYPE_NOT_SUPPORTED"

    @pytest.mark.asyncio
    async def test_gate_skipped_when_no_job_type_id_given(self):
        # No job_type_id -> must not raise/short-circuit on the job-type gate;
        # falls through to the next real gate (bookability), which we mock
        # to fail cleanly so the test proves gate 0 was SKIPPED, not crashed.
        from app.engines.home_service_booking.matching_engine import _passes_full_eligibility_gate

        db = AsyncMock()
        not_bookable = MagicMock()
        not_bookable.fetchone.return_value = None
        db.execute = AsyncMock(return_value=not_bookable)

        eligible, reason = await _passes_full_eligibility_gate(
            db, tenant_id=uuid.uuid4(), offering_id=uuid.uuid4(),
            offering_type_id=None, brand_id=None, job_type_id=None,
        )
        assert reason != "EXACT_JOB_TYPE_NOT_SUPPORTED"


class TestPolicyManifest:
    def test_manifest_is_code_controlled_and_read_only(self):
        from app.engines.home_service_booking.matching_engine import get_policy_manifest
        manifest = get_policy_manifest()
        assert manifest["code_controlled"] is True
        assert manifest["policy_key"]
        assert manifest["version"] >= 1
        assert len(manifest["factors"]) == 6
        assert manifest["version"] == 3
        assert "eligibility_gates" in manifest
        assert "EXACT_JOB_TYPE_NOT_SUPPORTED" in manifest["eligibility_gates"]
        assert "missing_signal_policy" in manifest

    def test_manifest_weights_match_deployed_constants_exactly(self):
        from app.engines.home_service_booking import matching_engine as me
        manifest = me.get_policy_manifest()
        weight_by_key = {f["factor_key"]: f["weight"] for f in manifest["factors"]}
        assert weight_by_key["health_score"] == float(me.WEIGHT_HEALTH_SCORE)
        assert weight_by_key["service_reliability"] == float(me.WEIGHT_SERVICE_RELIABILITY)
        assert weight_by_key["slot_fit"] == float(me.WEIGHT_SLOT_FIT)
        assert weight_by_key["area_match"] == float(me.WEIGHT_DISTANCE)
        assert weight_by_key["capacity"] == float(me.WEIGHT_CAPACITY)
        assert weight_by_key["fair_share"] == float(me.WEIGHT_FAIR_SHARE)

    def test_weights_sum_to_one(self):
        from app.engines.home_service_booking import matching_engine as me
        total = (me.WEIGHT_HEALTH_SCORE + me.WEIGHT_SERVICE_RELIABILITY
                 + me.WEIGHT_SLOT_FIT + me.WEIGHT_DISTANCE
                 + me.WEIGHT_CAPACITY + me.WEIGHT_FAIR_SHARE)
        assert total == 1

    def test_no_admin_write_route_exists_for_policy(self):
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        src = inspect.getsource(router_mod)
        assert '"/matching/policy"' in src
        assert 'admin_router.post("/matching/policy"' not in src
        assert 'admin_router.put("/matching/policy"' not in src


class TestTieBreakDeterminism:
    def test_equal_scores_break_tie_by_tenant_id_not_random(self):
        from app.engines.home_service_booking.matching_engine import rank_candidates, CandidateSignals
        # Two candidates with identical sub-scores -> identical weighted score.
        a = CandidateSignals(tenant_id="b-tenant", provider_name="B", health_score=80,
                              job_completion_score=80, rating_score=80, availability_score=80,
                              service_match_score=80, distance_score=80, cancellation_score=80, capacity_score=80)
        b = CandidateSignals(tenant_id="a-tenant", provider_name="A", health_score=80,
                              job_completion_score=80, rating_score=80, availability_score=80,
                              service_match_score=80, distance_score=80, cancellation_score=80, capacity_score=80)
        ranked = rank_candidates([a, b])
        assert ranked[0][0].tenant_id == "a-tenant"  # lexicographically first tenant_id wins the tie

    def test_equal_health_round_robin_rotates_to_waiting_provider(self):
        from app.engines.home_service_booking.matching_engine import select_best_candidate, CandidateSignals
        common = dict(provider_name="P", slot_fit_score=80, distance_score=100, capacity_score=80)
        served = CandidateSignals(tenant_id="served", health_score=80,
                                  service_reliability_score=82, recent_allocations=1, **common)
        waiting = CandidateSignals(tenant_id="waiting", health_score=80,
                                   service_reliability_score=80, recent_allocations=0, **common)
        assert select_best_candidate([served, waiting])[0].tenant_id == "waiting"

    def test_lower_health_receives_fewer_but_nonzero_jobs(self):
        from app.engines.home_service_booking.matching_engine import select_best_candidate, CandidateSignals
        counts = {"healthy": 0, "lower": 0}
        for _ in range(12):
            candidates = [
                CandidateSignals(tenant_id="healthy", provider_name="Healthy", health_score=90,
                                 service_reliability_score=80, recent_allocations=counts["healthy"]),
                CandidateSignals(tenant_id="lower", provider_name="Lower", health_score=60,
                                 service_reliability_score=80, recent_allocations=counts["lower"]),
            ]
            selected = select_best_candidate(candidates)[0].tenant_id
            counts[selected] += 1
        assert counts["healthy"] > counts["lower"] > 0

    def test_health_weight_declines_continuously_to_the_safe_floor(self):
        from app.engines.home_service_booking.matching_engine import health_allocation_weight
        assert float(health_allocation_weight(100)) == 1
        assert float(health_allocation_weight(70)) == pytest.approx(0.5)
        assert float(health_allocation_weight(50)) == pytest.approx(1 / 6)

    def test_ranking_is_deterministic_across_repeated_calls(self):
        from app.engines.home_service_booking.matching_engine import rank_candidates, CandidateSignals
        candidates = [
            CandidateSignals(tenant_id=f"t{i}", provider_name=f"P{i}", health_score=50 + i)
            for i in range(5)
        ]
        r1 = rank_candidates(candidates)
        r2 = rank_candidates(candidates)
        assert [c.tenant_id for c, _ in r1] == [c.tenant_id for c, _ in r2]

    def test_recent_allocation_deficit_becomes_fair_share_score(self):
        from app.engines.home_service_booking.matching_engine import _fair_share_scores
        waiting, served = uuid.uuid4(), uuid.uuid4()
        scores = _fair_share_scores({waiting, served}, {waiting: 1, served: 5})
        assert scores[waiting] == 100.0
        assert scores[served] == 0.0

    @pytest.mark.asyncio
    async def test_allocation_history_is_geographic_and_cross_service(self):
        from app.engines.home_service_booking.matching_engine import _recent_allocation_counts
        provider_id = uuid.uuid4()
        result = MagicMock()
        result.fetchall.return_value = [MagicMock(provider_id=str(provider_id), n=3)]
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result)

        counts = await _recent_allocation_counts(
            db, {provider_id}, offering_id=uuid.uuid4(), city="Bassi Pathana",
            zipcode="140412",
        )

        assert counts == {provider_id: 3}
        sql = str(db.execute.await_args.args[0])
        params = db.execute.await_args.args[1]
        assert "service_jobs" in sql and "zipcode" in sql
        assert "master_service_id" not in sql
        assert "hold_minutes" in params
        assert params["zipcode"] == "140412"


class TestDataScienceObservation:
    @pytest.mark.asyncio
    async def test_matching_observation_is_immutable_shadow_data(self):
        from app.engines.data_science.models import PredictionRecord
        from app.engines.data_science.service import DSService

        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        service = DSService(db)
        service._get_ds_phase = AsyncMock(return_value=1)
        service._get_active_model_version = AsyncMock(return_value="rule_based_v1")
        tenant_id = uuid.uuid4()

        await service.record_provider_matching_observation(
            selected_tenant_id=tenant_id,
            entity_id="draft-1",
            inputs={"candidates": [{"health_score": 80}]},
            output={"selected_provider_id": str(tenant_id)},
        )

        record = db.add.call_args.args[0]
        assert isinstance(record, PredictionRecord)
        assert record.observation_mode is True
        assert record.prediction_type == "provider_matching"
        assert record.inputs["candidates"][0]["health_score"] == 80


class TestDiagnosticNoMutation:
    def test_diagnostics_endpoint_never_creates_a_booking_job_or_assignment(self):
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        src = inspect.getsource(router_mod.admin_matching_diagnostics)
        for forbidden in ("HomeServiceBookingDraft(", "Job(", "ProviderTeamMember(", "create_job", "assign_job"):
            assert forbidden not in src

    def test_diagnostics_only_write_is_the_audit_log_row(self):
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        src = inspect.getsource(router_mod.admin_matching_diagnostics)
        assert "MasterDataAuditLog(" in src
        assert "db.add(" in src
        # Only one db.add call in the whole diagnostic handler.
        assert src.count("db.add(") == 1

    def test_diagnostics_never_writes_health_score(self):
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        src = inspect.getsource(router_mod.admin_matching_diagnostics)
        assert "HealthScore(" not in src
        assert ".health_score =" not in src


class TestDiagnosticProductionParity:
    def test_diagnostic_and_production_call_the_identical_function(self):
        from app.engines.admin_catalog import auto_price_options_router as admin_router_mod
        from app.engines.home_service_booking import service as booking_service_mod, matching_engine
        admin_src = inspect.getsource(admin_router_mod.admin_matching_diagnostics)
        assert "select_best_provider(" in admin_src
        assert admin_router_mod.select_best_provider is matching_engine.select_best_provider

        booking_src = inspect.getsource(booking_service_mod.HomeServiceChatbotBookingService.match_provider_and_price)
        assert "select_best_provider(" in booking_src


class TestAuditReusesCanonicalSystem:
    def test_audit_endpoints_read_master_data_audit_log_not_a_new_table(self):
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        audit_src = inspect.getsource(router_mod.get_matching_diagnostic_audit)
        decisions_src = inspect.getsource(router_mod.get_matching_live_decisions)
        assert "MasterDataAuditLog" in audit_src
        assert "MasterDataAuditLog" in decisions_src

    def test_audit_and_decisions_are_read_only_get_routes(self):
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        src = inspect.getsource(router_mod)
        assert 'admin_router.get("/matching/audit"' in src
        assert 'admin_router.get("/matching/decisions"' in src
