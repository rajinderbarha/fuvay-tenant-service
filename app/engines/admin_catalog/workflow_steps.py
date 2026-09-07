"""Cross-app step choreography for `service_job_workflow` (migration 274).

Defines, validates and resolves the ordered step sequence a job runs through —
which app owns each step, who may act, and what each step demands.

The shape is ported from the step model migration 186 dropped along with
`workflow_templates`; that engine was the only place in this codebase that ever
expressed cross-app choreography, and the idea was worth keeping even though the
engine was not. It now lives on the one workflow authority instead of a fourth
table.

The join to reality is `maps_to_status`. A step either names a canonical
`service_jobs.status` — the same JOB_TRANSITIONS vocabulary the execution engine
enforces — or names none, for steps that sit outside the job's own lifecycle
(booking-level acceptance, post-completion review). Steps that map to a status
can be marked done from the job's real state; steps that don't are informational
and are never used to infer progress.

Nothing here invents a second state machine. `JOB_TRANSITIONS` remains the
authority on what job status changes are legal; a step sequence describes and
presents that journey per audience. Custom transition edges and allowed roles
constrain execution; photo/note/approval/SLA annotations are descriptive only.
Enforced evidence and approval belong to checklist and workflow capabilities.
"""
from __future__ import annotations

from typing import Any

from app.engines.execution.constants import JOB_TRANSITIONS

# Which app surface a step belongs to.
OWNER_APPS = {"customer_app", "tenant_app", "staff_app", "admin", "system"}

# Who may perform a step / take a transition.
OWNER_ROLES = {
    "customer", "tenant_owner", "tenant_manager", "technician",
    "platform_admin", "support_admin", "finance_admin", "system",
}

# Canonical job statuses a step may map to. Derived from the execution engine's
# own graph rather than restated, so the two can never drift: any status the
# execution engine knows about is addressable by a step, and nothing else is.
CANONICAL_JOB_STATUSES: set[str] = set(JOB_TRANSITIONS) | {
    target for targets in JOB_TRANSITIONS.values() for target in targets
}

_REQUIRED_STEP_KEYS = ("step_key", "step_name")


def validate_steps(steps: Any) -> list[dict]:
    """Validate and normalise a step list, or raise ValueError.

    Returned steps are ordered by `display_order` and renumbered from 1 so the
    stored order is always the presented order.
    """
    if not isinstance(steps, list):
        raise ValueError("steps must be a list.")
    seen_keys: set[str] = set()
    cleaned: list[dict] = []

    for i, raw in enumerate(steps):
        if not isinstance(raw, dict):
            raise ValueError(f"steps[{i}] must be an object.")
        for key in _REQUIRED_STEP_KEYS:
            if not str(raw.get(key) or "").strip():
                raise ValueError(f"steps[{i}].{key} is required.")

        step_key = str(raw["step_key"]).strip()
        if step_key in seen_keys:
            raise ValueError(f"Duplicate step_key '{step_key}'.")
        seen_keys.add(step_key)

        owner_app = str(raw.get("owner_app") or "staff_app")
        if owner_app not in OWNER_APPS:
            raise ValueError(f"steps[{i}].owner_app must be one of {sorted(OWNER_APPS)}.")
        owner_role = str(raw.get("owner_role") or "system")
        if owner_role not in OWNER_ROLES:
            raise ValueError(f"steps[{i}].owner_role must be one of {sorted(OWNER_ROLES)}.")

        maps_to = raw.get("maps_to_status") or None
        if maps_to is not None:
            maps_to = str(maps_to).strip()
            # Rejecting an unknown status here is the whole point of the field:
            # a typo'd status would produce a step that silently never completes.
            if maps_to not in CANONICAL_JOB_STATUSES:
                raise ValueError(
                    f"steps[{i}].maps_to_status '{maps_to}' is not a canonical job status. "
                    f"Use one of: {', '.join(sorted(CANONICAL_JOB_STATUSES))}, or omit it "
                    f"for a step outside the job lifecycle.")

        sla = raw.get("sla_minutes")
        if sla is not None and (isinstance(sla, bool) or not isinstance(sla, int) or sla <= 0):
            raise ValueError(f"steps[{i}].sla_minutes must be a positive whole number or null.")
        cleaned.append({
            "step_key": step_key,
            "step_name": str(raw["step_name"]).strip(),
            "maps_to_status": maps_to,
            "owner_app": owner_app,
            "owner_role": owner_role,
            "customer_visible": bool(raw.get("customer_visible", False)),
            "tenant_visible": bool(raw.get("tenant_visible", False)),
            "staff_visible": bool(raw.get("staff_visible", False)),
            "admin_visible": bool(raw.get("admin_visible", True)),
            "requires_note": bool(raw.get("requires_note", False)),
            "requires_photo": bool(raw.get("requires_photo", False)),
            "requires_approval": bool(raw.get("requires_approval", False)),
            "sla_minutes": sla,
            "display_order": int(raw.get("display_order", i + 1) or i + 1),
        })

    cleaned.sort(key=lambda s: s["display_order"])
    for position, step in enumerate(cleaned, start=1):
        step["display_order"] = position
    return cleaned


def validate_transitions(transitions: Any, steps: list[dict]) -> list[dict]:
    """Validate transitions against the step list, or raise ValueError."""
    if not isinstance(transitions, list):
        raise ValueError("transitions must be a list.")
    keys = {s["step_key"] for s in steps}
    cleaned: list[dict] = []

    for i, raw in enumerate(transitions):
        if not isinstance(raw, dict):
            raise ValueError(f"transitions[{i}] must be an object.")
        src = str(raw.get("from_step_key") or "").strip()
        dst = str(raw.get("to_step_key") or "").strip()
        # A transition naming a step that does not exist is the single most
        # common way a workflow silently dead-ends, so it is rejected outright
        # rather than stored and discovered at runtime.
        if src not in keys:
            raise ValueError(f"transitions[{i}].from_step_key '{src}' is not a defined step.")
        if dst not in keys:
            raise ValueError(f"transitions[{i}].to_step_key '{dst}' is not a defined step.")
        if src == dst:
            raise ValueError(f"transitions[{i}] cannot go from a step to itself.")

        role = str(raw.get("allowed_role") or "system")
        if role not in OWNER_ROLES:
            raise ValueError(f"transitions[{i}].allowed_role must be one of {sorted(OWNER_ROLES)}.")

        cleaned.append({
            "from_step_key": src,
            "to_step_key": dst,
            "action_label": str(raw.get("action_label") or "").strip() or None,
            "allowed_role": role,
            "requires_reason": bool(raw.get("requires_reason", False)),
            "triggers_notification": bool(raw.get("triggers_notification", False)),
            "auto_transition": bool(raw.get("auto_transition", False)),
        })
    return cleaned


def validate_workflow_steps(steps: Any, transitions: Any) -> tuple[list[dict], list[dict]]:
    """Validate a whole definition. Returns (steps, transitions)."""
    clean_steps = validate_steps(steps)
    clean_transitions = validate_transitions(transitions, clean_steps)
    review = check_definition(clean_steps, clean_transitions)
    if review["errors"]:
        raise ValueError(" ".join(review["errors"]))
    return clean_steps, clean_transitions


def check_definition(steps: list[dict], transitions: list[dict]) -> dict:
    """Review a definition, distinguishing publishing blockers from guidance."""
    errors: list[str] = []
    warnings: list[str] = []

    if not steps:
        if transitions:
            errors.append("Transitions require custom journey steps.")
        return {"valid": not errors, "errors": errors, "warnings": warnings}

    mapped = [s for s in steps if s["maps_to_status"]]
    if not mapped:
        warnings.append(
            "No step maps to a job status, so no step can ever be marked complete "
            "from the job's real state. The sequence will render but never progress.")

    duplicates = {s["maps_to_status"] for s in mapped
                  if [x["maps_to_status"] for x in mapped].count(s["maps_to_status"]) > 1}
    for status in sorted(duplicates):
        errors.append(f"More than one step maps to job status '{status}' — "
                        f"progress for that status is ambiguous.")

    for app in ("customer_app", "tenant_app", "staff_app"):
        if not any(s["owner_app"] == app for s in steps):
            warnings.append(f"No step is owned by {app}.")

    # A transition between two status-mapped steps that the execution engine
    # would refuse is a journey that can never actually run. The guard blocks it
    # at runtime anyway; saying so here means an admin finds out while authoring
    # rather than when a technician is standing in someone's kitchen.
    by_key = {s["step_key"]: s for s in steps}
    for t in transitions:
        src = by_key.get(t.get("from_step_key"), {}).get("maps_to_status")
        dst = by_key.get(t.get("to_step_key"), {}).get("maps_to_status")
        if not src or not dst or src == dst:
            continue
        if dst not in JOB_TRANSITIONS.get(src, set()):
            # ASCII arrow deliberately: this text is returned by the API and
            # written to logs, and a non-ASCII arrow raises UnicodeEncodeError
            # on any cp1252 console or log handler in the path.
            errors.append(
                f"\"{by_key[t['from_step_key']]['step_name']}\" -> "
                f"\"{by_key[t['to_step_key']]['step_name']}\" is not a job status change the "
                f"platform allows ({src} -> {dst}), so this transition can never fire.")

    # Steps nothing can reach, ignoring the first step which is the entry point.
    if transitions:
        reachable = {steps[0]["step_key"]}
        while True:
            expanded = reachable | {t["to_step_key"] for t in transitions if t["from_step_key"] in reachable}
            if expanded == reachable:
                break
            reachable = expanded
        for s in steps[1:]:
            if s["step_key"] not in reachable:
                warnings.append(f"Step '{s['step_name']}' is unreachable — no transition leads to it.")

    if any(s.get("requires_photo") or s.get("requires_note") or s.get("requires_approval") or s.get("sla_minutes") for s in steps):
        warnings.append("Journey photo/note/approval and SLA fields are descriptive only, not execution gates. Configure enforced evidence in Checklists and approval in Workflow settings.")
    if any(t.get("requires_reason") or t.get("triggers_notification") or t.get("auto_transition") for t in transitions):
        warnings.append("Journey reason, notification and auto-transition metadata does not trigger automation. Platform actions and notification rules remain authoritative.")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def check_capability_alignment(workflow: dict) -> list[str]:
    """Return hard coherence errors between workflow flags and its journey.

    Capability booleans are runtime gates, while ``steps_json`` is what every
    app renders. A required approval that has no visible status step produces
    a workflow that is enforced by the backend but invisible to customers,
    providers and technicians.
    """
    steps = list(workflow.get("steps_json") or workflow.get("steps") or [])
    if not steps:
        return []  # Optional custom journey: the standard runtime still enforces approval.
    mapped_statuses = {str(step.get("maps_to_status")) for step in steps if step.get("maps_to_status")}
    errors: list[str] = []
    if workflow.get("quote_approval_required") and "quote_required" not in mapped_statuses:
        errors.append(
            "Estimate approval is required, but the journey has no step mapped to 'quote_required'."
        )
    return errors


def steps_for_audience(steps: list[dict], audience: str) -> list[dict]:
    """The steps one app should show. `audience` is customer|tenant|staff|admin."""
    flag = {
        "customer": "customer_visible", "tenant": "tenant_visible",
        "staff": "staff_visible", "admin": "admin_visible",
    }.get(audience)
    if flag is None:
        raise ValueError("audience must be one of customer|tenant|staff|admin")
    return [s for s in steps if s.get(flag)]


def to_client_stages(annotated: list[dict]) -> list[dict]:
    """Render annotated steps in the shape client stage-trackers already expect.

    `state` is translated to the existing done/current/upcoming vocabulary the
    technician app's tracker already used, with `skipped` passed through — a
    stage the workflow bypassed is genuinely neither completed nor upcoming, and
    flattening it into either would misreport what happened on the job.
    """
    return [
        {
            "key": s.get("maps_to_status") or s["step_key"],
            "step_key": s["step_key"],
            "label": s["step_name"],
            "state": {"done": "completed", "current": "current",
                      "skipped": "skipped"}.get(s["state"], "upcoming"),
            "owner_app": s.get("owner_app"),
            "owner_role": s.get("owner_role"),
            "requires_photo": s.get("requires_photo", False),
            "requires_note": s.get("requires_note", False),
            "requires_approval": s.get("requires_approval", False),
            "sla_minutes": s.get("sla_minutes"),
            "completed_at": None,
        }
        for s in annotated
    ]


async def resolve_job_workflow_stages(db, job, audience: str) -> list[dict] | None:
    """The workflow steps one audience should see for one job, with progress.

    Shared by every client surface — technician app, tenant portal, customer app
    — so the three can never drift into showing different journeys for the same
    job. Each caller passes only its own audience.

    Resolution goes through `job.service_job_workflow_id`, the immutable snapshot
    taken at booking time, so publishing a new step sequence never rewrites the
    journey of a job already running.

    Returns None when the job's workflow defines no steps, which is the signal
    for a caller to fall back to whatever it rendered before — every workflow
    authored before migration 274 has an empty definition.
    """
    from sqlalchemy import select

    from app.engines.admin_catalog.models import ServiceJobWorkflow
    from app.engines.execution.models import ServiceJobExecutionEvent

    workflow_id = getattr(job, "service_job_workflow_id", None)
    if workflow_id is None:
        return None
    workflow = await db.get(ServiceJobWorkflow, workflow_id)
    steps = list(getattr(workflow, "steps_json", None) or []) if workflow else []
    if not steps:
        return None

    # The statuses this job has genuinely been in. Read from its real event
    # history rather than inferred from position, so a step the workflow skipped
    # is reported as skipped instead of silently shown as completed.
    reached = set((await db.execute(
        select(ServiceJobExecutionEvent.new_status).where(
            ServiceJobExecutionEvent.job_id == job.id,
            ServiceJobExecutionEvent.new_status.is_not(None),
        )
    )).scalars().all())
    if job.status:
        reached.add(job.status)

    # Annotate against the FULL sequence, then filter to the audience — never
    # the other way round. Progress depends on where the job sits in the whole
    # journey, and a step hidden from one audience is still part of it. Filtering
    # first made the current step invisible to that audience's own calculation,
    # so every later step looked passed-over: a customer whose job was mid
    # "Work Started" (an internal step they never see) was shown the following
    # step as "skipped" on a job that was actively progressing.
    return steps_for_audience(annotate_progress(steps, job.status, reached), audience)


def annotate_progress(steps: list[dict], current_status: str | None,
                      reached_statuses: set[str] | None = None) -> list[dict]:
    """Mark each step done / current / pending from the job's real state.

    `reached_statuses` is the set of statuses the job has actually been in
    (from its execution events). Passing it is strongly preferred to inferring
    from position: a job that skipped inspection because its workflow does not
    require one must not have "Inspection" shown as completed just because a
    later step is current.
    """
    reached = reached_statuses or set()
    out: list[dict] = []
    seen_current = False
    # A partial custom journey may omit the current runtime status. In that
    # case, future steps are still pending, not skipped.
    has_current = any(s.get("maps_to_status") == current_status and current_status
                      or s.get("step_key") == "provider_accepted" and current_status == "accepted"
                      for s in steps)
    for step in steps:
        status = step.get("maps_to_status")
        step_key = step.get("step_key")

        # These are real milestones but intentionally have no direct job
        # status in the admin workflow schema. Treating every status-less step
        # as pending made a newly accepted booking show "Booking Created" as
        # incomplete and "Technician Assigned" as skipped. A persisted job is
        # conclusive proof of booking creation; `accepted` is the provider
        # acceptance state owned by the assignment engine.
        if step_key == "booking_created":
            state = "done"
        elif step_key == "provider_accepted" and current_status == "accepted":
            state = "current"
            seen_current = True
        elif step_key == "provider_accepted" and (
            "accepted" in reached or current_status in {
                "assigned", "scheduled", "on_the_way", "reached_site",
                "inspection_started", "inspection_done", "quote_required",
                "service_started", "work_done", "completed",
            }
        ):
            state = "done"
        elif status and status == current_status:
            state = "current"
            seen_current = True
        elif status and status in reached:
            state = "done"
        elif status and has_current and not seen_current and current_status and status not in reached:
            # Before the current step but never actually reached — the workflow
            # skipped it. Say so rather than implying it was completed.
            state = "skipped"
        else:
            state = "pending"
        out.append({**step, "state": state})
    return out
