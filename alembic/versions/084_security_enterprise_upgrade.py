"""Security Enterprise Upgrade — Threats / Sessions / IP Blocklist / API Keys / Audit / Policies SOC.
- Extend suspicious_activity_logs (-> "Threats") with threat_number, risk_score, source,
  target_user_id, assigned_to_admin_id, last_seen_at, resolved_at
- Extend ip_blocklist with scope, status, hit_count, last_hit_at, revoked_at, revoked_by_user_id
- Extend tenant_api_keys with owner_type, allowed_ips_json, rate_limit_per_minute, permissions_json
- Create ip_block_hits, api_key_usage_logs, security_policies (seeded with 10 default policies)

Revision ID: 084
Revises: 083
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "084"
down_revision = "083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    def _table_exists(t: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:t"), {"t": t})
        return bool(r.fetchone())

    # ── suspicious_activity_logs ("Threats") ──────────────────────────────────
    if not _col_exists("suspicious_activity_logs", "threat_number"):
        op.add_column("suspicious_activity_logs", sa.Column("threat_number", sa.String(60), nullable=True))
        conn.execute(sa.text(
            "UPDATE suspicious_activity_logs SET threat_number = 'THR-' || substr(id::text, 1, 8) "
            "WHERE threat_number IS NULL"))
    if not _col_exists("suspicious_activity_logs", "risk_score"):
        op.add_column("suspicious_activity_logs", sa.Column("risk_score", sa.Integer, server_default="0", nullable=False))
    if not _col_exists("suspicious_activity_logs", "source"):
        op.add_column("suspicious_activity_logs", sa.Column("source", sa.String(50), nullable=True))
    if not _col_exists("suspicious_activity_logs", "target_user_id"):
        op.add_column("suspicious_activity_logs", sa.Column("target_user_id", UUID(as_uuid=True), nullable=True))
    if not _col_exists("suspicious_activity_logs", "assigned_to_admin_id"):
        op.add_column("suspicious_activity_logs", sa.Column("assigned_to_admin_id", UUID(as_uuid=True), nullable=True))
    if not _col_exists("suspicious_activity_logs", "last_seen_at"):
        op.add_column("suspicious_activity_logs", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        conn.execute(sa.text("UPDATE suspicious_activity_logs SET last_seen_at = created_at WHERE last_seen_at IS NULL"))
    if not _col_exists("suspicious_activity_logs", "resolved_at"):
        op.add_column("suspicious_activity_logs", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))

    # ── ip_blocklist ──────────────────────────────────────────────────────────
    if not _col_exists("ip_blocklist", "scope"):
        op.add_column("ip_blocklist", sa.Column("scope", sa.String(30), server_default="'all'", nullable=False))
    if not _col_exists("ip_blocklist", "status"):
        op.add_column("ip_blocklist", sa.Column("status", sa.String(20), server_default="'active'", nullable=False))
        conn.execute(sa.text(
            "UPDATE ip_blocklist SET status = CASE WHEN is_active THEN 'active' ELSE 'revoked' END"))
    if not _col_exists("ip_blocklist", "hit_count"):
        op.add_column("ip_blocklist", sa.Column("hit_count", sa.Integer, server_default="0", nullable=False))
    if not _col_exists("ip_blocklist", "last_hit_at"):
        op.add_column("ip_blocklist", sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True))
    if not _col_exists("ip_blocklist", "revoked_at"):
        op.add_column("ip_blocklist", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    if not _col_exists("ip_blocklist", "revoked_by_user_id"):
        op.add_column("ip_blocklist", sa.Column("revoked_by_user_id", UUID(as_uuid=True), nullable=True))

    # ── tenant_api_keys ───────────────────────────────────────────────────────
    if not _col_exists("tenant_api_keys", "owner_type"):
        op.add_column("tenant_api_keys", sa.Column("owner_type", sa.String(20), server_default="'tenant'", nullable=False))
    if not _col_exists("tenant_api_keys", "allowed_ips_json"):
        op.add_column("tenant_api_keys", sa.Column("allowed_ips_json", JSONB, nullable=True))
    if not _col_exists("tenant_api_keys", "rate_limit_per_minute"):
        op.add_column("tenant_api_keys", sa.Column("rate_limit_per_minute", sa.Integer, nullable=True))
    if not _col_exists("tenant_api_keys", "permissions_json"):
        op.add_column("tenant_api_keys", sa.Column("permissions_json", JSONB, server_default="[]", nullable=False))

    # ── ip_block_hits ─────────────────────────────────────────────────────────
    if not _table_exists("ip_block_hits"):
        op.create_table(
            "ip_block_hits",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("block_id", UUID(as_uuid=True), nullable=False),
            sa.Column("ip_or_cidr", sa.String(50), nullable=False),
            sa.Column("hit_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("path", sa.String(500), nullable=True),
            sa.Column("method", sa.String(10), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("blocked_scope", sa.String(30), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_ibh_block_id", "ip_block_hits", ["block_id"])
        op.create_index("ix_ibh_hit_at", "ip_block_hits", ["hit_at"])

    # ── api_key_usage_logs ────────────────────────────────────────────────────
    if not _table_exists("api_key_usage_logs"):
        op.create_table(
            "api_key_usage_logs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("api_key_id", UUID(as_uuid=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("endpoint", sa.String(500), nullable=True),
            sa.Column("method", sa.String(10), nullable=True),
            sa.Column("status_code", sa.Integer, nullable=True),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("response_ms", sa.Integer, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_akul_api_key_id", "api_key_usage_logs", ["api_key_id"])
        op.create_index("ix_akul_used_at", "api_key_usage_logs", ["used_at"])

    # ── security_policies ─────────────────────────────────────────────────────
    if not _table_exists("security_policies"):
        op.create_table(
            "security_policies",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("policy_key", sa.String(80), nullable=False, unique=True),
            sa.Column("policy_value_json", JSONB, nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("updated_reason", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        defaults = [
            ("mfa_required_super_admin", "true", "Require MFA for Super Admin accounts"),
            ("mfa_required_platform_admin", "false", "Require MFA for Platform Admin accounts"),
            ("fresh_mfa_for_sensitive_actions", "true", "Require a fresh MFA challenge before sensitive actions"),
            ("failed_login_threshold", "5", "Failed login attempts before a warning/lockout escalation"),
            ("auto_lock_threshold", "10", "Failed login attempts before automatic account lock"),
            ("session_max_lifetime_minutes", "1440", "Maximum session lifetime in minutes"),
            ("idle_timeout_minutes", "30", "Idle timeout before a session is considered expired"),
            ("api_key_max_expiry_days", "365", "Maximum allowed expiry window for a new API key, in days"),
            ("ip_block_auto_expiry_default_days", "30", "Default auto-expiry for a temporary IP block, in days"),
            ("export_audit_retention_days", "365", "How long exported audit log files are retained"),
        ]
        table = sa.table(
            "security_policies",
            sa.column("id", UUID(as_uuid=True)),
            sa.column("policy_key", sa.String),
            sa.column("policy_value_json", JSONB),
            sa.column("description", sa.String),
        )
        import json
        op.bulk_insert(table, [
            {"id": uuid.uuid4(), "policy_key": key, "policy_value_json": json.loads(val), "description": desc}
            for key, val, desc in defaults
        ])


def downgrade() -> None:
    op.drop_table("security_policies")
    op.drop_table("api_key_usage_logs")
    op.drop_table("ip_block_hits")
    for col in ("permissions_json", "rate_limit_per_minute", "allowed_ips_json", "owner_type"):
        op.drop_column("tenant_api_keys", col)
    for col in ("revoked_by_user_id", "revoked_at", "last_hit_at", "hit_count", "status", "scope"):
        op.drop_column("ip_blocklist", col)
    for col in ("resolved_at", "last_seen_at", "assigned_to_admin_id", "target_user_id", "source", "risk_score", "threat_number"):
        op.drop_column("suspicious_activity_logs", col)
