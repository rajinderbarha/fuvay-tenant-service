"""Admin Catalog Engine — Models.
12 tables that form the platform-wide source of truth for:
  service categories → master services → types/brands → pricing tiers → pricing rules
  → tenant service enablement → tenant type/brand selection.
Sprint 14: ServiceCategory extended with customer-flow fields; MasterOffering +
CustomerFlowConfig added.
"""
import uuid
from decimal import Decimal
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy import (
    Boolean, Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


# ── Pricing Tiers ─────────────────────────────────────────────────────────────
class PricingTier(ServiceOSBase):
    """Platform-defined pricing tier (Metro / Large City / Small City / Rural …)."""
    __tablename__ = "pricing_tiers"
    __table_args__ = (
        UniqueConstraint("code", name="uq_pt_code"),
        Index("ix_pt_active", "is_active"),
    )

    name:                       Mapped[str]           = mapped_column(String(120), nullable=False)
    code:                       Mapped[str]           = mapped_column(String(60), nullable=False)
    tier_type:                  Mapped[str]           = mapped_column(String(30), nullable=False)
    description:                Mapped[str | None]    = mapped_column(Text, nullable=True)
    base_multiplier:            Mapped[Decimal]       = mapped_column(Numeric(6, 3), default=Decimal("1"), nullable=False)
    platform_fee_percent:       Mapped[Decimal]       = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    default_commission_percent: Mapped[Decimal]       = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    default_sla_minutes:        Mapped[int]           = mapped_column(Integer, default=60, nullable=False)
    is_active:                  Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    deleted_at:                 Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Tier Locations ────────────────────────────────────────────────────────────
class TierLocation(ServiceOSBase):
    """Maps a city / zipcode / state to a PricingTier. Zipcode overrides city."""
    __tablename__ = "tier_locations"
    __table_args__ = (
        Index("ix_tl_tier",     "tier_id"),
        Index("ix_tl_zipcode",  "zipcode"),
        Index("ix_tl_city",     "city"),
        Index("ix_tl_active",   "is_active"),
    )

    tier_id:    Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    country:    Mapped[str]        = mapped_column(String(60), default="India", nullable=False)
    state:      Mapped[str | None] = mapped_column(String(100), nullable=True)
    district:   Mapped[str | None] = mapped_column(String(100), nullable=True)
    city:       Mapped[str | None] = mapped_column(String(100), nullable=True)
    zipcode:    Mapped[str | None] = mapped_column(String(20), nullable=True)
    zone_name:  Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority:   Mapped[int]        = mapped_column(Integer, default=100, nullable=False)
    is_active:  Mapped[bool]       = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Service Categories ────────────────────────────────────────────────────────
class ServiceCategory(ServiceOSBase):
    """Top-level grouping: Home Services, Coaching Center, Real Estate, etc."""
    __tablename__ = "service_categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_sc_slug"),
        Index("ix_sc_active",           "is_active"),
        Index("ix_sc_customer_visible", "is_customer_visible"),
    )

    name:                   Mapped[str]           = mapped_column(String(200), nullable=False)
    slug:                   Mapped[str]           = mapped_column(String(200), nullable=False)
    description:            Mapped[str | None]    = mapped_column(Text, nullable=True)
    icon_url:               Mapped[str | None]    = mapped_column(String(500), nullable=True)
    image_url:              Mapped[str | None]    = mapped_column(String(500), nullable=True)
    banner_url:             Mapped[str | None]    = mapped_column(String(500), nullable=True)
    display_order:          Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    is_active:              Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    # Category runtime / multi-vertical fields (added in Sprint 3 / Category Runtime sprint)
    category_type:          Mapped[str | None]    = mapped_column(String(50), nullable=True)
    primary_engine_id:      Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    primary_engine_key:     Mapped[str | None]    = mapped_column(String(100), nullable=True)
    customer_flow_type:     Mapped[str | None]    = mapped_column(String(50), nullable=True)
    frontend_component_key: Mapped[str | None]    = mapped_column(String(100), nullable=True)
    provider_dashboard_type:Mapped[str | None]    = mapped_column(String(100), nullable=True)
    is_provider_registerable:Mapped[bool]         = mapped_column(Boolean, default=True, nullable=False)
    is_customer_visible:    Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    monetization_model:     Mapped[str | None]    = mapped_column(String(50), nullable=True)
    # MODULE-L5-10 (migration 139) — per-category commission rate. NULL = use the
    # platform default (DEFAULT_COMMISSION_RATE). Set per category by the admin.
    commission_pct:         Mapped[Decimal | None]= mapped_column(Numeric(5, 2), nullable=True)
    # Sprint 38 — universal category fields
    vertical_type:          Mapped[str | None]    = mapped_column(String(50), nullable=True)
    finance_model:          Mapped[str | None]    = mapped_column(String(50), nullable=True)
    provider_business_model:Mapped[str | None]    = mapped_column(String(50), nullable=True)
    requires_location:      Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    requires_schedule:      Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    requires_brand:         Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    requires_service_option:Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    requires_issue_type:    Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    tenant_selectable:      Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    pricing_supported:      Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)


# ── Service Groups ────────────────────────────────────────────────────────────
class ServiceGroup(ServiceOSBase):
    """Intermediate grouping layer between ServiceCategory and MasterService.

    Example: ServiceCategory='Home Services' → ServiceGroup='AC Services'
             → MasterService='AC Repair', 'AC Installation', ...
    """
    __tablename__ = "service_groups"
    __table_args__ = (
        UniqueConstraint("code", name="uq_sg_code"),
        UniqueConstraint("slug", name="uq_sg_slug"),
        Index("ix_sg_category",   "category_id"),
        Index("ix_sg_status",     "status"),
        Index("ix_sg_deleted_at", "deleted_at"),
    )

    category_id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    code:                Mapped[str]            = mapped_column(String(100), nullable=False)
    name:                Mapped[str]            = mapped_column(String(200), nullable=False)
    slug:                Mapped[str]            = mapped_column(String(200), nullable=False)
    description:         Mapped[str | None]    = mapped_column(Text, nullable=True)
    status:              Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    display_order:       Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    icon_url:            Mapped[str | None]    = mapped_column(String(500), nullable=True)
    metadata_json:       Mapped[dict | None]   = mapped_column(JSONB, nullable=True)
    created_by_user_id:  Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:  Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at:          Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                  str(self.id),
            "category_id":         str(self.category_id),
            "code":                self.code,
            "name":                self.name,
            "slug":                self.slug,
            "description":         self.description,
            "status":              self.status,
            "display_order":       self.display_order,
            "icon_url":            self.icon_url,
            "created_by_user_id":  str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
            "updated_at":          self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Master Services ───────────────────────────────────────────────────────────
class MasterService(ServiceOSBase):
    """Platform-defined service: AC Repair (repair), AC Annual Service (service), etc."""
    __tablename__ = "master_services"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_ms_slug"),
        Index("ix_ms_category",    "category_id"),
        Index("ix_ms_job_type",    "job_type"),
        Index("ix_ms_active",      "is_active"),
    )

    category_id:               Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    service_group_id:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_name:              Mapped[str]            = mapped_column(String(200), nullable=False)
    slug:                      Mapped[str]            = mapped_column(String(200), nullable=False)
    description:               Mapped[str | None]    = mapped_column(Text, nullable=True)
    image_url:                 Mapped[str | None]    = mapped_column(String(500), nullable=True)
    icon_url:                  Mapped[str | None]    = mapped_column(String(500), nullable=True)
    job_type:                  Mapped[str]            = mapped_column(String(20), nullable=False)
    pricing_model:             Mapped[str]            = mapped_column(String(30), nullable=False)
    base_price:                Mapped[Decimal]        = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    min_price:                 Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_price:                 Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    visit_fee:                 Mapped[Decimal]        = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    pre_approval_limit:        Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_duration_minutes:Mapped[int | None]    = mapped_column(Integer, nullable=True)
    requires_checklist:        Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_brand_required:         Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_type_required:          Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_issue_type:       Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_schedule:         Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_address:          Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    tenant_override_allowed:   Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    tenant_custom_name_allowed:Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    # Hourly-model fields
    hourly_rate:               Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    minimum_billable_hours:    Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_hours:           Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    maximum_hours:             Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Range-model field
    default_estimate:          Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Post-assessment fields
    assessment_label:          Mapped[str | None]    = mapped_column(String(200), nullable=True)
    show_estimated_range:      Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    customer_note:             Mapped[str | None]    = mapped_column(Text, nullable=True)
    is_active:                 Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    display_order:             Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    deleted_at:                Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)


# ── Service Types ─────────────────────────────────────────────────────────────
class ServiceType(ServiceOSBase):
    """Equipment sub-types: Split AC, Window AC, Cassette AC, etc."""
    __tablename__ = "service_types"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_st_slug"),
        Index("ix_st_category", "category_id"),
        Index("ix_st_active",   "is_active"),
    )

    category_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name:             Mapped[str]              = mapped_column(String(200), nullable=False)
    slug:             Mapped[str]              = mapped_column(String(200), nullable=False)
    description:      Mapped[str | None]      = mapped_column(Text, nullable=True)
    icon_url:         Mapped[str | None]      = mapped_column(String(500), nullable=True)
    is_active:        Mapped[bool]            = mapped_column(Boolean, default=True, nullable=False)
    deleted_at:       Mapped[datetime|None]   = mapped_column(DateTime(timezone=True), nullable=True)
    # Enterprise fields (migration 076)
    code:             Mapped[str | None]      = mapped_column(String(100), nullable=True)
    type_family:      Mapped[str | None]      = mapped_column(String(50), nullable=True)
    customer_visible: Mapped[bool]            = mapped_column(Boolean, default=True, nullable=False)
    status:           Mapped[str]             = mapped_column(String(20), default="active", nullable=False)
    display_order:    Mapped[int]             = mapped_column(Integer, default=0, nullable=False)


# ── Service Type Mappings (076) ────────────────────────────────────────────────
class ServiceTypeMapping(ServiceOSBase):
    """Maps a ServiceType (master) to a category / group / service."""
    __tablename__ = "service_type_mappings"
    __table_args__ = (
        sa.UniqueConstraint("type_id", "category_id", "service_group_id", "service_id",
                            name="uq_stm_type_cat_grp_svc"),
        Index("ix_stm_type_id",     "type_id"),
        Index("ix_stm_category_id", "category_id"),
        Index("ix_stm_service_id",  "service_id"),
    )

    type_id:          Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_visible: Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    provider_visible: Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    status:           Mapped[str]              = mapped_column(String(20), default="active", nullable=False)
    display_order:    Mapped[int]              = mapped_column(Integer, default=0, nullable=False)


# ── Brand Mappings (076) ───────────────────────────────────────────────────────
class BrandMapping(ServiceOSBase):
    """Maps a Brand (master) to a category / group / service."""
    __tablename__ = "brand_mappings"
    __table_args__ = (
        sa.UniqueConstraint("brand_id", "category_id", "service_group_id", "service_id",
                            name="uq_bm_brand_cat_grp_svc"),
        Index("ix_bm_brand_id",    "brand_id"),
        Index("ix_bm_category_id", "category_id"),
        Index("ix_bm_service_id",  "service_id"),
    )

    brand_id:         Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_visible: Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    provider_visible: Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    status:           Mapped[str]              = mapped_column(String(20), default="active", nullable=False)
    display_order:    Mapped[int]              = mapped_column(Integer, default=0, nullable=False)


# ── Brands ────────────────────────────────────────────────────────────────────
class Brand(ServiceOSBase):
    """Equipment brands: LG, Samsung, Daikin, Voltas, etc. (Sprint 34D: extended)."""
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("slug",            name="uq_b_slug"),
        Index("ix_b_category",              "category_id"),
        Index("ix_b_active",                "is_active"),
        Index("ix_brands_status",           "status"),
        Index("ix_brands_norm_name",        "normalized_name"),
        Index("ix_brands_is_global",        "is_global"),
    )

    category_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name:                   Mapped[str]              = mapped_column(String(200), nullable=False)
    slug:                   Mapped[str]              = mapped_column(String(200), nullable=False)
    # Sprint 34D additions
    code:                   Mapped[str | None]       = mapped_column(String(80), nullable=True)
    display_name:           Mapped[str | None]       = mapped_column(String(200), nullable=True)
    status:                 Mapped[str]              = mapped_column(String(30), default="active", nullable=False)
    normalized_name:        Mapped[str | None]       = mapped_column(String(200), nullable=True)
    alias_names_json:       Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    replacement_brand_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    website_url:            Mapped[str | None]       = mapped_column(String(500), nullable=True)
    country_of_origin:      Mapped[str | None]       = mapped_column(String(100), nullable=True)
    is_global:              Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    display_order:          Mapped[int]              = mapped_column(Integer, default=0, nullable=False)
    metadata_json:          Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    created_by_user_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Pre-34D fields kept
    logo_url:               Mapped[str | None]       = mapped_column(String(500), nullable=True)
    description:            Mapped[str | None]       = mapped_column(Text, nullable=True)
    is_active:              Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    deleted_at:             Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "category_id":          str(self.category_id) if self.category_id else None,
            "name":                 self.name,
            "slug":                 self.slug,
            "code":                 self.code,
            "display_name":         self.display_name,
            "status":               self.status,
            "normalized_name":      self.normalized_name,
            "alias_names":          self.alias_names_json or [],
            "replacement_brand_id": str(self.replacement_brand_id) if self.replacement_brand_id else None,
            "website_url":          self.website_url,
            "country_of_origin":    self.country_of_origin,
            "is_global":            self.is_global,
            "display_order":        self.display_order,
            "logo_url":             self.logo_url,
            "description":          self.description,
            "is_active":            self.is_active,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Brand ↔ Category Mapping (M2M) ───────────────────────────────────────────
class BrandCategoryMapping(ServiceOSBase):
    """Many-to-many: one brand can belong to many categories (Sprint 34D)."""
    __tablename__ = "brand_category_mappings"
    __table_args__ = (
        UniqueConstraint("brand_id", "category_id", name="uq_bcm_brand_category"),
        Index("ix_bcm_brand",    "brand_id"),
        Index("ix_bcm_category", "category_id"),
        Index("ix_bcm_status",   "status"),
    )

    brand_id:            Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    status:              Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    display_order:       Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    created_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at:          Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                 str(self.id),
            "brand_id":           str(self.brand_id),
            "category_id":        str(self.category_id),
            "status":             self.status,
            "display_order":      self.display_order,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
        }


# ── Brand ↔ Service Option Mapping ───────────────────────────────────────────
class BrandServiceOptionMapping(ServiceOSBase):
    """Optional: brand ↔ service option compatibility (e.g. Brand X supports Split AC only)."""
    __tablename__ = "brand_service_option_mappings"
    __table_args__ = (
        UniqueConstraint("brand_id", "service_option_id", name="uq_bsom_brand_option"),
        Index("ix_bsom_brand",          "brand_id"),
        Index("ix_bsom_service_option", "service_option_id"),
        Index("ix_bsom_status",         "status"),
    )

    brand_id:          Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    master_service_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_option_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    status:            Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    display_order:     Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    metadata_json:     Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    deleted_at:        Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                str(self.id),
            "brand_id":          str(self.brand_id),
            "master_service_id": str(self.master_service_id) if self.master_service_id else None,
            "service_option_id": str(self.service_option_id),
            "status":            self.status,
            "display_order":     self.display_order,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
        }


# ── Tenant Supported Brands (provider brand support with approval) ────────────
class TenantSupportedBrand(ServiceOSBase):
    """Provider's supported brand per service, with optional approval workflow."""
    __tablename__ = "tenant_supported_brands"
    __table_args__ = (
        UniqueConstraint("tenant_id", "master_service_id", "brand_id", name="uq_tsb_tenant_service_brand"),
        Index("ix_tsb_tenant",  "tenant_id"),
        Index("ix_tsb_service", "master_service_id"),
        Index("ix_tsb_brand",   "brand_id"),
        Index("ix_tsb_status",  "status"),
    )

    tenant_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    master_service_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    brand_id:            Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    service_option_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:              Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    support_level:       Mapped[str|None]       = mapped_column(String(30), nullable=True)
    notes:               Mapped[str|None]       = mapped_column(Text, nullable=True)
    created_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at:          Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                  str(self.id),
            "tenant_id":           str(self.tenant_id),
            "master_service_id":   str(self.master_service_id),
            "brand_id":            str(self.brand_id),
            "service_option_id":   str(self.service_option_id) if self.service_option_id else None,
            "status":              self.status,
            "support_level":       self.support_level,
            "notes":               self.notes,
            "created_by_user_id":  str(self.created_by_user_id) if self.created_by_user_id else None,
            "approved_by_user_id": str(self.approved_by_user_id) if self.approved_by_user_id else None,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
            "updated_at":          self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Brand Requests (provider can request missing brands) ──────────────────────
class BrandRequest(ServiceOSBase):
    """Provider-submitted brand-add request; reviewed by admin (Sprint 34D)."""
    __tablename__ = "brand_requests"
    __table_args__ = (
        Index("ix_br_tenant",  "tenant_id"),
        Index("ix_br_status",  "status"),
        Index("ix_br_matched", "matched_brand_id"),
    )

    requested_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:             Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    requested_brand_name:  Mapped[str]            = mapped_column(String(200), nullable=False)
    normalized_name:       Mapped[str|None]       = mapped_column(String(200), nullable=True)
    suggested_category_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    suggested_service_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason:                Mapped[str|None]       = mapped_column(Text, nullable=True)
    status:                Mapped[str]            = mapped_column(String(30), default="pending", nullable=False)
    matched_brand_id:      Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    admin_note:            Mapped[str|None]       = mapped_column(Text, nullable=True)
    reviewed_by_user_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at:           Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                    str(self.id),
            "requested_by_user_id":  str(self.requested_by_user_id) if self.requested_by_user_id else None,
            "tenant_id":             str(self.tenant_id) if self.tenant_id else None,
            "requested_brand_name":  self.requested_brand_name,
            "normalized_name":       self.normalized_name,
            "suggested_category_id": str(self.suggested_category_id) if self.suggested_category_id else None,
            "suggested_service_id":  str(self.suggested_service_id) if self.suggested_service_id else None,
            "reason":                self.reason,
            "status":                self.status,
            "matched_brand_id":      str(self.matched_brand_id) if self.matched_brand_id else None,
            "admin_note":            self.admin_note,
            "reviewed_by_user_id":   str(self.reviewed_by_user_id) if self.reviewed_by_user_id else None,
            "reviewed_at":           self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at":            self.created_at.isoformat() if self.created_at else None,
            "updated_at":            self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Brand Templates ───────────────────────────────────────────────────────────
class BrandTemplate(ServiceOSBase):
    """Reusable brand starter pack (e.g. 'AC Brands' → Voltas, Daikin, LG …)."""
    __tablename__ = "brand_templates"
    __table_args__ = (
        UniqueConstraint("code", name="uq_bt_code"),
        Index("ix_bt_status",   "status"),
        Index("ix_bt_category", "category_id"),
    )

    code:          Mapped[str]            = mapped_column(String(80), nullable=False)
    name:          Mapped[str]            = mapped_column(String(200), nullable=False)
    description:   Mapped[str|None]      = mapped_column(Text, nullable=True)
    category_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    vertical_type: Mapped[str|None]      = mapped_column(String(50), nullable=True)
    status:        Mapped[str]           = mapped_column(String(30), default="active", nullable=False)

    def to_dict(self) -> dict:
        return {
            "id":            str(self.id),
            "code":          self.code,
            "name":          self.name,
            "description":   self.description,
            "category_id":   str(self.category_id) if self.category_id else None,
            "vertical_type": self.vertical_type,
            "status":        self.status,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
            "updated_at":    self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Brand Template Items ──────────────────────────────────────────────────────
class BrandTemplateItem(ServiceOSBase):
    """Individual brand within a BrandTemplate."""
    __tablename__ = "brand_template_items"
    __table_args__ = (
        UniqueConstraint("brand_template_id", "brand_id", name="uq_bti_template_brand"),
        Index("ix_bti_template", "brand_template_id"),
        Index("ix_bti_brand",    "brand_id"),
    )

    brand_template_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    brand_id:          Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    master_service_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    display_order:     Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    status:            Mapped[str]            = mapped_column(String(30), default="active", nullable=False)

    def to_dict(self) -> dict:
        return {
            "id":                str(self.id),
            "brand_template_id": str(self.brand_template_id),
            "brand_id":          str(self.brand_id),
            "master_service_id": str(self.master_service_id) if self.master_service_id else None,
            "display_order":     self.display_order,
            "status":            self.status,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
        }


# ── Master Service ↔ Type Mapping ─────────────────────────────────────────────
class MasterServiceType(ServiceOSBase):
    """Which service types are valid for a given master service."""
    __tablename__ = "master_service_types"
    __table_args__ = (
        UniqueConstraint("master_service_id", "service_type_id", name="uq_mst_service_type"),
        Index("ix_mst_service", "master_service_id"),
    )

    master_service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    service_type_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_required:       Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    is_default:        Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    is_active:         Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)


# ── Master Service ↔ Brand Mapping ────────────────────────────────────────────
class MasterServiceBrand(ServiceOSBase):
    """Which brands are valid for a given master service."""
    __tablename__ = "master_service_brands"
    __table_args__ = (
        UniqueConstraint("master_service_id", "brand_id", name="uq_msb_service_brand"),
        Index("ix_msb_service", "master_service_id"),
    )

    master_service_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    brand_id:            Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    is_required:         Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_default:          Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_active:           Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    # Sprint 34D additions
    status:              Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    display_order:       Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    created_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Admin Home Services Catalog Console additions
    can_override_price:  Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    is_routing_only:     Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id":                str(self.id),
            "master_service_id": str(self.master_service_id),
            "brand_id":          str(self.brand_id),
            "is_required":       self.is_required,
            "is_default":        self.is_default,
            "is_active":         self.is_active,
            "status":            self.status,
            "display_order":     self.display_order,
            "can_override_price": self.can_override_price,
            "is_routing_only":    self.is_routing_only,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
        }


# ── Service Pricing Rules ─────────────────────────────────────────────────────
class ServicePricingRule(ServiceOSBase):
    """Hierarchical pricing rule: most-specific active rule wins at price resolution."""
    __tablename__ = "service_pricing_rules"
    __table_args__ = (
        Index("ix_spr_service",  "master_service_id"),
        Index("ix_spr_tier",     "tier_id"),
        Index("ix_spr_zipcode",  "zipcode"),
        Index("ix_spr_city",     "city"),
        Index("ix_spr_active",   "is_active"),
        # migration 120 — prevents duplicate service+type+brand+tier rules
        UniqueConstraint("master_service_id", "service_type_id", "brand_id", "tier_id",
                          name="uq_spr_service_type_brand_tier"),
    )

    master_service_id:   Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    job_type:            Mapped[str]              = mapped_column(String(20), nullable=False)
    tier_id:             Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_type_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_option_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    city:                Mapped[str | None]       = mapped_column(String(100), nullable=True)
    zipcode:             Mapped[str | None]       = mapped_column(String(20), nullable=True)
    pricing_model:       Mapped[str]              = mapped_column(String(30), nullable=False)
    base_price:          Mapped[Decimal]          = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    min_price:           Mapped[Decimal | None]   = mapped_column(Numeric(12, 2), nullable=True)
    max_price:           Mapped[Decimal | None]   = mapped_column(Numeric(12, 2), nullable=True)
    visit_fee:           Mapped[Decimal]          = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    platform_fee_percent:Mapped[Decimal]          = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    commission_percent:  Mapped[Decimal]          = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    tax_percent:         Mapped[Decimal]          = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    effective_from:      Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to:        Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    priority:            Mapped[int]              = mapped_column(Integer, default=100, nullable=False)
    is_active:           Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    deleted_at:          Mapped[datetime|None]    = mapped_column(DateTime(timezone=True), nullable=True)
    # Enterprise fields (migration 077)
    rule_name:           Mapped[str | None]       = mapped_column(String(200), nullable=True)
    rule_code:           Mapped[str | None]       = mapped_column(String(80), nullable=True)
    bargain_floor:       Mapped[Decimal | None]   = mapped_column(Numeric(12, 2), nullable=True)
    source:              Mapped[str]              = mapped_column(String(30), default="admin", nullable=False)
    district:            Mapped[str | None]       = mapped_column(String(100), nullable=True)
    state:               Mapped[str | None]       = mapped_column(String(100), nullable=True)
    zone:                Mapped[str | None]       = mapped_column(String(100), nullable=True)
    # Phase 3 — usage-credit deduction charged to the provider after job
    # completion (never cash). Configuration only in this phase.
    completed_job_deduction_credits: Mapped[int]  = mapped_column(Integer, default=0, nullable=False)


# ── Bargain Rules (Phase 3) ────────────────────────────────────────────────────
class BargainRule(ServiceOSBase):
    """Negotiation policy governing whether a customer's counter-offer is
    accepted for a given service/pricing rule. Distinct from the bare
    bargain_floor value on ServicePricingRule — this adds real evaluation
    configuration (below-floor action, approval requirement, attempt caps)."""
    __tablename__ = "bargain_rules"
    __table_args__ = (
        Index("ix_bargain_rules_pricing_rule", "pricing_rule_id"),
        Index("ix_bargain_rules_master_service", "master_service_id"),
        Index("ix_bargain_rules_status", "status"),
    )

    vertical_key:                Mapped[str | None]       = mapped_column(String(50), nullable=True)
    category_id:                 Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    master_service_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    pricing_rule_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rule_name:                   Mapped[str | None]       = mapped_column(String(200), nullable=True)
    rule_code:                   Mapped[str | None]       = mapped_column(String(80), nullable=True)
    bargain_enabled:              Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    floor_type:                   Mapped[str]              = mapped_column(String(20), default="fixed", nullable=False)
    floor_amount:                 Mapped[Decimal]          = mapped_column(Numeric(12, 2), nullable=False)
    # Customer Range + Platform Fee Floor Fix — customer-facing display/negotiation
    # range and the fee applied to its minimum to derive the real bargain floor.
    # When customer_min_price is set, evaluate_bargain() uses the corrected
    # formula (bargain_engine.evaluate_customer_bargain) instead of the flat
    # floor_amount above. See bargain_engine.py for the formula and rationale.
    customer_min_price:           Mapped[Decimal | None]   = mapped_column(Numeric(12, 2), nullable=True)
    customer_max_price:           Mapped[Decimal | None]   = mapped_column(Numeric(12, 2), nullable=True)
    platform_fee_percent:         Mapped[Decimal | None]   = mapped_column(Numeric(6, 2), nullable=True)
    platform_fee_fixed_amount:    Mapped[Decimal]          = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    below_floor_action:           Mapped[str]              = mapped_column(String(20), default="reject", nullable=False)
    provider_approval_required:   Mapped[bool]             = mapped_column(Boolean, default=False, nullable=False)
    max_attempts:                 Mapped[int | None]       = mapped_column(Integer, nullable=True)
    status:                       Mapped[str]              = mapped_column(String(20), default="active", nullable=False)
    created_by_user_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at:                   Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)


# ── Provider Pricing Overrides (Phase 3) ───────────────────────────────────────
class ProviderPricingOverride(ServiceOSBase):
    """Tenant-scoped price override — must never violate platform min/max or
    bypass the bargain floor. Requires admin approval before taking effect."""
    __tablename__ = "provider_pricing_overrides"
    __table_args__ = (
        Index("ix_ppo_tenant", "tenant_id"),
        Index("ix_ppo_master_service", "master_service_id"),
        Index("ix_ppo_approval_status", "approval_status"),
    )

    tenant_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    vertical_key:         Mapped[str | None]       = mapped_column(String(50), nullable=True)
    category_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    master_service_id:    Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    service_type_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id:             Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    issue_type_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    zipcode:               Mapped[str | None]       = mapped_column(String(20), nullable=True)
    tier_id:               Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    override_price:        Mapped[Decimal]          = mapped_column(Numeric(12, 2), nullable=False)
    currency:               Mapped[str]              = mapped_column(String(10), default="INR", nullable=False)
    approval_status:        Mapped[str]              = mapped_column(String(20), default="pending", nullable=False)
    status:                 Mapped[str]              = mapped_column(String(20), default="active", nullable=False)
    reason:                 Mapped[str | None]       = mapped_column(Text, nullable=True)
    rejection_reason:       Mapped[str | None]       = mapped_column(Text, nullable=True)
    approved_by_user_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at:            Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at:              Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)


# ── Location Import Batches (migration 077 — CSV import wizard) ──────────────
class LocationImportBatch(ServiceOSBase):
    """Tracks a City/Zipcode -> Tier CSV import: preview -> confirm -> report."""
    __tablename__ = "location_import_batches"
    __table_args__ = (
        Index("ix_lib_status",      "status"),
        Index("ix_lib_uploaded_by", "uploaded_by_user_id"),
    )

    status:               Mapped[str]            = mapped_column(String(20), default="preview", nullable=False)
    file_name:            Mapped[str | None]      = mapped_column(String(255), nullable=True)
    uploaded_by_user_id:  Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    total_rows:           Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    valid_rows:           Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    invalid_rows:         Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    conflict_rows:        Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    created_rows:         Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    updated_rows:         Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    skipped_rows:         Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    preview_payload:      Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    report_payload:       Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    conflict_resolution:  Mapped[str | None]      = mapped_column(String(20), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                  str(self.id),
            "status":              self.status,
            "file_name":           self.file_name,
            "uploaded_by_user_id": str(self.uploaded_by_user_id) if self.uploaded_by_user_id else None,
            "total_rows":          self.total_rows,
            "valid_rows":          self.valid_rows,
            "invalid_rows":        self.invalid_rows,
            "conflict_rows":       self.conflict_rows,
            "created_rows":        self.created_rows,
            "updated_rows":        self.updated_rows,
            "skipped_rows":        self.skipped_rows,
            "preview_payload":     self.preview_payload,
            "report_payload":      self.report_payload,
            "conflict_resolution": self.conflict_resolution,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
            "updated_at":          self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Tenant Services ───────────────────────────────────────────────────────────
class TenantService(ServiceOSBase):
    """A tenant's enablement of an admin master service, with optional price overrides."""
    __tablename__ = "tenant_services"
    __table_args__ = (
        UniqueConstraint("tenant_id", "master_service_id", name="uq_ts_tenant_service"),
        Index("ix_ts_tenant",  "tenant_id"),
        Index("ix_ts_service", "master_service_id"),
        Index("ix_ts_active",  "tenant_id", "is_enabled"),
    )

    tenant_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    master_service_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    job_type:            Mapped[str]            = mapped_column(String(20), nullable=False)
    is_enabled:          Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    tenant_display_name: Mapped[str | None]    = mapped_column(String(200), nullable=True)
    tenant_description:  Mapped[str | None]    = mapped_column(Text, nullable=True)
    tenant_base_price:   Mapped[Decimal|None]  = mapped_column(Numeric(12, 2), nullable=True)
    tenant_min_price:    Mapped[Decimal|None]  = mapped_column(Numeric(12, 2), nullable=True)
    tenant_max_price:    Mapped[Decimal|None]  = mapped_column(Numeric(12, 2), nullable=True)
    tenant_visit_fee:    Mapped[Decimal|None]  = mapped_column(Numeric(12, 2), nullable=True)
    override_allowed:    Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    requires_brand:      Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    requires_type:       Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    is_active:           Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    deleted_at:          Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Tenant Home Services Service Setup Wizard additions
    setup_status:        Mapped[str]           = mapped_column(String(20), default="draft", nullable=False)
    published_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Tenant Service Types ──────────────────────────────────────────────────────
class TenantServiceType(ServiceOSBase):
    """Which types a tenant supports for a given tenant_service."""
    __tablename__ = "tenant_service_types"
    __table_args__ = (
        UniqueConstraint("tenant_service_id", "service_type_id", name="uq_tst_service_type"),
        Index("ix_tst_tenant_service", "tenant_service_id"),
    )

    tenant_id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_service_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    service_type_id:        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    is_enabled:             Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    tenant_price_adjustment:Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tenant_min_price:       Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tenant_max_price:       Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)


# ── Tenant Service Brands ─────────────────────────────────────────────────────
class TenantServiceBrand(ServiceOSBase):
    """Which brands a tenant supports for a given tenant_service, priced per
    service type (migration 120 — Type-Dependent Brand Pricing). NULL
    service_type_id is reserved for fixed (non-type-based) services, where
    brand pricing is legitimately service-scoped only; for type-based
    services, service_type_id is required (enforced in tenant_service.py)."""
    __tablename__ = "tenant_service_brands"
    __table_args__ = (
        UniqueConstraint("tenant_service_id", "service_type_id", "brand_id", name="uq_tsb_service_type_brand"),
        Index("ix_tsb_tenant_service", "tenant_service_id"),
        Index("ix_tsb_service_type", "service_type_id"),
    )

    tenant_id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_service_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    service_type_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id:               Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    is_enabled:             Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    tenant_price_adjustment:Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tenant_min_price:       Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tenant_max_price:       Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)


# ── Master Offerings ──────────────────────────────────────────────────────────
class MasterOffering(ServiceOSBase):
    """Platform-wide customer-facing offering per category (Sprint 14)."""
    __tablename__ = "master_offerings"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_mo_slug"),
        Index("ix_mo_category",          "category_id"),
        Index("ix_mo_active",            "is_active"),
        Index("ix_mo_customer_flow_type","customer_flow_type"),
    )

    category_id:               Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    name:                      Mapped[str]            = mapped_column(String(200), nullable=False)
    slug:                      Mapped[str]            = mapped_column(String(200), nullable=False)
    description:               Mapped[str | None]     = mapped_column(Text, nullable=True)
    offering_class:            Mapped[str]            = mapped_column(String(50), nullable=False)   # service|appointment|lead|order
    image_url:                 Mapped[str | None]     = mapped_column(String(500), nullable=True)
    icon_url:                  Mapped[str | None]     = mapped_column(String(500), nullable=True)
    # Customer flow
    customer_flow_type:        Mapped[str | None]     = mapped_column(String(50), nullable=True)
    primary_engine_key:        Mapped[str | None]     = mapped_column(String(100), nullable=True)
    # Pricing
    default_pricing_model:     Mapped[str]            = mapped_column(String(30), nullable=False)
    default_base_price:        Mapped[Decimal]        = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    default_visit_fee:         Mapped[Decimal]        = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    default_appointment_fee:   Mapped[Decimal]        = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    default_lead_fee:          Mapped[Decimal]        = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    default_min_price:         Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    default_max_price:         Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency:                  Mapped[str]            = mapped_column(String(10), default="INR", nullable=False)
    # Requirements
    is_brand_required:         Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_type_required:          Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_checklist:        Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_address:          Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_slot:             Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_photo_upload:     Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_customer_notes:   Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    # Misc
    allow_provider_override:   Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    estimated_duration_minutes:Mapped[int | None]     = mapped_column(Integer, nullable=True)
    tags:                      Mapped[list | None]    = mapped_column(JSONB, nullable=True)
    extra_metadata:            Mapped[dict | None]    = mapped_column("metadata", JSONB, nullable=True)
    display_order:             Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    status:                    Mapped[str]            = mapped_column(String(20), default="active", nullable=False)
    is_active:                 Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    deleted_at:                Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)


# ── Customer Flow Configs ──────────────────────────────────────────────────────
# ── Service Option Groups ─────────────────────────────────────────────────────
class ServiceOptionGroup(ServiceOSBase):
    """Logical grouping for service options (Sprint 34E). E.g. 'AC Type', 'Washer Type'."""
    __tablename__ = "service_option_groups"
    __table_args__ = (
        UniqueConstraint("code", name="uq_sog_code"),
        Index("ix_sog_category", "category_id"),
        Index("ix_sog_status",   "status"),
    )

    code:          Mapped[str]            = mapped_column(String(80),  nullable=False)
    name:          Mapped[str]            = mapped_column(String(200), nullable=False)
    description:   Mapped[str | None]    = mapped_column(Text, nullable=True)
    category_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    vertical_type: Mapped[str | None]    = mapped_column(String(50), nullable=True)
    status:        Mapped[str]           = mapped_column(String(30), default="active", nullable=False)
    display_order: Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    deleted_at:    Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":            str(self.id),
            "code":          self.code,
            "name":          self.name,
            "description":   self.description,
            "category_id":   str(self.category_id) if self.category_id else None,
            "vertical_type": self.vertical_type,
            "status":        self.status,
            "display_order": self.display_order,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
            "updated_at":    self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Master Issue Types ────────────────────────────────────────────────────────
class MasterIssueType(ServiceOSBase):
    """Platform-defined problem/fault types per service (Sprint 34C/34E). Admin-only write."""
    __tablename__ = "master_issue_types"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_mit_slug"),
        Index("ix_mit_category",       "category_id"),
        Index("ix_mit_master_service", "master_service_id"),
        Index("ix_mit_active",         "is_active"),
        Index("ix_mit_status",         "status"),
    )

    category_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    master_service_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    code:                 Mapped[str]              = mapped_column(String(80),  nullable=False)
    name:                 Mapped[str]              = mapped_column(String(200), nullable=False)
    slug:                 Mapped[str]              = mapped_column(String(200), nullable=False)
    description:          Mapped[str | None]      = mapped_column(Text, nullable=True)
    severity:             Mapped[str]              = mapped_column(String(20), nullable=False, default="medium")
    is_active:            Mapped[bool]            = mapped_column(Boolean, default=True, nullable=False)
    display_order:        Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    # Sprint 34E additions
    vertical_type:        Mapped[str | None]      = mapped_column(String(50), nullable=True)
    status:               Mapped[str]             = mapped_column(String(30), default="active", nullable=False)
    metadata_json:        Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    requires_photo:       Mapped[bool]            = mapped_column(Boolean, default=False, nullable=False)
    requires_description: Mapped[bool]            = mapped_column(Boolean, default=False, nullable=False)
    customer_visible:     Mapped[bool]            = mapped_column(Boolean, default=True,  nullable=False)
    created_by_user_id:   Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:   Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "category_id":          str(self.category_id) if self.category_id else None,
            "master_service_id":    str(self.master_service_id) if self.master_service_id else None,
            "code":                 self.code,
            "name":                 self.name,
            "slug":                 self.slug,
            "description":          self.description,
            "severity":             self.severity,
            "is_active":            self.is_active,
            "customer_visible":     self.customer_visible,
            "display_order":        self.display_order,
            "vertical_type":        self.vertical_type,
            "status":               self.status,
            "metadata_json":        self.metadata_json,
            "requires_photo":       self.requires_photo,
            "requires_description": self.requires_description,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Master Service Options ────────────────────────────────────────────────────
class MasterServiceOption(ServiceOSBase):
    """Platform-defined service add-ons/extras per service (Sprint 34C/34E). Admin-only write."""
    __tablename__ = "master_service_options"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_mso_slug"),
        Index("ix_mso_category",       "category_id"),
        Index("ix_mso_master_service", "master_service_id"),
        Index("ix_mso_active",         "is_active"),
        Index("ix_mso_status",         "status"),
        Index("ix_mso_option_group",   "option_group_id"),
    )

    category_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    master_service_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    code:                   Mapped[str]              = mapped_column(String(80),  nullable=False)
    name:                   Mapped[str]              = mapped_column(String(200), nullable=False)
    slug:                   Mapped[str]              = mapped_column(String(200), nullable=False)
    description:            Mapped[str | None]      = mapped_column(Text, nullable=True)
    option_type:            Mapped[str]              = mapped_column(String(30), nullable=False, default="add_on")
    unit:                   Mapped[str]              = mapped_column(String(30), nullable=False, default="per_unit")
    default_price:          Mapped[Decimal]          = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    min_price:              Mapped[Decimal | None]   = mapped_column(Numeric(12, 2), nullable=True)
    max_price:              Mapped[Decimal | None]   = mapped_column(Numeric(12, 2), nullable=True)
    is_customer_selectable: Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    is_active:              Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    display_order:          Mapped[int]              = mapped_column(Integer, default=0, nullable=False)
    # Sprint 34E additions
    option_group_id:        Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)
    vertical_type:          Mapped[str | None]       = mapped_column(String(50), nullable=True)
    status:                 Mapped[str]              = mapped_column(String(30), default="active", nullable=False)
    metadata_json:          Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    created_by_user_id:     Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:     Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                     str(self.id),
            "category_id":            str(self.category_id) if self.category_id else None,
            "master_service_id":      str(self.master_service_id) if self.master_service_id else None,
            "code":                   self.code,
            "name":                   self.name,
            "slug":                   self.slug,
            "description":            self.description,
            "option_type":            self.option_type,
            "unit":                   self.unit,
            "default_price":          str(self.default_price),
            "min_price":              str(self.min_price) if self.min_price is not None else None,
            "max_price":              str(self.max_price) if self.max_price is not None else None,
            "is_customer_selectable": self.is_customer_selectable,
            "is_active":              self.is_active,
            "display_order":          self.display_order,
            "option_group_id":        str(self.option_group_id) if self.option_group_id else None,
            "vertical_type":          self.vertical_type,
            "status":                 self.status,
            "metadata_json":          self.metadata_json,
            "created_at":             self.created_at.isoformat() if self.created_at else None,
            "updated_at":             self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Service Option Mapping (M2M) ──────────────────────────────────────────────
class ServiceOptionMapping(ServiceOSBase):
    """Admin-defined M2M: which options are valid for a master service (Sprint 34E)."""
    __tablename__ = "service_option_mappings"
    __table_args__ = (
        UniqueConstraint("master_service_id", "service_option_id", name="uq_som_service_option"),
        Index("ix_som_service", "master_service_id"),
        Index("ix_som_option",  "service_option_id"),
        Index("ix_som_status",  "status"),
    )

    master_service_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    service_option_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    option_group_id:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:              Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    is_required:         Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_default:          Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    display_order:       Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    metadata_json:       Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    created_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at:          Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                 str(self.id),
            "master_service_id":  str(self.master_service_id),
            "service_option_id":  str(self.service_option_id),
            "option_group_id":    str(self.option_group_id) if self.option_group_id else None,
            "status":             self.status,
            "is_required":        self.is_required,
            "is_default":         self.is_default,
            "display_order":      self.display_order,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
            "updated_at":         self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Service Issue Mapping (M2M) ───────────────────────────────────────────────
class ServiceIssueMapping(ServiceOSBase):
    """Admin-defined M2M: which issue types apply to a master service (Sprint 34E)."""
    __tablename__ = "service_issue_mappings"
    __table_args__ = (
        UniqueConstraint("master_service_id", "issue_type_id", name="uq_sim_service_issue"),
        Index("ix_sim_service", "master_service_id"),
        Index("ix_sim_issue",   "issue_type_id"),
        Index("ix_sim_status",  "status"),
        Index("ix_sim_common",  "is_common"),
    )

    master_service_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    issue_type_id:        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    status:               Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    is_common:            Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_default:           Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    customer_visible:     Mapped[bool]           = mapped_column(Boolean, default=True,  nullable=False)
    requires_photo:       Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    requires_description: Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    severity_override:    Mapped[str|None]       = mapped_column(String(30), nullable=True)
    display_order:        Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    metadata_json:        Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    created_by_user_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at:           Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "master_service_id":    str(self.master_service_id),
            "issue_type_id":        str(self.issue_type_id),
            "status":               self.status,
            "is_common":            self.is_common,
            "is_default":           self.is_default,
            "customer_visible":     self.customer_visible,
            "requires_photo":       self.requires_photo,
            "requires_description": self.requires_description,
            "severity_override":    self.severity_override,
            "display_order":        self.display_order,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Tenant Supported Service Options ─────────────────────────────────────────
class TenantSupportedServiceOption(ServiceOSBase):
    """Provider's explicitly supported service options per service (Sprint 34E)."""
    __tablename__ = "tenant_supported_service_options"
    __table_args__ = (
        UniqueConstraint("tenant_id", "master_service_id", "service_option_id",
                         name="uq_tsso_tenant_service_option"),
        Index("ix_tsso_tenant",  "tenant_id"),
        Index("ix_tsso_service", "master_service_id"),
        Index("ix_tsso_option",  "service_option_id"),
        Index("ix_tsso_status",  "status"),
    )

    tenant_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    provider_profile_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    master_service_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    service_option_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    status:              Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    notes:               Mapped[str|None]       = mapped_column(Text, nullable=True)
    created_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at:          Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                  str(self.id),
            "tenant_id":           str(self.tenant_id),
            "master_service_id":   str(self.master_service_id),
            "service_option_id":   str(self.service_option_id),
            "status":              self.status,
            "notes":               self.notes,
            "created_by_user_id":  str(self.created_by_user_id) if self.created_by_user_id else None,
            "approved_by_user_id": str(self.approved_by_user_id) if self.approved_by_user_id else None,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
            "updated_at":          self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Master Workflow Templates ─────────────────────────────────────────────────
class MasterWorkflowTemplate(ServiceOSBase):
    """Platform-defined job workflow definitions per service/category (Sprint 34C,
    upgraded to enterprise runtime-configurable workflow engine — P0 sprint)."""
    __tablename__ = "master_workflow_templates"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_mwt_slug"),
        Index("ix_mwt_category",       "category_id"),
        Index("ix_mwt_master_service", "master_service_id"),
        Index("ix_mwt_workflow_type",  "workflow_type"),
        Index("ix_mwt_active",         "is_active"),
    )

    category_id:                 Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    master_service_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name:                        Mapped[str]              = mapped_column(String(200), nullable=False)
    slug:                        Mapped[str]              = mapped_column(String(200), nullable=False)
    description:                 Mapped[str | None]      = mapped_column(Text, nullable=True)
    workflow_type:               Mapped[str]              = mapped_column(String(30), nullable=False)
    steps:                       Mapped[list]             = mapped_column(JSONB, default=list, nullable=False)
    estimated_duration_minutes:  Mapped[int | None]      = mapped_column(Integer, nullable=True)
    is_active:                   Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    display_order:               Mapped[int]              = mapped_column(Integer, default=0, nullable=False)

    # ── P0 Enterprise Workflow Upgrade (migration 086) ────────────────────────
    status:                       Mapped[str]              = mapped_column(String(20), default="active", nullable=False)
    service_group_id:             Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_type_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    transitions:                  Mapped[list]             = mapped_column(JSONB, default=list, nullable=False)
    max_sla_hours:                Mapped[int | None]      = mapped_column(Integer, nullable=True)
    requires_technician_assignment:      Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_customer_confirmation:      Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_photo_proof:                Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_part_approval:              Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_estimate_approval:          Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_direct_payment_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allows_reschedule:                   Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allows_cancellation:                 Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allows_dispute_after_completion:     Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version_number:               Mapped[int]              = mapped_column(Integer, default=1, nullable=False)
    parent_template_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_latest:                    Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    activated_at:                 Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at:                Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                         str(self.id),
            "category_id":                str(self.category_id) if self.category_id else None,
            "master_service_id":          str(self.master_service_id) if self.master_service_id else None,
            "service_group_id":           str(self.service_group_id) if self.service_group_id else None,
            "service_type_id":            str(self.service_type_id) if self.service_type_id else None,
            "name":                       self.name,
            "slug":                       self.slug,
            "template_code":              self.slug,
            "description":                self.description,
            "workflow_type":              self.workflow_type,
            "steps":                      self.steps or [],
            "transitions":                self.transitions or [],
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "max_sla_hours":              self.max_sla_hours,
            "is_active":                  self.is_active,
            "status":                     self.status,
            "display_order":              self.display_order,
            "requires_technician_assignment":       self.requires_technician_assignment,
            "requires_customer_confirmation":       self.requires_customer_confirmation,
            "requires_photo_proof":                 self.requires_photo_proof,
            "requires_part_approval":               self.requires_part_approval,
            "requires_estimate_approval":           self.requires_estimate_approval,
            "requires_direct_payment_confirmation": self.requires_direct_payment_confirmation,
            "allows_reschedule":                    self.allows_reschedule,
            "allows_cancellation":                  self.allows_cancellation,
            "allows_dispute_after_completion":       self.allows_dispute_after_completion,
            "version_number":             self.version_number,
            "parent_template_id":         str(self.parent_template_id) if self.parent_template_id else None,
            "is_latest":                  self.is_latest,
            "activated_at":               self.activated_at.isoformat() if self.activated_at else None,
            "deprecated_at":              self.deprecated_at.isoformat() if self.deprecated_at else None,
            "created_by_user_id":         str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at":                 self.created_at.isoformat() if self.created_at else None,
            "updated_at":                 self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowServiceMapping(ServiceOSBase):
    """Maps a workflow template to category/service/service-type/brand/tenant scope,
    with priority ordering — more specific mapping wins at runtime resolution."""
    __tablename__ = "workflow_service_mappings"
    __table_args__ = (
        Index("ix_wsm_template",        "template_id"),
        Index("ix_wsm_category",        "category_id"),
        Index("ix_wsm_master_service",  "master_service_id"),
        Index("ix_wsm_service_type",    "service_type_id"),
    )

    template_id:        Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:        Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    service_group_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    master_service_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_type_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    priority:           Mapped[int]              = mapped_column(Integer, default=0, nullable=False)
    status:             Mapped[str]              = mapped_column(String(20), default="active", nullable=False)

    def to_dict(self) -> dict:
        return {
            "id":                str(self.id),
            "template_id":       str(self.template_id),
            "category_id":       str(self.category_id),
            "service_group_id":  str(self.service_group_id) if self.service_group_id else None,
            "master_service_id": str(self.master_service_id) if self.master_service_id else None,
            "service_type_id":   str(self.service_type_id) if self.service_type_id else None,
            "brand_id":          str(self.brand_id) if self.brand_id else None,
            "tenant_id":         str(self.tenant_id) if self.tenant_id else None,
            "priority":          self.priority,
            "status":            self.status,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
            "updated_at":        self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Master Data Audit Log ─────────────────────────────────────────────────────
class MasterDataAuditLog(ServiceOSBase):
    """Append-only change trail for all master data entities (Sprint 34C)."""
    __tablename__ = "master_data_audit_log"
    __table_args__ = (
        Index("ix_mdal_entity",     "entity_type", "entity_id"),
        Index("ix_mdal_actor",      "actor_user_id"),
        Index("ix_mdal_action",     "action"),
        Index("ix_mdal_created_at", "created_at"),
    )

    entity_type:    Mapped[str]              = mapped_column(String(60),  nullable=False)
    entity_id:      Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    action:         Mapped[str]              = mapped_column(String(30),  nullable=False)
    actor_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:     Mapped[str | None]      = mapped_column(String(30),  nullable=True)
    old_value:      Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    new_value:      Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    change_summary: Mapped[str | None]      = mapped_column(Text, nullable=True)
    request_id:     Mapped[str | None]      = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":             str(self.id),
            "entity_type":    self.entity_type,
            "entity_id":      str(self.entity_id),
            "action":         self.action,
            "actor_user_id":  str(self.actor_user_id) if self.actor_user_id else None,
            "actor_role":     self.actor_role,
            "old_value":      self.old_value,
            "new_value":      self.new_value,
            "change_summary": self.change_summary,
            "request_id":     self.request_id,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
        }


# ── Service Setup Templates ───────────────────────────────────────────────────
class ServiceSetupTemplate(ServiceOSBase):
    # LEGACY (Sprint 34F, superseded by migration 097 / app/engines/service_setup):
    # renamed off "service_setup_templates" to stop a SQLAlchemy table-name
    # collision with the new engine's model of the same original name.
    """Reusable service setup starter pack / template (Sprint 34F)."""
    __tablename__ = "service_setup_templates_legacy_34f"
    __table_args__ = (
        UniqueConstraint("code", name="uq_sst_code"),
        UniqueConstraint("slug", name="uq_sst_slug"),
        Index("ix_sst_status",   "status"),
        Index("ix_sst_vertical", "vertical_type"),
        Index("ix_sst_type",     "template_type"),
        Index("ix_sst_system",   "is_system_template"),
    )

    code:                Mapped[str]            = mapped_column(String(80),  nullable=False)
    name:                Mapped[str]            = mapped_column(String(200), nullable=False)
    slug:                Mapped[str]            = mapped_column(String(200), nullable=False)
    description:         Mapped[str | None]    = mapped_column(Text, nullable=True)
    vertical_type:       Mapped[str | None]    = mapped_column(String(50), nullable=True)
    category_id:         Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    template_type:       Mapped[str]           = mapped_column(String(50), default="starter_pack", nullable=False)
    status:              Mapped[str]           = mapped_column(String(30), default="draft", nullable=False)
    version:             Mapped[int]           = mapped_column(Integer, default=1, nullable=False)
    is_system_template:  Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json:       Mapped[dict|None]     = mapped_column(JSONB, nullable=True)
    deleted_at:          Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                str(self.id),
            "code":              self.code,
            "name":              self.name,
            "slug":              self.slug,
            "description":       self.description,
            "vertical_type":     self.vertical_type,
            "category_id":       str(self.category_id) if self.category_id else None,
            "template_type":     self.template_type,
            "status":            self.status,
            "version":           self.version,
            "is_system_template":self.is_system_template,
            "metadata_json":     self.metadata_json,
            "created_by_user_id":str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
            "updated_at":        self.updated_at.isoformat() if self.updated_at else None,
        }


class ServiceSetupTemplateItem(ServiceOSBase):
    """An item within a service setup template (Sprint 34F). LEGACY — see
    ServiceSetupTemplate above; renamed to avoid colliding with the newer
    app/engines/service_setup table of the same original name."""
    __tablename__ = "service_setup_template_items_legacy_34f"
    __table_args__ = (
        Index("ix_ssti_template",  "template_id"),
        Index("ix_ssti_item_type", "item_type"),
        Index("ix_ssti_ref_id",    "reference_id"),
        Index("ix_ssti_ref_code",  "reference_code"),
        Index("ix_ssti_status",    "status"),
    )

    template_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    item_type:      Mapped[str]            = mapped_column(String(50), nullable=False)
    reference_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_code: Mapped[str | None]    = mapped_column(String(80), nullable=True)
    payload_json:   Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)
    apply_mode:     Mapped[str]           = mapped_column(String(30), default="create_if_missing", nullable=False)
    is_required:    Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    display_order:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    status:         Mapped[str]           = mapped_column(String(30), default="active", nullable=False)
    deleted_at:     Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":             str(self.id),
            "template_id":    str(self.template_id),
            "item_type":      self.item_type,
            "reference_id":   str(self.reference_id) if self.reference_id else None,
            "reference_code": self.reference_code,
            "payload_json":   self.payload_json,
            "apply_mode":     self.apply_mode,
            "is_required":    self.is_required,
            "display_order":  self.display_order,
            "status":         self.status,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
            "updated_at":     self.updated_at.isoformat() if self.updated_at else None,
        }


class ServiceSetupTemplateRelationship(ServiceOSBase):
    """A relationship between two template items (Sprint 34F)."""
    __tablename__ = "service_setup_template_relationships"
    __table_args__ = (
        Index("ix_sstr_template",  "template_id"),
        Index("ix_sstr_source",    "source_item_id"),
        Index("ix_sstr_target",    "target_item_id"),
        Index("ix_sstr_rel_type",  "relationship_type"),
    )

    template_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    source_item_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    target_item_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_type: Mapped[str]            = mapped_column(String(50), nullable=False)
    payload_json:      Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    status:            Mapped[str]            = mapped_column(String(30), default="active", nullable=False)
    display_order:     Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    deleted_at:        Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                str(self.id),
            "template_id":       str(self.template_id),
            "source_item_id":    str(self.source_item_id),
            "target_item_id":    str(self.target_item_id),
            "relationship_type": self.relationship_type,
            "payload_json":      self.payload_json,
            "status":            self.status,
            "display_order":     self.display_order,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
        }


class ServiceSetupTemplateRun(ServiceOSBase):
    """Tracks a template application run (Sprint 34F)."""
    __tablename__ = "service_setup_template_runs"
    __table_args__ = (
        Index("ix_sst_run_template", "template_id"),
        Index("ix_sst_run_status",   "status"),
        Index("ix_sst_run_actor",    "applied_by_user_id"),
    )

    template_id:        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    version:            Mapped[int]            = mapped_column(Integer, default=1, nullable=False)
    applied_by_user_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_scope:       Mapped[str]            = mapped_column(String(30), default="platform", nullable=False)
    target_category_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_service_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_tenant_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:             Mapped[str]            = mapped_column(String(30), default="running", nullable=False)
    summary_json:       Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    error_json:         Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    completed_at:       Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                 str(self.id),
            "template_id":        str(self.template_id),
            "version":            self.version,
            "applied_by_user_id": str(self.applied_by_user_id) if self.applied_by_user_id else None,
            "target_scope":       self.target_scope,
            "status":             self.status,
            "summary_json":       self.summary_json,
            "error_json":         self.error_json,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
            "completed_at":       self.completed_at.isoformat() if self.completed_at else None,
        }


class ServiceSetupTemplateRunItem(ServiceOSBase):
    """Individual action record within a template run (Sprint 34F)."""
    __tablename__ = "service_setup_template_run_items"
    __table_args__ = (
        Index("ix_sst_run_item_run",    "run_id"),
        Index("ix_sst_run_item_action", "action"),
    )

    run_id:             Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    template_item_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action:             Mapped[str]            = mapped_column(String(30), nullable=False)
    target_record_type: Mapped[str|None]       = mapped_column(String(50), nullable=True)
    target_record_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    message:            Mapped[str|None]       = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                 str(self.id),
            "run_id":             str(self.run_id),
            "template_item_id":   str(self.template_item_id) if self.template_item_id else None,
            "action":             self.action,
            "target_record_type": self.target_record_type,
            "target_record_id":   str(self.target_record_id) if self.target_record_id else None,
            "message":            self.message,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
        }


# ── Admin Bulk Setup Wizard ───────────────────────────────────────────────────
class AdminBulkSetupDraft(ServiceOSBase):
    """Stores admin bulk setup wizard draft state (Sprint 34H)."""
    __tablename__ = "admin_bulk_setup_drafts"
    __table_args__ = (
        Index("ix_abs_draft_creator",  "created_by_user_id"),
        Index("ix_abs_draft_status",   "status"),
        Index("ix_abs_draft_vertical", "target_vertical_type"),
        Index("ix_abs_draft_category", "target_category_id"),
    )

    created_by_user_id:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:                      Mapped[str]            = mapped_column(String(30), default="draft", nullable=False)
    current_step:                Mapped[int]            = mapped_column(Integer, default=1, nullable=False)
    target_vertical_type:        Mapped[str|None]       = mapped_column(String(50), nullable=True)
    target_category_id:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_category_payload_json:Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    selected_service_ids_json:   Mapped[list|None]      = mapped_column(JSONB, nullable=True)
    new_services_payload_json:   Mapped[list|None]      = mapped_column(JSONB, nullable=True)
    selected_template_ids_json:  Mapped[list|None]      = mapped_column(JSONB, nullable=True)
    bulk_setup_payload_json:     Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    preview_summary_json:        Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    blocking_items_json:         Mapped[list|None]      = mapped_column(JSONB, nullable=True)
    last_previewed_at:           Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at:                  Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at:                  Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                           str(self.id),
            "created_by_user_id":           str(self.created_by_user_id) if self.created_by_user_id else None,
            "status":                       self.status,
            "current_step":                 self.current_step,
            "target_vertical_type":         self.target_vertical_type,
            "target_category_id":           str(self.target_category_id) if self.target_category_id else None,
            "target_category_payload_json": self.target_category_payload_json,
            "selected_service_ids_json":    self.selected_service_ids_json,
            "new_services_payload_json":    self.new_services_payload_json,
            "selected_template_ids_json":   self.selected_template_ids_json,
            "bulk_setup_payload_json":      self.bulk_setup_payload_json,
            "preview_summary_json":         self.preview_summary_json,
            "blocking_items_json":          self.blocking_items_json,
            "last_previewed_at":            self.last_previewed_at.isoformat() if self.last_previewed_at else None,
            "applied_at":                   self.applied_at.isoformat() if self.applied_at else None,
            "created_at":                   self.created_at.isoformat() if self.created_at else None,
            "updated_at":                   self.updated_at.isoformat() if self.updated_at else None,
        }


class AdminBulkSetupRun(ServiceOSBase):
    """Tracks a bulk setup apply execution (Sprint 34H)."""
    __tablename__ = "admin_bulk_setup_runs"
    __table_args__ = (
        Index("ix_abs_run_draft",  "draft_id"),
        Index("ix_abs_run_status", "status"),
        Index("ix_abs_run_actor",  "applied_by_user_id"),
    )

    draft_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    applied_by_user_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:             Mapped[str]            = mapped_column(String(30), default="running", nullable=False)
    target_vertical_type: Mapped[str|None]     = mapped_column(String(50), nullable=True)
    target_category_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    summary_json:       Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    error_json:         Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    completed_at:       Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "draft_id":             str(self.draft_id),
            "applied_by_user_id":   str(self.applied_by_user_id) if self.applied_by_user_id else None,
            "status":               self.status,
            "target_vertical_type": self.target_vertical_type,
            "target_category_id":   str(self.target_category_id) if self.target_category_id else None,
            "summary_json":         self.summary_json,
            "error_json":           self.error_json,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "completed_at":         self.completed_at.isoformat() if self.completed_at else None,
        }


class AdminBulkSetupRunItem(ServiceOSBase):
    """Individual action record within a bulk setup run (Sprint 34H)."""
    __tablename__ = "admin_bulk_setup_run_items"
    __table_args__ = (
        Index("ix_abs_run_item_run",    "run_id"),
        Index("ix_abs_run_item_type",   "entity_type"),
        Index("ix_abs_run_item_action", "action"),
    )

    run_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str]            = mapped_column(String(50), nullable=False)
    entity_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    entity_code: Mapped[str|None]       = mapped_column(String(80), nullable=True)
    action:      Mapped[str]            = mapped_column(String(20), nullable=False)
    message:     Mapped[str|None]       = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":          str(self.id),
            "run_id":      str(self.run_id),
            "entity_type": self.entity_type,
            "entity_id":   str(self.entity_id) if self.entity_id else None,
            "entity_code": self.entity_code,
            "action":      self.action,
            "message":     self.message,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }


# ── Sprint 34I — Recommendation Rules Engine ─────────────────────────────────

class RecommendationRule(ServiceOSBase):
    """Admin-defined rule for automatic platform recommendations."""
    __tablename__ = "recommendation_rules"
    __table_args__ = (
        UniqueConstraint("code", name="uq_rr_code"),
        Index("ix_rr_status",    "status"),
        Index("ix_rr_rule_type", "rule_type"),
        Index("ix_rr_scope",     "scope"),
        Index("ix_rr_category",  "category_id"),
        Index("ix_rr_service",   "service_id"),
        Index("ix_rr_priority",  "priority"),
        Index("ix_rr_vertical",  "vertical_type"),
    )

    code:                 Mapped[str]            = mapped_column(String(100), nullable=False)
    name:                 Mapped[str]            = mapped_column(String(200), nullable=False)
    description:          Mapped[str | None]     = mapped_column(Text, nullable=True)
    rule_type:            Mapped[str]            = mapped_column(String(60), nullable=False)
    scope:                Mapped[str]            = mapped_column(String(30), default="platform", nullable=False)
    vertical_type:        Mapped[str | None]     = mapped_column(String(60), nullable=True)
    category_id:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_id:           Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:            Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    location_id:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    priority:             Mapped[int]            = mapped_column(Integer, default=100, nullable=False)
    status:               Mapped[str]            = mapped_column(String(30), default="draft", nullable=False)
    condition_json:       Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    recommendation_json:  Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    explanation_template: Mapped[str | None]     = mapped_column(Text, nullable=True)
    created_by_user_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json:        Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    deleted_at:           Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    VALID_RULE_TYPES = {
        "brand", "service_option", "issue_type", "document_requirement",
        "checklist_template", "pricing_template", "commission_template",
        "workflow_template", "provider_default", "customer_next_step",
    }
    VALID_SCOPES = {"platform", "vertical", "category", "service", "tenant", "location", "customer_flow"}
    VALID_STATUSES = {"draft", "active", "inactive", "archived"}

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "code":                 self.code,
            "name":                 self.name,
            "description":          self.description,
            "rule_type":            self.rule_type,
            "scope":                self.scope,
            "vertical_type":        self.vertical_type,
            "category_id":          str(self.category_id) if self.category_id else None,
            "service_id":           str(self.service_id) if self.service_id else None,
            "tenant_id":            str(self.tenant_id) if self.tenant_id else None,
            "location_id":          str(self.location_id) if self.location_id else None,
            "priority":             self.priority,
            "status":               self.status,
            "condition_json":       self.condition_json or {},
            "recommendation_json":  self.recommendation_json or {},
            "explanation_template": self.explanation_template,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }


class RecommendationResult(ServiceOSBase):
    """Tracks each recommendation shown/accepted/rejected/auto-applied."""
    __tablename__ = "recommendation_results"
    __table_args__ = (
        Index("ix_res_context_type",  "context_type"),
        Index("ix_res_rule_id",       "rule_id"),
        Index("ix_res_status",        "status"),
        Index("ix_res_tenant",        "tenant_id"),
        Index("ix_res_actor",         "actor_user_id"),
        Index("ix_res_entity_type",   "recommended_entity_type"),
    )

    request_id:               Mapped[str | None]       = mapped_column(String(100), nullable=True)
    actor_user_id:            Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:                Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id:              Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)
    context_type:             Mapped[str]              = mapped_column(String(60), nullable=False)
    context_id:               Mapped[str | None]       = mapped_column(String(200), nullable=True)
    rule_id:                  Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)
    rule_type:                Mapped[str | None]       = mapped_column(String(60), nullable=True)
    input_json:               Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    recommended_entity_type:  Mapped[str | None]       = mapped_column(String(60), nullable=True)
    recommended_entity_id:    Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)
    recommended_payload_json: Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    confidence_score:         Mapped[Decimal | None]   = mapped_column(Numeric(4, 3), nullable=True)
    explanation:              Mapped[str | None]       = mapped_column(Text, nullable=True)
    status:                   Mapped[str]              = mapped_column(String(30), default="shown", nullable=False)

    VALID_STATUSES = {"shown", "accepted", "rejected", "auto_applied", "ignored", "failed"}

    def to_dict(self) -> dict:
        return {
            "id":                       str(self.id),
            "request_id":               self.request_id,
            "actor_user_id":            str(self.actor_user_id) if self.actor_user_id else None,
            "tenant_id":                str(self.tenant_id) if self.tenant_id else None,
            "customer_id":              str(self.customer_id) if self.customer_id else None,
            "context_type":             self.context_type,
            "context_id":               self.context_id,
            "rule_id":                  str(self.rule_id) if self.rule_id else None,
            "rule_type":                self.rule_type,
            "recommended_entity_type":  self.recommended_entity_type,
            "recommended_entity_id":    str(self.recommended_entity_id) if self.recommended_entity_id else None,
            "recommended_payload_json": self.recommended_payload_json,
            "confidence_score":         float(self.confidence_score) if self.confidence_score else None,
            "explanation":              self.explanation,
            "status":                   self.status,
            "created_at":               self.created_at.isoformat() if self.created_at else None,
            "updated_at":               self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
class CustomerFlowConfig(ServiceOSBase):
    """Per-category customer UX flow configuration (Sprint 14)."""
    __tablename__ = "customer_flow_configs"
    __table_args__ = (
        UniqueConstraint("category_id", name="uq_cfc_category"),
        Index("ix_cfc_category",  "category_id"),
        Index("ix_cfc_flow_type", "customer_flow_type"),
        Index("ix_cfc_active",    "is_active"),
    )

    category_id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_flow_type:    Mapped[str]       = mapped_column(String(50), nullable=False)
    frontend_component_key:Mapped[str]       = mapped_column(String(100), nullable=False)
    primary_engine_key:    Mapped[str]       = mapped_column(String(100), nullable=False)
    required_steps:        Mapped[list|None] = mapped_column(JSONB, nullable=True)
    optional_steps:        Mapped[list|None] = mapped_column(JSONB, nullable=True)
    config:                Mapped[dict|None] = mapped_column(JSONB, nullable=True)
    is_active:             Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 34J — Customer Booking Draft (unified cross-flow)
# ─────────────────────────────────────────────────────────────────────────────
class CustomerBookingDraft(ServiceOSBase):
    """Unified customer booking draft across all flow types.

    Backend validates all catalog selections — AI cannot invent IDs.
    Status: draft → estimated → confirmed → cancelled
    """
    __tablename__ = "customer_booking_drafts"
    __table_args__ = (
        Index("ix_cbd_customer_id",      "customer_id"),
        Index("ix_cbd_ai_session_id",    "ai_session_id"),
        Index("ix_cbd_status",           "status"),
        Index("ix_cbd_flow_type",        "flow_type"),
        Index("ix_cbd_category_service", "category_id", "service_id"),
    )

    VALID_FLOW_TYPES = {"service_booking", "appointment_booking", "lead_capture", "subscription_only"}
    VALID_STATUSES   = {"draft", "estimated", "confirmed", "cancelled"}

    # Identity
    customer_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    guest_session_id: Mapped[str | None]       = mapped_column(String(100), nullable=True)
    ai_session_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Flow
    flow_type: Mapped[str] = mapped_column(String(50), nullable=False, default="service_booking")

    # Catalog selections (all validated against active catalog before save)
    category_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    issue_type_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_option_ids: Mapped[list | None]      = mapped_column(JSONB, nullable=True)

    # Customer identity
    customer_name:  Mapped[str | None] = mapped_column(String(150), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(30),  nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Location
    city:         Mapped[str | None] = mapped_column(String(100), nullable=True)
    zipcode:      Mapped[str | None] = mapped_column(String(20),  nullable=True)
    address_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Issue description
    issue_summary: Mapped[str | None]  = mapped_column(Text, nullable=True)
    issue_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Scheduling (appointment_booking flow)
    preferred_date:      Mapped[date | None] = mapped_column(Date, nullable=True)
    preferred_time_slot: Mapped[str | None]  = mapped_column(String(50), nullable=True)

    # Lead capture
    lead_notes:   Mapped[str | None]  = mapped_column(Text, nullable=True)
    lead_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Estimate (computed by backend)
    estimate_min:      Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimate_max:      Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimate_currency: Mapped[str | None]     = mapped_column(String(10), nullable=True, default="INR")

    # Provider selection
    selected_tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")

    # Final record references (populated after confirmation)
    final_job_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    final_appointment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    final_lead_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Extra fields (flow-specific overrides)
    extra_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":               str(self.id),
            "flow_type":        self.flow_type,
            "status":           self.status,
            "customer_id":      str(self.customer_id) if self.customer_id else None,
            "guest_session_id": self.guest_session_id,
            "category_id":      str(self.category_id) if self.category_id else None,
            "service_id":       str(self.service_id) if self.service_id else None,
            "brand_id":         str(self.brand_id) if self.brand_id else None,
            "issue_type_id":    str(self.issue_type_id) if self.issue_type_id else None,
            "service_option_ids": self.service_option_ids,
            "customer_name":    self.customer_name,
            "customer_phone":   self.customer_phone,
            "customer_email":   self.customer_email,
            "city":             self.city,
            "zipcode":          self.zipcode,
            "address_text":     self.address_text,
            "issue_summary":    self.issue_summary,
            "preferred_date":   str(self.preferred_date) if self.preferred_date else None,
            "preferred_time_slot": self.preferred_time_slot,
            "estimate_min":     float(self.estimate_min) if self.estimate_min else None,
            "estimate_max":     float(self.estimate_max) if self.estimate_max else None,
            "estimate_currency": self.estimate_currency,
            "selected_tenant_id": str(self.selected_tenant_id) if self.selected_tenant_id else None,
            "final_job_id":     str(self.final_job_id) if self.final_job_id else None,
            "final_appointment_id": str(self.final_appointment_id) if self.final_appointment_id else None,
            "final_lead_id":    str(self.final_lead_id) if self.final_lead_id else None,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
            "updated_at":       self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Master Checklist Items (Phase 2 — admin/master-catalog-level, not
#    tenant-scoped like field_ops.ServiceChecklistTemplate) ────────────────────
class MasterChecklistItem(ServiceOSBase):
    """Platform-defined checklist item per master service — the admin-level
    catalog checklist (distinct from the tenant-owned runtime checklist
    system in app/engines/field_ops/models.py::ServiceChecklistTemplate)."""
    __tablename__ = "master_checklist_items"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_mci_slug"),
        Index("ix_mci_category",       "category_id"),
        Index("ix_mci_master_service", "master_service_id"),
        Index("ix_mci_active",         "is_active"),
        Index("ix_mci_status",         "status"),
    )

    category_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    master_service_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    workflow_step_key:    Mapped[str | None]       = mapped_column(String(100), nullable=True)
    code:                 Mapped[str]              = mapped_column(String(80),  nullable=False)
    title:                Mapped[str]              = mapped_column(String(200), nullable=False)
    slug:                 Mapped[str]              = mapped_column(String(200), nullable=False)
    description:          Mapped[str | None]       = mapped_column(Text, nullable=True)
    is_required:          Mapped[bool]              = mapped_column(Boolean, default=True, nullable=False)
    owner_role:           Mapped[str]              = mapped_column(String(30), default="technician", nullable=False)
    customer_visible:     Mapped[bool]              = mapped_column(Boolean, default=False, nullable=False)
    staff_visible:        Mapped[bool]              = mapped_column(Boolean, default=True, nullable=False)
    tenant_visible:       Mapped[bool]              = mapped_column(Boolean, default=True, nullable=False)
    is_active:            Mapped[bool]              = mapped_column(Boolean, default=True, nullable=False)
    status:               Mapped[str]              = mapped_column(String(30), default="active", nullable=False)
    display_order:        Mapped[int]              = mapped_column(Integer, default=0, nullable=False)
    vertical_type:        Mapped[str | None]       = mapped_column(String(50), nullable=True)
    metadata_json:        Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    created_by_user_id:   Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:   Mapped[uuid.UUID|None]   = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                str(self.id),
            "category_id":       str(self.category_id) if self.category_id else None,
            "master_service_id": str(self.master_service_id) if self.master_service_id else None,
            "workflow_step_key": self.workflow_step_key,
            "code":              self.code,
            "title":             self.title,
            "slug":              self.slug,
            "description":       self.description,
            "is_required":       self.is_required,
            "owner_role":        self.owner_role,
            "customer_visible":  self.customer_visible,
            "staff_visible":     self.staff_visible,
            "tenant_visible":    self.tenant_visible,
            "is_active":         self.is_active,
            "status":            self.status,
            "display_order":     self.display_order,
            "vertical_type":     self.vertical_type,
            "metadata_json":     self.metadata_json,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
            "updated_at":        self.updated_at.isoformat() if self.updated_at else None,
        }
