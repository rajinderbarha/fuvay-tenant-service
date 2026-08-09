"""Home layout constants.

`HOME_SECTION_KEYS` is the contract between admin and the app: exactly the
sections the app has a renderer for. Admin can reorder, rename or hide any of
them; it cannot invent a key, because a key with no renderer is a row that does
nothing and would read to admin as a broken feature.

Kept here rather than in the migration so the validation and the seed cannot
drift apart -- the migration's list must stay a subset of this one.
"""
from __future__ import annotations

HOME_SECTION_KEYS = (
    "active_booking",
    "quick_problems",
    # Five banner slots (migration 237). Each is a section in its own right, so
    # admin can re-order, rename or switch off any one of them, and each renders
    # as a swipeable carousel once it holds more than one banner.
    "campaign_top",
    "campaign_after_problems",
    "service_grid",
    "campaign_after_services",
    "assistant_entry",
    "campaign_mid",
    "global_services",
    "how_it_works",
    "trust_benefits",
    "campaign_bottom",
)

ERR_UNKNOWN_SECTION = "HOME_SECTION_UNKNOWN"
