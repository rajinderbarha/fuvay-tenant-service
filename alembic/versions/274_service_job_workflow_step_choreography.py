"""Give the canonical workflow an ordered, cross-app step definition.

`service_job_workflow` is the single workflow authority (migration 186), but it
only ever expressed *capability booleans* — inspection_required,
quote_approval_required, and so on. It has never held a step SEQUENCE, so
nothing could answer "what happens next, in which app, and who does it".

That gap is why `execution/mobile_job_detail_service.py` carries a hard-coded
`_REPAIR_SEQUENCE`, disclosing in its own docstring: "there is no per-job-type
ordered-stage table in the schema (audited)". This adds one.

The shape is ported from the step model that migration 186 dropped along with
`workflow_templates` (app/engines/workflows/), because that model was the only
place in the codebase that expressed cross-app choreography — per-step
`owner_app` and per-audience visibility, per-transition `allowed_role`. Rather
than resurrect that engine and re-create the three-way split 186 set out to end,
its one genuinely missing idea lands on the canonical table.

Both columns default to an empty array, so every existing workflow row keeps
behaving exactly as it does today until an admin defines steps.

Revision ID: 274
Revises: 273
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "274"
down_revision = "273"
branch_labels = None
depends_on = None

_TABLE = "service_job_workflow"


def _has_column(name: str) -> bool:
    bind = op.get_bind()
    return bind.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = :t AND column_name = :c
    """), {"t": _TABLE, "c": name}).scalar() is not None


def upgrade() -> None:
    # steps_json: ordered list of
    #   {step_key, step_name, maps_to_status, owner_app, owner_role,
    #    customer_visible, tenant_visible, staff_visible, admin_visible,
    #    requires_note, requires_photo, requires_approval, sla_minutes,
    #    display_order}
    #
    # `maps_to_status` is the join to reality: it holds a canonical
    # service_jobs.status value (the JOB_TRANSITIONS vocabulary) or NULL for
    # steps that live outside the job's own lifecycle — a booking-level step
    # like "Provider Accepted", or a post-completion one like "Review
    # Requested". Without it a step sequence is decoration; with it, a client
    # can mark each step done from the job's real status and event history.
    if not _has_column("steps_json"):
        op.add_column(_TABLE, sa.Column("steps_json", JSONB, nullable=False,
                                        server_default=sa.text("'[]'::jsonb")))
    # transitions_json: ordered list of
    #   {from_step_key, to_step_key, action_label, allowed_role,
    #    requires_reason, triggers_notification, auto_transition}
    if not _has_column("transitions_json"):
        op.add_column(_TABLE, sa.Column("transitions_json", JSONB, nullable=False,
                                        server_default=sa.text("'[]'::jsonb")))

    # The per-job resolver reads the snapshotted row by id, but the admin
    # surfaces list "workflows that actually define steps" — cheap partial
    # index rather than scanning every version row ever published.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_sjw_has_steps ON service_job_workflow (is_current)
         WHERE jsonb_array_length(steps_json) > 0
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sjw_has_steps")
    if _has_column("transitions_json"):
        op.drop_column(_TABLE, "transitions_json")
    if _has_column("steps_json"):
        op.drop_column(_TABLE, "steps_json")
