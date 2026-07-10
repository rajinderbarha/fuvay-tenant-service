"""P0 Trust & Quality Engine — Phase 1 data model.

Creates the badge, health, risk, and recalculation-job tables backing the
new Trust & Quality engine (Badge Engine, Badge Rule Engine, Health Engine,
Health Rule Engine, Risk Scoring Engine, Rule Simulator, Recalculation Jobs).

Revision ID: 095
Revises: 094
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "095"
down_revision = "094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "badge_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("badge_key", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("icon", sa.String(100)),
        sa.Column("color", sa.String(30)),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("customer_visible", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_visible", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("admin_only", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_badge_def_target_type", "badge_definitions", ["target_type"])

    op.create_table(
        "badge_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_key", sa.String(100), nullable=False, unique=True),
        sa.Column("badge_id", UUID(as_uuid=True), sa.ForeignKey("badge_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="global"),
        sa.Column("scope_id", UUID(as_uuid=True)),
        sa.Column("auto_award", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("manual_award_allowed", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("requires_admin_review", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("expiry_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("expiry_days", sa.Integer),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by_user_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_badge_rule_badge_id", "badge_rules", ["badge_id"])
    op.create_index("ix_badge_rule_status", "badge_rules", ["status"])

    op.create_table(
        "badge_rule_criteria",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("badge_rule_id", UUID(as_uuid=True), sa.ForeignKey("badge_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_key", sa.String(80), nullable=False),
        sa.Column("operator", sa.String(30), nullable=False),
        sa.Column("value_json", JSONB, nullable=False),
        sa.Column("time_window_days", sa.Integer),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("weight", sa.Numeric(5, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_badge_criteria_rule_id", "badge_rule_criteria", ["badge_rule_id"])

    op.create_table(
        "badge_rule_removal_criteria",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("badge_rule_id", UUID(as_uuid=True), sa.ForeignKey("badge_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_key", sa.String(80), nullable=False),
        sa.Column("operator", sa.String(30), nullable=False),
        sa.Column("value_json", JSONB, nullable=False),
        sa.Column("time_window_days", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_badge_removal_rule_id", "badge_rule_removal_criteria", ["badge_rule_id"])

    op.create_table(
        "badge_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("badge_id", UUID(as_uuid=True), sa.ForeignKey("badge_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_rule_id", UUID(as_uuid=True), sa.ForeignKey("badge_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("award_source", sa.String(30), nullable=False, server_default="auto_rule"),
        sa.Column("assigned_by_user_id", UUID(as_uuid=True)),
        sa.Column("assigned_reason", sa.Text),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by_user_id", UUID(as_uuid=True)),
        sa.Column("revoked_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_badge_assign_target", "badge_assignments", ["target_type", "target_id"])
    op.create_index("ix_badge_assign_badge", "badge_assignments", ["badge_id"])
    op.create_index("ix_badge_assign_status", "badge_assignments", ["status"])

    op.create_table(
        "health_formulas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("formula_key", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="global"),
        sa.Column("scope_id", UUID(as_uuid=True)),
        sa.Column("base_score", sa.Numeric(6, 2), nullable=False, server_default="100"),
        sa.Column("min_score", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("max_score", sa.Numeric(6, 2), nullable=False, server_default="100"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by_user_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_formula_target_type", "health_formulas", ["target_type"])
    op.create_index("ix_health_formula_status", "health_formulas", ["status"])

    op.create_table(
        "health_formula_components",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("formula_id", UUID(as_uuid=True), sa.ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_key", sa.String(80), nullable=False),
        sa.Column("weight_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False, server_default="positive"),
        sa.Column("min_value", sa.Numeric(12, 4)),
        sa.Column("max_value", sa.Numeric(12, 4)),
        sa.Column("normalization_method", sa.String(30), server_default="linear"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_component_formula_id", "health_formula_components", ["formula_id"])

    op.create_table(
        "health_penalty_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("formula_id", UUID(as_uuid=True), sa.ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_key", sa.String(80), nullable=False),
        sa.Column("operator", sa.String(30), nullable=False),
        sa.Column("value_json", JSONB, nullable=False),
        sa.Column("penalty_points", sa.Numeric(6, 2), nullable=False),
        sa.Column("hard_override_score", sa.Numeric(6, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_penalty_formula_id", "health_penalty_rules", ["formula_id"])

    op.create_table(
        "health_bonus_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("formula_id", UUID(as_uuid=True), sa.ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_key", sa.String(80), nullable=False),
        sa.Column("operator", sa.String(30), nullable=False),
        sa.Column("value_json", JSONB, nullable=False),
        sa.Column("bonus_points", sa.Numeric(6, 2), nullable=False),
        sa.Column("max_bonus_cap", sa.Numeric(6, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_bonus_formula_id", "health_bonus_rules", ["formula_id"])

    op.create_table(
        "health_band_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("formula_id", UUID(as_uuid=True), sa.ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("band_key", sa.String(40), nullable=False),
        sa.Column("band_name", sa.String(80), nullable=False),
        sa.Column("min_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("max_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("color", sa.String(30)),
        sa.Column("bookable_allowed", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("recommended_action", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_band_formula_id", "health_band_rules", ["formula_id"])

    op.create_table(
        "health_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("formula_id", UUID(as_uuid=True), sa.ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Numeric(6, 2), nullable=False),
        sa.Column("band_key", sa.String(40)),
        sa.Column("risk_level", sa.String(30)),
        sa.Column("component_breakdown_json", JSONB),
        sa.Column("penalties_json", JSONB),
        sa.Column("bonuses_json", JSONB),
        sa.Column("recommended_actions_json", JSONB),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_score_target", "health_scores", ["target_type", "target_id"])
    op.create_unique_constraint("uq_health_score_target_formula", "health_scores", ["target_type", "target_id", "formula_id"])

    op.create_table(
        "risk_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_key", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="global"),
        sa.Column("scope_id", UUID(as_uuid=True)),
        sa.Column("condition_json", JSONB, nullable=False),
        sa.Column("risk_level", sa.String(30), nullable=False),
        sa.Column("risk_score_delta", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("recommended_actions_json", JSONB),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_rule_target_type", "risk_rules", ["target_type"])

    op.create_table(
        "risk_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("risk_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("risk_level", sa.String(30), nullable=False),
        sa.Column("reasons_json", JSONB),
        sa.Column("recommended_actions_json", JSONB),
        sa.Column("bookable_impact", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("finance_impact", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_score_target", "risk_scores", ["target_type", "target_id"], unique=True)

    op.create_table(
        "trust_quality_recalculation_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(20), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="all"),
        sa.Column("scope_id", UUID(as_uuid=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("total_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("triggered_by", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("triggered_by_user_id", UUID(as_uuid=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_summary", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tq_recalc_job_status", "trust_quality_recalculation_jobs", ["status"])

    op.create_table(
        "trust_quality_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("action_type", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(30)),
        sa.Column("target_id", UUID(as_uuid=True)),
        sa.Column("actor_user_id", UUID(as_uuid=True)),
        sa.Column("actor_role", sa.String(40)),
        sa.Column("old_value_json", JSONB),
        sa.Column("new_value_json", JSONB),
        sa.Column("reason", sa.Text),
        sa.Column("request_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tq_audit_action", "trust_quality_audit_logs", ["action_type"])
    op.create_index("ix_tq_audit_target", "trust_quality_audit_logs", ["target_type", "target_id"])

    # ── Register the 8 Trust & Quality engines in Engine Management (migration 081 table) ──
    conn = op.get_bind()
    has_platform_engines = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name='platform_engines'")).fetchone()
    if has_platform_engines:
        engines = [
            ("trust_quality_engine", "Trust & Quality Engine",
             "Umbrella engine coordinating badges, health, and risk scoring.", "core"),
            ("badge_engine", "Badge Engine", "Runtime badge assignment/revocation.", "core"),
            ("badge_rule_engine", "Badge Rule Engine", "Configurable badge award/removal criteria.", "core"),
            ("health_engine", "Health Engine", "Runtime provider/staff/customer/service health scoring.", "core"),
            ("health_rule_engine", "Health Rule Engine", "Configurable health formulas, penalties, bonuses, bands.", "core"),
            ("risk_scoring_engine", "Risk Scoring Engine", "Converts health/rule signals into risk levels and actions.", "core"),
            ("rule_simulator_engine", "Rule Simulator Engine", "Previews badge/health rule outcomes before activation.", "plugin"),
            ("recalculation_job_engine", "Recalculation Job Engine", "Runs badge/health/risk recalculation jobs.", "plugin"),
        ]
        for key, name, desc, etype in engines:
            conn.execute(sa.text("""
                INSERT INTO platform_engines
                    (id, engine_key, display_name, description, engine_type,
                     lifecycle_status, global_status, is_core, is_locked,
                     is_customer_visible, is_tenant_visible, version, metadata_json,
                     created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :key, :name, :desc, :etype,
                     'active', 'enabled', :is_core, false,
                     false, true, '1.0.0', '{}'::jsonb,
                     now(), now())
                ON CONFLICT (engine_key) DO NOTHING
            """), {"key": key, "name": name, "desc": desc, "etype": etype, "is_core": etype == "core"})

        deps = [
            ("trust_quality_engine", "badge_engine"),
            ("trust_quality_engine", "health_engine"),
            ("trust_quality_engine", "risk_scoring_engine"),
            ("badge_engine", "badge_rule_engine"),
            ("badge_engine", "recalculation_job_engine"),
            ("health_engine", "health_rule_engine"),
            ("health_engine", "recalculation_job_engine"),
            ("health_engine", "risk_scoring_engine"),
            ("rule_simulator_engine", "badge_rule_engine"),
            ("rule_simulator_engine", "health_rule_engine"),
        ]
        for engine_key, depends_on_key in deps:
            conn.execute(sa.text("""
                INSERT INTO engine_dependencies
                    (id, engine_id, engine_key, depends_on_engine_id, depends_on_engine_key,
                     dependency_type, status, created_at, updated_at)
                SELECT gen_random_uuid(), e.id, e.engine_key, d.id, d.engine_key,
                       'required', 'active', now(), now()
                FROM platform_engines e, platform_engines d
                WHERE e.engine_key = :ekey AND d.engine_key = :dkey
                ON CONFLICT (engine_id, depends_on_engine_id) DO NOTHING
            """), {"ekey": engine_key, "dkey": depends_on_key})


def downgrade() -> None:
    conn = op.get_bind()
    has_platform_engines = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name='platform_engines'")).fetchone()
    if has_platform_engines:
        conn.execute(sa.text("""
            DELETE FROM engine_dependencies WHERE engine_key IN (
                'trust_quality_engine','badge_engine','badge_rule_engine','health_engine',
                'health_rule_engine','risk_scoring_engine','rule_simulator_engine','recalculation_job_engine')
        """))
        conn.execute(sa.text("""
            DELETE FROM platform_engines WHERE engine_key IN (
                'trust_quality_engine','badge_engine','badge_rule_engine','health_engine',
                'health_rule_engine','risk_scoring_engine','rule_simulator_engine','recalculation_job_engine')
        """))
    op.drop_table("trust_quality_audit_logs")
    op.drop_table("trust_quality_recalculation_jobs")
    op.drop_table("risk_scores")
    op.drop_table("risk_rules")
    op.drop_table("health_scores")
    op.drop_table("health_band_rules")
    op.drop_table("health_bonus_rules")
    op.drop_table("health_penalty_rules")
    op.drop_table("health_formula_components")
    op.drop_table("health_formulas")
    op.drop_table("badge_assignments")
    op.drop_table("badge_rule_removal_criteria")
    op.drop_table("badge_rule_criteria")
    op.drop_table("badge_rules")
    op.drop_table("badge_definitions")
