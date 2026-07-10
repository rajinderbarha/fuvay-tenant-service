"""
Seed 3 demo packages to showcase the P0 Package Creation system:
  1. Home Service Starter     — onboarding_package   (signup visible, popular)
  2. Pro Growth Subscription  — subscription_plan    (signup visible, recommended)
  3. Lead Credits Bundle      — lead_credit_package  (signup visible)

Each package includes realistic features and limits.
Idempotent — skips if slug already exists.

Usage:
    python scripts/seed_demo_packages.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.engines.package_commerce.models import ServicePackage, PackageFeature, PackageLimit

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://serviceos:serviceos@127.0.0.1:5432/serviceos",
)

PACKAGES = [
    {
        "name": "Home Service Starter",
        "slug": "home-service-starter",
        "package_type": "onboarding_package",
        "short_description": "Everything a new home-service provider needs to start taking jobs.",
        "description": (
            "The Starter pack gives you immediate access to the provider dashboard, "
            "credit wallet, and job management tools. Includes a security deposit that "
            "is held by the platform and fully refundable on contract close."
        ),
        "vertical_type": "home_services",
        "package_price": 2999,
        "security_deposit_amount": 5000,
        "included_credit_amount": 1000,
        "validity_days": 365,
        "is_active": True,
        "is_public_signup_visible": True,
        "is_popular": True,
        "is_featured": False,
        "is_recommended": False,
        "badge_label": "Most Popular",
        "cta_label": "Get Started",
        "display_order": 1,
        "terms_summary": "No lock-in. Security deposit fully refundable.",
        "refund_policy": "Security deposit refunded within 7 business days of account closure.",
        "features": [
            {"feature_key": "dashboard",         "feature_label": "Provider dashboard access",       "is_highlighted": True,  "is_included": True, "display_order": 0},
            {"feature_key": "credit_wallet",      "feature_label": "₹1,000 starting wallet credits",  "is_highlighted": True,  "is_included": True, "display_order": 1},
            {"feature_key": "job_management",     "feature_label": "Unlimited job posting",           "is_highlighted": False, "is_included": True, "display_order": 2},
            {"feature_key": "staff_management",   "feature_label": "Manage up to 5 staff",            "is_highlighted": False, "is_included": True, "display_order": 3},
            {"feature_key": "analytics_basic",    "feature_label": "Basic performance analytics",     "is_highlighted": False, "is_included": True, "display_order": 4},
            {"feature_key": "email_support",      "feature_label": "Email & chat support",            "is_highlighted": False, "is_included": True, "display_order": 5},
        ],
        "limits": [
            {"limit_key": "staff_count",    "limit_label": "Staff members",     "limit_value": 5,    "limit_unit": "staff",   "is_unlimited": False, "display_order": 0},
            {"limit_key": "active_services","limit_label": "Active services",   "limit_value": 20,   "limit_unit": "services","is_unlimited": False, "display_order": 1},
            {"limit_key": "service_areas",  "limit_label": "Service areas",     "limit_value": 3,    "limit_unit": "zones",   "is_unlimited": False, "display_order": 2},
            {"limit_key": "storage_gb",     "limit_label": "Media storage",     "limit_value": 5,    "limit_unit": "GB",      "is_unlimited": False, "display_order": 3},
        ],
    },
    {
        "name": "Pro Growth Subscription",
        "slug": "pro-growth-subscription",
        "package_type": "subscription_plan",
        "short_description": "For growing businesses — advanced analytics, priority support & more staff.",
        "description": (
            "The Pro Growth plan is a monthly subscription designed for established home-service "
            "businesses ready to scale. Get priority support, advanced analytics, dedicated "
            "account management, and expanded team & territory coverage."
        ),
        "vertical_type": "home_services",
        "package_price": 4999,
        "billing_cycle": "monthly",
        "trial_days": 14,
        "renewal_price_amount": 4999,
        "is_active": True,
        "is_public_signup_visible": True,
        "is_popular": False,
        "is_featured": False,
        "is_recommended": True,
        "badge_label": "Recommended",
        "cta_label": "Start Free Trial",
        "display_order": 2,
        "terms_summary": "14-day free trial. Cancel anytime before billing.",
        "refund_policy": "Unused months refunded pro-rata within 30 days of cancellation.",
        "features": [
            {"feature_key": "priority_support",     "feature_label": "Priority phone & chat support",  "is_highlighted": True,  "is_included": True, "display_order": 0},
            {"feature_key": "advanced_analytics",   "feature_label": "Advanced analytics dashboard",   "is_highlighted": True,  "is_included": True, "display_order": 1},
            {"feature_key": "customer_visibility",  "feature_label": "Featured in customer app search","is_highlighted": False, "is_included": True, "display_order": 2},
            {"feature_key": "dedicated_manager",    "feature_label": "Dedicated account manager",      "is_highlighted": False, "is_included": True, "display_order": 3},
            {"feature_key": "api_access",           "feature_label": "API access for integrations",    "is_highlighted": False, "is_included": True, "display_order": 4},
            {"feature_key": "staff_management",     "feature_label": "Up to 25 staff members",         "is_highlighted": False, "is_included": True, "display_order": 5},
            {"feature_key": "bulk_scheduling",      "feature_label": "Bulk scheduling tools",          "is_highlighted": False, "is_included": True, "display_order": 6},
        ],
        "limits": [
            {"limit_key": "staff_count",     "limit_label": "Staff members",     "limit_value": 25,  "limit_unit": "staff",    "is_unlimited": False, "display_order": 0},
            {"limit_key": "active_services", "limit_label": "Active services",   "limit_value": None, "limit_unit": "",        "is_unlimited": True,  "display_order": 1},
            {"limit_key": "service_areas",   "limit_label": "Service areas",     "limit_value": 15,  "limit_unit": "zones",    "is_unlimited": False, "display_order": 2},
            {"limit_key": "storage_gb",      "limit_label": "Media storage",     "limit_value": 50,  "limit_unit": "GB",       "is_unlimited": False, "display_order": 3},
            {"limit_key": "monthly_jobs",    "limit_label": "Jobs per month",    "limit_value": None, "limit_unit": "",        "is_unlimited": True,  "display_order": 4},
        ],
    },
    {
        "name": "Lead Credits Bundle",
        "slug": "lead-credits-bundle",
        "package_type": "lead_credit_package",
        "short_description": "Buy lead credits for real-estate & coaching verticals. No subscription.",
        "description": (
            "Lead Credits are consumed each time you unlock a customer lead contact. "
            "Buy a bundle once and use them at your own pace — no expiry, no recurring billing."
        ),
        "vertical_type": None,
        "package_price": 1499,
        "lead_credits": 50,
        "validity_days": 180,
        "is_active": True,
        "is_public_signup_visible": True,
        "is_popular": False,
        "is_featured": True,
        "is_recommended": False,
        "badge_label": "Best Value",
        "cta_label": "Buy Credits",
        "display_order": 3,
        "terms_summary": "Credits valid 180 days. Non-refundable after first use.",
        "refund_policy": "Unused credits refundable within 7 days of purchase.",
        "features": [
            {"feature_key": "lead_credits",    "feature_label": "50 lead credits included",          "is_highlighted": True,  "is_included": True, "display_order": 0},
            {"feature_key": "no_expiry_early", "feature_label": "Valid 180 days",                    "is_highlighted": False, "is_included": True, "display_order": 1},
            {"feature_key": "multi_vertical",  "feature_label": "Use across real estate & coaching", "is_highlighted": False, "is_included": True, "display_order": 2},
            {"feature_key": "no_subscription", "feature_label": "One-time purchase, no auto-renew",  "is_highlighted": False, "is_included": True, "display_order": 3},
        ],
        "limits": [
            {"limit_key": "leads",         "limit_label": "Lead unlocks",  "limit_value": 50,  "limit_unit": "leads",   "is_unlimited": False, "display_order": 0},
        ],
    },
]


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for p in PACKAGES:
            existing = await session.execute(
                select(ServicePackage).where(
                    ServicePackage.slug == p["slug"],
                    ServicePackage.deleted_at.is_(None),
                )
            )
            if existing.scalar_one_or_none():
                print(f"  SKIP  {p['slug']} (already exists)")
                continue

            pkg = ServicePackage(
                name=p["name"],
                slug=p["slug"],
                package_type=p["package_type"],
                short_description=p.get("short_description"),
                description=p.get("description"),
                vertical_type=p.get("vertical_type"),
                package_price=p.get("package_price", 0),
                security_deposit_amount=p.get("security_deposit_amount", 0),
                included_credit_amount=p.get("included_credit_amount", 0),
                lead_credits=p.get("lead_credits"),
                validity_days=p.get("validity_days"),
                trial_days=p.get("trial_days"),
                billing_cycle=p.get("billing_cycle"),
                renewal_price_amount=p.get("renewal_price_amount"),
                is_active=p.get("is_active", True),
                is_public_signup_visible=p.get("is_public_signup_visible", False),
                is_popular=p.get("is_popular", False),
                is_featured=p.get("is_featured", False),
                is_recommended=p.get("is_recommended", False),
                badge_label=p.get("badge_label"),
                cta_label=p.get("cta_label"),
                display_order=p.get("display_order", 0),
                terms_summary=p.get("terms_summary"),
                refund_policy=p.get("refund_policy"),
                currency="INR",
                features={},
            )
            session.add(pkg)
            await session.flush()

            for f in p.get("features", []):
                session.add(PackageFeature(
                    package_id=pkg.id,
                    feature_key=f.get("feature_key"),
                    feature_label=f["feature_label"],
                    is_highlighted=f.get("is_highlighted", False),
                    is_included=f.get("is_included", True),
                    display_order=f.get("display_order", 0),
                    status="active",
                ))

            for l in p.get("limits", []):
                session.add(PackageLimit(
                    package_id=pkg.id,
                    limit_key=l["limit_key"],
                    limit_label=l["limit_label"],
                    limit_value=l.get("limit_value"),
                    limit_unit=l.get("limit_unit", ""),
                    is_unlimited=l.get("is_unlimited", False),
                    display_order=l.get("display_order", 0),
                    status="active",
                ))

            await session.commit()
            f_count = len(p.get("features", []))
            l_count = len(p.get("limits", []))
            print(f"  OK    {p['slug']} ({p['package_type']}) | {f_count} features, {l_count} limits")

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
