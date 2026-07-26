"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader } from "../../../../components/shared/ui";
import {
  autoPriceOptionsApi, catalogApi, catalogWorkspaceApi,
  type MatchingDiagnosticsResult, type MatchingPolicyManifest, type MatchingAuditRow,
  type ServiceCategory, type MasterService, type MasterServiceJobTypeLink,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Search, CheckCircle2, XCircle, Shield } from "lucide-react";

const money = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN")}`;

type Tab = "diagnostics" | "live" | "policy" | "audit";

const selectStyle: React.CSSProperties = {
  width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)",
  border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)",
  fontSize: 13, outline: "none",
};
const fieldLabel: React.CSSProperties = {
  fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5,
};
function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label style={fieldLabel}>{label}</label>{children}</div>;
}

export default function ProviderMatchingPage() {
  const [tab, setTab] = useState<Tab>("diagnostics");

  return (
    <AdminLayout activeNav="hs-provider-matching">
      <SectionHeader
        title="Provider Matching"
        subtitle="Monitor the matching engine, simulate booking scenarios and explain every provider decision."
      />

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 20 }}>
        {([["diagnostics", "Diagnostics"], ["live", "Live Decisions"], ["policy", "Policy Reference"], ["audit", "Audit"]] as [Tab, string][]).map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "10px 16px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
            borderBottom: tab === id ? "2px solid var(--primary)" : "2px solid transparent",
            color: tab === id ? "var(--primary)" : "var(--text-secondary)", cursor: "pointer",
          }}>{label}</button>
        ))}
      </div>

      <RuntimeSafeguards />

      {tab === "diagnostics" && <DiagnosticsTab />}
      {tab === "live" && <LiveDecisionsTab />}
      {tab === "policy" && <PolicyReferenceTab />}
      {tab === "audit" && <AuditTab />}
    </AdminLayout>
  );
}

function RuntimeSafeguards() {
  const items = [
    "Exact Job-Type Blueprint is resolved server-side",
    "Tenant isolation enforced",
    "Customer cannot select a provider",
    "Pricing is not calculated or configured here",
    "Diagnostic creates no booking, job, assignment or score change",
    "Admin cannot override the selected winner",
  ];
  return (
    <Card style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <Shield size={14} style={{ color: "var(--primary)" }} />
        <p style={{ fontSize: 12, fontWeight: 700, margin: 0 }}>Runtime Safeguards</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 6 }}>
        {items.map(i => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-secondary)" }}>
            <CheckCircle2 size={12} style={{ color: "var(--success-text, var(--success))", flexShrink: 0 }} /> {i}
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Diagnostics tab ───────────────────────────────────────────────────────

function DiagnosticsTab() {
  const [categoryId, setCategoryId] = useState("");
  const [masterServiceId, setMasterServiceId] = useState("");
  const [jobTypeLinkId, setJobTypeLinkId] = useState("");
  const [city, setCity] = useState("");
  const [zipcode, setZipcode] = useState("");
  const [result, setResult] = useState<MatchingDiagnosticsResult | null>(null);

  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const catList: ServiceCategory[] = cats.data?.categories ?? [];
  const svcs = useApi(useCallback(
    () => categoryId ? catalogApi.listMasterServices(categoryId) : Promise.resolve({ services: [] as MasterService[] }),
    [categoryId]), [categoryId]);
  const svcList: MasterService[] = svcs.data?.services ?? [];
  const jobTypes = useApi(useCallback(
    () => masterServiceId ? catalogWorkspaceApi.getJobTypesForService(masterServiceId) : Promise.resolve({ items: [] as MasterServiceJobTypeLink[] }),
    [masterServiceId]), [masterServiceId]);
  const jobTypeList: MasterServiceJobTypeLink[] = jobTypes.data?.items ?? [];
  const selectedJobType = jobTypeList.find(l => l.id === jobTypeLinkId);

  const runAction = useAction(useCallback(async () => {
    return autoPriceOptionsApi.runMatchingDiagnostics({
      category_id: categoryId, master_service_id: masterServiceId,
      city, zipcode: zipcode || undefined,
      job_type_id: selectedJobType?.job_type_id,
    });
  }, [categoryId, masterServiceId, city, zipcode, selectedJobType]));

  async function handleRun() {
    const r = await runAction.execute();
    if (r) setResult(r);
  }

  const canRun = !!(categoryId && masterServiceId && city);

  return (
    <div>
      <Card style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 12px" }}>Run diagnostic</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 12 }}>
          <FieldRow label="Business Vertical / Service Group">
            <select value={categoryId} onChange={e => { setCategoryId(e.target.value); setMasterServiceId(""); setJobTypeLinkId(""); }} style={selectStyle}>
              <option value="">— Select —</option>
              {catList.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
            </select>
          </FieldRow>
          <FieldRow label="Master Service">
            <select value={masterServiceId} onChange={e => { setMasterServiceId(e.target.value); setJobTypeLinkId(""); }} style={selectStyle} disabled={!categoryId}>
              <option value="">— Select —</option>
              {svcList.map(s => <option key={s.service_id} value={s.service_id}>{s.service_name}</option>)}
            </select>
          </FieldRow>
          <FieldRow label="Job Type">
            <select value={jobTypeLinkId} onChange={e => setJobTypeLinkId(e.target.value)} style={selectStyle} disabled={!masterServiceId}>
              <option value="">— Any / not yet resolved —</option>
              {jobTypeList.map(l => <option key={l.id} value={l.id}>{l.job_type?.label ?? l.job_type_id}</option>)}
            </select>
          </FieldRow>
          <FieldRow label="Customer location (city)">
            <input value={city} onChange={e => setCity(e.target.value)} placeholder="e.g. Ludhiana" style={selectStyle} />
          </FieldRow>
          <FieldRow label="Pincode (optional)">
            <input value={zipcode} onChange={e => setZipcode(e.target.value)} placeholder="e.g. 141001" style={selectStyle} />
          </FieldRow>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
          Type and Brand are derived from the selected Job-Type Blueprint where enabled and cannot be set manually here.
        </p>
        <Btn size="sm" variant="primary" loading={runAction.loading} disabled={!canRun} onClick={handleRun}>
          <Search size={13} style={{ marginRight: 4 }} />Run Diagnostic
        </Btn>
        {runAction.error && (
          <p style={{ fontSize: 12, color: "var(--danger-text)", marginTop: 10 }}>
            {runAction.error}{runAction.requestId && ` — Request ID: ${runAction.requestId}`}
          </p>
        )}
      </Card>

      {result && <DiagnosticResult result={result} />}
    </div>
  );
}

function DiagnosticResult({ result }: { result: MatchingDiagnosticsResult }) {
  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
        <MiniStat label="Providers Found" value={result.candidate_provider_count} />
        <MiniStat label="Eligible" value={result.eligible_provider_count} />
        <MiniStat label="Excluded" value={result.excluded_provider_count} danger={result.excluded_provider_count > 0} />
      </div>

      {result.trace_id && (
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 16px" }}>
          Trace ID: <code>{result.trace_id}</code> · Policy v{result.policy_version}
        </p>
      )}

      <Card style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Canonical Sources</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8, fontSize: 12 }}>
          <div><span style={{ color: "var(--text-tertiary)" }}>Bookability Source:</span> {result.bookability_source}</div>
          <div><span style={{ color: "var(--text-tertiary)" }}>Area Coverage Source:</span> {result.area_coverage_source}</div>
          <div><span style={{ color: "var(--text-tertiary)" }}>Availability Source:</span> {result.availability_source}</div>
          <div><span style={{ color: "var(--text-tertiary)" }}>Pricing Source:</span> {result.pricing_source}</div>
        </div>
      </Card>

      {result.excluded_providers.length > 0 && (
        <Card style={{ marginBottom: 20 }}>
          <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Exclusion Summary</p>
          {result.excluded_providers.map((ep, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0",
              borderBottom: i < result.excluded_providers.length - 1 ? "1px solid var(--border)" : "none" }}>
              <span style={{ fontSize: 12 }}>{ep.provider_name}</span>
              <Badge variant="danger" size="sm">{ep.reason_code ?? "UNKNOWN"}</Badge>
            </div>
          ))}
        </Card>
      )}

      {!result.selected_provider ? (
        <Card style={{ marginBottom: 20, textAlign: "center", padding: 32 }}>
          <XCircle size={28} style={{ color: "var(--danger-text)", margin: "0 auto 10px" }} />
          <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px" }}>No eligible provider found</p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
            {result.candidate_provider_count} candidate(s) found in the area, all excluded by eligibility gates.
          </p>
        </Card>
      ) : (
        <Card style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <CheckCircle2 size={18} style={{ color: "var(--success-text, var(--success))" }} />
                <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{result.selected_provider.provider_name}</p>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                {result.selected_provider.customer_visible_reason}
              </p>
              <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                {result.selected_provider.public_badges.map(b => <Badge key={b} variant="info" size="sm">{b}</Badge>)}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: 10, color: "var(--muted-text)", textTransform: "uppercase", margin: 0 }}>Final Score</p>
              <p style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>{result.selected_provider.internal_score.toFixed(1)}</p>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8 }}>
            {Object.entries(result.selected_provider.internal_score_breakdown).map(([k, v]) => (
              <div key={k} style={{ padding: 8, borderRadius: "var(--radius-md)", background: "var(--surface-sunken)", textAlign: "center" }}>
                <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{typeof v === "number" ? v : String(v)}</p>
                <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: 0, textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {result.top_candidates.length > 1 && (
        <Card style={{ marginBottom: 20 }}>
          <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Provider Evaluation</p>
          {result.top_candidates.map((c, i) => (
            <div key={c.tenant_id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0",
              borderBottom: i < result.top_candidates.length - 1 ? "1px solid var(--border)" : "none" }}>
              <span style={{ fontSize: 12 }}>{i + 1}. {c.provider_name}</span>
              <span style={{ fontSize: 12, fontWeight: 700 }}>{c.internal_score.toFixed(1)}</span>
            </div>
          ))}
        </Card>
      )}

      {result.price_options && (
        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Low / Mid / High Price Preview</p>
          <div style={{ display: "flex", gap: 10 }}>
            <PriceTierCard label="Low" value={result.price_options.low_price} />
            <PriceTierCard label="Mid" value={result.price_options.mid_price} />
            <PriceTierCard label="High" value={result.price_options.high_price} />
          </div>
        </Card>
      )}
    </>
  );
}

function MiniStat({ label, value, danger }: { label: string; value: number; danger?: boolean }) {
  return (
    <div style={{ padding: "10px 14px", background: "var(--surface-sunken)", borderRadius: 10 }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: danger ? "var(--danger-text)" : "var(--text-primary)" }}>{value}</div>
      <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 2, textTransform: "uppercase" }}>{label}</div>
    </div>
  );
}

function PriceTierCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ flex: 1, padding: 12, borderRadius: "var(--radius-md)", background: "var(--surface-sunken)", textAlign: "center" }}>
      <p style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", margin: "0 0 2px" }}>{label}</p>
      <p style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>{money(value)}</p>
    </div>
  );
}

// ── Live Decisions tab ────────────────────────────────────────────────────

function LiveDecisionsTab() {
  const decisions = useApi(useCallback(() => autoPriceOptionsApi.getMatchingLiveDecisions(50), []));
  const rows = decisions.data?.items ?? [];
  return (
    <Card padding={0}>
      <div style={{ padding: 14, borderBottom: "1px solid var(--border)", fontSize: 13, fontWeight: 700 }}>
        Recent Real Matching Decisions
      </div>
      {decisions.loading ? (
        <p style={{ padding: 16, fontSize: 12, color: "var(--text-tertiary)" }}>Loading…</p>
      ) : rows.length === 0 ? (
        <p style={{ padding: 16, fontSize: 12, color: "var(--text-tertiary)" }}>No production matching decisions recorded yet.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Trace", "Job Type", "City", "Candidates", "Excluded", "Selected Provider", "Policy", "Timestamp"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-tertiary)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(row => {
                const nv = row.new_value ?? {};
                return (
                  <tr key={row.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "8px 12px" }}><code style={{ fontSize: 10 }}>{row.entity_id.slice(0, 8)}</code></td>
                    <td style={{ padding: "8px 12px" }}>{String(nv.job_type_id ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>{String(nv.city ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>{String(nv.candidate_count ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>{String(nv.excluded_count ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>{String(nv.selected_provider_id ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>v{String(nv.policy_version ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>{row.created_at ? new Date(row.created_at).toLocaleString() : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ── Policy Reference tab ──────────────────────────────────────────────────

function PolicyReferenceTab() {
  const policy = useApi(useCallback(() => autoPriceOptionsApi.getMatchingPolicy(), []));
  const p: MatchingPolicyManifest | null = policy.data ?? null;

  return (
    <div>
      <div style={{ padding: "10px 14px", marginBottom: 16, borderRadius: "var(--radius-md)",
        background: "var(--surface-sunken)", border: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 10 }}>
        <Shield size={14} style={{ color: "var(--primary)" }} />
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          Code-controlled policy · Admin editing disabled by design.
        </span>
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 16px" }}>
        Visibility only — values come from the deployed backend manifest. Changes require a reviewed code deployment.
      </p>

      {policy.loading || !p ? (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Loading…</p>
      ) : (
        <>
          <Card style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>
              {p.policy_key} · v{p.version} · Scope: {p.scope}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10 }}>
              {p.factors.map(f => (
                <div key={f.factor_key} style={{ padding: 10, borderRadius: "var(--radius-md)", background: "var(--surface-sunken)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{f.label}</span>
                    <span style={{ fontSize: 12, fontWeight: 700 }}>{(f.weight * 100).toFixed(0)}%</span>
                  </div>
                  <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{f.source_engine}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Eligibility Gates</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {p.eligibility_gates.map(g => <Badge key={g} variant="muted" size="sm">{g}</Badge>)}
            </div>
          </Card>

          <Card style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Tie-Break Sequence</p>
            <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)" }}>
              {p.tie_break_policy.map((t, i) => <li key={i}>{t}</li>)}
            </ol>
          </Card>

          <Card>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Missing-Signal Policy</p>
            {Object.entries(p.missing_signal_policy).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 8 }}>
                <p style={{ fontSize: 12, fontWeight: 600, margin: 0, textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{v}</p>
              </div>
            ))}
          </Card>
        </>
      )}
    </div>
  );
}

// ── Audit tab ─────────────────────────────────────────────────────────────

function AuditTab() {
  const audit = useApi(useCallback(() => autoPriceOptionsApi.getMatchingAudit(50), []));
  const rows: MatchingAuditRow[] = audit.data?.items ?? [];
  return (
    <Card padding={0}>
      <div style={{ padding: 14, borderBottom: "1px solid var(--border)", fontSize: 13, fontWeight: 700 }}>
        Diagnostic Audit Trail
      </div>
      {audit.loading ? (
        <p style={{ padding: 16, fontSize: 12, color: "var(--text-tertiary)" }}>Loading…</p>
      ) : rows.length === 0 ? (
        <p style={{ padding: 16, fontSize: 12, color: "var(--text-tertiary)" }}>No diagnostic runs recorded yet.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Actor", "Input Context", "Policy", "Selected", "Candidates/Excluded", "Timestamp", "Trace"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-tertiary)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(row => {
                const nv = row.new_value ?? {};
                return (
                  <tr key={row.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "8px 12px" }}>{row.actor_role ?? "—"}</td>
                    <td style={{ padding: "8px 12px" }}>{String(nv.city ?? "—")} · {String(nv.master_service_id ?? "").slice(0, 8)}</td>
                    <td style={{ padding: "8px 12px" }}>v{String(nv.policy_version ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>{String(nv.selected_provider_id ?? nv.outcome ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>{String(nv.candidate_count ?? "—")}/{String(nv.excluded_count ?? "—")}</td>
                    <td style={{ padding: "8px 12px" }}>{row.created_at ? new Date(row.created_at).toLocaleString() : "—"}</td>
                    <td style={{ padding: "8px 12px" }}><code style={{ fontSize: 10 }}>{row.entity_id.slice(0, 8)}</code></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
