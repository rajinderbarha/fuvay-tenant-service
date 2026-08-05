"""TENANT-SUPPORT-01: tenant↔ServiceOS platform support engine.

Audited first: there was NO support/ticket engine anywhere in the codebase.
app/engines/complaints is the CUSTOMER complaint system (customer disputes a
service job) and is deliberately NOT reused — different actors, lifecycle,
SLA and remedies. Tables here are new and separate.

Creates:
  support_tickets, support_ticket_messages, support_ticket_events,
  support_ticket_attachments, support_knowledge_articles,
  support_article_feedback, support_announcements,
  support_announcement_acks, support_platform_incidents,
  support_status_heartbeats

Also seeds the notif_event_templates rows for the nine support notification
events registered in event_registry.py — without a template row
NotificationService silently drops delivery (same pattern as 202/203/206) —
and seeds the real published knowledge-base content (the KB is
admin-manageable data, never a hardcoded frontend array).

Revision ID: 207
Revises: 206
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "207"
down_revision = "206"
branch_labels = None
depends_on = None

UUIDT = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def _ts(name, nullable=True, default=None):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable, server_default=default)


_TEMPLATES = [
    ("support.request.submitted.in_app", "Support Request Submitted (In-App)",
     "Support request {{ticket_number}} received",
     "We have received your support request \"{{subject}}\". First response is due by {{first_response_due}}.",
     "View request"),
    ("support.request.replied.in_app", "ServiceOS Replied (In-App)",
     "ServiceOS replied to {{ticket_number}}",
     "The ServiceOS support team replied to your request \"{{subject}}\".",
     "Read reply"),
    ("support.request.info_requested.in_app", "Information Requested (In-App)",
     "{{ticket_number}} needs your information",
     "ServiceOS support needs more information to continue with \"{{subject}}\".",
     "Reply now"),
    ("support.request.priority_changed.in_app", "Priority Changed (In-App)",
     "Priority updated on {{ticket_number}}",
     "Priority is now {{priority}}. Reason: {{reason}}",
     "View request"),
    ("support.request.sla_breached.in_app", "Support SLA Breached (In-App)",
     "SLA breached on {{ticket_number}}",
     "The {{sla_kind}} target for \"{{subject}}\" has been breached.",
     "View request"),
    ("support.request.resolved.in_app", "Support Request Resolved (In-App)",
     "{{ticket_number}} resolved",
     "Your request \"{{subject}}\" was resolved. {{resolution_summary}}",
     "View resolution"),
    ("support.request.reopened.in_app", "Support Request Reopened (In-App)",
     "{{ticket_number}} reopened",
     "The tenant reopened \"{{subject}}\".",
     "View request"),
    ("support.incident.critical_reported.in_app", "Critical Incident Reported (In-App)",
     "CRITICAL: {{ticket_number}} — {{subject}}",
     "A critical incident was reported by {{tenant_name}}: {{critical_impact}}.",
     "Open incident"),
    ("support.announcement.published.in_app", "Platform Announcement (In-App)",
     "{{title}}",
     "{{body}}",
     "Read announcement"),
]

_ARTICLES = [
    # (slug, title, summary, area, keywords, featured, body)
    ("go-live-checklist", "Go-live checklist for a new provider business",
     "Everything ServiceOS verifies before your business can accept bookings, in order.",
     "getting_started", ["onboarding", "activation", "verification", "go live", "setup"], True,
     "Complete your business profile, upload the required documents, publish at least one service with pricing, define your coverage area, and add at least one technician. Activation is granted once document verification passes."),
    ("document-verification-timeline", "How long document verification takes",
     "Verification windows, what a rejection means and how to resubmit a corrected document.",
     "getting_started", ["documents", "verification", "rejected", "kyc"], False,
     "Business documents are reviewed in the order received. If a document is rejected you will see the reason on Documents & Verification; upload a corrected version against the same requirement — the version history is preserved."),
    ("booking-not-appearing", "A booking is not appearing in Bookings & Jobs",
     "The four common causes: coverage, bookability, service publication and vertical activation.",
     "bookings_jobs", ["booking", "missing", "not showing", "bookability", "coverage"], True,
     "Check that the service is published, the pincode is inside an active coverage area, bookability has been refreshed, and the Home Services vertical is active for your account."),
    ("job-lifecycle", "The job lifecycle end to end",
     "From booking confirmation through dispatch, on-site execution, completion and invoicing.",
     "bookings_jobs", ["job", "status", "lifecycle", "dispatch", "complete"], False,
     "A confirmed booking creates a service job. The job moves through assigned, accepted, en route, in progress, completed and then invoiced. Only the assigned technician or an owner/manager can advance it."),
    ("dispatch-no-match", "Auto-dispatch is not matching any technician",
     "How matching evaluates job type, skills, availability and trust score.",
     "bookings_jobs", ["dispatch", "matching", "technician", "no match"], False,
     "Matching requires an exact job-type capability, an available slot in the technician's roster, and coverage of the service pincode. Use Matching Diagnostics to see which gate excluded each technician."),
    ("invite-team-members", "Invite staff and technicians and set their access",
     "Roles available in the tenant portal and what each role can and cannot do.",
     "team_access", ["team", "staff", "technician", "invite", "role", "permission"], True,
     "Owners can invite team members from Staff & Technicians. Managers can run day-to-day operations; technicians see only their own assigned jobs; read-only users can view but not change anything."),
    ("technician-cannot-sign-in", "A technician cannot sign in to the staff app",
     "Lockouts, password resets and deactivated team members.",
     "team_access", ["login", "staff app", "technician", "locked", "password"], False,
     "Confirm the team member is active, then trigger a password reset from their profile. Repeated failed sign-ins temporarily lock the account; the lock clears automatically."),
    ("pricing-not-applying", "A price is not applying to a booking",
     "Resolution order for base price, service options, modifiers and promotions.",
     "services_pricing", ["price", "pricing", "not applying", "option", "modifier"], False,
     "Pricing resolves in a fixed order: job-type base, selected service options, area/time modifiers, then promotions. A draft or unpublished price is never used for a live booking."),
    ("coverage-area-setup", "Set up and troubleshoot your coverage area",
     "Pincode-level coverage, overlap rules and why a saved area may not be bookable yet.",
     "services_pricing", ["coverage", "area", "pincode", "serviceability"], True,
     "Coverage is stored per pincode. After saving an area, bookability must be recalculated before customers can book — this normally happens within a few minutes."),
    ("usage-credits-explained", "How usage credits are charged and topped up",
     "What consumes credit, when it is deducted and how low-balance warnings work.",
     "finance_credits", ["credit", "usage", "top up", "balance", "wallet"], True,
     "Usage credit is deducted per chargeable platform action according to your active package. Low-balance warnings appear in the portal before service is restricted."),
    ("security-deposit-refund", "Security deposit: holds, deductions and refunds",
     "When a deposit is held, what can be deducted and how to request a refund.",
     "finance_credits", ["deposit", "refund", "security", "hold"], False,
     "Your security deposit is held against platform obligations. Refund requests are reviewed by the ServiceOS finance team; approved refunds are returned to the original payment method."),
    ("direct-payment-records", "Recording a direct or cash payment correctly",
     "Evidence requirements and how reconciliation decides accepted vs rejected.",
     "finance_credits", ["cash", "direct payment", "reconcile", "evidence"], False,
     "Record the amount actually collected and attach the receipt or UPI reference. Records without verifiable evidence are rejected during reconciliation."),
    ("sign-in-problems", "Cannot sign in to the tenant portal",
     "Lockouts, expired sessions, forced password changes and two-person accounts.",
     "account_security", ["login", "sign in", "locked", "401", "password"], True,
     "Use Forgot password first. Repeated failures lock the account temporarily. If your account is flagged for a forced password change you will be redirected before reaching the dashboard."),
    ("notification-not-received", "You are not receiving notifications",
     "Channel preferences, mandatory notifications and delivery troubleshooting.",
     "account_security", ["notification", "email", "not receiving", "alert"], False,
     "Check Notifications for your channel preferences. Some notifications are mandatory and cannot be disabled. In-app notifications are always delivered."),
    ("keep-your-account-secure", "Keeping your ServiceOS account secure",
     "Password hygiene, team offboarding and what ServiceOS support will never ask you for.",
     "account_security", ["security", "password", "otp", "phishing", "safe"], False,
     "ServiceOS support will never ask for your password, an OTP, or card/UPI credentials. Remove departing team members immediately and review access periodically."),
]

_ANNOUNCEMENTS = [
    ("planned_maintenance", "Scheduled maintenance: dispatch and matching, Sunday 02:00–03:30 IST",
     "Auto-dispatch and matching diagnostics will be briefly unavailable during this window. Bookings and job execution are unaffected.",
     False),
    ("feature_release", "New: Direct Payments reconciliation workspace",
     "Cash and direct payments recorded by technicians now reconcile in a dedicated workspace under Finance, with evidence review and dispute handling.",
     False),
    ("policy_update", "Updated document verification policy (effective this month)",
     "Business licence and insurance documents now require an explicit expiry date. Existing verified documents remain valid until their next renewal.",
     True),
]


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("ticket_number", sa.String(40), nullable=False),
        sa.Column("tenant_id", UUIDT, nullable=False),
        sa.Column("vertical_id", UUIDT, nullable=True),
        sa.Column("vertical_key", sa.String(60), nullable=True),
        sa.Column("reporter_user_id", UUIDT, nullable=False),
        sa.Column("reporter_name", sa.String(200), nullable=True),
        sa.Column("reporter_role", sa.String(60), nullable=True),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("subcategory", sa.String(120), nullable=True),
        sa.Column("product_area", sa.String(60), nullable=True),
        sa.Column("affected_feature", sa.String(200), nullable=True),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        _ts("started_at"),
        sa.Column("impact", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("priority_reasons", JSONB, nullable=True),
        sa.Column("is_critical_incident", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("critical_impact_key", sa.String(40), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="submitted"),
        sa.Column("related_entities", JSONB, nullable=True),
        sa.Column("assigned_team", sa.String(80), nullable=True),
        sa.Column("assigned_admin_user_id", UUIDT, nullable=True),
        sa.Column("assigned_admin_name", sa.String(200), nullable=True),
        sa.Column("sla_policy", sa.String(80), nullable=True),
        _ts("first_response_due_at"),
        _ts("first_response_met_at"),
        _ts("next_update_due_at"),
        _ts("resolution_target_at"),
        _ts("sla_paused_at"),
        sa.Column("sla_paused_seconds", sa.Integer(), nullable=False, server_default="0"),
        _ts("sla_breached_at"),
        _ts("escalated_at"),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        _ts("resolved_at"),
        _ts("closed_at"),
        _ts("reopen_deadline_at"),
        sa.Column("reopen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incident_id", UUIDT, nullable=True),
        sa.Column("merged_into_id", UUIDT, nullable=True),
        sa.Column("tenant_unread_count", sa.Integer(), nullable=False, server_default="0"),
        _ts("last_tenant_reply_at"),
        _ts("last_support_reply_at"),
        _ts("created_at", nullable=False, default=sa.text("now()")),
        _ts("updated_at", nullable=False, default=sa.text("now()")),
        sa.UniqueConstraint("ticket_number", name="uq_support_ticket_number"),
    )
    op.create_index("ix_support_tickets_tenant", "support_tickets", ["tenant_id"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index("ix_support_tickets_tenant_status", "support_tickets", ["tenant_id", "status"])
    op.create_index("ix_support_tickets_created", "support_tickets", ["created_at"])

    op.create_table(
        "support_ticket_messages",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("ticket_id", UUIDT, nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("author_user_id", UUIDT, nullable=True),
        sa.Column("author_name", sa.String(200), nullable=True),
        sa.Column("author_type", sa.String(40), nullable=False),
        sa.Column("author_role", sa.String(60), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="tenant_visible"),
        sa.Column("attachments", JSONB, nullable=True),
        _ts("created_at", nullable=False, default=sa.text("now()")),
    )
    op.create_index("ix_support_msgs_ticket", "support_ticket_messages", ["ticket_id"])
    op.create_index("ix_support_msgs_ticket_created", "support_ticket_messages", ["ticket_id", "created_at"])

    op.create_table(
        "support_ticket_events",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("ticket_id", UUIDT, nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("from_value", sa.String(80), nullable=True),
        sa.Column("to_value", sa.String(80), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", UUIDT, nullable=True),
        sa.Column("actor_type", sa.String(40), nullable=False, server_default="system"),
        sa.Column("actor_name", sa.String(200), nullable=True),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="tenant_visible"),
        sa.Column("meta", JSONB, nullable=True),
        _ts("created_at", nullable=False, default=sa.text("now()")),
    )
    op.create_index("ix_support_events_ticket", "support_ticket_events", ["ticket_id"])
    op.create_index("ix_support_events_ticket_created", "support_ticket_events", ["ticket_id", "created_at"])

    op.create_table(
        "support_ticket_attachments",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("ticket_id", UUIDT, nullable=False),
        sa.Column("message_id", UUIDT, nullable=True),
        sa.Column("media_asset_id", UUIDT, nullable=False),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("mime_type", sa.String(120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", UUIDT, nullable=True),
        sa.Column("uploaded_by_type", sa.String(40), nullable=False, server_default="tenant"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="tenant_visible"),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("created_at", nullable=False, default=sa.text("now()")),
    )
    op.create_index("ix_support_attach_ticket", "support_ticket_attachments", ["ticket_id"])

    op.create_table(
        "support_knowledge_articles",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("product_area", sa.String(60), nullable=False),
        sa.Column("keywords", JSONB, nullable=True),
        sa.Column("vertical_keys", JSONB, nullable=True),
        sa.Column("role_keys", JSONB, nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("policy_version", sa.String(40), nullable=True),
        sa.Column("helpful_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("not_helpful_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at", nullable=False, default=sa.text("now()")),
        _ts("updated_at", nullable=False, default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_support_kb_slug"),
    )
    op.create_index("ix_support_kb_area", "support_knowledge_articles", ["product_area"])
    op.create_index("ix_support_kb_published", "support_knowledge_articles", ["is_published"])

    op.create_table(
        "support_article_feedback",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("article_id", UUIDT, nullable=False),
        sa.Column("tenant_id", UUIDT, nullable=True),
        sa.Column("user_id", UUIDT, nullable=True),
        sa.Column("is_helpful", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        _ts("created_at", nullable=False, default=sa.text("now()")),
    )
    op.create_index("ix_support_kb_fb_article", "support_article_feedback", ["article_id"])

    op.create_table(
        "support_announcements",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("announcement_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("vertical_keys", JSONB, nullable=True),
        sa.Column("role_keys", JSONB, nullable=True),
        sa.Column("region_keys", JSONB, nullable=True),
        sa.Column("tenant_ids", JSONB, nullable=True),
        sa.Column("requires_acknowledgement", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("effective_from"),
        _ts("expires_at"),
        sa.Column("incident_id", UUIDT, nullable=True),
        _ts("created_at", nullable=False, default=sa.text("now()")),
        _ts("updated_at", nullable=False, default=sa.text("now()")),
    )
    op.create_index("ix_support_ann_effective", "support_announcements", ["effective_from"])
    op.create_index("ix_support_ann_published", "support_announcements", ["is_published"])

    op.create_table(
        "support_announcement_acks",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("announcement_id", UUIDT, nullable=False),
        sa.Column("tenant_id", UUIDT, nullable=False),
        sa.Column("user_id", UUIDT, nullable=False),
        _ts("acknowledged_at", nullable=False, default=sa.text("now()")),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_support_ann_ack"),
    )
    op.create_index("ix_support_ann_ack_tenant", "support_announcement_acks", ["tenant_id"])

    op.create_table(
        "support_platform_incidents",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("reference", sa.String(40), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="minor"),
        sa.Column("status", sa.String(30), nullable=False, server_default="investigating"),
        sa.Column("components", JSONB, nullable=True),
        _ts("started_at", nullable=False, default=sa.text("now()")),
        _ts("resolved_at"),
        _ts("last_checked_at"),
        _ts("created_at", nullable=False, default=sa.text("now()")),
        _ts("updated_at", nullable=False, default=sa.text("now()")),
    )
    op.create_index("ix_support_incidents_status", "support_platform_incidents", ["status"])
    op.create_index("ix_support_incidents_started", "support_platform_incidents", ["started_at"])

    op.create_table(
        "support_status_heartbeats",
        sa.Column("id", UUIDT, primary_key=True),
        sa.Column("component", sa.String(60), nullable=False),
        sa.Column("is_healthy", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("detail", sa.Text(), nullable=True),
        _ts("checked_at", nullable=False, default=sa.text("now()")),
    )

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # ── notification templates (one INSERT per statement: asyncpg rejects
    # multi-statement execute — see migration 202's note) ──
    for key, name, subject, body, action in _TEMPLATES:
        exists = conn.execute(
            sa.text("SELECT 1 FROM notif_event_templates WHERE template_key = :k"), {"k": key}
        ).fetchone()
        if exists:
            continue
        conn.execute(sa.text("""
            INSERT INTO notif_event_templates
                (id, template_key, template_name, channel, subject_template, body_template,
                 action_label_template, action_url_template, is_active, created_at, updated_at)
            -- action_url comes from the event payload (DEEP_LINK in
            -- constants.py) so the notification opens the EXACT ticket,
            -- not just the Help & Support landing page.
            VALUES (:id, :k, :n, 'in_app', :s, :b, :a, '{{action_url}}', true, :now, :now)
        """), {"id": str(uuid.uuid4()), "k": key, "n": name, "s": subject, "b": body,
               "a": action, "now": now})

    # ── real published KB content (admin-manageable rows, not frontend JSON) ──
    for slug, title, summary, area, keywords, featured, body in _ARTICLES:
        conn.execute(sa.text("""
            INSERT INTO support_knowledge_articles
                (id, slug, title, summary, body, product_area, keywords, is_featured,
                 is_published, policy_version, created_at, updated_at)
            VALUES (:id, :slug, :title, :summary, :body, :area, CAST(:kw AS jsonb),
                    :featured, true, 'v1', :now, :now)
            ON CONFLICT (slug) DO NOTHING
        """), {"id": str(uuid.uuid4()), "slug": slug, "title": title, "summary": summary,
               "body": body, "area": area, "kw": json.dumps(keywords),
               "featured": featured, "now": now})

    for atype, title, body, ack in _ANNOUNCEMENTS:
        conn.execute(sa.text("""
            INSERT INTO support_announcements
                (id, announcement_type, title, body, requires_acknowledgement,
                 is_published, effective_from, created_at, updated_at)
            VALUES (:id, :t, :ti, :b, :ack, true, :now, :now, :now)
        """), {"id": str(uuid.uuid4()), "t": atype, "ti": title, "b": body,
               "ack": ack, "now": now})


def downgrade() -> None:
    conn = op.get_bind()
    for key, *_ in _TEMPLATES:
        conn.execute(sa.text("DELETE FROM notif_event_templates WHERE template_key = :k"), {"k": key})
    for t in ("support_status_heartbeats", "support_platform_incidents",
              "support_announcement_acks", "support_announcements",
              "support_article_feedback", "support_knowledge_articles",
              "support_ticket_attachments", "support_ticket_events",
              "support_ticket_messages", "support_tickets"):
        op.drop_table(t)
