"""Seat-plan top-up invoices are immutable, readable commercial records."""
from io import BytesIO

from pypdf import PdfReader

from app.engines.vertical_catalog.topup_invoice import render_topup_invoice_pdf


def _invoice():
    return {
        "invoice_number": "FV2026HS00000001",
        "issued_at": "2026-09-26",
        "gateway_order_id": "order_enterprise_01",
        "gateway_payment_id": "pay_enterprise_01",
        "currency": "INR",
        "amount": 1180,
        "credited_amount": 1000,
        "tax_amount": 180,
        "seats_granted": 3,
        "plan": {"name": "Growth Seat Plan", "gst_percent": 18, "validity_days": 365},
        "issuer": {
            "brand_name": "Fuvay", "legal_name": "Fuvay Technologies Private Limited",
            "gstin": "03ABCDE1234F1Z5", "support_email": "support@fuvay.com",
            "primary_color": "#0F6B60", "accent_color": "#2F9E8F",
            "address": {"line1": "Platform Office", "city": "Bassi Pathana", "state": "Punjab", "zipcode": "140412", "country": "India"},
        },
        "buyer": {
            "business_name": "Test Provider", "legal_name": "Test Provider",
            "gstin": "03AAAAA0000A1Z5", "billing_email": "billing@example.com",
            "address": {"line1": "Main Road", "city": "Bassi Pathana", "state": "Punjab", "zipcode": "140412", "country": "India"},
        },
    }


def test_invoice_pdf_has_one_readable_page_and_financial_split():
    payload = render_topup_invoice_pdf(_invoice())
    assert payload.startswith(b"%PDF")
    reader = PdfReader(BytesIO(payload))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "FV2026HS00000001" in text
    assert "Growth Seat Plan" in text
    assert "3 technician seats" in text
    assert "INR 1,000.00" in text
    assert "INR 180.00" in text
    assert "INR 1,180.00" in text
