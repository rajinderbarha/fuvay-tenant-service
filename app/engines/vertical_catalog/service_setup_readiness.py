"""Service configuration progress, distinct from later operational readiness."""
LATER_STEP_ERRORS = {"MISSING_SERVICE_AREA", "MISSING_BUSINESS_HOURS"}


def service_setup_readiness(validations: list[tuple[str, dict]]) -> dict:
    configured = 0
    blockers = []
    for service_id, validation in validations:
        errors = [error for error in validation["errors"]
                  if error.get("code") not in LATER_STEP_ERRORS]
        configured += not errors
        blockers.extend({**error, "tenant_service_id": service_id} for error in errors)
    total = len(validations)
    if not total:
        blockers.append({"code": "NO_ENABLED_SERVICE", "message": "Choose and configure at least one service."})
    complete = bool(total) and configured == total
    return {"configured_count": configured, "enabled_count": total,
            "percentage": 100 if complete else min(99, round(configured / total * 100)) if total else 0,
            "blocking_reasons": blockers, "complete": complete}
