"""Immutable provider warranty evidence issued when a service job completes."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

TERMS_VERSION = "2026-09-01"
WARRANTY_TERMS = [
    "The named service provider, not ServiceOS, is responsible for the workmanship warranty.",
    "ServiceOS does not collect or hold a provider security deposit.",
    "During the warranty period the customer may report a repeat issue with supporting evidence.",
    "The provider reviews the case, may inspect the work, and may propose rework, refund, credit, or another mutually agreed settlement.",
    "The technician performs field work on the provider's behalf; the provider remains responsible for supervision, customer communication, and resolution.",
    "Any settlement takes effect only when the customer and provider agree to it.",
    "Missing a configured service or complaint response SLA may cause a usage-credit penalty and reduce provider account health.",
]


def _clean(value) -> str:
    return str(value or "").strip()


def _address(tenant) -> str:
    return ", ".join(filter(None, [
        _clean(tenant.address_line1), _clean(tenant.address_line2),
        _clean(tenant.city), _clean(tenant.district), _clean(tenant.state),
        _clean(tenant.zipcode), _clean(tenant.country),
    ]))


async def issue_warranty_certificate(db: AsyncSession, job, booking=None) -> dict:
    """Create the certificate snapshot once; later tenant edits cannot rewrite it."""
    if job.warranty_certificate_snapshot:
        return job.warranty_certificate_snapshot

    from app.engines.admin_catalog.models import MasterService
    from app.engines.final_records.models import ServiceBooking
    from app.engines.tenant_engine.models import Tenant

    if booking is None:
        booking = await db.get(ServiceBooking, job.booking_id)
    tenant = await db.get(Tenant, job.tenant_id) if job.tenant_id else None
    service = await db.get(MasterService, job.offering_id) if job.offering_id else None
    issued_at = datetime.now(timezone.utc)
    raw_number = f"WRN-{issued_at:%Y%m%d}-{job.job_number or job.id}"
    certificate_number = re.sub(r"[^A-Za-z0-9-]", "", raw_number)[:80]

    provider_name = (
        _clean(getattr(tenant, "legal_name", None))
        or _clean(getattr(tenant, "business_name", None))
        or _clean(getattr(tenant, "tenant_name", None))
        or "Service Provider"
    )
    snapshot = {
        "certificate_number": certificate_number,
        "terms_version": TERMS_VERSION,
        "issued_at": issued_at.isoformat(),
        "warranty_expires_at": job.warranty_expires_at.isoformat() if job.warranty_expires_at else None,
        "warranty_days": job.warranty_days_snapshot,
        "job_number": job.job_number,
        "booking_number": getattr(booking, "booking_number", None),
        "service_name": getattr(service, "service_name", None) or "Home service",
        "customer_name": getattr(booking, "customer_name", None),
        "service_address": getattr(job, "address_snapshot", None),
        "work_summary": (job.completion_data or {}).get("work_summary"),
        "provider": {
            "name": provider_name,
            "business_name": getattr(tenant, "business_name", None),
            "legal_name": getattr(tenant, "legal_name", None),
            "tenant_code": getattr(tenant, "tenant_code", None),
            "gst_number": getattr(tenant, "gst_number", None),
            "phone": getattr(tenant, "phone", None),
            "email": getattr(tenant, "email", None),
            "registered_address": _address(tenant) if tenant else "",
        },
        "terms": list(WARRANTY_TERMS),
    }
    job.warranty_certificate_number = certificate_number
    job.warranty_certificate_snapshot = snapshot
    job.warranty_certificate_issued_at = issued_at
    await db.flush()
    return snapshot


def render_certificate_html(snapshot: dict) -> str:
    """Portable downloadable HTML document with no external asset dependency."""
    e = lambda value: html.escape(_clean(value))
    provider = snapshot.get("provider") or {}
    terms = "".join(f"<li>{e(term)}</li>" for term in snapshot.get("terms") or [])
    address = snapshot.get("service_address") or {}
    service_address = ", ".join(e(v) for v in address.values() if v) if isinstance(address, dict) else e(address)
    return f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>Warranty {e(snapshot.get('certificate_number'))}</title>
<style>body{{font-family:Arial,sans-serif;color:#172033;max-width:820px;margin:36px auto;padding:0 24px;line-height:1.5}}h1{{margin-bottom:4px}}.muted{{color:#60708a}}table{{width:100%;border-collapse:collapse;margin:24px 0}}td{{padding:9px;border-bottom:1px solid #dfe5ee;vertical-align:top}}td:first-child{{width:32%;font-weight:700}}.box{{border:1px solid #cfd8e6;border-radius:12px;padding:18px;margin:18px 0}}li{{margin:8px 0}}@media print{{body{{margin:0}}}}</style></head><body>
<h1>Provider Warranty Certificate</h1><div class=\"muted\">Immutable service evidence · Terms {e(snapshot.get('terms_version'))}</div>
<table><tr><td>Certificate</td><td>{e(snapshot.get('certificate_number'))}</td></tr><tr><td>Job</td><td>{e(snapshot.get('job_number'))}</td></tr><tr><td>Booking</td><td>{e(snapshot.get('booking_number'))}</td></tr><tr><td>Service</td><td>{e(snapshot.get('service_name'))}</td></tr><tr><td>Customer</td><td>{e(snapshot.get('customer_name'))}</td></tr><tr><td>Service address</td><td>{service_address}</td></tr><tr><td>Warranty</td><td>{e(snapshot.get('warranty_days'))} days, valid until {e(snapshot.get('warranty_expires_at'))}</td></tr><tr><td>Work completed</td><td>{e(snapshot.get('work_summary'))}</td></tr></table>
<div class=\"box\"><h2>Responsible service provider</h2><strong>{e(provider.get('name'))}</strong><br>{e(provider.get('registered_address'))}<br>{e(provider.get('phone'))} · {e(provider.get('email'))}<br>GST: {e(provider.get('gst_number'))}</div>
<h2>Warranty terms</h2><ol>{terms}</ol><p class=\"muted\">Issued {e(snapshot.get('issued_at'))}. Keep this document as evidence of the provider warranty.</p></body></html>"""
