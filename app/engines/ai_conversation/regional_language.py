"""BOOKING-ASSISTANT FOUNDATION (2026-08-01) — chatbot-only regional
language resolution.

Confirmed via audit: `app.engines.profile.schemas.ALLOWED_LANGUAGES` is a
flat, ZIP-independent set of 11 codes with no display names and no
location mapping anywhere in the codebase. There is no existing
ZIP/PIN-to-language infrastructure to reuse. This module is the smallest
backend-authoritative addition that lets the customer app offer a
genuinely backend-derived "regional" language option (e.g. Punjabi for a
Punjab PIN code) instead of guessing it client-side — per direction, ZIP
to language mapping must never be hardcoded in the mobile app.

India PIN codes: the first two digits denote a fixed postal circle
(unlike the rest of the code, this prefix is stable and public
information — https://www.indiapost.gov.in). This table only maps
prefixes to a language ALREADY present in ALLOWED_LANGUAGES; it will
never suggest an unsupported code.
"""
from __future__ import annotations

from app.engines.profile.schemas import ALLOWED_LANGUAGES

# Postal-circle prefix -> (language code, customer-safe English label).
# Deliberately small and additive -- extend as real launch geographies are
# confirmed, never guess a mapping for an unconfirmed region.
# CUSTOMER-ASSISTANT-UX-04 Part 1: labels are the language's OWN native
# endonym -- a customer who reads only Punjabi cannot be expected to
# recognise the English word "Punjabi". The word "(Regional)" was also
# removed entirely: it is internal sourcing vocabulary (how the backend
# derived the option), never something a customer should see next to
# their own language.
_PIN_PREFIX_REGIONAL_LANGUAGE: dict[str, tuple[str, str]] = {
    "14": ("pa", "ਪੰਜਾਬੀ"),  # Punjab / Chandigarh / parts of Haryana
    "16": ("pa", "ਪੰਜਾਬੀ"),  # Punjab
}

_LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "hi": "हिन्दी",
    "pa": "ਪੰਜਾਬੀ",
}


def resolve_regional_language(zipcode: str | None) -> dict | None:
    """Returns `{"code": ..., "label": ...}` for the ZIP's regional
    language, or None when no mapping is configured for that PIN prefix
    -- callers must not fabricate a fallback when this returns None (spec:
    "If no regional language is configured, show only the languages
    returned by the backend")."""
    if not zipcode or len(zipcode) < 2:
        return None
    prefix = zipcode[:2]
    entry = _PIN_PREFIX_REGIONAL_LANGUAGE.get(prefix)
    if not entry:
        return None
    code, label = entry
    if code not in ALLOWED_LANGUAGES:
        return None
    return {"code": code, "label": label}


def build_language_options(zipcode: str | None) -> list[dict]:
    """English and Hindi are always offered (core product languages);
    the third option is backend/location-derived and only present when
    genuinely configured for this ZIP."""
    options = [
        {"code": "en", "label": _LANGUAGE_LABELS["en"]},
        {"code": "hi", "label": _LANGUAGE_LABELS["hi"]},
    ]
    regional = resolve_regional_language(zipcode)
    if regional and regional["code"] not in {"en", "hi"}:
        options.append(regional)
    return options
