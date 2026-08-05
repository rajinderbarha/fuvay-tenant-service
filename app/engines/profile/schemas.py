"""Profile Engine — Pydantic schemas for Phase 0C."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator
import re as _re

_PHONE_RE = _re.compile(r"^\+?[1-9]\d{7,14}$")

ALLOWED_LANGUAGES = {"en", "hi", "ta", "te", "kn", "ml", "mr", "bn", "gu", "pa", "ur"}

ALLOWED_TIMEZONES = {
    "UTC", "Asia/Kolkata", "Asia/Dubai", "Asia/Singapore", "Asia/Bangkok",
    "Asia/Tokyo", "Asia/Shanghai", "Europe/London", "Europe/Paris",
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "Australia/Sydney", "Pacific/Auckland",
}


class UpdateUserProfileRequest(BaseModel):
    """Fields a user can update on their own profile."""
    full_name: str | None = Field(None, min_length=2, max_length=255)
    display_name: str | None = Field(None, min_length=1, max_length=255)
    language: str | None = None
    timezone: str | None = None
    phone: str | None = None

    @field_validator("language")
    @classmethod
    def _check_language(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_LANGUAGES:
            raise ValueError(f"Language '{v}' is not supported. Allowed: {sorted(ALLOWED_LANGUAGES)}")
        return v

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_TIMEZONES:
            raise ValueError(f"Timezone '{v}' is not supported.")
        return v

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str | None) -> str | None:
        if v is not None and not _PHONE_RE.match(v):
            raise ValueError("Invalid phone number format.")
        return v


CRITICAL_BUSINESS_FIELDS = frozenset({
    "business_name", "owner_name", "business_phone", "business_email",
    "address_line1", "state", "district", "city", "pincode",
    "gst_number",
})


class UpdateBusinessProfileRequest(BaseModel):
    """Fields a provider/tenant can update on their business profile."""
    business_name: str | None = Field(None, min_length=2, max_length=255)
    # Real bug fixed here: the onboarding Business Profile form has always
    # collected legal_name / business_type / registration_number /
    # year_established and sent them on PUT, but this schema never declared
    # them -- so Pydantic silently DROPPED all four and the tenant's answers
    # were lost on every save. The first three map to real Tenant columns;
    # registration_number has no column, so it is stored in tenant.meta
    # alongside website_url/description, which is the established pattern
    # here and avoids a migration for a single optional string.
    legal_name: str | None = Field(None, max_length=255)
    business_type: str | None = Field(None, max_length=50)
    registration_number: str | None = Field(None, max_length=100)
    year_established: int | None = Field(None, ge=1800, le=2200)
    owner_name: str | None = Field(None, min_length=2, max_length=255)
    business_phone: str | None = Field(None, alias="phone")
    business_email: str | None = Field(None, alias="email")
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    district: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=50)
    pincode: str | None = Field(None, max_length=20, alias="zipcode")
    gst_number: str | None = Field(None, max_length=20)
    website_url: str | None = Field(None, max_length=500)
    description: str | None = None

    model_config = {"populate_by_name": True}

    def changed_critical_fields(self, current: dict) -> list[str]:
        changed = []
        mapping = {
            "business_name": self.business_name,
            "owner_name": self.owner_name,
            "business_phone": self.business_phone,
            "business_email": self.business_email,
            "address_line1": self.address_line1,
            "state": self.state,
            "district": self.district,
            "city": self.city,
            "pincode": self.pincode,
            "gst_number": self.gst_number,
        }
        for field, new_val in mapping.items():
            if new_val is not None and str(new_val) != str(current.get(field) or ""):
                changed.append(field)
        return changed
