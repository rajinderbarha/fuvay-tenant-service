"""Home Services Customers — canonical, vertically-scoped customer directory.

Audit finding: the existing Home Services Customers page showed only Total/
Active Customers and an empty list (grep-verified: no customer-directory
router/service existed before this file). This is a genuine build, not a
bugfix.

Home Services isolation is structural: ServiceBooking/ServiceJob are the
Home-Services-only final-record tables (same fact already established for
usage_credit_ledger/financial_events elsewhere in this codebase -- Coaching/
Real Estate use their own separate tables). A query scoped to these tables
can never see another vertical's customer activity by construction.

Total/Active/New/Repeat/Returning-Rate are ALL computed here in ONE shared
per-customer aggregate (_customer_aggregates), so the summary counts and
the directory list/export can never disagree about who's in scope -- the
exact anti-pattern this session has repeatedly found and fixed elsewhere
(Home Services Provider Directory's "1 provider but empty table" bug).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func, or_, and_, case, cast, String, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.final_records.models import ServiceBooking, ServiceJob
from app.engines.invoice_payment.models import ServiceInvoice, ServicePaymentRecord, FinancialEvent
from app.engines.complaints.models import CustomerComplaint
from app.engines.auth.models import User
from app.engines.tenant_engine.customer_operational_access_policy import customer_alias, masked_locality
from app.exceptions import NotFoundException

JOB_STATUS_COMPLETED = "completed"
PAYMENT_RELIABILITY_MIN_DECISIONS = 3
PAYMENT_RELIABILITY_DECIDED_STATUSES = ("confirmed", "mismatched", "disputed")
PAYMENT_RELIABILITY_REVIEW_STATUSES = ("mismatched", "disputed")

# ── Policy constants -- the single source of truth for these window sizes.
# The frontend must read these from get_metric_definitions(), never
# hardcode 90/30 independently (per USER REQ).
ACTIVE_WINDOW_DAYS = 90
NEW_CUSTOMER_WINDOW_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _payment_reliability_status(decided_records: int, review_records: int) -> str:
    """Classify only canonical customer/provider payment decisions.

    Pending confirmations are not treated as bad behaviour. A customer needs
    review only while at least one canonical payment record is currently
    mismatched or disputed; otherwise three decisions are required before the
    UI may call the relationship reliable.
    """
    if decided_records < PAYMENT_RELIABILITY_MIN_DECISIONS:
        return "insufficient_data"
    return "needs_review" if review_records else "reliable"


class HomeServicesCustomerDirectoryService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role

    def get_metric_definitions(self) -> dict:
        return {
            "active_window_days": ACTIVE_WINDOW_DAYS,
            "new_customer_window_days": NEW_CUSTOMER_WINDOW_DAYS,
            "total_customers": "Unique customer IDs with at least one ServiceBooking "
                                "(ServiceBooking rows only exist post-draft-confirmation, "
                                "so no separate draft exclusion is needed).",
            "active_customers": f"Unique customers with a ServiceJob updated within the last "
                                 f"{ACTIVE_WINDOW_DAYS} days.",
            "new_customers": f"Customers whose first ServiceBooking fell within the last "
                              f"{NEW_CUSTOMER_WINDOW_DAYS} days.",
            "repeat_customers": "Customers with >= 2 completed ServiceJobs.",
            "one_time_customers": "Customers with exactly 1 completed ServiceJob.",
            "returning_rate": "repeat_customers / customers_with_at_least_one_completed_job * 100",
            "multi_service_customers": "Customers with completed jobs across >= 2 distinct "
                                        "Master Services (ServiceJob.offering_id).",
            "multi_provider_customers": "Customers with completed jobs across >= 2 distinct "
                                         "provider tenant_ids.",
            "confirmed_job_value": "Sum of ServiceInvoice.customer_payable_amount for this "
                                    "customer's paid invoices. Not platform collection -- the "
                                    "customer pays the provider directly.",
            "payment_reliability": "Derived from canonical direct-payment reconciliation records. "
                                    "Pending confirmations are neutral; at least 3 customer decisions "
                                    "are required. Any current mismatch or dispute needs review.",
        }

    async def _payment_reliability_by_customer(
        self, customer_ids: list[uuid.UUID], *, tenant_id: uuid.UUID | None = None,
    ) -> dict[uuid.UUID, dict]:
        """Return payment decision counts in one grouped query (never N+1)."""
        if not customer_ids:
            return {}
        clauses = [
            ServicePaymentRecord.customer_id.in_(customer_ids),
            ServicePaymentRecord.reconciliation_status.in_(PAYMENT_RELIABILITY_DECIDED_STATUSES),
        ]
        if tenant_id:
            clauses.append(ServicePaymentRecord.tenant_id == tenant_id)
        rows = (await self.db.execute(
            select(
                ServicePaymentRecord.customer_id,
                func.count(ServicePaymentRecord.id),
                func.sum(case(
                    (ServicePaymentRecord.reconciliation_status.in_(PAYMENT_RELIABILITY_REVIEW_STATUSES), 1),
                    else_=0,
                )),
            ).where(*clauses).group_by(ServicePaymentRecord.customer_id)
        )).all()
        result: dict[uuid.UUID, dict] = {}
        for customer_id, decided, review in rows:
            decided_count = int(decided or 0)
            review_count = int(review or 0)
            result[customer_id] = {
                "status": _payment_reliability_status(decided_count, review_count),
                "decided_records": decided_count,
                "review_records": review_count,
            }
        return result

    # ── The one shared per-customer aggregate ────────────────────────────────
    async def _customer_aggregates(self, *, customer_ids: list[uuid.UUID] | None = None,
                                    tenant_id: uuid.UUID | None = None) -> dict[uuid.UUID, dict]:
        """Returns {customer_id: {...}} computed from ServiceBooking + ServiceJob
        in bounded queries (grouped SQL, not N+1 per customer).

        `tenant_id` is the tenant-isolation boundary (marketplace anti-
        disintermediation / customer-privacy policy): when provided, this
        customer's relationship is scoped to bookings/jobs with THIS
        tenant, never another tenant's -- see
        app.engines.tenant_engine.customer_operational_access_policy. The
        cross-tenant/no-tenant_id path remains for the platform-admin
        console (hs_customer_directory_router's own /v1/admin/... surface),
        which legitimately needs a cross-tenant view."""
        now = _utcnow()
        active_cutoff = now - timedelta(days=ACTIVE_WINDOW_DAYS)
        new_cutoff = now - timedelta(days=NEW_CUSTOMER_WINDOW_DAYS)

        booking_clauses = [ServiceBooking.customer_id.isnot(None)]
        if customer_ids:
            booking_clauses.append(ServiceBooking.customer_id.in_(customer_ids))
        if tenant_id:
            booking_clauses.append(ServiceBooking.tenant_id == tenant_id)

        first_booking_rows = (await self.db.execute(
            select(ServiceBooking.customer_id, func.min(ServiceBooking.created_at))
            .where(*booking_clauses).group_by(ServiceBooking.customer_id)
        )).all()
        first_booking_at = {cid: ts for cid, ts in first_booking_rows}

        job_clauses = [ServiceJob.customer_id.isnot(None)]
        if customer_ids:
            job_clauses.append(ServiceJob.customer_id.in_(customer_ids))
        if tenant_id:
            job_clauses.append(ServiceJob.tenant_id == tenant_id)
        # Aggregate in PostgreSQL. The old implementation selected every job
        # row and rebuilt these counters/sets in Python, so memory and transfer
        # cost grew with total job history rather than customer count.
        job_rows = (await self.db.execute(
            select(
                ServiceJob.customer_id,
                func.count(ServiceJob.id).filter(ServiceJob.status == JOB_STATUS_COMPLETED),
                func.count(ServiceJob.id).filter(ServiceJob.status == "cancelled"),
                func.max(ServiceJob.updated_at),
                func.count(func.distinct(ServiceJob.offering_id)).filter(
                    ServiceJob.status == JOB_STATUS_COMPLETED,
                ),
                func.count(func.distinct(ServiceJob.tenant_id)).filter(
                    ServiceJob.status == JOB_STATUS_COMPLETED,
                ),
            ).where(*job_clauses).group_by(ServiceJob.customer_id)
        )).all()

        agg: dict[uuid.UUID, dict] = {}
        for cid in first_booking_at:
            agg[cid] = {
                "first_booking_at": first_booking_at[cid],
                "completed_jobs": 0, "cancelled_jobs": 0,
                "last_activity_at": first_booking_at[cid],
                "services_used_count": 0, "providers_used_count": 0,
                "is_active": False,
            }
        for cid, completed_jobs, cancelled_jobs, updated_at, services_used, providers_used in job_rows:
            if cid not in agg:
                continue
            a = agg[cid]
            a["completed_jobs"] = int(completed_jobs or 0)
            a["cancelled_jobs"] = int(cancelled_jobs or 0)
            a["services_used_count"] = int(services_used or 0)
            a["providers_used_count"] = int(providers_used or 0)
            if updated_at and (a["last_activity_at"] is None or updated_at > a["last_activity_at"]):
                a["last_activity_at"] = updated_at
            if updated_at and updated_at >= active_cutoff:
                a["is_active"] = True

        for cid, a in agg.items():
            a["is_new"] = a["first_booking_at"] is not None and a["first_booking_at"] >= new_cutoff
            a["repeat_status"] = "repeat" if a["completed_jobs"] >= 2 else ("one_time" if a["completed_jobs"] == 1 else "none")
            a["multi_service"] = a["services_used_count"] >= 2
            a["multi_provider"] = a["providers_used_count"] >= 2

        return agg

    def _customer_rollup_subquery(self, *, tenant_id: uuid.UUID | None = None):
        """PostgreSQL customer rollup used by high-cardinality admin reads.

        The result stays inside SQL so summary/list endpoints never transfer
        one row per customer merely to count or paginate it in Python.
        """
        booking_clauses = [ServiceBooking.customer_id.isnot(None)]
        job_clauses = [ServiceJob.customer_id.isnot(None)]
        if tenant_id:
            booking_clauses.append(ServiceBooking.tenant_id == tenant_id)
            job_clauses.append(ServiceJob.tenant_id == tenant_id)

        bookings = (
            select(
                ServiceBooking.customer_id.label("customer_id"),
                func.min(ServiceBooking.created_at).label("first_booking_at"),
            )
            .where(*booking_clauses)
            .group_by(ServiceBooking.customer_id)
            .subquery("hs_customer_bookings")
        )
        jobs = (
            select(
                ServiceJob.customer_id.label("customer_id"),
                func.count(ServiceJob.id).filter(
                    ServiceJob.status == JOB_STATUS_COMPLETED
                ).label("completed_jobs"),
                func.count(ServiceJob.id).filter(
                    ServiceJob.status == "cancelled"
                ).label("cancelled_jobs"),
                func.max(ServiceJob.updated_at).label("last_job_at"),
                func.count(func.distinct(ServiceJob.offering_id)).filter(
                    ServiceJob.status == JOB_STATUS_COMPLETED
                ).label("services_used_count"),
                func.count(func.distinct(ServiceJob.tenant_id)).filter(
                    ServiceJob.status == JOB_STATUS_COMPLETED
                ).label("providers_used_count"),
            )
            .where(*job_clauses)
            .group_by(ServiceJob.customer_id)
            .subquery("hs_customer_jobs")
        )
        return (
            select(
                bookings.c.customer_id,
                bookings.c.first_booking_at,
                func.coalesce(jobs.c.completed_jobs, 0).label("completed_jobs"),
                func.coalesce(jobs.c.cancelled_jobs, 0).label("cancelled_jobs"),
                jobs.c.last_job_at,
                func.coalesce(jobs.c.last_job_at, bookings.c.first_booking_at).label("last_activity_at"),
                func.coalesce(jobs.c.services_used_count, 0).label("services_used_count"),
                func.coalesce(jobs.c.providers_used_count, 0).label("providers_used_count"),
            )
            .select_from(bookings.outerjoin(jobs, jobs.c.customer_id == bookings.c.customer_id))
            .subquery("hs_customer_rollup")
        )

    async def _list_customers_sql(
        self, *, q: str | None, activity: str | None, repeat_status: str | None,
        payment_reliability: str | None, complaint_state: str | None,
        sort: str, page: int, page_size: int,
        tenant_id: uuid.UUID | None = None,
    ) -> dict:
        """High-cardinality directory query executed entirely in PostgreSQL.

        Tenant callers use the same rollup as platform admins, but the query
        projects only a deterministic tenant-scoped alias. Raw identity is
        never joined into or searchable from the provider surface.
        """
        active_cutoff = _utcnow() - timedelta(days=ACTIVE_WINDOW_DAYS)
        rollup = self._customer_rollup_subquery(tenant_id=tenant_id)
        complaint_clauses = [
            CustomerComplaint.customer_id.isnot(None),
            CustomerComplaint.status.notin_(("resolved", "closed", "rejected")),
        ]
        payment_clauses = [
            ServicePaymentRecord.customer_id.isnot(None),
            ServicePaymentRecord.reconciliation_status.in_(PAYMENT_RELIABILITY_DECIDED_STATUSES),
        ]
        if tenant_id:
            complaint_clauses.append(CustomerComplaint.tenant_id == tenant_id)
            payment_clauses.append(ServicePaymentRecord.tenant_id == tenant_id)
        open_complaints = (
            select(
                CustomerComplaint.customer_id.label("customer_id"),
                func.count(CustomerComplaint.id).label("open_complaints"),
            )
            .where(*complaint_clauses)
            .group_by(CustomerComplaint.customer_id)
            .subquery("hs_customer_open_complaints")
        )
        payment = (
            select(
                ServicePaymentRecord.customer_id.label("customer_id"),
                func.count(ServicePaymentRecord.id).label("decided_records"),
                func.sum(case(
                    (ServicePaymentRecord.reconciliation_status.in_(PAYMENT_RELIABILITY_REVIEW_STATUSES), 1),
                    else_=0,
                )).label("review_records"),
            )
            .where(*payment_clauses)
            .group_by(ServicePaymentRecord.customer_id)
            .subquery("hs_customer_payment_reliability")
        )
        joined = rollup.outerjoin(
            open_complaints, open_complaints.c.customer_id == rollup.c.customer_id,
        ).outerjoin(payment, payment.c.customer_id == rollup.c.customer_id)
        if tenant_id is None:
            joined = joined.outerjoin(User, User.id == rollup.c.customer_id)

        complaint_count = func.coalesce(open_complaints.c.open_complaints, 0)
        decided_count = func.coalesce(payment.c.decided_records, 0)
        review_count = func.coalesce(payment.c.review_records, 0)
        alias_expr = None
        if tenant_id:
            # Must stay byte-for-byte compatible with customer_alias().
            # pgcrypto is installed by migration 001. Computing the alias in
            # SQL keeps alias search and pagination correct at any cardinality.
            digest_input = literal(
                "serviceos-customer-alias-v1" + str(tenant_id)
            ) + cast(rollup.c.customer_id, String)
            alias_expr = func.concat(
                literal("Customer HS-"),
                func.upper(func.substr(
                    func.encode(func.digest(digest_input, literal("sha256")), literal("hex")),
                    1, 4,
                )),
            )
        filters = []
        if q:
            needle = f"%{q.strip()}%"
            if tenant_id:
                filters.append(alias_expr.ilike(needle))
            else:
                filters.append(or_(
                    User.full_name.ilike(needle), User.email.ilike(needle),
                    User.phone.ilike(needle), cast(rollup.c.customer_id, String).ilike(needle),
                ))
        if activity == "active":
            filters.append(rollup.c.last_job_at >= active_cutoff)
        elif activity == "inactive":
            filters.append(or_(rollup.c.last_job_at.is_(None), rollup.c.last_job_at < active_cutoff))
        if repeat_status == "repeat":
            filters.append(rollup.c.completed_jobs >= 2)
        elif repeat_status == "one_time":
            filters.append(rollup.c.completed_jobs == 1)
        elif repeat_status == "none":
            filters.append(rollup.c.completed_jobs == 0)
        if payment_reliability == "reliable":
            filters.append(and_(
                decided_count >= PAYMENT_RELIABILITY_MIN_DECISIONS,
                review_count == 0,
            ))
        elif payment_reliability == "needs_review":
            filters.append(and_(
                decided_count >= PAYMENT_RELIABILITY_MIN_DECISIONS,
                review_count > 0,
            ))
        elif payment_reliability == "insufficient_data":
            filters.append(decided_count < PAYMENT_RELIABILITY_MIN_DECISIONS)
        if complaint_state == "open":
            filters.append(complaint_count > 0)
        elif complaint_state == "clear":
            filters.append(complaint_count == 0)

        order_by = {
            "last_activity_asc": (rollup.c.last_activity_at.asc().nulls_last(), rollup.c.customer_id),
            "completed_desc": (rollup.c.completed_jobs.desc(), rollup.c.last_activity_at.desc().nulls_last()),
            "complaints_desc": (complaint_count.desc(), rollup.c.last_activity_at.desc().nulls_last()),
            "first_booking_desc": (rollup.c.first_booking_at.desc().nulls_last(), rollup.c.customer_id),
        }.get(sort, (rollup.c.last_activity_at.desc().nulls_last(), rollup.c.customer_id))

        total = int((await self.db.execute(
            select(func.count()).select_from(joined).where(*filters)
        )).scalar() or 0)
        columns = [
            rollup,
            complaint_count.label("open_complaints"),
            decided_count.label("decided_records"),
            review_count.label("review_records"),
        ]
        if tenant_id:
            columns.append(alias_expr.label("alias"))
        else:
            columns.extend((User.full_name.label("name"), User.email, User.phone))
        rows = (await self.db.execute(
            select(*columns)
            .select_from(joined)
            .where(*filters)
            .order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).mappings().all()

        items = []
        for row in rows:
            completed = int(row["completed_jobs"] or 0)
            last_job_at = row["last_job_at"]
            decided = int(row["decided_records"] or 0)
            review = int(row["review_records"] or 0)
            item = {
                "customer_id": str(row["customer_id"]),
                "is_active": bool(last_job_at and last_job_at >= active_cutoff),
                "repeat_status": "repeat" if completed >= 2 else ("one_time" if completed == 1 else "none"),
                "completed_jobs": completed,
                "cancelled_jobs": int(row["cancelled_jobs"] or 0),
                "services_used_count": int(row["services_used_count"] or 0),
                "providers_used_count": int(row["providers_used_count"] or 0),
                "open_complaints": int(row["open_complaints"] or 0),
                "first_booking_at": row["first_booking_at"].isoformat() if row["first_booking_at"] else None,
                "last_activity_at": row["last_activity_at"].isoformat() if row["last_activity_at"] else None,
                "payment_reliability": _payment_reliability_status(decided, review),
            }
            if tenant_id:
                item["alias"] = row["alias"]
            else:
                item.update({
                    "name": row["name"], "email": row["email"], "phone": row["phone"],
                    "providers_used_count": int(row["providers_used_count"] or 0),
                })
            items.append(item)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_summary(self, *, tenant_id: uuid.UUID | None = None) -> dict:
        active_cutoff = _utcnow() - timedelta(days=ACTIVE_WINDOW_DAYS)
        new_cutoff = _utcnow() - timedelta(days=NEW_CUSTOMER_WINDOW_DAYS)
        rollup = self._customer_rollup_subquery(tenant_id=tenant_id)
        stats = (await self.db.execute(select(
            func.count().label("total"),
            func.count().filter(rollup.c.last_job_at >= active_cutoff).label("active"),
            func.count().filter(rollup.c.first_booking_at >= new_cutoff).label("new"),
            func.count().filter(rollup.c.completed_jobs >= 2).label("repeat"),
            func.count().filter(rollup.c.completed_jobs == 1).label("one_time"),
            func.count().filter(rollup.c.completed_jobs >= 1).label("with_completed"),
            func.count().filter(rollup.c.services_used_count >= 2).label("multi_service"),
            func.count().filter(rollup.c.providers_used_count >= 2).label("multi_provider"),
            func.avg(rollup.c.completed_jobs).filter(
                rollup.c.completed_jobs >= 1
            ).label("avg_completed"),
        ).select_from(rollup))).mappings().one()

        complaint_clauses = [
            CustomerComplaint.customer_id.isnot(None),
            CustomerComplaint.status.notin_(("resolved", "closed", "rejected")),
        ]
        invoice_clauses = [
            ServiceInvoice.customer_id.isnot(None), ServiceInvoice.payment_status == "paid",
        ]
        payment_clauses = [
            ServicePaymentRecord.customer_id.isnot(None),
            ServicePaymentRecord.reconciliation_status.in_(PAYMENT_RELIABILITY_DECIDED_STATUSES),
        ]
        if tenant_id:
            complaint_clauses.append(CustomerComplaint.tenant_id == tenant_id)
            invoice_clauses.append(ServiceInvoice.tenant_id == tenant_id)
            payment_clauses.append(ServicePaymentRecord.tenant_id == tenant_id)

        open_complaints = int((await self.db.execute(
            select(func.count(func.distinct(CustomerComplaint.customer_id)))
            .select_from(CustomerComplaint)
            .join(rollup, rollup.c.customer_id == CustomerComplaint.customer_id)
            .where(*complaint_clauses)
        )).scalar() or 0)
        confirmed_value = (await self.db.execute(
            select(func.coalesce(func.sum(ServiceInvoice.customer_payable_amount), 0))
            .select_from(ServiceInvoice)
            .join(rollup, rollup.c.customer_id == ServiceInvoice.customer_id)
            .where(*invoice_clauses)
        )).scalar() or Decimal("0")
        payment_rollup = (
            select(
                ServicePaymentRecord.customer_id.label("customer_id"),
                func.count(ServicePaymentRecord.id).label("decided"),
                func.sum(case(
                    (ServicePaymentRecord.reconciliation_status.in_(PAYMENT_RELIABILITY_REVIEW_STATUSES), 1),
                    else_=0,
                )).label("review"),
            )
            .where(*payment_clauses)
            .group_by(ServicePaymentRecord.customer_id)
            .subquery("hs_customer_payment_summary")
        )
        payment_review = int((await self.db.execute(
            select(func.count())
            .select_from(payment_rollup.join(
                rollup, rollup.c.customer_id == payment_rollup.c.customer_id
            ))
            .where(
                payment_rollup.c.decided >= PAYMENT_RELIABILITY_MIN_DECISIONS,
                payment_rollup.c.review > 0,
            )
        )).scalar() or 0)

        total = int(stats["total"] or 0)
        active = int(stats["active"] or 0)
        repeat = int(stats["repeat"] or 0)
        with_completed = int(stats["with_completed"] or 0)

        return {
            "total_customers": total,
            "active_customers": active,
            "new_customers": int(stats["new"] or 0),
            "repeat_customers": repeat,
            "one_time_customers": int(stats["one_time"] or 0),
            "inactive_customers": total - active,
            "returning_rate": round((repeat / with_completed * 100), 1) if with_completed else 0.0,
            "multi_service_customers": int(stats["multi_service"] or 0),
            "multi_provider_customers": int(stats["multi_provider"] or 0),
            "completed_job_customers": with_completed,
            "average_completed_jobs": round(float(stats["avg_completed"] or 0), 1),
            "confirmed_job_value": str(confirmed_value),
            "open_complaints": open_complaints,
            "payment_review": payment_review,
            "payment_review_available": True,
            "active_window_days": ACTIVE_WINDOW_DAYS,
            "new_customer_window_days": NEW_CUSTOMER_WINDOW_DAYS,
        }

    async def list_customers(self, *, q: str | None = None, activity: str | None = None,
                              repeat_status: str | None = None,
                              payment_reliability: str | None = None,
                              complaint_state: str | None = None,
                              sort: str = "last_activity_desc",
                              page: int = 1, page_size: int = 20,
                              tenant_id: uuid.UUID | None = None) -> dict:
        return await self._list_customers_sql(
            q=q, activity=activity, repeat_status=repeat_status,
            payment_reliability=payment_reliability,
            complaint_state=complaint_state, sort=sort,
            page=page, page_size=page_size, tenant_id=tenant_id,
        )

    async def get_customer_detail(self, customer_id: uuid.UUID, *, tenant_id: uuid.UUID | None = None) -> dict:
        agg = await self._customer_aggregates(customer_ids=[customer_id], tenant_id=tenant_id)
        a = agg.get(customer_id)
        if not a:
            raise NotFoundException("HomeServicesCustomer", str(customer_id))
        u = await self.db.get(User, customer_id)
        payment_reliability = (
            await self._payment_reliability_by_customer([customer_id], tenant_id=tenant_id)
        ).get(customer_id, {
            "status": "insufficient_data", "decided_records": 0, "review_records": 0,
        })

        service_clauses = [ServiceJob.customer_id == customer_id, ServiceJob.status == JOB_STATUS_COMPLETED]
        if tenant_id:
            service_clauses.append(ServiceJob.tenant_id == tenant_id)
        service_rows = (await self.db.execute(
            select(ServiceJob.offering_id, func.count()).where(*service_clauses).group_by(ServiceJob.offering_id)
        )).all()

        invoice_clauses = [ServiceInvoice.customer_id == customer_id, ServiceInvoice.payment_status == "paid"]
        if tenant_id:
            invoice_clauses.append(ServiceInvoice.tenant_id == tenant_id)
        confirmed_value = (await self.db.execute(
            select(func.coalesce(func.sum(ServiceInvoice.customer_payable_amount), 0)).where(*invoice_clauses)
        )).scalar() or Decimal("0")

        complaint_clauses = [
            CustomerComplaint.customer_id == customer_id,
            CustomerComplaint.status.notin_(("resolved", "closed", "rejected")),
        ]
        if tenant_id:
            complaint_clauses.append(CustomerComplaint.tenant_id == tenant_id)
        open_complaints = (await self.db.execute(
            select(func.count()).where(*complaint_clauses)
        )).scalar() or 0

        from app.engines.admin_catalog.models import MasterService
        service_ids = [o for o, _ in service_rows if o]
        master_services = {}
        if service_ids:
            ms_rows = (await self.db.execute(select(MasterService).where(MasterService.id.in_(service_ids)))).scalars().all()
            master_services = {m.id: m.service_name for m in ms_rows}

        result = {
            "customer_id": str(customer_id),
            "is_active": a["is_active"],
            "repeat_status": a["repeat_status"],
            "completed_jobs": a["completed_jobs"],
            "cancelled_jobs": a["cancelled_jobs"],
            "first_booking_at": a["first_booking_at"].isoformat() if a["first_booking_at"] else None,
            "last_activity_at": a["last_activity_at"].isoformat() if a["last_activity_at"] else None,
            "confirmed_job_value": str(confirmed_value),
            "open_complaints": open_complaints,
            "services_used_by_master_service": [
                {"offering_id": str(o), "master_service_name": master_services.get(o), "completed_jobs": c}
                for o, c in service_rows if o
            ],
            "payment_reliability": payment_reliability["status"],
            "payment_decisions": payment_reliability["decided_records"],
            "payment_records_needing_review": payment_reliability["review_records"],
        }
        if tenant_id:
            # Customer-privacy policy: alias only, never raw name/phone/
            # email, and no cross-tenant "providers used" -- this call is
            # already scoped to exactly one tenant by construction.
            result["alias"] = customer_alias(tenant_id, customer_id)
        else:
            result["name"] = u.full_name if u else None
            result["email"] = u.email if u else None
            result["phone"] = u.phone if u else None
            provider_rows = (await self.db.execute(
                select(ServiceJob.tenant_id, func.count()).where(
                    ServiceJob.customer_id == customer_id, ServiceJob.status == JOB_STATUS_COMPLETED,
                ).group_by(ServiceJob.tenant_id)
            )).all()
            from app.engines.tenant_engine.models import Tenant
            tenant_ids = [t for t, _ in provider_rows if t]
            tenants = {}
            if tenant_ids:
                t_rows = (await self.db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))).scalars().all()
                tenants = {t.id: (t.business_name or t.tenant_name) for t in t_rows}
            result["providers_used"] = [
                {"tenant_id": str(t), "provider_name": tenants.get(t), "completed_jobs": c}
                for t, c in provider_rows if t
            ]
        return result

    # ── Customer 360 Jobs tab ─────────────────────────────────────────────────
    async def get_customer_jobs(self, customer_id: uuid.UUID, *, page: int = 1, page_size: int = 20,
                                 tenant_id: uuid.UUID | None = None) -> dict:
        clauses = [ServiceJob.customer_id == customer_id]
        if tenant_id:
            clauses.append(ServiceJob.tenant_id == tenant_id)
        total = (await self.db.execute(
            select(func.count()).select_from(select(ServiceJob).where(*clauses).subquery())
        )).scalar() or 0
        rows = (await self.db.execute(
            select(ServiceJob).where(*clauses).order_by(ServiceJob.updated_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()

        from app.engines.admin_catalog.models import MasterService
        from app.engines.tenant_engine.models import Tenant
        offering_ids = {j.offering_id for j in rows if j.offering_id}
        tenant_ids = {j.tenant_id for j in rows if j.tenant_id}
        master_services = {}
        if offering_ids:
            ms_rows = (await self.db.execute(select(MasterService).where(MasterService.id.in_(offering_ids)))).scalars().all()
            master_services = {m.id: m.service_name for m in ms_rows}
        tenants = {}
        if tenant_ids:
            t_rows = (await self.db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))).scalars().all()
            tenants = {t.id: (t.business_name or t.tenant_name) for t in t_rows}

        return {
            "items": [{
                "job_id": str(j.id),
                "job_number": j.job_number,
                "master_service_name": master_services.get(j.offering_id),
                "provider_name": tenants.get(j.tenant_id),
                "tenant_id": str(j.tenant_id) if j.tenant_id else None,
                "status": j.status,
                "assignment_status": j.assignment_status,
                "scheduled_date": j.scheduled_date.isoformat() if j.scheduled_date else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            } for j in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    # ── Customer 360 Complaints tab ──────────────────────────────────────────
    async def get_customer_complaints(self, customer_id: uuid.UUID, *, page: int = 1, page_size: int = 20,
                                       tenant_id: uuid.UUID | None = None) -> dict:
        clauses = [CustomerComplaint.customer_id == customer_id]
        if tenant_id:
            clauses.append(CustomerComplaint.tenant_id == tenant_id)
        total = (await self.db.execute(
            select(func.count()).select_from(select(CustomerComplaint).where(*clauses).subquery())
        )).scalar() or 0
        rows = (await self.db.execute(
            select(CustomerComplaint).where(*clauses).order_by(CustomerComplaint.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return {
            "items": [{
                "complaint_id": str(c.id),
                "complaint_number": c.complaint_number,
                "title": c.title,
                "status": c.status,
                "severity": c.severity,
                "sla_status": c.sla_status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            } for c in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    # ── Customer 360 Payments tab ─────────────────────────────────────────────
    # Customer pays the provider directly -- ServiceOS never collects this
    # payment. ServicePaymentRecord.customer_id already scopes correctly.
    async def get_customer_payments(self, customer_id: uuid.UUID, *, page: int = 1, page_size: int = 20,
                                     tenant_id: uuid.UUID | None = None) -> dict:
        clauses = [ServicePaymentRecord.customer_id == customer_id]
        if tenant_id:
            clauses.append(ServicePaymentRecord.tenant_id == tenant_id)
        total = (await self.db.execute(
            select(func.count()).select_from(select(ServicePaymentRecord).where(*clauses).subquery())
        )).scalar() or 0
        rows = (await self.db.execute(
            select(ServicePaymentRecord).where(*clauses).order_by(ServicePaymentRecord.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return {
            "items": [{
                "payment_id": str(p.id),
                "job_id": str(p.job_id) if p.job_id else None,
                "collected_amount": str(p.collected_amount),
                "payment_mode": p.payment_mode,
                "payment_status": p.payment_status,
                "customer_confirmed": p.customer_confirmed,
                "provider_confirmed_at": p.provider_confirmed_at.isoformat() if p.provider_confirmed_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            } for p in rows],
            "total": total, "page": page, "page_size": page_size,
            "note": "Paid directly to provider. ServiceOS does not collect the job payment.",
        }

    # ── Customer 360 Activity & Audit tab ────────────────────────────────────
    # FinancialEvent.customer_id already scopes to this customer; this table
    # is exclusively written by invoice_payment (grep-verified elsewhere in
    # this codebase), so it's structurally Home-Services-only.
    async def get_customer_activity(self, customer_id: uuid.UUID, *, page: int = 1, page_size: int = 30,
                                     tenant_id: uuid.UUID | None = None) -> dict:
        """Read-only, composed timeline -- NOT a new table. Each entry is
        query-time-projected from its own canonical source (Booking/Job/
        Payment/FinancialEvent/Review/Complaint), tagged with source_system
        and source_record_id so nothing is duplicated or copied. Bounded per-
        source fetch (200 each) then merged and sorted in Python, matching
        this file's established _customer_aggregates merge pattern."""
        from app.engines.customer_reviews.models import CustomerReview
        LIMIT_PER_SOURCE = 200
        timeline: list[dict] = []

        booking_clauses = [ServiceBooking.customer_id == customer_id]
        if tenant_id:
            booking_clauses.append(ServiceBooking.tenant_id == tenant_id)
        bookings = (await self.db.execute(
            select(ServiceBooking).where(*booking_clauses)
            .order_by(ServiceBooking.created_at.desc()).limit(LIMIT_PER_SOURCE)
        )).scalars().all()
        for b in bookings:
            timeline.append({
                "event_type": "booking_created", "source_system": "booking",
                "source_record_id": str(b.id), "actor": "customer",
                "description": f"Booking {b.booking_number} created ({b.status})",
                "timestamp": b.created_at.isoformat() if b.created_at else None,
                "_sort": b.created_at,
            })

        job_clauses = [ServiceJob.customer_id == customer_id]
        if tenant_id:
            job_clauses.append(ServiceJob.tenant_id == tenant_id)
        jobs = (await self.db.execute(
            select(ServiceJob).where(*job_clauses)
            .order_by(ServiceJob.updated_at.desc()).limit(LIMIT_PER_SOURCE)
        )).scalars().all()
        for j in jobs:
            timeline.append({
                "event_type": f"job_{j.status}", "source_system": "service_job",
                "source_record_id": str(j.id), "actor": "system",
                "description": f"Job {j.job_number} status: {j.status}",
                "timestamp": j.updated_at.isoformat() if j.updated_at else None,
                "_sort": j.updated_at,
            })

        payment_clauses = [ServicePaymentRecord.customer_id == customer_id]
        if tenant_id:
            payment_clauses.append(ServicePaymentRecord.tenant_id == tenant_id)
        payments = (await self.db.execute(
            select(ServicePaymentRecord).where(*payment_clauses)
            .order_by(ServicePaymentRecord.created_at.desc()).limit(LIMIT_PER_SOURCE)
        )).scalars().all()
        for p in payments:
            timeline.append({
                "event_type": "payment_recorded", "source_system": "payment",
                "source_record_id": str(p.id), "actor": "provider",
                "description": f"Payment recorded ({p.payment_mode}, {p.payment_status})"
                                + (", customer confirmed" if p.customer_confirmed else ", awaiting customer confirmation"),
                "timestamp": p.created_at.isoformat() if p.created_at else None,
                "_sort": p.created_at,
            })
            if p.customer_confirmed_at:
                timeline.append({
                    "event_type": "payment_confirmed", "source_system": "payment",
                    "source_record_id": str(p.id), "actor": "customer",
                    "description": "Customer confirmed payment",
                    "timestamp": p.customer_confirmed_at.isoformat(),
                    "_sort": p.customer_confirmed_at,
                })

        fin_clauses = [FinancialEvent.customer_id == customer_id]
        if tenant_id:
            fin_clauses.append(FinancialEvent.tenant_id == tenant_id)
        fin_events = (await self.db.execute(
            select(FinancialEvent).where(*fin_clauses)
            .order_by(FinancialEvent.created_at.desc()).limit(LIMIT_PER_SOURCE)
        )).scalars().all()
        for e in fin_events:
            timeline.append({
                "event_type": e.event_type, "source_system": "financial_event",
                "source_record_id": str(e.record_id), "actor": e.actor_type,
                "description": e.event_type.replace("_", " "),
                "timestamp": e.created_at.isoformat() if e.created_at else None,
                "_sort": e.created_at,
            })

        review_clauses = [CustomerReview.customer_id == customer_id]
        if tenant_id:
            review_clauses.append(CustomerReview.tenant_id == tenant_id)
        reviews = (await self.db.execute(
            select(CustomerReview).where(*review_clauses)
            .order_by(CustomerReview.created_at.desc()).limit(LIMIT_PER_SOURCE)
        )).scalars().all()
        for r in reviews:
            timeline.append({
                "event_type": "review_submitted", "source_system": "review",
                "source_record_id": str(r.id), "actor": "customer",
                "description": f"Review submitted ({r.overall_rating}★)",
                "timestamp": r.created_at.isoformat() if r.created_at else None,
                "_sort": r.created_at,
            })

        complaint_clauses = [CustomerComplaint.customer_id == customer_id]
        if tenant_id:
            complaint_clauses.append(CustomerComplaint.tenant_id == tenant_id)
        complaints = (await self.db.execute(
            select(CustomerComplaint).where(*complaint_clauses)
            .order_by(CustomerComplaint.created_at.desc()).limit(LIMIT_PER_SOURCE)
        )).scalars().all()
        for c in complaints:
            timeline.append({
                "event_type": "complaint_created", "source_system": "complaint",
                "source_record_id": str(c.id), "actor": "customer",
                "description": f"Complaint {c.complaint_number} ({c.status})",
                "timestamp": c.created_at.isoformat() if c.created_at else None,
                "_sort": c.created_at,
            })

        # Customer Service Credits and account/security events: no canonical
        # per-customer read source is wired into this path yet -- omitted
        # rather than fabricated. Same for a dedicated audit-log source
        # beyond FinancialEvent.
        timeline = [t for t in timeline if t["_sort"] is not None]
        timeline.sort(key=lambda t: t["_sort"], reverse=True)
        for t in timeline:
            del t["_sort"]

        total = len(timeline)
        start = (page - 1) * page_size
        return {
            "items": timeline[start:start + page_size], "total": total, "page": page, "page_size": page_size,
            "sources_included": ["booking", "service_job", "payment", "financial_event", "review", "complaint"],
            "sources_not_available": ["customer_service_credit", "account_security_event"],
        }

    # ── Customer 360 Reviews tab ──────────────────────────────────────────────
    async def get_customer_reviews(self, customer_id: uuid.UUID, *, page: int = 1, page_size: int = 20,
                                    tenant_id: uuid.UUID | None = None) -> dict:
        from app.engines.customer_reviews.models import CustomerReview
        clauses = [CustomerReview.customer_id == customer_id]
        if tenant_id:
            clauses.append(CustomerReview.tenant_id == tenant_id)
        total = (await self.db.execute(
            select(func.count()).select_from(select(CustomerReview).where(*clauses).subquery())
        )).scalar() or 0
        rows = (await self.db.execute(
            select(CustomerReview).where(*clauses).order_by(CustomerReview.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return {
            "items": [{
                "review_id": str(r.id),
                "review_number": r.review_number,
                "job_id": str(r.job_id) if r.job_id else None,
                "overall_rating": r.overall_rating,
                "provider_rating": r.provider_rating,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            } for r in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    # ── Customer 360 Addresses tab ────────────────────────────────────────────
    # No dedicated customer-address model is wired into this path -- the only
    # address data available is ServiceBooking.address_snapshot (a per-
    # booking JSON snapshot, not a reusable address book). Reporting the
    # distinct snapshots actually used, not fabricating a full address book.
    async def get_customer_addresses(self, customer_id: uuid.UUID) -> dict:
        rows = (await self.db.execute(
            select(ServiceBooking.address_snapshot, ServiceBooking.city, ServiceBooking.zipcode, ServiceBooking.created_at)
            .where(ServiceBooking.customer_id == customer_id, ServiceBooking.address_snapshot.isnot(None))
            .order_by(ServiceBooking.created_at.desc())
        )).all()
        seen = set()
        items = []
        for snapshot, city, zipcode, created_at in rows:
            key = (city, zipcode, str(snapshot))
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "address_snapshot": snapshot, "city": city, "zipcode": zipcode,
                "last_used_at": created_at.isoformat() if created_at else None,
            })
        return {"items": items, "total": len(items)}
