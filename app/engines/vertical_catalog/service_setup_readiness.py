"""Service configuration progress, distinct from later operational readiness."""
LATER_STEP_ERRORS = {"MISSING_SERVICE_AREA", "MISSING_BUSINESS_HOURS"}


def service_setup_readiness(validations: list[tuple[str, dict]]) -> dict:
    configured = 0
    blockers = []
    for service_id, validation in validations:
        errors = [error for error in validation["errors"]
                  if error.get("code") not in LATER_STEP_ERRORS]
        configured += not errors
        name = validation.get("service_name")
        job_type = validation.get("job_type")
        label = f"{name} ({job_type})" if name and job_type else name
        blockers.extend({**error, "tenant_service_id": service_id,
                         "message": f"{label}: {error.get('message', error.get('code'))}" if label else error.get("message", error.get("code"))}
                        for error in errors)
    total = len(validations)
    if not total:
        blockers.append({"code": "NO_ENABLED_SERVICE", "message": "Choose and configure at least one service."})
    complete = bool(total) and configured == total
    return {"configured_count": configured, "enabled_count": total,
            "percentage": 100 if complete else min(99, round(configured / total * 100)) if total else 0,
            "blocking_reasons": blockers, "complete": complete}
