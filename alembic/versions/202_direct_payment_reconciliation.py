"""TENANT-HS-DIRECT-PAYMENTS-01: direct-payment declaration + reconciliation fields.

Home Services customers pay the provider business DIRECTLY. ServiceOS never
collects, holds, settles or pays out that money -- it only records the
provider's declaration and the customer's confirmation of it.

The canonical row for that already exists: ServicePaymentRecord
(service_payment_records, Sprint 23). It carried enough for "provider says
they collected X" + a single customer_confirmed boolean, but NOT the
reconciliation facts the Direct Payments workflow needs:

  * the backend-resolved EXPECTED amount (so a declared/expected mismatch is
    a first-class, separately-stored fact rather than an unrecoverable
    overwrite),
  * provider reference id / note / evidence type,
  * declaration versioning + correction reason (edits before customer
    confirmation must preserve the prior version -- prior versions
    themselves are written to financial_events, not a shadow table),
  * what the CUSTOMER actually reported (amount/method/action) when they
    disagree,
  * the linked complaint id for a payment dispute (Complaints & Resolution
    Center is the canonical dispute system -- no parallel dispute table),
  * reminder throttle state.

No new payment table is created and no payout/settlement/wallet concept is
introduced by this migration.

Also seeds the notification template for the customer confirmation reminder
so "Send confirmation reminder" fires a REAL notification (the notification
service skips delivery when no template row matches).

Revision ID: 202
Revises: 201
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "202"
down_revision = "201"
branch_labels = None
depends_on = None

_COLS = [
    ("expected_amount",              sa.Numeric(14, 2), True,  None),
    ("payment_reference_id",          sa.String(120),    True,  None),
    ("declaration_note",              sa.Text(),         True,  None),
    ("declaration_version",           sa.Integer(),      False, "1"),
    ("correction_reason",             sa.Text(),         True,  None),
    ("amount_difference_reason",      sa.Text(),         True,  None),
    ("received_at",                   sa.DateTime(timezone=True), True, None),
    ("reconciliation_status",         sa.String(40),     True,  None),
    ("customer_reported_amount",      sa.Numeric(14, 2), True,  None),
    ("customer_reported_method",      sa.String(40),     True,  None),
    ("customer_confirmation_action",  sa.String(40),     True,  None),
    ("customer_confirmation_note",    sa.Text(),         True,  None),
    ("dispute_complaint_id",          postgresql.UUID(as_uuid=True), True, None),
    ("last_reminder_at",              sa.DateTime(timezone=True), True, None),
    ("reminder_count",                sa.Integer(),      False, "0"),
    ("evidence_media_id",             postgresql.UUID(as_uuid=True), True, None),
    ("evidence_type",                 sa.String(40),     True,  None),
]

_TEMPLATES = [
    (
        "payment.confirmation_requested.in_app",
        "Direct payment — confirmation requested",
        "in_app",
        "Please confirm the payment for {{job_number}}",
        "{{provider_business}} has recorded a direct payment of {{currency}} {{declared_amount}} "
        "({{method}}) for {{job_number}}. Please confirm the amount you paid, or report a "
        "different amount. ServiceOS does not collect this money.",
        "Confirm payment",
        "/bookings/{{booking_id}}/payment-confirmation",
    ),
    (
        "payment.mismatch_reported.in_app",
        "Direct payment — mismatch reported",
        "in_app",
        "Payment amount mismatch on {{job_number}}",
        "The customer reported a different direct payment for {{job_number}}. "
        "Declared: {{currency}} {{declared_amount}}. Reported: {{currency}} {{reported_amount}}. "
        "Review and correct the declaration, or open a payment dispute.",
        "Review payment",
        "/home-services/direct-payments?payment_id={{payment_id}}",
    ),
    (
        "payment.confirmed_by_customer.in_app",
        "Direct payment — confirmed by customer",
        "in_app",
        "Payment confirmed for {{job_number}}",
        "The customer confirmed the direct payment of {{currency}} {{declared_amount}} for "
        "{{job_number}}. The record is reconciled. No settlement or payout is created by "
        "ServiceOS.",
        "View record",
        "/home-services/direct-payments?payment_id={{payment_id}}",
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        r[0] for r in conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'service_payment_records'"
        ))
    }
    for name, type_, nullable, server_default in _COLS:
        if name in existing:
            continue
        op.add_column(
            "service_payment_records",
            sa.Column(name, type_, nullable=True, server_default=server_default),
        )
        if not nullable:
            op.execute(
                f"UPDATE service_payment_records SET {name} = {server_default} "
                f"WHERE {name} IS NULL"
            )
            op.alter_column("service_payment_records", name, nullable=False)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_spr_reconciliation_status "
        "ON service_payment_records (reconciliation_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_spr_dispute_complaint_id "
        "ON service_payment_records (dispute_complaint_id)"
    )

    for key, name, channel, subject, body, label, url in _TEMPLATES:
        conn.execute(
            sa.text(
                "INSERT INTO notif_event_templates "
                "(id, template_key, template_name, channel, subject_template, "
                " body_template, action_label_template, action_url_template, "
                " is_active, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :k, :n, :c, :s, :b, :l, :u, true, now(), now()) "
                "ON CONFLICT (template_key) DO NOTHING"
            ),
            {"k": key, "n": name, "c": channel, "s": subject, "b": body, "l": label, "u": url},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for key, *_ in _TEMPLATES:
        conn.execute(
            sa.text("DELETE FROM notif_event_templates WHERE template_key = :k"), {"k": key}
        )
    op.execute("DROP INDEX IF EXISTS ix_spr_dispute_complaint_id")
    op.execute("DROP INDEX IF EXISTS ix_spr_reconciliation_status")
    for name, *_ in _COLS:
        op.execute(f"ALTER TABLE service_payment_records DROP COLUMN IF EXISTS {name}")
