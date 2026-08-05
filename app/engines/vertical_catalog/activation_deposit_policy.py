"""Home Services mandatory security deposit + starter credit policy.

Real business rule (not a placeholder): every Home Services tenant must
provide a security deposit scaled to technician headcount, and purchase a
mandatory starter credit top-up, before activation -- neither is optional
or skippable regardless of what a tenant's `tenant_billing` row happens to
already contain.

These amounts are currently fixed constants rather than an admin-editable
setting (no admin UI for this policy exists yet) -- a real, deliberate
scope cut, not an oversight. Move to a real settings table if/when Admin
needs to change these without a code deploy.
"""
from __future__ import annotations

from decimal import Decimal

# ₹2,000 security deposit per active technician (minimum 1 technician's
# worth even before any technician is added, since a workspace with zero
# technicians still cannot be considered activation-ready on this gate --
# see STAFF_TECHNICIANS gate for that separate requirement).
SECURITY_DEPOSIT_PER_TECHNICIAN = Decimal("2000")

# Mandatory starter credit package: ₹1,000 base + 18% GST = ₹1,180 total.
CREDIT_PACKAGE_BASE_AMOUNT = Decimal("1000")
CREDIT_PACKAGE_GST_PERCENT = Decimal("18")
CREDIT_PACKAGE_TOTAL_AMOUNT = (
    CREDIT_PACKAGE_BASE_AMOUNT * (Decimal("1") + CREDIT_PACKAGE_GST_PERCENT / Decimal("100"))
).quantize(Decimal("0.01"))


def required_security_deposit(active_technician_count: int) -> Decimal:
    technicians = max(1, active_technician_count)
    return SECURITY_DEPOSIT_PER_TECHNICIAN * technicians
