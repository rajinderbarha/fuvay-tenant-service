"""Phase Y -- seed technician-audience knowledge-base articles into the
EXISTING canonical `support_knowledge_articles` table (app/engines/support).
Confirmed by audit: this is a real, admin-managed KB model with a working
GET /v1/tenant/support/knowledge search/list endpoint already reachable by
the "technician" role -- not a stub, and never a second help-content engine.
Without real published rows scoped to role_keys=["technician"], the mobile
Help & Support screen's Quick Help / Recommended articles would always be
empty for a technician even though the underlying system is fully real.

Revision ID: 218
Revises: 217
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "218"
down_revision = "217"
branch_labels = None
depends_on = None

_articles_table = sa.table(
    "support_knowledge_articles",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("slug", sa.String),
    sa.column("title", sa.String),
    sa.column("summary", sa.Text),
    sa.column("body", sa.Text),
    sa.column("product_area", sa.String),
    sa.column("keywords", postgresql.JSONB),
    sa.column("vertical_keys", postgresql.JSONB),
    sa.column("role_keys", postgresql.JSONB),
    sa.column("is_featured", sa.Boolean),
    sa.column("is_published", sa.Boolean),
    sa.column("policy_version", sa.String),
)

# (slug, title, summary, body, product_area, keywords, featured)
_ARTICLES = [
    ("tech-sign-in-mfa", "Signing in and two-step verification",
     "How to sign in, set up an authenticator app, and what trusted devices do.",
     "Sign in with your registered mobile number or email and password. If your business requires two-step "
     "verification, you'll be asked for a 6-digit code from your authenticator app after your password. "
     "Marking a device as trusted may reduce how often you're asked for a code on that device, but it never "
     "changes what you're allowed to do in the app.",
     "account_security", ["login", "mfa", "password", "trusted device", "sign in"], True),
    ("tech-password-sessions", "Changing your password and managing sessions",
     "Update your password and see which devices are signed in to your account.",
     "You can change your password from Profile > Security. Changing your password signs out every other "
     "device except the one you're using. You can also view all signed-in devices and sign any of them out "
     "individually from Active Sessions.",
     "account_security", ["password", "sessions", "security", "sign out"], False),
    ("tech-documents-required", "Why documents are required and how verification works",
     "What documents your business needs from you and what each status means.",
     "Your business may require identity proof, address proof or a skill certificate before you can be "
     "assigned certain jobs. Upload a clear photo or PDF from Profile > Documents. Your business reviews and "
     "verifies each document -- you cannot verify your own documents. If a document is rejected or needs "
     "changes, you'll see the reason and can upload a corrected version.",
     "team_access", ["documents", "verification", "upload", "certificate"], True),
    ("tech-view-accept-jobs", "Viewing and accepting assigned jobs",
     "How assigned work appears and what each job status means.",
     "New jobs assigned to you appear on the Jobs tab and trigger a notification. Job status moves through "
     "the real workflow stages as you make progress -- you don't need to manually 'accept' most jobs, but "
     "your business may require an on-the-way confirmation before you start.",
     "bookings_jobs", ["jobs", "assignment", "accept", "status"], True),
    ("tech-creating-estimate", "Creating an estimate for a customer",
     "How to build an estimate during inspection and what happens after you send it.",
     "During inspection, add line items with quantities and prices to build an estimate. Once sent, the "
     "customer reviews and approves or requests changes -- you'll be notified either way. You cannot mark "
     "your own estimate as approved.",
     "bookings_jobs", ["estimate", "quote", "pricing", "inspection"], False),
    ("tech-direct-payment", "Recording a direct payment confirmation",
     "How to record that a customer paid you directly for a job.",
     "For jobs where the customer pays you directly, record the payment details after completing the work. "
     "The customer confirms the amount on their side -- if the amounts don't match, it's flagged for review "
     "rather than silently accepted.",
     "bookings_jobs", ["payment", "direct payment", "invoice", "completion"], False),
    ("tech-schedule-leave", "Managing your schedule and requesting time off",
     "How your working hours, blocked time and leave requests work.",
     "Your recurring working hours are set by your business. You can add ad-hoc blocked time for short "
     "periods, and submit a time-off request for longer absences. Your business approves or rejects time-off "
     "requests -- you can never approve your own.",
     "bookings_jobs", ["schedule", "leave", "time off", "availability", "blocked time"], True),
    ("tech-photo-upload-failed", "What to do if a photo upload fails",
     "Common causes for a failed job-evidence upload and how to retry safely.",
     "Photo uploads usually fail due to a weak or interrupted connection. Check you have a stable connection "
     "and retry -- the app will not silently discard your evidence. If it keeps failing, use Report a "
     "technical problem so we can see safe diagnostics for your device and connection.",
     "bookings_jobs", ["photo", "upload", "evidence", "offline", "troubleshooting"], False),
]


def upgrade() -> None:
    now = sa.text("now()")
    op.bulk_insert(_articles_table, [
        {
            "id": uuid.uuid4(), "slug": slug, "title": title, "summary": summary, "body": body,
            "product_area": area, "keywords": keywords, "vertical_keys": ["home_services"],
            "role_keys": ["technician", "staff"],
            "is_featured": featured, "is_published": True, "policy_version": "HELP_2026_01",
        }
        for slug, title, summary, body, area, keywords, featured in _ARTICLES
    ])
    op.execute(
        "UPDATE support_knowledge_articles SET created_at = now(), updated_at = now() "
        "WHERE slug IN (" + ",".join(f"'{a[0]}'" for a in _ARTICLES) + ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM support_knowledge_articles WHERE slug IN (" +
        ",".join(f"'{a[0]}'" for a in _ARTICLES) + ")"
    )
