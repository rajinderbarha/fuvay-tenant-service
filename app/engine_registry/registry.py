"""
ServiceOS — Engine Registry
The central registry of runtime engines.
Each engine self-registers at import time.
The registry provides:
  - Engine metadata (name, version, description, dependencies)
  - Enable/disable per tenant
  - Introspection endpoint: GET /v1/engines
  - Health status per engine
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


EngineType = Literal["core", "plugin"]


@dataclass
class EngineDefinition:
    """Metadata for a registered engine."""
    engine_id: str
    name: str
    description: str
    engine_type: EngineType
    version: str
    dependencies: list[str]          # Engine IDs this engine requires
    api_prefix: str                  # e.g. /v1/field-ops
    endpoint_count: int
    category: str                    # e.g. "operations", "scheduling", "ai"
    is_enabled_by_default: bool      # True for core engines

    # Runtime state (set after DB check)
    is_healthy: bool = True
    avg_latency_ms: float | None = None
    error_rate: float | None = None


class EngineRegistry:
    """
    Singleton registry loaded at startup.
    Each engine's router file calls registry.register(...) at module import.
    """

    def __init__(self) -> None:
        self._engines: dict[str, EngineDefinition] = {}

    def register(self, engine: EngineDefinition) -> None:
        self._engines[engine.engine_id] = engine

    def get(self, engine_id: str) -> EngineDefinition | None:
        return self._engines.get(engine_id)

    def all(self) -> list[EngineDefinition]:
        return list(self._engines.values())

    def core_engines(self) -> list[EngineDefinition]:
        return [e for e in self._engines.values() if e.engine_type == "core"]

    def plugin_engines(self) -> list[EngineDefinition]:
        return [e for e in self._engines.values() if e.engine_type == "plugin"]

    def is_registered(self, engine_id: str) -> bool:
        return engine_id in self._engines

    def summary(self) -> dict:
        return {
            "total": len(self._engines),
            "core": len(self.core_engines()),
            "plugin": len(self.plugin_engines()),
            "engines": [
                {
                    "engine_id": e.engine_id,
                    "name": e.name,
                    "type": e.engine_type,
                    "version": e.version,
                    "is_healthy": e.is_healthy,
                    "api_prefix": e.api_prefix,
                    "endpoint_count": e.endpoint_count,
                    "dependencies": e.dependencies,
                }
                for e in self._engines.values()
            ],
        }


# ── Global Singleton ──────────────────────────────────────────────────────────
registry = EngineRegistry()


def _seed_registry() -> None:
    """Register the canonical runtime engines at startup."""

    # ── CORE ENGINES ─────────────────────────────────────────────────────────
    CORE = [
        EngineDefinition(
            engine_id="auth",
            name="Auth & IAM Engine",
            description="JWT authentication, multi-tenant RBAC, refresh token rotation, MFA, impersonation, device sessions.",
            engine_type="core",
            version="2.4.1",
            dependencies=[],
            api_prefix="/v1/auth",
            endpoint_count=24,
            category="security",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="rag",
            name="RAG Engine",
            description="Per-tenant knowledge base, pgvector semantic search, async document ingestion, grounded AI chat with citations.",
            engine_type="core",
            version="1.8.3",
            dependencies=["auth", "media"],
            api_prefix="/v1/rag",
            endpoint_count=18,
            category="ai",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="notification",
            name="Notification Engine",
            description="Push (FCM/APNs), SMS (Twilio), Email (SendGrid), WhatsApp — template-driven, delivery tracking, retry.",
            engine_type="core",
            version="3.1.0",
            dependencies=["auth"],
            api_prefix="/v1/notifications",
            endpoint_count=22,
            category="messaging",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="payment",
            name="Payment Engine",
            description="Razorpay, Stripe, UPI — payment links, refunds, webhooks, invoice generation, multi-currency.",
            engine_type="core",
            version="2.2.0",
            dependencies=["auth"],
            api_prefix="/v1/payments",
            endpoint_count=20,
            category="finance",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="analytics",
            name="Analytics Engine",
            description="Real-time tenant KPIs, engine-level metrics, custom dashboards, CSV/Excel export.",
            engine_type="core",
            version="1.5.2",
            dependencies=["auth"],
            api_prefix="/v1/analytics",
            endpoint_count=16,
            category="data",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="media",
            name="Media Vault Engine",
            description="S3 presigned uploads, image compression, virus scan hook, before/after photo pairing for jobs.",
            engine_type="core",
            version="2.0.1",
            dependencies=["auth"],
            api_prefix="/v1/media",
            endpoint_count=14,
            category="storage",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="review",
            name="Review & Rating Engine",
            description="Customer reviews, star ratings, staff performance scores, response management, moderation queue.",
            engine_type="core",
            version="1.3.0",
            dependencies=["auth"],
            api_prefix="/v1/reviews",
            endpoint_count=12,
            category="engagement",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="chat",
            name="Chat Engine",
            description="Real-time WebSocket messaging, conversation threads, AI-assisted reply suggestions, read receipts, media in chat.",
            engine_type="core",
            version="2.1.0",
            dependencies=["auth", "media"],
            api_prefix="/v1/chat",
            endpoint_count=15,
            category="messaging",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="settings",
            name="Settings & Config Engine",
            description="Per-tenant configuration, branding (logo, colors, name), feature flags, business hours, localization.",
            engine_type="core",
            version="1.2.0",
            dependencies=["auth"],
            api_prefix="/v1/settings",
            endpoint_count=18,
            category="platform",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="service_catalog",
            name="Service Catalog Engine",
            description="Tenant-defined services replacing hardcoded service types — name, service_type "
                         "(repair/service/consultation), pricing model, base/max price, visit fee, "
                         "pre-approval limit, duration estimate, checklist flag.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth"],
            api_prefix="/v1/catalog",
            endpoint_count=6,
            category="operations",
            is_enabled_by_default=True,
        ),
    ]

    # ── PLUGIN ENGINES ────────────────────────────────────────────────────────
    PLUGINS = [
        EngineDefinition(
            engine_id="field_ops",
            name="Field Ops Engine",
            description="23-status job lifecycle, GPS tracking, customer approval (OTP + digital signature), photo evidence, real-time updates, PDF invoice export.",
            engine_type="plugin",
            version="3.0.0",
            dependencies=["auth", "notification", "media", "payment"],
            api_prefix="/v1/jobs",
            endpoint_count=47,
            category="operations",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="booking",
            name="Booking Engine",
            description="Online booking, slot management, buffer times, calendar sync, no-show handling, reschedule flows.",
            engine_type="plugin",
            version="2.3.0",
            dependencies=["auth", "notification"],
            api_prefix="/v1/bookings",
            endpoint_count=28,
            category="scheduling",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="appointment",
            name="Appointment Engine",
            description="Appointment lifecycle, pre/post reminders, rescheduling, no-show management, staff availability.",
            engine_type="plugin",
            version="1.9.0",
            dependencies=["auth", "notification", "booking"],
            api_prefix="/v1/appointments",
            endpoint_count=22,
            category="scheduling",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="leads",
            name="Leads CRM Engine",
            description="Lead capture, pipeline stages, follow-up automation, conversion tracking, team assignment.",
            engine_type="plugin",
            version="2.0.1",
            dependencies=["auth", "notification"],
            api_prefix="/v1/leads",
            endpoint_count=26,
            category="sales",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="food",
            name="Food & Menu Engine",
            description="Menu builder, modifiers, live orders, KDS (Kitchen Display System), table QR ordering, order tracking.",
            engine_type="plugin",
            version="2.1.3",
            dependencies=["auth", "payment", "notification"],
            api_prefix="/v1/food",
            endpoint_count=30,
            category="ordering",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="dispatch",
            name="Job Dispatch Engine",
            description="Auto-assign algorithm, zone routing, workload balancing, dispatch queue, skill-based routing.",
            engine_type="plugin",
            version="1.7.0",
            dependencies=["auth", "notification", "geo"],
            api_prefix="/v1/dispatch",
            endpoint_count=20,
            category="operations",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="inventory",
            name="Inventory Engine",
            description="Parts catalog, stock levels, automatic deduction per job, low-stock alerts, supplier management.",
            engine_type="plugin",
            version="2.0.1",
            dependencies=["auth"],
            api_prefix="/v1/inventory",
            endpoint_count=22,
            category="operations",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="real_estate",
            name="Real Estate Engine",
            description="Property listings, virtual tour URLs, enquiry routing, document vault, deal pipeline CRM.",
            engine_type="plugin",
            version="1.5.0",
            dependencies=["auth", "leads", "media", "document"],
            api_prefix="/v1/real-estate",
            endpoint_count=30,
            category="industry",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="loyalty",
            name="Loyalty & Rewards Engine",
            description="Points earn/burn, tier management (Bronze/Silver/Gold), stamp cards, reward catalog, redemption.",
            engine_type="plugin",
            version="1.3.0",
            dependencies=["auth"],
            api_prefix="/v1/loyalty",
            endpoint_count=18,
            category="retention",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="promo",
            name="Promo & Discounts Engine",
            description="Coupon codes, percentage/flat/bundle discounts, referral codes, campaign tracking, usage limits.",
            engine_type="plugin",
            version="1.2.0",
            dependencies=["auth"],
            api_prefix="/v1/promos",
            endpoint_count=14,
            category="marketing",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="document",
            name="Document Vault Engine",
            description="Contract templates, e-signature capture, document generation (PDF), version control, expiry tracking.",
            engine_type="plugin",
            version="1.1.0",
            dependencies=["auth", "media"],
            api_prefix="/v1/documents",
            endpoint_count=16,
            category="documents",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="geo",
            name="Geo & Maps Engine",
            description="Service zone management, live GPS tracking, ETA calculation, geofencing, route optimization.",
            engine_type="plugin",
            version="1.0.2",
            dependencies=["auth"],
            api_prefix="/v1/geo",
            endpoint_count=12,
            category="location",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="webhook",
            name="Webhook Engine",
            description="Named event subscriptions per engine, HMAC-SHA256 signed payloads, retry with backoff, delivery log.",
            engine_type="plugin",
            version="1.2.0",
            dependencies=["auth"],
            api_prefix="/v1/webhooks",
            endpoint_count=14,
            category="integrations",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="inventory_document_extraction",
            name="Inventory Document Extraction Engine",
            description="Tenant uploads a PDF (price list/stock sheet); extracted text is sent to the "
                         "platform LLM client which identifies inventory line items (name, SKU, quantity, "
                         "unit, unit cost, category) and creates draft InventoryItem rows for the provider "
                         "to review, edit, and publish. Requires the core Inventory Engine.",
            engine_type="plugin",
            version="1.0.0",
            dependencies=["auth", "inventory", "rag"],
            api_prefix="/v1/inventory/extraction",
            endpoint_count=4,
            category="operations",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="form_builder",
            name="Form Builder Engine",
            description="Custom inspection checklists · conditional field logic · mandatory before job status transitions · answers stored per job · feeds quote builder.",
            engine_type="plugin",
            version="1.0.0",
            dependencies=["auth"],
            api_prefix="/v1/forms",
            endpoint_count=16,
            category="data-collection",
            is_enabled_by_default=False,
        ),
    ]

    # NEW ENGINES (Phase 2+)
    NEW_ENGINES = [
        EngineDefinition(
            engine_id="tenant",
            name="Tenant Engine",
            description="7-state lifecycle · 8-step onboarding checklist · provisioning transaction · 360 view · health score · plan enforcement.",
            engine_type="core",
            version="2.4.1",
            dependencies=["auth"],
            api_prefix="/v1/tenants",
            endpoint_count=42,
            category="platform",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="platform_commerce",
            name="Platform Commerce Engine",
            description="Tenant security deposit · credit packages · wallet · auto commission deduction · tenant health score · customer health · badges · warranty.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth", "tenant", "payment"],
            api_prefix="/v1/commerce",
            endpoint_count=35,
            category="finance",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="pricing",
            name="Pricing Engine",
            description="City tiers · type-level base prices · tenant type pricing · brand adjustments · dynamic surge rules · 5-step price pipeline · audit trail.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth", "tenant", "geo"],
            api_prefix="/v1/pricing",
            endpoint_count=28,
            category="commerce",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="serviceability",
            name="Serviceability Engine",
            description="Customer address management · tenant service area coverage by city/zipcode/zone · "
                         "ranked tenant matching · booking preflight integration · serviceability audit log.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth", "tenant", "booking"],
            api_prefix="/v1/serviceability",
            endpoint_count=22,
            category="operations",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="data_science",
            name="Data Science Engine",
            description="Demand forecasting · churn prediction · warranty claim risk · price elasticity · LTV scoring · MLflow model registry · 3-phase cold start.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth", "analytics"],
            api_prefix="/v1/ds",
            endpoint_count=18,
            category="ai",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="workflow",
            name="Job-Type Workflow Engine",
            description="Runtime job-type workflow blueprints on service_job_workflow · app-owned steps · evidence rules · approvals · SLA · immutable job snapshots.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth", "tenant"],
            api_prefix="/v1/admin/master-services/{service_id}/job-types/{job_type_id}/workflow",
            endpoint_count=32,
            category="operations",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="trust_quality",
            name="Trust & Quality Engine",
            description="Badge Engine · Badge Rule Engine · Health Engine · Health Rule Engine · Risk Scoring · Recalculation Jobs · audit.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth", "tenant"],
            api_prefix="/v1/admin/trust-quality",
            endpoint_count=21,
            category="quality",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="compliance",
            name="Compliance Engine",
            description="DPDP requests · consent records · data exports · retention policies · SLA jobs.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth", "tenant"],
            api_prefix="/v1/compliance",
            endpoint_count=20,
            category="governance",
            is_enabled_by_default=True,
        ),
        EngineDefinition(
            engine_id="marketing",
            name="Marketing Engine",
            description="Campaigns · coupons/offers · push notifications · featured listings · referral rules · asset approval.",
            engine_type="plugin",
            version="1.0.0",
            dependencies=["auth", "tenant", "notification"],
            api_prefix="/v1/admin/marketing",
            endpoint_count=24,
            category="marketing",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="complaint_dispute",
            name="Complaint & Remedy Engine",
            description="Customer complaints, provider response, rework, refunds, warranty remedies and admin escalation.",
            engine_type="plugin",
            version="1.0.0",
            dependencies=["auth", "notification", "field_ops", "platform_commerce"],
            api_prefix="/v1/admin/complaints",
            endpoint_count=24,
            category="quality",
            is_enabled_by_default=False,
        ),
        EngineDefinition(
            engine_id="audit",
            name="Audit Engine",
            description="Cross-engine platform audit log mirror · high-risk operation flagging · per-engine audit trails.",
            engine_type="core",
            version="1.0.0",
            dependencies=["auth"],
            api_prefix="/v1/admin/audit-logs",
            endpoint_count=10,
            category="security",
            is_enabled_by_default=True,
        ),
    ]

    for engine in CORE + PLUGINS + NEW_ENGINES:
        registry.register(engine)


# Seed registry immediately on module import
_seed_registry()
