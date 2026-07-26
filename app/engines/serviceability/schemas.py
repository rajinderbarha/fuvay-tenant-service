"""Serviceability Engine — Pydantic Schemas."""
from __future__ import annotations
from pydantic import BaseModel, Field


# ── Customer Addresses ──────────────────────────────────────────────────────────

class AddressCreate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address_line_1: str = Field(..., min_length=2, max_length=300)
    address_line_2: str | None = None
    landmark: str | None = None
    city: str = Field(..., min_length=1, max_length=100)
    district: str | None = None
    state: str = Field(..., min_length=1, max_length=100)
    country: str = "India"
    zipcode: str = Field(..., min_length=1, max_length=20)
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    landmark: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool | None = None


# ── Tenant Service Areas ────────────────────────────────────────────────────────

class ServiceAreaCreate(BaseModel):
    coverage_type: str = Field(..., description="city | zipcode | zone | radius")
    country: str = "India"
    state: str = Field(..., min_length=1, max_length=100)
    district: str | None = None
    city: str = Field(..., min_length=1, max_length=100)
    zipcode: str | None = None
    zone_id: str | None = None
    zone_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float | None = None
    priority: int = 100
    is_active: bool = True
    is_primary: bool = False


class ServiceAreaUpdate(BaseModel):
    coverage_type: str | None = None
    state: str | None = None
    district: str | None = None
    city: str | None = None
    zipcode: str | None = None
    zone_id: str | None = None
    zone_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float | None = None
    priority: int | None = None
    is_active: bool | None = None
    is_primary: bool | None = None


class ServiceAreaValidateRequest(BaseModel):
    coverage_type: str = Field(default="zipcode", description="city | zipcode | zone | radius")
    state: str | None = None
    district: str | None = None
    city: str | None = None
    zipcode: str | None = None
    zone_id: str | None = None
    zone_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float | None = None


class ServiceMappingCreate(BaseModel):
    service_id: str
    job_type: str = Field(..., description="repair | service | consultation")
    is_available: bool = True
    sla_minutes: int | None = None
    base_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None


class ServiceMappingUpdate(BaseModel):
    job_type: str | None = None
    is_available: bool | None = None
    sla_minutes: int | None = None
    base_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None


# ── Serviceability ───────────────────────────────────────────────────────────────

class ServiceabilityCheckRequest(BaseModel):
    address_id: str | None = None
    city: str | None = None
    state: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    service_id: str | None = None
    job_type: str | None = None


class MatchingTenantsRequest(BaseModel):
    address_id: str | None = None
    city: str | None = None
    state: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    service_id: str | None = None
    job_type: str | None = None


class AvailableServicesRequest(BaseModel):
    address_id: str | None = None
    city: str | None = None
    state: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class AdminServiceabilityTestRequest(BaseModel):
    city: str
    state: str | None = None
    zipcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    service_id: str
    job_type: str


class ServiceAreaRequestCreate(BaseModel):
    category_id: str


class ServiceAreaRequestItemCreate(BaseModel):
    tenant_service_id: str
    job_type_id: str | None = None
    applies_to_all_job_types: bool = False
    country: str = "India"
    state: str = Field(..., min_length=1, max_length=100)
    district: str | None = None
    city: str = Field(..., min_length=1, max_length=100)
    zipcode: str | None = None
    requested_effective_date: str | None = None


class ServiceAreaItemDecision(BaseModel):
    item_id: str
    decision: str = Field(..., description="APPROVED | REJECTED | CHANGES_REQUESTED")
    reason: str | None = None


class ServiceAreaRequestDecide(BaseModel):
    decisions: list[ServiceAreaItemDecision]


class CoverageSuspendRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class CoverageRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class BookingPreflightRequest(BaseModel):
    customer_id: str
    address_id: str
    service_id: str
    job_type: str
    scheduled_at: str | None = None
    tenant_id: str | None = None
