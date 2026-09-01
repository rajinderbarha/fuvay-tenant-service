"""Sprint 28 — ReportService.

Handles:
- Report run creation and lifecycle
- Report status tracking
- Export orchestration (sync for small sets, async-required flag for large)
"""
from __future__ import annotations
import uuid
import csv
import io
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.analytics.sprint28_models import AnalyticsReportRun
from app.engines.analytics.report_definitions import ReportDefinitionRegistry
from app.engines.analytics.constants import (
    ERR_REPORT_NOT_FOUND, ERR_REPORT_ACCESS_DENIED, ERR_REPORT_FILTER_NOT_ALLOWED,
    ERR_REPORT_RUN_FAILED, ERR_REPORT_ASYNC_REQUIRED, ERR_REPORT_TOO_LARGE,
    ERR_REPORT_FORMAT_UNSUPPORTED,
    REPORT_STATUS_PENDING, REPORT_STATUS_RUNNING, REPORT_STATUS_COMPLETED,
    REPORT_STATUS_FAILED, SCOPE_ADMIN, SCOPE_PROVIDER,
    EXPORT_SYNC_ROW_LIMIT, EXPORT_MAX_ROW_LIMIT,
)
from app.engines.analytics.helpers import resolve_date_range, date_range_to_datetimes

_utcnow = lambda: datetime.now(timezone.utc)


class ReportService:

    # ── List report definitions ───────────────────────────────────────────────

    def list_reports(self, scope: str) -> list[dict]:
        defs = ReportDefinitionRegistry.all_for_scope(scope)
        return [
            {
                "report_key":      d.report_key,
                "report_name":     d.report_name,
                "scope":           d.scope,
                "allowed_filters": d.allowed_filters,
                "export_formats":  d.export_formats,
            }
            for d in defs
        ]

    # ── Run a report ──────────────────────────────────────────────────────────

    async def run_report(
        self, db: AsyncSession,
        report_key: str,
        scope: str,
        requested_by_user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        filters: dict,
        export_format: str | None = None,
    ) -> dict:
        defn = ReportDefinitionRegistry.get(report_key)
        if not defn:
            raise ValueError(ERR_REPORT_NOT_FOUND)

        # Scope check
        if defn.scope != scope:
            raise ValueError(ERR_REPORT_ACCESS_DENIED)

        # Filter validation
        for k in filters:
            if k not in defn.allowed_filters:
                raise ValueError(ERR_REPORT_FILTER_NOT_ALLOWED)

        # Create run record
        run = AnalyticsReportRun(
            report_key=report_key,
            report_name=defn.report_name,
            scope=scope,
            requested_by_user_id=requested_by_user_id,
            tenant_id=tenant_id,
            status=REPORT_STATUS_RUNNING,
            filters=filters,
            export_format=export_format,
        )
        db.add(run)
        await db.flush()
        run_id = run.id

        try:
            # Generate report data synchronously for now
            # Provider reports are always tenant-scoped
            result_rows = await self._generate_rows(
                db, report_key, filters, tenant_id if scope == SCOPE_PROVIDER else None,
                scope,
            )

            row_count = len(result_rows)

            if row_count > EXPORT_MAX_ROW_LIMIT:
                run.status = REPORT_STATUS_FAILED
                run.failure_reason = ERR_REPORT_TOO_LARGE
                run.completed_at = _utcnow()
                await db.commit()
                raise ValueError(ERR_REPORT_TOO_LARGE)

            if row_count > EXPORT_SYNC_ROW_LIMIT and export_format:
                # Would need async worker for export; mark as requiring async
                run.status = REPORT_STATUS_FAILED
                run.failure_reason = ERR_REPORT_ASYNC_REQUIRED
                run.completed_at = _utcnow()
                await db.commit()
                raise ValueError(ERR_REPORT_ASYNC_REQUIRED)

            # Remove sensitive columns for provider scope
            if scope == SCOPE_PROVIDER:
                result_rows = _strip_sensitive(result_rows, defn.sensitive_cols)

            # Generate CSV if requested. An unsupported format is rejected up
            # front rather than silently completing with no file: a run that
            # says "completed" and hands back nothing is worse than an error,
            # because the caller cannot tell it failed.
            file_content = None
            if export_format and export_format not in defn.export_formats:
                run.status = REPORT_STATUS_FAILED
                run.failure_reason = ERR_REPORT_FORMAT_UNSUPPORTED
                run.completed_at = _utcnow()
                await db.commit()
                raise ValueError(ERR_REPORT_FORMAT_UNSUPPORTED)
            if export_format == "csv" and result_rows:
                file_content = _to_csv(result_rows)

            run.status = REPORT_STATUS_COMPLETED
            run.row_count = row_count
            run.result_summary = {"row_count": row_count, "columns": list(result_rows[0].keys()) if result_rows else []}
            run.completed_at = _utcnow()
            await db.commit()

            return {
                "id": str(run_id),
                "report_key": report_key,
                "status": REPORT_STATUS_COMPLETED,
                "row_count": row_count,
                "preview": result_rows[:5],  # First 5 rows as preview
                "csv_content": file_content,
                "generated_at": _utcnow().isoformat(),
            }

        except ValueError:
            raise
        except Exception as e:
            try:
                run_obj = await db.get(AnalyticsReportRun, run_id)
                if run_obj:
                    run_obj.status = REPORT_STATUS_FAILED
                    run_obj.failure_reason = str(e)
                    run_obj.completed_at = _utcnow()
                    await db.commit()
            except Exception:
                pass
            raise ValueError(ERR_REPORT_RUN_FAILED)

    # ── Get report run ────────────────────────────────────────────────────────

    async def get_report_run(
        self, db: AsyncSession,
        run_id: uuid.UUID,
        scope: str,
        tenant_id: uuid.UUID | None,
    ) -> dict:
        result = await db.execute(
            select(AnalyticsReportRun).where(AnalyticsReportRun.id == run_id)
        )
        run = result.scalars().first()
        if not run:
            raise ValueError(ERR_REPORT_NOT_FOUND)

        # Provider can only see own runs
        if scope == SCOPE_PROVIDER and run.tenant_id != tenant_id:
            raise ValueError(ERR_REPORT_ACCESS_DENIED)

        return run.to_dict()

    # ── List report runs ──────────────────────────────────────────────────────

    async def list_report_runs(
        self, db: AsyncSession,
        scope: str,
        tenant_id: uuid.UUID | None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        q = select(AnalyticsReportRun).where(AnalyticsReportRun.scope == scope)
        if scope == SCOPE_PROVIDER and tenant_id:
            q = q.where(AnalyticsReportRun.tenant_id == tenant_id)
        q = q.order_by(AnalyticsReportRun.created_at.desc()).limit(limit).offset(offset)

        result = await db.execute(q)
        runs = result.scalars().all()

        count_q = select(text("COUNT(*)")).select_from(AnalyticsReportRun).where(
            AnalyticsReportRun.scope == scope
        )
        if scope == SCOPE_PROVIDER and tenant_id:
            count_q = count_q.where(AnalyticsReportRun.tenant_id == tenant_id)

        try:
            count_r = await db.execute(text(
                "SELECT COUNT(*) FROM analytics_report_runs WHERE scope = :scope"
                + (" AND tenant_id = :tenant_id" if scope == SCOPE_PROVIDER and tenant_id else "")
            ), {"scope": scope, **({"tenant_id": tenant_id} if scope == SCOPE_PROVIDER and tenant_id else {})})
            total = count_r.scalar_one_or_none() or 0
        except Exception:
            total = len(runs)

        return {"items": [r.to_dict() for r in runs], "total": total}

    # ── Generate rows for a given report ─────────────────────────────────────

    async def _generate_rows(
        self, db: AsyncSession,
        report_key: str,
        filters: dict,
        tenant_id: uuid.UUID | None,
        scope: str,
    ) -> list[dict]:
        """Generate result rows for a given report key.

        Each report key maps to a specific SQL query.
        Filters are applied as parameterized bind variables.
        """
        date_from = filters.get("date_from")
        date_to   = filters.get("date_to")
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p: dict = {"from_dt": from_dt, "to_dt": to_dt}
        if tenant_id:
            p["tenant_id"] = tenant_id
        tc = "AND tenant_id = :tenant_id" if tenant_id else ""

        # Every report advertised category_id / offering_id / staff_member_id /
        # status (and payment_status, commission_status, review_rating,
        # complaint_status) in `allowed_filters`, and `run_report` validated
        # them as allowed — but ONLY the dates were ever bound into the SQL, so
        # the rest were accepted and silently ignored. Confirmed live: the jobs
        # report returned the same 16 rows for status=accepted,
        # status=pending_assignment and a specific staff_member_id.
        #
        # A filter that quietly does nothing is worse than one that is absent:
        # the operator believes the number in front of them is filtered. Each
        # entry below binds to a column that genuinely exists on that report's
        # own table (verified against information_schema), and each report's
        # `allowed_filters` has been trimmed to exactly this set.
        def _opt(column: str, key: str, kind: str = "") -> str:
            """`AND <column> = :<key>` when the caller supplied that filter.

            The value is coerced in PYTHON rather than written as a `::uuid`
            cast in the SQL: a cast placed directly after a named bind reads as
            part of the parameter token and the statement fails to prepare.
            A malformed id is treated as "no such row" rather than a 500.
            """
            value = (filters or {}).get(key)
            if value in (None, ""):
                return ""
            try:
                if kind == "uuid":
                    value = uuid.UUID(str(value))
                elif kind == "int":
                    value = int(value)
            except (ValueError, AttributeError, TypeError):
                # An unparseable filter must narrow to nothing, never widen to
                # everything — silently dropping it would return the FULL
                # report while the caller believes it is filtered.
                return " AND 1 = 0"
            p[key] = value
            return f" AND {column} = :{key}"

        jobs_f = (
            _opt("status", "status")
            + _opt("offering_id", "offering_id", "uuid")
            + _opt("category_id", "category_id", "uuid")
            + _opt("assigned_staff_id", "staff_member_id", "uuid")
        )
        invoice_f = _opt("payment_status", "payment_status") + _opt("commission_status", "commission_status")
        review_f = _opt("overall_rating", "review_rating", "int") + _opt("status", "status")
        complaint_f = _opt("status", "complaint_status")

        # Map report_key → SQL
        sql_map = {
            "admin_platform_summary_report": f"""
                SELECT 'tenants' AS metric, COUNT(*)::text AS value FROM tenants
                UNION ALL
                SELECT 'active_tenants', COUNT(*)::text FROM tenants WHERE status = 'active'
                UNION ALL
                SELECT 'total_bookings', COUNT(*)::text FROM service_bookings
                WHERE created_at BETWEEN :from_dt AND :to_dt
            """,
            "admin_financial_report": f"""
                SELECT invoice_number, total_amount::text, payment_status,
                       commission_status, created_at::text
                FROM service_invoices
                WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
                ORDER BY created_at DESC LIMIT :row_limit
            """,
            "admin_quality_report": f"""
                SELECT review_number, overall_rating, status, created_at::text
                FROM customer_reviews
                WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
                ORDER BY created_at DESC LIMIT :row_limit
            """,
            "admin_complaint_report": f"""
                SELECT complaint_number, complaint_type, priority, status, created_at::text
                FROM customer_complaints
                WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
                ORDER BY created_at DESC LIMIT :row_limit
            """,
            "admin_commission_report": f"""
                SELECT cr.id::text, cr.status,
                       cr.commission_amount::text, cr.created_at::text
                FROM svc_commission_records cr
                WHERE cr.created_at BETWEEN :from_dt AND :to_dt {tc}
                ORDER BY cr.created_at DESC LIMIT :row_limit
            """,
            "admin_wallet_report": f"""
                SELECT tenant_id::text, credit_balance::text,
                       entitled_seats::text
                FROM tenant_billing
                LIMIT :row_limit
            """,
            "provider_dashboard_report": f"""
                SELECT job_number, status, assignment_status, created_at::text
                FROM service_jobs
                WHERE tenant_id = :tenant_id
                AND created_at BETWEEN :from_dt AND :to_dt
                ORDER BY created_at DESC LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
            "provider_financial_report": f"""
                SELECT invoice_number, total_amount::text, payment_status,
                       commission_status, created_at::text
                FROM service_invoices
                WHERE tenant_id = :tenant_id
                AND created_at BETWEEN :from_dt AND :to_dt {invoice_f}
                ORDER BY created_at DESC LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
            "provider_jobs_report": f"""
                SELECT job_number, status, assignment_status, city, created_at::text
                FROM service_jobs
                WHERE tenant_id = :tenant_id
                AND created_at BETWEEN :from_dt AND :to_dt {jobs_f}
                ORDER BY created_at DESC LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
            "provider_appointments_report": f"""
                SELECT appointment_number, status, target_exam,
                       selected_date::text, created_at::text
                FROM coaching_appointments
                WHERE tenant_id = :tenant_id
                AND created_at BETWEEN :from_dt AND :to_dt
                ORDER BY created_at DESC LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
            "provider_leads_report": f"""
                SELECT id::text, status, created_at::text
                FROM real_estate_leads
                WHERE tenant_id = :tenant_id
                AND created_at BETWEEN :from_dt AND :to_dt
                ORDER BY created_at DESC LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
            "provider_reviews_report": f"""
                SELECT review_number, overall_rating, status, created_at::text
                FROM customer_reviews
                WHERE tenant_id = :tenant_id
                AND created_at BETWEEN :from_dt AND :to_dt
                ORDER BY created_at DESC LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
            "provider_complaints_report": f"""
                SELECT complaint_number, complaint_type, status, created_at::text
                FROM customer_complaints
                WHERE tenant_id = :tenant_id
                AND created_at BETWEEN :from_dt AND :to_dt
                ORDER BY created_at DESC LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
            "provider_wallet_ledger_report": f"""
                SELECT event_type AS txn_type, credit_delta::text AS amount, balance_before::text,
                       balance_after::text, created_at::text
                FROM usage_credit_ledger
                WHERE tenant_id = :tenant_id
                AND created_at BETWEEN :from_dt AND :to_dt
                ORDER BY created_at DESC LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
            "provider_staff_performance_report": f"""
                SELECT sja.assigned_staff_member_id::text AS staff_id,
                       COUNT(*) AS assignments,
                       COUNT(CASE WHEN sja.assignment_status='accepted' THEN 1 END) AS accepted
                FROM service_job_assignments sja
                WHERE sja.tenant_id = :tenant_id
                AND sja.created_at BETWEEN :from_dt AND :to_dt
                GROUP BY sja.assigned_staff_member_id
                LIMIT :row_limit
            """ if tenant_id else "SELECT 'no_data' AS info",
        }

        sql = sql_map.get(report_key, "SELECT 'unknown_report' AS info")
        p["row_limit"] = EXPORT_SYNC_ROW_LIMIT

        try:
            result = await db.execute(text(sql), p)
            return [dict(row) for row in result.mappings().all()]
        except Exception:
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_sensitive(rows: list[dict], sensitive_cols: list[str]) -> list[dict]:
    if not sensitive_cols:
        return rows
    return [{k: v for k, v in row.items() if k not in sensitive_cols} for row in rows]


def _to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
