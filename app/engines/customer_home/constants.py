"""Customer Home section constants.

Home Layout admin control was retired on 2026-08-20. These keys remain as the
app/backend vocabulary for the shipped Home screen only; promotional banner
slots and Global Services are no longer part of the contract.
"""
from __future__ import annotations

HOME_SECTION_KEYS = (
    "active_booking",
    "quick_problems",
    "service_grid",
    "assistant_entry",
    "problem_circles",
    "repair_intent",
    "consult_intent",
    "how_it_works",
    "trust_benefits",
)

ERR_UNKNOWN_SECTION = "HOME_SECTION_UNKNOWN"
