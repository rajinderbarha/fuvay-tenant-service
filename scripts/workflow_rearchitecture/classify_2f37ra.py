"""Slice 2F-37R-A Workstream 6 changed-path classifier.

Deterministic, rule-based classification of every path that differs between
the recovery base (4ce23c5) and the recovery snapshot (e0652e2). Reads three
already-captured inventories (all relative to repo root, from the original
G:/serviceos checkout):
  - all-changed-paths.txt      (git diff --name-only 4ce23c5 e0652e2)
  - modified-paths.txt         (git diff --name-status, base..worktree, M/D entries)
  - untracked-list.txt         (git ls-files --others --exclude-standard, at
                                 the time of the original preservation)

Zero UNKNOWN paths permitted; every path gets exactly one label.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

PRESERVE = Path("../serviceos-2f37r-preserve")

UNRELATED_FILES = {
    "alembic/versions/087_fix_master_data_audit_log_updated_at.py",
    "scripts/canonical_seed_final_l5_01.py",
    "app/engines/execution/my_work_router.py",
    "app/engines/execution/my_work_service.py",
}

UX05_PREFIXES = (
    "mobile/staff-app/",
    "docs/design/ux-05-staff-technician-app/",
)

UNRELATED_PREFIXES = (
    "mobile/customer-app/",
    "frontend/customer-app/",
    "docs/customer-app/",
    "e2e/docs/",
)
UNRELATED_TENANT_PORTAL_FILES_HINT = "frontend/tenant-portal/"  # needs per-file check below

# Files under frontend/tenant-portal confirmed (prior investigation) to be
# leftover MODULE-L5 fix work, not part of the 2F34-37 authorization program.
UNRELATED_TENANT_PORTAL_FILES = {
    "frontend/tenant-portal/app/(tenant)/catalog/page.tsx",
    "frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx",
    "frontend/tenant-portal/app/(tenant)/provider/service-areas/page.tsx",
    "frontend/tenant-portal/app/(tenant)/service-jobs/[id]/execution/page.tsx",
    "frontend/tenant-portal/app/staff/jobs/[job_id]/page.tsx",
    "frontend/tenant-portal/components/dashboard/MarketingLaunchWidget.tsx",
    "frontend/tenant-portal/components/layout/Breadcrumbs.tsx",
    "frontend/tenant-portal/components/layout/StaffLayout.tsx",
    "frontend/tenant-portal/components/layout/TenantLayout.tsx",
    "frontend/tenant-portal/lib/api.ts",
    "frontend/tenant-portal/playwright.config.ts",
    "frontend/customer-app/app/customer/reviews/page.tsx",
    "frontend/customer-app/lib/api/customer-reviews.ts",
}

GENERATED_SUFFIXES = (".tsbuildinfo", ".pyc", "package-lock.json")
GENERATED_PREFIXES = (
    "mobile/customer-app/.expo/",
    "mobile/customer-app/node_modules/",
    "__pycache__/",
)


def classify(path: str, modified_set: set[str]) -> str:
    if path in {".fullreg.txt", "bash.exe.stackdump", "frontend/tenant-portal/next-env.d.ts"}:
        return "GENERATED_OR_CACHE_FILE"
    if path in {
        "frontend/tenant-portal/app/staff/my-work/page.tsx",
        "frontend/tenant-portal/lib/api.persona.test.ts",
    }:
        return "UNRELATED_PRE_EXISTING_DIRTY_FILE"
    if any(seg in path for seg in ("/__pycache__/", ".pyc")):
        return "GENERATED_OR_CACHE_FILE"
    if any(path.startswith(p) for p in GENERATED_PREFIXES) or path.endswith(GENERATED_SUFFIXES):
        return "GENERATED_OR_CACHE_FILE"
    if path in UNRELATED_FILES or path in UNRELATED_TENANT_PORTAL_FILES:
        return "UNRELATED_PRE_EXISTING_DIRTY_FILE"
    if any(path.startswith(p) for p in UNRELATED_PREFIXES):
        return "UNRELATED_PRE_EXISTING_DIRTY_FILE"
    if any(path.startswith(p) for p in UX05_PREFIXES):
        return "UX05_FRONTEND"
    if path.startswith("mobile/") and "customer-app" not in path and "staff" not in path.lower():
        return "UNRELATED_PRE_EXISTING_DIRTY_FILE"

    if path.startswith("docs/workflow-rearchitecture/phase-02a-slice-02f34/"):
        return "SLICE_2F34_DOCUMENTATION"
    if path.startswith("docs/workflow-rearchitecture/phase-02a-slice-02f35/"):
        return "SLICE_2F35_DOCUMENTATION"
    if path.startswith("docs/workflow-rearchitecture/phase-02a-slice-02f36/"):
        return "SLICE_2F36_DOCUMENTATION"
    if path.startswith("docs/workflow-rearchitecture/phase-02a-slice-02f37/"):
        return "SLICE_2F37_DOCUMENTATION"
    if path.startswith("docs/workflow-rearchitecture/"):
        return "HISTORICAL_POINT_IN_TIME_ARTIFACT"

    if path.startswith("tests/test_phase2f"):
        is_new = path not in modified_set
        if "2f35" in path:
            return "SLICE_2F35_TEST"
        if "2f36" in path:
            return "SLICE_2F36_TEST"
        if "2f37" in path:
            return "SLICE_2F37_TEST"
        if not is_new:
            return "CURRENT_STATE_CANARY_UPDATE"
        return "HISTORICAL_POINT_IN_TIME_ARTIFACT"
    if path.startswith("tests/test_module_l5") or path.startswith("tests/test_sprint") or path.startswith("tests/test_step") or path in {
        "tests/test_checklist_system.py", "tests/test_customer_idor.py", "tests/test_job_type_flows.py",
        "tests/test_service_catalog.py", "tests/test_p0_job_completion_credit_deduction.py",
        "tests/test_tenant_service_coverage_enterprise_ui.py",
    }:
        return "UNRELATED_PRE_EXISTING_DIRTY_FILE"
    if path.startswith("tests/"):
        return "HISTORICAL_POINT_IN_TIME_ARTIFACT"

    if path.startswith("scripts/workflow_rearchitecture/"):
        if path.endswith("verify_2f35.py"):
            return "SLICE_2F35_APPLICATION"
        if path.endswith("verify_2f36.py"):
            return "SLICE_2F36_APPLICATION"
        if path.endswith("verify_2f37.py"):
            return "SLICE_2F37_APPLICATION"
        return "SHARED_AUTHORIZATION_INFRASTRUCTURE"

    if path == "alembic/versions/144_users_role_canonical_check.py":
        return "SHARED_AUTHORIZATION_INFRASTRUCTURE"
    if path.startswith("alembic/"):
        return "UNRELATED_PRE_EXISTING_DIRTY_FILE"

    if path.startswith("app/core/") or path.startswith("app/dependencies/") or path == "app/main.py":
        return "SHARED_AUTHORIZATION_INFRASTRUCTURE"
    if path.startswith("app/engines/"):
        return "SHARED_AUTHORIZATION_INFRASTRUCTURE"

    return "UNKNOWN"


def main() -> int:
    all_paths = (PRESERVE / "all-changed-paths.txt").read_text().splitlines()
    modified = set()
    mp = PRESERVE / "modified-backend-core.txt"
    for f in (PRESERVE / "modified-paths.txt",):
        for line in f.read_text().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] in ("M", "D"):
                modified.add(parts[-1])

    rows = []
    counts: dict[str, int] = {}
    unknown = []
    for p in all_paths:
        p = p.strip()
        if not p:
            continue
        label = classify(p, modified)
        rows.append((p, label))
        counts[label] = counts.get(label, 0) + 1
        if label == "UNKNOWN":
            unknown.append(p)

    out = PRESERVE / "changed-path-classification.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "classification"])
        w.writerows(rows)

    print(f"Total: {len(rows)}")
    for label, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {n}")
    if unknown:
        print(f"\nUNKNOWN ({len(unknown)}):")
        for u in unknown[:50]:
            print(f"  {u}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
