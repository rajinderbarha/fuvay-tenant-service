"""
MODULE-L5-01B: privileged-router authorization guard (router-scoped, not
file-scoped).

MODULE-L5-01A's first version of this guard flagged an entire FILE as
exposed if it contained >=1 bare-auth handler anywhere, even when that
file also contained legitimately-scoped role routers (e.g.
`execution/real_estate_router.py` mixes a `/v1/staff/...` router that
correctly scopes by the caller's own `tenant_id`, with a `/v1/admin/...`
router that does not). That imprecision would have made this sprint's fix
of the genuinely-privileged `admin_router` sub-router indistinguishable
from the untouched, already-safe `agent_router`/`provider_router`/
`customer_router` in the same file.

This version parses each file's `APIRouter(prefix=...)` assignments,
builds a router-variable -> prefix map, and only classifies a handler as
"privileged" if it is registered against a router whose prefix matches a
privileged-path signal (Section 6 of the MODULE-L5-01B mission: /admin,
/platform, /internal, /ops, /moderation). Non-privileged routers
(role-named paths like /v1/staff/*, /v1/customer/*, /v1/provider/*) are
never flagged by this guard -- they are a different, already-addressed
concern (tenant-scoped-by-JWT-claim, verified case-by-case in MODULE-L5-01B).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENGINES_DIR = ROOT / "app" / "engines"

PERMISSION_MARKERS = [
    "require_permission(", "require_super_admin", "require_tenant_owner",
    "require_staff_or_above", "require_customer)", "require_technician",
    "require_tenant_mutation_permission(", "require_platform_staff",
    "require_platform_mutate", "require_mfa", "require_any_permission(",
    "require_engine(",
]

PRIVILEGED_PATH_SIGNALS = ["/admin", "/platform", "/internal", "/ops", "/moderation"]

ROUTER_DEF_RE = re.compile(r'(\w+)\s*=\s*APIRouter\(\s*prefix\s*=\s*"([^"]*)"')
DECORATOR_RE = re.compile(r'@(\w+)\.(get|post|put|patch|delete)\(')
DEPENDS_AUTH_RE = re.compile(r'Depends\((get_current_user|require_super_admin|require_permission\([^)]*\)|require_platform_staff|require_tenant_owner|require_staff_or_above|require_customer|require_technician)\)')


def _find_router_level_auth(text: str, var: str) -> bool:
    """
    MODULE-L5-01B self-correction: the first version of this guard only
    looked at per-handler Depends(...) and missed FastAPI's router-level
    `APIRouter(..., dependencies=[Depends(require_super_admin)])` form,
    which applies to every route on that router without appearing in any
    individual handler signature. Confirmed via direct inspection this
    sprint that 6 files (marketing_automation, analytics x4, ai_conversation
    sprint29) already used this exact pattern -- the first guard version
    would have flagged all of them as false positives. This looks for a
    `dependencies=[...]` argument within the same APIRouter(...) call as
    the router's own prefix/tags, scanning a bounded window after the
    `var = APIRouter(` line.
    """
    m = re.search(re.escape(var) + r"\s*=\s*APIRouter\(", text)
    if not m:
        return False
    start = m.start()
    # Bounded window: the APIRouter(...) call rarely spans more than a
    # handful of lines even with prefix/tags/dependencies all present.
    window = text[start:start + 400]
    if "dependencies=" not in window:
        return False
    return any(marker.rstrip("(") in window for marker in PERMISSION_MARKERS)


def classify_file(path: Path):
    text = path.read_text(encoding="utf-8")

    routers = {var: prefix for var, prefix in ROUTER_DEF_RE.findall(text)}
    privileged_routers = {
        var for var, prefix in routers.items()
        if any(sig in prefix for sig in PRIVILEGED_PATH_SIGNALS)
        and not _find_router_level_auth(text, var)
    }
    if not privileged_routers:
        return []

    findings = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = DECORATOR_RE.search(line)
        if not m:
            continue
        router_var, method = m.group(1), m.group(2)
        if router_var not in privileged_routers:
            continue
        # Scan forward a bounded window covering this handler's full
        # signature up to its closing "):" -- handler signatures vary in
        # line count, so search until we see the body start rather than a
        # fixed window, to avoid spilling into the NEXT handler and
        # mis-crediting its auth dependency to this one.
        window_lines = []
        for k in range(i, min(i + 50, len(lines))):
            window_lines.append(lines[k])
            if re.match(r'^\)\s*(->.*)?:\s*$', lines[k]) or lines[k].rstrip().endswith("):"):
                break
        window = "\n".join(window_lines)
        auth_deps = DEPENDS_AUTH_RE.findall(window)
        has_bare = "get_current_user" in auth_deps
        has_real_permission = any(
            marker.rstrip("(") in "".join(auth_deps) or marker in window
            for marker in PERMISSION_MARKERS
        )
        has_any_auth = bool(auth_deps) or has_real_permission
        if not has_any_auth:
            findings.append({
                "router_var": router_var, "prefix": routers[router_var],
                "method": method.upper(), "line": i + 1,
                "severity": "MISSING_AUTHENTICATION",
            })
        elif has_bare and not has_real_permission:
            findings.append({
                "router_var": router_var, "prefix": routers[router_var],
                "method": method.upper(), "line": i + 1,
                "severity": "BARE_AUTHENTICATION_ONLY",
            })
    return findings


def main():
    all_findings = []
    for f in ENGINES_DIR.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        findings = classify_file(f)
        if findings:
            rel = str(f.relative_to(ROOT)).replace("\\", "/")
            for finding in findings:
                all_findings.append({"file": rel, **finding})

    result = {
        "privileged_bare_auth_findings": all_findings,
        "result": "ADMIN_ROUTER_AUTH_GUARD_FAILED" if all_findings else "ADMIN_ROUTER_AUTH_GUARD_PASSED",
    }
    print(__import__("json").dumps(result, indent=2))
    return 1 if all_findings else 0


if __name__ == "__main__":
    sys.exit(main())
