"""Populate a Home Services provider workspace with demo operating data.

Creates the data the tenant portal's Customers / Staff & Technicians /
Bookings & Jobs / Dispatch screens read, for ONE tenant, so those screens can
be exercised with realistic content instead of empty states:

  * 6 customers (users with role=customer) plus their per-tenant health rows,
    which is what the customer directory and the commerce customer list are
    both built from.
  * 4 team members (3 technicians + 1 supervisor) with logins, Mon-Sat
    availability, supported offerings and both service areas, plus a seat
    entitlement so the technicians sit inside the paid seat limit.
  * 10 bookings, each with the draft row the real customer flow would have
    produced, and 10 jobs spread across the REAL execution statuses
    (app.engines.execution.constants) so every Bookings & Jobs stage and both
    Dispatch columns have something in them.
  * Assignment rows for the assigned jobs, so Dispatch shows a current
    assignment and technician workload is not empty.

Idempotent: every row is keyed and skipped when already present, so re-running
changes nothing. Only INSERTs -- it never deletes or truncates.

Run:  python scripts/seed_tenant_portal_demo.py [--tenant "<business name>"]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.auth.utils import hash_password

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos"
)
FORBIDDEN_ENVIRONMENTS = {"production", "prod", "live", "staging-live"}
DEFAULT_TENANT = "Barha auto store"
DEMO_PASSWORD = "Password123!"
SEED_KEY = "tenant_portal_demo"

# Demo customers. Emails are @demo.local so they can never collide with a real
# signup and are trivially greppable if this data is ever cleaned out.
CUSTOMERS = [
    ("Harpreet Kaur",   "harpreet.kaur@demo.local",  "+919041100011", "healthy",  92.0),
    ("Manjit Singh",    "manjit.singh@demo.local",   "+919041100012", "healthy",  88.0),
    ("Simran Bedi",     "simran.bedi@demo.local",    "+919041100013", "standard", 78.0),
    ("Rohit Sharma",    "rohit.sharma@demo.local",   "+919041100014", "standard", 74.0),
    ("Anjali Verma",    "anjali.verma@demo.local",   "+919041100015", "cautious", 61.0),
    ("Gurdeep Sandhu",  "gurdeep.sandhu@demo.local", "+919041100016", "healthy",  90.0),
]

# (full_name, email, phone, member_type, designation, make_login)
TEAM = [
    ("Jaspreet Singh", "jaspreet.tech@demo.local", "+919041200021", "technician", "Senior Technician",  True),
    ("Amandeep Kumar", "amandeep.tech@demo.local", "+919041200022", "technician", "Technician",         True),
    ("Ravi Thakur",    "ravi.tech@demo.local",     "+919041200023", "technician", "Technician",         True),
    ("Neha Chopra",    "neha.super@demo.local",    "+919041200024", "staff",      "Service Supervisor", False),
]

ADDRESSES = [
    ("bassi pathana", "140412", "H.No. 45, Guru Nanak Nagar", "Near Civil Hospital"),
    ("bassi pathana", "140412", "SCO 12, Main Bazaar", "Above State Bank"),
    ("sirhind", "140406", "House 221, Model Colony", "Opposite Gurudwara"),
    ("sirhind", "140406", "Plot 8, Industrial Area", "Gate No. 2"),
]

# (suffix, job status, assignment status, technician index or None, day offset, booking status)
PLAN = [
    ("0001", "pending_assignment", "unassigned", None, 0, "converted"),
    ("0002", "pending_assignment", "unassigned", None, 1, "converted"),
    ("0003", "assigned", "assigned", 0, 0, "converted"),
    ("0004", "scheduled", "assigned", 1, 0, "converted"),
    ("0005", "on_the_way", "assigned", 0, 0, "converted"),
    ("0006", "service_started", "assigned", 2, 0, "converted"),
    ("0007", "work_done", "assigned", 1, -1, "converted"),
    ("0008", "completed", "assigned", 0, -2, "converted"),
    ("0009", "completed", "assigned", 2, -5, "converted"),
    ("0010", "cancelled", "unassigned", None, 2, "cancelled"),
]
WINDOWS = ["09:00-11:00", "11:00-13:00", "14:00-16:00", "16:00-18:00"]


def _guard() -> None:
    env = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "local").lower()
    if env in FORBIDDEN_ENVIRONMENTS:
        raise SystemExit(f"Refusing to seed demo data in environment '{env}'.")
    if any(marker in DATABASE_URL for marker in (".rds.", ".amazonaws.com", "prod-")):
        raise SystemExit("Refusing to seed demo data against a managed/production database URL.")


async def run(tenant_name: str) -> None:
    _guard()
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    created = {"customers": 0, "team": 0, "bookings": 0, "jobs": 0, "assignments": 0}
    skipped = {"customers": 0, "team": 0, "jobs": 0}

    async with Session() as db:
        tenant = (await db.execute(text(
            "SELECT id, business_name FROM tenants WHERE business_name = :n LIMIT 1"
        ), {"n": tenant_name})).first()
        if not tenant:
            raise SystemExit(f"No tenant named '{tenant_name}'.")
        tenant_id, business_name = tenant[0], tenant[1]
        print(f"Tenant: {business_name} ({tenant_id})")

        services = (await db.execute(text(
            "SELECT id, master_service_id, category_id, job_type_id FROM tenant_services "
            "WHERE tenant_id = :t AND is_active AND deleted_at IS NULL ORDER BY created_at"
        ), {"t": str(tenant_id)})).all()
        if not services:
            raise SystemExit("Tenant has no active services -- nothing to book against.")
        category_id = services[0][2]
        areas = [r[0] for r in (await db.execute(text(
            "SELECT id FROM tenant_service_areas WHERE tenant_id = :t"
        ), {"t": str(tenant_id)})).all()]
        print(f"  {len(services)} active services, {len(areas)} service areas")

        # -- 1. Customers ---------------------------------------------------
        customer_ids: list[uuid.UUID] = []
        for name, email, phone, band, score in CUSTOMERS:
            existing = (await db.execute(text(
                "SELECT id FROM users WHERE email = :e"), {"e": email})).scalar_one_or_none()
            if existing:
                customer_ids.append(existing)
                skipped["customers"] += 1
            else:
                cid = uuid.uuid4()
                await db.execute(text(
                    "INSERT INTO users (id, email, phone, full_name, hashed_password, role, "
                    "is_active, is_verified, created_at, updated_at) "
                    "VALUES (:id, :e, :p, :n, :pw, 'customer', true, true, now(), now())"
                ), {"id": str(cid), "e": email, "p": phone, "n": name,
                    "pw": hash_password(DEMO_PASSWORD)})
                customer_ids.append(cid)
                created["customers"] += 1
                print(f"[CREATE] customer {name}")

            # Per-tenant health row -- what the tenant customer list joins on.
            has_health = (await db.execute(text(
                "SELECT id FROM customer_health_scores WHERE customer_id = :c AND tenant_id = :t"
            ), {"c": str(customer_ids[-1]), "t": str(tenant_id)})).scalar_one_or_none()
            if not has_health:
                await db.execute(text(
                    "INSERT INTO customer_health_scores (id, customer_id, tenant_id, score, band, "
                    "can_book, computed_at, created_at, updated_at) "
                    "VALUES (:id, :c, :t, :s, :b, true, now(), now(), now())"
                ), {"id": str(uuid.uuid4()), "c": str(customer_ids[-1]),
                    "t": str(tenant_id), "s": score, "b": band})
        await db.commit()

        # -- 2. Team members ------------------------------------------------
        # Every ENABLED offering needs at least one ready technician or the
        # provider stays unbookable (READY_TECHNICIAN_MISSING) -- see
        # team_readiness_service.compute_service_coverage. A small shop
        # covers its whole catalogue, so give each technician all of it.
        offering_ids = json.dumps([str(s[0]) for s in services])
        area_ids = json.dumps([str(a) for a in areas])
        member_ids: list[uuid.UUID | None] = []
        for full_name, email, phone, member_type, designation, make_login in TEAM:
            member = (await db.execute(text(
                "SELECT id FROM provider_team_members WHERE tenant_id = :t AND email = :e "
                "AND deleted_at IS NULL LIMIT 1"
            ), {"t": str(tenant_id), "e": email})).scalar_one_or_none()
            if member:
                # Re-runnable repair: keep an existing member's service and area
                # coverage in step with the catalogue rather than leaving a
                # half-covered roster behind.
                await db.execute(text(
                    "UPDATE provider_team_members SET supported_offering_ids = CAST(:off AS jsonb), "
                    "service_area_ids = CAST(:areas AS jsonb), updated_at = now() WHERE id = :id"
                ), {"off": offering_ids, "areas": area_ids, "id": str(member)})
                member_ids.append(member)
                skipped["team"] += 1
                continue

            user_id = None
            if make_login:
                user_id = (await db.execute(text(
                    "SELECT id FROM users WHERE email = :e"), {"e": email})).scalar_one_or_none()
                if not user_id:
                    user_id = uuid.uuid4()
                    await db.execute(text(
                        "INSERT INTO users (id, email, phone, full_name, hashed_password, role, "
                        "tenant_id, is_active, is_verified, created_at, updated_at) "
                        "VALUES (:id, :e, :p, :n, :pw, 'technician', :t, true, true, now(), now())"
                    ), {"id": str(user_id), "e": email, "p": phone, "n": full_name,
                        "pw": hash_password(DEMO_PASSWORD), "t": str(tenant_id)})

            member = uuid.uuid4()
            await db.execute(text(
                "INSERT INTO provider_team_members "
                "(id, tenant_id, category_id, user_id, member_type, full_name, phone, email, "
                " designation, status, can_receive_assignment, supported_offering_ids, "
                " supported_type_ids, supported_brand_ids, service_area_ids, max_concurrent_jobs, "
                " availability_state, created_at, updated_at) "
                "VALUES (:id, :t, :cid, :uid, :mtype, :n, :p, :e, :d, 'active', :assignable, "
                " CAST(:off AS jsonb), '[]'::jsonb, '[]'::jsonb, CAST(:areas AS jsonb), 4, "
                " 'available', now(), now())"
            ), {"id": str(member), "t": str(tenant_id), "cid": str(category_id),
                "uid": str(user_id) if user_id else None, "mtype": member_type,
                "n": full_name, "p": phone, "e": email, "d": designation,
                "assignable": member_type == "technician",
                "off": offering_ids, "areas": area_ids})

            for dow in range(0, 6):
                await db.execute(text(
                    "INSERT INTO provider_availability_rules "
                    "(id, tenant_id, scope_type, scope_id, category_id, day_of_week, start_time, "
                    " end_time, slot_duration_minutes, max_bookings_per_slot, is_active, "
                    " break_start_time, break_end_time, max_jobs_per_day, timezone, created_at, updated_at) "
                    "VALUES (:id, :t, 'staff_member', :sid, :cid, :dow, '09:00', '18:00', 60, 1, "
                    " true, '13:00', '14:00', 6, 'Asia/Kolkata', now(), now())"
                ), {"id": str(uuid.uuid4()), "t": str(tenant_id), "sid": str(member),
                    "cid": str(category_id), "dow": dow})

            member_ids.append(member)
            created["team"] += 1
            print(f"[CREATE] team member {full_name} ({designation})")

        # Seat entitlement so the technicians sit inside the paid seat limit
        # rather than tripping the over-limit bookability blocker.
        technicians_count = sum(1 for m in TEAM if m[3] == "technician")
        seat_row = (await db.execute(text(
            "SELECT id FROM tenant_topup_entitlements WHERE tenant_id = :t AND status = 'active' "
            "AND meta ->> 'seed_key' = :k LIMIT 1"
        ), {"t": str(tenant_id), "k": SEED_KEY})).scalar_one_or_none()
        if not seat_row:
            await db.execute(text(
                "INSERT INTO tenant_topup_entitlements (id, tenant_id, seats, credit_granted, "
                " credit_expired, validity_days, starts_at, expires_at, status, meta, created_at, updated_at) "
                "VALUES (:id, :t, :seats, 0, 0, 0, now(), NULL, 'active', CAST(:meta AS jsonb), now(), now())"
            ), {"id": str(uuid.uuid4()), "t": str(tenant_id), "seats": technicians_count,
                "meta": json.dumps({"seed_key": SEED_KEY, "purpose": "demo_capacity"})})
            print(f"[CREATE] seat entitlement for {technicians_count} technicians")
        await db.commit()

        # -- 3. Bookings + jobs across the real execution statuses ----------
        today = date.today()
        techs = [m for m, spec in zip(member_ids, TEAM) if spec[3] == "technician" and m]

        for idx, (suffix, status, assign_status, tech_idx, day_offset, booking_status) in enumerate(PLAN):
            job_number = f"BAS-JOB-{suffix}"
            if (await db.execute(text("SELECT id FROM service_jobs WHERE job_number = :j"),
                                 {"j": job_number})).scalar_one_or_none():
                skipped["jobs"] += 1
                continue

            tenant_service_id, master_service_id, _cat, job_type_id = services[idx % len(services)]
            customer_id = customer_ids[idx % len(customer_ids)]
            city, zipcode, line1, landmark = ADDRESSES[idx % len(ADDRESSES)]
            address = json.dumps({"line1": line1, "landmark": landmark, "city": city,
                                  "state": "Punjab", "zipcode": zipcode})
            scheduled = today + timedelta(days=day_offset)
            window = WINDOWS[idx % len(WINDOWS)]
            staff_id = techs[tech_idx] if tech_idx is not None and tech_idx < len(techs) else None

            draft_id = uuid.uuid4()
            await db.execute(text(
                "INSERT INTO home_service_booking_drafts (id, customer_id, category_id, offering_id, "
                " selected_tenant_id, status, city, zipcode, address_snapshot, created_at, updated_at) "
                "VALUES (:id, :cust, :cat, :off, :t, :dstatus, :city, :zip, CAST(:addr AS jsonb), now(), now())"
            ), {"id": str(draft_id), "cust": str(customer_id), "cat": str(category_id),
                "off": str(master_service_id), "t": str(tenant_id),
                "dstatus": "cancelled" if booking_status == "cancelled" else "converted",
                "city": city, "zip": zipcode, "addr": address})

            booking_id = uuid.uuid4()
            await db.execute(text(
                "INSERT INTO service_bookings (id, booking_number, draft_id, customer_id, tenant_id, "
                " category_id, offering_id, job_type_id, city, zipcode, address_snapshot, status, "
                " assignment_status, created_at, updated_at) "
                "VALUES (:id, :bnum, :did, :cust, :t, :cat, :off, :jtid, :city, :zip, "
                " CAST(:addr AS jsonb), :bstatus, :astatus, now() - make_interval(days => :age_days), now())"
            ), {"id": str(booking_id), "bnum": f"BAS-BK-{suffix}", "did": str(draft_id),
                "cust": str(customer_id), "t": str(tenant_id), "cat": str(category_id),
                "off": str(master_service_id), "jtid": str(job_type_id), "city": city,
                "zip": zipcode, "addr": address, "bstatus": booking_status,
                "astatus": assign_status, "age_days": idx + 1})
            created["bookings"] += 1

            completion = None
            if status == "completed":
                completion = json.dumps({
                    "work_summary": "Serviced the unit, replaced worn parts, tested on site.",
                    "collected_amount": 1450 + idx * 75,
                    "completion_notes": "Customer confirmed the unit is working.",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                })

            job_id = uuid.uuid4()
            await db.execute(text(
                "INSERT INTO service_jobs (id, job_number, booking_id, customer_id, tenant_id, "
                " category_id, offering_id, job_type_id, assigned_staff_id, scheduled_date, "
                " scheduled_time_window, city, zipcode, address_snapshot, status, assignment_status, "
                " completion_data, reschedule_count, is_emergency, created_at, updated_at) "
                "VALUES (:id, :jn, :bid, :cust, :t, :cat, :off, :jtid, :staff, :sched, :window, "
                " :city, :zip, CAST(:addr AS jsonb), :status, :astatus, CAST(:completion AS jsonb), "
                " 0, false, now() - make_interval(days => :age_days), now())"
            ), {"id": str(job_id), "jn": job_number, "bid": str(booking_id),
                "cust": str(customer_id), "t": str(tenant_id), "cat": str(category_id),
                "off": str(master_service_id), "jtid": str(job_type_id),
                "staff": str(staff_id) if staff_id else None,
                "sched": scheduled, "window": window, "city": city, "zip": zipcode,
                "addr": address, "status": status, "astatus": assign_status,
                "completion": completion, "age_days": idx + 1})
            created["jobs"] += 1

            if staff_id:
                await db.execute(text(
                    "INSERT INTO service_job_assignments (id, job_id, booking_id, tenant_id, "
                    " assigned_staff_member_id, assignment_status, assignment_type, scheduled_date, "
                    " scheduled_time_window, is_current, accepted_at, created_at, updated_at) "
                    "VALUES (:id, :job, :booking, :t, :staff, :astatus, 'manual', :sched, :window, "
                    " true, now(), now(), now())"
                ), {"id": str(uuid.uuid4()), "job": str(job_id), "booking": str(booking_id),
                    "t": str(tenant_id), "staff": str(staff_id),
                    "astatus": "completed" if status == "completed" else "accepted",
                    "sched": scheduled, "window": window})
                created["assignments"] += 1

            print(f"[CREATE] job {job_number} status={status} "
                  f"staff={'yes' if staff_id else 'no'} scheduled={scheduled}")

        await db.commit()

    await engine.dispose()
    print("\nCreated: " + ", ".join(f"{k}={v}" for k, v in created.items()))
    print("Skipped (already present): " + ", ".join(f"{k}={v}" for k, v in skipped.items()))
    print(f"Demo logins use password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default=DEFAULT_TENANT, help="tenant business_name to seed")
    args = ap.parse_args()
    asyncio.run(run(args.tenant))
