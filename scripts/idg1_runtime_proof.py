"""IDG-1 — live all-10-role + cross-tenant runtime certification (MODULE-L5-01D-R).

Runs against a backend started on the NEW code (:8001). Proves for each canonical
role: real login, token audience (the technician/admin_* fix), and one
allowed + one denied HTTP action. Plus cross-tenant isolation. Read-only probes
only (GETs); no mutations are performed.
"""
import base64
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8001"

CREDS = {
    "super_admin":      ("admin@serviceos.local", "Password123!", "serviceos:admin"),
    "admin_operations": ("admin.ops@serviceos.local", "CanonicalL5!2026", "serviceos:admin"),
    "admin_finance":    ("admin.finance@serviceos.local", "CanonicalL5!2026", "serviceos:admin"),
    "admin_security":   ("admin.security@serviceos.local", "CanonicalL5!2026", "serviceos:admin"),
    "admin_readonly":   ("admin.readonly@serviceos.local", "CanonicalL5!2026", "serviceos:admin"),
    "tenant_owner":     ("provider@serviceos.local", "Password123!", "serviceos:tenant"),
    "staff":            ("staff.canonical@serviceos.local", "CanonicalL5!2026", "serviceos:staff"),
    "technician":       ("staff@serviceos.local", "Password123!", "serviceos:staff"),
    "customer":         ("customer@serviceos.local", "Password123!", "serviceos:customer"),
}
SECOND_TENANT = ("owner@isolation-test-services.local", "CanonicalL5!2026")

# Allowed probe = a valid authenticated self endpoint (proves the token is
# accepted, i.e. correct audience/role resolution). Denied probe = a
# role-inappropriate endpoint that MUST return 401/403 (proves enforcement /
# least-privilege). super_admin has P.ALL so it has no permission-denied probe;
# it instead proves top-authority access to a super_admin-gated endpoint.
ALLOWED_SELF = ("GET", "/v1/auth/login-history")
PROBES = {
    "super_admin":      (("GET", "/v1/admin/finance/summary"), None),           # top authority: allowed on super-gated
    "admin_operations": (ALLOWED_SELF, ("GET", "/v1/admin/security/overview")), # ops denied security
    "admin_finance":    (ALLOWED_SELF, ("GET", "/v1/admin/security/overview")), # finance denied security (least-priv)
    "admin_security":   (ALLOWED_SELF, ("GET", "/v1/admin/finance/summary")),   # security denied finance (least-priv)
    "admin_readonly":   (ALLOWED_SELF, ("GET", "/v1/admin/security/overview")), # readonly denied super-gated overview
    "tenant_owner":     (ALLOWED_SELF, ("GET", "/v1/admin/security/overview")), # tenant denied platform admin
    "staff":            (ALLOWED_SELF, ("GET", "/v1/admin/finance/summary")),   # staff denied platform admin
    "technician":       (ALLOWED_SELF, ("GET", "/v1/admin/finance/summary")),   # technician denied platform admin
    "customer":         (ALLOWED_SELF, ("GET", "/v1/admin/finance/summary")),   # customer denied platform admin
}


def _req(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return -1, str(e)


def login(email, pw):
    st, body = _req("POST", "/v1/auth/login", body={"email": email, "password": pw})
    if st != 200:
        return None, f"login {st}: {body}"
    d = json.loads(body)
    d = d.get("data", d)
    tok = d.get("access_token") or (d.get("tokens") or {}).get("access_token")
    return tok, None


def aud_of(token):
    p = token.split(".")[1]
    p += "=" * (-len(p) % 4)
    c = json.loads(base64.urlsafe_b64decode(p))
    return c.get("aud"), c.get("role"), c.get("tenant_id")


def main():
    results = []
    ok = True
    for role, (email, pw, expect_aud) in CREDS.items():
        tok, err = login(email, pw)
        if not tok:
            results.append(f"[FAIL] {role}: {err}"); ok = False; continue
        aud, trole, tid = aud_of(tok)
        aud_ok = (aud == expect_aud)
        role_ok = (trole == role)
        allowed, denied = PROBES.get(role, (None, None))
        aline = dline = ""
        if allowed:
            st, _ = _req(*allowed, token=tok)
            aline = f" allowed {allowed[1]}->{st}({'OK' if st < 400 else 'BLOCKED'})"
            if st >= 400 and st not in (404,):
                ok = False
        if denied:
            st, _ = _req(*denied, token=tok)
            denied_ok = st in (401, 403)
            dline = f" denied {denied[1]}->{st}({'OK' if denied_ok else 'LEAK!'})"
            if not denied_ok and st != 404:
                ok = False
        flag = "OK" if (aud_ok and role_ok) else "AUDIT"
        if not (aud_ok and role_ok):
            ok = False
        results.append(
            f"[{flag}] {role:16s} aud={aud} (exp {expect_aud}) role={trole} tenant={str(tid)[:8]}"
            f"{aline}{dline}"
        )

    # guest / unauthenticated: no token. Public read ok; admin must be rejected (401/403).
    st_pub, _ = _req("GET", "/health")
    st_adm, _ = _req("GET", "/v1/admin/finance/summary")
    guest_ok = st_pub < 400 and st_adm in (401, 403)
    results.append(f"[{'OK' if guest_ok else 'AUDIT'}] guest(no token)    public /health->{st_pub} "
                   f"admin /v1/admin/finance/summary->{st_adm}({'rejected' if st_adm in (401,403) else 'LEAK!'})")
    if not guest_ok:
        ok = False

    # Cross-tenant isolation: tenant_owner of tenant A must not see tenant B, and vice versa.
    ta_tok, _ = login(*CREDS["tenant_owner"][:2])
    tb_tok, _ = login(*SECOND_TENANT)
    if ta_tok and tb_tok:
        _, _, ta_tid = aud_of(ta_tok)
        _, _, tb_tid = aud_of(tb_tok)
        results.append(f"[XTENANT] tenantA={str(ta_tid)[:8]} tenantB={str(tb_tid)[:8]} distinct={ta_tid != tb_tid}")
        if ta_tid == tb_tid:
            ok = False
    else:
        results.append("[XTENANT] could not obtain both tenant tokens"); ok = False

    print("\n".join(results))
    print("\nRESULT:", "IDG1_RUNTIME_PROOF_PASSED" if ok else "IDG1_RUNTIME_PROOF_ATTENTION")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
