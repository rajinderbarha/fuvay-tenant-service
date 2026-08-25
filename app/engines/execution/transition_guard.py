"""One place that decides whether a job may move from one status to another.

Before this, three modules each did their own `JOB_TRANSITIONS.get(current)`
check — execution/home_service_service.py (raising 422),
quote_checklist/quote_service.py (raising ValueError) and
execution/admin_job_actions.py — and mobile_job_detail_service.py kept a fourth,
separate ordered copy of the same graph. Four places to keep in step is how a
graph drifts.

Two layers, in this order:

1. `JOB_TRANSITIONS` — the platform's fixed vocabulary of legal status moves.
   Unchanged and still absolute: no workflow can authorise a move the execution
   engine considers impossible.
2. The job's own workflow definition, when it has one. If both the current and
   target statuses correspond to steps in that workflow, the move must also be
   described by one of its transitions, and — when the caller supplies an actor
   role — that transition must permit that role.

Layer 2 only ever NARROWS what layer 1 allows, and only for jobs whose workflow
actually defines transitions. Every job created before migration 274, and every
job type with no journey authored, is unaffected: the workflow layer finds
nothing to say and defers.
"""
from __future__ import annotations

from app.engines.execution.constants import JOB_TRANSITIONS
from app.exceptions import ServiceOSException

ERR_INVALID_TRANSITION = "EXECUTION_INVALID_STATUS_TRANSITION"
ERR_WORKFLOW_FORBIDS = "EXECUTION_WORKFLOW_FORBIDS_TRANSITION"


def is_status_move_allowed(current: str | None, target: str) -> bool:
    """Layer 1 only — the platform graph. Pure, no I/O."""
    if current is None or current == target:
        return True
    return target in JOB_TRANSITIONS.get(current, set())


#: The execution engine calls every field-worker transition `actor_role="staff"`
#: (11 call sites in home_service_service.py), while workflow authors write the
#: same actor as `technician` in `allowed_role`. Those two words never compared
#: equal, so EVERY technician-authored step was unreachable: a real job sat in
#: `accepted` and "On The Way" answered `"On The Way" can only be performed by
#: technician.` to the technician it was assigned to. These are synonyms for one
#: actor; tenant_owner / tenant_manager stay distinct from them and from each
#: other.
_ACTOR_SYNONYMS: dict[str, set[str]] = {
    "staff":       {"staff", "technician", "field_staff"},
    "technician":  {"staff", "technician", "field_staff"},
    "field_staff": {"staff", "technician", "field_staff"},
}


def _actor_satisfies(actor_role: str, permitted: set[str | None]) -> bool:
    """True when `actor_role` meets any of the roles a transition permits."""
    accepted = _ACTOR_SYNONYMS.get(actor_role, {actor_role})
    return any(p in accepted for p in permitted if p)


async def workflow_verdict(db, job, target: str, actor_role: str | None = None) -> tuple[bool, str | None]:
    """Layer 2. Returns (allowed, reason_if_not).

    Defers — returns (True, None) — whenever the workflow has nothing to say:
    no snapshot, no steps, no transitions, or a status that no step represents.
    Silence must mean permission here, or authoring a partial journey would
    start blocking real work.
    """
    # A move to the status the job is already in is a no-op, which layer 1
    # permits; the workflow must agree rather than reject it for lacking a
    # self-transition nobody would author.
    if job.status == target:
        return True, None

    workflow_id = getattr(job, "service_job_workflow_id", None)
    if workflow_id is None:
        return True, None

    from app.engines.admin_catalog.models import ServiceJobWorkflow

    workflow = await db.get(ServiceJobWorkflow, workflow_id)
    if workflow is None:
        return True, None
    steps = list(workflow.steps_json or [])
    transitions = list(workflow.transitions_json or [])
    if not steps or not transitions:
        return True, None

    by_status: dict[str, dict] = {}
    for step in steps:
        status = step.get("maps_to_status")
        if status and status not in by_status:
            by_status[status] = step

    from_step = by_status.get(job.status)
    to_step = by_status.get(target)
    # A move into or out of a status this journey never describes is outside the
    # workflow's remit — the platform graph already vetted it.
    if from_step is None or to_step is None:
        return True, None

    matching = [t for t in transitions
                if t.get("from_step_key") == from_step.get("step_key")
                and t.get("to_step_key") == to_step.get("step_key")]
    if not matching:
        return False, (f"This job's workflow does not allow moving from "
                       f"\"{from_step.get('step_name')}\" to \"{to_step.get('step_name')}\".")

    if actor_role is not None:
        permitted = {t.get("allowed_role") for t in matching}
        # "system" is the platform acting on its own behalf and is never blocked
        # by a role rule authored for humans.
        if actor_role != "system" and permitted and not _actor_satisfies(actor_role, permitted):
            return False, (f"\"{to_step.get('step_name')}\" can only be performed by "
                           f"{', '.join(sorted(r for r in permitted if r))}.")
    return True, None


async def assert_transition_allowed(db, job, target: str, actor_role: str | None = None) -> None:
    """Raise unless `job` may move to `target`. The single enforcement point."""
    if not is_status_move_allowed(job.status, target):
        raise ServiceOSException(
            ERR_INVALID_TRANSITION,
            f"This job cannot move from {job.status} to {target} directly.",
            status_code=422,
        )
    allowed, reason = await workflow_verdict(db, job, target, actor_role)
    if not allowed:
        raise ServiceOSException(ERR_WORKFLOW_FORBIDS, reason or "Not permitted by this job's workflow.",
                                 status_code=422)
