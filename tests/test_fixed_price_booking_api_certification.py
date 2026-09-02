"""Continuous API certification for a fixed-price Home Services job.

The repair certification covers inspection, estimate revision and approval.
This companion proves that fixed-price maintenance follows the shorter
published workflow and still reaches payment, completion and one credit debit.
Every write is rolled back.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.main import app
from tests.test_booking_api_end_to_end_certification import (
    CUSTOMER_ID,
    TENANT_ID,
    TENANT_OWNER_ID,
    TECHNICIAN_MEMBER_ID,
    TECHNICIAN_USER_ID,
    _assert_ok,
    _context,
    _provision_transactional_provider_capacity,
)


@pytest.mark.asyncio
async def test_fixed_price_maintenance_booking_to_completion_api_only():
    engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        outer = await connection.begin()
        sessions = async_sessionmaker(
            bind=connection, class_=AsyncSession, expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async def override_db():
            async with sessions() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise

        active = {"user": _context("customer", CUSTOMER_ID)}
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: active["user"]
        try:
            await _provision_transactional_provider_capacity(connection)
            address_id = uuid.uuid4()
            await connection.execute(text(
                "INSERT INTO customer_addresses "
                "(id, customer_id, name, address_line_1, city, state, country, zipcode, "
                "is_default, is_active, created_at, updated_at) VALUES "
                "(:id,:customer,'Fixed Price Cert','2 Maintenance Road','BASSIPATHANA',"
                "'Punjab','India','140412',false,true,now(),now())"
            ), {"id": address_id, "customer": CUSTOMER_ID})

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", timeout=90,
            ) as client:
                headers = {"Authorization": "Bearer fixed-cert"}
                bootstrap = _assert_ok(await client.get(
                    "/v1/customer/home-services/assistant-bootstrap", headers=headers,
                    params={"category_slug": "home_services", "zipcode": "140412"},
                ))
                issue = next(i for i in bootstrap["issues"] if i["label"] == "Routine AC servicing")
                selected = _assert_ok(await client.post(
                    "/v1/customer/home-services/assistant-bootstrap/select-issue",
                    headers=headers,
                    json={"category_slug": "home_services", "zipcode": "140412", "issue_id": issue["id"]},
                ))
                draft_id = selected["draft_id"]
                envelope = selected["envelope"]
                while not envelope["progress"]["complete"]:
                    question = envelope["current_question"]
                    payload = {"question_id": question["question_id"]}
                    options = question.get("options") or []
                    if options:
                        payload["option_id"] = options[0]["id"]
                    else:
                        payload["value"] = "Fixed-price certification response"
                    envelope = _assert_ok(await client.post(
                        f"/v1/customer/home-services/booking-drafts/{draft_id}/question-flow/answer",
                        headers=headers, json=payload,
                    ))

                _assert_ok(await client.put(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}", headers=headers,
                    json={
                        "address_id": str(address_id), "customer_name": "Fixed Price Cert",
                        "customer_phone": "9999999999",
                        "preferred_date": (date.today() + timedelta(days=3)).isoformat(),
                        "preferred_time_window": "09:00-10:00",
                    },
                ))
                assert _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/serviceability-check",
                    headers=headers,
                ))["serviceable"] is True
                match = _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/match-and-price",
                    headers=headers,
                ))
                assert match["selected_provider"]["tenant_id"] == str(TENANT_ID)
                assert match["pricing_mode"] == "fixed"
                draft = _assert_ok(await client.get(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}", headers=headers,
                ))
                price = draft["price_snapshot"]
                assert price["requires_inspection_estimate"] is False
                assert price["standard_price"] is not None
                assert price.get("visit_fee") in (None, 0, "0", "0.00")
                choice = _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/confirm-price-choice",
                    headers=headers, json={"price_tier": "standard"},
                ))
                assert choice["booking_summary"]["selected_price_tier"] == "standard"

                slots = _assert_ok(await client.get(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/available-slots",
                    headers=headers,
                ))["slots"]
                assert slots
                slot = slots[0]
                _assert_ok(await client.put(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}", headers=headers,
                    json={"preferred_date": slot["date"], "preferred_time_window": slot["time_window"]},
                ))
                _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/select-slot",
                    headers=headers, json={"date": slot["date"], "time_window": slot["time_window"]},
                ))
                confirmed = _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/confirm",
                    headers={**headers, "Idempotency-Key": f"fixed-{uuid.uuid4()}"},
                ))
                job_id = confirmed["job_id"]

                active["user"] = _context("tenant_owner", TENANT_OWNER_ID, TENANT_ID)
                _assert_ok(await client.post(
                    f"/v1/provider/service-jobs/{job_id}/assign", headers=headers,
                    json={"staff_member_id": str(TECHNICIAN_MEMBER_ID)},
                ))
                active["user"] = _context("technician", TECHNICIAN_USER_ID, TENANT_ID)
                _assert_ok(await client.post(f"/v1/staff/service-jobs/{job_id}/accept", headers=headers))
                for action, payload in (
                    ("customer-contacted", {"notes": "Maintenance requirements confirmed"}),
                    ("on-the-way", None), ("reached-site", None),
                ):
                    _assert_ok(await client.post(
                        f"/v1/staff/service-jobs/{job_id}/{action}", headers=headers, json=payload,
                    ))

                # The central assertion for fixed work: no inspection/estimate
                # detour is needed or exposed before Start Work.
                inspection = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/start-inspection", headers=headers,
                )
                assert inspection.status_code in (409, 422), inspection.text
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/start", headers=headers,
                ))
                work = _assert_ok(await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-work-execution", headers=headers,
                ))
                checklist = work.get("checklist") or {}
                instance_id = checklist.get("instance_id")
                if instance_id:
                    for item in checklist.get("items", []):
                        body = {"response_value": {"value": "yes"}}
                        if item.get("evidence_required"):
                            body["evidence"] = [{"file_id": str(uuid.uuid4())}]
                        _assert_ok(await client.post(
                            f"/v1/staff/service-jobs/checklist-instances/{instance_id}/responses/{item['id']}",
                            headers=headers, json=body,
                        ))
                assert _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/finish", headers=headers,
                ))["status"] == "work_done"

                proof = _assert_ok(await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof", headers=headers,
                ))
                _assert_ok(await client.put(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/draft", headers=headers,
                    json={"resolution_summary": "AC serviced and tested.",
                          "final_service_notes": "Fixed-price certification completed."},
                ))
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/evidence", headers=headers,
                    json={"category": "after", "file_id": str(uuid.uuid4())},
                ))
                for check in proof["definition"].get("final_checks", []):
                    body = {"response_value": {"value": "yes"}}
                    if check.get("evidence_required"):
                        body["evidence"] = [{"file_id": str(uuid.uuid4())}]
                    _assert_ok(await client.post(
                        f"/v1/staff/service-jobs/checklist-instances/{check['instance_id']}/responses/{check['id']}",
                        headers=headers, json=body,
                    ))
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/submit", headers=headers,
                ))
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/request-handover",
                    headers=headers,
                ))
                payment_detail = _assert_ok(await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment", headers=headers,
                ))
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/declare", headers=headers,
                    json={"amount": payment_detail["amount"]["expected_amount"], "method": "onsite_cash"},
                ))

                active["user"] = _context("customer", CUSTOMER_ID)
                _assert_ok(await client.post(
                    f"/v1/customer/service-jobs/{job_id}/acknowledge-handover", headers=headers,
                ))
                payments = _assert_ok(await client.get(
                    "/v1/customer/direct-payments", headers=headers,
                ))["items"]
                payment = next(p for p in payments if p["job_id"] == job_id)
                _assert_ok(await client.post(
                    f"/v1/customer/direct-payments/{payment['payment_id']}/confirm", headers=headers,
                ))

                active["user"] = _context("technician", TECHNICIAN_USER_ID, TENANT_ID)
                assert _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/finalize", headers=headers,
                ))["status"] == "completed"
                rows = (await connection.execute(text(
                    "SELECT credit_delta FROM usage_credit_ledger WHERE job_id=:job "
                    "AND event_type='completed_job_deduction'"
                ), {"job": uuid.UUID(job_id)})).scalars().all()
                assert len(rows) == 1 and rows[0] < 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if outer.is_active:
                await outer.rollback()
    await engine.dispose()
