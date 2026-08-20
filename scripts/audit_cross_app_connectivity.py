"""Cross-app connectivity audit — super-admin, tenant-portal, customer-app, staff-app.

Run with the API up:
    python scripts/audit_cross_app_connectivity.py audit.json
    python scripts/audit_triage_dead_calls.py audit.json

Buckets, and why the third exists:
  DEAD     — the client calls a path the backend does not serve. A broken feature.
  SUSPECT  — the exact path is not served but a PARENT is. Ambiguous by
             construction: `/path${qs}` (a query string) is fine, `/path/${id}`
             (a real path param) is broken, and they normalise identically.
             PUT/DELETE /v1/admin/pricing-rules/{id} hid here — both unrouted
             while the whole workspace could only list. Always review this bucket.
  ORPHAN   — a served route no client calls. Dead backend surface, or a route
             only reached by a mobile app this script cannot see.

Known limitation: paths are compared, not HTTP methods, so a path served for GET
but called with POST reads as served. Treat the counts as a floor.
"""

import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path("g:/serviceos")

APPS = {
    "super-admin":  ROOT / "frontend/super-admin",
    "tenant-portal": ROOT / "frontend/tenant-portal",
    "customer-app": ROOT / "mobile/customer-app/src",
    "staff-app":    ROOT / "mobile/staff-app/src",
}

# Matches any string/template literal that looks like an API path.
PATH_RE = re.compile(r"""["'`](/v1/[^"'`\s]*)["'`]""")
# The HTTP method, when it is declared close by.
METHOD_RE = re.compile(r"""method\s*:\s*["'](\w+)["']""")


def normalise(p: str) -> str:
    p = p.split("?")[0].rstrip("/")
    p = re.sub(r"\$\{[^}]*\}", "{p}", p)      # ${jobId} -> {p}
    p = re.sub(r"\{[^}]*\}", "{p}", p)        # {job_id} -> {p}
    p = re.sub(r"/\+\s*", "/", p)
    return p


def candidates(p: str) -> list[str]:
    """Forms a called path might legitimately take.

    A template like `/path${qs}` builds a QUERY STRING, not a path segment, but
    it normalises to `/path{p}` and would otherwise be reported dead. So a path
    is considered matched if it matches with its trailing `{p}` groups stripped
    too. Without this the report is dominated by false positives and is useless.
    """
    forms = {p}
    cur = p
    while cur.endswith("{p}"):
        cur = cur[: -len("{p}")].rstrip("/")
        if cur:
            forms.add(cur)
    return sorted(forms)


def collect_calls(app_dir: Path) -> dict[str, set[str]]:
    """{normalised_path: {files that call it}}"""
    out: dict[str, set[str]] = defaultdict(set)
    if not app_dir.exists():
        return out
    for f in app_dir.rglob("*.ts*"):
        s = str(f)
        if "node_modules" in s or "/.next/" in s or "\\.next\\" in s or "__tests__" in s:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in PATH_RE.finditer(text):
            raw = m.group(1)
            if len(raw) < 4:
                continue
            # `/v1/provider/service-jobs/*` and friends appear in docstrings and
            # comments describing a route GROUP, never as a real call.
            if "*" in raw:
                continue
            out[normalise(raw)].add(str(f.relative_to(ROOT)))
    return out


def main():
    spec = json.loads(urllib.request.urlopen(
        "http://127.0.0.1:8000/openapi.json", timeout=120).read())
    served = {normalise(p) for p in spec["paths"]}
    served_raw = sorted(spec["paths"])

    print(f"backend serves {len(served_raw)} routes ({len(served)} after param-normalising)\n")

    all_called: set[str] = set()
    report: dict[str, dict] = {}

    for app, d in APPS.items():
        calls = collect_calls(d)
        all_called |= set(calls)
        # Exact match is the only safe "served" verdict. Matching only AFTER
        # stripping a trailing {p} is ambiguous: it is right for `/path${qs}`
        # (a query string) and WRONG for `/path/${id}` (a real path param).
        # PUT/DELETE /v1/admin/pricing-rules/{id} hid in that gap — both were
        # unrouted while the audit called them served. So they get their own
        # bucket instead of being silently absolved.
        dead = {p: f for p, f in calls.items() if p not in served
                and not any(c in served for c in candidates(p))}
        suspect = {p: f for p, f in calls.items() if p not in served
                   and any(c in served for c in candidates(p))}
        report[app] = {"total": len(calls), "dead": dead, "suspect": suspect}
        print(f"=== {app} ===")
        print(f"  distinct API paths called : {len(calls)}")
        print(f"  DEAD (not served)         : {len(dead)}")
        print(f"  SUSPECT (parent served,   : {len(suspect)}")
        print(f"           this exact path not)")
        for p in sorted(dead)[:25]:
            files = sorted(dead[p])[:2]
            print(f"    DEAD  {p}")
            for fl in files:
                print(f"            {fl}")
        if len(dead) > 25:
            print(f"    … and {len(dead) - 25} more")
        print()

    called_forms = set()
    for p in all_called:
        called_forms |= set(candidates(p))
    orphans = sorted(p for p in served if p not in called_forms)
    print(f"=== ORPHAN ROUTES (served, no client calls them): {len(orphans)} ===")
    # Group by engine prefix so the output is readable.
    by_prefix = defaultdict(list)
    for p in orphans:
        parts = p.strip("/").split("/")
        by_prefix["/".join(parts[:3])].append(p)
    for prefix in sorted(by_prefix, key=lambda k: -len(by_prefix[k]))[:20]:
        print(f"  {len(by_prefix[prefix]):>3}  /{prefix}/…")

    Path(sys.argv[1] if len(sys.argv) > 1 else "audit.json").write_text(
        json.dumps({
            "served": served_raw,
            "dead": {a: sorted(r["dead"]) for a, r in report.items()},
            "suspect": {a: sorted(r["suspect"]) for a, r in report.items()},
            "dead_detail": {a: {p: sorted(f) for p, f in r["dead"].items()}
                            for a, r in report.items()},
            "orphans": orphans,
        }, indent=1), encoding="utf-8")
    print("\nwrote audit json")


main()
