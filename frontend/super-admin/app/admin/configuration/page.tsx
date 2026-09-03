"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Select, Input, Modal, SectionHeader, SummaryCard } from "../../../components/shared/ui";
import {
  configurationApi, settingsAdminApi,
  type ConfigurationListItem, type ConfigurationDetail, type ConfigurationValueVersion,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  FileText, GitCompare, Plus, Lock, ShieldCheck, AlertTriangle, CheckCircle2, RotateCw,
} from "lucide-react";

type Tab = "registry" | "flags" | "changes" | "history" | "audit";

const RISK_VARIANT: Record<string, "success" | "warning" | "danger" | "muted"> = {
  low: "muted", medium: "warning", high: "danger", critical: "danger",
};
const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "muted"> = {
  Active: "success", "Needs Review": "warning", "Code-Controlled Locked": "muted",
  draft: "muted", pending_approval: "warning", scheduled: "warning",
  active: "success", superseded: "muted", rolled_back: "danger",
};

export default function PlatformConfigurationPage() {
  const [tab, setTab] = useState<Tab>("registry");

  return (
    <AdminLayout activeNav="configuration">
      <SectionHeader
        title="Platform Configuration"
        subtitle="Review and safely manage registered Fuvay configuration policies."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="ghost" onClick={() => setTab("audit")}><FileText size={14} style={{ marginRight: 4 }}/>View Audit</Btn>
            <Btn size="sm" variant="ghost" onClick={() => setTab("history")}><GitCompare size={14} style={{ marginRight: 4 }}/>Compare Versions</Btn>
            <Btn size="sm" variant="primary" onClick={() => setTab("registry")}><Plus size={14} style={{ marginRight: 4 }}/>Create Change Request</Btn>
          </div>
        }
      />

      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 16px", borderRadius: "var(--radius-lg)",
        background: "var(--info-bg, rgba(59,130,246,0.08))", border: "1px solid var(--info-border, rgba(59,130,246,0.3))", marginBottom: 16 }}>
        <Lock size={16} style={{ color: "var(--brand)", flexShrink: 0, marginTop: 1 }}/>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Configuration definitions are code-registered. Admins can change approved values only; secrets are managed outside this page.
        </p>
      </div>

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 20 }}>
        {([
          ["registry", "Configuration Registry"], ["flags", "Feature Flags"],
          ["changes", "Change Requests"], ["history", "Version History"], ["audit", "Audit"],
        ] as [Tab, string][]).map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "10px 16px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
            borderBottom: tab === id ? "2px solid var(--brand)" : "2px solid transparent",
            color: tab === id ? "var(--brand)" : "var(--text-secondary)", cursor: "pointer",
          }}>{label}</button>
        ))}
      </div>

      {tab === "registry" && <ConfigurationRegistryTab/>}
      {tab === "flags" && <FeatureFlagsTab/>}
      {tab === "changes" && <ChangeRequestsTab/>}
      {tab === "history" && <VersionHistoryTab/>}
      {tab === "audit" && <AuditTab/>}
    </AdminLayout>
  );
}

// ── Tab 1: Configuration Registry ────────────────────────────────────────────
function ConfigurationRegistryTab() {
  const [ownerFilter, setOwnerFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [scopeFilter, setScopeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const listApi = useApi(useCallback(() => configurationApi.list({
    owner_module: ownerFilter || undefined, risk_level: riskFilter || undefined,
    scope: scopeFilter || undefined, search: search || undefined,
  }), [ownerFilter, riskFilter, scopeFilter, search]));

  const rows = listApi.data?.items ?? [];
  const summary = listApi.data?.summary;
  const selectedRow = rows.find(r => r.key === selectedKey) ?? rows[0] ?? null;

  const ownerModules = Array.from(new Set(rows.map(r => r.owner_module).filter(Boolean))) as string[];

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(100px, 1fr))", gap: 10, marginBottom: 18 }}>
        <Metric icon={<FileText size={16}/>} value={summary?.registered_settings} label="Registered Settings"/>
        <Metric icon={<CheckCircle2 size={16}/>} value={summary?.active} label="Active"/>
        <Metric icon={<AlertTriangle size={16}/>} value={summary?.pending_approval} label="Pending Approval"/>
        <Metric icon={<AlertTriangle size={16}/>} value={summary?.needs_review} label="Needs Review"/>
        <Metric icon={<ShieldCheck size={16}/>} value={summary?.vertical_overrides} label="Vertical Overrides"/>
        <Metric icon={<AlertTriangle size={16}/>} value={summary?.invalid} label="Invalid"/>
        <Metric icon={<RotateCw size={16}/>} value={summary?.rollback_available} label="Rollback Available"/>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Card style={{ padding: 0 }}>
            <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", gap: 8, flexWrap: "wrap" }}>
              <p style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)", flex: "1 1 160px" }}>Registered configuration</p>
              <div style={{ flex: "1 1 180px" }}><Input placeholder="Search setting name or key…" value={search} onChange={setSearch}/></div>
              <Select value={scopeFilter} onChange={setScopeFilter} placeholder="Scope" options={[
                { value: "", label: "All scopes" }, { value: "global", label: "Global" },
                { value: "vertical", label: "Vertical" }, { value: "environment", label: "Environment" },
              ]}/>
              <Select value={ownerFilter} onChange={setOwnerFilter} placeholder="Owner Module" options={[
                { value: "", label: "All modules" }, ...ownerModules.map(m => ({ value: m, label: m })),
              ]}/>
              <Select value={riskFilter} onChange={setRiskFilter} placeholder="Risk" options={[
                { value: "", label: "All risk levels" }, { value: "low", label: "Low" },
                { value: "medium", label: "Medium" }, { value: "high", label: "High" }, { value: "critical", label: "Critical" },
              ]}/>
            </div>

            {listApi.loading ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading configuration…</div>
            ) : rows.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No settings match this filter.</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                      {["Setting", "Owner", "Scope", "Current Value", "Risk", "Status", "Version", ""].map(h => (
                        <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(row => (
                      <tr key={row.key} onClick={() => setSelectedKey(row.key)}
                        style={{ borderBottom: "1px solid var(--border)", cursor: "pointer",
                          background: selectedRow?.key === row.key ? "var(--surface-sunken)" : "transparent",
                          borderLeft: selectedRow?.key === row.key ? "3px solid var(--brand)" : "3px solid transparent" }}>
                        <td style={{ padding: "10px 14px" }}>
                          <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 5 }}>
                            {row.label}{row.locked && <Lock size={11} style={{ color: "var(--warning-text)" }}/>}
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{row.key}</div>
                        </td>
                        <td style={{ padding: "10px 14px" }}>{row.owner_module ?? "—"}</td>
                        <td style={{ padding: "10px 14px" }}>{row.allowed_scopes.join(", ")}</td>
                        <td style={{ padding: "10px 14px" }}>{typeof row.effective_value === "object" ? JSON.stringify(row.effective_value) : String(row.effective_value ?? "—")}</td>
                        <td style={{ padding: "10px 14px" }}><Badge variant={RISK_VARIANT[row.risk_level] ?? "muted"} size="sm">{row.risk_level}</Badge></td>
                        <td style={{ padding: "10px 14px" }}><Badge variant={STATUS_VARIANT[row.status] ?? "muted"} size="sm">{row.status}</Badge></td>
                        <td style={{ padding: "10px 14px" }}>{row.version ? `v${row.version}` : "—"}</td>
                        <td style={{ padding: "10px 14px", textAlign: "right", color: "var(--text-tertiary)" }}>⋮</td>
                      </tr>
                    ))}
                  </tbody>
                </TableSurface>
              </div>
            )}
            <div style={{ padding: "8px 14px", fontSize: 12, color: "var(--text-tertiary)" }}>Showing 1 to {rows.length} of {summary?.registered_settings ?? rows.length} settings</div>
          </Card>
        </div>

        {selectedRow && (
          <div style={{ width: 400, flexShrink: 0 }}>
            <SettingInspector row={selectedRow} onChanged={() => listApi.refetch()}/>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ icon, value, label }: { icon: React.ReactNode; value: React.ReactNode; label: string }) {
  return <SummaryCard label={label} value={value ?? "—"} icon={icon} />;
}

function SettingInspector({ row, onChanged }: { row: ConfigurationListItem; onChanged: () => void }) {
  const [creating, setCreating] = useState(false);
  const [newValue, setNewValue] = useState("");
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const detailApi = useApi(useCallback(() => configurationApi.getDetail(row.key), [row.key]), [row.key]);
  const createAction = useAction((body: { scope_type: string; value: unknown; reason: string }) =>
    configurationApi.createChangeRequest(row.key, body));

  const detail: ConfigurationDetail | undefined = detailApi.data;
  const draft = detail?.history.find(h => h.status === "draft" || h.status === "pending_approval");

  function startCreate() {
    setNewValue(String(detail?.effective.effective_value ?? ""));
    setCreating(true);
    setErrors([]);
  }

  async function validateAndSubmit() {
    let parsed: unknown = newValue;
    if (detail?.data_type === "boolean") parsed = newValue === "true";
    else if (["integer", "duration", "percentage", "decimal"].includes(detail?.data_type ?? "")) parsed = Number(newValue);

    const v = await configurationApi.validate(row.key, "global", parsed);
    setErrors(v.errors);
    if (v.errors.length === 0) {
      const result = await createAction.execute({ scope_type: "global", value: parsed, reason });
      if (result) {
        setCreating(false); setReason(""); detailApi.refetch(); onChanged();
        setToast("Change request created."); setTimeout(() => setToast(null), 3000);
      }
    }
  }

  if (row.locked) {
    return (
      <Card style={{ padding: 16, position: "sticky", top: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>{row.label}</h2>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 12px", fontFamily: "monospace" }}>{row.key}</p>
        <div style={{ padding: "12px 14px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
          <Lock size={16} style={{ color: "var(--warning-text)" }}/>
          <div>
            <p style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Code-Controlled</p>
            <p style={{ fontSize: 12, margin: "2px 0 0", color: "var(--text-secondary)" }}>Critical Locked — no edit action is offered.</p>
          </div>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 12 }}>{detail?.consumer_note}</p>
      </Card>
    );
  }

  return (
    <Card style={{ padding: 16, position: "sticky", top: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{row.label}</h2>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0", fontFamily: "monospace" }}>{row.key}</p>
        </div>
        <Badge variant={STATUS_VARIANT[row.status] ?? "muted"} size="sm">{row.status}</Badge>
      </div>

      {toast && <p style={{ fontSize: 12, color: "var(--success-text)" }}>{toast}</p>}

      {!creating ? (
        <>
          <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "14px 0 8px" }}>Definition</p>
          <SummaryRow label="Type" value={row.data_type}/>
          <SummaryRow label="Owner" value={row.owner_module ?? "—"}/>
          <SummaryRow label="Allowed scopes" value={row.allowed_scopes.join(", ")}/>
          {!row.has_real_consumer && (
            <p style={{ fontSize: 11, color: "var(--warning-text)", margin: "4px 0" }}>
              Registered for governance — no runtime consumer reads this value yet.
            </p>
          )}

          <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Current effective value</p>
          <SummaryRow label="Value" value={typeof detail?.effective.effective_value === "object" ? JSON.stringify(detail?.effective.effective_value) : String(detail?.effective.effective_value ?? "—")}/>
          <SummaryRow label="Source" value={detail?.effective.source ?? "—"}/>
          <SummaryRow label="Fallback" value={String(detail?.effective.fallback_value ?? "—")}/>

          {(row.data_type === "duration" || row.data_type === "integer" || row.data_type === "percentage") && (
            <>
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Constraints</p>
              <SummaryRow label="Minimum" value={String(detail?.minimum ?? "—")}/>
              <SummaryRow label="Maximum" value={String(detail?.maximum ?? "—")}/>
              <SummaryRow label="Unit" value={detail?.unit ?? "—"}/>
            </>
          )}

          <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Impact</p>
          <SummaryRow label="Snapshot behavior" value={(detail?.snapshot_behavior ?? "—").replace(/_/g, " ")}/>
          <SummaryRow label="Requires approval" value={detail?.approval_required ? "Yes" : "No"}/>
          <SummaryRow label="Requires restart" value={detail?.restart_required ? "Yes" : "No"}/>

          {draft && (
            <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: "var(--radius-md)", background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--warning-text)", margin: 0 }}>A {draft.status.replace(/_/g, " ")} change request exists</p>
              <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "4px 0 0" }}>{draft.change_reason}</p>
            </div>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <Btn variant="primary" size="sm" onClick={startCreate} disabled={!row.admin_mutable}>Create Configuration Change</Btn>
          </div>
        </>
      ) : (
        <>
          <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "8px 0" }}>Create Configuration Change</p>
          <SummaryRow label="Setting (read-only)" value={row.label}/>
          <SummaryRow label="Scope (read-only)" value="Global"/>
          <SummaryRow label="Current value" value={String(detail?.effective.effective_value ?? "—")}/>
          <Field label="New value">
            {detail?.data_type === "boolean" ? (
              <select value={newValue} onChange={e => setNewValue(e.target.value)} style={inputStyle}>
                <option value="true">true</option><option value="false">false</option>
              </select>
            ) : (
              <input type={["integer", "duration", "percentage", "decimal"].includes(detail?.data_type ?? "") ? "number" : "text"}
                value={newValue} onChange={e => setNewValue(e.target.value)} style={inputStyle}/>
            )}
          </Field>
          <Field label="Change reason">
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={2} style={{ ...inputStyle, resize: "vertical" }}/>
          </Field>
          {errors.length > 0 && (
            <div style={{ marginTop: 8, padding: "8px 10px", borderRadius: "var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              {errors.map(e => <p key={e} style={{ fontSize: 11, color: "var(--danger-text)", margin: "2px 0" }}>{e}</p>)}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <Btn variant="ghost" size="sm" onClick={() => setCreating(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" onClick={validateAndSubmit} disabled={!reason.trim() || createAction.loading}>
              {createAction.loading ? "Submitting…" : "Submit for Approval"}
            </Btn>
          </div>
        </>
      )}
    </Card>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6, gap: 8 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 500, textAlign: "right" }}>{value}</span>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginTop: 10 }}>
      {label}
      <div style={{ marginTop: 4 }}>{children}</div>
    </label>
  );
}

const inputStyle: React.CSSProperties = { width: "100%", padding: "7px 9px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box" };

// ── Tab 2: Feature Flags (reuses existing FeatureFlag rows, unchanged) ──────
function FeatureFlagsTab() {
  const flagsApi = useApi(useCallback(() => settingsAdminApi.listFeatureFlags(), []), []);
  const flags = flagsApi.data?.flags ?? [];
  return (
    <Card style={{ padding: 0 }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          Feature flags are separate from Business Vertical enablement — they must never bypass authorization,
          tenant isolation, workflow gates, or financial integrity.
        </p>
      </div>
      {flagsApi.loading ? (
        <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
      ) : flags.length === 0 ? (
        <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No feature flags registered.</div>
      ) : (
        <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
              {["Flag", "Owner", "Status", "Rollout"].map(h => (
                <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {flags.map(f => (
              <tr key={f.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "9px 14px", fontWeight: 600 }}>{f.label}<div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{f.flag_key}</div></td>
                <td style={{ padding: "9px 14px" }}>{f.owner_module ?? "—"}</td>
                <td style={{ padding: "9px 14px" }}><Badge variant={f.status === "enabled" ? "success" : "muted"} size="sm">{f.status}</Badge></td>
                <td style={{ padding: "9px 14px" }}>{f.rollout_type}{f.rollout_percent ? ` (${f.rollout_percent}%)` : ""}</td>
              </tr>
            ))}
          </tbody>
        </TableSurface>
      )}
    </Card>
  );
}

// ── Tab 3: Change Requests (cross-setting queue) ────────────────────────────
function ChangeRequestsTab() {
  const [toast, setToast] = useState<string | null>(null);
  const crApi = useApi(useCallback(() => configurationApi.listChangeRequests(), []), []);
  const approveAction = useAction((id: string) => configurationApi.approve(id));
  const activateAction = useAction((id: string) => configurationApi.activate(id));
  const [rollbackTarget, setRollbackTarget] = useState<ConfigurationValueVersion | null>(null);
  const [rollbackReason, setRollbackReason] = useState("");
  const rollbackAction = useAction((id: string, reason: string) => configurationApi.rollback(id, reason));

  const items = crApi.data?.items ?? [];

  function notify(msg: string) { setToast(msg); setTimeout(() => setToast(null), 3000); }

  async function handleApprove(id: string) {
    try { await approveAction.execute(id); crApi.refetch(); notify("Change request approved."); }
    catch (e) { notify(e instanceof Error ? e.message : "Approval failed."); }
  }
  async function handleActivate(id: string) {
    try { await activateAction.execute(id); crApi.refetch(); notify("Change activated."); }
    catch (e) { notify(e instanceof Error ? e.message : "Activation failed."); }
  }
  async function handleRollback() {
    if (!rollbackTarget || !rollbackReason.trim()) return;
    await rollbackAction.execute(rollbackTarget.id, rollbackReason.trim());
    setRollbackTarget(null); setRollbackReason("");
    crApi.refetch(); notify("Rolled back.");
  }

  return (
    <div>
      {toast && <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10 }}>{toast}</p>}
      <Card style={{ padding: 0 }}>
        {crApi.loading ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
        ) : items.length === 0 ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No open change requests.</div>
        ) : (
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                {["Setting", "Scope", "New Value", "Status", "Reason", "Created", "Actions"].map(h => (
                  <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(cr => (
                <tr key={cr.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "9px 14px", fontWeight: 600 }}>{cr.label}</td>
                  <td style={{ padding: "9px 14px" }}>{cr.scope_type} / {cr.scope_id}</td>
                  <td style={{ padding: "9px 14px" }}>{typeof cr.value === "object" ? JSON.stringify(cr.value) : String(cr.value)}</td>
                  <td style={{ padding: "9px 14px" }}><Badge variant={STATUS_VARIANT[cr.status] ?? "muted"} size="sm">{cr.status.replace(/_/g, " ")}</Badge></td>
                  <td style={{ padding: "9px 14px", color: "var(--text-secondary)", maxWidth: 200 }}>{cr.change_reason}</td>
                  <td style={{ padding: "9px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>{new Date(cr.created_at).toLocaleString()}</td>
                  <td style={{ padding: "9px 14px", display: "flex", gap: 4 }}>
                    {cr.status === "pending_approval" && (
                      <Btn size="xs" variant="secondary" onClick={() => handleApprove(cr.id)} loading={approveAction.loading}>Approve</Btn>
                    )}
                    {(cr.status === "approved" || cr.status === "draft" || cr.status === "scheduled") && (
                      <Btn size="xs" variant="primary" onClick={() => handleActivate(cr.id)} loading={activateAction.loading}>Activate</Btn>
                    )}
                    {cr.status === "active" && (
                      <Btn size="xs" variant="ghost" onClick={() => setRollbackTarget(cr)}>Rollback</Btn>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        )}
      </Card>

      {rollbackTarget && (
        <Modal open onClose={() => setRollbackTarget(null)} title={`Roll back ${rollbackTarget.label}`} size="sm">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>This creates a new active version restoring the prior value — history is never mutated.</p>
            <textarea value={rollbackReason} onChange={e => setRollbackReason(e.target.value)} rows={3} placeholder="Rollback reason (required)" style={inputStyle}/>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Btn size="sm" variant="ghost" onClick={() => setRollbackTarget(null)}>Cancel</Btn>
              <Btn size="sm" variant="primary" disabled={!rollbackReason.trim() || rollbackAction.loading} onClick={handleRollback}>Confirm Rollback</Btn>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Tab 4: Version History (cross-setting) ──────────────────────────────────
function VersionHistoryTab() {
  const historyApi = useApi(useCallback(() => configurationApi.listVersionHistory(), []), []);
  const items = historyApi.data?.items ?? [];
  return (
    <Card style={{ padding: 0 }}>
      {historyApi.loading ? (
        <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
      ) : items.length === 0 ? (
        <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No configuration versions recorded yet.</div>
      ) : (
        <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
              {["Setting", "Version", "Status", "Value", "Effective From", "Created"].map(h => (
                <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(v => (
              <tr key={v.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "9px 14px", fontWeight: 600 }}>{v.label}</td>
                <td style={{ padding: "9px 14px" }}>v{v.version_number}</td>
                <td style={{ padding: "9px 14px" }}><Badge variant={STATUS_VARIANT[v.status] ?? "muted"} size="sm">{v.status}</Badge></td>
                <td style={{ padding: "9px 14px" }}>{typeof v.value === "object" ? JSON.stringify(v.value) : String(v.value)}</td>
                <td style={{ padding: "9px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>{v.effective_from ? new Date(v.effective_from).toLocaleString() : "—"}</td>
                <td style={{ padding: "9px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>{new Date(v.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </TableSurface>
      )}
    </Card>
  );
}

// ── Tab 5: Audit ──────────────────────────────────────────────────────────
function AuditTab() {
  const auditApi = useApi(useCallback(() => configurationApi.getAudit(), []), []);
  const items = auditApi.data?.items ?? [];
  return (
    <Card style={{ padding: 0 }}>
      {auditApi.loading ? (
        <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
      ) : items.length === 0 ? (
        <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No configuration changes recorded yet.</div>
      ) : (
        <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
              {["Key", "Action", "Old Value", "New Value", "Reason", "When"].map(h => (
                <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(a => (
              <tr key={a.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "9px 14px", fontFamily: "monospace", fontSize: 12 }}>{a.key}</td>
                <td style={{ padding: "9px 14px" }}>{a.action_type.replace("change_request.", "")}</td>
                <td style={{ padding: "9px 14px" }}>{a.old_value === null ? "—" : String(a.old_value)}</td>
                <td style={{ padding: "9px 14px" }}>{String(a.new_value)}</td>
                <td style={{ padding: "9px 14px", color: "var(--text-secondary)" }}>{a.reason ?? "—"}</td>
                <td style={{ padding: "9px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>{a.created_at ? new Date(a.created_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </TableSurface>
      )}
    </Card>
  );
}
