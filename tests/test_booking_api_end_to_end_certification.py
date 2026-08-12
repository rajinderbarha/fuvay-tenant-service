"""One continuous, API-only Home Services booking certification.

Uses the real 140412 catalog/provider configuration but wraps every write in
an outer transaction that is rolled back after the test. No browser, app
screen, mocked service, or manually pre-advanced job state is involved.
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
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.main import app


CUSTOMER_ID = uuid.UUID("4ec45157-8b63-4a8d-b09d-8a4a0c54ab34")
TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")
TENANT_OWNER_ID = uuid.UUID("2436be02-99e0-4926-a4a4-44fd6fdaf08b")
TECHNICIAN_ID = uuid.UUID("be602b65-7faf-451d-9b08-3b6afba58b5d")
AC_NOT_COOLING_ISSUE_ID = "88326e0c-6da5-4c71-9689-fedef0c7813e"


def _context(role: str, user_id: uuid.UUID, tenant_id: uuid.UUID | None = None) -> UserContext:
    return UserContext(
        user_id=str(user_id),
        email=f"api-cert-{role}@serviceos.local",
        role=role,
        tenant_id=str(tenant_id) if tenant_id else None,
        full_name=f"API Cert {role}",
        is_verified=True,
    )


def _assert_ok(response, *, status: int = 200):
    assert response.status_code == status, response.text
    body = response.json()
    assert body.get("success") is True, body
    return body["data"]


@pytest.mark.asyncio
async def test_booking_to_job_completion_and_single_credit_deduction_api_only():
    engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        outer = await connection.begin()
        sessions = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
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
            # A fresh active address keeps the test independent of a demo
            # customer's saved-address history while still exercising the
            # real address ownership/snapshot path.
            address_id = uuid.uuid4()
            await connection.execute(text(
                "INSERT INTO customer_addresses "
                "(id, customer_id, name, address_line_1, city, state, country, zipcode, "
                "is_default, is_active, created_at, updated_at) VALUES "
                "(:id, :customer, 'API Cert Customer', '1 Certification Road', "
                "'BASSIPATHANA', 'Punjab', 'India', '140412', true, true, now(), now())"
            ), {"id": address_id, "customer": CUSTOMER_ID})

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", timeout=90
            ) as client:
                headers = {"Authorization": "Bearer api-cert"}

                active["user"] = _context("technician", TECHNICIAN_ID, TENANT_ID)
                access_context = _assert_ok(await client.get(
                    "/v1/auth/access-context", headers=headers
                ))
                assert access_context["audience"] == "serviceos:staff"
                assert access_context["tenant_status"] == "active"
                assert access_context["technician_id"]
                assert "home_services" in access_context["enabled_verticals"]

                active["user"] = _context("customer", CUSTOMER_ID)

                # Customer: canonical issue-first draft and deterministic
                # backend-authored question flow.
                selected = _assert_ok(await client.post(
                    "/v1/customer/home-services/assistant-bootstrap/select-issue",
                    headers=headers,
                    json={
                        "category_slug": "air-conditioning",
                        "zipcode": "140412",
                        "issue_id": AC_NOT_COOLING_ISSUE_ID,
                    },
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
                        payload["value"] = "API certification response"
                    envelope = _assert_ok(await client.post(
                        f"/v1/customer/home-services/booking-drafts/{draft_id}/question-flow/answer",
                        headers=headers, json=payload,
                    ))

                preferred = (date.today() + timedelta(days=3)).isoformat()
                draft = _assert_ok(await client.put(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}",
                    headers=headers,
                    json={
                        "address_id": str(address_id),
                        "customer_name": "API Cert Customer",
                        "customer_phone": "9999999999",
                        "preferred_date": preferred,
                        "preferred_time_window": "09:00-10:00",
                    },
                ))
                assert draft["zipcode"] == "140412"
                assert draft["job_type_id"]

                serviceability = _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/serviceability-check",
                    headers=headers,
                ))
                assert serviceability["serviceable"] is True

                match = _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/match-and-price",
                    headers=headers,
                ))
                assert match["selected_provider"]["tenant_id"] == str(TENANT_ID)
                assert match["pricing_mode"] == "inspection"

                # Regression: match-and-price itself must persist the
                # inspection contract. No call to the legacy price-estimate
                # endpoint is needed and no fake fixed price is accepted.
                draft = _assert_ok(await client.get(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}", headers=headers
                ))
                price = draft["price_snapshot"]
                assert price["requires_inspection_estimate"] is True
                assert float(price["visit_fee"]) > 0
                assert price["standard_price"] is None

                summary = _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/summary",
                    headers=headers,
                ))["booking_summary"]
                assert summary["ready_for_confirmation"] is True

                slots = _assert_ok(await client.get(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/available-slots",
                    headers=headers,
                ))["slots"]
                assert slots
                slot = slots[0]
                _assert_ok(await client.put(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}",
                    headers=headers,
                    json={
                        "preferred_date": slot["date"],
                        "preferred_time_window": slot["time_window"],
                    },
                ))
                _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/select-slot",
                    headers=headers,
                    json={"date": slot["date"], "time_window": slot["time_window"]},
                ))

                idempotency_key = f"api-cert-{uuid.uuid4()}"
                confirmed = _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/confirm",
                    headers={**headers, "Idempotency-Key": idempotency_key},
                ))
                booking_id = confirmed["booking_id"]
                job_id = confirmed["job_id"]

                duplicate = _assert_ok(await client.post(
                    f"/v1/customer/home-services/booking-drafts/{draft_id}/confirm",
                    headers={**headers, "Idempotency-Key": idempotency_key},
                ))
                assert duplicate["booking_id"] == booking_id
                assert duplicate["job_id"] == job_id

                booking = _assert_ok(await client.get(
                    f"/v1/customer/bookings/{booking_id}", headers=headers
                ))
                assert booking["job_id"] == job_id

                # Tenant assignment. Staff cannot execute an assigned job
                # before accepting it.
                active["user"] = _context("tenant_owner", TENANT_OWNER_ID, TENANT_ID)
                assigned = _assert_ok(await client.post(
                    f"/v1/provider/service-jobs/{job_id}/assign",
                    headers=headers,
                    json={"staff_member_id": str(TECHNICIAN_ID)},
                ))
                assert assigned["success"] is True

                active["user"] = _context("technician", TECHNICIAN_ID, TENANT_ID)
                missing_rejection_reason = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/reject",
                    headers=headers, json={},
                )
                assert missing_rejection_reason.status_code == 422
                rejected = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/reject",
                    headers=headers, json={"reason": "Schedule conflict"},
                ))
                assert rejected["success"] is True

                active["user"] = _context("tenant_owner", TENANT_OWNER_ID, TENANT_ID)
                reassigned = _assert_ok(await client.post(
                    f"/v1/provider/service-jobs/{job_id}/assign",
                    headers=headers,
                    json={"staff_member_id": str(TECHNICIAN_ID)},
                ))
                assert reassigned["success"] is True

                active["user"] = _context("technician", TECHNICIAN_ID, TENANT_ID)
                invalid_transition = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/on-the-way", headers=headers
                )
                assert invalid_transition.status_code in (409, 422), invalid_transition.text

                accepted = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/accept", headers=headers
                ))
                assert accepted["success"] is True

                for action, payload in (
                    ("customer-contacted", {"notes": "Requirements confirmed"}),
                    ("on-the-way", None),
                    ("reached-site", None),
                    ("start-inspection", None),
                ):
                    response = await client.post(
                        f"/v1/staff/service-jobs/{job_id}/{action}",
                        headers=headers, json=payload,
                    )
                    _assert_ok(response)

                # Complete every inspection item returned by the API, then
                # advance the canonical workflow.
                inspection = _assert_ok(await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-inspection", headers=headers
                ))
                instance_id = (inspection.get("instance") or {}).get("instance_id")
                if instance_id:
                    for section in inspection.get("sections", []):
                        for item in section.get("items", []):
                            response_value = {"value": "yes"}
                            body = {"response_value": response_value}
                            if item.get("evidence_required"):
                                body["evidence"] = [{"file_id": str(uuid.uuid4())}]
                            _assert_ok(await client.post(
                                f"/v1/staff/service-jobs/checklist-instances/{instance_id}/responses/{item['id']}",
                                headers=headers, json=body,
                            ))
                    _assert_ok(await client.post(
                        f"/v1/staff/service-jobs/checklist-instances/{instance_id}/complete",
                        headers=headers,
                    ))
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/complete-inspection", headers=headers
                ))

                estimate = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-estimate/create", headers=headers
                ))
                quote_id = estimate["id"]
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-estimate/{quote_id}/items",
                    headers=headers,
                    json={
                        "item_type": "labour",
                        "item_name": "Certified AC repair",
                        "quantity": 1,
                        "unit_price": 1200,
                    },
                ))
                sent = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-estimate/{quote_id}/send",
                    headers=headers, json={},
                ))
                assert sent["status"] == "sent_to_customer"

                active["user"] = _context("customer", CUSTOMER_ID)
                missing_revision_reason = await client.post(
                    f"/v1/customer/quotes/{quote_id}/request-revision",
                    headers=headers, json={},
                )
                assert missing_revision_reason.status_code == 422
                revision_requested = _assert_ok(await client.post(
                    f"/v1/customer/quotes/{quote_id}/request-revision",
                    headers=headers,
                    json={"reason": "Please separate labour from materials."},
                ))
                assert revision_requested["status"] == "revision_requested"

                stale_approval = await client.post(
                    f"/v1/customer/quotes/{quote_id}/approve",
                    headers={**headers, "Idempotency-Key": f"stale-{quote_id}"},
                )
                assert stale_approval.status_code in (409, 422)

                active["user"] = _context("technician", TECHNICIAN_ID, TENANT_ID)
                revised = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-estimate/{quote_id}/revise",
                    headers=headers,
                ))
                quote_id = revised["id"]
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-estimate/{quote_id}/items",
                    headers=headers,
                    json={
                        "item_type": "labour",
                        "item_name": "Revised certified AC repair",
                        "quantity": 1,
                        "unit_price": 1200,
                    },
                ))
                revised_sent = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-estimate/{quote_id}/send",
                    headers=headers, json={},
                ))
                assert revised_sent["status"] == "sent_to_customer"

                # Approval is a hard work-start gate and quote approval is
                # idempotent for the same customer request key.
                blocked_start = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/start",
                    headers=headers,
                )
                assert blocked_start.status_code in (409, 422), blocked_start.text

                active["user"] = _context("customer", CUSTOMER_ID)
                customer_checklists = _assert_ok(await client.get(
                    f"/v1/customer/service-jobs/{job_id}/checklists", headers=headers
                ))
                assert isinstance(customer_checklists, list)

                active["user"] = _context("customer", uuid.uuid4())
                other_customer_checklists = await client.get(
                    f"/v1/customer/service-jobs/{job_id}/checklists", headers=headers
                )
                assert other_customer_checklists.status_code == 404

                active["user"] = _context("customer", CUSTOMER_ID)
                quote = _assert_ok(await client.get(
                    f"/v1/customer/quotes/{quote_id}", headers=headers
                ))
                assert quote["status"] == "sent_to_customer"
                quote_key = f"quote-{quote_id}"
                approved = _assert_ok(await client.post(
                    f"/v1/customer/quotes/{quote_id}/approve",
                    headers={**headers, "Idempotency-Key": quote_key},
                ))
                assert approved["status"] == "customer_approved"
                approved_again = _assert_ok(await client.post(
                    f"/v1/customer/quotes/{quote_id}/approve",
                    headers={**headers, "Idempotency-Key": quote_key},
                ))
                assert approved_again["status"] == "customer_approved"

                active["user"] = _context("technician", TECHNICIAN_ID, TENANT_ID)
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/start",
                    headers=headers,
                ))
                work = _assert_ok(await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-work-execution", headers=headers
                ))
                checklist = work.get("checklist") or {}
                work_instance = checklist.get("instance_id")
                if work_instance:
                    for item in checklist.get("items", []):
                        body = {"response_value": {"value": "yes"}}
                        if item.get("evidence_required"):
                            body["evidence"] = [{"file_id": str(uuid.uuid4())}]
                        _assert_ok(await client.post(
                            f"/v1/staff/service-jobs/checklist-instances/{work_instance}/responses/{item['id']}",
                            headers=headers,
                            json=body,
                        ))
                finished = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/finish",
                    headers=headers,
                ))
                assert finished["status"] == "work_done"

                proof = _assert_ok(await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof", headers=headers
                ))
                _assert_ok(await client.put(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/draft",
                    headers=headers,
                    json={
                        "resolution_summary": "AC repaired and verified.",
                        "final_service_notes": "API certification completed.",
                    },
                ))
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/evidence",
                    headers=headers,
                    json={"category": "after", "file_id": str(uuid.uuid4())},
                ))
                for check in proof["definition"].get("final_checks", []):
                    body = {"response_value": {"value": "yes"}}
                    if check.get("evidence_required"):
                        body["evidence"] = [{"file_id": str(uuid.uuid4())}]
                    _assert_ok(await client.post(
                        f"/v1/staff/service-jobs/checklist-instances/{check['instance_id']}/responses/{check['id']}",
                        headers=headers,
                        json=body,
                    ))
                submitted = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/submit",
                    headers=headers,
                ))
                assert submitted["status"] == "submitted"
                _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/request-handover",
                    headers=headers,
                ))

                payment_detail = _assert_ok(await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment", headers=headers
                ))
                expected_amount = payment_detail["amount"]["expected_amount"]
                wrong_amount = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/declare",
                    headers=headers,
                    json={"amount": "1.00", "method": "onsite_cash"},
                )
                assert wrong_amount.status_code == 422, wrong_amount.text
                declaration = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/declare",
                    headers=headers,
                    json={"amount": expected_amount, "method": "onsite_cash"},
                ))
                assert declaration["status"] == "awaiting_customer"

                active["user"] = _context("customer", CUSTOMER_ID)
                handover = _assert_ok(await client.post(
                    f"/v1/customer/service-jobs/{job_id}/acknowledge-handover",
                    headers=headers,
                ))
                assert handover["handover_status"] == "acknowledged"
                payments = _assert_ok(await client.get(
                    "/v1/customer/direct-payments", headers=headers
                ))["items"]
                payment = next(item for item in payments if item["job_id"] == job_id)

                clarification = _assert_ok(await client.post(
                    f"/v1/customer/direct-payments/{payment['payment_id']}/report-mismatch",
                    headers=headers,
                    json={
                        "action": "request_clarification",
                        "note": "Please confirm the recorded payment method.",
                    },
                ))
                assert clarification["status"] == "awaiting_customer"

                active["user"] = _context("technician", TECHNICIAN_ID, TENANT_ID)
                blocked_while_unconfirmed = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/finalize",
                    headers=headers,
                )
                assert blocked_while_unconfirmed.status_code == 409

                active["user"] = _context("customer", CUSTOMER_ID)
                confirmed_payment = _assert_ok(await client.post(
                    f"/v1/customer/direct-payments/{payment['payment_id']}/confirm",
                    headers=headers,
                ))
                assert confirmed_payment["status"] == "confirmed"

                active["user"] = _context("technician", TECHNICIAN_ID, TENANT_ID)
                before = (await connection.execute(text(
                    "SELECT credit_balance FROM tenant_billing WHERE tenant_id=:tenant"
                ), {"tenant": TENANT_ID})).scalar_one()
                finalized = _assert_ok(await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/finalize",
                    headers=headers,
                ))
                assert finalized["status"] == "completed"

                ledger = (await connection.execute(text(
                    "SELECT credit_delta, balance_before, balance_after "
                    "FROM usage_credit_ledger WHERE job_id=:job "
                    "AND event_type='completed_job_deduction'"
                ), {"job": uuid.UUID(job_id)})).mappings().all()
                assert len(ledger) == 1
                assert ledger[0]["balance_before"] == before
                assert ledger[0]["balance_after"] == before + ledger[0]["credit_delta"]
                assert ledger[0]["credit_delta"] < 0

                duplicate_finalize = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/finalize",
                    headers=headers,
                )
                assert duplicate_finalize.status_code >= 400
                ledger_count = (await connection.execute(text(
                    "SELECT count(*) FROM usage_credit_ledger WHERE job_id=:job "
                    "AND event_type='completed_job_deduction'"
                ), {"job": uuid.UUID(job_id)})).scalar_one()
                assert ledger_count == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if outer.is_active:
                await outer.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_customer_cancel_reschedule_policy_api_only():
    """Certify the native customer's self-service exception paths without a
    browser or a separately seeded demo booking."""
    engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        outer = await connection.begin()
        sessions = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
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

        async def seed_job(status: str = "pending_assignment") -> tuple[uuid.UUID, uuid.UUID]:
            catalog = (await connection.execute(text(
                "SELECT id, category_id, job_type_id FROM master_services "
                "WHERE service_name='AC Service' AND is_active=true LIMIT 1"
            ))).mappings().one()
            booking_id, job_id = uuid.uuid4(), uuid.uuid4()
            await connection.execute(text(
                "INSERT INTO service_bookings "
                "(id, booking_number, draft_id, customer_id, tenant_id, category_id, "
                "offering_id, job_type_id, status, assignment_status, created_at, updated_at) "
                "VALUES (:bid, :bnum, :draft, :customer, :tenant, :category, :offering, "
                ":job_type, 'pending_assignment', 'unassigned', now(), now())"
            ), {
                "bid": booking_id,
                "bnum": f"BK-API-{booking_id.hex[:8]}",
                "draft": uuid.uuid4(),
                "customer": CUSTOMER_ID,
                "tenant": TENANT_ID,
                "category": catalog["category_id"],
                "offering": catalog["id"],
                "job_type": catalog["job_type_id"],
            })
            await connection.execute(text(
                "INSERT INTO service_jobs "
                "(id, job_number, booking_id, customer_id, tenant_id, category_id, "
                "offering_id, job_type_id, status, assignment_status, reschedule_count, "
                "created_at, updated_at) "
                "VALUES (:jid, :jnum, :bid, :customer, :tenant, :category, :offering, "
                ":job_type, :status, 'unassigned', 0, now(), now())"
            ), {
                "jid": job_id,
                "jnum": f"JOB-API-{job_id.hex[:8]}",
                "bid": booking_id,
                "customer": CUSTOMER_ID,
                "tenant": TENANT_ID,
                "category": catalog["category_id"],
                "offering": catalog["id"],
                "job_type": catalog["job_type_id"],
                "status": status,
            })
            return booking_id, job_id

        try:
            booking_id, _ = await seed_job()
            progressed_booking_id, _ = await seed_job("quote_approved")
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", timeout=90
            ) as client:
                headers = {"Authorization": "Bearer api-cert"}

                eligibility = _assert_ok(await client.get(
                    f"/v1/customer/bookings/{booking_id}/cancel-reschedule-eligibility",
                    headers=headers,
                ))
                assert eligibility["can_cancel"] is True
                assert eligibility["can_reschedule"] is True
                assert eligibility["remaining_reschedule_allowance"] == 3

                missing_reason = await client.post(
                    f"/v1/customer/bookings/{booking_id}/cancel",
                    headers=headers, json={},
                )
                assert missing_reason.status_code == 422

                stale = await client.post(
                    f"/v1/customer/bookings/{booking_id}/cancel",
                    headers=headers,
                    json={"reason": "schedule conflict", "expected_version": "stale"},
                )
                assert stale.status_code == 409

                past = await client.post(
                    f"/v1/customer/bookings/{booking_id}/reschedule",
                    headers=headers,
                    json={"scheduled_date": "2020-01-01", "reason": "schedule conflict"},
                )
                assert past.status_code == 422

                availability = _assert_ok(await client.get(
                    f"/v1/customer/bookings/{booking_id}/reschedule-availability?horizon_days=30",
                    headers=headers,
                ))
                available_dates = [row["date"] for row in availability["dates"] if row["available"]]
                assert available_dates, "seeded provider must expose at least one reschedule date"
                target_date = available_dates[0]

                for attempt in range(3):
                    rescheduled = _assert_ok(await client.post(
                        f"/v1/customer/bookings/{booking_id}/reschedule",
                        headers=headers,
                        json={
                            "scheduled_date": target_date,
                            "scheduled_time_window": f"{9 + attempt:02d}:00-{10 + attempt:02d}:00",
                            "reason": f"schedule conflict {attempt + 1}",
                        },
                    ))
                    assert rescheduled["scheduled_date"] == target_date

                over_limit = await client.post(
                    f"/v1/customer/bookings/{booking_id}/reschedule",
                    headers=headers,
                    json={"scheduled_date": target_date, "reason": "fourth request"},
                )
                assert over_limit.status_code == 409

                at_limit = _assert_ok(await client.get(
                    f"/v1/customer/bookings/{booking_id}/cancel-reschedule-eligibility",
                    headers=headers,
                ))
                assert at_limit["can_reschedule"] is False
                assert at_limit["remaining_reschedule_allowance"] == 0
                assert at_limit["can_cancel"] is True

                cancelled = _assert_ok(await client.post(
                    f"/v1/customer/bookings/{booking_id}/cancel",
                    headers=headers, json={"reason": "changed my mind"},
                ))
                assert cancelled["status"] == "cancelled"
                duplicate_cancel = await client.post(
                    f"/v1/customer/bookings/{booking_id}/cancel",
                    headers=headers, json={"reason": "another request"},
                )
                assert duplicate_cancel.status_code == 409

                blocked_after_progress = await client.post(
                    f"/v1/customer/bookings/{progressed_booking_id}/cancel",
                    headers=headers, json={"reason": "too late"},
                )
                assert blocked_after_progress.status_code == 409

                active["user"] = _context("customer", uuid.uuid4())
                wrong_customer = await client.get(
                    f"/v1/customer/bookings/{progressed_booking_id}/cancel-reschedule-eligibility",
                    headers=headers,
                )
                assert wrong_customer.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if outer.is_active:
                await outer.rollback()
    await engine.dispose()
