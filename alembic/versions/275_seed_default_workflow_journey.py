"""Seed the standard cross-app journey onto existing job-type workflows.

Migration 274 gave `service_job_workflow` a step definition but left every row
empty, so every job kept using the platform's fixed fallback sequence. This
gives each CURRENT workflow row a real journey, so the feature is usable without
an admin having to author one from scratch first.

The sequence is the Home Services repair journey ported from the step model
migration 186 dropped — the only place this codebase ever described who does
what in which app — with each step mapped to the canonical `service_jobs.status`
it represents. Steps outside the job's own lifecycle (booking acceptance, the
post-completion review request) carry no status, by design.

Only rows that currently have NO steps are touched, and only `is_current` ones,
so a workflow an admin has already authored is never overwritten. Transitions
follow the platform's own JOB_TRANSITIONS graph exactly — a transition it would
refuse can never fire, so seeding one would be seeding a dead end.

Revision ID: 275
Revises: 274
"""
import json

from alembic import op
import sqlalchemy as sa


revision = "275"
down_revision = "274"
branch_labels = None
depends_on = None


def _step(key, name, status, app, role, *, customer=False, tenant=False, staff=False,
          photo=False, note=False, approval=False, sla=None, order=1):
    return {
        "step_key": key, "step_name": name, "maps_to_status": status,
        "owner_app": app, "owner_role": role,
        "customer_visible": customer, "tenant_visible": tenant,
        "staff_visible": staff, "admin_visible": True,
        "requires_note": note, "requires_photo": photo, "requires_approval": approval,
        "sla_minutes": sla, "display_order": order,
    }


STEPS = [
    _step("booking_created", "Booking Created", None, "customer_app", "customer",
          customer=True, order=1),
    _step("provider_accepted", "Provider Accepted", None, "tenant_app", "tenant_owner",
          customer=True, tenant=True, sla=30, order=2),
    _step("technician_assigned", "Technician Assigned", "assigned", "tenant_app", "tenant_manager",
          customer=True, tenant=True, staff=True, order=3),
    _step("technician_accepted", "Technician Accepted", "accepted", "staff_app", "technician",
          tenant=True, staff=True, order=4),
    _step("on_the_way", "On The Way", "on_the_way", "staff_app", "technician",
          customer=True, tenant=True, staff=True, order=5),
    _step("arrived", "Arrived", "reached_site", "staff_app", "technician",
          customer=True, tenant=True, staff=True, order=6),
    # reached_site can only lead to inspection_started in the platform graph,
    # so the journey goes through inspection rather than jumping to work.
    _step("inspection_started", "Inspection", "inspection_started", "staff_app", "technician",
          tenant=True, staff=True, order=7),
    _step("inspection_done", "Inspection Complete", "inspection_done", "staff_app", "technician",
          tenant=True, staff=True, note=True, order=8),
    # Internal working state: the provider needs it, the customer does not.
    _step("work_started", "Work Started", "service_started", "staff_app", "technician",
          tenant=True, staff=True, order=9),
    _step("work_completed", "Work Completed", "work_done", "staff_app", "technician",
          customer=True, tenant=True, staff=True, photo=True, note=True, order=10),
    _step("job_completed", "Job Completed", "completed", "system", "system",
          customer=True, tenant=True, staff=True, order=11),
    _step("review_requested", "Review Requested", None, "customer_app", "customer",
          customer=True, order=12),
]

# Every status pair below is an edge the execution engine's JOB_TRANSITIONS
# graph already permits (assigned -> accepted -> on_the_way -> reached_site ->
# service_started -> work_done -> completed). Pairs whose steps carry no status
# are outside that graph and are unconstrained by it.
TRANSITIONS = [
    {"from_step_key": "booking_created", "to_step_key": "provider_accepted",
     "action_label": "Accept Booking", "allowed_role": "tenant_owner",
     "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    {"from_step_key": "provider_accepted", "to_step_key": "technician_assigned",
     "action_label": "Assign Technician", "allowed_role": "tenant_manager",
     "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    {"from_step_key": "technician_assigned", "to_step_key": "technician_accepted",
     "action_label": "Accept Job", "allowed_role": "technician",
     "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "technician_accepted", "to_step_key": "on_the_way",
     "action_label": "Start Travel", "allowed_role": "technician",
     "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    {"from_step_key": "on_the_way", "to_step_key": "arrived",
     "action_label": "Mark Arrived", "allowed_role": "technician",
     "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "arrived", "to_step_key": "inspection_started",
     "action_label": "Start Inspection", "allowed_role": "technician",
     "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "inspection_started", "to_step_key": "inspection_done",
     "action_label": "Finish Inspection", "allowed_role": "technician",
     "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "inspection_done", "to_step_key": "work_started",
     "action_label": "Start Work", "allowed_role": "technician",
     "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "work_started", "to_step_key": "work_completed",
     "action_label": "Complete Work", "allowed_role": "technician",
     "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    {"from_step_key": "work_completed", "to_step_key": "job_completed",
     "action_label": "Close Job", "allowed_role": "system",
     "requires_reason": False, "triggers_notification": True, "auto_transition": True},
    {"from_step_key": "job_completed", "to_step_key": "review_requested",
     "action_label": "Request Review", "allowed_role": "system",
     "requires_reason": False, "triggers_notification": True, "auto_transition": True},
]


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        UPDATE service_job_workflow
           SET steps_json = CAST(:steps AS jsonb),
               transitions_json = CAST(:transitions AS jsonb),
               updated_at = now()
         WHERE is_current IS TRUE
           AND COALESCE(jsonb_array_length(steps_json), 0) = 0
    """), {"steps": json.dumps(STEPS), "transitions": json.dumps(TRANSITIONS)})
    print(f"[275] seeded the standard journey onto {result.rowcount or 0} workflow row(s)")


def downgrade() -> None:
    # Clears only journeys identical to the seeded one, so an admin's own
    # authoring is never destroyed by a downgrade.
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE service_job_workflow
           SET steps_json = '[]'::jsonb, transitions_json = '[]'::jsonb
         WHERE steps_json = CAST(:steps AS jsonb)
    """), {"steps": json.dumps(STEPS)})
