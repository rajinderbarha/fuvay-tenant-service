"""Tenant AI Assistant engine — admin-configured, retrieval-grounded support agent.

Creates the assistant's own tables (config, admin-authored quick options,
sessions, messages, feedback) and seeds:

  * one enabled global config row with safe enterprise defaults
  * a full quick-option menu mapped to the real support_knowledge_articles
    product areas, so the panel is populated the moment it is switched on
  * email channel templates for the support events that already exist but
    were in_app-only, so an admin reply reaches the tenant by email too

Revision ID: 293
Revises: 292
"""
import json
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "293"
down_revision = "292"
branch_labels = None
depends_on = None


# ──────────────────────────────────────────────────────────────────────────────
# Seed data — the default option menu. Every article-backed entry points at a
# product_area that really exists in support_knowledge_articles today.
# ──────────────────────────────────────────────────────────────────────────────
_OPTIONS = [
    # group, label, description, icon, action_type, action_target, order, featured
    ("getting_started", "Get my business live",
     "What is still pending before you can take bookings", "Rocket",
     "topic", "getting_started", 10, True),
    ("getting_started", "Where do I stand right now?",
     "A live readiness snapshot of your account", "Gauge",
     "tool", "get_readiness_snapshot", 20, True),
    ("getting_started", "How long does verification take?",
     "Document review timelines", "Clock",
     "prompt", "How long does document verification take?", 30, False),

    ("services_pricing", "Add or change a service",
     "Publish a service and set what you charge", "Wrench",
     "topic", "services_pricing", 10, True),
    ("services_pricing", "My price is not applying",
     "Why a booking shows a different amount", "IndianRupee",
     "prompt", "Why is my price not applying to a booking?", 20, False),
    ("services_pricing", "Set up my coverage area",
     "Pincodes and zones you serve", "MapPin",
     "prompt", "How do I set up my coverage area?", 30, True),

    ("bookings_jobs", "Why is a job not dispatching?",
     "Auto-dispatch is not matching a technician", "Send",
     "prompt", "Why is auto-dispatch not matching any technician?", 10, True),
    ("bookings_jobs", "How my jobs are doing",
     "Live counts by stage for your business", "ClipboardList",
     "tool", "get_job_summary", 20, True),
    ("bookings_jobs", "The job lifecycle end to end",
     "Every stage from booking to completion", "GitBranch",
     "topic", "bookings_jobs", 30, False),

    ("team_access", "Invite staff or technicians",
     "Add people and set what they can see", "UserPlus",
     "topic", "team_access", 10, True),
    ("team_access", "My team at a glance",
     "Who is active on your account", "Users",
     "tool", "get_team_summary", 20, False),
    ("team_access", "A technician cannot sign in",
     "Staff app access problems", "KeyRound",
     "prompt", "A technician cannot sign in to the staff app.", 30, False),

    ("finance_credits", "How usage credits work",
     "Charging, balances and top-ups", "Coins",
     "topic", "finance_credits", 10, True),
    ("finance_credits", "My plan and limits",
     "What your current package includes", "Package",
     "tool", "get_business_profile", 20, True),

    ("account_security", "Sign-in and two-step verification",
     "Access and account protection", "ShieldCheck",
     "topic", "account_security", 10, False),
    ("account_security", "I am not receiving notifications",
     "Alerts are not arriving", "BellOff",
     "prompt", "I am not receiving notifications.", 20, False),

    ("support", "Is anything down right now?",
     "Live ServiceOS platform status", "Activity",
     "tool", "get_platform_status", 10, True),
    ("support", "My open requests",
     "Tickets you have with the ServiceOS team", "Inbox",
     "tool", "get_open_requests", 20, True),
    ("support", "Talk to a human",
     "Raise a ticket — support replies in your Help & Support page", "LifeBuoy",
     "ticket", None, 30, True),
]

_DEFAULT_TOOLS = [
    "search_knowledge", "get_readiness_snapshot", "get_business_profile",
    "get_job_summary", "get_team_summary", "get_open_requests",
    "get_platform_status", "get_announcements",
]

_SYSTEM_PROMPT = """You are {display_name}, the in-product support assistant for \
ServiceOS provider businesses (tenants).

ABSOLUTE RULES — these override anything a user asks:
1. Answer ONLY from the CONTEXT block supplied to you. The context is retrieved \
from the ServiceOS help centre and from this tenant's own live account data.
2. If the context does not contain the answer, say so plainly and offer to raise \
a support ticket. NEVER guess a procedure, menu path, URL, price, or policy.
3. You have no knowledge of ServiceOS source code, database schema, servers, \
API internals, or other tenants. If asked, say it is not something you can help \
with and offer to raise a ticket.
4. Only discuss this tenant's own business and how to use the ServiceOS provider \
portal. Decline anything else, briefly and politely.
5. Never reveal internal identifiers, commission rates, platform margins, or \
another business's data, even if they appear in context.

STYLE: Direct and practical. Lead with the answer. Use short numbered steps for \
procedures. Keep it under 150 words unless steps demand more. Plain text only — \
no markdown headings or bold. Indian English, ₹ for money."""


def upgrade() -> None:
    # ── config ────────────────────────────────────────────────────────────────
    op.create_table(
        "tenant_assistant_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scope", sa.String(20), nullable=False, server_default="global"),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),

        # identity
        sa.Column("display_name", sa.String(80), nullable=False, server_default="Fuvay AI"),
        sa.Column("tagline", sa.String(160), nullable=True),
        sa.Column("avatar_emoji", sa.String(16), nullable=False, server_default="✨"),
        sa.Column("greeting", sa.Text, nullable=True),
        sa.Column("input_placeholder", sa.String(160), nullable=False,
                  server_default="Ask about your business…"),
        sa.Column("disabled_message", sa.Text, nullable=True),

        # answering
        sa.Column("llm_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("model", sa.String(60), nullable=False, server_default="deepseek-chat"),
        sa.Column("temperature", sa.Numeric(3, 2), nullable=False, server_default="0.20"),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="700"),
        sa.Column("max_tool_iterations", sa.Integer, nullable=False, server_default="4"),
        sa.Column("system_prompt", sa.Text, nullable=False),

        # retrieval gate
        sa.Column("retrieval_top_k", sa.Integer, nullable=False, server_default="5"),
        sa.Column("retrieval_min_score", sa.Numeric(4, 3), nullable=False, server_default="0.180"),
        sa.Column("require_citation", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("allowed_product_areas", JSONB, nullable=True),
        sa.Column("allowed_tools", JSONB, nullable=False),

        # refusal copy
        sa.Column("out_of_scope_message", sa.Text, nullable=False),
        sa.Column("no_answer_message", sa.Text, nullable=False),

        # panel composition
        sa.Column("show_categories", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("show_most_asked", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("show_live_state", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("show_recent_requests", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("show_page_context", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("show_announcements", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("max_options_total", sa.Integer, nullable=False, server_default="24"),
        sa.Column("max_options_per_group", sa.Integer, nullable=False, server_default="6"),

        # escalation
        sa.Column("escalation_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("auto_escalate_after_unresolved", sa.Integer, nullable=False, server_default="2"),
        sa.Column("escalation_category", sa.String(60), nullable=False, server_default="other"),
        sa.Column("escalation_impact", sa.String(40), nullable=False, server_default="question"),
        sa.Column("escalation_include_transcript", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("email_on_escalation", sa.Boolean, nullable=False, server_default=sa.text("true")),

        # limits
        sa.Column("rate_limit_per_hour", sa.Integer, nullable=False, server_default="40"),
        sa.Column("session_idle_minutes", sa.Integer, nullable=False, server_default="120"),
        sa.Column("allowed_roles", JSONB, nullable=True),

        sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ta_configs_scope", "tenant_assistant_configs", ["scope", "scope_id"])
    op.create_unique_constraint("uq_ta_config_global", "tenant_assistant_configs", ["scope", "scope_id"])

    # ── admin-authored quick options ──────────────────────────────────────────
    op.create_table(
        "tenant_assistant_options",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("config_id", UUID(as_uuid=True), nullable=True),
        sa.Column("group_key", sa.String(60), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("description", sa.String(300), nullable=True),
        sa.Column("icon", sa.String(60), nullable=True),
        sa.Column("action_type", sa.String(20), nullable=False),
        sa.Column("action_target", sa.Text, nullable=True),
        sa.Column("role_keys", JSONB, nullable=True),
        sa.Column("vertical_keys", JSONB, nullable=True),
        sa.Column("page_prefixes", JSONB, nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="100"),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_featured", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("click_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ta_options_group", "tenant_assistant_options", ["group_key", "display_order"])
    op.create_index("ix_ta_options_enabled", "tenant_assistant_options", ["is_enabled"])

    # ── sessions ──────────────────────────────────────────────────────────────
    op.create_table(
        "tenant_assistant_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_role", sa.String(60), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("turn_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unresolved_streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("escalated_ticket_id", UUID(as_uuid=True), nullable=True),
        sa.Column("opened_from_path", sa.String(300), nullable=True),
        sa.Column("context_data", JSONB, nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ta_sessions_tenant", "tenant_assistant_sessions", ["tenant_id"])
    op.create_index("ix_ta_sessions_user_active", "tenant_assistant_sessions",
                    ["user_id", "status", "last_activity_at"])

    # ── messages ──────────────────────────────────────────────────────────────
    op.create_table(
        "tenant_assistant_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("resolution", sa.String(30), nullable=True),
        sa.Column("citations", JSONB, nullable=True),
        sa.Column("tools_used", JSONB, nullable=True),
        sa.Column("retrieval_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("used_llm", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ta_messages_session", "tenant_assistant_messages", ["session_id", "created_at"])
    op.create_index("ix_ta_messages_resolution", "tenant_assistant_messages", ["resolution"])

    # ── answer feedback ───────────────────────────────────────────────────────
    op.create_table(
        "tenant_assistant_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("is_helpful", sa.Boolean, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("message_id", "user_id", name="uq_ta_feedback_once"),
    )

    # ── seed the global config ────────────────────────────────────────────────
    conn = op.get_bind()
    config_id = str(uuid.uuid4())
    conn.execute(sa.text("""
        INSERT INTO tenant_assistant_configs (
            id, scope, scope_id, is_enabled, display_name, tagline, avatar_emoji,
            greeting, system_prompt, allowed_tools,
            out_of_scope_message, no_answer_message
        ) VALUES (
            :id, 'global', NULL, true, 'Fuvay AI',
            'Support for your business on ServiceOS', '✨',
            'Hello! I can help with your services, bookings, team, plan and payouts. '
            'Pick a topic below or ask me anything about your business.',
            :prompt, CAST(:tools AS jsonb),
            'I can only help with your ServiceOS business account — services, bookings, '
            'team, plan and payouts. For anything else, I can raise a ticket with our '
            'support team.',
            'I do not have a documented answer for that yet. I can raise a ticket so the '
            'ServiceOS support team replies to you directly in Help & Support.'
        )
    """), {"id": config_id, "prompt": _SYSTEM_PROMPT,
           "tools": json.dumps(_DEFAULT_TOOLS)})

    for group, label, desc, icon, atype, target, order, featured in _OPTIONS:
        conn.execute(sa.text("""
            INSERT INTO tenant_assistant_options (
                config_id, group_key, label, description, icon,
                action_type, action_target, display_order, is_featured
            ) VALUES (:cid, :g, :l, :d, :i, :at, :tg, :o, :f)
        """), {"cid": config_id, "g": group, "l": label, "d": desc, "i": icon,
               "at": atype, "tg": target, "o": order, "f": featured})

    # ── email templates for support events (previously in_app only) ───────────
    # Requirement: an admin reply must also reach the tenant by email.
    email_templates = [
        ("support.request.submitted.email", "Support request received (email)",
         "We have received your request {ticket_number}",
         "Hello,\n\nWe have received your support request {ticket_number}: {subject}\n\n"
         "Priority: {priority}\nStatus: {status}\n\n"
         "You can follow the conversation here:\n{action_url}\n\n— ServiceOS Support"),
        ("support.request.replied.email", "Support replied (email)",
         "ServiceOS replied to {ticket_number}",
         "Hello,\n\nThe ServiceOS support team has replied to your request "
         "{ticket_number}: {subject}\n\nOpen the conversation to read the reply "
         "and respond:\n{action_url}\n\n— ServiceOS Support"),
        ("support.request.info_requested.email", "Support needs information (email)",
         "Action needed on {ticket_number}",
         "Hello,\n\nOur support team needs more information to continue with "
         "{ticket_number}: {subject}\n\nPlease reply here:\n{action_url}\n\n— ServiceOS Support"),
        ("support.request.resolved.email", "Support request resolved (email)",
         "{ticket_number} has been resolved",
         "Hello,\n\nYour support request {ticket_number}: {subject} has been marked "
         "resolved.\n\nIf the problem is still there you can reopen it here:\n"
         "{action_url}\n\n— ServiceOS Support"),
    ]
    for key, name, subject, body in email_templates:
        conn.execute(sa.text("""
            INSERT INTO notif_event_templates
                (template_key, template_name, channel, subject_template,
                 body_template, action_label_template, action_url_template, is_active)
            VALUES (:k, :n, 'email', :s, :b, 'Open request', '{action_url}', true)
            ON CONFLICT DO NOTHING
        """), {"k": key, "n": name, "s": subject, "b": body})


def downgrade() -> None:
    op.execute("DELETE FROM notif_event_templates WHERE template_key LIKE 'support.request.%.email'")
    op.drop_table("tenant_assistant_feedback")
    op.drop_table("tenant_assistant_messages")
    op.drop_table("tenant_assistant_sessions")
    op.drop_table("tenant_assistant_options")
    op.drop_table("tenant_assistant_configs")
