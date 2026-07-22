"""FINAL-L5-01 — Canonical deterministic seed for Level-5 testing baseline.

Idempotent, re-runnable, environment-guarded. Creates the canonical
platform users, tenant, tenant users, staff, customers, pricing rules,
provider setup/coverage, usage credit ledger (with exactly-once completed
job deduction), deterministic job lifecycle scenarios, notifications, and
a minimal audit trail — per the FINAL-L5-01 mission specification.

Does NOT reset/truncate data itself — see scripts/reset_final_l5_01.py
for the destructive reset step. This script only INSERTs (idempotently,
via existence checks) and is safe to run against an already-seeded DB.

Run: python scripts/canonical_seed_final_l5_01.py
"""
from __future__ import annotations
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.auth.utils import hash_password
from app.core.permissions import ROLE_PERMISSIONS

ALLOWED_ENVIRONMENTS = {"local", "development", "dev", "test", "e2e", "certification"}
FORBIDDEN_ENVIRONMENTS = {"production", "prod", "staging-live", "live"}
FORBIDDEN_HOST_MARKERS = (".amazonaws.com", ".azure.com", ".gcp.com", "prod-", ".rds.")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

# Canonical test password — NOT printed to any report. Documented only in the
# ignored local credential file (.backups/final-l5-01/e2e_credentials.local.txt).
CANONICAL_TEST_PASSWORD = "CanonicalL5!2026"

TENANT_SLUG = "demo-ac-services"
TENANT_B_SLUG = "isolation-test-services"


def _safety_guard() -> None:
    env = os.getenv("APP_ENV", "development").lower()
    allow = os.getenv("ALLOW_DATABASE_RESET", "false").lower() == "true"
    if env in FORBIDDEN_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} is forbidden. Aborting."); sys.exit(1)
    if env not in ALLOWED_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} not in allow-list {ALLOWED_ENVIRONMENTS}. Aborting."); sys.exit(1)
    if not allow:
        print("[REFUSED] ALLOW_DATABASE_RESET != true. Aborting."); sys.exit(1)
    if any(m in DATABASE_URL for m in FORBIDDEN_HOST_MARKERS):
        print("[REFUSED] DATABASE_URL host looks managed/cloud/production. Aborting."); sys.exit(1)
    masked = DATABASE_URL.split("@")[-1]
    print(f"[OK] Safety guard passed. APP_ENV={env}, target=...@{masked}")


# admin@serviceos.local is a pre-existing hardcoded auth fixture consumed by
# tests/test_trust_quality_phase1.py and tests/test_p0_sidebar_duplicate_cleanup.py
# (ADMIN_EMAIL/ADMIN_PASS constants). Its password must stay "Password123!" —
# NOT the canonical test password — or those pre-existing tests regress.
# Documented, not silently overridden: this is the one deliberate exception.
LEGACY_FIXTURE_PASSWORDS = {"admin@serviceos.local": "Password123!"}


# Not a second hardcoded list -- derived from the one authoritative
# registry (app.core.permissions.ROLE_PERMISSIONS) so the two can never
# drift apart. tests/test_phase2d_tenant_access_model.py asserts this
# equals the 10-role set.
CANONICAL_ROLES = frozenset(ROLE_PERMISSIONS.keys())


def _require_canonical_role(role: str) -> None:
    """Fail closed before any database call. Slice 2F-39 fix for a gap
    2F-38 found where this function had zero role validation at all.
    """
    if not role or role not in CANONICAL_ROLES:
        raise ValueError(
            f"non-canonical role {role!r}: seed scripts may only create users "
            f"with one of the 10 canonical roles {sorted(ROLE_PERMISSIONS.keys())}. "
            f"Aliases/designations (manager, readonly, tenant_manager, "
            f"tenant_readonly, etc.) are never valid role values."
        )


async def get_or_create_user(db, email, full_name, role, tenant_id=None, platform_role=None, is_active=True):
    _require_canonical_role(role)
    row = (await db.execute(text("SELECT id, role FROM users WHERE email = :e"), {"e": email})).first()
    if row:
        existing_id, existing_role = row[0], row[1]
        if existing_role != role:
            print(f"[SKIP]   user {email} (exists, role mismatch: requested {role!r} "
                  f"but existing row has {existing_role!r} -- NOT modified; "
                  f"seed scripts never promote/change an existing user's role)")
        else:
            print(f"[SKIP]   user {email} (exists)")
        return existing_id
    uid = uuid.uuid4()
    password = LEGACY_FIXTURE_PASSWORDS.get(email, CANONICAL_TEST_PASSWORD)
    await db.execute(text("""
        INSERT INTO users (id, email, full_name, role, tenant_id, hashed_password,
                            is_active, is_verified, onboarding_complete, platform_role,
                            account_status, created_at, updated_at)
        VALUES (:id, :email, :name, :role, :tid, :pw, true, true, true, :prole,
                'active', now(), now())
    """), {"id": str(uid), "email": email, "name": full_name, "role": role,
            "tid": str(tenant_id) if tenant_id else None,
            "pw": hash_password(password), "prole": platform_role})
    print(f"[CREATE] user {email} ({role})")
    return uid


async def run():
    _safety_guard()
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    created = {"users": 0, "tenants": 0, "pricing_rules": 0, "coverage": 0, "jobs": 0,
               "ledger": 0, "notifications": 0}

    async with async_session() as db:
        # ── 1. Platform users ───────────────────────────────────────────────
        super_admin = await get_or_create_user(db, "admin@serviceos.local", "Platform Super Admin",
                                                "super_admin", platform_role="super_admin")
        admin_ops = await get_or_create_user(db, "admin.ops@serviceos.local", "Admin Operations User",
                                              "super_admin", platform_role="operations")
        admin_finance = await get_or_create_user(db, "admin.finance@serviceos.local", "Admin Finance User",
                                                  "super_admin", platform_role="finance")
        admin_readonly = await get_or_create_user(db, "admin.readonly@serviceos.local", "Admin Read Only User",
                                                   "super_admin", platform_role="read_only")

        # ── 2. Tenant A: Demo AC Services (active, bookable) ────────────────
        trow = (await db.execute(text("SELECT id, status FROM tenants WHERE slug = :s"), {"s": TENANT_SLUG})).first()
        if trow and trow[1] == "active":
            tenant_id = trow[0]
            print(f"[SKIP]   tenant {TENANT_SLUG} (already active)")
        elif trow:
            tenant_id = trow[0]
            await db.execute(text("""
                UPDATE tenants SET status='active', verification_status='verified',
                       is_discoverable=true, activated_at=now(), updated_at=now()
                WHERE id=:tid
            """), {"tid": str(tenant_id)})
            print(f"[UPDATE] tenant {TENANT_SLUG} -> active/verified/discoverable")
        else:
            tenant_id = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO tenants (id, tenant_name, business_name, slug, vertical, status,
                                      verification_status, city, state, country, zipcode,
                                      is_discoverable, activated_at, created_at, updated_at)
                VALUES (:id, 'Demo AC Services', 'Demo AC Services', :slug, 'home_services', 'active',
                        'verified', 'Ludhiana', 'Punjab', 'India', '141001', true, now(), now(), now())
            """), {"id": str(tenant_id), "slug": TENANT_SLUG})
            created["tenants"] += 1
            print(f"[CREATE] tenant {TENANT_SLUG} (active)")

        # ── 2b. Tenant B: Isolation Test Services (for Part 13 isolation tests) ──
        trow_b = (await db.execute(text("SELECT id FROM tenants WHERE slug = :s"), {"s": TENANT_B_SLUG})).first()
        if trow_b:
            tenant_b_id = trow_b[0]
            print(f"[SKIP]   tenant {TENANT_B_SLUG} (exists)")
        else:
            tenant_b_id = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO tenants (id, tenant_name, business_name, slug, vertical, status,
                                      verification_status, city, state, country, zipcode,
                                      is_discoverable, activated_at, created_at, updated_at)
                VALUES (:id, 'Isolation Test Services', 'Isolation Test Services', :slug, 'home_services',
                        'active', 'verified', 'Ludhiana', 'Punjab', 'India', '141002', true, now(), now(), now())
            """), {"id": str(tenant_b_id), "slug": TENANT_B_SLUG})
            created["tenants"] += 1
            print(f"[CREATE] tenant {TENANT_B_SLUG} (active, isolation test only)")

        # ── 3. Tenant A users: Owner / Manager / Read Only ──────────────────
        owner = await get_or_create_user(db, "owner@demo-ac-services.local", "Tenant Owner",
                                          "tenant_owner", tenant_id=tenant_id)
        # manager@/readonly@demo-ac-services.local are intentionally NOT
        # (re)created here. Slice 2F-38/2F-39 found this script previously
        # hardcoded "tenant_manager"/"tenant_readonly" -- neither is a
        # canonical role -- which is exactly how the two known
        # MANUAL_ROLE_CONFIRMATION_REQUIRED demo accounts came to exist.
        # No canonical replacement value is authorized (no evidence-backed
        # mapping exists; see docs/workflow-rearchitecture/phase-02a-slice-02f38/
        # manual-role-confirmation-request.md) and this script must not
        # guess one. Once a human decision is recorded, update this seed
        # accordingly -- do not restore the old literals.
        await db.execute(text("UPDATE tenants SET owner_user_id=:o WHERE id=:t AND owner_user_id IS NULL"),
                          {"o": str(owner), "t": str(tenant_id)})

        # ── 3b. Tenant B user (isolation test owner only) ───────────────────
        owner_b = await get_or_create_user(db, "owner@isolation-test-services.local", "Isolation Tenant Owner",
                                            "tenant_owner", tenant_id=tenant_b_id)
        await db.execute(text("UPDATE tenants SET owner_user_id=:o WHERE id=:t AND owner_user_id IS NULL"),
                          {"o": str(owner_b), "t": str(tenant_b_id)})

        # ── 4. Staff (technicians) — Tenant A only ──────────────────────────
        tech1 = await get_or_create_user(db, "tech1@demo-ac-services.local", "Technician One",
                                          "technician", tenant_id=tenant_id)
        tech2 = await get_or_create_user(db, "tech2@demo-ac-services.local", "Technician Two",
                                          "technician", tenant_id=tenant_id)
        tech_inactive = await get_or_create_user(db, "tech.inactive@demo-ac-services.local",
                                                  "Technician Inactive", "technician", tenant_id=tenant_id)
        await db.execute(text("UPDATE users SET is_active=false, account_status='inactive' WHERE id=:u"),
                          {"u": str(tech_inactive)})

        # ── 5. Customers (platform-level, not tenant-scoped) ────────────────
        cust1 = await get_or_create_user(db, "customer1@serviceos.local", "Customer One", "customer")
        cust2 = await get_or_create_user(db, "customer2@serviceos.local", "Customer Two", "customer")

        await db.commit()

        # ── 6. Catalog lookups (already canonically seeded by prior sprints —
        #      verify presence, do not duplicate) ──────────────────────────
        ac_repair = (await db.execute(text("SELECT id FROM master_services WHERE slug='ac_repair'"))).scalar_one_or_none()
        split_ac = (await db.execute(text("SELECT id FROM service_types WHERE slug='split_ac'"))).scalar_one_or_none()
        window_ac = (await db.execute(text("SELECT id FROM service_types WHERE slug='window_ac'"))).scalar_one_or_none()
        lg = (await db.execute(text("SELECT id FROM brands WHERE slug='lg'"))).scalar_one_or_none()
        not_cooling = (await db.execute(text("SELECT id FROM master_issue_types WHERE slug='ac_not_cooling'"))).scalar_one_or_none()
        category_id = (await db.execute(text("SELECT category_id FROM master_services WHERE slug='ac_repair'"))).scalar_one_or_none()
        if not all([ac_repair, split_ac, window_ac, lg, not_cooling]):
            print("[FATAL] Required catalog entities missing (ac_repair/split_ac/window_ac/lg/ac_not_cooling). "
                  "Run scripts/seed_master_services.py, seed_brands.py, seed_ac_repair_baseline_mappings.py, "
                  "seed_issue_types.py first.")
            await engine.dispose()
            return
        print(f"[OK]     catalog verified: ac_repair={ac_repair}, split_ac={split_ac}, window_ac={window_ac}, "
              f"lg={lg}, not_cooling={not_cooling}")

        # ── 7. Canonical pricing rules: Split AC+LG and Window AC+LG, distinct ──
        async def upsert_rule(service_type_id, code, name, base, mn, mx, deduction):
            existing = (await db.execute(text("""
                SELECT id FROM service_pricing_rules
                WHERE rule_code = :code AND deleted_at IS NULL
            """), {"code": code})).scalar_one_or_none()
            if existing:
                print(f"[SKIP]   pricing_rule {code} (exists)")
                return existing
            rid = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO service_pricing_rules
                    (id, master_service_id, category_id, service_type_id, brand_id, job_type,
                     city, district, state, zipcode, pricing_model,
                     base_price, min_price, max_price, completed_job_deduction_credits,
                     rule_name, rule_code, priority, is_active, source, created_at, updated_at)
                VALUES
                    (:id, :svc, :cat, :typ, :brand, 'repair',
                     'Ludhiana', 'Ludhiana', 'Punjab', '141001', 'range',
                     :base, :mn, :mx, :ded,
                     :name, :code, 10, true, 'final_l5_01_canonical_seed', now(), now())
            """), {"id": str(rid), "svc": str(ac_repair), "cat": str(category_id), "typ": str(service_type_id),
                    "brand": str(lg), "base": base, "mn": mn, "mx": mx, "ded": deduction,
                    "name": name, "code": code})
            created["pricing_rules"] += 1
            print(f"[CREATE] pricing_rule {code}: {name} (Rs{mn}-{mx})")
            return rid

        rule_split = await upsert_rule(split_ac, "final_l5_01_split_ac_lg_141001",
                                        "AC Repair - Split AC - LG - Ludhiana 141001 (canonical)",
                                        775, 700, 850, 21)
        rule_window = await upsert_rule(window_ac, "final_l5_01_window_ac_lg_141001",
                                         "AC Repair - Window AC - LG - Ludhiana 141001 (canonical)",
                                         425, 350, 500, 15)

        # ── 7b. Ensure a master_offering exists for AC Repair (required FK for jobs) ──
        offering = (await db.execute(text("SELECT id FROM master_offerings WHERE slug='ac_repair_offering'"))
                    ).scalar_one_or_none()
        if not offering:
            offering = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO master_offerings
                    (id, category_id, name, slug, offering_class, default_pricing_model,
                     default_base_price, default_min_price, default_max_price, currency,
                     is_brand_required, is_type_required, status, is_active, created_at, updated_at)
                VALUES
                    (:id, :cat, 'AC Repair', 'ac_repair_offering', 'service', 'range',
                     775, 350, 850, 'INR', true, true, 'active', true, now(), now())
            """), {"id": str(offering), "cat": str(category_id)})
            print("[CREATE] master_offering: AC Repair")
        else:
            print("[SKIP]   master_offering: AC Repair (exists)")

        # ── 8. Tenant provider setup: enable AC Repair, Split AC, Window AC, LG ──
        if offering:
            enabled = (await db.execute(text("""
                SELECT id FROM provider_enabled_offerings WHERE tenant_id=:t AND offering_id=:o
            """), {"t": str(tenant_id), "o": str(offering)})).scalar_one_or_none()
            if not enabled:
                await db.execute(text("""
                    INSERT INTO provider_enabled_offerings
                        (id, tenant_id, offering_id, category_id, is_enabled, is_active, status,
                         readiness_status, supported_type_ids, supported_brand_ids,
                         provider_min_price, provider_max_price, activated_at, created_at, updated_at)
                    VALUES
                        (:id, :t, :o, :c, true, true, 'active', 'ready',
                         CAST(:types AS jsonb), CAST(:brands AS jsonb), 700, 850, now(), now(), now())
                """), {"id": str(uuid.uuid4()), "t": str(tenant_id), "o": str(offering), "c": str(category_id),
                        "types": f'["{split_ac}", "{window_ac}"]', "brands": f'["{lg}"]'})
                print("[CREATE] provider_enabled_offering: Demo AC Services -> AC Repair (Split+Window AC, LG)")
            else:
                print("[SKIP]   provider_enabled_offering (exists)")
        else:
            print("[WARN]   no master_offerings row found for AC Repair category — skipping provider offering seed")

        # ── 9. Service area coverage: 141001 active for Tenant A ────────────
        cov = (await db.execute(text(
            "SELECT id FROM tenant_service_areas WHERE tenant_id=:t AND zipcode='141001'"),
            {"t": str(tenant_id)})).scalar_one_or_none()
        if not cov:
            await db.execute(text("""
                INSERT INTO tenant_service_areas
                    (id, tenant_id, coverage_type, country, state, district, city, zipcode,
                     zone_name, priority, is_active, is_primary, created_at, updated_at)
                VALUES
                    (:id, :t, 'zipcode', 'India', 'Punjab', 'Ludhiana', 'Ludhiana', '141001',
                     'Ludhiana Central', 1, true, true, now(), now())
            """), {"id": str(uuid.uuid4()), "t": str(tenant_id)})
            created["coverage"] += 1
            print("[CREATE] tenant_service_area: 141001 (active, primary)")
        else:
            print("[SKIP]   tenant_service_area 141001 (exists)")

        # ── 10. Weekly availability rule (Mon-Sat 09:00-18:00, lunch break) ──
        avail = (await db.execute(text(
            "SELECT id FROM provider_availability_rules WHERE tenant_id=:t AND scope_type='tenant' LIMIT 1"),
            {"t": str(tenant_id)})).scalar_one_or_none()
        if not avail:
            for dow in range(0, 6):  # Mon-Sat
                await db.execute(text("""
                    INSERT INTO provider_availability_rules
                        (id, tenant_id, scope_type, category_id, day_of_week, start_time, end_time,
                         slot_duration_minutes, max_bookings_per_slot, is_active,
                         break_start_time, break_end_time, max_jobs_per_day, timezone, created_at, updated_at)
                    VALUES
                        (:id, :t, 'tenant', :c, :dow, '09:00', '18:00', 60, 2, true,
                         '13:00', '14:00', 12, 'Asia/Kolkata', now(), now())
                """), {"id": str(uuid.uuid4()), "t": str(tenant_id), "c": str(category_id), "dow": dow})
            print("[CREATE] provider_availability_rules: Mon-Sat 09:00-18:00 with 13:00-14:00 break")
        else:
            print("[SKIP]   provider_availability_rules (exists)")

        await db.commit()

        # ── 11. Usage credits: tenant_billing.credit_balance opening = 4000 ──
        billing = (await db.execute(text("SELECT id, credit_balance FROM tenant_billing WHERE tenant_id=:t"),
                                     {"t": str(tenant_id)})).first()
        if not billing:
            await db.execute(text("""
                INSERT INTO tenant_billing (id, tenant_id, billing_cycle, subscription_status,
                                             credit_balance, created_at, updated_at)
                VALUES (:id, :t, 'monthly', 'active', 4000, now(), now())
            """), {"id": str(uuid.uuid4()), "t": str(tenant_id)})
            opening_balance = Decimal("4000")
            print("[CREATE] tenant_billing: Demo AC Services opening credit_balance=4000")
        else:
            opening_balance = billing[1]
            print(f"[SKIP]   tenant_billing (exists, credit_balance={opening_balance})")

        # tenant_wallets intentionally NOT seeded with active data (dormant legacy per mission rule)

        await db.commit()

        # ── 12. Deterministic job lifecycle scenarios (5 jobs) ───────────────
        async def upsert_job(job_number, status, assignment_status, assigned=None, completion=None,
                              booking_status="converted", customer=None):
            customer = customer or cust1
            existing = (await db.execute(text(
                "SELECT id FROM service_jobs WHERE job_number=:jn"), {"jn": job_number})).scalar_one_or_none()
            if existing:
                print(f"[SKIP]   service_job {job_number} (exists)")
                return existing
            addr_json = '{"line1": "H.No. 123, Model Town", "city": "Ludhiana", "zipcode": "141001"}'

            # ── FINAL-L5-01D fix: service_jobs.booking_id must point at
            # service_bookings.id, matching the real application flow in
            # app/engines/final_records/creation_service.py (ServiceJob.booking_id
            # = booking.id where booking is a ServiceBooking). FINAL-L5-01's
            # original seed incorrectly pointed this at the generic `bookings`
            # table instead — see FINAL_L5_01D_BOOKING_SOURCE_DECISION_REPORT.md.
            # A minimal home_service_booking_drafts row is created first to
            # satisfy service_bookings.draft_id's NOT NULL FK, exactly as the
            # real customer booking flow would produce one.
            draft_id = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO home_service_booking_drafts
                    (id, customer_id, category_id, offering_id, selected_tenant_id, status,
                     city, zipcode, address_snapshot, created_at, updated_at)
                VALUES
                    (:id, :cust, :cat, :off, :t, 'converted', 'Ludhiana', '141001', CAST(:addr AS jsonb), now(), now())
            """), {"id": str(draft_id), "cust": str(customer), "cat": str(category_id),
                    "off": str(offering) if offering else None, "t": str(tenant_id), "addr": addr_json})

            booking_id = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO service_bookings
                    (id, booking_number, draft_id, customer_id, tenant_id, category_id, offering_id,
                     city, zipcode, address_snapshot, status, assignment_status, created_at, updated_at)
                VALUES
                    (:id, :bnum, :did, :cust, :t, :cat, :off, 'Ludhiana', '141001', CAST(:addr AS jsonb),
                     :bstatus, :astatus, now(), now())
            """), {"id": str(booking_id), "bnum": f"L501-BK-{job_number[-4:]}", "did": str(draft_id),
                    "cust": str(customer), "t": str(tenant_id), "cat": str(category_id),
                    "off": str(offering) if offering else None, "addr": addr_json,
                    "bstatus": booking_status, "astatus": assignment_status})

            jid = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO service_jobs
                    (id, job_number, booking_id, customer_id, tenant_id, category_id, offering_id,
                     assigned_staff_id, scheduled_date, scheduled_time_window, city, zipcode,
                     address_snapshot, status, assignment_status, completion_data, created_at, updated_at)
                VALUES
                    (:id, :jn, :bid, :cust, :t, :cat, :off, :staff, current_date, '10:00-12:00', 'Ludhiana', '141001',
                     :addr, :status, :astatus, :completion, now(), now())
            """), {"id": str(jid), "jn": job_number, "bid": str(booking_id), "cust": str(customer), "t": str(tenant_id),
                    "cat": str(category_id), "off": str(offering) if offering else None,
                    "staff": str(assigned) if assigned else None,
                    "addr": addr_json,
                    "status": status, "astatus": assignment_status, "completion": completion})
            created["jobs"] += 1
            print(f"[CREATE] service_job {job_number} (status={status}, service_booking={booking_id})")
            return jid

        job_new = await upsert_job("L501-JOB-0001", "new", "unassigned")
        job_assigned = await upsert_job("L501-JOB-0002", "assigned", "assigned", assigned=tech1)
        job_in_progress = await upsert_job("L501-JOB-0003", "in_progress", "assigned", assigned=tech1)
        job_completed = await upsert_job(
            "L501-JOB-0004", "completed", "assigned", assigned=tech2,
            completion='{"work_summary": "Replaced capacitor, cleaned filter, gas checked OK.", '
                       '"collected_amount": 775, "completion_notes": "Customer confirmed cooling restored.", '
                       '"technician": "Technician Two", "completed_at": "' +
                       datetime.now(timezone.utc).isoformat() + '"}')
        job_cancelled = await upsert_job("L501-JOB-0005", "cancelled", "unassigned", booking_status="cancelled")
        # FINAL-L5-02B: a separate booking for Customer Two, distinct from
        # Customer One's 5 jobs above -- needed for genuine bidirectional
        # customer-isolation proof (Customer One must not see this one,
        # Customer Two must not see Customer One's), not just "Customer Two
        # sees nothing" which only proves one direction.
        job_customer2 = await upsert_job(
            "L501-JOB-0006", "new", "unassigned", customer=cust2)

        await db.commit()

        # ── 13. Completed Job Deduction — exactly once, idempotent ──────────
        existing_deduction = (await db.execute(text("""
            SELECT id FROM usage_credit_ledger WHERE job_id=:j AND event_type='completed_job_deduction'
        """), {"j": str(job_completed)})).scalar_one_or_none()
        if not existing_deduction:
            current_balance = (await db.execute(text(
                "SELECT credit_balance FROM tenant_billing WHERE tenant_id=:t"), {"t": str(tenant_id)})).scalar_one()
            delta = Decimal("-21")
            new_balance = current_balance + delta
            await db.execute(text("""
                INSERT INTO usage_credit_ledger
                    (id, tenant_id, job_id, event_type, credit_delta, balance_before, balance_after,
                     deduction_source, service_id, service_type_id, brand_id, reason, created_at, updated_at)
                VALUES
                    (:id, :t, :j, 'completed_job_deduction', :delta, :before, :after,
                     'completed_job', :svc, :typ, :brand, 'Completed Job Deduction for L501-JOB-0004', now(), now())
            """), {"id": str(uuid.uuid4()), "t": str(tenant_id), "j": str(job_completed), "delta": delta,
                    "before": current_balance, "after": new_balance, "svc": str(ac_repair),
                    "typ": str(split_ac), "brand": str(lg)})
            await db.execute(text("UPDATE tenant_billing SET credit_balance=:b, updated_at=now() WHERE tenant_id=:t"),
                              {"b": new_balance, "t": str(tenant_id)})
            created["ledger"] += 1
            print(f"[CREATE] usage_credit_ledger: Completed Job Deduction {current_balance} -> {new_balance}")
        else:
            print("[SKIP]   Completed Job Deduction for L501-JOB-0004 (already applied, exactly-once preserved)")

        await db.commit()

        # ── 14. Notifications ────────────────────────────────────────────────
        async def upsert_notification(user_id, tenant_id_, ntype, title, body, read):
            existing = (await db.execute(text("""
                SELECT id FROM in_app_notifications WHERE user_id=:u AND notification_type=:nt AND title=:ti
            """), {"u": str(user_id), "nt": ntype, "ti": title})).scalar_one_or_none()
            if existing:
                print(f"[SKIP]   notification '{title}' for {user_id} (exists)")
                return
            await db.execute(text("""
                INSERT INTO in_app_notifications
                    (id, user_id, tenant_id, notification_type, title, body, severity,
                     read_status, read_at, created_at, updated_at)
                VALUES
                    (:id, :u, :t, :nt, :ti, :bo, 'info', :rs, :ra, now(), now())
            """), {"id": str(uuid.uuid4()), "u": str(user_id), "t": str(tenant_id_) if tenant_id_ else None,
                    "nt": ntype, "ti": title, "bo": body,
                    "rs": "read" if read else "unread", "ra": datetime.now(timezone.utc) if read else None})
            created["notifications"] += 1
            print(f"[CREATE] notification '{title}' -> {user_id} ({'read' if read else 'unread'})")

        await upsert_notification(super_admin, None, "system", "New tenant activated",
                                   "Demo AC Services has been activated and is now bookable.", read=True)
        await upsert_notification(owner, tenant_id, "job_completed", "Job L501-JOB-0004 completed",
                                   "Technician Two completed the AC repair job. 21 credits deducted.", read=False)
        await upsert_notification(cust1, None, "booking_update", "Your AC repair is complete",
                                   "Technician Two has completed your Split AC repair.", read=False)
        await upsert_notification(tech1, tenant_id, "job_assigned", "New job assigned",
                                   "You have been assigned job L501-JOB-0002.", read=True)

        await db.commit()
        print("\n[DONE] FINAL-L5-01 canonical seed complete.")
        print(f"[SUMMARY] {created}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
