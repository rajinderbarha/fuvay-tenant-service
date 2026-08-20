"use client";
import React, { useCallback, useMemo, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn } from "../../../../components/shared/ui";
import {
  verticalCatalogApi, type VerticalDetail, type VerticalCapabilityRegistry,
  type VerticalDependencyHealth, type VerticalAuditEntry,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  FileText, ShieldCheck, Sparkles, RefreshCw, Users, Briefcase, Package,
  ShieldAlert, AlertTriangle, CheckCircle2, XCircle, HelpCircle, Search, Shield,
  ArrowUpRight,
} from "lucide-react";

// HOME-SERVICES-OPERATIONS / Platform > Business Verticals > [key] >
// Capabilities & Policies. This page is primarily a READ-ONLY projection of
// capabilities/policies owned by their canonical engines. The only editable
// control anywhere on this page is vertical availability itself.

const TABS = ["overview", "capabilities", "dependencies", "impact", "audit"] as const;
type TabKey = typeof TABS[number];
const TAB_LABEL: Record<TabKey, string> = {
  overview: "Overview", capabilities: "Capabilities & Policies", dependencies: "Dependencies",
  impact: "Impact", audit: "Audit",
};

const STATUS_BADGE: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  active: "success", enforced: "success", healthy: "success",
  disabled: "muted", degraded: "warning", unverified: "muted",
  unavailable: "danger", disabled_by_vertical: "muted", provider_direct: "info",
};

export default function VerticalDetailPage() {
  const params = useParams();
  const search = useSearchParams();
  const router = useRouter();
  const key = String(params.key);
  const requestedTab = search.get("tab") as TabKey | null;
  const [tab, setTab] = useState<TabKey>(requestedTab && TABS.includes(requestedTab) ? requestedTab : "capabilities");
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [reason, setReason] = useState("");
  const [capSearch, setCapSearch] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");

  const vApi = useApi(useCallback(() => verticalCatalogApi.getVertical(key), [key]));
  const capApi = useApi(useCallback(() => verticalCatalogApi.getCapabilities(key), [key]));
  const healthApi = useApi(useCallback(() => verticalCatalogApi.getDependencyHealth(key), [key]));
  const impactApi = useApi(useCallback(() => verticalCatalogApi.getDisableImpact(key), [key]));
  const auditApi = useApi(useCallback(() => verticalCatalogApi.getAuditLog(key), [key]), [key], { enabled: tab === "audit" });

  const disableAction = useAction((k: string, r: string) => verticalCatalogApi.disableVertical(k, r));
  const enableAction = useAction((k: string) => verticalCatalogApi.enableVertical(k));

  const v = vApi.data as VerticalDetail | null;
  const caps = capApi.data as VerticalCapabilityRegistry | null;
  const health = healthApi.data as VerticalDependencyHealth | null;
  const impact = impactApi.data as Record<string, unknown> | null;
  const currentModules = useMemo(
    () => (v?.modules ?? []).filter(module => module.navigation_status === "available"),
    [v?.modules],
  );
  const enabledModules = currentModules.filter(module => module.is_enabled).length;
  const configurationErrors = health?.checks.filter(check => check.required && check.status !== "healthy").length ?? null;

  function setTabParam(t: TabKey) {
    setTab(t);
    router.replace(`/admin/verticals/${key}?tab=${t}`);
  }

  async function confirmDisable() {
    if (!reason.trim()) return;
    const result = await disableAction.execute(key, reason.trim());
    if (result) { setShowDisableModal(false); setReason(""); vApi.refetch(); impactApi.refetch(); }
  }

  async function handleEnable() {
    const result = await enableAction.execute(key);
    if (result) vApi.refetch();
  }

  const allCapabilities = (caps?.groups ?? []).flatMap(g => g.capabilities.map(c => ({ ...c, group: g.name })));
  const owners = Array.from(new Set(allCapabilities.map(c => c.owner)));
  const filteredCapabilities = allCapabilities.filter(c =>
    (!capSearch || c.name.toLowerCase().includes(capSearch.toLowerCase())) &&
    (!ownerFilter || c.owner === ownerFilter));
  const groupedFiltered = (caps?.groups ?? []).map(g => ({
    ...g, capabilities: g.capabilities.filter(c => filteredCapabilities.some(f => f.name === c.name)),
  })).filter(g => g.capabilities.length > 0);

  return (
    <AdminLayout activeNav="verticals">
      <div style={{ padding: "0 4px" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 4px" }}>
          Platform / Business Verticals / {v?.label ?? key}
        </p>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 14 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>{v?.label ?? key}</h1>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 8px" }}>
              Review vertical capabilities, deployed policies and runtime dependencies.
            </p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <Badge variant={v?.is_enabled ? "success" : "muted"} size="sm">{v?.is_enabled ? "Active" : "Disabled"}</Badge>
              <Badge variant="info" size="sm">{v?.label ?? key}</Badge>
              <Badge variant="muted" size="sm">Policy-controlled</Badge>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn variant="ghost" size="sm" onClick={() => setTabParam("audit")}><FileText size={14} style={{ marginRight: 4 }}/>View Audit</Btn>
            <Btn variant="ghost" size="sm" onClick={() => { healthApi.refetch(); }}><ShieldCheck size={14} style={{ marginRight: 4 }}/>Refresh Dependency Health</Btn>
            <Btn variant="primary" size="sm" onClick={() => setTabParam("impact")}><Sparkles size={14} style={{ marginRight: 4 }}/>Manage Availability</Btn>
          </div>
        </div>

        <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "1px solid var(--border)", overflowX: "auto" }} role="tablist">
          {TABS.map(t => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTabParam(t)}
              style={{ padding: "8px 14px", fontSize: 13, fontWeight: 600, border: "none", background: "none",
                borderBottom: `2px solid ${tab === t ? "var(--brand)" : "transparent"}`,
                color: tab === t ? "var(--text-primary)" : "var(--text-secondary)", cursor: "pointer", whiteSpace: "nowrap" }}>
              {TAB_LABEL[t]}
            </button>
          ))}
        </div>

        {tab === "overview" && (
          <Card style={{ padding: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 14 }}>
              <Metric icon={<Users size={16}/>} value={(impact?.active_tenant_enrollments as number) ?? "—"} label="Active tenants"/>
              <Metric icon={<Briefcase size={16}/>} value={(impact?.active_jobs as number) ?? "—"} label="Active jobs"/>
              <Metric icon={<Package size={16}/>} value={`${enabledModules} / ${currentModules.length}`} label="Admin pages enabled"/>
              <Metric icon={<ShieldCheck size={16}/>} value={health ? `${health.healthy_count} / ${health.total_count}` : "—"} label="Dependencies healthy"/>
              <Metric icon={<AlertTriangle size={16}/>} value={configurationErrors ?? "—"} label="Required checks unresolved"/>
            </div>
          </Card>
        )}

        {tab === "capabilities" && (
          <>
            <Card style={{ padding: 20, marginBottom: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 14 }}>
                <Metric icon={<Users size={16}/>} value={(impact?.active_tenant_enrollments as number) ?? "—"} label="Active tenants"/>
                <Metric icon={<Briefcase size={16}/>} value={(impact?.active_jobs as number) ?? "—"} label="Active jobs"/>
                <Metric icon={<Package size={16}/>} value={`${enabledModules} / ${currentModules.length}`} label="Admin pages enabled"/>
                <Metric icon={<ShieldCheck size={16}/>} value={health ? `${health.healthy_count} / ${health.total_count}` : "—"} label="Dependencies healthy"/>
                <Metric icon={<AlertTriangle size={16}/>} value={configurationErrors ?? "—"} label="Required checks unresolved"/>
              </div>
            </Card>

            <Card style={{ padding: 0, marginBottom: 14 }}>
              <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
                <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 2px", color: "var(--text-primary)" }}>Current admin workspaces</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                  Only implemented, project-scoped Home Services workspaces are listed here. Retired and placeholder module routes are hidden from admin navigation.
                </p>
              </div>
              {currentModules.length === 0 ? (
                <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No current workspaces are assigned.</div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10, padding: 16 }}>
                  {currentModules.map(module => (
                    <Link key={module.key} href={module.admin_path || "/admin/verticals/home_services?tab=capabilities"}
                      style={{ display: "flex", alignItems: "center", gap: 10, padding: "11px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: module.is_enabled ? "var(--surface)" : "var(--surface-sunken)", textDecoration: "none", color: "inherit" }}>
                      <Package size={15} style={{ color: module.is_enabled ? "var(--brand)" : "var(--text-tertiary)", flexShrink: 0 }}/>
                      <span style={{ flex: 1, minWidth: 0 }}>
                        <span style={{ display: "block", fontSize: 13, fontWeight: 700, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{module.label}</span>
                        <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{module.module_group || "Admin workspace"}{module.is_required ? " · Required" : ""}</span>
                      </span>
                      <Badge variant={module.is_enabled ? "success" : "muted"} size="sm">{module.is_enabled ? "Shown" : "Hidden"}</Badge>
                      <ArrowUpRight size={13} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>
                    </Link>
                  ))}
                </div>
              )}
            </Card>

            <Card style={{ padding: 0, marginBottom: 14 }}>
              <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
                <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 2px", color: "var(--text-primary)" }}>Capability registry</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
                  Runtime capabilities are derived from canonical engines. Editable controls live with their owning domain.
                </p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <div style={{ position: "relative", flex: "1 1 220px" }}>
                    <Search size={13} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
                    <input value={capSearch} onChange={e => setCapSearch(e.target.value)} placeholder="Search capabilities…"
                      style={{ width: "100%", padding: "7px 10px 7px 28px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                        background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}/>
                  </div>
                  <select value={ownerFilter} onChange={e => setOwnerFilter(e.target.value)}
                    style={{ padding: "7px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                      background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
                    <option value="">All ownership</option>
                    {owners.map((o: string) => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
              </div>

              {capApi.error ? (
                <div style={{ padding: 24, textAlign: "center", color: "var(--danger-text)", fontSize: 13 }}>{capApi.error}</div>
              ) : capApi.loading ? (
                <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading capabilities…</div>
              ) : groupedFiltered.length === 0 ? (
                <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No capabilities match this filter.</div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  {groupedFiltered.map(g => (
                    <div key={g.name}>
                      <div style={{ padding: "8px 16px", background: "var(--surface-sunken)", fontSize: 11, fontWeight: 700,
                        color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{g.name}</div>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                        <tbody>
                          {g.capabilities.map(c => (
                            <tr key={c.name} style={{ borderBottom: "1px solid var(--border)" }}>
                              <td style={{ padding: "10px 16px", width: 200 }}>{c.name}</td>
                              <td style={{ padding: "10px 16px", width: 110 }}>
                                <Badge variant={STATUS_BADGE[c.status] ?? "muted"} size="sm">{c.status.replace(/_/g, " ")}</Badge>
                              </td>
                              <td style={{ padding: "10px 16px", width: 150 }}>
                                <Badge variant="info" size="sm">{c.owner}</Badge>
                              </td>
                              <td style={{ padding: "10px 16px", width: 170, color: "var(--text-secondary)" }}>{c.source ?? "Canonical backend"}</td>
                              <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>{c.runtime_behaviour}</td>
                              <td style={{ padding: "10px 16px", textAlign: "right", whiteSpace: "nowrap" }}>
                                {c.action_href && (
                                  <Link href={c.action_href} style={{ fontSize: 12, color: "var(--primary)", textDecoration: "none" }}>{c.action_label} ↗</Link>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card style={{ padding: 16 }}>
              <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px", color: "var(--text-primary)" }}>Configuration boundaries</p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, marginBottom: 14 }}>
                <BoundaryTile icon={<Shield size={14}/>} text="Admin controls catalog structure and vertical availability"/>
                <BoundaryTile icon={<Shield size={14}/>} text="Tenant controls service prices, visit fees and coverage"/>
                <BoundaryTile icon={<Shield size={14}/>} text="Matching and execution gates are code-controlled"/>
                <BoundaryTile icon={<Shield size={14}/>} text="Historical jobs retain snapshotted policy versions"/>
              </div>
              {caps?.policy_boundaries && (
                <>
                  <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>Policy boundaries</p>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
                    {caps.policy_boundaries.map(p => (
                      <div key={p.policy} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                        <span style={{ color: "var(--text-secondary)" }}>{p.policy}</span>
                        <Badge variant={p.owner === "Admin-controlled" ? "warning" : p.owner === "Tenant-owned" ? "success" : "info"} size="sm">{p.owner}</Badge>
                      </div>
                    ))}
                  </div>
                </>
              )}
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Admin-navigation switches are managed separately and never change these runtime capabilities.</p>
            </Card>
          </>
        )}

        {tab === "dependencies" && (
          <Card style={{ padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <p style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Dependency health</p>
              <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                {health ? `${health.healthy_count} / ${health.total_count} healthy` : "—"}
              </span>
            </div>
            {healthApi.error ? (
              <p style={{ fontSize: 13, color: "var(--danger-text)" }}>{healthApi.error}</p>
            ) : healthApi.loading ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Checking dependencies…</p>
            ) : (health?.checks ?? []).length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No dependency mappings are configured.</p>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
                {(health?.checks ?? []).map(c => (
                  <div key={c.engine_key} style={{ padding: "10px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                    display: "flex", alignItems: "flex-start", gap: 8 }}>
                    {c.status === "healthy" ? <CheckCircle2 size={15} style={{ color: "var(--success-text)", flexShrink: 0 }}/>
                      : c.status === "unverified" ? <HelpCircle size={15} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>
                      : <XCircle size={15} style={{ color: "var(--danger-text)", flexShrink: 0 }}/>}
                    <div>
                      <p style={{ fontSize: 13, fontWeight: 600, margin: 0, color: "var(--text-primary)" }}>{c.engine_key.replaceAll("_", " ")}</p>
                      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{c.detail || `${c.required ? "Required" : "Optional"}${c.last_checked_at ? ` · checked ${new Date(c.last_checked_at).toLocaleString()}` : " · no persisted health check"}`}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {tab === "impact" && (
          <Card style={{ padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div>
                <p style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Vertical availability</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                  {v?.is_enabled ? "Active — new activity is currently allowed." : `Disabled${v?.disable_reason ? `: ${v.disable_reason}` : ""}`}
                </p>
              </div>
              <Badge variant={v?.is_enabled ? "success" : "muted"} size="sm">{v?.is_enabled ? "Active" : "Disabled"}</Badge>
            </div>

            {impact && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, marginBottom: 14 }}>
                {Object.entries(impact).filter(([k]) => !["vertical_key", "enrollments_by_status", "note"].includes(k)).map(([k, val]) => (
                  <div key={k} style={{ padding: "10px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                    <p style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{String(val)}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0", textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</p>
                  </div>
                ))}
              </div>
            )}
            {impact?.note && <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 14px" }}>{String(impact.note)}</p>}

            {v?.is_enabled ? (
              <Btn variant="primary" size="sm" onClick={() => setShowDisableModal(true)}>Disable {v?.label}</Btn>
            ) : (
              <Btn variant="primary" size="sm" onClick={handleEnable} disabled={enableAction.loading}>
                {enableAction.loading ? "Enabling…" : `Enable ${v?.label}`}
              </Btn>
            )}
          </Card>
        )}

        {tab === "audit" && (
          <Card style={{ padding: 0 }}>
            {auditApi.error ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--danger-text)", fontSize: 13 }}>{auditApi.error}</div>
            ) : auditApi.loading ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading audit history…</div>
            ) : ((auditApi.data as { items: VerticalAuditEntry[] } | null)?.items ?? []).length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No vertical or navigation changes recorded yet.</div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                    {["Action", "Notes", "When"].map(h => (
                      <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {((auditApi.data as { items: VerticalAuditEntry[] }).items).map(e => (
                    <tr key={e.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "9px 14px" }}>{e.action_type}</td>
                      <td style={{ padding: "9px 14px", color: "var(--text-secondary)" }}>{e.notes ?? "—"}</td>
                      <td style={{ padding: "9px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>
                        {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        )}
      </div>

      {showDisableModal && (
        <div role="dialog" aria-modal="true" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <Card style={{ padding: 20, width: 420 }}>
            <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
              <ShieldAlert size={16} style={{ color: "var(--danger-text)" }}/> Disable {v?.label}
            </p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>
              This blocks NEW registrations, tenant setup, bookings and matching. Existing jobs continue safely.
            </p>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
              Reason (required)
            </label>
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, marginBottom: 14, boxSizing: "border-box" }}/>
            {disableAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "0 0 10px" }}>{disableAction.error}</p>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Btn variant="ghost" size="sm" onClick={() => setShowDisableModal(false)}>Cancel</Btn>
              <Btn variant="primary" size="sm" disabled={!reason.trim() || disableAction.loading} onClick={confirmDisable}>
                {disableAction.loading ? "Disabling…" : "Confirm Disable"}
              </Btn>
            </div>
          </Card>
        </div>
      )}
    </AdminLayout>
  );
}

function Metric({ icon, value, label }: { icon: React.ReactNode; value: React.ReactNode; label: string }) {
  return (
    <div style={{ padding: "12px 14px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface)" }}>
      <div style={{ color: "var(--text-tertiary)", marginBottom: 6 }}>{icon}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{label}</div>
    </div>
  );
}

function BoundaryTile({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", padding: "10px 12px", borderRadius: "var(--radius-md)",
      border: "1px solid var(--border)" }}>
      <span style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: 1 }}>{icon}</span>
      <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{text}</span>
    </div>
  );
}
