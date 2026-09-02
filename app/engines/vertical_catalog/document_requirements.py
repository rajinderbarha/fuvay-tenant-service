"""Verification document requirement resolver.

Single source of truth for "which documents does this tenant need to
verify" -- resolved from vertical + business_type + country, never a
frontend-hardcoded array (per the Verification Documents onboarding spec).
Both the tenant-facing documents endpoint and
home_services_setup_service's Documents-section completion check import
from here, so there is exactly one manifest, not two that can drift.

POLICY_VERSION exists so a future requirement change is a new constant, not
a silent behavior change with no audit trail -- bump it whenever the
manifest below changes in a way that affects what's required.
"""
from __future__ import annotations

POLICY_VERSION = "2026-09-01"

# Requirement keys are stable identifiers, never display text -- the display
# label/description/examples can change without invalidating already-mapped
# TenantDocument.doc_type rows.
_BASE_REQUIREMENTS = [
    {
        "key": "business_registration",
        "label": "Business registration or ownership proof",
        "why": "Confirms the legal existence of your business.",
        "accepted_examples": ["Certificate", "License", "Incorporation"],
        "required": True,
        "requires_document_number": False,
        "requires_expiry": False,
    },
    {
        "key": "identity_proof",
        "label": "Owner identity proof",
        "why": "Confirms you are authorized to represent this business.",
        "accepted_examples": ["PAN card", "Aadhaar", "Passport", "Driver's license"],
        "required": True,
        "requires_document_number": True,
        "requires_expiry": True,
    },
    {
        "key": "address_proof",
        "label": "Registered address proof",
        "why": "Confirms the business's registered address.",
        "accepted_examples": ["Utility bill", "Bank statement", "Rent agreement"],
        "required": True,
        "requires_document_number": False,
        "requires_expiry": False,
    },
]

_GST_REQUIREMENT = {
    "key": "gst_certificate",
    "label": "GST registration certificate",
    "why": "Required for GST-registered businesses; skip if you are not GST-registered.",
    "accepted_examples": ["GST certificate"],
    "required": False,
    "requires_document_number": True,
    "requires_expiry": False,
}

# Vertical-specific additions layered on top of the base three. Home Services
# has none beyond the base + optional GST; other verticals get the same
# baseline until their own compliance capability is defined -- never a 500,
# never a fabricated requirement.
_VERTICAL_EXTRA_REQUIREMENTS: dict[str, list[dict]] = {
    "real_estate": [
        {
            "key": "rera_registration",
            "label": "RERA registration certificate",
            "why": "Required for real estate businesses operating under RERA-regulated states.",
            "accepted_examples": ["RERA certificate"],
            "required": False,
            "requires_document_number": True,
            "requires_expiry": True,
        },
    ],
}

# Technician evidence is provider-owned. ServiceOS verifies the business that
# joins the marketplace; the provider is legally and operationally responsible
# for checking the people it sends to a customer's address. Optional skill
# evidence may still be stored in the provider's private workspace, but it is
# never a platform approval or assignment gate.
_TECHNICIAN_BASE_REQUIREMENTS = [
    {
        "key": "technician_skill_certificate",
        "label": "Skill certificate (optional, provider records only)",
        "why": "Helps the provider keep its own training records. ServiceOS does not verify or require it.",
        "accepted_examples": ["ITI certificate", "Trade certificate", "Manufacturer training certificate"],
        "required": False,
        "requires_document_number": False,
        "requires_expiry": True,
    },
]


def resolve_technician_requirements(*, vertical: str) -> list[dict]:
    """Ordered technician document requirement manifest. Pure function, same
    contract as resolve_requirements -- vertical-specific extras can be
    layered in the same way if a real requirement emerges."""
    return [dict(r) for r in _TECHNICIAN_BASE_REQUIREMENTS]


def required_technician_keys(*, vertical: str) -> set[str]:
    # Deliberately empty: technician identity/background checks are the
    # provider's responsibility and cannot block marketplace readiness.
    return set()


def resolve_requirements(*, vertical: str, business_type: str | None, country: str | None = "India") -> list[dict]:
    """Returns the ordered requirement manifest for this tenant. Pure
    function of (vertical, business_type, country) -- no DB access, so it's
    cheap to call from both the documents endpoint and the setup-overview
    completion check without an extra round trip."""
    reqs = [dict(r) for r in _BASE_REQUIREMENTS]
    reqs.append(dict(_GST_REQUIREMENT))
    for extra in _VERTICAL_EXTRA_REQUIREMENTS.get(vertical, []):
        reqs.append(dict(extra))
    return reqs


def required_keys(*, vertical: str, business_type: str | None, country: str | None = "India") -> set[str]:
    return {r["key"] for r in resolve_requirements(vertical=vertical, business_type=business_type, country=country) if r["required"]}


def is_business_profile_complete(tenant_row) -> bool:
    """Shared with home_services_setup_service's overview -- same fields,
    one definition, so "profile complete" can't silently mean two different
    things between the overview card and the Documents-step gate."""
    return bool(tenant_row) and all([
        tenant_row.business_name, tenant_row.business_type, tenant_row.phone,
        tenant_row.email, tenant_row.address_line1, tenant_row.district,
        tenant_row.city, tenant_row.state, tenant_row.zipcode,
    ])
