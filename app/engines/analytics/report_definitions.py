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
    export_formats:  List[str] = field(default_factory=lambda: ["csv", "xlsx"])
    sensitive_cols:  List[str] = field(default_factory=list)
    default_sort:    str = "created_at"


_ADMIN_FILTERS = [
    "date_from", "date_to", "category_id", "tenant_id",
    "offering_id", "city", "zone_id", "status",
]
_PROVIDER_FILTERS = [
    "date_from", "date_to", "category_id", "offering_id",
    "staff_member_id", "status",
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
    allowed_filters=_ADMIN_FILTERS + ["payment_status", "commission_status"],
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_COMMISSION,
    report_name="Commission Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS + ["commission_status"],
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
    allowed_filters=_ADMIN_FILTERS + ["review_rating"],
    sensitive_cols=_SENSITIVE,
))
_reg(ReportDefinition(
    report_key=RPT_ADMIN_COMPLAINT,
    report_name="Complaints & Disputes Report",
    scope=SCOPE_ADMIN,
    allowed_filters=_ADMIN_FILTERS + ["complaint_status"],
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
    allowed_filters=_PROVIDER_FILTERS + ["review_rating"],
    sensitive_cols=_SENSITIVE,
))
_reg(ReportDefinition(
    report_key=RPT_PROVIDER_COMPLAINTS,
    report_name="Complaints & Disputes Report",
    scope=SCOPE_PROVIDER,
    allowed_filters=_PROVIDER_FILTERS + ["complaint_status"],
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
    allowed_filters=_PROVIDER_FILTERS,
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
