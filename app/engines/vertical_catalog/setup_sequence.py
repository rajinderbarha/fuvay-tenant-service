"""Shared onboarding prerequisite order; completed steps remain editable."""
STEPS = [
    ("BUSINESS_PROFILE", "business-profile"), ("DOCUMENTS", "documents"),
    ("SERVICES_PRICING", "services-pricing"), ("TECHNICIAN_PLAN", "plan"),
    ("STAFF_TECHNICIANS", "staff"), ("COVERAGE_AVAILABILITY", "coverage-availability"),
    ("FINANCE_READINESS", "finance"), ("REVIEW_SUBMIT", "review"),
]


def prerequisite(sections: list[dict], target: str) -> dict | None:
    by_key = {s["key"]: s for s in sections}
    for key, slug in STEPS:
        if key == target:
            return None
        section = by_key.get(key, {})
        if section.get("status") != "complete":
            return {"key": key, "label": section.get("label", key.replace("_", " ").title()),
                    "route": f"/tenant/home-services/setup/{slug}"}
    raise ValueError(f"Unknown setup section: {target}")


def mutation_step(path: str, method: str) -> str | None:
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if path.startswith("/v1/tenant/home-services/setup/documents"):
        return "DOCUMENTS"
    if path.startswith("/v1/tenant/catalog/"):
        return "SERVICES_PRICING"
    if path == "/v1/tenant/home-services/activation/funding/order":
        return "TECHNICIAN_PLAN"
    if path.startswith("/v1/provider/team-members"):
        return "STAFF_TECHNICIANS"
    if path.startswith(("/v1/provider/availability", "/v1/provider/booking-window",
                        "/v1/provider/service-areas", "/v1/tenant/service-areas")):
        return "COVERAGE_AVAILABILITY"
    if path.startswith("/v1/tenant/home-services/setup/finance"):
        return "FINANCE_READINESS"
    if path in {"/v1/tenant/home-services/setup/submit", "/v1/tenant/home-services/setup/declarations"}:
        return "REVIEW_SUBMIT"
    return None
