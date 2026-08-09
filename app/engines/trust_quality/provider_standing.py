"""A provider's STANDING: one badge, for the level they have actually reached.

Replaces a row of independent badges on the customer's card with a single claim. The
reason is not visual tidiness: a customer deciding whether to let a stranger into
their home reads a row of five pills as five endorsements, when they may be one fact
counted five ways. One level, earned, is a claim that means something.

The ladder supersedes rather than accumulates -- reaching Silver IS no longer being
Bronze, so there is nothing to revoke and no way to hold two levels at once. That
falls out of computing the level from current facts rather than storing awards.

Every threshold below is tied to something counted in this database:

* completed jobs        -- service_jobs.status = 'completed'
* approved reviews      -- customer_reviews.status = 'approved' (count and average)
* verification          -- tenants.verification_status, the platform's own check
* time on the platform  -- tenants.created_at

A provider who meets no level gets NO badge. That is the honest output and it is
deliberate: the fallback for "we cannot vouch for them yet" is silence, never a
starter badge, because a badge nobody has earned devalues the ones that were.

Thresholds are the platform's policy, and these are defaults -- ADJUST_ME is the
right attitude to the exact numbers, not to their shape. Tenure is only required from
Silver upward: at Bronze it would gate a genuinely verified provider with real
finished work on nothing but the calendar, while at the top it is what separates a
sustained record from a good month.

Presentation (name/icon/colour) is taken from an admin-configured badge definition
when one exists under the matching `badge_key`, so Trust & Quality stays the place
where these are named and styled. The code-level defaults are the fallback, never an
override.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("trust_quality.provider_standing")

_VERIFIED_STATUSES = ("verified", "approved", "completed")


@dataclass(frozen=True)
class StandingLevel:
    """One rung. `level` orders them; the highest satisfied rung wins."""
    level: int
    badge_key: str
    name: str
    icon: str
    color: str
    min_completed_jobs: int
    min_reviews: int
    min_average_rating: float
    min_days_active: int
    requires_verification: bool


# Ordered low to high. `badge_key` is what an admin-configured definition must use to
# supply its own name/icon/colour for that rung.
LADDER: tuple[StandingLevel, ...] = (
    StandingLevel(
        level=1, badge_key="standing_bronze", name="Bronze Partner",
        icon="medal", color="#b45309",
        min_completed_jobs=5, min_reviews=0, min_average_rating=0.0,
        min_days_active=0, requires_verification=True,
    ),
    StandingLevel(
        level=2, badge_key="standing_silver", name="Silver Partner",
        icon="medal", color="#64748b",
        min_completed_jobs=25, min_reviews=10, min_average_rating=4.3,
        min_days_active=90, requires_verification=True,
    ),
    StandingLevel(
        level=3, badge_key="standing_gold", name="Gold Partner",
        icon="trophy", color="#f59e0b",
        min_completed_jobs=100, min_reviews=40, min_average_rating=4.6,
        min_days_active=180, requires_verification=True,
    ),
    StandingLevel(
        level=4, badge_key="standing_elite", name="Elite Partner",
        icon="crown", color="#7c3aed",
        min_completed_jobs=250, min_reviews=100, min_average_rating=4.8,
        min_days_active=365, requires_verification=True,
    ),
)


@dataclass(frozen=True)
class StandingFacts:
    completed_jobs: int
    approved_reviews: int
    average_rating: float | None
    verified: bool
    days_active: int


def satisfies(level: StandingLevel, facts: StandingFacts) -> bool:
    """Whether these facts genuinely reach this rung.

    Every clause is an AND: a provider with 300 finished jobs and a 3.9 average has
    not earned Gold, because the level is a claim about quality as well as volume.
    """
    if level.requires_verification and not facts.verified:
        return False
    if facts.completed_jobs < level.min_completed_jobs:
        return False
    if facts.approved_reviews < level.min_reviews:
        return False
    if level.min_average_rating > 0:
        # No rating at all fails a rung that requires one -- absence is not a pass.
        if facts.average_rating is None or facts.average_rating < level.min_average_rating:
            return False
    if facts.days_active < level.min_days_active:
        return False
    return True


def resolve_level(facts: StandingFacts) -> StandingLevel | None:
    """The highest rung these facts reach, or None.

    Walks from the top down, so a provider who meets Gold is Gold even if some future
    rung's criteria are not a strict superset of the one below.
    """
    for level in sorted(LADDER, key=lambda l: l.level, reverse=True):
        if satisfies(level, facts):
            return level
    return None


async def load_facts(db: AsyncSession, tenant_id) -> StandingFacts | None:
    """The provider's real counts. None when the tenant does not exist."""
    row = (await db.execute(text(
        "SELECT t.verification_status, t.created_at, "
        "  (SELECT count(*) FROM service_jobs j "
        "     WHERE j.tenant_id = t.id AND j.status = 'completed') AS completed_jobs, "
        "  (SELECT count(*) FROM customer_reviews r "
        "     WHERE r.tenant_id = t.id AND r.status = 'approved') AS approved_reviews, "
        "  (SELECT avg(r.overall_rating) FROM customer_reviews r "
        "     WHERE r.tenant_id = t.id AND r.status = 'approved') AS average_rating "
        "FROM tenants t WHERE t.id = CAST(:tid AS uuid)"
    ), {"tid": str(tenant_id)})).first()
    if not row:
        return None

    m = row._mapping
    created = m["created_at"]
    if created is None:
        days_active = 0
    else:
        if created.tzinfo is None:
            created = created.replace(tzinfo=dt.timezone.utc)
        days_active = max(0, (dt.datetime.now(dt.timezone.utc) - created).days)

    average = m["average_rating"]
    return StandingFacts(
        completed_jobs=int(m["completed_jobs"] or 0),
        approved_reviews=int(m["approved_reviews"] or 0),
        average_rating=float(average) if average is not None else None,
        verified=str(m["verification_status"] or "").strip().lower() in _VERIFIED_STATUSES,
        days_active=days_active,
    )


async def _admin_presentation(db: AsyncSession, badge_key: str) -> dict | None:
    """An admin's own name/icon/colour for this rung, if they configured one.

    Only an ACTIVE, customer-visible definition counts: an admin who hid a badge from
    customers meant it, and this must not route around that.
    """
    row = (await db.execute(text(
        "SELECT name, icon, color FROM badge_definitions "
        "WHERE badge_key = :key AND status = 'active' AND customer_visible = true "
        "LIMIT 1"
    ), {"key": badge_key})).first()
    if not row:
        return None
    m = row._mapping
    name = (m["name"] or "").strip()
    return {"name": name, "icon": m["icon"], "color": m["color"]} if name else None


async def resolve_standing_badge(db: AsyncSession, tenant_id) -> dict | None:
    """The single customer-facing standing badge, or None if none is earned.

    Shape matches the other customer badges ({name, icon, color}) plus `level`, so a
    surface can style the top rungs differently without parsing a name.

    Never raises: a decorative read must not be able to break a booking card. A
    failure yields None -- no badge -- rather than a guess.
    """
    try:
        facts = await load_facts(db, tenant_id)
        if not facts:
            return None
        level = resolve_level(facts)
        if not level:
            return None
        presentation = await _admin_presentation(db, level.badge_key)
        return {
            "name": (presentation or {}).get("name") or level.name,
            "icon": (presentation or {}).get("icon") or level.icon,
            "color": (presentation or {}).get("color") or level.color,
            "level": level.level,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("provider_standing.failed", tenant_id=str(tenant_id), error=str(exc))
        return None
