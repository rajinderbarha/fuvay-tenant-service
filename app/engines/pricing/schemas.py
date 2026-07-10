"""Pricing Engine — Pydantic v2 Schemas."""
import uuid
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field


# ── City Tier ──────────────────────────────────────────────────────────────
class CityTierCreateRequest(BaseModel):
    city_name: str = Field(min_length=2, max_length=100)
    tier: Literal["tier_1","tier_2","tier_3"]
    service_category: str = Field(min_length=2, max_length=100)
    service_name: str = Field(default="", max_length=200,
        description="Leave empty for a category-wide fallback; set to service name for service-level rule.")
    floor_price: Decimal = Field(gt=0, description="Category minimum price (fallback). Provider cannot go below this.")
    min_price: Decimal | None = Field(None, ge=0, description="Service-level minimum shown to customer.")
    max_price: Decimal | None = Field(None, ge=0, description="Service-level maximum shown to customer.")
    default_estimate: Decimal | None = Field(None, ge=0, description="Default estimate shown in range pricing.")
    visit_fee: Decimal | None = Field(None, ge=0)
    bargain_floor: Decimal | None = Field(None, ge=0, description="Minimum price after customer negotiation.")
    provider_override_allowed: bool = Field(True, description="Whether provider can set prices above the min.")
    notes: str | None = None

class CityTierUpdateRequest(BaseModel):
    floor_price: Decimal | None = Field(None, gt=0)
    min_price: Decimal | None = Field(None, ge=0)
    max_price: Decimal | None = Field(None, ge=0)
    default_estimate: Decimal | None = Field(None, ge=0)
    visit_fee: Decimal | None = Field(None, ge=0)
    bargain_floor: Decimal | None = Field(None, ge=0)
    provider_override_allowed: bool | None = None
    is_active: bool | None = None
    notes: str | None = None

# ── Service Type Price ─────────────────────────────────────────────────────
class ServicePriceSetRequest(BaseModel):
    service_type_id: str = Field(min_length=1, max_length=100)
    service_category: str = Field(min_length=1, max_length=100)
    city_name: str = Field(min_length=2, max_length=100)
    base_price: Decimal = Field(gt=0)
    unit: str = "per_visit"
    change_reason: str | None = Field(None, max_length=500)

# ── Brand Adjustment ───────────────────────────────────────────────────────
class BrandAdjustmentRequest(BaseModel):
    adjustment_pct: Decimal = Field(ge=-50, le=50)
    label: str | None = Field(None, max_length=100)
    reason: str | None = Field(None, max_length=500)

# ── Zone Surcharge ─────────────────────────────────────────────────────────
class ZoneCreateRequest(BaseModel):
    zone_name: str = Field(min_length=2, max_length=100)
    zone_type: Literal["pincode","area_name","polygon"] = "pincode"
    zone_identifiers: list[str] = Field(min_length=1)
    surcharge_pct: Decimal = Field(gt=0, le=40)
    notes: str | None = None

class ZoneUpdateRequest(BaseModel):
    zone_name: str | None = None
    zone_identifiers: list[str] | None = None
    surcharge_pct: Decimal | None = Field(None, gt=0, le=40)
    is_active: bool | None = None
    notes: str | None = None

# ── Dynamic Rules ──────────────────────────────────────────────────────────
class DynamicRuleCreateRequest(BaseModel):
    rule_name: str = Field(min_length=2, max_length=100)
    rule_type: Literal["time_of_day","day_of_week","date_range","demand_surge","flat_override"]
    adjustment_pct: Decimal = Field(ge=-30, le=100)
    conditions: dict = Field(default_factory=dict)
    applies_to: list[str] = Field(default_factory=list)
    priority: int = Field(default=10, ge=1, le=100)
    active_from: str | None = None
    active_until: str | None = None

class DynamicRuleUpdateRequest(BaseModel):
    rule_name: str | None = None
    adjustment_pct: Decimal | None = Field(None, ge=-30, le=100)
    conditions: dict | None = None
    applies_to: list[str] | None = None
    priority: int | None = Field(None, ge=1, le=100)
    active_from: str | None = None
    active_until: str | None = None

# ── Price Compute ──────────────────────────────────────────────────────────
class PriceComputeRequest(BaseModel):
    tenant_id: uuid.UUID
    service_type_id: str
    service_category: str
    city_name: str
    pincode: str | None = None
    booking_id: str | None = None
    requested_at: str | None = None

class PricePreviewRequest(BaseModel):
    service_type_id: str
    service_category: str
    city_name: str
    pincode: str | None = None
