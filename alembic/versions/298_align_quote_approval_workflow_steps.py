"""Align quote-required workflow capability with cross-app steps.

Revision ID: 298
Revises: 297

The standard journey seeded by migration 275 omitted ``quote_required`` even
when the workflow's authoritative ``quote_approval_required`` flag was true.
Runtime correctly blocked work until approval, but every app skipped the gate
in its timeline. This data correction adds the missing state and replaces the
impossible direct inspection-to-work transition for affected current flows.
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op


revision = "298"
down_revision = "297"
branch_labels = None
depends_on = None


def _normalise(rows):
    for row in rows:
        steps = list(row.steps_json or [])
        mapped = {step.get("maps_to_status") for step in steps}
        if "quote_required" in mapped:
            continue

        insertion = next(
            (index + 1 for index, step in enumerate(steps) if step.get("maps_to_status") == "inspection_done"),
            len(steps),
        )
        steps.insert(insertion, {
            "step_key": "estimate_approval",
            "step_name": "Estimate approval",
            "maps_to_status": "quote_required",
            "owner_app": "customer_app",
            "owner_role": "customer",
            "customer_visible": True,
            "tenant_visible": True,
            "staff_visible": True,
            "admin_visible": True,
            "requires_note": False,
            "requires_photo": False,
            "requires_approval": True,
            "sla_minutes": None,
            "display_order": insertion + 1,
        })
        for order, step in enumerate(steps, start=1):
            step["display_order"] = order

        transitions = [
            transition for transition in list(row.transitions_json or [])
            if not (
                transition.get("from_step_key") == "inspection_done"
                and transition.get("to_step_key") == "work_started"
            )
        ]
        transitions.extend([
            {
                "from_step_key": "inspection_done", "to_step_key": "estimate_approval",
                "action_label": "Submit estimate", "allowed_role": "technician",
                "requires_reason": False, "triggers_notification": True, "auto_transition": False,
            },
            {
                "from_step_key": "estimate_approval", "to_step_key": "work_started",
                "action_label": "Approve estimate", "allowed_role": "customer",
                "requires_reason": False, "triggers_notification": True, "auto_transition": False,
            },
        ])
        yield row.id, steps, transitions


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("""
        SELECT id, steps_json, transitions_json
          FROM service_job_workflow
         WHERE is_current IS TRUE
           AND quote_approval_required IS TRUE
           AND NOT EXISTS (
               SELECT 1 FROM jsonb_array_elements(steps_json) AS step
                WHERE step->>'maps_to_status' = 'quote_required'
           )
    """)).fetchall()
    for workflow_id, steps, transitions in _normalise(rows):
        connection.execute(sa.text("""
            UPDATE service_job_workflow
               SET steps_json = CAST(:steps AS jsonb),
                   transitions_json = CAST(:transitions AS jsonb),
                   updated_at = now()
             WHERE id = :workflow_id
        """), {
            "workflow_id": workflow_id,
            "steps": json.dumps(steps),
            "transitions": json.dumps(transitions),
        })


def downgrade() -> None:
    # This is a correctness repair. Downgrading application code must not
    # silently reintroduce a journey that hides an enforced approval gate.
    pass
