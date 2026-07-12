"""FINAL-L5-05J — Usage Credit domain constants.

DEFAULT_LOW_USAGE_CREDIT_THRESHOLD mirrors the pre-existing
PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD constant already defined in
app.engines.package_commerce.service, so the repaired tenant-health
signal reuses the real platform default rather than inventing a new
number.
"""
from decimal import Decimal

# Matches app.engines.package_commerce.service.PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD
# (kept as a literal, not a cross-engine import, to avoid coupling the
# canonical Usage Credit domain's import graph to package_commerce's).
DEFAULT_LOW_USAGE_CREDIT_THRESHOLD = Decimal("500.00")
