"""Backfill canonical invoices for genuine completed jobs that predate them.

Only jobs whose tenant still exists and whose canonical completion_data is
present are eligible.  Legacy amounts that do not equal the immutable invoice
payable remain pending for admin reconciliation; the script never fabricates a
customer confirmation or a direct-payment record.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import exists, select

from app.database import get_session_factory, init_db
from app.engines.final_records.models import ServiceJob
from app.engines.invoice_payment.constants import (
    FEV_PAYMENT_RECORDED,
    INV_PAYMENT_COLLECTED,
)
from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
from app.engines.invoice_payment.models import ServiceInvoice
from app.engines.tenant_engine.models import Tenant


def _completed_at(data: dict) -> datetime | None:
    value = data.get("completed_at")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


async def run() -> dict[str, int]:
    await init_db()
    factory = get_session_factory()
    stats = {"created": 0, "collected": 0, "reconciliation_required": 0}
    async with factory() as db:
        jobs = (await db.execute(
            select(ServiceJob)
            .join(Tenant, Tenant.id == ServiceJob.tenant_id)
            .where(
                ServiceJob.status == "completed",
                ServiceJob.completion_data.is_not(None),
                ~exists().where(
                    ServiceInvoice.job_id == ServiceJob.id,
                    ServiceInvoice.status != "cancelled",
                ),
            )
            .order_by(ServiceJob.created_at)
        )).scalars().all()

        service = ServiceInvoiceService()
        for job in jobs:
            data = dict(job.completion_data or {})
            actor = data.get("completed_by_staff_id") or str(uuid.UUID(int=0))
            inv = await service.ensure_issued_for_job(
                db, str(job.id), str(job.tenant_id), str(actor),
                request_id="completed-job-invoice-backfill", notify_customer=False,
            )
            collected = Decimal(str(data.get("collected_amount") or 0))
            payable = Decimal(str(inv.customer_payable_amount or 0))
            legacy_mode = str(data.get("payment_mode") or "onsite")
            inv.payment_mode = legacy_mode if len(legacy_mode) <= 30 else "onsite_other"
            if collected > 0 and abs(collected - payable) <= Decimal("0.01"):
                inv.status = INV_PAYMENT_COLLECTED
                inv.payment_status = "collected"
                inv.paid_at = _completed_at(data)
                await service._log_event(
                    db, inv, FEV_PAYMENT_RECORDED, "system", None,
                    new_value={
                        "backfilled": True,
                        "provider_declared_amount": str(collected),
                        "customer_confirmation": "not_available_in_legacy_flow",
                    },
                    request_id="completed-job-invoice-backfill",
                )
                stats["collected"] += 1
            else:
                inv.notes = (
                    "Backfilled from a completed job. Legacy collected amount "
                    f"{collected} does not match invoice payable {payable}; admin "
                    "reconciliation is required."
                )
                stats["reconciliation_required"] += 1
            stats["created"] += 1
        await db.commit()
    return stats


if __name__ == "__main__":
    print(asyncio.run(run()))
