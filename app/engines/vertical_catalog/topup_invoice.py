"""Immutable provider tax invoices for Home Services top-up-plan purchases.

The invoice is rendered on demand from snapshots captured with the payment.
Changing a plan, provider profile, or platform setting later therefore cannot
rewrite a historical commercial document.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.engines.settings_engine.branding import read_platform_branding, unwrap_setting_value
from app.engines.settings_engine.models import PlatformSetting
from app.engines.settings_engine.registry import ConfigurationRegistry
from app.engines.tenant_engine.models import Tenant, TenantBilling, TenantBusinessProfile


INVOICE_PROFILE_KEY = "platform_topup_invoice_profile"
_BUNDLED_FUVAY_LOGO = (
    Path(__file__).resolve().parents[3]
    / "frontend" / "tenant-portal" / "public" / "brand" / "fuvay-green-light.png"
)


def _text(value: Any, fallback: str = "Not provided") -> str:
    cleaned = str(value or "").strip()
    return cleaned or fallback


def _money(value: Any, currency: str = "INR") -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return f"{currency} {number:,.2f}"


def _address(snapshot: dict) -> str:
    value = snapshot.get("address")
    if isinstance(value, dict):
        parts = [
            value.get("line1"), value.get("line2"), value.get("city"),
            value.get("state"), value.get("zipcode"), value.get("country"),
        ]
        return ", ".join(str(part).strip() for part in parts if str(part or "").strip())
    return _text(value)


def _invoice_logo(issuer: dict) -> Image | None:
    """Return the configured document logo with the bundled Fuvay logo as fallback.

    Remote artwork is deliberately restricted to HTTPS Cloudinary URLs, matching
    the platform-branding validation. Invoice generation remains available when
    the remote asset is temporarily unreachable.
    """
    sources: list[bytes | str] = []
    configured_url = str(issuer.get("document_logo_url") or "").strip()
    parsed = urlsplit(configured_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https" and (host == "cloudinary.com" or host.endswith(".cloudinary.com")):
        try:
            import httpx

            response = httpx.get(configured_url, follow_redirects=True, timeout=4.0)
            final_host = (urlsplit(str(response.url)).hostname or "").lower()
            content_type = response.headers.get("content-type", "").lower()
            if (
                response.status_code < 400
                and (final_host == "cloudinary.com" or final_host.endswith(".cloudinary.com"))
                and content_type.startswith("image/")
                and len(response.content) <= 2_000_000
            ):
                sources.append(response.content)
        except Exception:
            pass

    if _BUNDLED_FUVAY_LOGO.is_file():
        sources.append(str(_BUNDLED_FUVAY_LOGO))

    for source in sources:
        try:
            image_source = BytesIO(source) if isinstance(source, bytes) else source
            reader = ImageReader(image_source)
            image_width, image_height = reader.getSize()
            if isinstance(image_source, BytesIO):
                image_source.seek(0)
            max_width, max_height = 46 * mm, 15 * mm
            scale = min(max_width / image_width, max_height / image_height)
            logo = Image(image_source, width=image_width * scale, height=image_height * scale)
            logo.hAlign = "LEFT"
            return logo
        except Exception:
            continue
    return None


async def resolve_invoice_snapshots(
    db: AsyncSession,
    *,
    tenant_id,
    plan_snapshot: dict | None,
) -> tuple[dict, dict, dict]:
    """Resolve the current parties once, immediately before invoice issue."""
    definition = ConfigurationRegistry.get(INVOICE_PROFILE_KEY)
    profile = dict(definition.default_value if definition else {})
    setting = (await db.execute(
        select(PlatformSetting).where(
            PlatformSetting.key == INVOICE_PROFILE_KEY,
            PlatformSetting.status == "active",
        )
    )).scalar_one_or_none()
    configured = unwrap_setting_value(setting.value) if setting else None
    if isinstance(configured, dict):
        profile.update(configured)

    branding, _ = await read_platform_branding(db)
    issuer = {
        **profile,
        "brand_name": branding.brand_name,
        "primary_color": branding.primary_color,
        "accent_color": branding.accent_color,
        "document_logo_url": branding.document_logo_url,
    }

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    business = (await db.execute(
        select(TenantBusinessProfile).where(TenantBusinessProfile.tenant_id == tenant_id)
    )).scalar_one_or_none()
    billing = (await db.execute(
        select(TenantBilling).where(TenantBilling.tenant_id == tenant_id)
    )).scalar_one_or_none()
    registered = dict(business.registered_address or {}) if business else {}
    buyer_address = registered or {
        "line1": tenant.address_line1,
        "line2": tenant.address_line2,
        "city": tenant.city,
        "state": tenant.state,
        "zipcode": tenant.zipcode,
        "country": tenant.country,
    }
    buyer = {
        "business_name": tenant.business_name or tenant.tenant_name,
        "legal_name": tenant.legal_name or tenant.business_name or tenant.tenant_name,
        "gstin": (business.gstin if business else None) or tenant.gst_number,
        "billing_email": (billing.billing_email if billing else None) or tenant.email,
        "address": buyer_address,
    }
    return dict(plan_snapshot or {}), issuer, buyer


async def ensure_invoice_snapshots(db: AsyncSession, order) -> None:
    """Issue an invoice exactly once inside the payment transaction."""
    if order.invoice_number and order.plan_snapshot_json and order.invoice_issuer_snapshot_json and order.invoice_buyer_snapshot_json:
        return
    plan = dict(order.plan_snapshot_json or {})
    if not plan and order.topup_plan_id:
        row = (await db.execute(text("""
            SELECT name, description, base_amount, gst_percent, seats, validity_days
              FROM hs_topup_plans WHERE id = :plan_id
        """), {"plan_id": str(order.topup_plan_id)})).mappings().first()
        plan = dict(row or {})
    plan, issuer, buyer = await resolve_invoice_snapshots(
        db, tenant_id=order.tenant_id, plan_snapshot=plan,
    )
    order.plan_snapshot_json = plan
    order.invoice_issuer_snapshot_json = issuer
    order.invoice_buyer_snapshot_json = buyer
    if not order.invoice_number:
        sequence = int((await db.execute(
            text("SELECT nextval('hs_topup_invoice_number_seq')")
        )).scalar_one())
        issued = order.captured_at or order.created_at
        # 16 characters, unique and sequential. This stays within the common
        # Indian GST invoice-number length constraint while remaining readable.
        order.invoice_number = f"FV{issued:%Y}HS{sequence:08d}"
    if not order.invoice_issued_at:
        order.invoice_issued_at = order.captured_at or order.created_at


def invoice_payload(order) -> dict:
    return {
        "invoice_number": order.invoice_number,
        "issued_at": order.invoice_issued_at.date().isoformat() if order.invoice_issued_at else None,
        "gateway_order_id": order.gateway_order_id,
        "gateway_payment_id": order.gateway_payment_id,
        "currency": order.currency,
        "amount": float(order.amount or 0),
        "credited_amount": float(order.credited_amount or 0),
        "tax_amount": float(order.tax_amount or 0),
        "seats_granted": int(order.seats_granted or 0),
        "plan": dict(order.plan_snapshot_json or {}),
        "issuer": dict(order.invoice_issuer_snapshot_json or {}),
        "buyer": dict(order.invoice_buyer_snapshot_json or {}),
    }


def render_topup_invoice_pdf(invoice: dict) -> bytes:
    """Return a one-page, printable PDF for one captured plan purchase."""
    issuer = dict(invoice.get("issuer") or {})
    buyer = dict(invoice.get("buyer") or {})
    plan = dict(invoice.get("plan") or {})
    currency = _text(invoice.get("currency"), "INR")
    primary = colors.HexColor(_text(issuer.get("primary_color"), "#0F6B60"))
    accent = colors.HexColor(_text(issuer.get("accent_color"), "#2F9E8F"))
    document_title = "TAX INVOICE" if str(issuer.get("gstin") or "").strip() else "PAYMENT INVOICE"

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"{document_title.title()} {invoice.get('invoice_number', '')}",
        author=_text(issuer.get("legal_name"), _text(issuer.get("brand_name"), "Fuvay")),
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="InvoiceTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=26, textColor=primary, alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name="InvoiceSmall", parent=styles["BodyText"], fontSize=8.5,
        leading=12, textColor=colors.HexColor("#5F6B66"),
    ))
    styles.add(ParagraphStyle(
        name="InvoiceBody", parent=styles["BodyText"], fontSize=9.5,
        leading=14, textColor=colors.HexColor("#18211E"),
    ))
    styles.add(ParagraphStyle(
        name="InvoiceRight", parent=styles["InvoiceBody"], alignment=TA_RIGHT,
    ))

    brand_name = _text(issuer.get("brand_name"), "Fuvay")
    legal_name = _text(issuer.get("legal_name"), brand_name)
    logo = _invoice_logo(issuer)
    brand_block = [
        *([logo, Spacer(1, 2 * mm)] if logo is not None else []),
        Paragraph(
            ("" if logo is not None else f"<b>{brand_name}</b><br/>")
            + f"<font size='9'>{legal_name}</font>",
            styles["InvoiceBody"],
        ),
    ]
    header = Table([
        [
            brand_block,
            Paragraph(document_title, styles["InvoiceTitle"]),
        ]
    ], colWidths=[95 * mm, 79 * mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 2, primary),
    ]))

    meta = Table([
        [Paragraph("Invoice number", styles["InvoiceSmall"]), Paragraph(_text(invoice.get("invoice_number")), styles["InvoiceRight"])],
        [Paragraph("Invoice date", styles["InvoiceSmall"]), Paragraph(_text(invoice.get("issued_at")), styles["InvoiceRight"])],
        [Paragraph("Payment reference", styles["InvoiceSmall"]), Paragraph(_text(invoice.get("gateway_payment_id")), styles["InvoiceRight"])],
        [Paragraph("Order reference", styles["InvoiceSmall"]), Paragraph(_text(invoice.get("gateway_order_id")), styles["InvoiceRight"])],
    ], colWidths=[42 * mm, 50 * mm])
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE4E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F7F6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    party = Table([
        [Paragraph("SUPPLIER", styles["InvoiceSmall"]), Paragraph("BILLED TO", styles["InvoiceSmall"])],
        [
            Paragraph(
                f"<b>{legal_name}</b><br/>{_address(issuer)}<br/>GSTIN: {_text(issuer.get('gstin'))}<br/>"
                f"Email: {_text(issuer.get('support_email'))}",
                styles["InvoiceBody"],
            ),
            Paragraph(
                f"<b>{_text(buyer.get('legal_name'), _text(buyer.get('business_name')))}</b><br/>"
                f"{_address(buyer)}<br/>GSTIN: {_text(buyer.get('gstin'))}<br/>"
                f"Email: {_text(buyer.get('billing_email'))}",
                styles["InvoiceBody"],
            ),
        ],
    ], colWidths=[87 * mm, 87 * mm])
    party.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CCD7D3")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE4E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF4F1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    description = _text(plan.get("name"), "Home Services top-up plan")
    seats = int(invoice.get("seats_granted") or 0)
    validity_days = int(plan.get("validity_days") or 0)
    entitlement = (
        f"{seats} technician seat{'s' if seats != 1 else ''}; "
        + (f"valid for {validity_days} days" if validity_days else "no expiry")
    )
    items = Table([
        ["Description", "Entitlement", "Taxable value", "GST", "Total"],
        [
            Paragraph(description, styles["InvoiceBody"]),
            Paragraph(entitlement, styles["InvoiceBody"]),
            _money(invoice.get("credited_amount"), currency),
            _money(invoice.get("tax_amount"), currency),
            _money(invoice.get("amount"), currency),
        ],
    ], colWidths=[53 * mm, 43 * mm, 29 * mm, 23 * mm, 26 * mm], repeatRows=1)
    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7DFDC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    totals = Table([
        ["Taxable value", _money(invoice.get("credited_amount"), currency)],
        [f"GST ({float(plan.get('gst_percent') or 0):g}%)", _money(invoice.get("tax_amount"), currency)],
        ["Total paid", _money(invoice.get("amount"), currency)],
    ], colWidths=[42 * mm, 38 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), primary),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, accent),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    footer = KeepTogether([
        Paragraph(
            "Payment captured electronically. This system-generated invoice is valid without a signature. "
            "The taxable value is credited as platform usage credit; GST is recorded separately and never "
            "added to the usable credit balance.",
            styles["InvoiceSmall"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Support: {_text(issuer.get('support_email'))} | Invoice ID: {_text(invoice.get('invoice_number'))}",
            styles["InvoiceSmall"],
        ),
    ])

    document.build([
        header,
        Spacer(1, 7 * mm),
        Table([[meta, ""]], colWidths=[92 * mm, 82 * mm]),
        Spacer(1, 7 * mm),
        party,
        Spacer(1, 8 * mm),
        items,
        Spacer(1, 6 * mm),
        totals,
        Spacer(1, 13 * mm),
        footer,
    ])
    return buffer.getvalue()
