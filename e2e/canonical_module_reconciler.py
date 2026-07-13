"""
MODULE-L5-00A: canonical business-module reconciliation.

Converts the 68 real app/engines/* directories (already inventoried by
module_inventory_scan.py) into canonical BUSINESS modules. Engine-to-module
grouping is domain knowledge (business purpose), not something a naive
string/import scanner can derive -- so it is an explicit, reviewable mapping
table below, cross-checked against each engine's real per-engine evidence
(router/model/endpoint presence) already captured in 03-module-registry.json.

Every engine not explicitly listed below is a hard failure (fail-closed):
this script refuses to silently classify an unmapped engine as anything.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(ROOT, "docs", "module-l5", "03-module-registry.json")

# Canonical business modules, per the mission's own recommended domain list
# (Part 25), refined against actual repository evidence.
CANONICAL_MODULES = {
    "identity_access": {
        "name": "Identity and Access",
        "engines": ["auth", "roles_permissions", "security", "profile"],
    },
    "tenant_onboarding": {
        "name": "Tenant Onboarding and Verification",
        "engines": ["tenant_engine", "public_registration"],
    },
    "geography_serviceability": {
        "name": "Geography and Serviceability",
        "engines": ["geo", "location_engine", "serviceability"],
    },
    "catalog_offerings": {
        "name": "Catalog and Offerings",
        "engines": ["service_catalog", "admin_catalog", "vertical_catalog", "brands", "service_setup"],
    },
    "pricing_bargain": {
        "name": "Pricing and Bargain",
        "engines": ["pricing"],
    },
    "provider_staff_availability": {
        "name": "Provider, Staff and Availability",
        "engines": ["provider_portal", "field_ops", "dispatch"],
    },
    "packages_credits_deposits": {
        "name": "Packages, Credits and Security Deposit",
        "engines": ["package_commerce", "usage_credits", "customer_credits", "entitlement", "subscription"],
    },
    "booking_matching_scheduling": {
        "name": "Booking, Matching and Scheduling",
        "engines": ["booking", "appointment", "home_service_booking", "coaching_appointment"],
    },
    "job_lifecycle": {
        "name": "Job Lifecycle",
        "engines": ["execution", "quote_checklist", "final_records", "home_service_assignment", "inventory"],
    },
    "finance_ledger_commission": {
        "name": "Finance, Ledger, Invoice and Commission",
        "engines": ["finance_hub", "invoice_payment", "payment", "platform_commerce"],
    },
    "notifications_audit_workers": {
        "name": "Notifications, Audit, Workers and Cron",
        "engines": ["notification", "platform_notifications", "workflows"],
    },
    "reviews_rewards_disputes": {
        "name": "Reviews, Rewards, Badges, Health and Disputes",
        "engines": ["review", "customer_reviews", "loyalty", "trust_quality", "complaints"],
    },
    "compliance_security_ops": {
        "name": "Compliance and Security Operations",
        "engines": ["compliance"],
    },
    "media_storage_exports": {
        "name": "Media, Storage and Exports",
        "engines": ["media", "document", "enterprise_grid"],
    },
    "system_configuration": {
        "name": "System Configuration and Platform Health",
        "engines": ["settings_engine", "engine_mgmt", "dashboard_command_center"],
    },
    "marketing_leads": {
        "name": "Marketing and Lead Generation",
        "engines": ["marketing", "marketing_automation", "marketing_command_center", "leads", "real_estate_lead", "promo"],
    },
    "vertical_extensions": {
        "name": "Vertical-Specific Extensions (Real Estate, Food, AI Conversation Flows)",
        "engines": ["real_estate", "food", "customer_flow"],
    },
}

# Shared/cross-cutting infrastructure -- deliberately not "owned" by one
# business module; consumed by many.
SHARED_INFRASTRUCTURE = ["analytics", "data_science", "rag", "chat", "ai_chat", "ai_conversation", "webhook"]

# Duplicate/orphaned scaffolds with an explicit, evidence-based disposition
# (see MODULE-L5-00's gap register and this sprint's 00a-vertical-billing-disposition.md).
DUPLICATE_SCAFFOLDS = {
    "vertical_billing": {
        "canonical_replacement": "platform_commerce",
        "disposition": "DEPRECATE_AND_MIGRATE",
        "reason": "Orphaned scaffold; real VerticalBillingConfig implementation lives entirely in platform_commerce (billing_constants.py, billing_models.py, billing_router.py). No router or model of its own.",
    },
}


def load_engine_evidence():
    data = json.load(open(REGISTRY_PATH, encoding="utf-8"))
    return {m["module_id"]: m for m in data["modules"]}


def main():
    evidence = load_engine_evidence()
    all_engines = set(evidence.keys())

    mapped_engines = set()
    for mod in CANONICAL_MODULES.values():
        mapped_engines.update(mod["engines"])
    mapped_engines.update(SHARED_INFRASTRUCTURE)
    mapped_engines.update(DUPLICATE_SCAFFOLDS.keys())

    unmapped = sorted(all_engines - mapped_engines)
    unexpected = sorted(mapped_engines - all_engines)  # mapping references an engine that no longer exists

    engine_classification = []
    for name in sorted(all_engines):
        ev = evidence[name]
        if name in DUPLICATE_SCAFFOLDS:
            status = "DUPLICATE_SCAFFOLD"
            module = None
            disposition = DUPLICATE_SCAFFOLDS[name]
        elif name in SHARED_INFRASTRUCTURE:
            status = "SHARED_INFRASTRUCTURE"
            module = None
            disposition = None
        else:
            module = next((mid for mid, m in CANONICAL_MODULES.items() if name in m["engines"]), None)
            if module is None:
                status = "UNKNOWN"
            elif len(CANONICAL_MODULES[module]["engines"]) == 1:
                status = "CANONICAL_MODULE_ROOT"
            else:
                status = "MODULE_SUBCOMPONENT"
            disposition = None
        engine_classification.append({
            "engine": name,
            "canonical_module": module,
            "status": status,
            "endpoint_count": ev["endpoint_count"],
            "has_models": ev["has_models"],
            "disposition": disposition,
        })

    canonical_modules_out = {}
    for mid, mod in CANONICAL_MODULES.items():
        total_endpoints = sum(evidence[e]["endpoint_count"] for e in mod["engines"] if e in evidence)
        canonical_modules_out[mid] = {
            "name": mod["name"],
            "engines": mod["engines"],
            "total_endpoints": total_endpoints,
        }

    result = {
        "canonical_modules_total": len(CANONICAL_MODULES),
        "engines_total": len(all_engines),
        "engines_mapped_to_canonical_module": sum(1 for e in engine_classification if e["canonical_module"]),
        "engines_shared_infrastructure": len(SHARED_INFRASTRUCTURE),
        "engines_duplicate_scaffold": len(DUPLICATE_SCAFFOLDS),
        "engines_unmapped": unmapped,
        "mapping_references_nonexistent_engine": unexpected,
        "canonical_modules": canonical_modules_out,
        "engine_classification": engine_classification,
    }

    out_dir = os.path.join(ROOT, "docs", "module-l5")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "canonical-modules.json"), "w", encoding="utf-8") as f:
        json.dump({"canonical_modules": canonical_modules_out, "shared_infrastructure": SHARED_INFRASTRUCTURE, "duplicate_scaffolds": DUPLICATE_SCAFFOLDS}, f, indent=2)
    with open(os.path.join(out_dir, "engine-classification.json"), "w", encoding="utf-8") as f:
        json.dump(engine_classification, f, indent=2)

    summary = {
        "canonical_modules_total": result["canonical_modules_total"],
        "engines_total": result["engines_total"],
        "engines_mapped_to_canonical_module": result["engines_mapped_to_canonical_module"],
        "engines_shared_infrastructure": result["engines_shared_infrastructure"],
        "engines_duplicate_scaffold": result["engines_duplicate_scaffold"],
        "engines_unmapped": unmapped,
        "mapping_references_nonexistent_engine": unexpected,
    }
    print(json.dumps(summary, indent=2))
    return 0 if not unmapped and not unexpected else 1


if __name__ == "__main__":
    raise SystemExit(main())
