"""Immutable provider warranty evidence issued when a service job completes."""
from __future__ import annotations

import html
import re
import textwrap
from datetime import datetime, timezone
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

TERMS_VERSION = "2026-09-01"
WARRANTY_TERMS = [
    "The named service provider, not Fuvay, is responsible for the workmanship warranty.",
    "Fuvay does not collect or hold a provider security deposit.",
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


def render_certificate_pdf(snapshot: dict) -> bytes:
    """Render the issued snapshot as a standalone, paginated PDF certificate.

    PDF standard fonts keep this independent of server fonts or HTML renderers.
    pypdf serializes text operands, so customer-supplied text cannot introduce
    PDF drawing commands. The body uses Courier for predictable line wrapping.
    """
    from pypdf import PdfWriter
    from pypdf.generic import (
        ByteStringObject,
        ContentStream,
        DictionaryObject,
        FloatObject,
        NameObject,
    )

    def date_text(value) -> str:
        if not value:
            return "Not recorded"
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except ValueError:
            return _clean(value)

    provider = snapshot.get("provider") or {}
    address = snapshot.get("service_address") or ""
    if isinstance(address, dict):
        address = ", ".join(_clean(value) for value in address.values() if value)
    days = snapshot.get("warranty_days")
    statement = (
        f"You have a warranty of {days} days on your completed service."
        if days is not None else "Your provider warranty details are recorded below."
    )
    # Each block carries its font size and whether it is a section heading.
    blocks = [
        ("Provider Warranty Certificate", 19, True),
        (statement, 12, True),
        (f"Valid until: {date_text(snapshot.get('warranty_expires_at'))}", 10, False),
        ("Service details", 12, True),
        (f"Certificate: {_clean(snapshot.get('certificate_number'))}", 10, False),
        (f"Job: {_clean(snapshot.get('job_number'))}", 10, False),
        (f"Booking: {_clean(snapshot.get('booking_number'))}", 10, False),
        (f"Service: {_clean(snapshot.get('service_name'))}", 10, False),
        (f"Customer: {_clean(snapshot.get('customer_name'))}", 10, False),
        (f"Service address: {_clean(address)}", 10, False),
        (f"Work completed: {_clean(snapshot.get('work_summary'))}", 10, False),
        (f"Issued: {date_text(snapshot.get('issued_at'))}", 10, False),
        ("Responsible service provider", 12, True),
        (_clean(provider.get("name")) or "Service Provider", 10, False),
        (f"Registered address: {_clean(provider.get('registered_address'))}", 10, False),
        (f"Phone: {_clean(provider.get('phone'))}", 10, False),
        (f"Email: {_clean(provider.get('email'))}", 10, False),
        (f"GST: {_clean(provider.get('gst_number'))}", 10, False),
        ("Warranty terms", 12, True),
    ]
    for number, term in enumerate(snapshot.get("terms") or WARRANTY_TERMS, start=1):
        blocks.append((f"{number}. {_clean(term)}", 10, False))
    blocks.extend([
        (f"Terms version: {_clean(snapshot.get('terms_version'))}", 9, False),
        ("Keep this certificate as evidence of your provider warranty.", 9, False),
    ])

    writer = PdfWriter()
    writer.add_metadata({
        "/Title": f"Warranty Certificate {_clean(snapshot.get('certificate_number'))}",
        "/Author": "Fuvay",
    })
    fonts = DictionaryObject({
        NameObject(key): DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject(name),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        })
        for key, name in (("/F1", "/Courier"), ("/F2", "/Courier-Bold"))
    })
    page_width, page_height, margin = 595, 842, 48
    streams = []

    def new_page():
        page = writer.add_blank_page(width=page_width, height=page_height)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fonts})
        stream = ContentStream(None, writer)
        page.replace_contents(stream)
        streams.append(stream)
        return stream, page_height - margin

    def draw_line(stream, text, size, bold, y):
        # WinAnsi is the encoding of PDF standard fonts. Preserve any unsupported
        # characters as explicit Unicode escapes instead of silently losing data.
        encoded = text.encode("cp1252", errors="backslashreplace")
        stream.operations.extend([
            ([], b"BT"),
            ([NameObject("/F2" if bold else "/F1"), FloatObject(size)], b"Tf"),
            ([FloatObject(1), FloatObject(0), FloatObject(0), FloatObject(1),
              FloatObject(margin), FloatObject(y)], b"Tm"),
            ([ByteStringObject(encoded)], b"Tj"),
            ([], b"ET"),
        ])

    stream, y = new_page()
    for text, size, heading in blocks:
        # Encode before wrapping because unsupported characters expand to escapes.
        text = text.encode("cp1252", errors="backslashreplace").decode("cp1252")
        width = int((page_width - 2 * margin) / (size * 0.6))
        lines = textwrap.wrap(text, width=width, break_long_words=True) or [""]
        leading = size * 1.5
        if heading:
            y -= 10
            if y - leading * min(len(lines) + 1, 3) < margin + 25:
                stream, y = new_page()
        for line in lines:
            if y < margin + 25:
                stream, y = new_page()
            draw_line(stream, line, size, heading, y)
            y -= leading
        y -= 5 if heading else 3

    for number, stream in enumerate(streams, start=1):
        draw_line(stream, f"Fuvay | Provider warranty | Page {number} of {len(streams)}", 8,
                  False, 30)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


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
