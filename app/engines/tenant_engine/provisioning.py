"""
Tenant Engine — Provisioning
Real Postgres schema creation per tenant, engine-specific migrations,
seed data per vertical, all in a single atomic transaction.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import tenant_schema_name
from app.engines.tenant_engine.constants import DEFAULT_ENGINES_BY_VERTICAL, PLAN_LIMITS

logger = structlog.get_logger("tenant.provisioning")
utcnow = lambda: datetime.now(timezone.utc)


# ── Default seed data per vertical ────────────────────────────────────────────
DEFAULT_SERVICES = {
    "home_services": [
        {"name": "AC Servicing", "category": "hvac", "has_types": True, "has_brands": True,
         "types": ["Window", "Split", "Cassette", "Tower"], "duration_minutes": 90},
        {"name": "AC Installation", "category": "hvac", "has_types": True, "has_brands": True,
         "types": ["Window", "Split"], "duration_minutes": 180},
        {"name": "AC Gas Refill", "category": "hvac", "has_types": False, "has_brands": False,
         "duration_minutes": 60},
        {"name": "Electrical Inspection", "category": "electrical", "has_types": True, "has_brands": False,
         "types": ["Residential", "Commercial"], "duration_minutes": 60},
        {"name": "Plumbing Repair", "category": "plumbing", "has_types": False, "has_brands": False,
         "duration_minutes": 90},
    ],
    "salon": [
        {"name": "Haircut", "category": "hair", "has_types": True, "has_brands": False,
         "types": ["Men", "Women", "Kids"], "duration_minutes": 30},
        {"name": "Hair Color", "category": "hair", "has_types": True, "has_brands": True,
         "types": ["Full", "Highlights", "Balayage"], "duration_minutes": 120},
        {"name": "Facial", "category": "skin", "has_types": True, "has_brands": False,
         "types": ["Basic", "Deep Cleansing", "Anti-Aging"], "duration_minutes": 60},
        {"name": "Manicure", "category": "nails", "has_types": False, "has_brands": False,
         "duration_minutes": 45},
        {"name": "Pedicure", "category": "nails", "has_types": False, "has_brands": False,
         "duration_minutes": 60},
    ],
    "cafe": [
        {"name": "Espresso", "category": "coffee", "duration_minutes": 5},
        {"name": "Cappuccino", "category": "coffee", "duration_minutes": 7},
        {"name": "Cold Brew", "category": "coffee", "duration_minutes": 5},
        {"name": "Club Sandwich", "category": "food", "duration_minutes": 15},
        {"name": "Waffles", "category": "food", "duration_minutes": 12},
    ],
    "real_estate": [
        {"name": "Property Valuation", "category": "valuation", "duration_minutes": 60},
        {"name": "Site Visit", "category": "viewing", "duration_minutes": 90},
        {"name": "Documentation Support", "category": "legal", "duration_minutes": 120},
    ],
}

DEFAULT_SLA_HOURS = {
    "home_services": 4,
    "salon": 1,
    "cafe": 0,
    "real_estate": 24,
}

DEFAULT_NOTIFICATION_EVENTS = [
    "booking.confirmed", "booking.cancelled", "booking.reminder_24h", "booking.reminder_1h",
    "job.assigned", "job.en_route", "job.arrived", "job.completed",
    "job.quote_sent", "job.invoice_generated", "job.payment_collected",
    "payment.successful", "payment.failed",
    "review.requested", "staff.invited",
]


async def provision_tenant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant_name: str,
    vertical: str,
    plan_type: str,
    engines_to_enable: list[str],
    engine_configs: dict,
    owner_email: str,
    admin_id: uuid.UUID,
) -> dict:
    """
    Complete tenant provisioning in one atomic transaction.
    Steps:
      1. Create Postgres schema
      2. Run engine table migrations in that schema
      3. Seed default data (services, notification templates, SLA config)
      4. Returns provisioning summary
    """
    schema = tenant_schema_name(str(tenant_id))
    logger.info("provisioning.start", tenant_id=str(tenant_id), schema=schema, vertical=vertical)

    try:
        # Step 1: Create schema
        await db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        logger.info("provisioning.schema_created", schema=schema)

        # Step 2: Create tenant-scoped tables in the schema
        await _create_tenant_tables(db, schema)
        logger.info("provisioning.tables_created", schema=schema)

        # Step 3: Seed default data
        await _seed_service_catalog(db, schema, vertical, tenant_id)
        await _seed_notification_templates(db, schema, tenant_id, vertical)
        await _seed_zones(db, schema, tenant_id)
        await _seed_sla_config(db, schema, tenant_id, vertical)
        logger.info("provisioning.seed_complete", schema=schema)

        return {
            "schema": schema,
            "tables_created": True,
            "services_seeded": len(DEFAULT_SERVICES.get(vertical, [])),
            "notification_templates": len(DEFAULT_NOTIFICATION_EVENTS),
            "engines_enabled": len(engines_to_enable),
        }

    except Exception as e:
        logger.error("provisioning.failed", tenant_id=str(tenant_id), error=str(e))
        raise


async def _create_tenant_tables(db: AsyncSession, schema: str) -> None:
    """Create tenant-scoped tables. Each engine will add its own tables in later phases."""
    tables_sql = f"""
    -- Tenant settings (used by Settings Engine)
    CREATE TABLE IF NOT EXISTS "{schema}".tenant_settings (
        key VARCHAR(100) PRIMARY KEY,
        value JSONB NOT NULL DEFAULT '{{}}',
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Service catalog (used by Pricing Engine + Field Ops + Booking)
    CREATE TABLE IF NOT EXISTS "{schema}".services (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        category VARCHAR(100),
        has_types BOOLEAN DEFAULT FALSE,
        has_brands BOOLEAN DEFAULT FALSE,
        duration_minutes INTEGER DEFAULT 60,
        is_active BOOLEAN DEFAULT TRUE,
        sort_order INTEGER DEFAULT 0,
        meta JSONB DEFAULT '{{}}',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Service types (e.g., Window/Split for AC)
    CREATE TABLE IF NOT EXISTS "{schema}".service_types (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        service_id UUID NOT NULL REFERENCES "{schema}".services(id) ON DELETE CASCADE,
        type_name VARCHAR(100) NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE
    );

    -- Notification templates
    CREATE TABLE IF NOT EXISTS "{schema}".notification_templates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_type VARCHAR(100) NOT NULL UNIQUE,
        title_template TEXT NOT NULL,
        body_template TEXT NOT NULL,
        channels JSONB DEFAULT '["push"]',
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- SLA configuration
    CREATE TABLE IF NOT EXISTS "{schema}".sla_config (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        service_category VARCHAR(100) DEFAULT 'default',
        sla_hours INTEGER NOT NULL DEFAULT 4,
        escalation_hours INTEGER DEFAULT 6,
        auto_close_after_hours INTEGER DEFAULT 48,
        require_before_photo BOOLEAN DEFAULT TRUE,
        require_after_photo BOOLEAN DEFAULT TRUE,
        require_customer_approval BOOLEAN DEFAULT TRUE,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Service zones
    CREATE TABLE IF NOT EXISTS "{schema}".service_zones (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        zone_name VARCHAR(100) NOT NULL,
        zipcodes JSONB DEFAULT '[]',
        zone_multiplier DECIMAL(4,2) DEFAULT 1.00,
        travel_surcharge DECIMAL(10,2) DEFAULT 0.00,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Staff (populated by Auth Engine when staff logs in)
    CREATE TABLE IF NOT EXISTS "{schema}".staff_profiles (
        user_id UUID PRIMARY KEY,
        zone_id UUID REFERENCES "{schema}".service_zones(id),
        skills JSONB DEFAULT '[]',
        brand_certifications JSONB DEFAULT '[]',
        is_available BOOLEAN DEFAULT TRUE,
        rating DECIMAL(3,2) DEFAULT 0.00,
        jobs_completed INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    await db.execute(text(tables_sql))


async def _seed_service_catalog(
    db: AsyncSession, schema: str, vertical: str, tenant_id: uuid.UUID
) -> None:
    services = DEFAULT_SERVICES.get(vertical, [])
    for svc in services:
        svc_id = uuid.uuid4()
        await db.execute(text(f"""
            INSERT INTO "{schema}".services (id, name, category, has_types, has_brands, duration_minutes)
            VALUES (:id, :name, :category, :has_types, :has_brands, :duration_minutes)
            ON CONFLICT DO NOTHING
        """), {
            "id": str(svc_id),
            "name": svc["name"],
            "category": svc.get("category", "general"),
            "has_types": svc.get("has_types", False),
            "has_brands": svc.get("has_brands", False),
            "duration_minutes": svc.get("duration_minutes", 60),
        })

        # Seed types
        for i, type_name in enumerate(svc.get("types", [])):
            await db.execute(text(f"""
                INSERT INTO "{schema}".service_types (service_id, type_name, sort_order)
                VALUES (:service_id, :type_name, :sort_order)
                ON CONFLICT DO NOTHING
            """), {"service_id": str(svc_id), "type_name": type_name, "sort_order": i})


async def _seed_notification_templates(
    db: AsyncSession, schema: str, tenant_id: uuid.UUID, vertical: str
) -> None:
    templates = [
        ("booking.confirmed", "Booking Confirmed!", "Hi {customer_name}, your {service_name} is confirmed for {date_time}."),
        ("booking.cancelled", "Booking Cancelled", "Your booking for {service_name} has been cancelled."),
        ("booking.reminder_24h", "Reminder: Tomorrow's Appointment", "Reminder: {service_name} tomorrow at {time}."),
        ("booking.reminder_1h", "Your appointment starts in 1 hour", "{staff_name} is ready for your {service_name} at {time}."),
        ("job.assigned", "Technician Assigned", "{staff_name} has been assigned to your job."),
        ("job.en_route", "Technician On The Way", "{staff_name} is on the way. ETA: {eta} minutes."),
        ("job.arrived", "Technician Arrived", "{staff_name} has arrived at your location."),
        ("job.completed", "Service Complete", "Your {service_name} has been completed. Rate your experience."),
        ("job.quote_sent", "Quote Ready for Approval", "Your technician has sent a quote of {amount}. Tap to approve."),
        ("job.invoice_generated", "Invoice Generated", "Your invoice for {amount} is ready. Tap to pay."),
        ("job.payment_collected", "Payment Confirmed", "Thank you! Payment of {amount} received."),
        ("payment.successful", "Payment Successful", "Your payment of {amount} was successful."),
        ("payment.failed", "Payment Failed", "Your payment of {amount} failed. Please retry."),
        ("review.requested", "How was your experience?", "Please rate your {service_name} experience with {staff_name}."),
        ("staff.invited", "You've Been Invited", "You've been invited to join {tenant_name} on ServiceOS."),
    ]
    for event_type, title, body in templates:
        await db.execute(text(f"""
            INSERT INTO "{schema}".notification_templates (event_type, title_template, body_template)
            VALUES (:event_type, :title, :body)
            ON CONFLICT (event_type) DO NOTHING
        """), {"event_type": event_type, "title": title, "body": body})


async def _seed_zones(db: AsyncSession, schema: str, tenant_id: uuid.UUID) -> None:
    """Seed a default service zone (tenant customizes later)."""
    await db.execute(text(f"""
        INSERT INTO "{schema}".service_zones (zone_name, zipcodes, zone_multiplier, travel_surcharge)
        VALUES ('Default Zone', '[]', 1.00, 0.00)
        ON CONFLICT DO NOTHING
    """))


async def _seed_sla_config(
    db: AsyncSession, schema: str, tenant_id: uuid.UUID, vertical: str
) -> None:
    sla_hours = DEFAULT_SLA_HOURS.get(vertical, 4)
    await db.execute(text(f"""
        INSERT INTO "{schema}".sla_config (service_category, sla_hours, auto_close_after_hours)
        VALUES ('default', :sla_hours, :auto_close)
        ON CONFLICT DO NOTHING
    """), {"sla_hours": sla_hours, "auto_close": sla_hours * 12})


async def drop_tenant_schema(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Hard delete — only call on confirmed termination."""
    schema = tenant_schema_name(str(tenant_id))
    await db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    logger.warning("provisioning.schema_dropped", schema=schema, tenant_id=str(tenant_id))
