"""
MODULE-L5-00: source-derived enterprise module inventory scanner.

Produces docs/module-l5/03-module-registry.json by directly inspecting the
repository -- not a hand-typed duplicate of engine names. For every
app/engines/<name> directory, records real, checkable evidence:
  - whether it exports an APIRouter and how many endpoints it declares
  - whether it has model files (__tablename__ definitions)
  - whether a matching tests/ file exists (name-substring heuristic --
    explicitly caveated as approximate, not authoritative)
  - whether super-admin / tenant-portal frontend routes reference it by
    directory-name substring (same caveat)

This is intentionally a first-pass, directory-level scan appropriate for an
L00 inventory gate -- NOT a deep per-module layer-matrix certification,
which is explicitly out of scope for this sprint and belongs in each
module's future MODULE-[ID]-L1..L5 sprints.
"""
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINES_DIR = os.path.join(ROOT, "app", "engines")
TESTS_DIR = os.path.join(ROOT, "tests")
FRONTENDS = {
    "super_admin": os.path.join(ROOT, "frontend", "super-admin", "app"),
    "tenant_portal": os.path.join(ROOT, "frontend", "tenant-portal", "app"),
}


def count_endpoints(engine_path):
    total = 0
    router_files = []
    for dirpath, _, filenames in os.walk(engine_path):
        if "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                text = open(fp, encoding="utf-8").read()
            except Exception:
                continue
            if "APIRouter(" in text:
                router_files.append(os.path.relpath(fp, ROOT))
            # MODULE-L5-00 fix: router variables are not always named
            # `router` (e.g. `admin_complaint_router`, `admin_cpolicy_router`)
            # -- match any identifier immediately preceding .get/.post/etc,
            # not just the literal name `router`.
            total += len(re.findall(r"@[a-zA-Z_][a-zA-Z0-9_]*\.(get|post|put|patch|delete)\(", text))
    return router_files, total


def has_models(engine_path):
    for dirpath, _, filenames in os.walk(engine_path):
        if "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fp = os.path.join(dirpath, fn)
                try:
                    if "__tablename__" in open(fp, encoding="utf-8").read():
                        return True
                except Exception:
                    pass
    return False


def matching_test_files(name):
    if not os.path.isdir(TESTS_DIR):
        return []
    return [f for f in os.listdir(TESTS_DIR) if name in f and f.endswith(".py")]


def matching_frontend_routes(name, frontend_root):
    if not os.path.isdir(frontend_root):
        return 0
    count = 0
    key = name.replace("_", "")
    for dirpath, _, filenames in os.walk(frontend_root):
        if key in dirpath.replace("_", "").replace("-", "").lower():
            count += filenames.count("page.tsx")
    return count


def classify(router_files, endpoint_count, model_present, test_files, fe_super, fe_tenant):
    if not router_files and not model_present:
        return "UNKNOWN"
    if not router_files:
        return "MODELS_ONLY_NO_ROUTER"
    if endpoint_count == 0:
        return "ROUTER_PRESENT_NO_ENDPOINTS"
    has_fe = (fe_super + fe_tenant) > 0
    has_tests = len(test_files) > 0
    if has_fe and has_tests:
        return "COMPLETE_PROVISIONAL"
    if has_fe and not has_tests:
        return "PARTIAL_UNTESTED"
    if has_tests and not has_fe:
        return "BACKEND_ONLY_CANDIDATE"
    return "PARTIAL_NO_UI_NO_TEST_MATCH"


def main():
    entries = []
    for name in sorted(os.listdir(ENGINES_DIR)):
        full = os.path.join(ENGINES_DIR, name)
        if not os.path.isdir(full) or name == "__pycache__":
            continue
        router_files, endpoint_count = count_endpoints(full)
        model_present = has_models(full)
        test_files = matching_test_files(name)
        fe_super = matching_frontend_routes(name, FRONTENDS["super_admin"])
        fe_tenant = matching_frontend_routes(name, FRONTENDS["tenant_portal"])
        status = classify(router_files, endpoint_count, model_present, test_files, fe_super, fe_tenant)
        entries.append({
            "module_id": name,
            "router_files": router_files,
            "endpoint_count": endpoint_count,
            "has_models": model_present,
            "matching_test_files": test_files,
            "frontend_route_hits_super_admin": fe_super,
            "frontend_route_hits_tenant_portal": fe_tenant,
            "status_firstpass": status,
        })

    unknown = [e for e in entries if e["status_firstpass"] == "UNKNOWN"]
    summary = {
        "total_modules": len(entries),
        "status_counts": {},
        "unknown_modules": [e["module_id"] for e in unknown],
    }
    for e in entries:
        summary["status_counts"][e["status_firstpass"]] = summary["status_counts"].get(e["status_firstpass"], 0) + 1

    out = {"summary": summary, "modules": entries}
    out_path = os.path.join(ROOT, "docs", "module-l5", "03-module-registry.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
