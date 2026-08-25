"""
ServiceOS — FastAPI Application Factory
Lifespan: DB → Redis → Event Bus → Engine Registry → mount all routers.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.logging import configure_logging
from app.core.events import EventBus, set_event_bus
from app.database import init_db, close_db
from app.exceptions import register_exception_handlers
from app.middleware import register_middleware
from app.observability import setup_prometheus, setup_sentry
from app.redis_client import init_redis, close_redis, get_redis

logger = structlog.get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle — startup and shutdown.
    Order matters: DB before Redis before Event Bus before Routers.
    """
    settings = get_settings()
    configure_logging()
    logger.info("serviceos.starting", version=settings.APP_VERSION, env=settings.APP_ENV)

    # 1. Database
    await init_db()

    # 2. Redis
    await init_redis()

    # PostgreSQL is the durable source of truth for network blocks. Rebuild
    # the hot-path Redis sets after every process/Redis restart.
    try:
        from app.engines.security.service import warm_ip_blocklist_cache
        cache_counts = await warm_ip_blocklist_cache()
        logger.info("security.ip_blocklist_cache_ready", **cache_counts)
    except Exception as exc:
        logger.error("security.ip_blocklist_cache_warm_failed", error=str(exc))

    # 3. Event Bus (Redis pub/sub)
    event_bus = EventBus(get_redis())
    set_event_bus(event_bus)
    logger.info("event_bus.ready")

    # 4. Engine Registry — already seeded at import time
    from app.engine_registry.registry import registry
    # Import all models so Alembic can find them
    from app.engines.auth import models as _auth_models  # noqa
    from app.engines.tenant_engine import models as _tenant_models  # noqa
    from app.engines.serviceability import models as _serviceability_models  # noqa
    logger.info("engine_registry.ready", total=len(registry.all()), core=len(registry.core_engines()))

    logger.info("serviceos.ready", prefix=settings.API_V1_PREFIX)

    # 5. Compliance SLA background loop (runs every 15 min)
    from app.jobs.compliance_sla import background_loop as _compliance_sla_loop
    _sla_task = asyncio.create_task(_compliance_sla_loop())
    logger.info("compliance_sla_loop.started")

    # 6. Export worker background loop (FINAL-L5-05S) — claims and
    # processes enterprise_export_jobs, plus periodic expiry/orphan cleanup.
    from app.jobs.export_worker import background_loop as _export_worker_loop
    _export_worker_task = asyncio.create_task(_export_worker_loop())
    logger.info("export_worker_loop.started")

    # 7. Complaint SLA background loop (MODULE-L5-02 bug #32) — nothing ever
    # evaluated the complaint SLA deadlines, so sla_status stayed 'on_time'
    # forever and no escalation fired. This drives check_and_update_sla and the
    # admin escalation of complaints the provider never answered.
    from app.jobs.complaint_sla import background_loop as _complaint_sla_loop
    _complaint_sla_task = asyncio.create_task(_complaint_sla_loop())
    logger.info("complaint_sla_loop.started")

    # 8. Notification dispatch/retry loop (MODULE-L5-11) — the notification
    # outbox worker was CLI-only, so a transiently-failed (PENDING) notification
    # was never retried without external cron. Runs the same dispatch/retry the
    # docstring intends every minute.
    from app.jobs.notifications import background_loop as _notif_loop
    _notif_task = asyncio.create_task(_notif_loop())
    logger.info("notifications_loop.started")

    # 9. Draft-expiry housekeeping loop (MODULE-L5-11) — the draft-expiry job was
    # CLI-only, so abandoned lead/booking/appointment drafts were never cleaned
    # up without external cron.
    from app.jobs.expire_drafts import background_loop as _expire_loop
    _expire_task = asyncio.create_task(_expire_loop())
    logger.info("expire_drafts_loop.started")

    # 10. Trust & Quality recalculation worker — the platform-wide badge/health/
    # risk sweep used to run inline in the admin's HTTP request, which cannot
    # survive a large provider base. The endpoint now enqueues and this claims.
    from app.jobs.trust_quality_worker import background_loop as _tq_loop
    _tq_task = asyncio.create_task(_tq_loop())
    logger.info("trust_quality_worker_loop.started")

    yield  # ── Application is running ──────────────────────────────

    # ── Shutdown ───────────────────────────────────────────────────
    logger.info("serviceos.shutting_down")
    _sla_task.cancel()
    _export_worker_task.cancel()
    _complaint_sla_task.cancel()
    try:
        await _sla_task
    except asyncio.CancelledError:
        pass
    try:
        await _export_worker_task
    except asyncio.CancelledError:
        pass
    try:
        await _complaint_sla_task
    except asyncio.CancelledError:
        pass
    _notif_task.cancel()
    try:
        await _notif_task
    except asyncio.CancelledError:
        pass
    _expire_task.cancel()
    try:
        await _expire_task
    except asyncio.CancelledError:
        pass
    _tq_task.cancel()
    try:
        await _tq_task
    except asyncio.CancelledError:
        pass
    await close_redis()
    await close_db()
    logger.info("serviceos.stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ServiceOS API",
        description="""
## ServiceOS — Multi-Tenant Service Platform API

Enterprise-grade API with 23 plug-and-play engines for service businesses.

### Architecture
- **23 Engines**: 9 core (always on) + 14 plugin (toggled per tenant)
- **Multi-tenant**: per-schema Postgres isolation + Redis caching
- **Level 5 API**: RFC 7807 errors, HATEOAS, cursor pagination, HMAC webhooks
- **Real-time**: WebSocket rooms per job/conversation

### Authentication
All endpoints require `Authorization: Bearer <token>`.
Obtain a token via `POST /v1/auth/login`.

### Error Format (RFC 7807)
All errors return `application/problem+json` with machine-readable `error_code`.
        """,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={"name": "ServiceOS Platform", "email": "api@serviceos.io"},
        license_info={"name": "Proprietary"},
    )

    # ── Middleware (order: last registered = first executed) ───────
    register_middleware(app)

    # TEMPORARY diagnostic capture -- no-op unless SERVICEOS_CAPTURE_FILE
    # is set. Safe to delete along with app/middleware/capture_debug.py.
    from app.capture_debug import install_capture
    if install_capture(app):
        # Temporary client-error sink, mounted only alongside the capture.
        from app.debug_client_errors import router as _debug_client_error_router
        app.include_router(_debug_client_error_router)
    setup_prometheus(app)
    setup_sentry()

    # ── Exception Handlers ────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────
    _mount_routers(app, settings.API_V1_PREFIX)

    # ── Static files for local media storage ──────────────────────
    import pathlib
    from fastapi.staticfiles import StaticFiles
    uploads_dir = pathlib.Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    return app


def _mount_routers(app: FastAPI, prefix: str) -> None:
    """Mount all engine routers. Each engine owns its prefix. Each router registered ONCE."""

    # Health check (no versioning — load balancers need this at root)
    from app.engines.health_router import router as health_router
    app.include_router(health_router)

    # Engine Registry
    from app.engine_registry.router import router as registry_router
    app.include_router(registry_router, prefix=prefix)

    # Phase 2 — Auth + Public Registration
    from app.engines.auth.router import router as auth_router, admin_security_router, _me_security_router
    from app.engines.public_registration.router import router as public_reg_router
    # Real bug fixed here: RegistrationService (the 5-step no-payment signup
    # -- Owner Account -> Verify Contact -> Business Identity -> Select
    # Vertical -> Review & Consent, with real OTP and auto-login) was fully
    # implemented but never mounted anywhere. `public_reg_router` above is a
    # DIFFERENT, unrelated paid/Razorpay flow with its own inline logic --
    # not two versions of the same thing.
    from app.engines.public_registration.signup_router import router as public_signup_router
    for _r in [auth_router, admin_security_router, _me_security_router, public_reg_router, public_signup_router]:
        app.include_router(_r)

    # P0 Enterprise Platform Users
    from app.engines.auth.platform_users_router import router as platform_users_router
    app.include_router(platform_users_router)

    # Tenant Engine
    from app.engines.tenant_engine.router import router as tenant_router
    app.include_router(tenant_router)

    # Serviceability Engine — must mount before Booking (preflight depends on it)
    from app.engines.serviceability.router import router as serviceability_router
    app.include_router(serviceability_router)

    # Phase 15 — Marketing Automation Engine (Social media: DALL-E image gen, post scheduling)
    from app.engines.marketing.router import router as marketing_router
    app.include_router(marketing_router)

    # Billing Router — inside Platform Commerce (Phase 14)
    from app.engines.platform_commerce.billing_endpoint import router as billing_router
    app.include_router(billing_router)

    # Phase 13 — Compliance Engine
    from app.engines.compliance.router import router as compliance_router
    app.include_router(compliance_router)

    # Compliance Admin Router (enterprise DPDP)
    from app.engines.compliance.admin_router import router as compliance_admin_router
    app.include_router(compliance_admin_router)

    # Compliance Customer Self-Service Router
    from app.engines.compliance.customer_router import router as compliance_customer_router
    app.include_router(compliance_customer_router)

    # Compliance Tenant Portal Router
    from app.engines.compliance.provider_router import router as compliance_provider_router
    app.include_router(compliance_provider_router)

    # Compliance — Technician Mobile Privacy & Data (Phase — "make it 100%
    # working" pass; confirmed live/real via tests/test_mobile_privacy_data.py
    # but never mounted).
    from app.engines.compliance.technician_router import router as compliance_technician_router
    app.include_router(compliance_technician_router)

    # Enterprise Engine Management (migration 081)
    from app.engines.engine_mgmt.admin_router import router as engine_mgmt_admin_router
    app.include_router(engine_mgmt_admin_router)

    # Trust & Quality Engine — Badges, Health, Risk (migration 095)
    from app.engines.trust_quality.admin_router import router as trust_quality_admin_router
    from app.engines.trust_quality.provider_router import provider_trust_quality_router
    from app.engines.trust_quality.public_router import public_trust_quality_router
    app.include_router(trust_quality_admin_router)
    app.include_router(provider_trust_quality_router)
    app.include_router(public_trust_quality_router)

    # Notification Template Center (migration 101)
    from app.engines.notification.admin_router import router as notif_templates_admin_router
    app.include_router(notif_templates_admin_router)

    # Customer Service Credit + Dispute Settlement Engine (migration 080)
    from app.engines.customer_credits.admin_router import router as credits_admin_router
    from app.engines.customer_credits.customer_router import router as credits_customer_router
    from app.engines.customer_credits.provider_router import router as credits_provider_router
    app.include_router(credits_admin_router)
    app.include_router(credits_customer_router)
    app.include_router(credits_provider_router)

    # Phase 12 — Security Engine
    from app.engines.security.router import router as security_router
    app.include_router(security_router)

    # Security Enterprise Upgrade — SOC admin router
    from app.engines.security.admin_router import router as security_admin_router
    app.include_router(security_admin_router)

    # Phase 11 — Review + Chat + Webhook
    from app.engines.review.router  import router as review_router
    from app.engines.chat.router    import router as chat_router
    from app.engines.webhook.router import router as webhook_router
    for _r in [review_router, chat_router, webhook_router]:
        app.include_router(_r)

    # Phase 10 — Payment + Inventory + Subscription + Document
    from app.engines.payment.router      import router as payment_router
    from app.engines.inventory.router    import router as inventory_router
    from app.engines.inventory.extraction_router import router as inventory_extraction_router
    from app.engines.subscription.router import router as subscription_router
    from app.engines.document.router     import router as document_router
    for _r in [payment_router, inventory_router, inventory_extraction_router, subscription_router, document_router]:
        app.include_router(_r)

    # Phase 9 — Booking + Appointment
    from app.engines.booking.router              import router as booking_router
    from app.engines.booking.admin_router        import router as booking_admin_router
    from app.engines.appointment.router          import router as appointment_router
    from app.engines.auth.admin_customers_router import router as admin_customers_router
    from app.engines.auth.admin_staff_router     import router as admin_staff_router
    for _r in [booking_router, booking_admin_router, appointment_router, admin_customers_router, admin_staff_router]:
        app.include_router(_r)

    # Phase 18 — Service Catalog Engine
    from app.engines.service_catalog.router import router as catalog_router
    app.include_router(catalog_router)

    # Phase 8 — Geo + Dispatch + Field Ops
    from app.engines.geo.router       import router as geo_router
    from app.engines.dispatch.router  import router as dispatch_router
    from app.engines.field_ops.router import router as fieldops_router
    # Step 6 — Job Assignment + Staff Status Lifecycle
    from app.engines.field_ops.staff_router    import router as fieldops_staff_router
    from app.engines.field_ops.customer_router import (
        router as fieldops_customer_router,
        invoice_router as fieldops_customer_invoice_router,
    )
    # Step 8 — Checklist Templates (tenant CRUD)
    from app.engines.field_ops.checklist_router import router as fieldops_checklist_router
    # Step 9 — Payment / Invoice / Commission Closure Flow
    from app.engines.field_ops.tenant_finance_router import (
        router as fieldops_tenant_finance_router, wallet_router as fieldops_tenant_wallet_router,
    )
    from app.engines.field_ops.admin_finance_router import (
        router as fieldops_admin_finance_router, wallet_router as fieldops_admin_wallet_router,
    )
    # P0 — Enterprise Finance Hub Upgrade. Mounted BEFORE fieldops_admin_finance_router:
    # both define GET /v1/admin/finance/summary — FastAPI matches first-registered-wins,
    # and finance_hub's enterprise summary is the one the admin frontend calls.
    # fieldops_admin_finance_router's other paths (/invoices, /payments, /commissions)
    # are unaffected since they don't overlap.
    from app.engines.finance_hub.admin_router import router as finance_hub_router
    app.include_router(finance_hub_router)
    # fieldops_customer_quote_router is deliberately NOT mounted: it declares
    # the same prefix (/v1/customer/quotes) and the same three paths
    # (GET /{quote_id}, POST /{quote_id}/approve, POST /{quote_id}/reject) as
    # quote_checklist's customer_router, and being registered first it
    # silently swallowed every customer quote approve/reject/detail request.
    # It is backed by the dead field_ops `job_quotes` table (0 rows platform-
    # wide) while the live engine is quote_checklist's `service_job_quotes` --
    # so extra-work quote approval could never succeed from either the web or
    # mobile customer app. Its bare list route (GET "") has no callers in any
    # frontend. Unmounting removes the collision; the file is left in place.
    for _r in [geo_router, dispatch_router, fieldops_router,
               fieldops_staff_router, fieldops_customer_router,
               fieldops_checklist_router,
               fieldops_customer_invoice_router, fieldops_tenant_finance_router,
               fieldops_tenant_wallet_router, fieldops_admin_finance_router,
               fieldops_admin_wallet_router]:
        app.include_router(_r)

    # Sprint 76 — Types & Brands Enterprise (service types master, mappings, brand mappings)
    from app.engines.admin_catalog.catalog_enterprise_router import router as catalog_enterprise_router
    # Sprint 3 — Admin Catalog + Pricing + Tenant Service Enablement
    from app.engines.admin_catalog.admin_router    import router as admin_catalog_router
    from app.engines.admin_catalog.tenant_router   import router as tenant_catalog_router
    # Migration 154 — Generic catalog dimension engine (admin Dimensions tab)
    from app.engines.admin_catalog.dimension_router import router as catalog_dimension_router
    # Admin Job Type CRUD + Blueprint Impact Report
    from app.engines.admin_catalog.job_type_router import (
        router as catalog_job_type_router, impact_router as catalog_impact_router,
        draft_router as catalog_blueprint_draft_router,
    )
    # Migration 155 — Conditional Question Engine (admin Problems & Questions tab)
    from app.engines.admin_catalog.question_router import router as catalog_question_router
    # Migration 160 — Job-Type Blueprint (job type as a child record + workflow ownership)
    from app.engines.admin_catalog.job_type_blueprint_router import router as job_type_blueprint_router
    # Sprint 34C — Customer master catalog read endpoints
    from app.engines.admin_catalog.customer_router import router as customer_master_catalog_router
    # Sprint 34D — Brand management (admin CRUD + requests + templates)
    from app.engines.admin_catalog.brand_router import (
        router as brand_admin_router,
        req_router as brand_req_router,
        tmpl_router as brand_tmpl_router,
    )
    from app.engines.admin_catalog.brand_provider_router import router as brand_provider_router
    from app.engines.admin_catalog.brand_customer_router import router as brand_customer_router
    # Sprint 34E — Service Options + Issue Catalog
    from app.engines.admin_catalog.service_option_admin_router import (
        grp_router as svc_opt_grp_router,
        iss_router as svc_iss_router,
        map_router as svc_map_router,
        chk_router as svc_chk_router,
    )
    from app.engines.admin_catalog.service_option_provider_router import (
        router as svc_opt_provider_router,
    )
    from app.engines.admin_catalog.service_option_customer_router import (
        router as svc_opt_customer_router,
    )
    # Sprint 34F — Service Setup Templates
    from app.engines.admin_catalog.service_setup_template_router import (
        admin_router as sst_admin_router,
        provider_router as sst_provider_router,
    )
    # Deactivate Manual Bargain Module — Automatic Customer Price Options
    from app.engines.admin_catalog.auto_price_options_router import (
        admin_router as auto_price_admin_router,
        tenant_router as auto_price_tenant_router,
    )
    from app.engines.admin_catalog.home_services_catalog_console_router import (
        router as home_services_catalog_console_router,
    )
    from app.engines.admin_catalog.skill_catalog_router import (
        admin_router as category_skill_admin_router,
        provider_router as category_skill_provider_router,
    )
    app.include_router(catalog_enterprise_router)
    for _r in [admin_catalog_router, tenant_catalog_router, customer_master_catalog_router,
               catalog_dimension_router, catalog_job_type_router, catalog_impact_router,
               catalog_blueprint_draft_router, catalog_question_router, job_type_blueprint_router,
               brand_admin_router, brand_req_router, brand_tmpl_router,
               brand_provider_router, brand_customer_router,
               svc_opt_grp_router, svc_iss_router, svc_map_router, svc_chk_router,
               svc_opt_provider_router, svc_opt_customer_router,
               sst_admin_router, sst_provider_router,
               auto_price_admin_router, auto_price_tenant_router,
               home_services_catalog_console_router,
               category_skill_admin_router, category_skill_provider_router]:
        app.include_router(_r)
    # Sprint 34H — Admin Bulk Setup Wizard
    from app.engines.admin_catalog.bulk_setup_router import router as bulk_setup_router
    app.include_router(bulk_setup_router)

    # Sprint 34I — Recommendation Rules Engine
    from app.engines.admin_catalog.recommendation_router import (
        admin_router    as rec_admin_router,
        shared_router   as rec_shared_router,
        ai_router       as rec_ai_router,
        ctx_admin_router as rec_ctx_admin_router,
        ctx_provider_router as rec_ctx_provider_router,
        ctx_customer_router as rec_ctx_customer_router,
    )
    for _r in [rec_admin_router, rec_shared_router, rec_ai_router,
               rec_ctx_admin_router, rec_ctx_provider_router, rec_ctx_customer_router]:
        app.include_router(_r)

    # Sprint 34J — Customer Flow Simplification
    from app.engines.admin_catalog.customer_flow_router import (
        customer_router as cflow_customer_router,
        admin_router    as cflow_admin_router,
    )
    app.include_router(cflow_customer_router)
    app.include_router(cflow_admin_router)

    # Sprint 4 — Admin Tenant Onboarding + Tenant 360 sub-resources
    # Static package-commerce tenant paths must be mounted before the generic
    # tenant portal `/{tenant_id}` paths. Otherwise `credit-wallet` is parsed
    # as a tenant UUID and the real static endpoint is never reached.
    from app.engines.package_commerce.tenant_router import router as pkg_tenant_router
    app.include_router(pkg_tenant_router)

    from app.engines.tenant_engine.admin_router import router as admin_tenant_router
    # Sprint 4 — Tenant portal mirror (tenant_id from JWT)
    from app.engines.tenant_engine.portal_router import router as tenant_portal_router
    for _r in [admin_tenant_router, tenant_portal_router]:
        app.include_router(_r)

    # Sprint 5 — Package Commerce: packages, security deposit, credit wallet, commission
    from app.engines.package_commerce.admin_router import router as pkg_admin_router
    # Sprint 070 — Public signup packages (unauthenticated)
    from app.engines.package_commerce.public_router import router as pkg_public_router
    for _r in [pkg_admin_router, pkg_public_router]:
        app.include_router(_r)

    # Scalability Sprint — Location Engine (states, districts, cities, zones)
    from app.engines.location_engine.router import router as location_router
    app.include_router(location_router)

    # Phase 7 — Data Science Engine
    from app.engines.data_science.router import router as ds_router
    app.include_router(ds_router)

    # Phase 6 — RAG Engine (knowledge base, document ingestion, vector search)
    from app.engines.rag.router import router as rag_router
    app.include_router(rag_router)

    # Phase 5 — Settings + Notification + Media + Analytics + AI Chat
    from app.engines.settings_engine.router import router as settings_router
    from app.engines.settings_engine.admin_router import router as settings_admin_router
    from app.engines.notification.router    import router as notif_router
    from app.engines.media.router           import router as media_router
    from app.engines.analytics.router       import router as analytics_router
    from app.engines.ai_chat.router         import router as ai_chat_router
    for _r in [settings_router, settings_admin_router, notif_router, media_router, analytics_router, ai_chat_router]:
        app.include_router(_r)

    # Phase 0A — Media Engine (new: direct upload, access-checked serve, profile photos)
    from app.engines.media.new_router import router as media_assets_router, profile_router as media_profile_router
    app.include_router(media_assets_router)
    app.include_router(media_profile_router)

    # P0 Enterprise Media Library — admin management + signed URLs
    from app.engines.media.admin_router import router as media_admin_router, signed_router as media_signed_router
    app.include_router(media_admin_router)
    app.include_router(media_signed_router)

    # Phase 0C — Profile Edit Engine
    from app.engines.profile.router import router as profile_edit_router
    app.include_router(profile_edit_router)

    # Phase 4 — Pricing Engine
    from app.engines.pricing.router import router as pricing_router
    app.include_router(pricing_router)

    # Phase 3 — Platform Commerce Engine
    from app.engines.platform_commerce.router import router as commerce_router
    app.include_router(commerce_router)

    # FINAL-L5-05J — Canonical Usage Credit Engine
    from app.engines.usage_credits.router import router as usage_credits_router
    app.include_router(usage_credits_router)

    # Plugin Engines (disabled: only home_services vertical is active)
    # from app.engines.leads.router       import router as leads_router
    # from app.engines.food.router        import router as food_router
    # from app.engines.real_estate.router import router as real_estate_router
    # from app.engines.loyalty.router     import router as loyalty_router
    # from app.engines.promo.router       import router as promo_router

    # Sprint 14 — Customer Category Flow Routing
    from app.engines.customer_flow.router       import router as customer_flow_router
    from app.engines.customer_flow.admin_router import router as customer_flow_admin_router
    for _r in [customer_flow_router, customer_flow_admin_router]:
        app.include_router(_r)

    # Sprint 35 — Category Runtime Router (/v1/admin/categories/*)
    from app.engines.admin_catalog.category_runtime_router import router as category_runtime_router
    app.include_router(category_runtime_router)

    # Sprint 15 — AI Conversation Engine + DeepSeek Orchestrator
    from app.engines.ai_conversation.customer_router import router as ai_conv_customer_router
    from app.engines.ai_conversation.admin_router    import router as ai_conv_admin_router
    for _r in [ai_conv_customer_router, ai_conv_admin_router]:
        app.include_router(_r)

    # Sprint 16 — Home Service Chatbot Booking Flow
    from app.engines.home_service_booking.customer_router import (
        router as hs_booking_customer_router,
        assistant_bootstrap_router as hs_booking_assistant_bootstrap_router,
    )
    from app.engines.home_service_booking.admin_router    import router as hs_booking_admin_router
    for _r in [hs_booking_customer_router, hs_booking_assistant_bootstrap_router, hs_booking_admin_router]:
        app.include_router(_r)

    # Sprint 17 — Coaching / IELTS Chatbot Appointment Flow
    from app.engines.coaching_appointment.customer_router import router as coaching_appt_customer_router
    from app.engines.coaching_appointment.admin_router    import router as coaching_appt_admin_router
    for _r in [coaching_appt_customer_router, coaching_appt_admin_router]:
        app.include_router(_r)

    # Sprint 18 — Real Estate Chatbot Lead Flow
    from app.engines.real_estate_lead.customer_router import router as re_lead_customer_router
    from app.engines.real_estate_lead.admin_router    import router as re_lead_admin_router
    for _r in [re_lead_customer_router, re_lead_admin_router]:
        app.include_router(_r)

    # Sprint 19 — Booking Confirmation → Final Record Creation
    from app.engines.final_records.confirm_router  import router as final_confirm_router
    from app.engines.final_records.customer_router import router as final_customer_router
    from app.engines.final_records.provider_router import router as final_provider_router
    from app.engines.final_records.admin_router    import router as final_admin_router
    from app.engines.final_records.operations_router import router as final_operations_router
    for _r in [final_confirm_router, final_customer_router, final_provider_router,
               final_admin_router, final_operations_router]:
        app.include_router(_r)

    # Sprint 20 — Home Service Job Assignment + Staff Lifecycle
    from app.engines.home_service_assignment.provider_router import router as assign_provider_router
    from app.engines.home_service_assignment.staff_router    import router as assign_staff_router
    from app.engines.home_service_assignment.customer_router import router as assign_customer_router
    from app.engines.home_service_assignment.admin_router    import (
        router as assign_admin_router,
        admin_jobs_router as assign_admin_jobs_router,
    )
    for _r in [assign_provider_router, assign_staff_router, assign_customer_router,
               assign_admin_router, assign_admin_jobs_router]:
        app.include_router(_r)

    # Sprint 21 — Repair / Service / Consultation Execution Flow
    from app.engines.execution.home_service_router import (
        staff_router    as exec_hs_staff_router,
        provider_router as exec_hs_provider_router,
        customer_router as exec_hs_customer_router,
        admin_router    as exec_hs_admin_router,
    )
    from app.engines.execution.coaching_router import (
        staff_router    as exec_ca_staff_router,
        provider_router as exec_ca_provider_router,
        customer_router as exec_ca_customer_router,
        admin_router    as exec_ca_admin_router,
    )
    from app.engines.execution.real_estate_router import (
        agent_router    as exec_re_agent_router,
        provider_router as exec_re_provider_router,
        customer_router as exec_re_customer_router,
        admin_router    as exec_re_admin_router,
    )
    for _r in [
        exec_hs_staff_router, exec_hs_provider_router,
        exec_hs_customer_router, exec_hs_admin_router,
        exec_ca_staff_router, exec_ca_provider_router,
        exec_ca_customer_router, exec_ca_admin_router,
        exec_re_agent_router, exec_re_provider_router,
        exec_re_customer_router, exec_re_admin_router,
    ]:
        app.include_router(_r)

    # Phase 2A — My Work foundation (technician role, ServiceJob-scoped only;
    # see docs/workflow-rearchitecture/phase-01a/my-work-contract.md)
    from app.engines.execution.my_work_router import router as exec_my_work_router
    app.include_router(exec_my_work_router)

    # Technician mobile app routers -- RESTORED during the Final Phase
    # end-to-end pass (2026-08-02): these were confirmed mounted and
    # passing their full regression suite (26/26) earlier in this same
    # session, then found completely absent from main.py partway through
    # this pass with no corresponding edit by this agent -- app/main.py
    # appears to be modified by an external process during this session
    # (see the standing system note about it). Restoring verbatim.
    from app.engines.home_service_assignment.mobile_schedule_router import router as mobile_schedule_router, tenant_router as mobile_schedule_tenant_router
    app.include_router(mobile_schedule_router)
    app.include_router(mobile_schedule_tenant_router)

    from app.engines.platform_notifications.mobile_notifications_router import router as mobile_notifications_router
    app.include_router(mobile_notifications_router)

    from app.engines.home_service_assignment.mobile_profile_router import router as mobile_profile_router
    app.include_router(mobile_profile_router)

    from app.engines.home_service_assignment.mobile_employment_router import router as mobile_employment_router, tenant_router as mobile_employment_tenant_router
    app.include_router(mobile_employment_router)
    app.include_router(mobile_employment_tenant_router)

    from app.engines.home_service_assignment.mobile_documents_router import router as mobile_documents_router, tenant_router as mobile_documents_tenant_router
    from app.engines.vertical_catalog.tenant_documents_workspace_router import router as tenant_documents_workspace_router
    app.include_router(tenant_documents_workspace_router)
    app.include_router(mobile_documents_router)
    app.include_router(mobile_documents_tenant_router)

    from app.engines.home_service_assignment.mobile_notification_preferences_router import router as mobile_notif_prefs_router, push_router as mobile_push_router
    app.include_router(mobile_notif_prefs_router)
    app.include_router(mobile_push_router)

    from app.engines.home_service_assignment.mobile_sync_router import router as mobile_sync_router
    app.include_router(mobile_sync_router)

    # Sprint 22 — Quote Approval + Checklist Engine
    from app.engines.quote_checklist.provider_router import (
        provider_router as qc_provider_router,
        staff_router    as qc_staff_router,
        checklist_router as qc_checklist_router,
    )
    from app.engines.quote_checklist.customer_router import (
        customer_router as qc_customer_router,
    )
    from app.engines.quote_checklist.admin_router import (
        admin_router      as qc_admin_router,
        admin_quote_router as qc_admin_quote_router,
    )
    for _r in [
        qc_provider_router, qc_staff_router, qc_checklist_router,
        qc_customer_router, qc_admin_router, qc_admin_quote_router,
    ]:
        app.include_router(_r)

    # PARTS-APPROVAL phase -- customer parts-request read/decide.
    from app.engines.execution.customer_parts_router import router as exec_customer_parts_router
    app.include_router(exec_customer_parts_router)

    # Technician mobile app job-execution routers -- found unmounted during
    # the Final Phase end-to-end pass (2026-08-02): the router files and
    # their dedicated pytest suites are real and passing, but none of these
    # 8 routers were ever registered here, so the ENTIRE staff mobile app's
    # inspection/estimate/work-execution/completion-proof/direct-payment
    # pipeline was unreachable (404) despite working code.
    from app.engines.execution.mobile_home_router import router as exec_mobile_home_router
    app.include_router(exec_mobile_home_router)

    from app.engines.execution.mobile_jobs_router import router as exec_mobile_jobs_router
    app.include_router(exec_mobile_jobs_router)

    from app.engines.execution.mobile_job_detail_router import router as exec_mobile_job_detail_router
    app.include_router(exec_mobile_job_detail_router)

    from app.engines.execution.mobile_inspection_router import router as exec_mobile_inspection_router
    app.include_router(exec_mobile_inspection_router)

    from app.engines.execution.mobile_estimate_router import router as exec_mobile_estimate_router
    app.include_router(exec_mobile_estimate_router)

    from app.engines.execution.mobile_work_execution_router import router as exec_mobile_work_execution_router
    app.include_router(exec_mobile_work_execution_router)

    from app.engines.execution.mobile_completion_proof_router import router as exec_mobile_completion_proof_router
    app.include_router(exec_mobile_completion_proof_router)

    from app.engines.execution.mobile_direct_payment_router import router as exec_mobile_direct_payment_router
    app.include_router(exec_mobile_direct_payment_router)

    # Checklist Catalog Engine — canonical, job-type-mapped checklists
    # (consolidates quote_checklist/field_ops/admin_catalog checklist
    # systems onto one reusable-template + exact-Job-Type-mapping model).
    from app.engines.checklist_catalog.admin_router import router as cc_admin_router
    from app.engines.checklist_catalog.execution_router import (
        staff_router as cc_staff_router,
        tenant_router as cc_tenant_router,
        customer_router as cc_customer_router,
        admin_router as cc_instance_admin_router,
    )
    # Masked calling — platform-bridged technician<->customer calls so neither
    # side ever learns the other's number (off-platform leakage prevention).
    from app.engines.masked_calling.router import (
        staff_router as mc_staff_router, webhook_router as mc_webhook_router,
    )
    app.include_router(mc_staff_router)
    app.include_router(mc_webhook_router)

    # Tenant selection of which authored checklist points this provider runs
    # per service (minimum 5) -- the tenant half of the admin-authors/
    # tenant-selects rule. Distinct from execution_router's tenant_router,
    # which serves per-job checklist instance reads.
    from app.engines.checklist_catalog.tenant_router import router as cc_tenant_selection_router
    for _r in [cc_admin_router, cc_staff_router, cc_tenant_router, cc_customer_router,
               cc_instance_admin_router, cc_tenant_selection_router]:
        app.include_router(_r)

    # Sprint 23 — Invoice / Payment / Commission / Wallet / Subscription
    from app.engines.invoice_payment.provider_router import (
        provider_invoice_router, provider_wallet_router,
        provider_sub_router, staff_invoice_router,
    )
    from app.engines.invoice_payment.customer_router import customer_invoice_router
    from app.engines.invoice_payment.admin_router import (
        admin_invoice_router, admin_payment_router, admin_commission_router,
        admin_wallet_router, admin_sub_router, admin_fin_events_router,
    )
    for _r in [
        provider_invoice_router, provider_wallet_router, provider_sub_router,
        staff_invoice_router, customer_invoice_router,
        admin_invoice_router, admin_payment_router, admin_commission_router,
        admin_wallet_router, admin_sub_router, admin_fin_events_router,
    ]:
        app.include_router(_r)

    # Tenant Help & Support engine (Phase Y this session -- built, tested
    # 3/3, verified live, then found unmounted later in the SAME session
    # with no edit by this agent -- see the standing note on app/main.py
    # being externally modified). Restoring verbatim.
    from app.engines.support.tenant_router import router as support_tenant_router
    from app.engines.support.admin_router import router as support_admin_router
    app.include_router(support_tenant_router)
    app.include_router(support_admin_router)

    from app.engines.tenant_assistant.tenant_router import router as assistant_tenant_router
    from app.engines.tenant_assistant.admin_router import router as assistant_admin_router
    app.include_router(assistant_tenant_router)
    app.include_router(assistant_admin_router)

    # Home Services Direct Payments (tenant declaration + customer
    # confirm/dispute) -- found unmounted during the Final Phase
    # end-to-end pass: the customer could never confirm/dispute a direct
    # payment via the real API, and the canonical tenant-side declaration
    # endpoints were unreachable too (the staff mobile app has its own
    # separate, already-mounted declare/remind endpoints, which masked
    # this gap during earlier phases' testing).
    from app.engines.invoice_payment.direct_payments_router import (
        router as dp_tenant_router, customer_router as dp_customer_router,
    )
    app.include_router(dp_tenant_router)
    app.include_router(dp_customer_router)

    # Sprint 24 — Customer Reviews + Rating Engine
    from app.engines.customer_reviews.customer_router import customer_review_router
    from app.engines.customer_reviews.provider_router import provider_review_router
    from app.engines.customer_reviews.public_router   import public_review_router
    from app.engines.customer_reviews.admin_router import (
        admin_review_router, admin_flag_router, admin_reply_router,
        admin_policy_router, admin_rating_router,
    )
    for _r in [
        customer_review_router, provider_review_router, public_review_router,
        admin_review_router, admin_flag_router, admin_reply_router,
        admin_policy_router, admin_rating_router,
    ]:
        app.include_router(_r)

    # Sprint 26 — Enterprise Grid
    from app.engines.enterprise_grid.router import enterprise_router
    app.include_router(enterprise_router, prefix="/v1")

    # Sprint 25 — Complaints / Disputes / Refund / Rework
    from app.engines.complaints.customer_router import customer_complaint_router
    from app.engines.complaints.provider_router import (
        provider_complaint_router, provider_rework_router, provider_refund_router,
    )
    from app.engines.complaints.admin_router import (
        admin_complaint_router, admin_rework_router, admin_refund_router, admin_cpolicy_router,
    )
    for _r in [
        customer_complaint_router,
        provider_complaint_router, provider_rework_router, provider_refund_router,
        admin_complaint_router, admin_rework_router, admin_refund_router, admin_cpolicy_router,
    ]:
        app.include_router(_r)

    # LEVEL-5 REMEDIATION Phase 10 — Customer Home aggregation. The router
    # existed (app/engines/customer_home/router.py) but was never included
    # here, so GET /v1/customer/home 404'd on every environment despite the
    # mobile customer-app's entire Home screen being built against it
    # (found live during the In-App Notification Center phase's mandated
    # Home-count-sync proof).
    from app.engines.customer_home.router import router as customer_home_router
    app.include_router(customer_home_router)

    # Fuvay's own web/app/software services are nationwide lead-generation
    # products, not local provider bookings. Mount them independently from
    # customer Home serviceability so every ZIP receives the same catalog.
    from app.engines.global_services.customer_router import router as global_services_customer_router
    from app.engines.global_services.admin_router import router as global_services_admin_router
    app.include_router(global_services_customer_router)
    app.include_router(global_services_admin_router)

    # Address autocomplete. Proxied so the Places key never ships in the app bundle.
    from app.engines.places.router import router as places_router
    app.include_router(places_router)

    # Per-technician time off and date overrides -- the writes behind the availability
    # board's override and time-off cells, which had nothing to read until now.
    from app.engines.home_service_assignment.staff_availability_router import (
        router as staff_availability_router,
    )
    app.include_router(staff_availability_router)

    # Real bug fixed here: ELEVEN routers serving the tenant portal's Home
    # Services workspaces were written and never mounted. Every one of their
    # routes 404'd, which is why those pages appeared to have "no backend" --
    # the backends existed all along. Same dead-router class as the twelve
    # mounted above.
    for _tenant_hs_router in [
        "app.engines.final_records.tenant_bookings_jobs_router",
        "app.engines.admin_catalog.tenant_services_workspace_router",
        "app.engines.complaints.tenant_router",
        "app.engines.customer_reviews.hs_quality_router",
        "app.engines.home_service_assignment.team_directory_router",
        "app.engines.serviceability.tenant_router",
        "app.engines.tenant_engine.hs_tenant_customer_router",
        "app.engines.vertical_catalog.activation_payment_router",
        "app.engines.vertical_catalog.tenant_documents_router",
        "app.engines.vertical_catalog.tenant_finance_readiness_router",
        "app.engines.vertical_catalog.tenant_setup_router",
        "app.engines.tenant_engine.workspace_settings_router",
        "app.engines.home_service_assignment.dispatch_router",
        "app.engines.home_service_assignment.availability_planner_router",
    ]:
        import importlib
        app.include_router(importlib.import_module(_tenant_hs_router).router)

    # Retired 2026-08-20: customer Home promotional banners/campaign slots.

    # Sprint 27 — Notification + Chat + Audit Integration
    from app.engines.platform_notifications.customer_router import (
        customer_notif_router, customer_chat_router,
    )
    from app.engines.platform_notifications.provider_router import (
        provider_notif_router, provider_chat_router, provider_audit_router,
        staff_notif_router, staff_chat_router,
    )
    from app.engines.platform_notifications.admin_router import (
        admin_notif_router, admin_outbox_router, admin_notif_events_router,
        admin_notif_templates_router, admin_chat_router, admin_audit_router,
    )
    for _r in [
        customer_notif_router, customer_chat_router,
        provider_notif_router, provider_chat_router, provider_audit_router,
        staff_notif_router, staff_chat_router,
        admin_notif_router, admin_outbox_router, admin_notif_events_router,
        admin_notif_templates_router, admin_chat_router, admin_audit_router,
    ]:
        app.include_router(_r)

    # Sprint 28 — Category Analytics + Provider/Admin Reports
    from app.engines.analytics.admin_router import (
        admin_analytics_router, admin_reports_router,
    )
    from app.engines.analytics.provider_router import (
        provider_analytics_router, provider_reports_router,
    )
    from app.engines.analytics.platform_router import platform_analytics_router
    for _r in [
        admin_analytics_router, admin_reports_router,
        provider_analytics_router, provider_reports_router,
        platform_analytics_router,
    ]:
        app.include_router(_r)

    # Sprint 29 — AI Hardening + Marketing Automation
    from app.engines.ai_conversation.sprint29_admin_router import admin_ai_router
    from app.engines.ai_conversation.sprint29_customer_router import customer_ai_router
    from app.engines.marketing_automation.admin_router import admin_marketing_router
    from app.engines.marketing_automation.provider_router import provider_marketing_router
    from app.engines.customer_home.admin_router import router as customer_home_admin_router
    for _r in [
        admin_ai_router, customer_ai_router,
        admin_marketing_router, provider_marketing_router, customer_home_admin_router,
    ]:
        app.include_router(_r)

    # Provider Portal — Sprint 11/12 provider team-members, availability, offerings, status
    # + Admin bookability, onboarding, monetization, engine admin stubs
    from app.engines.provider_portal.router import router as provider_portal_router
    from app.engines.provider_portal.admin_router import admin_router as provider_admin_router
    app.include_router(provider_portal_router)
    app.include_router(provider_admin_router)

    # P0 Multi-Vertical Catalog Architecture (migration 089)
    from app.engines.vertical_catalog.admin_router import router as verticals_router
    from app.engines.vertical_catalog.admin_router import modules_router as catalog_modules_router
    from app.engines.vertical_catalog.admin_router import enrollments_router as tenant_vertical_enrollments_router
    app.include_router(verticals_router)
    app.include_router(catalog_modules_router)
    app.include_router(tenant_vertical_enrollments_router)

    # FINAL-L5-04B — Tenant Module and Category Entitlement Architecture (migration 132)
    from app.engines.entitlement.admin_router import router as entitlement_admin_router
    from app.engines.entitlement.tenant_router import router as entitlement_tenant_router
    app.include_router(entitlement_admin_router)
    app.include_router(entitlement_tenant_router)

    # P0 Enterprise Service Setup Templates (migration 091)
    from app.engines.service_setup.templates_router import router as setup_templates_router
    app.include_router(setup_templates_router)

    # P0 Enterprise Service Setup Bulk Wizard (migration 098)
    from app.engines.service_setup.bulk_router import router as bulk_wizard_router
    app.include_router(bulk_wizard_router)

    # P0 Marketing Automation Command Center (migration 100)
    from app.engines.marketing_command_center.admin_router import router as marketing_command_center_router
    app.include_router(marketing_command_center_router)

    # Knowledge Base Enterprise (migration 104) — must be BEFORE intelligence_cmd_router
    from app.engines.analytics.kb_router import router as kb_router
    app.include_router(kb_router)

    # Intelligence Command Center (migration 103)
    from app.engines.analytics.intelligence_router import router as intelligence_cmd_router
    app.include_router(intelligence_cmd_router)

    # P0 Platform Command Center Dashboard (migration 104)
    from app.engines.dashboard_command_center.admin_router import router as dashboard_command_center_router
    app.include_router(dashboard_command_center_router)

    # Workflow Templates Enterprise (migration 106) is NOT mounted: migration
    # 186 dropped its tables (workflow_templates / workflow_template_versions)
    # as a confirmed-dead system and stated the router and service files would
    # be removed with it. The unmount was missed, so the routes stayed live and
    # every one of them returned 500 against tables that no longer existed.
    # Its one genuinely missing idea — cross-app step choreography — now lives
    # on the canonical service_job_workflow (migration 274).

    # Phase 1B — Admin Roles & Permissions read API
    from app.engines.roles_permissions.admin_router import router as roles_permissions_router
    app.include_router(roles_permissions_router)

    # Global Services (migration 227) — platform-owned promotional listings
    # shown to every customer nationwide, independent of vertical/category/
    # tenant serviceability. Customer interest becomes a Lead an admin calls.
    # Retired 2026-08-20: Global Services promotional lead-capture listings.

    # Phase 1B — safe, dev-only 500-error-envelope verification route.
    # Never mounted in production; requires super_admin even in dev/test.
    from app.config import get_settings as _get_settings
    if not _get_settings().is_production:
        from fastapi import APIRouter as _APIRouter, Depends as _Depends
        from app.dependencies.auth import require_super_admin as _require_super_admin

        _test_router = _APIRouter(prefix="/v1/admin/test", tags=["Dev-Only Test Routes"])

        @_test_router.get("/error-500", summary="[dev/test only] Deliberately raise an unhandled "
                           "exception to verify the 500 error envelope includes request_id.")
        async def _trigger_500(u=_Depends(_require_super_admin)):
            raise RuntimeError("Phase 1B controlled test failure — verifying 500 error envelope.")

        app.include_router(_test_router)

    # ── PRODUCTION BUG FIX: engines that were fully built but NEVER MOUNTED ──
    # Each of these engines has a complete router, service layer, models and
    # migrations, and each has a Super Admin / Tenant Portal workspace built
    # against it -- but none of them was ever added to _mount_routers, so
    # EVERY one of their routes returned 404 in production. Several also
    # failed to import at all (permission constants and one model class were
    # referenced but never declared), which is why the omission stayed
    # invisible: adding the include_router() alone would have raised at boot.
    from app.engines.vertical_monetization.admin_router import router as vertical_monetization_admin_router
    from app.engines.vertical_monetization.customer_router import router as vertical_monetization_customer_router
    from app.engines.vertical_directory.admin_router import router as vertical_directory_router
    from app.engines.tenant_engine.hs_customer_directory_router import router as hs_customer_directory_router
    from app.engines.tenant_engine.hs_provider_directory_router import router as hs_provider_directory_router
    from app.engines.tenant_engine.hs_dashboard_router import router as hs_dashboard_router
    from app.engines.platform_notifications.policy_router import router as notification_policy_router
    from app.engines.settings_engine.configuration_router import router as platform_configuration_router
    from app.engines.customer_reviews.hs_review_router import router as hs_review_router
    # `admin_router` here is the Home Services deposit-refund-request console
    # (/v1/admin/finance/home-services/deposit-refund-requests). It was written
    # and permission-guarded but NEVER MOUNTED -- only `router` was imported --
    # so every one of its endpoints 404'd. A tenant could file a security-
    # deposit refund request that no admin could then list, request info on,
    # approve, reject or mark refunded: the request was stuck forever, and the
    # `info_requested` note the Finance Hub renders could never be set by
    # anyone. Mounting it is what makes the documented state machine reachable.
    # WhatsApp/Instagram inbound channel. A thin adapter in front of the
    # existing ai_conversation agent -- no second bot, no duplicated booking
    # logic. Unauthenticated by design: Meta calls it, and authenticity is
    # proved by the verify token and the HMAC signature over the raw body.
    from app.engines.messaging_gateway.router import router as messaging_gateway_router
    from app.engines.finance_hub.tenant_hs_finance_router import (
        router as tenant_hs_finance_router,
        admin_router as admin_hs_deposit_refund_router,
    )
    from app.engines.finance_hub.admin_hs_finance_router import (
        router as admin_hs_finance_router,
        canonical_router as admin_hs_finance_canonical_router,
    )
    from app.engines.vertical_monetization.home_services_finance_router import (
        router as hs_finance_monetization_router,
    )
    from app.engines.vertical_catalog.topup_plan_router import router as hs_topup_plan_router
    for _unmounted in [
        vertical_monetization_admin_router, vertical_monetization_customer_router,
        vertical_directory_router, hs_customer_directory_router,
        hs_provider_directory_router, hs_dashboard_router,
        notification_policy_router, platform_configuration_router,
        hs_review_router, admin_hs_finance_router,
        admin_hs_finance_canonical_router,
        tenant_hs_finance_router, admin_hs_deposit_refund_router,
        messaging_gateway_router,
        hs_finance_monetization_router, hs_topup_plan_router,
    ]:
        app.include_router(_unmounted)

    # Shared admin routers mix platform-wide list routes with tenant-owned
    # resource routes. Apply the dynamic guard only to the latter so a
    # disabled vertical cannot be mutated through a shared surface while
    # cross-vertical admin queues remain reachable.
    from fastapi import Depends as _Depends
    from fastapi.dependencies.utils import get_parameterless_sub_dependant
    from app.dependencies.vertical_guard import require_dynamic_vertical_enabled

    _dynamic_guard_routes = {
        ("/v1/admin/onboarding/providers/{tenant_id}/send-reminder", "POST"),
        ("/v1/admin/onboarding/providers/{tenant_id}", "GET"),
        ("/v1/admin/onboarding/providers/{tenant_id}/documents/{document_id}/review", "POST"),
        ("/v1/admin/onboarding/providers/{tenant_id}/approve", "POST"),
        ("/v1/admin/onboarding/providers/{tenant_id}/reject", "POST"),
        ("/v1/admin/onboarding/providers/{tenant_id}/request-changes", "POST"),
        ("/v1/admin/onboarding/providers/{tenant_id}/refresh", "POST"),
        ("/v1/admin/onboarding/providers/{tenant_id}/items/{checklist_key}/override", "PUT"),
        ("/v1/admin/bookability/providers/{tenant_id}", "GET"),
        ("/v1/admin/bookability/providers/{tenant_id}/audit-logs", "GET"),
        ("/v1/admin/bookability/providers/{tenant_id}/refresh", "POST"),
        ("/v1/admin/bookability/providers/{tenant_id}/override-visibility", "POST"),
        ("/v1/admin/bookability/providers/{tenant_id}/override-visibility", "DELETE"),
        ("/v1/admin/bookability/providers/{tenant_id}/override-bookability", "POST"),
        ("/v1/admin/bookability/providers/{tenant_id}/override-bookability", "DELETE"),
        ("/v1/admin/monetization/providers/{tenant_id}", "GET"),
        ("/v1/admin/monetization/providers/{tenant_id}/sync", "POST"),
        ("/v1/admin/complaints/{complaint_id}", "GET"),
        ("/v1/admin/complaints/{complaint_id}/assign", "POST"),
        ("/v1/admin/complaints/{complaint_id}/priority", "POST"),
        ("/v1/admin/complaints/{complaint_id}/request-provider-response", "POST"),
        ("/v1/admin/complaints/{complaint_id}/messages", "POST"),
        ("/v1/admin/complaints/{complaint_id}/messages", "GET"),
        ("/v1/admin/complaints/{complaint_id}/propose-resolution", "POST"),
        ("/v1/admin/complaints/{complaint_id}/resolutions", "GET"),
        ("/v1/admin/complaints/{complaint_id}/reject", "POST"),
        ("/v1/admin/complaints/{complaint_id}/resolve", "POST"),
        ("/v1/admin/complaints/{complaint_id}/close", "POST"),
        ("/v1/admin/complaints/{complaint_id}/events", "GET"),
        ("/v1/admin/complaints/{complaint_id}/start-ai-settlement", "POST"),
        ("/v1/admin/complaints/{complaint_id}/finalize-settlement", "POST"),
        ("/v1/admin/complaints/{complaint_id}/settlement-proposals", "POST"),
        ("/v1/admin/complaints/{complaint_id}/settlement-proposals", "GET"),
        ("/v1/admin/complaints/{complaint_id}/ai-session", "GET"),
        ("/v1/admin/complaints/{complaint_id}/timeline", "GET"),
        ("/v1/admin/rework-requests/{rework_id}/approve", "POST"),
        ("/v1/admin/rework-requests/{rework_id}/reject", "POST"),
        ("/v1/admin/rework-requests/{rework_id}/assign", "POST"),
        ("/v1/admin/refund-requests/{refund_id}/approve", "POST"),
        ("/v1/admin/refund-requests/{refund_id}/reject", "POST"),
        ("/v1/admin/refund-requests/{refund_id}/record", "POST"),
        ("/v1/admin/refund-requests/{refund_id}/verify", "POST"),
        ("/v1/admin/reviews/{review_id}", "GET"),
        ("/v1/admin/reviews/{review_id}/approve", "POST"),
        ("/v1/admin/reviews/{review_id}/reject", "POST"),
        ("/v1/admin/reviews/{review_id}/hide", "POST"),
        ("/v1/admin/reviews/{review_id}", "DELETE"),
        ("/v1/admin/reviews/{review_id}/events", "GET"),
        ("/v1/admin/review-flags/{flag_id}/resolve", "POST"),
        ("/v1/admin/review-replies/{review_id}/approve", "POST"),
        ("/v1/admin/review-replies/{review_id}/reject", "POST"),
        ("/v1/admin/rating-summaries/tenant/{tenant_id}/recompute", "POST"),
        ("/admin/checklist-templates/jobs/{job_id}", "GET"),
        ("/admin/quotes/jobs/{job_id}", "GET"),
        ("/admin/quotes/{quote_id}", "GET"),
        ("/admin/quotes/{quote_id}/events", "GET"),
    }
    _guard_dependant = lambda path: get_parameterless_sub_dependant(
        depends=_Depends(require_dynamic_vertical_enabled), path=path,
    )
    for _included in app.routes:
        if type(_included).__name__ != "_IncludedRouter":
            continue
        _guard_added = False
        for _route in _included.original_router.routes:
            _path = getattr(_route, "path", "")
            _methods = getattr(_route, "methods", set()) or set()
            if any((_path, _method) in _dynamic_guard_routes for _method in _methods):
                _dependency = _Depends(require_dynamic_vertical_enabled)
                _route.dependencies.insert(0, _dependency)
                _route.dependant.dependencies.insert(0, get_parameterless_sub_dependant(
                    depends=_dependency, path=_path,
                ))
                _guard_added = True
        if _guard_added:
            # FastAPI 0.116+ lazily caches an effective copy of every
            # included route. Invalidate it after changing the original
            # dependency graph; otherwise OpenAPI sees the guard while live
            # requests may keep executing a previously cached copy.
            _included._effective_candidates_version = None
            _included._effective_low_priority_routes_version = None

    logger.info("routers.mounted", count="...analytics + ai_hardening + marketing_automation + provider_portal + vertical_catalog + setup_templates + bulk_wizard + marketing_command_center + dashboard_command_center + workflow_enterprise + roles_permissions")


# ── WSGI/ASGI entry point ─────────────────────────────────────────────────────
app = create_app()
