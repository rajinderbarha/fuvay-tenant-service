"""Immutable provider warranty evidence issued when a service job completes."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urlsplit

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
        snapshot = job.warranty_certificate_snapshot
        provider = dict(snapshot.get("provider") or {})
        # logo_url is a presentation-only field added after certificates were
        # already live. Fill it once for historical snapshots so an existing
        # warranty also receives the provider letterhead; all legal/service
        # evidence remains untouched and immutable.
        if not provider.get("logo_url") and getattr(job, "tenant_id", None):
            from app.engines.tenant_engine.models import Tenant

            tenant = await db.get(Tenant, job.tenant_id)
            if tenant and tenant.logo_url:
                provider["logo_url"] = tenant.logo_url
                snapshot = {**snapshot, "provider": provider}
                job.warranty_certificate_snapshot = snapshot
                await db.flush()
        return snapshot

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
            "logo_url": getattr(tenant, "logo_url", None),
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
    """Render a polished, provider-branded A4 warranty card.

    The provider identity and logo URL come from the immutable certificate
    snapshot. Logo loading is best-effort and restricted to HTTPS Cloudinary
    assets; a clean initials mark is used when the image cannot be loaded.
    """
    import httpx
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.platypus import (
        KeepTogether, Paragraph, SimpleDocTemplate,
        Spacer, Table, TableStyle,
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

    def safe_text(value) -> str:
        # Helvetica is WinAnsi. Expand unsupported glyphs visibly instead of
        # silently dropping customer-supplied text from the certificate.
        return _clean(value).encode("cp1252", errors="backslashreplace").decode("cp1252")

    def p(value) -> str:
        return html.escape(safe_text(value)).replace("\n", "<br/>")

    def load_logo(url: str | None):
        value = _clean(url)
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (host == "cloudinary.com" or host.endswith(".cloudinary.com")):
            return None
        try:
            response = httpx.get(value, follow_redirects=True, timeout=4.0)
            final_host = (urlsplit(str(response.url)).hostname or "").lower()
            content_type = response.headers.get("content-type", "").lower()
            if (
                response.status_code >= 400
                or not (final_host == "cloudinary.com" or final_host.endswith(".cloudinary.com"))
                or not content_type.startswith("image/")
                or len(response.content) > 2_000_000
            ):
                return None
            return ImageReader(BytesIO(response.content))
        except Exception:
            return None

    provider = snapshot.get("provider") or {}
    address = snapshot.get("service_address") or ""
    if isinstance(address, dict):
        address = ", ".join(_clean(value) for value in address.values() if value)
    days = snapshot.get("warranty_days")
    certificate = safe_text(snapshot.get("certificate_number")) or "Not recorded"
    provider_name = safe_text(provider.get("name")) or "Service Provider"
    logo = load_logo(provider.get("logo_url"))
    navy = colors.HexColor("#102F2A")
    teal = colors.HexColor("#0E8174")
    mint = colors.HexColor("#E6F5F1")
    ink = colors.HexColor("#172321")
    muted = colors.HexColor("#60706D")
    line = colors.HexColor("#D9E3E0")
    paper = colors.HexColor("#F7FAF9")

    output = BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
        topMargin=42 * mm, bottomMargin=18 * mm,
        title=f"Warranty Certificate {certificate}", author="Fuvay",
    )

    def page_chrome(canvas, document):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(paper)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(navy)
        canvas.rect(0, height - 35 * mm, width, 35 * mm, fill=1, stroke=0)
        canvas.setFillColor(teal)
        canvas.rect(0, height - 37 * mm, width, 2 * mm, fill=1, stroke=0)

        logo_x, logo_y, logo_size = 17 * mm, height - 29 * mm, 19 * mm
        canvas.setFillColor(colors.white)
        canvas.roundRect(logo_x, logo_y, logo_size, logo_size, 3 * mm, fill=1, stroke=0)
        initials = "".join(part[:1] for part in provider_name.split()[:2]).upper() or "SP"
        rendered_logo = False
        if logo:
            try:
                img_w, img_h = logo.getSize()
                scale = min((logo_size - 4 * mm) / img_w, (logo_size - 4 * mm) / img_h)
                draw_w, draw_h = img_w * scale, img_h * scale
                canvas.drawImage(logo, logo_x + (logo_size - draw_w) / 2,
                                 logo_y + (logo_size - draw_h) / 2,
                                 draw_w, draw_h, preserveAspectRatio=True, mask="auto")
                rendered_logo = True
            except Exception:
                pass
        if not rendered_logo:
            canvas.setFillColor(teal)
            canvas.setFont("Helvetica-Bold", 17)
            canvas.drawCentredString(logo_x + logo_size / 2, logo_y + 6.4 * mm, initials)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawString(41 * mm, height - 17 * mm, provider_name[:46])
        canvas.setFillColor(colors.HexColor("#B8D6CF"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(41 * mm, height - 22 * mm, "Provider Warranty Certificate")
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawRightString(width - 17 * mm, height - 17 * mm, "WARRANTY CARD")
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(width - 17 * mm, height - 22 * mm, f"Certificate {certificate}")

        canvas.setStrokeColor(line)
        canvas.line(17 * mm, 15 * mm, width - 17 * mm, 15 * mm)
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 7.2)
        canvas.drawString(17 * mm, 11 * mm, f"Terms version: {safe_text(snapshot.get('terms_version'))}")
        canvas.restoreState()

    styles = getSampleStyleSheet()
    eyebrow = ParagraphStyle("eyebrow", parent=styles["Normal"], fontName="Helvetica-Bold",
                             fontSize=7.5, leading=10, textColor=teal, spaceAfter=3)
    heading = ParagraphStyle("heading", parent=styles["Heading2"], fontName="Helvetica-Bold",
                             fontSize=12, leading=15, textColor=ink, spaceBefore=9, spaceAfter=7)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica",
                          fontSize=8.5, leading=12, textColor=ink)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, leading=10, textColor=muted)
    label = ParagraphStyle("label", parent=small, fontName="Helvetica-Bold", fontSize=6.8,
                           leading=8, textColor=muted, spaceAfter=2)
    value = ParagraphStyle("value", parent=body, fontName="Helvetica-Bold", fontSize=8.5,
                           leading=11, textColor=ink)
    hero_title = ParagraphStyle("hero", parent=styles["Heading1"], fontName="Helvetica-Bold",
                                fontSize=22, leading=25, textColor=colors.white, alignment=TA_LEFT)
    hero_sub = ParagraphStyle("hero-sub", parent=body, fontSize=8.5, leading=12,
                              textColor=colors.HexColor("#D9F0EB"))
    centered = ParagraphStyle("centered", parent=body, alignment=TA_CENTER)

    def detail_cell(title, content):
        return [Paragraph(p(title).upper(), label), Paragraph(p(content) or "Not recorded", value)]

    warranty_title = f"{p(days)} DAY WARRANTY" if days is not None else "PROVIDER WARRANTY"
    statement = (
        f"You have a warranty of {days} days on your completed service."
        if days is not None else "Your provider warranty details are recorded below."
    )
    hero = Table([
        [Paragraph("WORKMANSHIP PROTECTION", ParagraphStyle(
            "hero-eye", parent=eyebrow, textColor=colors.HexColor("#8AD5C7"))), ""],
        [Paragraph(warranty_title, hero_title), Paragraph("VALID UNTIL", ParagraphStyle(
            "hero-label", parent=label, textColor=colors.HexColor("#B8D6CF"), alignment=TA_CENTER))],
        [Paragraph(p(statement), hero_sub), Paragraph(p(f"Valid until: {date_text(snapshot.get('warranty_expires_at'))}"),
                                                      ParagraphStyle("hero-date", parent=centered,
                                                                     fontName="Helvetica-Bold",
                                                                     fontSize=9.5, textColor=colors.white))],
    ], colWidths=[doc.width * .62, doc.width * .38], rowHeights=[7 * mm, 10 * mm, 12 * mm])
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), teal),
        ("BOX", (0, 0), (-1, -1), 0.6, teal),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 7 * mm),
        ("RIGHTPADDING", (0, 0), (0, -1), 5 * mm),
        ("LEFTPADDING", (1, 0), (1, -1), 4 * mm),
        ("RIGHTPADDING", (1, 0), (1, -1), 6 * mm),
        ("LINEBEFORE", (1, 1), (1, -1), 0.5, colors.HexColor("#57AFA4")),
        ("ROUNDEDCORNERS", [4 * mm]),
    ]))

    details = Table([
        [detail_cell("Certificate number", certificate), detail_cell("Service", snapshot.get("service_name"))],
        [detail_cell("Job number", snapshot.get("job_number")), detail_cell("Booking number", snapshot.get("booking_number"))],
        [detail_cell("Customer", snapshot.get("customer_name")), detail_cell("Issued on", date_text(snapshot.get("issued_at")))],
        [detail_cell("Service address", address), detail_cell("Work completed", snapshot.get("work_summary"))],
    ], colWidths=[doc.width / 2, doc.width / 2])
    details.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, line),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
    ]))

    provider_lines = [f"<b>{p(provider_name)}</b>"]
    if provider.get("registered_address"):
        provider_lines.append(p(provider.get("registered_address")))
    contacts = " | ".join(filter(None, [safe_text(provider.get("phone")), safe_text(provider.get("email"))]))
    if contacts:
        provider_lines.append(p(contacts))
    if provider.get("gst_number"):
        provider_lines.append(f"GST: {p(provider.get('gst_number'))}")
    provider_box = Table([[
        Paragraph("RESPONSIBLE SERVICE PROVIDER", eyebrow),
        Paragraph("<br/>".join(provider_lines), body),
    ]], colWidths=[doc.width * .31, doc.width * .69])
    provider_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), mint),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B9DDD5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ("ROUNDEDCORNERS", [3 * mm]),
    ]))

    story = [hero, Spacer(1, 6 * mm), Paragraph("SERVICE DETAILS", heading), details,
             Spacer(1, 5 * mm), provider_box, Paragraph("WARRANTY TERMS", heading)]
    for number, term in enumerate(snapshot.get("terms") or WARRANTY_TERMS, start=1):
        story.append(KeepTogether(Table([
            [Paragraph(str(number), ParagraphStyle(
                f"term-number-{number}", parent=centered, fontName="Helvetica-Bold",
                fontSize=7, textColor=colors.white)), Paragraph(p(term), body)]
        ], colWidths=[6 * mm, doc.width - 6 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), teal),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 0),
            ("TOPPADDING", (0, 0), (0, 0), 1.6 * mm),
            ("BOTTOMPADDING", (0, 0), (0, 0), 1.6 * mm),
            ("LEFTPADDING", (1, 0), (1, 0), 3 * mm),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (1, 0), (1, 0), 1 * mm),
            ("BOTTOMPADDING", (1, 0), (1, 0), 2 * mm),
        ]))))
    story.extend([
        Table([[Paragraph("KEEP THIS DOCUMENT", eyebrow),
                Paragraph("Keep this certificate as evidence of your provider warranty.", body)]],
              colWidths=[doc.width * .31, doc.width * .69], style=TableStyle([
                  ("LINEABOVE", (0, 0), (-1, 0), 0.6, line),
                  ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                  ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ])),
    ])
    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)

    # Platypus knows the current page while drawing but not the final count.
    # Add the authoritative Page X of Y footer in a short merge pass.
    from pypdf import PdfReader, PdfWriter

    source = PdfReader(BytesIO(output.getvalue()))
    writer = PdfWriter()
    total_pages = len(source.pages)
    for number, page in enumerate(source.pages, start=1):
        overlay_bytes = BytesIO()
        overlay = pdf_canvas.Canvas(overlay_bytes, pagesize=A4)
        overlay.setFillColor(muted)
        overlay.setFont("Helvetica", 7.2)
        overlay.drawRightString(A4[0] - 17 * mm, 11 * mm,
                                f"Page {number} of {total_pages} | Provider warranty powered by Fuvay")
        overlay.save()
        page.merge_page(PdfReader(BytesIO(overlay_bytes.getvalue())).pages[0])
        writer.add_page(page)
    writer.add_metadata({
        "/Title": f"Warranty Certificate {certificate}",
        "/Author": "Fuvay",
    })
    final_output = BytesIO()
    writer.write(final_output)
    return final_output.getvalue()


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
