"""TENANT-DOCUMENTS-WORKSPACE-01: post-activation Documents & Verification page.

Reuses the canonical TenantDocument model/table (migration 189) and the
document_requirements resolver end to end -- no new document table, no new
verification lifecycle. Two additions to the existing table:

  * staff_member_id (nullable) -- lets a TenantDocument row scope to a
    specific technician instead of the whole business, so Technician
    Documents reuses the exact same model/versioning/review pipeline rather
    than a parallel table.
  * reviewed_by / review_notes -- the admin verify endpoint set
    doc.verified_at but never recorded WHO reviewed a document (verified_by
    existed but was never actually written by the endpoint -- a real gap,
    fixed alongside this migration). review_notes covers the
    changes_requested case where rejection_reason alone reads oddly.

Also seeds notification templates for the document review lifecycle
(submitted/verified/changes_requested/rejected/expiring) -- without a
template row NotificationService silently drops delivery, same pattern as
migration 202.

Revision ID: 203
Revises: 202
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "203"
down_revision = "202"
branch_labels = None
depends_on = None

_TEMPLATES = [
    (
        "document.submitted.in_app",
        "Document submitted for review",
        "in_app",
        "Document submitted: {{document_label}}",
        "{{tenant_name}} submitted {{document_label}} for verification.",
        "Review document",
        "/admin/tenants/{{tenant_id}}/documents",
    ),
    (
        "document.verified.in_app",
        "Document verified",
        "in_app",
        "{{document_label}} verified",
        "Your {{document_label}} has been verified and is now active.",
        "View document",
        "/documents?tab=business",
    ),
    (
        "document.changes_requested.in_app",
        "Document changes requested",
        "in_app",
        "Changes requested on {{document_label}}",
        "ServiceOS requested changes on {{document_label}}: {{reason}}",
        "Upload correction",
        "/documents?tab=requests",
    ),
    (
        "document.rejected.in_app",
        "Document rejected",
        "in_app",
        "{{document_label}} rejected",
        "Your {{document_label}} was rejected: {{reason}}",
        "Upload replacement",
        "/documents?tab=business",
    ),
    (
        "document.expiring.in_app",
        "Document expiring soon",
        "in_app",
        "{{document_label}} expires soon",
        "{{document_label}} expires on {{expiry_date}}. Upload a replacement before it expires.",
        "Upload replacement",
        "/documents?tab=expiry",
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        r[0] for r in conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'tenant_documents'"
        ))
    }
    if "staff_member_id" not in existing:
        op.add_column("tenant_documents", sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=True))
    if "reviewed_by" not in existing:
        op.add_column("tenant_documents", sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True))
    if "review_notes" not in existing:
        op.add_column("tenant_documents", sa.Column("review_notes", sa.Text(), nullable=True))

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenant_docs_staff ON tenant_documents (tenant_id, staff_member_id, doc_type, is_current)"
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
        conn.execute(sa.text("DELETE FROM notif_event_templates WHERE template_key = :k"), {"k": key})
    op.execute("DROP INDEX IF EXISTS ix_tenant_docs_staff")
    op.execute("ALTER TABLE tenant_documents DROP COLUMN IF EXISTS review_notes")
    op.execute("ALTER TABLE tenant_documents DROP COLUMN IF EXISTS reviewed_by")
    op.execute("ALTER TABLE tenant_documents DROP COLUMN IF EXISTS staff_member_id")
