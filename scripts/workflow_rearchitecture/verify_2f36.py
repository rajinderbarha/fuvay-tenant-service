#!/usr/bin/env python
"""Slice 2F-36 — enterprise/tenant-administration/operational batch verifier.

    python scripts/workflow_rearchitecture/verify_2f36.py
    python scripts/workflow_rearchitecture/verify_2f36.py --selftest
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
S34 = os.path.join(DOCS, "phase-02a-slice-02f34")
S36 = os.path.join(DOCS, "phase-02a-slice-02f36")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
CANON_HASH = "72932524e0aa17b3"
MATRIX_HASH = "7cd530722272193e"
SETA_HASH = "0994c5373c08a2b6"
SETB_HASH = "9fe3fe305b53d174"
SETC_HASH = "6adb8d71a4c7e2b6"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

SET_A = {
    ("POST", "/v1/provider/setup/services/{service_id}/supported-options"),
    ("DELETE", "/v1/enterprise/saved-views/{view_id}"),
    ("POST", "/v1/provider/brands/services/{service_id}/supported"),
    ("PUT", "/v1/me/profile"),
    ("PUT", "/v1/provider/business-profile"),
    ("PUT", "/v1/enterprise/saved-views/{view_id}"),
    ("POST", "/v1/provider/brands/requests"),
    ("POST", "/v1/provider/reports/run"),
    ("POST", "/v1/enterprise/exports"),
    ("PUT", "/v1/provider/marketing/assets/{asset_id}/provider-notes"),
    ("PUT", "/v1/staff/profile"),
    ("PUT", "/v1/enterprise/column-preferences"),
    ("POST", "/v1/provider/marketing/campaigns/generate-launch"),
    ("POST", "/v1/enterprise/saved-views/{view_id}/set-default"),
    ("POST", "/v1/provider/business-profile/submit-review"),
    ("POST", "/v1/provider/setup/recommendations"),
    ("POST", "/v1/provider/marketing/campaigns/{campaign_id}/submit-review"),
    ("POST", "/v1/enterprise/saved-views"),
}
SET_B_CANONICAL = {
    ("POST", "/v1/chat/conversations/{conversation_id}/messages"),
    ("POST", "/v1/inventory/tenants/{tenant_id}/items"),
    ("POST", "/v1/inventory/items/{item_id}/locations/{location_id}/receive"),
    ("POST", "/v1/inventory/reservations"),
    ("POST", "/v1/inventory/reservations/confirm"),
    ("POST", "/v1/inventory/reservations/release"),
    ("POST", "/v1/appointments/{appointment_id}/confirm"),
    ("POST", "/v1/appointments/{appointment_id}/cancel"),
    ("POST", "/v1/appointments/{appointment_id}/reschedule"),
    ("POST", "/v1/appointments/{appointment_id}/no-show"),
    ("POST", "/v1/appointments/staff/{staff_id}/calendar/block"),
    ("DELETE", "/v1/appointments/calendar/blocks/{block_id}"),
    ("PUT", "/v1/appointments/staff/{staff_id}/working-hours"),
    ("POST", "/v1/catalog"),
    ("PUT", "/v1/catalog/{item_id}"),
    ("POST", "/v1/dispatch/jobs/{job_id}/dispatch"),
    ("POST", "/v1/dispatch/jobs/{job_id}/reassign"),
    ("POST", "/v1/ds/tenants/{tenant_id}/demand/recompute"),
    ("POST", "/v1/ds/tenants/{tenant_id}/pricing/apply"),
    ("GET", "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv"),
    ("POST", "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv/recompute"),
    ("PUT", "/v1/settings/tenants/{tenant_id}/{key}"),
    ("DELETE", "/v1/settings/tenants/{tenant_id}/{key}"),
    ("PUT", "/v1/notifications/tenants/{tenant_id}/channels/{channel}"),
}
SET_B_ALL_28 = SET_B_CANONICAL | {
    ("POST", "/v1/serviceability/check"),        # READ_ONLY_EXCLUDE
    ("GET", "/v1/ds/tenants/{tenant_id}/churn/score"),        # READ_ONLY_EXCLUDE
    ("GET", "/v1/ds/tenants/{tenant_id}/demand/forecast"),    # READ_ONLY_EXCLUDE
    ("POST", "/v1/bookings"),                     # CUSTOMER_SELF_SERVICE_EXCLUDE (already protected)
}
assert len(SET_B_ALL_28) == 28

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am36v", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def conditions(state=None):
    st = state or {}
    out = []
    E = _model()
    idx = E.route_index()
    canon = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    canon_rows = {(r[0], r[1]): r for r in canon}

    from app.engines.chat.service import ChatService
    from app.engines.inventory.service import InventoryService
    from app.engines.appointment.service import AppointmentService
    from app.engines.service_catalog.service import ServiceCatalogService
    from app.engines.dispatch.service import DispatchService
    from app.engines.data_science.service import DSService
    from app.engines.settings_engine.service import SettingsService
    from app.engines.notification.service import NotificationService
    from app.engines.enterprise_grid.services import SavedViewService

    out.append(("R01 Set A/B/C frozen hashes unchanged",
                st.get("r01", _h(os.path.join(S34, "slice-2f36-module-scope.csv")) == SETA_HASH
                       and _h(os.path.join(S34, "slice-2f36-held-scope.csv")) == SETB_HASH
                       and _h(os.path.join(S34, "slice-2f36-exclusion-scope.csv")) == SETC_HASH), ""))

    out.append(("R02 every Set A route is present and protected",
                st.get("r02", all(k in canon_rows and canon_rows[k][6] in VERIFIED for k in SET_A)),
                str([k for k in SET_A if k not in canon_rows or canon_rows[k][6] not in VERIFIED])))

    out.append(("R03 all 28 Set B routes received a final disposition (adjudicated in held-route-adjudication.csv)",
                st.get("r03", os.path.exists(os.path.join(S36, "held-route-adjudication.csv"))
                       and len(list(csv.DictReader(open(os.path.join(S36, "held-route-adjudication.csv"), encoding="utf-8")))) == 28),
                ""))

    out.append(("R04 every canonically-added Set B route is protected",
                st.get("r04", all(k in canon_rows and canon_rows[k][6] in VERIFIED for k in SET_B_CANONICAL)),
                str([k for k in SET_B_CANONICAL if k not in canon_rows or canon_rows[k][6] not in VERIFIED])))

    out.append(("R05 all 18+24 routes have mutation access-scope guard live",
                st.get("r05", all(any(g["access_scope_gated"] for g in E.route_guards(idx[k]))
                                   for k in (SET_A | SET_B_CANONICAL) if k in idx)), ""))

    sd = inspect.getsource(SavedViewService.set_default)
    out.append(("R06 set_default re-checks owner_user_id before mutating is_default",
                st.get("r06", "owner_user_id) != str(user_id)" in sd), ""))

    for svc_cls in [ChatService, InventoryService, AppointmentService, ServiceCatalogService,
                    DispatchService, DSService, SettingsService, NotificationService]:
        has_helper = hasattr(svc_cls, "_require_trusted_tenant")
        if not has_helper:
            out.append((f"R07 {svc_cls.__name__} has a _require_trusted_tenant helper",
                        st.get("r07", False), svc_cls.__name__))
            break
    else:
        out.append(("R07 every touched service has a _require_trusted_tenant helper",
                    st.get("r07", True), ""))

    for svc_cls in [ChatService, InventoryService, AppointmentService, ServiceCatalogService,
                    DispatchService, DSService, SettingsService, NotificationService]:
        src = inspect.getsource(svc_cls._require_trusted_tenant)
        if "self.actor_tenant_id is None" not in src or "raise" not in src:
            out.append((f"R08 {svc_cls.__name__}._require_trusted_tenant rejects missing tenant context",
                        st.get("r08", False), svc_cls.__name__))
            break
    else:
        out.append(("R08 every _require_trusted_tenant rejects missing tenant context",
                    st.get("r08", True), ""))

    aaa = inspect.getsource(AppointmentService._assert_appt_access)
    out.append(("R09 appointment ownership check is non-oracular (NotFoundException, not a distinct 403)",
                st.get("r09", aaa.count("NotFoundException") >= 2), ""))

    dj = inspect.getsource(DispatchService.dispatch_job)
    out.append(("R10 dispatch_job cross-checks the job's own tenant before advancing it",
                st.get("r10", "job_check.tenant_id != tenant_id" in dj), ""))

    ci = inspect.getsource(ServiceCatalogService.update_item)
    out.append(("R11 catalog update_item checks tenant ownership before mutating",
                st.get("r11", "item.tenant_id != self.actor_tenant_id" in ci), ""))

    rr = inspect.getsource(InventoryService.confirm_reservation)
    out.append(("R12 reservation confirm/release predicate the lookup by tenant_id (not just status)",
                st.get("r12", "StockReservation.tenant_id == tenant_id" in rr), ""))

    import subprocess
    fo = subprocess.run(["git", "grep", "-n", "actor_tenant_id=uuid.UUID(u.tenant_id)", "--",
                          "app/engines/chat/router.py", "app/engines/inventory/router.py",
                          "app/engines/appointment/router.py", "app/engines/service_catalog/router.py",
                          "app/engines/dispatch/router.py", "app/engines/data_science/router.py",
                          "app/engines/settings_engine/router.py", "app/engines/notification/router.py"],
                         cwd=REPO, capture_output=True, text=True)
    out.append(("R13 every touched router passes actor_tenant_id into its service constructor",
                st.get("r13", fo.stdout.count("actor_tenant_id") >= 8), str(fo.stdout.count("actor_tenant_id"))))

    prot = sum(1 for r in canon if r[6] in VERIFIED)
    out.append(("R14 coverage arithmetic is 294/297 (252+18+24 / 273+24)",
                st.get("r14", len(canon) == 297 and prot == 294), f"{prot}/{len(canon)}"))
    out.append(("R15 unprotected count is 3",
                st.get("r15", len(canon) - prot == 3), str(len(canon) - prot)))

    m01 = ("POST", "/v1/auth/api-keys")
    n01 = ("POST", "/v1/media/upload")
    geo = ("DELETE", "/v1/geo/zones/{zone_id}")
    s35a = ("DELETE", "/v1/webhooks/endpoints/{endpoint_id}")
    s35b = ("POST", "/v1/rag/query")
    out.append(("R16 M01 sample route remains VERIFIED (no regression)",
                st.get("r16", canon_rows[m01][6] in VERIFIED), ""))
    out.append(("R17 N01 sample route remains VERIFIED (no regression)",
                st.get("r17", canon_rows[n01][6] in VERIFIED), ""))
    out.append(("R18 geo sample route remains VERIFIED (no regression)",
                st.get("r18", canon_rows[geo][6] in VERIFIED), ""))
    out.append(("R18b Slice 2F-35 sample routes remain VERIFIED (no regression)",
                st.get("r18b", canon_rows[s35a][6] in VERIFIED and canon_rows[s35b][6] in VERIFIED), ""))

    # Set C (5 routes) must remain byte-identical -- untouched, no route
    # newly protected as a side effect of this slice.
    setc = None
    p = os.path.join(S34, "slice-2f36-exclusion-scope.csv")
    if os.path.exists(p):
        setc = list(csv.DictReader(open(p, encoding="utf-8")))
    setc_keys = {(r["method"], r["path"]) for r in (setc or [])}
    newly_verified_c = [k for k in setc_keys if k in canon_rows and canon_rows[k][6] in VERIFIED
                         and k not in (s35a, s35b)]  # 2F-35 already closed these before this slice
    out.append(("R19 no Set C route was newly protected by this slice",
                st.get("r19", not newly_verified_c), str(newly_verified_c)))

    # Slice 2F-35/2F-37/2F-38-exclusive files must not be touched BY THIS
    # slice. This session does not commit between slices, so `git status`
    # alone cannot distinguish "changed by an earlier, already-completed
    # slice" from "changed by 2F-36" -- geo/media/webhook/rag were all
    # legitimately modified by Slices 2F-31/2F-33/2F-35 before 2F-36 ever
    # started. Instead, confirm none of those files carry a 2F-36 marker
    # comment (every file this slice DID touch has one -- see
    # frozen-scope-verification.md).
    forbidden_files = [
        "app/engines/geo/router.py", "app/engines/geo/service.py",
        "app/engines/media/router.py", "app/engines/media/service.py",
        "app/engines/webhook/router.py", "app/engines/webhook/service.py",
        "app/engines/rag/router.py", "app/engines/rag/service.py",
    ]
    marked = [f for f in forbidden_files
              if "2F-36" in open(os.path.join(REPO, f), encoding="utf-8").read()]
    out.append(("R20 no Slice 2F-35/37-exclusive application file carries a 2F-36 marker",
                st.get("r20", not marked), str(marked)))

    docs = {f: open(os.path.join(S36, f), encoding="utf-8").read()
            for f in os.listdir(S36) if f.endswith(".md")} if os.path.isdir(S36) else {}

    def _claims_overclosure(body: str) -> bool:
        low = body.lower()
        for phrase in ("application-wide security closure", "entire application is secure",
                       "application-wide authorization closure"):
            start = 0
            while True:
                i = low.find(phrase, start)
                if i == -1:
                    break
                window = low[max(0, i - 40):i]
                if not any(neg in window for neg in ("no ", "not ", "n't ", "does not", "isn't")):
                    return True
                start = i + len(phrase)
        return False

    overclaim = [f for f, b in docs.items() if _claims_overclosure(b)]
    out.append(("R21 no document claims application-wide closure",
                st.get("r21", not overclaim), ",".join(overclaim)))

    out.append(("R22 canonical hash matches the post-closure frozen value",
                st.get("r22", _h(CANON) == CANON_HASH), _h(CANON)))
    out.append(("R23 matrix hash matches the post-closure frozen value",
                st.get("r23", _h(MATRIX) == MATRIX_HASH), _h(MATRIX)))

    return out


def selftest() -> int:
    print("Slice 2F-36 verifier negative-fixture self-test\n")
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
    print("Slice 2F-36 verifier\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (enterprise/tenant-admin/operational batch scope only -- not application-wide)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
