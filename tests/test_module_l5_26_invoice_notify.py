"""MODULE-L5-26 — issuing an invoice notifies the customer.

issue_invoice transitioned the invoice to 'issued' and synced the job, but never
told the customer — so the customer had no idea an amount was owed until they
happened to open the booking. issue_invoice now raises an "Your invoice is ready"
in-app notification to the customer with the amount due and a link to the invoice.
"""
from __future__ import annotations

import inspect
import uuid

import pytest


def test_issue_invoice_notifies_customer_in_source():
    from app.engines.invoice_payment import invoice_service
    src = inspect.getsource(invoice_service.ServiceInvoiceService.issue_invoice)
    assert "InAppNotification" in src
    assert "invoice.issued" in src
    assert "/customer/invoices/" in src


class TestInvoiceIssueNotifyLive:
    @pytest.mark.asyncio
    async def test_issuing_a_draft_invoice_notifies_the_customer(self):
        import asyncpg
        from sqlalchemy import text
        from app.database import get_session_factory, init_db
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService

        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            tmpl = await c.fetchrow(
                "SELECT category_id, offering_id, booking_id, job_id, tenant_id, customer_id "
                "FROM service_invoices WHERE customer_id IS NOT NULL LIMIT 1")
            if not tmpl:
                pytest.skip("no invoice template row to clone")
            iid = uuid.uuid4()
            await c.execute(
                """INSERT INTO service_invoices
                   (id,invoice_number,booking_id,job_id,tenant_id,customer_id,category_id,offering_id,
                    status,currency,subtotal_amount,labour_amount,parts_amount,service_amount,
                    discount_amount,tax_amount,total_amount,customer_payable_amount,payment_mode,
                    payment_status,commission_status,invoice_source,platform_fee_amount,created_at,updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'draft','INR',500,500,0,0,0,90,590,590,'onsite',
                    'pending','pending','manual',0,now(),now())""",
                iid, f"INV-L5T-{uuid.uuid4().hex[:6]}", tmpl["booking_id"], tmpl["job_id"],
                tmpl["tenant_id"], tmpl["customer_id"], tmpl["category_id"], tmpl["offering_id"])
            before = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='invoice.issued'", tmpl["customer_id"])
        finally:
            await c.close()

        await init_db()
        async with get_session_factory()() as db:
            await ServiceInvoiceService().issue_invoice(
                db, str(iid), str(tmpl["tenant_id"]), str(tmpl["customer_id"]), "rid")

        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            after = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='invoice.issued'", tmpl["customer_id"])
            action = await c.fetchval(
                "SELECT action_url FROM in_app_notifications WHERE source_record_id=$1 "
                "AND notification_type='invoice.issued'", iid)
        finally:
            await c.close()
        assert after == before + 1, "issuing an invoice did not notify the customer"
        assert action == f"/customer/invoices/{iid}"
