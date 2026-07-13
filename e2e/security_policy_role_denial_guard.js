// FINAL-L5-05AM: bounded, real, live role-denial guard for the Security
// Policy Update action -- the one action this sprint proved end-to-end
// (frontend gate + direct API + DB mutation/revert) across all 5 canonical
// roles. Fails closed: any unexpected status, any non-zero mutation for a
// denied role, or a login failure all fail the guard.
//
// This is intentionally scoped to ONE action, not all 29 in the registry --
// building the full role-denial guard for every registered action is real,
// substantial, separate future work (see FINAL_L5_05AM certification doc).
// This guard demonstrates the pattern and is the first of what should
// become a per-action loop once each action has its own live-verified
// expectation (most of the 29 registry rows do not yet).
const http = require("http");

const BASE = "http://localhost:8000";
const POLICY_KEY = "export_audit_retention_days";
const ORIGINAL_VALUE = 365;

const ROLE_CREDS = {
  super_admin: { email: "admin@serviceos.local", password: "Password123!" },
  admin_operations: { email: "admin.ops@serviceos.local", password: "CanonicalL5!2026" },
  admin_finance: { email: "admin.finance@serviceos.local", password: "CanonicalL5!2026" },
  admin_security: { email: "admin.security@serviceos.local", password: "CanonicalL5!2026" },
  admin_readonly: { email: "admin.readonly@serviceos.local", password: "CanonicalL5!2026" },
};

const EXPECTED_STATUS = {
  super_admin: 200,
  admin_operations: 403,
  admin_finance: 403,
  admin_security: 403,
  admin_readonly: 403,
};

function request(method, path, body, token) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const req = http.request(
      `${BASE}${path}`,
      {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(data ? { "Content-Length": Buffer.byteLength(data) } : {}),
        },
      },
      res => {
        let raw = "";
        res.on("data", c => (raw += c));
        res.on("end", () => {
          let json = null;
          try { json = JSON.parse(raw); } catch (_) {}
          resolve({ status: res.statusCode, json });
        });
      }
    );
    req.on("error", reject);
    if (data) req.write(data);
    req.end();
  });
}

async function login(email, password) {
  const r = await request("POST", "/v1/auth/login", { email, password });
  if (r.status !== 200 || !r.json?.data?.access_token) {
    throw new Error(`login failed for ${email}: status ${r.status}`);
  }
  return r.json.data.access_token;
}

async function getPolicyValue(token) {
  const r = await request("GET", "/v1/admin/security/policies", null, token);
  if (r.status !== 200) throw new Error(`GET policies failed: ${r.status}`);
  const p = r.json.data.policies.find(x => x.policy_key === POLICY_KEY);
  if (!p) throw new Error(`policy ${POLICY_KEY} not found`);
  return p.policy_value;
}

async function main() {
  const findings = [];
  const superToken = await login(ROLE_CREDS.super_admin.email, ROLE_CREDS.super_admin.password);

  const before = await getPolicyValue(superToken);
  if (before !== ORIGINAL_VALUE) {
    findings.push({ severity: "BLOCKER", reason: `precondition failed: expected ${POLICY_KEY}=${ORIGINAL_VALUE}, found ${before} -- guard cannot safely proceed` });
    return report(findings);
  }

  // Phase 1: the 4 denied roles first, while the DB is known-good at
  // ORIGINAL_VALUE. Each attempt must be rejected with zero mutation --
  // checked immediately after every single attempt, not batched, so a
  // false pass can never be attributed to a later step.
  const deniedRoles = Object.keys(ROLE_CREDS).filter(r => r !== "super_admin");
  for (const role of deniedRoles) {
    const creds = ROLE_CREDS[role];
    const token = await login(creds.email, creds.password);
    const r = await request(
      "PATCH",
      `/v1/admin/security/policies/${POLICY_KEY}`,
      { value: 999, reason: "FINAL-L5-05AM role-denial guard (should be rejected)" },
      token
    );
    const expected = EXPECTED_STATUS[role];
    if (r.status !== expected) {
      findings.push({ severity: "CRITICAL", role, expected_status: expected, actual_status: r.status, reason: "status mismatch" });
    }
    const afterRoleCall = await getPolicyValue(superToken);
    if (afterRoleCall !== ORIGINAL_VALUE) {
      findings.push({ severity: "CRITICAL", role, reason: `denied role mutated DB: value is now ${afterRoleCall}, expected unchanged ${ORIGINAL_VALUE}` });
    }
  }

  // Phase 2: super_admin, the one role expected to succeed. Mutate, verify,
  // then revert in the same isolated step and verify the revert too.
  const mutateResp = await request(
    "PATCH",
    `/v1/admin/security/policies/${POLICY_KEY}`,
    { value: 999, reason: "FINAL-L5-05AM role-denial guard (auto-reverted)" },
    superToken
  );
  if (mutateResp.status !== EXPECTED_STATUS.super_admin) {
    findings.push({ severity: "CRITICAL", role: "super_admin", expected_status: EXPECTED_STATUS.super_admin, actual_status: mutateResp.status, reason: "status mismatch" });
  }
  const persistedValue = mutateResp.json?.data?.policy_value;
  if (persistedValue !== 999) {
    findings.push({ severity: "CRITICAL", role: "super_admin", reason: `PATCH response did not reflect the new value: expected 999, got ${persistedValue}` });
  }

  const revert = await request(
    "PATCH",
    `/v1/admin/security/policies/${POLICY_KEY}`,
    { value: ORIGINAL_VALUE, reason: "FINAL-L5-05AM role-denial guard revert" },
    superToken
  );
  if (revert.status !== 200) {
    findings.push({ severity: "BLOCKER", reason: `revert failed: status ${revert.status} -- policy left mutated at 999` });
  }
  const revertedValue = revert.json?.data?.policy_value;
  if (revertedValue !== ORIGINAL_VALUE) {
    findings.push({ severity: "BLOCKER", reason: `revert response did not reflect original value: expected ${ORIGINAL_VALUE}, got ${revertedValue}` });
  }
  const finalCheck = await getPolicyValue(superToken);
  if (finalCheck !== ORIGINAL_VALUE) {
    findings.push({ severity: "BLOCKER", reason: `final GET after revert shows ${finalCheck}, expected ${ORIGINAL_VALUE} -- guard left residual state` });
  }

  report(findings);
}

function report(findings) {
  const result = {
    action: "Policy Update",
    endpoint: `PATCH /v1/admin/security/policies/${POLICY_KEY}`,
    roles_tested: Object.keys(ROLE_CREDS),
    findings,
    result: findings.length === 0 ? "ROLE_DENIAL_GUARD_PASSED" : "ROLE_DENIAL_GUARD_FAILED",
  };
  console.log(JSON.stringify(result, null, 2));
  process.exit(findings.length === 0 ? 0 : 1);
}

main().catch(err => {
  console.log(JSON.stringify({ result: "ROLE_DENIAL_GUARD_FAILED", reason: err.message }, null, 2));
  process.exit(1);
});
