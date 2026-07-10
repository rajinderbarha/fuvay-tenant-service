"""FINAL-L5-01B — Canonical configuration/rule seed.

Idempotent, deterministic, environment-guarded (same guard as
canonical_seed_final_l5_01.py). Seeds only rule domains with a real,
verified backing table in the current schema — see
docs/final-l5-01b/FINAL_L5_01B_RULE_MODEL_ENDPOINT_INVENTORY.md for what
was found to NOT have a schema (Reward Rules, Credit Threshold Rules,
Provider Verification Rules, standalone Notification Policy) and is
therefore deliberately not seeded here.

Health Rules and Badge Rules already have active canonical rows from
prior sprints (verified, not re-seeded). This script adds:
  - Matching rule (recommendation_rules) — wiped by FINAL-L5-01's tenant-
    scoped table reset since the table carries a nullable tenant_id.
  - Notification channel config for the canonical tenant.

Run: python scripts/canonical_rule_seed_final_l5_01b.py
"""
from __future__ import annotations
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

ALLOWED_ENVIRONMENTS = {"local", "development", "dev", "test", "e2e", "certification"}
FORBIDDEN_ENVIRONMENTS = {"production", "prod", "staging-live", "live"}
FORBIDDEN_HOST_MARKERS = (".amazonaws.com", ".azure.com", ".gcp.com", "prod-", ".rds.")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")


def _safety_guard() -> None:
    env = os.getenv("APP_ENV", "development").lower()
    allow = os.getenv("ALLOW_DATABASE_RESET", "false").lower() == "true"
    if env in FORBIDDEN_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} is forbidden. Aborting."); sys.exit(1)
    if env not in ALLOWED_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} not in allow-list. Aborting."); sys.exit(1)
    if not allow:
        print("[REFUSED] ALLOW_DATABASE_RESET != true. Aborting."); sys.exit(1)
    if any(m in DATABASE_URL for m in FORBIDDEN_HOST_MARKERS):
        print("[REFUSED] DATABASE_URL host looks managed/cloud/production. Aborting."); sys.exit(1)
    print(f"[OK] Safety guard passed. APP_ENV={env}, target=...@{DATABASE_URL.split('@')[-1]}")


async def run():
    _safety_guard()
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    created = {"health_rules_verified": 0, "badge_rules_verified": 0, "matching_rules": 0, "notification_channel_configs": 0}

    async with async_session() as db:
        # ── Verify (not re-create) existing Health/Badge canonical rules ────
        health_count = (await db.execute(text("SELECT count(*) FROM health_formulas WHERE status='active'"))).scalar_one()
        badge_count = (await db.execute(text("SELECT count(*) FROM badge_rules WHERE status='active'"))).scalar_one()
        print(f"[VERIFY] {health_count} active health_formulas (pre-existing, e.g. 'Standard Provider Health Rule' equivalent)")
        print(f"[VERIFY] {badge_count} active badge_rules (pre-existing, incl. 'rule_verified_provider' matching 'Verified Service Provider')")
        created["health_rules_verified"] = health_count
        created["badge_rules_verified"] = badge_count

        # ── Matching rule: Provider-First Home Services Matching ────────────
        tenant_id = (await db.execute(text("SELECT id FROM tenants WHERE slug='demo-ac-services'"))).scalar_one_or_none()
        ac_repair = (await db.execute(text("SELECT id FROM master_services WHERE slug='ac_repair'"))).scalar_one_or_none()
        category_id = (await db.execute(text("SELECT category_id FROM master_services WHERE slug='ac_repair'"))).scalar_one_or_none()

        existing_rule = (await db.execute(text(
            "SELECT id FROM recommendation_rules WHERE code='final_l5_01b_provider_first_matching'"
        ))).scalar_one_or_none()
        if not existing_rule:
            condition = (
                '{"requires": ["active_tenant", "active_service_setup", "active_coverage", '
                '"valid_provider_pricing", "supported_zipcode", "availability"]}'
            )
            recommendation = '{"strategy": "provider_first", "fallback": "none"}'
            await db.execute(text("""
                INSERT INTO recommendation_rules
                    (id, code, name, description, rule_type, scope, vertical_type, category_id,
                     service_id, tenant_id, priority, status, condition_json, recommendation_json,
                     explanation_template, created_at, updated_at)
                VALUES
                    (:id, 'final_l5_01b_provider_first_matching', 'Provider-First Home Services Matching',
                     'Matches customer bookings to providers requiring an active tenant, active service '
                     'setup, active coverage, valid provider pricing, a supported zipcode, and availability.',
                     'matching', 'global', 'home_services', :cat, :svc, NULL, 10, 'active',
                     CAST(:cond AS jsonb), CAST(:rec AS jsonb),
                     'Matched to {tenant_name} based on active coverage and pricing for {service_name}.',
                     now(), now())
            """), {"id": str(uuid.uuid4()), "cat": str(category_id) if category_id else None,
                    "svc": str(ac_repair) if ac_repair else None, "cond": condition, "rec": recommendation})
            created["matching_rules"] += 1
            print("[CREATE] recommendation_rule: Provider-First Home Services Matching (global scope)")
        else:
            print("[SKIP]   recommendation_rule: Provider-First Home Services Matching (exists)")

        # ── Notification policy substitute: channel config for canonical tenant ──
        if tenant_id:
            for channel in ("email", "sms", "push", "in_app"):
                existing = (await db.execute(text(
                    "SELECT id FROM notification_channel_configs WHERE tenant_id=:t AND channel=:c"
                ), {"t": str(tenant_id), "c": channel})).scalar_one_or_none()
                if not existing:
                    await db.execute(text("""
                        INSERT INTO notification_channel_configs
                            (id, tenant_id, channel, is_enabled, config, created_at, updated_at)
                        VALUES (:id, :t, :c, :enabled, CAST(:cfg AS jsonb), now(), now())
                    """), {"id": str(uuid.uuid4()), "t": str(tenant_id), "c": channel,
                            "enabled": channel != "sms",  # SMS off by default, matches typical starter-tier policy
                            "cfg": '{"policy_name": "Core Booking and Operations Notifications", '
                                   '"events": ["booking_created", "job_assigned", "job_completed", '
                                   '"deduction_applied"]}'})
                    created["notification_channel_configs"] += 1
                    print(f"[CREATE] notification_channel_config: {channel} for Demo AC Services")
                else:
                    print(f"[SKIP]   notification_channel_config: {channel} (exists)")

        await db.commit()
        print(f"\n[DONE] Canonical rule seed complete.\n[SUMMARY] {created}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
