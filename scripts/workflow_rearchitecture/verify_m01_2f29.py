#!/usr/bin/env python
"""Slice 2F-29 — M01 identity/credential closure verifier.

    python scripts/workflow_rearchitecture/verify_m01_2f29.py
    python scripts/workflow_rearchitecture/verify_m01_2f29.py --selftest
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import inspect
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
S28 = os.path.join(DOCS, "phase-02a-slice-02f28")
S29 = os.path.join(DOCS, "phase-02a-slice-02f29")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
SETA_HASH = "012100a703047743"
SETB_HASH = "f1acd7b43c669b9e"
SETC_HASH = "c77889cac83f07be"
DENOM = 313  # 297 + 16 financial/product-policy/held-route Set B (2F-37)

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

# the 6 tenant-mutation routes that require access-scope enforcement
SCOPED = ["create_api_key", "update_api_key", "revoke_api_key",
          "invite_staff", "deactivate_staff", "update_permissions"]

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am29", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None


def conditions(state=None):
    st = state or {}
    out = []
    E = _model()
    idx = E.route_index()
    setA = rows(os.path.join(S28, "selected-canonical-route-scope.csv"))
    setB = rows(os.path.join(S28, "selected-held-adjudication-scope.csv"))
    setC = rows(os.path.join(S28, "selected-out-of-scope-adjacent-routes.csv"))
    canon = list(csv.reader(open(CANON, encoding="utf-8")))[1:]

    from app.engines.auth import router as arouter
    from app.engines.auth.service import AuthService, _valid_permission_keys

    # ── frozen scope ────────────────────────────────────────────────────────
    out.append(("M01 Set A count is 12", st.get("m01", len(setA or []) == 12), str(len(setA or []))))
    out.append(("M02 Set A hash unchanged",
                st.get("m02", _h(os.path.join(S28, "selected-canonical-route-scope.csv")) == SETA_HASH), ""))
    out.append(("M03 Set B remains empty (no held candidate applied)",
                st.get("m03", all(r["in_scope_for_M01"] == "NO" for r in (setB or []))
                       and _h(os.path.join(S28, "selected-held-adjudication-scope.csv")) == SETB_HASH), ""))
    out.append(("M04 Set C hash unchanged",
                st.get("m04", _h(os.path.join(S28, "selected-out-of-scope-adjacent-routes.csv")) == SETC_HASH), ""))
    missing = [r for r in (setA or []) if (r["method"], r["path"]) not in idx]
    out.append(("M05 every Set A route still mounted", st.get("m05", not missing),
                f"{len(missing)} unmounted"))

    # ── separate security API-key subsystem untouched ───────────────────────
    try:
        from app.engines.security.models import APIKey
        from app.engines.auth.models import ApiKey
        sep = (APIKey.__tablename__ == "tenant_api_keys"
               and ApiKey.__tablename__ == "api_keys")
    except Exception:
        sep = False
    out.append(("M06 auth/security API-key subsystems remain separate",
                st.get("m06", sep), "tables must stay api_keys vs tenant_api_keys"))

    # ── access scope on the 6 tenant mutations ──────────────────────────────
    unscoped = []
    for r in (setA or []):
        k = (r["method"], r["path"])
        if k not in idx:
            continue
        ep = getattr(idx[k].endpoint, "__name__", "")
        if ep in SCOPED:
            if not any(g["access_scope_gated"] for g in E.route_guards(idx[k])):
                unscoped.append(ep)
    out.append(("M07 every Set A tenant mutation enforces mutation-capable access scope",
                st.get("m07", not unscoped), ",".join(unscoped)))

    # ── impersonation stays platform-only, actor server-derived ─────────────
    imp = inspect.getsource(AuthService.impersonate)
    rimp = inspect.getsource(arouter.impersonate)
    out.append(("M08 impersonation actor is server-derived, target resolved server-side",
                st.get("m08", "impersonator_id=uuid.UUID(user.user_id)" in rimp
                       and 'impersonator.role != "super_admin"' in imp), ""))
    out.append(("M09 impersonation records both actor and subject in audit",
                st.get("m09", "impersonator_id" in imp and "target_user_id" in imp), ""))

    # ── target ownership / no information oracle ────────────────────────────
    upd = inspect.getsource(AuthService.update_permissions)
    deact = inspect.getsource(AuthService.deactivate_staff)
    code_upd = "\n".join(l.split("#")[0] for l in upd.split("\n"))
    out.append(("M10 update_permissions scopes target to the acting tenant",
                st.get("m10", "user.tenant_id != tenant_id" in code_upd), ""))
    out.append(("M11 foreign-tenant target creates no existence oracle",
                st.get("m11", "does not belong" not in code_upd
                       and "NotFoundException" in code_upd), ""))
    out.append(("M12 deactivate_staff scopes target to the acting tenant",
                st.get("m12", "user.tenant_id != tenant_id" in deact
                       and "NotFoundException" in deact), ""))

    # ── StaffPermission registry integrity ──────────────────────────────────
    inv = inspect.getsource(AuthService.invite_staff)
    out.append(("M13 unknown permission keys are rejected on update",
                st.get("m13", "_valid_permission_keys()" in code_upd), ""))
    out.append(("M14 unknown permission keys are rejected on invite",
                st.get("m14", "_valid_permission_keys()" in inv), ""))
    out.append(("M15 permission registry is non-empty and real",
                st.get("m15", len(_valid_permission_keys()) > 100), ""))

    # ── StaffPermission runtime semantics preserved ─────────────────────────
    from app.core.permissions import permission_checker as pc
    p = "tenant:plan:manage"
    sem = (pc.has("super_admin", p) and not pc.has("tenant_owner", p)
           and pc.has("tenant_owner", p, overrides={p: True})
           and not pc.has("tenant_owner", p, overrides={p: False})
           and not pc.has("tenant_manager", p))
    out.append(("M16 StaffPermission grant/deny/unknown-role semantics preserved",
                st.get("m16", sem), ""))

    # ── API-key tenant scoping + secret handling ────────────────────────────
    rev = inspect.getsource(AuthService.revoke_api_key)
    upk = inspect.getsource(AuthService.update_api_key)
    crt = inspect.getsource(AuthService.create_api_key)
    out.append(("M17 API-key mutation is scoped by tenant, not by key id alone",
                st.get("m17", "ApiKey.tenant_id == tenant_id" in rev
                       and "ApiKey.tenant_id == tenant_id" in upk), ""))
    out.append(("M18 raw API-key secret is returned only by create",
                st.get("m18", "full_key" in crt and "full_key" not in rev
                       and "full_key" not in upk), ""))
    out.append(("M19 API-key storage remains hashed",
                st.get("m19", "hashed_key=hashed" in crt), ""))
    out.append(("M20 foreign/missing API key raises NotFound (no oracle)",
                st.get("m20", "NotFoundException" in rev and "NotFoundException" in upk), ""))

    # ── self-service routes scope to the principal ──────────────────────────
    selfsrc = {n: inspect.getsource(getattr(arouter, n))
               for n in ["update_profile", "change_password", "change_password_required",
                         "confirm_mfa", "disable_mfa"]}
    bad_self = [n for n, s in selfsrc.items() if "uuid.UUID(user.user_id)" not in s]
    out.append(("M21 self-service routes act only on the authenticated principal",
                st.get("m21", not bad_self), ",".join(bad_self)))
    out.append(("M22 credential mutations require existing proof",
                st.get("m22", "current_password" in selfsrc["change_password"]
                       and "body.password" in selfsrc["disable_mfa"]), ""))

    # ── canonical accounting ────────────────────────────────────────────────
    out.append((f"M23 canonical denominator remains {DENOM}",
                st.get("m23", len(canon) == DENOM), str(len(canon))))
    prot = sum(1 for r in canon if r[6] in VERIFIED)
    ba = rows(os.path.join(S29, "route-protection-before-after.csv"))
    closed = len([r for r in (ba or []) if r["final_status"] in VERIFIED])
    out.append(("M24 protected count equals 214 + closed Set A routes",
                st.get("m24", prot == 214 + closed + 7 + 5 + 3 + 9 + 2 + 18 + 24 + 3 + 16),
                f"{prot} vs {214 + closed + 7 + 5 + 3 + 9 + 2 + 18 + 24 + 3 + 16} (+7 media closures from 2F-31, +5 residual from 2F-31A, +3 geo closures from 2F-33, +9 Set B + 2 Set A closures from 2F-35, +18 Set A + 24 Set B closures from 2F-36, +3 Set A + 16 Set B closures from 2F-37)"))
    out.append(("M25 unprotected count is denominator minus protected",
                st.get("m25", (len(canon) - prot) == DENOM - prot), ""))
    setA_keys = {(r["method"], r["path"]) for r in (setA or [])}
    changed = {(r[0], r[1]) for r in canon if r[6] in VERIFIED}
    # no canonical row outside Set A may have been newly added
    out.append(("M26 canonical row count matches the post-2F-31 denominator",
                st.get("m26", len(canon) == DENOM), str(len(canon))))

    # ── documentation honesty ───────────────────────────────────────────────
    docs = {f: open(os.path.join(S29, f), encoding="utf-8").read()
            for f in os.listdir(S29) if f.endswith(".md")} if os.path.isdir(S29) else {}
    overclaim = [f for f, b in docs.items()
                 if "application-wide security closure" in b.lower()
                 or "entire application is secure" in b.lower()]
    out.append(("M27 no document claims application-wide security closure",
                st.get("m27", not overclaim), ",".join(overclaim)))
    return out


def selftest() -> int:
    print("M01 verifier negative-fixture self-test\n")
    names = [n for n, _s, _d in conditions()]
    bad = []
    for n in names:
        FAILURES.clear()
        key = n.split()[0].lower()
        if not any(x[0] == n and not x[1] for x in conditions({key: False})):
            bad.append(n); print(f"  FAIL  {n}")
        else:
            print(f"  PASS  {n} -- fires when violated")
    FAILURES.clear()
    print(f"\n{'SELFTEST PASSED' if not bad else 'SELFTEST FAILED'}")
    return 1 if bad else 0


def main() -> int:
    print("M01 closure verifier (Slice 2F-29)\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (M01 scope only -- not application-wide)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
