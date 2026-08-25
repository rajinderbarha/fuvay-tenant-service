"""Sprint 28 — Report definitions registry.

Each report definition describes:
  - report_key       unique identifier
  - report_name      human label
  - scope            'admin' | 'provider'
  - allowed_filters  list of accepted filter names
  - export_formats   csv / xlsx
  - sensitive_cols   excluded from exports unless admin_full permission
  - default_sort     default ORDER BY field
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

from app.engines.analytics.constants import (
    SCOPE_ADMIN, SCOPE_PROVIDER,
    RPT_ADMIN_PLATFORM_SUMMARY, RPT_ADMIN_CATEGORY_PERFORMANCE,
    RPT_ADMIN_PROVIDER_PERFORMANCE, RPT_ADMIN_FINANCIAL,
    RPT_ADMIN_COMMISSION, RPT_ADMIN_WALLET, RPT_ADMIN_QUALITY,
    RPT_ADMIN_COMPLAINT, RPT_ADMIN_STAFF_PERFORMANCE, RPT_ADMIN_AUDIT_ACTIVITY,
    RPT_PROVIDER_DASHBOARD, RPT_PROVIDER_FINANCIAL, RPT_PROVIDER_STAFF_PERFORMANCE,
    RPT_PROVIDER_REVIEWS, RPT_PROVIDER_COMPLAINTS, RPT_PROVIDER_WALLET_LEDGER,
    RPT_PROVIDER_JOBS, RPT_PROVIDER_APPOINTMENTS, RPT_PROVIDER_LEADS,
)


@dataclass
class ReportDefinition:
    report_key:      str
    report_name:     str
    scope:           str
    allowed_filters: List[str]
    # CSV only. `report_service.run_report` generates a file solely under
    # `if export_format == "csv"`, and nothing in the codebase can write an
    # xlsx (no openpyxl/xlsxwriter anywhere). Advertising "xlsx" meant a client
    # could request it, get a run marked `completed` with `csv_content: null`,
    # and never receive a file — confirmed live. Declare what we can actually
    # deliver; re-add "xlsx" in the same commit that implements the writer.
    export_formats:  List[str] = field(default_factory=lambda: ["csv"])
    sensitive_cols:  List[str] = field(default_factory=list)
    default_sort:    str = "created_at"


# Same correction as the provider list below: the admin report SQL binds only
# the date range (verified — zero references to city / zone_id / offering_id /
# category_id / status anywhere in the admin queries), so advertising those
# eight filters told a client it could narrow a report in ways the query never
# honoured. Widen this only alongside the predicate that binds the column.
_ADMIN_FILTERS = ["date_from", "date_to"]
# `allowed_filters` is a PROMISE: `run_report` validates against it, and a
# client builds its filter UI from it. Every provider report used to advertise
# the full list below while `_generate_rows` bound only the dates into the SQL,
# so category/offering/staff/status were accepted and silently ignored —
# confirmed live, the jobs report returned the same 16 rows for
# status=accepted, status=pending_assignment and a specific technician.
#
# Each report now advertises exactly what its own query applies. Widen a list
# only in the same change that binds the column.
_PROVIDER_FILTERS = ["date_from", "date_to"]

#: service_jobs really has status / offering_id / category_id /
#: assigned_staff_id, and the jobs query now binds all four.
_PROVIDER_JOB_FILTERS = _PROVIDER_FILTERS + [
    "status", "offering_id", "category_id", "staff_member_id",
]
_SENSITIVE = ["customer_phone", "customer_email", "customer_name", "student_name",
              "student_phone", "student_email", "address_snapshot"]

_REGISTRY: dict[str, ReportDefinition] = {}


def _reg(d: ReportDefinition) -> ReportDefinition:
    _REGISTRY[d.report_key] = d
    return d


# ── Admin reports ──────────────────────────────────────────────────────────────
_reg(ReportDefinition(
    report_key=RPT_ADMIN_PLATFORM_SUMMARY,
    report_name="Platform Summary Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_CATEGORY_PERFORMANCE,
    report_name="Category Performance Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_PROVIDER_PERFORMANCE,
    report_name="Provider Performance Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
    sensitive_cols=["owner_email", "owner_phone"],
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_FINANCIAL,
    report_name="Financial Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_COMMISSION,
    report_name="Commission Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_WALLET,
    report_name="Wallet Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_QUALITY,
    report_name="Quality & Reviews Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
    sensitive_cols=_SENSITIVE,
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_COMPLAINT,
    report_name="Complaints & Disputes Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
    sensitive_cols=_SENSITIVE,
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_STAFF_PERFORMANCE,
    report_name="Staff Performance Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS + ["staff_member_id"],
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_AUDIT_ACTIVITY,
    report_name="Audit Activity Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS,
))

# ── Provider reports ───────────────────────────────────────────────────────────
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_DASHBOARD,
    report_name="Provider Dashboard Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS,
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_FINANCIAL,
    report_name="Provider Financial Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS + ["payment_status", "commission_status"],
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_STAFF_PERFORMANCE,
    report_name="Staff Performance Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS,
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_REVIEWS,
    report_name="Reviews & Ratings Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS,
    sensitive_cols=_SENSITIVE,
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_COMPLAINTS,
    report_name="Complaints & Disputes Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS,
    sensitive_cols=_SENSITIVE,
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_WALLET_LEDGER,
    report_name="Wallet Ledger Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS,
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_JOBS,
    report_name="Jobs Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_JOB_FILTERS,
    sensitive_cols=_SENSITIVE,
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_APPOINTMENTS,
    report_name="Appointments Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS,
    sensitive_cols=_SENSITIVE,
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_LEADS,
    report_name="Leads Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS,
    sensitive_cols=_SENSITIVE,
))


class ReportDefinitionRegistry:
    @staticmethod
    def get(report_key: str) -> ReportDefinition | None:
        return _REGISTRY.get(report_key)

    @staticmethod
    def all_for_scope(scope: str) -> list[ReportDefinition]:
        return [d for d in _REGISTRY.values() if d.scope == scope]

    @staticmethod
    def all() -> list[ReportDefinition]:
        return list(_REGISTRY.values())
