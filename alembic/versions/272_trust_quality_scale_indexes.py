"""Scale indexes for the Trust & Quality engine.

Every index here backs an access path that the batched recalculation worker or
the admin console now performs on every sweep or page load, and that was doing a
sequential scan before.

Revision ID: 272
Revises: 271
"""
from alembic import op


revision = "272"
down_revision = "271"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Built concurrently: badge_assignments and health_scores are read on the
    # customer-facing provider profile, so an ACCESS EXCLUSIVE lock is not
    # acceptable in production.
    with op.get_context().autocommit_block():
        statements = (
            # The recalculation worker's per-batch assignment lookup, and the
            # console's "badges this target holds" read. Partial on the active
            # status because revoked/expired rows accumulate forever and are
            # never what either caller is looking for.
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ba_active_target "
            "ON badge_assignments (target_type, target_id, badge_id) WHERE status = 'active'",
            # Job history is read newest-first, page by page.
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tqrj_created "
            "ON trust_quality_recalculation_jobs (created_at DESC)",
            # The worker claims queued jobs oldest-first; the in-flight guard and
            # stale recovery both filter on status.
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tqrj_status_created "
            "ON trust_quality_recalculation_jobs (status, created_at)",
            # Audit trail: newest-first, optionally filtered.
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tqal_created "
            "ON trust_quality_audit_logs (created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tqal_target_created "
            "ON trust_quality_audit_logs (target_type, created_at DESC)",
            # The Scores tab: worst-scoring first, filtered by band or target.
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hs_target_type_score "
            "ON health_scores (target_type, score)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hs_band_score "
            "ON health_scores (band_key, score)",
            # The worker fetches a whole batch's existing scores per formula.
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hs_formula_target "
            "ON health_scores (formula_id, target_type, target_id)",
            # The Risk tab: highest risk first, and the "who is blocked" filter.
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rs_level_score "
            "ON risk_scores (risk_level, risk_score DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rs_target_type_score "
            "ON risk_scores (target_type, risk_score DESC)",
            # Rule loading is once per sweep, but it is on the critical path of
            # every sweep and every rules page.
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_br_active_target "
            "ON badge_rules (target_type, status) WHERE auto_award",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_brc_rule "
            "ON badge_rule_criteria (badge_rule_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_brrc_rule "
            "ON badge_rule_removal_criteria (badge_rule_id)",
        )
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    names = (
        "ix_brrc_rule", "ix_brc_rule", "ix_br_active_target",
        "ix_rs_target_type_score", "ix_rs_level_score",
        "ix_hs_formula_target", "ix_hs_band_score", "ix_hs_target_type_score",
        "ix_tqal_target_created", "ix_tqal_created",
        "ix_tqrj_status_created", "ix_tqrj_created",
        "ix_ba_active_target",
    )
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
