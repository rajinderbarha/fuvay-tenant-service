"""Pydantic schemas for the bargain evaluation preview endpoint — ensures the
OpenAPI/Swagger schema documents bargain_floor, allowed_offer_min, and every
other field in the Customer Range + Platform Fee response shape, rather than
leaving the response as an untyped dict (see BARGAIN_MODULE ticket hard gate 6)."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class BargainEvaluationRequest(BaseModel):
    master_service_id: str | None = Field(None, description="Master service to evaluate against (or pricing_rule_id).")
    pricing_rule_id: str | None = Field(None, description="Specific pricing rule to evaluate against (or master_service_id).")
    offer_price: Decimal = Field(..., ge=0, description="The customer's counter-offer.")


class BargainEvaluationResponse(BaseModel):
    service_name: str | None = None
    currency: str = "INR"

    admin_min_price: float | None = Field(None, description="Admin platform range minimum.")
    admin_max_price: float | None = Field(None, description="Admin platform range maximum.")
    admin_base_price: float | None = Field(None, description="Fallback base price — never used as the bargain floor.")

    customer_min_price: float | None = Field(None, description="Customer-facing display/negotiation range minimum.")
    customer_max_price: float | None = Field(None, description="Customer-facing display/negotiation range maximum.")

    platform_fee_percent: float | None = None
    platform_fee_amount: float | None = None

    bargain_floor: float | None = Field(None, description="customer_min_price * (1 + platform_fee_percent/100) + platform_fee_fixed_amount")
    allowed_offer_min: float | None = Field(None, description="Equal to bargain_floor — the true customer-facing minimum offer.")
    allowed_offer_max: float | None = Field(None, description="Equal to customer_max_price.")

    customer_offer: float | None = None
    decision: Literal["accepted", "rejected", "provider_approval_required"] | None = None
    reason: str | None = None
    payment_mode: str = "customer_pays_provider_directly"

    # Legacy/back-compat fields retained for the existing admin bargain-rules UI.
    accepted: bool | None = None
    eligible: bool | None = None
    minimum_allowed_offer: float | None = None
    provider_approval_required: bool | None = None
    pricing_source: str | None = None
    rule_used: str | None = None
    base_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None

    class Config:
        extra = "allow"
