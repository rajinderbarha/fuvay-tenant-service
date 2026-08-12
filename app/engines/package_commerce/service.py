"""Sprint 5 — Package Commerce Service.

Handles: packages CRUD, package visibility, purchase flow (atomic),
         security deposit management, credit wallet top-up/adjust,
         commission calculation + deduction, storage quota.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP

import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.package_commerce.models import (
    ServicePackage, PackageFeature, PackageLimit,
    TenantPackagePurchase, TenantPackageAssignment, PackageAuditLog,
)
from app.engines.platform_commerce.models import (
    TenantWallet, WalletTransaction, SecurityDeposit,
    CommissionRecord,
)
from app.engines.platform_commerce.ledger import credit_wallet, debit_wallet
from app.engines.tenant_engine.models import TenantSettings, TenantLimits, Tenant
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("package_commerce")
utcnow = lambda: datetime.now(timezone.utc)

PLATFORM_DEFAULT_COMMISSION_RATE = Decimal("10.00")
PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD = Decimal("500.00")

VALID_PACKAGE_TYPES = {
    "onboarding_package",    # One-time provider onboarding fee (may include deposit + starting credits)
    "security_deposit_rule", # Deposit requirement definition — NOT spendable wallet credit
    "credit_topup",          # Provider buys spendable wallet credits for commission deduction
    "subscription_plan",     # Monthly/quarterly/yearly recurring plan (coaching, real estate…)
    "lead_credit_package",   # Lead credits for lead-based verticals (real estate etc.)
    "trial_plan",            # Free/limited-feature trial period
    "custom_plan",           # Miscellaneous/special plan
}
VALID_PLAN_LEVELS = {"starter", "growth", "enterprise", "custom"}


def _slugify(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class PackageCommerceService:
    """All package/credit/commission operations for Sprint 5."""

    def __init__(
        self,
        db: AsyncSession,
        request_id: str = "—",
        actor_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.ip_address = ip_address

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2 — PACKAGE ADMIN CRUD
    # ═══════════════════════════════════════════════════════════════

    async def create_package(self, data: dict) -> dict:
        pkg_type = data.get("package_type", "")
        if pkg_type not in VALID_PACKAGE_TYPES:
            raise ServiceOSException("PACKAGE_TYPE_INVALID",
                                     f"package_type must be one of {VALID_PACKAGE_TYPES}")

        price = Decimal(str(data.get("package_price", 0)))
        if price < 0:
            raise ServiceOSException("PACKAGE_PRICE_INVALID", "package_price cannot be negative.")

        deposit = Decimal(str(data.get("security_deposit_amount", 0)))
        credit = Decimal(str(data.get("included_credit_amount", 0)))

        # credit_topup = spendable wallet credits → must NOT carry a security deposit
        if pkg_type == "credit_topup" and deposit > 0:
            raise ServiceOSException("PACKAGE_PRICE_INVALID",
                                     "credit_topup packages must have security_deposit_amount = 0.")
        # security_deposit_rule = non-spendable trust deposit → must NOT carry included spendable credits
        if pkg_type == "security_deposit_rule" and credit > 0:
            raise ServiceOSException("PACKAGE_PRICE_INVALID",
                                     "security_deposit_rule must not include spendable credits. "
                                     "Security deposit is separate from provider credit wallet.")
        if deposit < 0:
            raise ServiceOSException("PACKAGE_PRICE_INVALID",
                                     "security_deposit_amount cannot be negative.")
        if credit < 0:
            raise ServiceOSException("PACKAGE_PRICE_INVALID",
                                     "included_credit_amount cannot be negative.")

        name = data.get("name", "").strip()
        if not name:
            raise ServiceOSException("VALIDATION_ERROR", "Package name is required.")

        slug = _slugify(name)
        existing = await self.db.execute(
            select(ServicePackage).where(ServicePackage.slug == slug,
                                        ServicePackage.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        commission_rate = data.get("commission_rate")
        storage_quota_gb = data.get("storage_quota_gb")
        plan_level = data.get("plan_level")
        if plan_level and plan_level not in VALID_PLAN_LEVELS:
            raise ServiceOSException("VALIDATION_ERROR", f"plan_level must be one of {VALID_PLAN_LEVELS}")

        def _dec(key: str, default: str = "0") -> Decimal | None:
            v = data.get(key)
            return Decimal(str(v)) if v is not None else None

        pkg = ServicePackage(
            name=name, slug=slug,
            description=data.get("description"),
            short_description=data.get("short_description"),
            package_type=pkg_type,
            plan_level=plan_level,
            package_price=price,
            security_deposit_amount=deposit,
            included_credit_amount=credit,
            storage_quota_gb=Decimal(str(storage_quota_gb)) if storage_quota_gb is not None else None,
            commission_rate=Decimal(str(commission_rate)) if commission_rate is not None else None,
            validity_days=data.get("validity_days"),
            trial_days=data.get("trial_days"),
            features=data.get("features") or {},
            is_active=bool(data.get("is_active", True)),
            display_order=int(data.get("display_order", 0)),
            created_by=self.actor_id,
            # Sprint 070 — signup fields
            vertical_type=data.get("vertical_type"),
            billing_cycle=data.get("billing_cycle"),
            currency=data.get("currency", "INR") or "INR",
            is_public_signup_visible=bool(data.get("is_public_signup_visible", False)),
            is_popular=bool(data.get("is_popular", False)),
            # Sprint P0 — extended fields
            badge_label=data.get("badge_label"),
            cta_label=data.get("cta_label"),
            terms_summary=data.get("terms_summary"),
            terms_content_json=data.get("terms_content_json"),
            is_featured=bool(data.get("is_featured", False)),
            is_recommended=bool(data.get("is_recommended", False)),
            bonus_credits=_dec("bonus_credits"),
            lead_credits=int(data["lead_credits"]) if data.get("lead_credits") is not None else None,
            setup_fee_amount=_dec("setup_fee_amount"),
            renewal_price_amount=_dec("renewal_price_amount"),
            refund_policy=data.get("refund_policy"),
            metadata_json=data.get("metadata_json"),
        )
        self.db.add(pkg)
        await self.db.flush()
        await self._pkg_audit(None, pkg.id, None, "package_created",
                              new_value=self._pkg_dict(pkg))
        logger.info("package.created", pkg_id=str(pkg.id), name=name, type=pkg_type)
        return self._pkg_dict(pkg)

    async def list_packages(
        self,
        package_type: str | None = None,
        is_active: bool | None = None,
        vertical_type: str | None = None,
    ) -> dict:
        q = select(ServicePackage).where(ServicePackage.deleted_at.is_(None))
        if package_type:
            q = q.where(ServicePackage.package_type == package_type)
        if is_active is not None:
            q = q.where(ServicePackage.is_active == is_active)
        if vertical_type:
            q = q.where(ServicePackage.vertical_type == vertical_type)
        q = q.order_by(ServicePackage.display_order, ServicePackage.created_at)
        r = await self.db.execute(q)
        pkgs = r.scalars().all()
        return {"packages": [self._pkg_dict(p) for p in pkgs], "total": len(pkgs)}

    async def list_public_packages(
        self,
        vertical_type: str | None = None,
        package_context: str | None = None,
    ) -> dict:
        """Public (unauthenticated) endpoint — returns only active, signup-visible packages
        with their features and limits included."""
        q = (
            select(ServicePackage)
            .where(ServicePackage.deleted_at.is_(None))
            .where(ServicePackage.is_active == True)  # noqa: E712
            .where(ServicePackage.is_public_signup_visible == True)  # noqa: E712
        )
        if vertical_type:
            q = q.where(ServicePackage.vertical_type == vertical_type)
        q = q.order_by(ServicePackage.display_order, ServicePackage.created_at)
        r = await self.db.execute(q)
        pkgs = r.scalars().all()

        results = []
        for pkg in pkgs:
            feats_r = await self.db.execute(
                select(PackageFeature)
                .where(PackageFeature.package_id == pkg.id,
                       PackageFeature.deleted_at.is_(None),
                       PackageFeature.status == "active")
                .order_by(PackageFeature.display_order)
            )
            lims_r = await self.db.execute(
                select(PackageLimit)
                .where(PackageLimit.package_id == pkg.id,
                       PackageLimit.deleted_at.is_(None),
                       PackageLimit.status == "active")
                .order_by(PackageLimit.display_order)
            )
            features = [self._feature_dict(f) for f in feats_r.scalars().all()]
            limits = [self._limit_dict(l) for l in lims_r.scalars().all()]
            results.append(self._pkg_dict(pkg, features=features, limits=limits))

        return {"packages": results, "total": len(results)}

    async def get_package(self, package_id: uuid.UUID) -> dict:
        pkg = await self._load_package(package_id)
        return self._pkg_dict(pkg)

    async def update_package(self, package_id: uuid.UUID, data: dict) -> dict:
        pkg = await self._load_package(package_id)
        old = self._pkg_dict(pkg)

        if "name" in data and data["name"].strip():
            pkg.name = data["name"].strip()
        if "description" in data:
            pkg.description = data["description"]
        if "package_price" in data:
            price = Decimal(str(data["package_price"]))
            if price < 0:
                raise ServiceOSException("PACKAGE_PRICE_INVALID", "package_price cannot be negative.")
            pkg.package_price = price
        if "security_deposit_amount" in data:
            dep = Decimal(str(data["security_deposit_amount"]))
            if dep < 0:
                raise ServiceOSException("PACKAGE_PRICE_INVALID", "security_deposit_amount cannot be negative.")
            if pkg.package_type == "credit_topup" and dep > 0:
                raise ServiceOSException("PACKAGE_PRICE_INVALID",
                                         "credit_topup packages cannot have security_deposit_amount > 0.")
            pkg.security_deposit_amount = dep
        if "included_credit_amount" in data:
            cr = Decimal(str(data["included_credit_amount"]))
            if cr < 0:
                raise ServiceOSException("PACKAGE_PRICE_INVALID", "included_credit_amount cannot be negative.")
            pkg.included_credit_amount = cr
        if "storage_quota_gb" in data:
            pkg.storage_quota_gb = Decimal(str(data["storage_quota_gb"])) if data["storage_quota_gb"] is not None else None
        if "commission_rate" in data:
            pkg.commission_rate = Decimal(str(data["commission_rate"])) if data["commission_rate"] is not None else None
        if "validity_days" in data:
            pkg.validity_days = data["validity_days"]
        if "features" in data:
            pkg.features = data["features"] or {}
        if "display_order" in data:
            pkg.display_order = int(data["display_order"])
        if "plan_level" in data:
            if data["plan_level"] and data["plan_level"] not in VALID_PLAN_LEVELS:
                raise ServiceOSException("VALIDATION_ERROR", f"plan_level must be one of {VALID_PLAN_LEVELS}")
            pkg.plan_level = data["plan_level"]
        if "vertical_type" in data:
            pkg.vertical_type = data["vertical_type"] or None
        if "billing_cycle" in data:
            pkg.billing_cycle = data["billing_cycle"] or None
        if "currency" in data and data["currency"]:
            pkg.currency = data["currency"]
        if "is_public_signup_visible" in data:
            pkg.is_public_signup_visible = bool(data["is_public_signup_visible"])
        if "is_popular" in data:
            pkg.is_popular = bool(data["is_popular"])
        # Sprint P0 extended fields
        for simple_field in (
            "short_description", "badge_label", "cta_label", "terms_summary",
            "refund_policy", "terms_content_json", "metadata_json",
        ):
            if simple_field in data:
                setattr(pkg, simple_field, data[simple_field] or None)
        if "trial_days" in data:
            pkg.trial_days = int(data["trial_days"]) if data["trial_days"] is not None else None
        if "is_featured" in data:
            pkg.is_featured = bool(data["is_featured"])
        if "is_recommended" in data:
            pkg.is_recommended = bool(data["is_recommended"])
        for dec_field in ("bonus_credits", "setup_fee_amount", "renewal_price_amount"):
            if dec_field in data:
                setattr(pkg, dec_field,
                        Decimal(str(data[dec_field])) if data[dec_field] is not None else None)
        if "lead_credits" in data:
            pkg.lead_credits = int(data["lead_credits"]) if data["lead_credits"] is not None else None

        await self._pkg_audit(None, pkg.id, None, "package_updated",
                              old_value=old, new_value=self._pkg_dict(pkg))
        return self._pkg_dict(pkg)

    async def activate_package(self, package_id: uuid.UUID) -> dict:
        pkg = await self._load_package(package_id)
        pkg.is_active = True
        await self._pkg_audit(None, pkg.id, None, "package_updated",
                              new_value={"is_active": True})
        return self._pkg_dict(pkg)

    async def deactivate_package(self, package_id: uuid.UUID) -> dict:
        pkg = await self._load_package(package_id)
        pkg.is_active = False
        await self._pkg_audit(None, pkg.id, None, "package_deactivated",
                              new_value={"is_active": False})
        return self._pkg_dict(pkg)

    async def delete_package(self, package_id: uuid.UUID) -> dict:
        pkg = await self._load_package(package_id)
        # MODULE-L5-32: this queried TenantPackagePurchase, whose backing
        # table (tenant_package_purchases) was never migrated -- this check
        # 500'd on every call instead of ever actually blocking a delete.
        # TenantPackageAssignment is the real, live table tenant purchases
        # are recorded in.
        r = await self.db.execute(
            select(TenantPackageAssignment).where(TenantPackageAssignment.package_id == package_id)
        )
        if r.scalar_one_or_none():
            raise ServiceOSException(
                "CONFLICT", "Cannot delete a package that has existing purchases. Deactivate instead."
            )
        pkg.deleted_at = utcnow()
        pkg.is_active = False
        await self._pkg_audit(None, pkg.id, None, "package_deactivated",
                              reason="soft_deleted")
        return {"package_id": str(package_id), "deleted": True}

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3 — TENANT PACKAGE VISIBILITY
    # ═══════════════════════════════════════════════════════════════

    async def get_available_packages(self, tenant_id: uuid.UUID) -> dict:
        deposit = await self._get_deposit(tenant_id)
        wallet = await self._get_wallet(tenant_id)
        deposit_status = deposit.status if deposit else "unpaid"
        deposit_paid = deposit_status == "paid"

        q = select(ServicePackage).where(
            ServicePackage.is_active == True,
            ServicePackage.deleted_at.is_(None),
        )
        if deposit_paid:
            # Hide onboarding packages after deposit paid
            q = q.where(ServicePackage.package_type != "onboarding")
            message = "Security deposit already paid. You can buy credit top-up packages."
        else:
            # Show only onboarding packages before deposit paid
            q = q.where(ServicePackage.package_type == "onboarding")
            message = "Security deposit is required before credit top-up packages are available."

        q = q.order_by(ServicePackage.display_order, ServicePackage.name)
        r = await self.db.execute(q)
        pkgs = r.scalars().all()

        balance = float(wallet.credit_balance) if wallet else 0.0
        threshold = float(wallet.low_balance_threshold or PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD) if wallet else float(PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD)
        is_low = wallet is not None and wallet.credit_balance < (wallet.low_balance_threshold or PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD)

        return {
            "security_deposit_status": deposit_status,
            "credit_wallet_balance": balance,
            "is_low_balance": is_low,
            "low_balance_threshold": threshold,
            "available_packages": [self._pkg_dict(p) for p in pkgs],
            "message": message,
        }

    # ═══════════════════════════════════════════════════════════════
    # PHASE 4 — PACKAGE PURCHASE
    # ═══════════════════════════════════════════════════════════════

    async def purchase_package(
        self, tenant_id: uuid.UUID, package_id: uuid.UUID, data: dict
    ) -> dict:
        pkg = await self._load_package(package_id)
        if not pkg.is_active:
            raise ServiceOSException("PACKAGE_INACTIVE",
                                     "This package is no longer available for purchase.")

        deposit = await self._get_deposit(tenant_id)
        deposit_paid = deposit is not None and deposit.status == "paid"

        # Visibility rules
        if pkg.package_type == "onboarding" and deposit_paid:
            raise ServiceOSException("PACKAGE_PURCHASE_NOT_ALLOWED",
                                     "Security deposit already paid. Purchase a credit top-up instead.")
        if pkg.package_type == "credit_topup" and not deposit_paid:
            raise ServiceOSException("PACKAGE_PURCHASE_NOT_ALLOWED",
                                     "Security deposit must be paid before purchasing credit top-up packages.")

        payment_status = "paid" if data.get("mark_paid") else "pending"
        payment_reference = data.get("payment_reference")

        now = utcnow()
        expires_at = None
        if pkg.validity_days and payment_status == "paid":
            expires_at = now + timedelta(days=pkg.validity_days)

        purchase = TenantPackagePurchase(
            tenant_id=tenant_id,
            package_id=package_id,
            package_type=pkg.package_type,
            package_price=pkg.package_price,
            security_deposit_amount=pkg.security_deposit_amount,
            credit_amount=pkg.included_credit_amount,
            commission_rate=pkg.commission_rate,
            storage_quota_gb=pkg.storage_quota_gb,
            payment_status=payment_status,
            payment_reference=payment_reference,
            purchased_at=now if payment_status == "paid" else None,
            expires_at=expires_at,
        )
        self.db.add(purchase)
        await self.db.flush()

        credit_added = Decimal("0.00")
        deposit_status_after = deposit.status if deposit else "unpaid"

        if payment_status == "paid":
            # If onboarding package — mark/update security deposit
            if pkg.package_type == "onboarding" and pkg.security_deposit_amount > 0:
                if deposit is None:
                    deposit = SecurityDeposit(
                        tenant_id=tenant_id,
                        required_amount=pkg.security_deposit_amount,
                        total_paid=pkg.security_deposit_amount,
                        status="paid",
                        paid_at=now,
                        package_purchase_id=purchase.id,
                        payment_reference=payment_reference,
                    )
                    self.db.add(deposit)
                else:
                    deposit.total_paid = pkg.security_deposit_amount
                    deposit.status = "paid"
                    deposit.paid_at = now
                    deposit.package_purchase_id = purchase.id
                    if payment_reference:
                        deposit.payment_reference = payment_reference
                await self.db.flush()
                deposit_status_after = "paid"

            # Add included credit — FINAL-L5-05J: routed through the
            # canonical UsageCreditService (tenant_billing/usage_credit_ledger)
            # instead of ledger.credit_wallet (TenantWallet/wallet_transactions).
            if pkg.included_credit_amount > 0:
                from app.engines.usage_credits.service import UsageCreditService
                uc_svc = UsageCreditService(
                    self.db, actor_id=self.actor_id, actor_role=self.actor_role,
                    request_id=self.request_id,
                )
                await uc_svc.grant_package_credit(
                    tenant_id=tenant_id, package_assignment_id=str(purchase.id),
                    activation_version=1, amount=pkg.included_credit_amount,
                    reason=f"Included credit from {pkg.package_type} package: {pkg.name}",
                )
                credit_added = pkg.included_credit_amount

            # Apply storage quota + commission rate to tenant limits/settings
            if pkg.storage_quota_gb is not None:
                await self._apply_storage_quota(tenant_id, pkg.storage_quota_gb)
            if pkg.commission_rate is not None:
                await self._apply_commission_rate(tenant_id, pkg.commission_rate)

            await self._pkg_audit(tenant_id, package_id, purchase.id, "package_purchased",
                                  new_value={"payment_status": "paid",
                                             "credit_added": float(credit_added)})

        wallet = await self._get_wallet(tenant_id)
        wallet_balance = float(wallet.credit_balance) if wallet else 0.0

        return {
            "package_purchase_id": str(purchase.id),
            "package_type": pkg.package_type,
            "payment_status": payment_status,
            "security_deposit_status": deposit_status_after,
            "credit_added": float(credit_added),
            "credit_wallet_balance": wallet_balance,
            "message": "Package purchased successfully." if payment_status == "paid"
                       else "Purchase recorded as pending. Credit not added until payment is confirmed.",
        }

    # ═══════════════════════════════════════════════════════════════
    # PHASE 5 — SECURITY DEPOSIT MANAGEMENT
    # ═══════════════════════════════════════════════════════════════

    async def get_security_deposit(self, tenant_id: uuid.UUID) -> dict:
        deposit = await self._get_deposit(tenant_id)
        if deposit is None:
            return {
                "tenant_id": str(tenant_id),
                "status": "not_initialized",
                "required_amount": 0,
                "paid_amount": 0,
                "paid_at": None,
                "message": "Security deposit not yet initialized for this tenant.",
            }
        return self._deposit_dict(deposit)

    async def admin_mark_deposit_paid(self, tenant_id: uuid.UUID, data: dict) -> dict:
        deposit = await self._get_deposit(tenant_id)
        if deposit is None:
            raise ServiceOSException("SECURITY_DEPOSIT_NOT_FOUND",
                                     "Security deposit record not found for this tenant.")
        if deposit.status == "paid":
            raise ServiceOSException("SECURITY_DEPOSIT_ALREADY_PAID",
                                     "Security deposit is already marked as paid.")

        amount = Decimal(str(data.get("amount", deposit.required_amount)))
        payment_ref = data.get("payment_reference")

        deposit.total_paid = amount
        deposit.status = "paid"
        deposit.paid_at = utcnow()
        if payment_ref:
            deposit.payment_reference = payment_ref

        await self._pkg_audit(tenant_id, None, None, "security_deposit_paid",
                              new_value={"status": "paid", "paid_amount": float(amount),
                                         "payment_reference": payment_ref},
                              reason=data.get("notes"))
        logger.info("deposit.marked_paid", tenant_id=str(tenant_id), amount=float(amount))
        return self._deposit_dict(deposit)

    async def admin_refund_deposit(self, tenant_id: uuid.UUID, data: dict) -> dict:
        deposit = await self._load_deposit(tenant_id)
        if deposit.status == "refunded":
            raise ServiceOSException("SECURITY_DEPOSIT_REFUND_FAILED",
                                     "Security deposit is already refunded.")
        old_status = deposit.status
        deposit.status = "refunded"
        deposit.refunded_at = utcnow()
        await self._pkg_audit(tenant_id, None, None, "security_deposit_refunded",
                              old_value={"status": old_status},
                              new_value={"status": "refunded"},
                              reason=data.get("reason"))
        return self._deposit_dict(deposit)

    async def admin_forfeit_deposit(self, tenant_id: uuid.UUID, data: dict) -> dict:
        deposit = await self._load_deposit(tenant_id)
        if deposit.status == "forfeited":
            raise ServiceOSException("SECURITY_DEPOSIT_FORFEIT_FAILED",
                                     "Security deposit is already forfeited.")
        old_status = deposit.status
        deposit.status = "forfeited"
        await self._pkg_audit(tenant_id, None, None, "security_deposit_forfeited",
                              old_value={"status": old_status},
                              new_value={"status": "forfeited"},
                              reason=data.get("reason"))
        return self._deposit_dict(deposit)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 6 — CREDIT WALLET + LEDGER
    # ═══════════════════════════════════════════════════════════════

    async def get_credit_wallet_detail(self, tenant_id: uuid.UUID) -> dict:
        wallet = await self._get_wallet(tenant_id)
        if wallet is None:
            # A newly activated tenant can legitimately have no legacy package wallet:
            # Home Services finance provisions usage credits separately. Returning a
            # zero balance keeps dashboard reads total and avoids turning that valid
            # state into a noisy 404 on every workspace visit.
            return {
                "tenant_id": str(tenant_id), "balance": 0.0, "reserved_balance": 0.0,
                "currency": "INR", "low_balance_threshold": float(PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD),
                "is_low_balance": True, "is_active": False, "lifetime_purchased": 0.0,
                "lifetime_consumed": 0.0, "last_transaction_at": None,
            }
        threshold = wallet.low_balance_threshold or PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD
        return {
            "tenant_id": str(tenant_id),
            "balance": float(wallet.credit_balance),
            "reserved_balance": float(wallet.reserved_balance),
            "currency": wallet.currency or "INR",
            "low_balance_threshold": float(threshold),
            "is_low_balance": wallet.credit_balance < threshold,
            "is_active": wallet.is_active,
            "lifetime_purchased": float(wallet.lifetime_purchased),
            "lifetime_consumed": float(wallet.lifetime_consumed),
            "last_transaction_at": wallet.last_transaction_at.isoformat() if wallet.last_transaction_at else None,
        }

    async def get_credit_ledger(
        self, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> dict:
        r = await self.db.execute(
            select(WalletTransaction)
            .where(WalletTransaction.tenant_id == tenant_id)
            .order_by(desc(WalletTransaction.created_at))
            .offset(offset)
            .limit(limit)
        )
        txns = r.scalars().all()
        return {
            "tenant_id": str(tenant_id),
            "items": [self._txn_dict(t) for t in txns],
            "total": len(txns),
            "limit": limit,
            "offset": offset,
        }

    async def admin_topup_wallet(self, tenant_id: uuid.UUID, data: dict) -> dict:
        amount = Decimal(str(data.get("amount", 0)))
        if amount <= 0:
            raise ServiceOSException("CREDIT_AMOUNT_INVALID",
                                     "Top-up amount must be greater than 0.")
        reason = data.get("reason", "")
        payment_ref = data.get("payment_reference")

        txn = await credit_wallet(
            db=self.db,
            tenant_id=tenant_id,
            amount=amount,
            txn_type="admin_topup",
            reference_id=payment_ref,
            reference_type="admin_topup",
            description=reason or "Admin credit top-up",
            actor_id=self.actor_id,
            idempotency_key=f"admin-topup-{tenant_id}-{payment_ref or uuid.uuid4().hex[:8]}",
        )
        await self.db.flush()
        await self._pkg_audit(tenant_id, None, None, "credit_topup",
                              new_value={"amount": float(amount),
                                         "balance_after": float(txn.balance_after),
                                         "payment_reference": payment_ref},
                              reason=reason)

        wallet = await self._get_wallet(tenant_id)
        low_alert = self._check_low_credit(wallet)
        return {
            "tenant_id": str(tenant_id),
            "amount_added": float(amount),
            "balance": float(wallet.credit_balance),
            "transaction_id": str(txn.id),
            "low_balance_alert": low_alert,
        }

    async def admin_adjust_wallet(self, tenant_id: uuid.UUID, data: dict) -> dict:
        entry_type = data.get("entry_type", "credit")
        amount = Decimal(str(data.get("amount", 0)))
        reason = data.get("reason", "").strip()
        if amount <= 0:
            raise ServiceOSException("CREDIT_AMOUNT_INVALID", "Adjustment amount must be > 0.")
        if not reason:
            raise ServiceOSException("CREDIT_ADJUSTMENT_REASON_REQUIRED",
                                     "A reason is required for wallet adjustment.")

        if entry_type == "credit":
            txn = await credit_wallet(
                db=self.db,
                tenant_id=tenant_id,
                amount=amount,
                txn_type="admin_adjustment",
                reference_id=None,
                reference_type="admin_adjustment",
                description=reason,
                actor_id=self.actor_id,
            )
        else:
            txn = await debit_wallet(
                db=self.db,
                tenant_id=tenant_id,
                amount=amount,
                txn_type="admin_adjustment",
                reference_id=None,
                reference_type="admin_adjustment",
                description=reason,
                actor_id=self.actor_id,
            )

        await self.db.flush()
        await self._pkg_audit(tenant_id, None, None, "credit_adjustment",
                              new_value={"entry_type": entry_type, "amount": float(amount)},
                              reason=reason)

        wallet = await self._get_wallet(tenant_id)
        low_alert = self._check_low_credit(wallet)
        return {
            "tenant_id": str(tenant_id),
            "entry_type": entry_type,
            "amount": float(amount),
            "balance": float(wallet.credit_balance),
            "transaction_id": str(txn.id),
            "low_balance_alert": low_alert,
        }

    # ═══════════════════════════════════════════════════════════════
    # PHASES 7+8 — COMMISSION CALCULATION + DEDUCTION
    # ═══════════════════════════════════════════════════════════════

    async def calculate_commission(self, job_id: str, tenant_id: uuid.UUID,
                                   job_value: Decimal,
                                   invoice_id: uuid.UUID | None = None,
                                   payment_id: uuid.UUID | None = None) -> dict:
        """Calculate commission amount. Does not deduct from wallet."""
        # Check if commission already exists
        existing = await self.db.execute(
            select(CommissionRecord).where(CommissionRecord.job_id == job_id)
        )
        record = existing.scalar_one_or_none()
        if record:
            return self._commission_dict(record)

        rate, purchase_id = await self._resolve_commission_rate(tenant_id)
        commission_amount = (job_value * rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Wallet balance snapshot
        wallet = await self._get_wallet(tenant_id)
        balance = wallet.credit_balance if wallet else Decimal("0.00")

        record = CommissionRecord(
            tenant_id=tenant_id,
            job_id=job_id,
            base_rate=rate,
            health_adjustment=Decimal("0.00"),
            effective_rate=rate,
            job_value=job_value,
            commission_amount=commission_amount,
            wallet_balance_before=balance,
            wallet_balance_after=balance,
            health_band_at_time="gold",
            invoice_id=invoice_id,
            payment_id=payment_id,
            package_purchase_id=purchase_id,
            calculation_base="total_amount",
            status="pending",
        )
        self.db.add(record)
        await self.db.flush()
        logger.info("commission.calculated", job_id=job_id, rate=float(rate),
                    amount=float(commission_amount))
        return self._commission_dict(record)

    async def deduct_commission(self, job_id: str, tenant_id: uuid.UUID) -> dict:
        """Deduct pending commission from credit wallet. Idempotent."""
        existing = await self.db.execute(
            select(CommissionRecord).where(CommissionRecord.job_id == job_id)
        )
        record = existing.scalar_one_or_none()
        if not record:
            raise ServiceOSException("COMMISSION_NOT_FOUND",
                                     f"No commission record found for job {job_id}.")
        if record.tenant_id != tenant_id:
            raise ServiceOSException("TENANT_ACCESS_DENIED",
                                     "Commission job does not belong to this tenant.")
        if record.status == "deducted":
            raise ServiceOSException("COMMISSION_ALREADY_DEDUCTED",
                                     "Commission has already been deducted for this job.")

        wallet = await self._get_wallet(tenant_id)
        if wallet is None:
            raise ServiceOSException("CREDIT_WALLET_NOT_FOUND",
                                     "Credit wallet not found for this tenant.")

        balance_before = wallet.credit_balance
        if wallet.credit_balance < record.commission_amount:
            record.status = "failed"
            record.failure_reason = "insufficient_credit"
            record.wallet_balance_before = balance_before
            await self.db.flush()
            await self._pkg_audit(tenant_id, None, None, "commission_failed",
                                  new_value={"job_id": job_id,
                                             "commission_amount": float(record.commission_amount),
                                             "balance": float(balance_before)})
            low_alert = self._check_low_credit(wallet)
            return {
                "job_id": job_id,
                "commission_id": str(record.id),
                "commission_rate": float(record.effective_rate),
                "commission_amount": float(record.commission_amount),
                "wallet_balance_before": float(balance_before),
                "wallet_balance_after": float(balance_before),
                "commission_status": "failed",
                "failure_reason": "insufficient_credit",
                "low_balance_alert": low_alert,
                "message": "Commission deduction failed: insufficient credit.",
            }

        txn = await debit_wallet(
            db=self.db,
            tenant_id=tenant_id,
            amount=record.commission_amount,
            txn_type="commission",
            reference_id=job_id,
            reference_type="job_commission",
            description=f"Commission deduction for job {job_id}",
            actor_id=self.actor_id,
            idempotency_key=f"commission-deduct-{record.id}",
        )
        await self.db.flush()

        wallet_after = await self._get_wallet(tenant_id)
        balance_after = wallet_after.credit_balance if wallet_after else balance_before - record.commission_amount

        record.status = "deducted"
        record.deducted_at = utcnow()
        record.wallet_balance_before = balance_before
        record.wallet_balance_after = balance_after
        record.wallet_ledger_entry_id = txn.id

        await self._pkg_audit(tenant_id, None, None, "commission_deducted",
                              new_value={"job_id": job_id,
                                         "commission_amount": float(record.commission_amount),
                                         "balance_after": float(balance_after)})

        low_alert = self._check_low_credit(wallet_after)
        logger.info("commission.deducted", job_id=job_id,
                    amount=float(record.commission_amount), balance_after=float(balance_after))
        return {
            "job_id": job_id,
            "commission_id": str(record.id),
            "commission_rate": float(record.effective_rate),
            "commission_amount": float(record.commission_amount),
            "wallet_balance_before": float(balance_before),
            "wallet_balance_after": float(balance_after),
            "commission_status": "deducted",
            "low_balance_alert": low_alert,
            "message": "Commission deducted successfully.",
        }

    async def list_commissions(self, tenant_id: uuid.UUID, status: str | None = None,
                               limit: int = 50, offset: int = 0) -> dict:
        q = select(CommissionRecord).where(CommissionRecord.tenant_id == tenant_id)
        if status:
            q = q.where(CommissionRecord.status == status)
        q = q.order_by(desc(CommissionRecord.created_at)).offset(offset).limit(limit)
        r = await self.db.execute(q)
        records = r.scalars().all()
        return {
            "tenant_id": str(tenant_id),
            "items": [self._commission_dict(c) for c in records],
            "total": len(records),
        }

    # ═══════════════════════════════════════════════════════════════
    # PHASE 11 — STORAGE QUOTA
    # ═══════════════════════════════════════════════════════════════

    async def get_storage_quota(self, tenant_id: uuid.UUID) -> dict:
        limits = await self._get_tenant_limits(tenant_id)
        if not limits:
            return {"tenant_id": str(tenant_id), "storage_quota_gb": None,
                    "storage_used_gb": 0, "storage_remaining_gb": None}

        quota_gb = float(limits.max_storage_gb)
        # Count used storage from media if media engine exists
        used_gb = await self._count_storage_used(tenant_id)
        remaining_gb = max(0.0, quota_gb - used_gb)
        return {
            "tenant_id": str(tenant_id),
            "storage_quota_gb": quota_gb,
            "storage_used_gb": round(used_gb, 3),
            "storage_remaining_gb": round(remaining_gb, 3),
        }

    async def get_tenant_purchases(self, tenant_id: uuid.UUID | None = None,
                                   limit: int = 50, offset: int = 0) -> dict:
        """Lists tenant package assignments (selection/purchase/approval lifecycle).

        Reads from tenant_package_assignments — the real, live table backing
        tenant package selection — not the unmigrated TenantPackagePurchase
        model (that table does not exist in the database; querying it 500s).
        """
        q = select(TenantPackageAssignment)
        if tenant_id:
            q = q.where(TenantPackageAssignment.tenant_id == tenant_id)
        q = q.order_by(desc(TenantPackageAssignment.created_at)).offset(offset).limit(limit)
        rows = (await self.db.scalars(q)).all()
        return {
            "tenant_id": str(tenant_id) if tenant_id else None,
            "items": [self._assignment_dict(a) for a in rows],
            "total": len(rows),
        }

    def _assignment_dict(self, a: "TenantPackageAssignment") -> dict:
        return {
            "purchase_id": str(a.id), "assignment_id": str(a.id),
            "tenant_id": str(a.tenant_id),
            "package_id": str(a.package_id) if a.package_id else None,
            "package_type": a.package_type, "status": a.status,
            "price_amount": float(a.price_amount),
            "security_deposit_amount": float(a.security_deposit_amount) if a.security_deposit_amount is not None else None,
            "included_spendable_credits": float(a.included_spendable_credits) if a.included_spendable_credits is not None else None,
            "selected_at": a.selected_at.isoformat() if a.selected_at else None,
            "paid_at": a.paid_at.isoformat() if a.paid_at else None,
            "approved_at": a.approved_at.isoformat() if a.approved_at else None,
            "activated_at": a.activated_at.isoformat() if a.activated_at else None,
            "starts_at": a.starts_at.isoformat() if a.starts_at else None,
            "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

    # ═══════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ═══════════════════════════════════════════════════════════════

    async def _load_package(self, package_id: uuid.UUID) -> ServicePackage:
        r = await self.db.execute(
            select(ServicePackage).where(
                ServicePackage.id == package_id,
                ServicePackage.deleted_at.is_(None),
            )
        )
        pkg = r.scalar_one_or_none()
        if not pkg:
            raise ServiceOSException("PACKAGE_NOT_FOUND", f"Package {package_id} not found.")
        return pkg

    async def _get_deposit(self, tenant_id: uuid.UUID) -> SecurityDeposit | None:
        r = await self.db.execute(
            select(SecurityDeposit).where(SecurityDeposit.tenant_id == tenant_id)
        )
        return r.scalar_one_or_none()

    async def _load_deposit(self, tenant_id: uuid.UUID) -> SecurityDeposit:
        dep = await self._get_deposit(tenant_id)
        if not dep:
            raise ServiceOSException("SECURITY_DEPOSIT_NOT_FOUND",
                                     "Security deposit not found for this tenant.")
        return dep

    async def _get_wallet(self, tenant_id: uuid.UUID) -> TenantWallet | None:
        r = await self.db.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
        )
        return r.scalar_one_or_none()

    async def _get_tenant_limits(self, tenant_id: uuid.UUID) -> TenantLimits | None:
        r = await self.db.execute(
            select(TenantLimits).where(TenantLimits.tenant_id == tenant_id)
        )
        return r.scalar_one_or_none()

    async def _resolve_commission_rate(
        self, tenant_id: uuid.UUID
    ) -> tuple[Decimal, uuid.UUID | None]:
        """Commission rate priority: active_purchase > tenant_settings > platform_default."""
        # MODULE-L5-32: this queried TenantPackagePurchase, whose backing
        # table (tenant_package_purchases) was never migrated -- every call
        # 500'd, so a per-package commission override could never actually
        # be honored; it always fell through to tenant settings/platform
        # default (or crashed). TenantPackageAssignment is the real, active
        # assignment; the commission rate itself lives on ServicePackage.
        r = await self.db.execute(
            select(TenantPackageAssignment, ServicePackage.commission_rate)
            .join(ServicePackage, ServicePackage.id == TenantPackageAssignment.package_id)
            .where(
                TenantPackageAssignment.tenant_id == tenant_id,
                TenantPackageAssignment.status == "active",
                ServicePackage.commission_rate.is_not(None),
            )
            .order_by(desc(TenantPackageAssignment.activated_at))
            .limit(1)
        )
        row = r.first()
        if row is not None:
            assignment, commission_rate = row
            if commission_rate is not None:
                return commission_rate, assignment.id

        # 2. Tenant operational settings
        r2 = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        settings = r2.scalar_one_or_none()
        if settings and settings.commission_rate:
            rate = Decimal(str(settings.commission_rate)) * Decimal("100")  # stored as fraction
            return rate, None

        # 3. Platform default
        return PLATFORM_DEFAULT_COMMISSION_RATE, None

    async def _apply_storage_quota(self, tenant_id: uuid.UUID, quota_gb: Decimal) -> None:
        # MODULE-L5-45: this only ever updated an existing TenantLimits row --
        # no tenant in the platform has one (tenant onboarding never creates
        # it), so this silently did nothing for every tenant, ever. Create
        # the row (with model defaults for every other limit) if missing.
        limits = await self._get_tenant_limits(tenant_id)
        if limits:
            limits.max_storage_gb = int(quota_gb)
        else:
            self.db.add(TenantLimits(tenant_id=tenant_id, max_storage_gb=int(quota_gb)))
        await self.db.flush()

    async def _apply_commission_rate(self, tenant_id: uuid.UUID, rate: Decimal) -> None:
        # MODULE-L5-45: same missing-row bug as _apply_storage_quota above --
        # no tenant has a TenantSettings row, so this always silently no-op'd.
        r = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        settings = r.scalar_one_or_none()
        rate_fraction = float(rate / Decimal("100"))
        if settings:
            settings.commission_rate = rate_fraction
        else:
            self.db.add(TenantSettings(tenant_id=tenant_id, commission_rate=rate_fraction))
        await self.db.flush()

    async def _count_storage_used(self, tenant_id: uuid.UUID) -> float:
        try:
            from app.engines.media.models import MediaFile
            from sqlalchemy import func
            r = await self.db.execute(
                select(func.coalesce(func.sum(MediaFile.size_bytes), 0))
                .where(MediaFile.tenant_id == tenant_id)
            )
            total_bytes = r.scalar_one() or 0
            return total_bytes / (1024 ** 3)
        except Exception:
            return 0.0

    def _check_low_credit(self, wallet: TenantWallet | None) -> bool:
        if wallet is None:
            return False
        threshold = wallet.low_balance_threshold or PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD
        return wallet.credit_balance < threshold

    # ═══════════════════════════════════════════════════════════════
    # P0 — PACKAGE FEATURES CRUD
    # ═══════════════════════════════════════════════════════════════

    async def list_package_features(self, package_id: uuid.UUID) -> dict:
        await self._load_package(package_id)
        r = await self.db.execute(
            select(PackageFeature)
            .where(PackageFeature.package_id == package_id,
                   PackageFeature.deleted_at.is_(None))
            .order_by(PackageFeature.display_order, PackageFeature.created_at)
        )
        rows = r.scalars().all()
        return {"features": [self._feature_dict(f) for f in rows], "total": len(rows)}

    async def create_package_feature(self, package_id: uuid.UUID, data: dict) -> dict:
        await self._load_package(package_id)
        label = (data.get("feature_label") or "").strip()
        if not label:
            raise ServiceOSException("VALIDATION_ERROR", "feature_label is required.")
        feat = PackageFeature(
            package_id=package_id,
            feature_key=data.get("feature_key") or None,
            feature_label=label,
            feature_description=data.get("feature_description") or None,
            feature_icon=data.get("feature_icon") or None,
            is_highlighted=bool(data.get("is_highlighted", False)),
            is_included=bool(data.get("is_included", True)),
            display_order=int(data.get("display_order", 0)),
            status=data.get("status", "active"),
        )
        self.db.add(feat)
        await self.db.flush()
        return self._feature_dict(feat)

    async def update_package_feature(self, package_id: uuid.UUID,
                                     feature_id: uuid.UUID, data: dict) -> dict:
        await self._load_package(package_id)
        feat = await self._load_feature(feature_id, package_id)
        if "feature_label" in data and data["feature_label"]:
            feat.feature_label = data["feature_label"].strip()
        for f in ("feature_key", "feature_description", "feature_icon"):
            if f in data:
                setattr(feat, f, data[f] or None)
        if "is_highlighted" in data:
            feat.is_highlighted = bool(data["is_highlighted"])
        if "is_included" in data:
            feat.is_included = bool(data["is_included"])
        if "display_order" in data:
            feat.display_order = int(data["display_order"])
        if "status" in data and data["status"]:
            feat.status = data["status"]
        await self.db.flush()
        return self._feature_dict(feat)

    async def delete_package_feature(self, package_id: uuid.UUID, feature_id: uuid.UUID) -> dict:
        await self._load_package(package_id)
        feat = await self._load_feature(feature_id, package_id)
        feat.deleted_at = utcnow()
        return {"feature_id": str(feature_id), "deleted": True}

    async def _load_feature(self, feature_id: uuid.UUID, package_id: uuid.UUID) -> PackageFeature:
        r = await self.db.execute(
            select(PackageFeature).where(
                PackageFeature.id == feature_id,
                PackageFeature.package_id == package_id,
                PackageFeature.deleted_at.is_(None),
            )
        )
        feat = r.scalar_one_or_none()
        if not feat:
            raise ServiceOSException("NOT_FOUND", f"Feature {feature_id} not found.")
        return feat

    # ═══════════════════════════════════════════════════════════════
    # P0 — PACKAGE LIMITS CRUD
    # ═══════════════════════════════════════════════════════════════

    async def list_package_limits(self, package_id: uuid.UUID) -> dict:
        await self._load_package(package_id)
        r = await self.db.execute(
            select(PackageLimit)
            .where(PackageLimit.package_id == package_id,
                   PackageLimit.deleted_at.is_(None))
            .order_by(PackageLimit.display_order, PackageLimit.created_at)
        )
        rows = r.scalars().all()
        return {"limits": [self._limit_dict(lim) for lim in rows], "total": len(rows)}

    async def create_package_limit(self, package_id: uuid.UUID, data: dict) -> dict:
        await self._load_package(package_id)
        key = (data.get("limit_key") or "").strip()
        label = (data.get("limit_label") or "").strip()
        if not key:
            raise ServiceOSException("VALIDATION_ERROR", "limit_key is required.")
        if not label:
            raise ServiceOSException("VALIDATION_ERROR", "limit_label is required.")
        is_unlimited = bool(data.get("is_unlimited", False))
        limit_value = None
        if not is_unlimited and data.get("limit_value") is not None:
            v = Decimal(str(data["limit_value"]))
            if v < 0:
                raise ServiceOSException("VALIDATION_ERROR", "limit_value cannot be negative.")
            limit_value = v
        lim = PackageLimit(
            package_id=package_id,
            limit_key=key,
            limit_label=label,
            limit_value=limit_value,
            limit_unit=data.get("limit_unit") or None,
            is_unlimited=is_unlimited,
            display_order=int(data.get("display_order", 0)),
            status=data.get("status", "active"),
        )
        self.db.add(lim)
        await self.db.flush()
        return self._limit_dict(lim)

    async def update_package_limit(self, package_id: uuid.UUID,
                                   limit_id: uuid.UUID, data: dict) -> dict:
        await self._load_package(package_id)
        lim = await self._load_limit(limit_id, package_id)
        if "limit_label" in data and data["limit_label"]:
            lim.limit_label = data["limit_label"].strip()
        if "limit_key" in data and data["limit_key"]:
            lim.limit_key = data["limit_key"].strip()
        if "limit_unit" in data:
            lim.limit_unit = data["limit_unit"] or None
        if "is_unlimited" in data:
            lim.is_unlimited = bool(data["is_unlimited"])
        if "limit_value" in data:
            lim.limit_value = Decimal(str(data["limit_value"])) if data["limit_value"] is not None else None
        if "display_order" in data:
            lim.display_order = int(data["display_order"])
        if "status" in data and data["status"]:
            lim.status = data["status"]
        await self.db.flush()
        return self._limit_dict(lim)

    async def delete_package_limit(self, package_id: uuid.UUID, limit_id: uuid.UUID) -> dict:
        await self._load_package(package_id)
        lim = await self._load_limit(limit_id, package_id)
        lim.deleted_at = utcnow()
        return {"limit_id": str(limit_id), "deleted": True}

    async def _load_limit(self, limit_id: uuid.UUID, package_id: uuid.UUID) -> PackageLimit:
        r = await self.db.execute(
            select(PackageLimit).where(
                PackageLimit.id == limit_id,
                PackageLimit.package_id == package_id,
                PackageLimit.deleted_at.is_(None),
            )
        )
        lim = r.scalar_one_or_none()
        if not lim:
            raise ServiceOSException("NOT_FOUND", f"Limit {limit_id} not found.")
        return lim

    # ═══════════════════════════════════════════════════════════════
    # P0 — PACKAGE WITH DETAILS + CLONE
    # ═══════════════════════════════════════════════════════════════

    async def get_package_with_details(self, package_id: uuid.UUID) -> dict:
        pkg = await self._load_package(package_id)
        feats_r = await self.db.execute(
            select(PackageFeature)
            .where(PackageFeature.package_id == package_id,
                   PackageFeature.deleted_at.is_(None))
            .order_by(PackageFeature.display_order)
        )
        lims_r = await self.db.execute(
            select(PackageLimit)
            .where(PackageLimit.package_id == package_id,
                   PackageLimit.deleted_at.is_(None))
            .order_by(PackageLimit.display_order)
        )
        features = [self._feature_dict(f) for f in feats_r.scalars().all()]
        limits = [self._limit_dict(l) for l in lims_r.scalars().all()]
        return self._pkg_dict(pkg, features=features, limits=limits)

    async def clone_package(self, package_id: uuid.UUID) -> dict:
        """Clone a package with all its features and limits."""
        pkg = await self._load_package(package_id)
        new_slug = f"{pkg.slug}-copy-{uuid.uuid4().hex[:5]}"
        cloned = ServicePackage(
            name=f"{pkg.name} (copy)",
            slug=new_slug,
            description=pkg.description,
            short_description=getattr(pkg, "short_description", None),
            package_type=pkg.package_type,
            plan_level=pkg.plan_level,
            package_price=pkg.package_price,
            security_deposit_amount=pkg.security_deposit_amount,
            included_credit_amount=pkg.included_credit_amount,
            storage_quota_gb=pkg.storage_quota_gb,
            commission_rate=pkg.commission_rate,
            validity_days=pkg.validity_days,
            trial_days=getattr(pkg, "trial_days", None),
            features=pkg.features or {},
            is_active=False,
            display_order=pkg.display_order,
            vertical_type=pkg.vertical_type,
            billing_cycle=pkg.billing_cycle,
            currency=pkg.currency,
            is_public_signup_visible=False,
            is_popular=getattr(pkg, "is_popular", False),
            is_featured=getattr(pkg, "is_featured", False),
            is_recommended=getattr(pkg, "is_recommended", False),
            badge_label=getattr(pkg, "badge_label", None),
            cta_label=getattr(pkg, "cta_label", None),
            terms_summary=getattr(pkg, "terms_summary", None),
            terms_content_json=getattr(pkg, "terms_content_json", None),
            bonus_credits=getattr(pkg, "bonus_credits", None),
            lead_credits=getattr(pkg, "lead_credits", None),
            setup_fee_amount=getattr(pkg, "setup_fee_amount", None),
            renewal_price_amount=getattr(pkg, "renewal_price_amount", None),
            refund_policy=getattr(pkg, "refund_policy", None),
            created_by=self.actor_id,
        )
        self.db.add(cloned)
        await self.db.flush()

        # Copy features
        feats_r = await self.db.execute(
            select(PackageFeature)
            .where(PackageFeature.package_id == package_id,
                   PackageFeature.deleted_at.is_(None))
        )
        for f in feats_r.scalars().all():
            self.db.add(PackageFeature(
                package_id=cloned.id,
                feature_key=f.feature_key,
                feature_label=f.feature_label,
                feature_description=f.feature_description,
                feature_icon=f.feature_icon,
                is_highlighted=f.is_highlighted,
                is_included=f.is_included,
                display_order=f.display_order,
                status=f.status,
            ))

        # Copy limits
        lims_r = await self.db.execute(
            select(PackageLimit)
            .where(PackageLimit.package_id == package_id,
                   PackageLimit.deleted_at.is_(None))
        )
        for l in lims_r.scalars().all():
            self.db.add(PackageLimit(
                package_id=cloned.id,
                limit_key=l.limit_key,
                limit_label=l.limit_label,
                limit_value=l.limit_value,
                limit_unit=l.limit_unit,
                is_unlimited=l.is_unlimited,
                display_order=l.display_order,
                status=l.status,
            ))

        await self.db.flush()
        await self._pkg_audit(None, cloned.id, None, "package_created",
                              new_value={"cloned_from": str(package_id)})
        return await self.get_package_with_details(cloned.id)

    async def _pkg_audit(
        self,
        tenant_id: uuid.UUID | None,
        package_id: uuid.UUID | None,
        purchase_id: uuid.UUID | None,
        action: str,
        old_value: dict | None = None,
        new_value: dict | None = None,
        reason: str | None = None,
    ) -> None:
        log = PackageAuditLog(
            tenant_id=tenant_id,
            package_id=package_id,
            package_purchase_id=purchase_id,
            actor_user_id=self.actor_id,
            actor_role=self.actor_role,
            action=action,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            request_id=(self.request_id if getattr(self, "request_id", None) not in (None, "—") else None),
        )
        self.db.add(log)

    def _audit_dict(self, a: "PackageAuditLog") -> dict:
        return {
            "id": str(a.id), "tenant_id": str(a.tenant_id) if a.tenant_id else None,
            "package_id": str(a.package_id) if a.package_id else None,
            "package_purchase_id": str(a.package_purchase_id) if a.package_purchase_id else None,
            "actor_user_id": str(a.actor_user_id) if a.actor_user_id else None,
            "actor_role": a.actor_role,
            "action": a.action, "action_type": a.action,
            "target_type": "package" if a.package_id else ("tenant_finance" if a.tenant_id else None),
            "target_id": str(a.package_id or a.tenant_id) if (a.package_id or a.tenant_id) else None,
            "old_value_json": a.old_value, "new_value_json": a.new_value,
            "reason": a.reason, "request_id": a.request_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

    async def list_package_audit(self, package_id: uuid.UUID | None = None,
                                  tenant_id: uuid.UUID | None = None,
                                  limit: int = 50) -> dict:
        q = select(PackageAuditLog)
        if package_id:
            q = q.where(PackageAuditLog.package_id == package_id)
        if tenant_id:
            q = q.where(PackageAuditLog.tenant_id == tenant_id)
        q = q.order_by(PackageAuditLog.created_at.desc()).limit(limit)
        rows = (await self.db.scalars(q)).all()
        return {"items": [self._audit_dict(a) for a in rows], "total": len(rows)}

    # ── Serializers ────────────────────────────────────────────────

    def _pkg_dict(self, p: ServicePackage, features: list | None = None, limits: list | None = None) -> dict:
        price_val = float(p.package_price)
        return {
            # ── identity ──────────────────────────────────────────────
            "id": str(p.id),
            "package_id": str(p.id),   # backward compat for tests
            "name": p.name,
            "slug": p.slug,
            # ── description ──────────────────────────────────────────
            "short_description": getattr(p, "short_description", None),
            "description": p.description,
            # ── type / status ─────────────────────────────────────────
            "package_type": p.package_type,
            "plan_level": p.plan_level,
            "is_active": p.is_active,
            # ── pricing ───────────────────────────────────────────────
            "price": price_val,                 # frontend-compatible alias
            "package_price": price_val,         # backward compat
            "currency": getattr(p, "currency", "INR") or "INR",
            "billing_cycle": p.billing_cycle,
            "validity_days": p.validity_days,
            "trial_days": getattr(p, "trial_days", None),
            "security_deposit_amount": float(p.security_deposit_amount),
            "included_credit_amount": float(p.included_credit_amount),
            "bonus_credits": float(p.bonus_credits) if getattr(p, "bonus_credits", None) is not None else None,
            "lead_credits": getattr(p, "lead_credits", None),
            "setup_fee_amount": float(p.setup_fee_amount) if getattr(p, "setup_fee_amount", None) is not None else None,
            "renewal_price_amount": float(p.renewal_price_amount) if getattr(p, "renewal_price_amount", None) is not None else None,
            "storage_quota_gb": float(p.storage_quota_gb) if p.storage_quota_gb is not None else None,
            "commission_rate": float(p.commission_rate) if p.commission_rate is not None else None,
            # ── signup display ────────────────────────────────────────
            "vertical_type": p.vertical_type,
            "is_public_signup_visible": getattr(p, "is_public_signup_visible", False),
            "is_popular": getattr(p, "is_popular", False),
            "is_featured": getattr(p, "is_featured", False),
            "is_recommended": getattr(p, "is_recommended", False),
            "badge_label": getattr(p, "badge_label", None),
            "cta_label": getattr(p, "cta_label", None),
            "display_order": p.display_order,
            # ── terms / refund ────────────────────────────────────────
            "terms_summary": getattr(p, "terms_summary", None),
            "terms_content_json": getattr(p, "terms_content_json", None),
            "refund_policy": getattr(p, "refund_policy", None),
            # ── legacy features JSONB ─────────────────────────────────
            "features": p.features or {},
            # ── child rows (populated by full-detail methods) ─────────
            "package_features": features if features is not None else [],
            "package_limits": limits if limits is not None else [],
            # ── timestamps ────────────────────────────────────────────
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }

    def _feature_dict(self, f: "PackageFeature") -> dict:
        return {
            "feature_id": str(f.id),
            "package_id": str(f.package_id),
            "feature_key": f.feature_key,
            "feature_label": f.feature_label,
            "feature_description": f.feature_description,
            "feature_icon": f.feature_icon,
            "is_highlighted": f.is_highlighted,
            "is_included": f.is_included,
            "display_order": f.display_order,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }

    def _limit_dict(self, lim: "PackageLimit") -> dict:
        return {
            "limit_id": str(lim.id),
            "package_id": str(lim.package_id),
            "limit_key": lim.limit_key,
            "limit_label": lim.limit_label,
            "limit_value": float(lim.limit_value) if lim.limit_value is not None else None,
            "limit_unit": lim.limit_unit,
            "is_unlimited": lim.is_unlimited,
            "display_order": lim.display_order,
            "status": lim.status,
            "created_at": lim.created_at.isoformat() if lim.created_at else None,
        }

    def _deposit_dict(self, d: SecurityDeposit) -> dict:
        return {
            "tenant_id": str(d.tenant_id),
            "required_amount": float(d.required_amount),
            "paid_amount": float(d.total_paid),
            "status": d.status,
            "paid_at": d.paid_at.isoformat() if d.paid_at else None,
            "refunded_at": d.refunded_at.isoformat() if d.refunded_at else None,
            "package_purchase_id": str(d.package_purchase_id) if d.package_purchase_id else None,
            "payment_reference": d.payment_reference,
        }

    def _txn_dict(self, t: WalletTransaction) -> dict:
        entry_type = "credit" if t.amount >= 0 else "debit"
        return {
            "id": str(t.id),
            "entry_type": entry_type,
            "source_type": t.txn_type,
            "amount": abs(float(t.amount)),
            "balance_before": float(t.balance_before),
            "balance_after": float(t.balance_after),
            "description": t.description,
            "reference_id": t.reference_id,
            "reference_type": t.reference_type,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

    def _purchase_dict(self, p: TenantPackagePurchase) -> dict:
        return {
            "purchase_id": str(p.id),
            "tenant_id": str(p.tenant_id),
            "package_id": str(p.package_id),
            "package_type": p.package_type,
            "package_price": float(p.package_price),
            "security_deposit_amount": float(p.security_deposit_amount),
            "credit_amount": float(p.credit_amount),
            "commission_rate": float(p.commission_rate) if p.commission_rate is not None else None,
            "storage_quota_gb": float(p.storage_quota_gb) if p.storage_quota_gb is not None else None,
            "payment_status": p.payment_status,
            "payment_reference": p.payment_reference,
            "purchased_at": p.purchased_at.isoformat() if p.purchased_at else None,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }

    def _commission_dict(self, c: CommissionRecord) -> dict:
        return {
            "commission_id": str(c.id),
            "tenant_id": str(c.tenant_id),
            "job_id": c.job_id,
            "commission_rate": float(c.effective_rate),
            "commission_amount": float(c.commission_amount),
            "job_value": float(c.job_value),
            "calculation_base": c.calculation_base,
            "status": c.status,
            "deducted_at": c.deducted_at.isoformat() if c.deducted_at else None,
            "failure_reason": c.failure_reason,
            "wallet_balance_before": float(c.wallet_balance_before),
            "wallet_balance_after": float(c.wallet_balance_after),
            "package_purchase_id": str(c.package_purchase_id) if c.package_purchase_id else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    # ═══════════════════════════════════════════════════════════════
    # P1 — PACKAGE ASSIGNMENT LIFECYCLE (starts after admin approval)
    # ═══════════════════════════════════════════════════════════════

    VALID_ASSIGNMENT_STATUSES = {
        "selected", "pending_review", "pending_payment",
        "paid_pending_approval", "active", "expired",
        "cancelled", "refunded", "rejected",
    }

    async def create_package_assignment(
        self,
        tenant_id: uuid.UUID,
        package_id: uuid.UUID,
        payment_reference: str | None = None,
        is_paid: bool = False,
        payment_authority: str = "unspecified",
    ) -> dict:
        """
        Record a tenant's package selection.  Called at signup (after payment).

        starts_at / expires_at remain NULL — they are set only when admin approves.
        Wallet credits are NOT added here.
        Security deposit is recorded but remains non-spendable.

        Slice 2F-22 — `payment_authority` makes the trust boundary for
        `is_paid=True` explicit at the SERVICE layer, so a router dependency is
        not the only thing standing between an untrusted caller and a fabricated
        paid state. Marking an assignment paid asserts money changed hands; only
        a caller that can actually prove it may do so:

          * "gateway_signature_verified" — public_registration, after
            `verify_payment_signature()` returned True.
          * "admin_attestation"          — admin_router, under P.PACKAGES_CREATE;
            a human admin recording an out-of-band payment on the tenant's behalf.
          * "tenant_unpaid_request"      — tenant self-service; MUST NOT be paid.

        Any caller passing is_paid=True without one of the two authoritative
        values fails closed. This is deliberately a hard failure rather than a
        silent downgrade to unpaid: a caller that believes it recorded a payment
        must not be left thinking it succeeded.
        """
        _PAID_AUTHORITIES = {"gateway_signature_verified", "admin_attestation"}
        if is_paid and payment_authority not in _PAID_AUTHORITIES:
            raise ServiceOSException(
                "PAYMENT_AUTHORITY_REQUIRED",
                "Cannot record a package assignment as paid without an "
                "authoritative payment source (verified gateway signature or "
                "admin attestation).")
        if not is_paid and payment_reference:
            # An unpaid selection carrying an external transaction reference is
            # an unverifiable claim; storing it would mislead the admin who
            # later approves the assignment.
            raise ServiceOSException(
                "PAYMENT_REFERENCE_WITHOUT_PAYMENT",
                "A payment reference cannot be recorded on an unpaid selection.")
        pkg = await self._load_package(package_id)
        if not pkg.is_active:
            raise ServiceOSException("PACKAGE_INACTIVE", "Package is not available.")

        # MODULE-L5-30: without this, a tenant clicking Purchase twice (or a
        # retried request) created a second pending assignment for the same
        # package with no guard at all — a customer_credits-style double-spend
        # shape (see MODULE-L5-28). One in-flight selection per tenant+package.
        existing = (await self.db.execute(
            select(TenantPackageAssignment).where(
                TenantPackageAssignment.tenant_id == tenant_id,
                TenantPackageAssignment.package_id == package_id,
                TenantPackageAssignment.status.in_(
                    ["selected", "pending_review", "pending_payment", "paid_pending_approval"]
                ),
            )
        )).scalars().first()
        if existing:
            raise ServiceOSException(
                "PACKAGE_ALREADY_PENDING",
                "You already have a pending selection for this package awaiting approval.")

        now = utcnow()
        status = "paid_pending_approval" if is_paid else "pending_review"

        assignment = TenantPackageAssignment(
            tenant_id=tenant_id,
            package_id=package_id,
            package_type=pkg.package_type,
            status=status,
            selected_at=now,
            paid_at=now if is_paid else None,
            # starts_at and expires_at remain NULL until admin approval
            starts_at=None,
            expires_at=None,
            validity_days=pkg.validity_days,
            billing_cycle=pkg.billing_cycle,
            price_amount=pkg.package_price,
            security_deposit_amount=pkg.security_deposit_amount if pkg.security_deposit_amount else None,
            included_spendable_credits=pkg.included_credit_amount if pkg.included_credit_amount else None,
            lead_credits=pkg.lead_credits,
            payment_reference_id=payment_reference,
        )
        self.db.add(assignment)
        await self.db.flush()

        await self._pkg_audit(
            tenant_id, package_id, None,
            "tenant.package_selected",
            new_value={
                "assignment_id": str(assignment.id),
                "status": status,
                "package_type": pkg.package_type,
                "price": float(pkg.package_price),
                "is_paid": is_paid,
            },
        )
        logger.info("package_assignment.created",
                    tenant_id=str(tenant_id), package_id=str(package_id),
                    status=status)
        return self._assignment_dict(assignment)

    async def activate_tenant_package_assignment(self, tenant_id: uuid.UUID) -> dict | None:
        """
        Called when admin approves a tenant.
        Finds the most recent selected/paid_pending_approval assignment and activates it.
        Sets starts_at = now, expires_at = starts_at + validity_days.
        Adds wallet credits if package includes them.
        Security deposit stays in deposit ledger (not wallet).
        """
        now = utcnow()

        # Find the best assignment to activate
        result = await self.db.execute(
            select(TenantPackageAssignment)
            .where(
                TenantPackageAssignment.tenant_id == tenant_id,
                TenantPackageAssignment.status.in_(
                    ["selected", "pending_review", "pending_payment", "paid_pending_approval"]
                ),
            )
            .order_by(
                # prefer paid > selected
                TenantPackageAssignment.paid_at.desc().nullslast(),
                TenantPackageAssignment.created_at.desc(),
            )
            .limit(1)
        )
        assignment: TenantPackageAssignment | None = result.scalar_one_or_none()
        if not assignment:
            return None  # no package to activate — not an error

        # Calculate expiry
        expires_at = None
        if assignment.validity_days:
            from datetime import timedelta
            expires_at = now + timedelta(days=assignment.validity_days)

        assignment.status      = "active"
        assignment.approved_at = now
        assignment.activated_at = now
        assignment.starts_at   = now
        assignment.expires_at  = expires_at
        await self.db.flush()

        # MODULE-L5-45: storage quota and commission rate were only ever
        # applied from the dead purchase_package()/TenantPackagePurchase path
        # (unreachable since MODULE-L5-30 repointed the purchase endpoints to
        # this assignment flow, and never live-reachable before that either
        # since that table was never migrated). This is the real, live
        # activation path and never called either helper -- every tenant
        # approved through it kept whatever quota/commission they already had
        # regardless of the package they actually bought. media/service.py's
        # own docstring assumes this already happens ("tenant_limits.max_storage_gb,
        # which the package engine writes on package approval").
        if assignment.package_id:
            pkg = await self._load_package(assignment.package_id)
            if pkg.storage_quota_gb is not None:
                await self._apply_storage_quota(tenant_id, pkg.storage_quota_gb)
            if pkg.commission_rate is not None:
                await self._apply_commission_rate(tenant_id, pkg.commission_rate)

        # Add spendable wallet credits if package includes them (ONLY after approval)
        credits_added = Decimal("0.00")
        if assignment.included_spendable_credits and assignment.included_spendable_credits > 0:
            await credit_wallet(
                db=self.db,
                tenant_id=tenant_id,
                amount=assignment.included_spendable_credits,
                txn_type="package_activation",
                reference_id=str(assignment.id),
                reference_type="tenant_package_assignment",
                description=f"Wallet credits activated after admin approval (pkg type: {assignment.package_type})",
                actor_id=self.actor_id,
                idempotency_key=f"pkg-assign-credit-{assignment.id}",
            )
            credits_added = assignment.included_spendable_credits

        await self._pkg_audit(
            tenant_id, assignment.package_id, None,
            "tenant.package_activated_after_approval",
            new_value={
                "assignment_id":  str(assignment.id),
                "status":         "active",
                "starts_at":      now.isoformat(),
                "expires_at":     expires_at.isoformat() if expires_at else None,
                "credits_added":  float(credits_added),
            },
        )
        logger.info("package_assignment.activated",
                    tenant_id=str(tenant_id), assignment_id=str(assignment.id),
                    credits_added=float(credits_added))
        return self._assignment_dict(assignment)

    async def reject_tenant_package_assignment(self, tenant_id: uuid.UUID, reason: str = "") -> dict | None:
        """
        Called when admin rejects a tenant.
        Package is never activated — marks assignment as rejected.
        starts_at / expires_at remain NULL.
        No credits are ever added.
        """
        result = await self.db.execute(
            select(TenantPackageAssignment)
            .where(
                TenantPackageAssignment.tenant_id == tenant_id,
                TenantPackageAssignment.status.in_(
                    ["selected", "pending_review", "pending_payment", "paid_pending_approval"]
                ),
            )
            .order_by(TenantPackageAssignment.created_at.desc())
            .limit(1)
        )
        assignment: TenantPackageAssignment | None = result.scalar_one_or_none()
        if not assignment:
            return None

        assignment.status = "rejected"
        await self.db.flush()

        await self._pkg_audit(
            tenant_id, assignment.package_id, None,
            "tenant.package_rejected_before_activation",
            new_value={"assignment_id": str(assignment.id), "reason": reason},
        )
        return self._assignment_dict(assignment)

    async def get_package_assignment_summary(self, tenant_id: uuid.UUID) -> dict:
        """
        Returns the current package assignment status for the tenant.
        Used by the provider-facing package summary endpoint.
        """
        result = await self.db.execute(
            select(TenantPackageAssignment)
            .where(
                TenantPackageAssignment.tenant_id == tenant_id,
            )
            .order_by(TenantPackageAssignment.created_at.desc())
            .limit(1)
        )
        assignment: TenantPackageAssignment | None = result.scalar_one_or_none()
        if not assignment:
            return {
                "has_package": False,
                "status": None,
                "package_name": None,
                "starts_at": None,
                "expires_at": None,
                "message": "No package selected.",
            }

        # Load package name
        pkg_name = None
        if assignment.package_id:
            pkg_result = await self.db.execute(
                select(ServicePackage).where(ServicePackage.id == assignment.package_id)
            )
            pkg = pkg_result.scalar_one_or_none()
            if pkg:
                pkg_name = pkg.name

        status = assignment.status
        if status in ("selected", "pending_review", "pending_payment", "paid_pending_approval"):
            message = "Your package will start after admin approval."
        elif status == "active":
            message = "Your package is active."
        elif status == "expired":
            message = "Your package has expired. Please renew."
        elif status == "rejected":
            message = "Package was not activated. Please contact support."
        elif status == "cancelled":
            message = "Package was cancelled."
        else:
            message = f"Package status: {status}."

        return {
            "has_package":   True,
            "assignment_id": str(assignment.id),
            "package_id":    str(assignment.package_id) if assignment.package_id else None,
            "package_name":  pkg_name,
            "package_type":  assignment.package_type,
            "status":        status,
            "selected_at":   assignment.selected_at.isoformat()  if assignment.selected_at  else None,
            "paid_at":       assignment.paid_at.isoformat()       if assignment.paid_at       else None,
            "approved_at":   assignment.approved_at.isoformat()   if assignment.approved_at   else None,
            "activated_at":  assignment.activated_at.isoformat()  if assignment.activated_at  else None,
            "starts_at":     assignment.starts_at.isoformat()     if assignment.starts_at     else None,
            "expires_at":    assignment.expires_at.isoformat()    if assignment.expires_at    else None,
            "validity_days": assignment.validity_days,
            "billing_cycle": assignment.billing_cycle,
            "price_amount":  float(assignment.price_amount),
            "included_credits": float(assignment.included_spendable_credits) if assignment.included_spendable_credits else 0,
            "lead_credits":  assignment.lead_credits,
            "message":       message,
        }

    def _assignment_dict(self, a: TenantPackageAssignment) -> dict:
        return {
            "assignment_id":            str(a.id),
            "tenant_id":                str(a.tenant_id),
            "package_id":               str(a.package_id) if a.package_id else None,
            "package_type":             a.package_type,
            "status":                   a.status,
            "selected_at":              a.selected_at.isoformat()  if a.selected_at  else None,
            "paid_at":                  a.paid_at.isoformat()       if a.paid_at       else None,
            "approved_at":              a.approved_at.isoformat()   if a.approved_at   else None,
            "activated_at":             a.activated_at.isoformat()  if a.activated_at  else None,
            "starts_at":                a.starts_at.isoformat()     if a.starts_at     else None,
            "expires_at":               a.expires_at.isoformat()    if a.expires_at    else None,
            "validity_days":            a.validity_days,
            "billing_cycle":            a.billing_cycle,
            "price_amount":             float(a.price_amount),
            "security_deposit_amount":  float(a.security_deposit_amount) if a.security_deposit_amount else 0,
            "included_spendable_credits": float(a.included_spendable_credits) if a.included_spendable_credits else 0,
            "lead_credits":             a.lead_credits,
            "payment_reference_id":     a.payment_reference_id,
            "created_at":               a.created_at.isoformat() if a.created_at else None,
        }
