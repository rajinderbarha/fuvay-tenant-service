from io import BytesIO

import pytest
from pypdf import PdfReader
from pypdf.generic import IndirectObject

from app.engines.final_records.warranty_certificate import render_certificate_pdf


@pytest.fixture
def snapshot():
    return {
        "certificate_number": "WRN-20260911-JOB-7",
        "terms_version": "2026-09-01",
        "issued_at": "2026-09-11T10:15:00+00:00",
        "warranty_expires_at": "2026-09-16T10:15:00+00:00",
        "warranty_days": 5,
        "job_number": "JOB-7",
        "booking_number": "BK-7",
        "service_name": "AC service",
        "customer_name": "Customer Name",
        "service_address": {"line1": "12 Main Road", "city": "Ludhiana"},
        "work_summary": "Cleaned the filter and checked cooling.",
        "provider": {
            "name": "Provider & Co",
            "registered_address": "14 Park Road, Ludhiana",
            "phone": "+919000000000",
            "email": "provider@example.test",
            "gst_number": "GST123",
        },
        "terms": ["The named provider is responsible for the workmanship warranty."],
    }


def _read_pdf(snapshot):
    payload = render_certificate_pdf(snapshot)
    assert payload.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(payload), strict=True)
    assert all(isinstance(page.raw_get("/Contents"), IndirectObject) for page in reader.pages)
    return reader, "\n".join(page.extract_text() for page in reader.pages)


def test_pdf_contains_customer_warranty_and_immutable_service_evidence(snapshot):
    reader, text = _read_pdf(snapshot)
    assert "Provider Warranty Certificate" in text
    assert "You have a warranty of 5 days" in text
    for expected in (
        "2026-09-16 10:15 UTC", "2026-09-11 10:15 UTC", "WRN-20260911-JOB-7",
        "BK-7", "JOB-7", "AC service", "Customer Name", "12 Main Road, Ludhiana",
        "Provider & Co", "+919000000000", "provider@example.test", "GST123",
        "workmanship warranty", "Terms version: 2026-09-01",
    ):
        assert expected in text
    assert len(reader.pages) == 1
    assert "Page 1 of 1" in text


def test_pdf_preserves_longer_provider_warranty(snapshot):
    snapshot.update(warranty_days=30, warranty_expires_at="2026-10-11T10:15:00Z")
    _, text = _read_pdf(snapshot)
    assert "You have a warranty of 30 days" in text
    assert "2026-10-11 10:15 UTC" in text
    assert "warranty of 5 days" not in text


def test_pdf_serializes_special_characters_as_text_not_commands(snapshot):
    snapshot["customer_name"] = r"Renée (A & B) \ BT ET <Customer>"
    snapshot["provider"]["name"] = "Provider € & Co"
    _, text = _read_pdf(snapshot)
    assert snapshot["customer_name"] in text
    assert "Provider € & Co" in text
    assert "You have a warranty of 5 days" in text


def test_pdf_wraps_and_paginates_all_content_without_losing_terms(snapshot):
    snapshot["work_summary"] = "BEGIN " + "W" * 350 + " FINISH"
    snapshot["terms"] = [
        f"Condition {number}: " + "The provider reviews supporting evidence. " * 5
        for number in range(100)
    ]
    reader, text = _read_pdf(snapshot)
    assert len(reader.pages) > 3
    assert "W" * 350 in "".join(text.split())
    assert "BEGIN" in text and "FINISH" in text
    for number in range(100):
        assert f"Condition {number}:" in text
    assert "Keep this certificate as evidence" in text
    for number, page in enumerate(reader.pages, start=1):
        assert f"Page {number} of {len(reader.pages)}" in page.extract_text()
        positions = []
        page.extract_text(visitor_text=lambda value, _cm, tm, _font, _size:
                          positions.append(tm[5]) if value.strip() else None)
        assert all(30 <= y <= 794 for y in positions)


def test_pdf_handles_missing_optional_fields():
    _, text = _read_pdf({"warranty_days": 5})
    assert "You have a warranty of 5 days" in text
    assert "Valid until: Not recorded" in text
    assert "The named service provider" in text


def test_pdf_preserves_non_winansi_text_with_explicit_unicode_escapes(snapshot):
    snapshot["customer_name"] = "客户"
    _, text = _read_pdf(snapshot)
    assert r"\u5ba2\u6237" in text
