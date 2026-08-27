"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useState, useCallback, useEffect } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import {
  PageHeader, Card, Button, Modal, Input, Skeleton,
  StatusBadge as DsStatusBadge, Alert,
} from "@serviceos/design-system";
import {
  settingsApi, complianceApi, securityApi, workspaceSettingsApi,
  type SettingEntry, type Webhook, type WebhookDelivery,
  type ConsentCheck, type DeletionRequestResult, type ExportRequestResult,
  type SecurityApiKey, type SecurityApiKeyCreated, type IpBlockCheck,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const SOURCE_STATUS: Record<string,string> = { tenant:"active", plan:"info", platform:"neutral", code_default:"neutral" };
const SOURCE_LABEL: Record<string,string> = { tenant:"Your Override", plan:"Plan Default", platform:"Platform Default", code_default:"System Default" };

const CONSENT_TYPES = [
  { key:"data_processing",    label:"Data Processing",      hint:"Required to operate your account and deliver services." },
  { key:"marketing",          label:"Marketing Communications", hint:"Promotional emails, SMS and offers." },
  { key:"analytics",         label:"Analytics",             hint:"Usage analytics to improve the product." },
  { key:"third_party_share", label:"Third-Party Sharing",   hint:"Sharing data with partner integrations." },
  { key:"push_notifications",label:"Push Notifications",    hint:"Mobile/web push alerts." },
] as const;

const ACTIVITY_TYPES = [
  { key:"failed_login",       label:"Repeated failed login attempts" },
  { key:"unusual_location",   label:"Login from an unrecognised location" },
  { key:"mass_data_export",   label:"Unexpected bulk data export" },
  { key:"excessive_requests", label:"Excessive API/request activity" },
] as const;

const API_KEYS_ENABLED = false;

export default function SettingsPage() {
  const [tab, setTab] = useState<"workspace"|"team"|"activity"|"general"|"webhooks"|"deliveries"|"privacy"|"security">("workspace");

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("tab");
    if (["workspace", "team", "activity", "general", "webhooks", "deliveries", "privacy", "security"].includes(requested ?? "")) {
      setTab(requested as typeof tab);
    }
  }, []);

  // Workspace settings (real: identity, regional prefs, business hours,
  // controlled policy -- see workspace_settings_service.py)
  const workspaceGeneral = useApi(() => workspaceSettingsApi.getGeneral(), []);
  const teamAccess = useApi(() => workspaceSettingsApi.getTeamAccess(), []);
  const wsActivity = useApi(() => workspaceSettingsApi.getActivity(30), []);
  const [wsEdits, setWsEdits] = useState<Record<string, string>>({});
  const wsSaveAction = useAction(async () => {
    await workspaceSettingsApi.updateGeneral(wsEdits, workspaceGeneral.data?.configuration_version ?? null);
    setWsEdits({});
    await workspaceGeneral.refetch();
    notify("Workspace settings saved.");
  });

  // General settings
  const settings = useApi(() => settingsApi.get(), []);
  const [editKey,    setEditKey]    = useState("");
  const [editVal,    setEditVal]    = useState("");
  // A tenant override is an audited change and the API refuses one without a
  // reason; it is stored alongside the value.
  const [editReason, setEditReason] = useState("");
  const [editModal,  setEditModal]  = useState(false);
  const [deleteKey,  setDeleteKey]  = useState("");
  const [confirmDel, setConfirmDel] = useState(false);
  const [toast,      setToast]      = useState("");

  // Webhooks
  const webhooks   = useApi(() => settingsApi.listWebhooks(), []);
  const deliveries = useApi(() => settingsApi.listDeliveries({ limit: 30 }), [tab === "deliveries"]);
  const [whModal,  setWhModal]  = useState(false);
  const [whUrl,    setWhUrl]    = useState("");
  const [whDesc,   setWhDesc]   = useState("");
  // Chosen from the catalogue the API returns. This used to be a free-text
  // comma-separated string pre-filled with "job.completed,booking.confirmed" —
  // and `job.completed` is not a real event (the catalogue has job.created /
  // job.status_changed / job.closed), so the default itself was invalid.
  const [whEvents, setWhEvents] = useState<string[]>([]);

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const updateSetting = useAction(async () => {
    await settingsApi.update(editKey, editVal, editReason.trim());
    await settings.refetch();
    setEditModal(false);
    setEditReason("");
    notify("Setting saved.");
  });

  const deleteSetting = useAction(async () => {
    await settingsApi.delete(deleteKey);
    await settings.refetch();
    setConfirmDel(false);
    notify("Override removed.");
  });

  const createWebhook = useAction(async () => {
    await settingsApi.createWebhook(whUrl.trim(), whEvents, whDesc.trim() || undefined);
    await webhooks.refetch();
    setWhModal(false);
    setWhUrl(""); setWhDesc(""); setWhEvents([]);
    notify("Webhook created.");
  });

  const deleteWebhook = useAction(async (id: string) => {
    await settingsApi.deleteWebhook(id);
    await webhooks.refetch();
    notify("Webhook deleted.");
  });

  const testWebhook = useAction(async (id: string) => {
    await settingsApi.testWebhook(id);
    notify("Test event sent.");
  });

  const pauseWebhook = useAction(async (id: string) => {
    await settingsApi.pauseWebhook(id);
    await webhooks.refetch();
    notify("Webhook paused.");
  });

  const resumeWebhook = useAction(async (id: string) => {
    await settingsApi.resumeWebhook(id);
    await webhooks.refetch();
    notify("Webhook resumed.");
  });

  // ── Privacy & Data (Compliance Engine) ───────────────────────────────────────
  const consents = useApi(useCallback(async () => {
    const results = await Promise.all(CONSENT_TYPES.map(c => complianceApi.checkConsent(c.key)));
    return results.reduce((acc, r) => { acc[r.consent_type] = r; return acc; }, {} as Record<string, ConsentCheck>);
  }, []), []);

  const [exportResult,   setExportResult]   = useState<ExportRequestResult | null>(null);
  const [deletionResult, setDeletionResult] = useState<DeletionRequestResult | null>(null);
  const [deleteConfirm,  setDeleteConfirm]  = useState(false);

  const toggleConsent = useAction(async (consentType: string, currentlyGranted: boolean) => {
    if (currentlyGranted) await complianceApi.withdrawConsent(consentType);
    else                   await complianceApi.recordConsent(consentType, "granted");
    await consents.refetch();
    notify(currentlyGranted ? "Consent withdrawn." : "Consent granted.");
  });

  const requestExport = useAction(async () => {
    const result = await complianceApi.requestExport([], "json");
    setExportResult(result);
    notify("Data export requested — you'll be notified within 72 hours.");
  });

  const refreshExport = useAction(async () => {
    if (!exportResult) return;
    const result = await complianceApi.getExportStatus(exportResult.request_id);
    setExportResult(result);
  });

  const requestDeletion = useAction(async () => {
    const result = await complianceApi.requestDeletion("User-initiated account deletion request");
    setDeletionResult(result);
    setDeleteConfirm(false);
    notify("Deletion request submitted — processed within 72 hours.");
  });

  const refreshDeletion = useAction(async () => {
    if (!deletionResult) return;
    const result = await complianceApi.getDeletionRequest(deletionResult.request_id);
    setDeletionResult(result);
  });

  // ── Security (Security Engine — integration keys, blocklist, threats) ──────
  const secKeys = useApi(useCallback(() => API_KEYS_ENABLED
    ? securityApi.listApiKeys()
    : Promise.resolve({ api_keys: [] }), []));
  const [secKeyModal,  setSecKeyModal]  = useState(false);
  const [secKeyResult, setSecKeyResult] = useState<SecurityApiKeyCreated | null>(null);
  const [secKeyName,   setSecKeyName]   = useState("");
  const [secKeyScopes, setSecKeyScopes] = useState("read:jobs,read:bookings");
  const [ipQuery,      setIpQuery]      = useState("");
  const [ipResult,     setIpResult]     = useState<IpBlockCheck | null>(null);
  const [reportType,   setReportType]   = useState<string>(ACTIVITY_TYPES[0].key);

  const createSecKey = useAction(async () => {
    const scopes = secKeyScopes.split(",").map(s => s.trim()).filter(Boolean);
    const result = await securityApi.createApiKey(secKeyName, scopes);
    setSecKeyResult(result);
    setSecKeyName(""); setSecKeyScopes("read:jobs,read:bookings");
    await secKeys.refetch();
  });

  const rotateSecKey = useAction(async (keyId: string) => {
    const result = await securityApi.rotateApiKey(keyId);
    setSecKeyResult(result);
    setSecKeyModal(true);
    await secKeys.refetch();
  });

  const revokeSecKey = useAction(async (keyId: string) => {
    await securityApi.revokeApiKey(keyId, "Revoked by tenant owner");
    await secKeys.refetch();
    notify("Integration key revoked.");
  });

  const checkIp = useAction(async () => {
    const result = await securityApi.checkIpBlocked(ipQuery);
    setIpResult(result);
  });

  const reportActivity = useAction(async () => {
    await securityApi.reportActivity(reportType);
    notify("Activity reported to the security team.");
  });

  const TABS = [
    { id:"workspace", label:"General"          },
    { id:"team",      label:"Team & Access"    },
    { id:"activity",  label:"Activity & Audit" },
    { id:"security",  label:"Security"         },
    { id:"webhooks",  label:"Integrations"     },
    { id:"deliveries",label:"Delivery Log"     },
    { id:"privacy",   label:"Privacy & Data"   },
    { id:"general",   label:"Advanced"         },
  ] as const;

  return (
    <TenantLayout activeNav="settings">
      <div style={{ display:"flex", flexDirection:"column", gap:24 }}>
        <PageHeader title="Settings" description="Configure your tenant settings, webhooks and integrations" />

        {toast && <Alert tone="success">{toast}</Alert>}

        {/* Tabs */}
        <div style={{ display:"flex", gap:4, borderBottom:"1px solid var(--border)" }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id as typeof tab)}
              style={{ padding:"8px 14px", border:"none", background:"none", cursor:"pointer",
                fontWeight: tab === t.id ? 700 : 400, fontSize:13,
                color: tab === t.id ? "var(--brand)" : "var(--text-secondary)",
                borderBottom: tab === t.id ? "2px solid var(--brand)" : "2px solid transparent",
                marginBottom:-1 }}>
              {t.label}
            </button>
          ))}
        </div>

        {/* WORKSPACE (General) -- real Tenant/TenantSettings/business-hours/
            controlled-policy data via workspace_settings_service.py, which
            existed fully written but had no router until this pass. */}
        {tab === "workspace" && (
          workspaceGeneral.loading || !workspaceGeneral.data ? (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(6)].map((_,i) => <Skeleton key={i} height="2.75rem" />)}
            </div>
          ) : (
            <div style={{ display:"grid", gridTemplateColumns:"2fr 1fr", gap:16 }} className="ws-grid">
              <style>{`@media (max-width: 900px) { .ws-grid { grid-template-columns: 1fr !important; } }`}</style>
              <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                <Card>
                  <p style={{ fontWeight:700, margin:"0 0 12px" }}>Workspace identity</p>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(200px,1fr))", gap:14 }}>
                    {(workspaceGeneral.data.identity ?? []).map((f: { key: string; label: string; value: unknown; editable: boolean }) => (
                      <div key={f.key}>
                        <label style={{ display:"block", fontSize:11, color:"var(--text-tertiary)", marginBottom:4 }}>{f.label}</label>
                        {f.editable ? (
                          <Input value={wsEdits[f.key] ?? String(f.value ?? "")}
                            onChange={e => setWsEdits(p => ({ ...p, [f.key]: e.target.value }))} />
                        ) : (
                          <div style={{ display:"flex", alignItems:"center", gap:6, padding:"8px 0", fontSize:13, color:"var(--text-secondary)" }}>
                            {String(f.value ?? "—")}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </Card>

                <Card>
                  <p style={{ fontWeight:700, margin:"0 0 12px" }}>Regional preferences</p>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(200px,1fr))", gap:14 }}>
                    {(workspaceGeneral.data.regional ?? []).map((f: { key: string; label: string; value: unknown; editable: boolean; help_text?: string }) => (
                      <div key={f.key}>
                        <label style={{ display:"block", fontSize:11, color:"var(--text-tertiary)", marginBottom:4 }}>{f.label}</label>
                        {f.editable ? (
                          <Input value={wsEdits[f.key] ?? String(f.value ?? "")}
                            onChange={e => setWsEdits(p => ({ ...p, [f.key]: e.target.value }))} />
                        ) : (
                          <div style={{ padding:"8px 0", fontSize:13, color:"var(--text-secondary)" }}>{String(f.value ?? "—")}</div>
                        )}
                        {f.help_text && <p style={{ fontSize:10.5, color:"var(--text-tertiary)", margin:"2px 0 0" }}>{f.help_text}</p>}
                      </div>
                    ))}
                  </div>
                  {Object.keys(wsEdits).length > 0 && (
                    <div style={{ marginTop:14, display:"flex", gap:8 }}>
                      <Button size="sm" onClick={wsSaveAction.execute} loading={wsSaveAction.loading}>Save changes</Button>
                      <Button size="sm" variant="ghost" onClick={() => setWsEdits({})}>Discard</Button>
                    </div>
                  )}
                </Card>

                <Card>
                  <p style={{ fontWeight:700, margin:"0 0 4px" }}>Business hours</p>
                  <p style={{ fontSize:11.5, color:"var(--text-tertiary)", margin:"0 0 12px" }}>{workspaceGeneral.data.business_hours_note}</p>
                  <div style={{ overflowX:"auto" }}>
                    <TableSurface style={{ width:"100%", borderCollapse:"collapse" }}>
                      <thead>
                        <tr>
                          {(workspaceGeneral.data.business_hours ?? []).map((d: { day: string }) => (
                            <th key={d.day} style={{ padding:"6px 8px", fontSize:11, color:"var(--text-tertiary)", textTransform:"uppercase", borderBottom:"1px solid var(--border)" }}>{d.day}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          {(workspaceGeneral.data.business_hours ?? []).map((d: { day: string; is_open: boolean; start_time: string | null; end_time: string | null }) => (
                            <td key={d.day} style={{ padding:"8px", fontSize:12, textAlign:"center", color: d.is_open ? "var(--text-primary)" : "var(--text-tertiary)" }}>
                              {d.is_open ? `${d.start_time} – ${d.end_time}` : "Closed"}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </TableSurface>
                  </div>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"10px 0 0" }}>
                    Edited from Availability, not here — see <code>/home-services/availability</code>.
                  </p>
                </Card>

                <Card>
                  <p style={{ fontWeight:700, margin:"0 0 12px" }}>Platform-controlled policy</p>
                  {(workspaceGeneral.data.controlled_policy ?? []).map((p: { key: string; label: string; effective_value: string; explanation: string }, i: number, arr: unknown[]) => (
                    <div key={p.key} style={{ padding:"10px 0", borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:2 }}>
                        <span style={{ fontSize:13, fontWeight:600 }}>{p.label}</span>
                        <span style={{ fontSize:13, color:"var(--brand)", fontWeight:600 }}>{p.effective_value}</span>
                      </div>
                      <p style={{ fontSize:11.5, color:"var(--text-tertiary)", margin:0 }}>{p.explanation}</p>
                    </div>
                  ))}
                </Card>
              </div>

              <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                <Card>
                  <p style={{ fontWeight:700, margin:"0 0 12px" }}>Configuration ownership</p>
                  {[
                    { label:"Tenant controlled", desc:"You can edit these settings.", tone:"success" },
                    { label:"ServiceOS controlled", desc:"These are platform rules.", tone:"info" },
                    { label:"Admin policy", desc:"Set by ServiceOS administrators.", tone:"warning" },
                  ].map(o => (
                    <div key={o.label} style={{ display:"flex", gap:10, marginBottom:12 }}>
                      <div style={{ width:8, height:8, borderRadius:"50%", background:`var(--${o.tone}-text)`, marginTop:5, flexShrink:0 }} />
                      <div>
                        <p style={{ fontSize:13, fontWeight:600, margin:0 }}>{o.label}</p>
                        <p style={{ fontSize:11.5, color:"var(--text-tertiary)", margin:"2px 0 0" }}>{o.desc}</p>
                      </div>
                    </div>
                  ))}
                </Card>
                <Card>
                  <p style={{ fontWeight:700, margin:"0 0 10px" }}>Workspace status</p>
                  <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
                    <DsStatusBadge status={workspaceGeneral.data.workspace_status === "active" ? "active" : "inactive"}/>
                  </div>
                  <p style={{ fontSize:11.5, color:"var(--text-tertiary)", margin:0 }}>
                    Last updated {workspaceGeneral.data.last_updated_at ? new Date(workspaceGeneral.data.last_updated_at).toLocaleString() : "—"}
                  </p>
                </Card>
              </div>
            </div>
          )
        )}

        {/* TEAM & ACCESS -- real owner + active staff/technicians roster */}
        {tab === "team" && (
          teamAccess.loading || !teamAccess.data ? (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(4)].map((_,i) => <Skeleton key={i} height="2.75rem" />)}
            </div>
          ) : (
            <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
              <Card>
                <p style={{ fontWeight:700, margin:"0 0 10px" }}>Owner</p>
                {teamAccess.data.owner ? (
                  <p style={{ fontSize:13, margin:0 }}>{teamAccess.data.owner.full_name} · {teamAccess.data.owner.email}</p>
                ) : <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No owner on record.</p>}
              </Card>
              {[
                { key:"active_managers", label:"Managers" },
                { key:"active_staff", label:"Staff" },
                { key:"active_technicians", label:"Technicians" },
              ].map(g => (
                <Card key={g.key}>
                  <p style={{ fontWeight:700, margin:"0 0 10px" }}>{g.label} ({(teamAccess.data[g.key] ?? []).length})</p>
                  {(teamAccess.data[g.key] ?? []).length === 0 ? (
                    <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>None.</p>
                  ) : (teamAccess.data[g.key] as Array<{ id: string; full_name: string }>).map(m => (
                    <p key={m.id} style={{ fontSize:13, margin:"4px 0" }}>{m.full_name}</p>
                  ))}
                </Card>
              ))}
              <p style={{ fontSize:11.5, color:"var(--text-tertiary)" }}>{teamAccess.data.pending_invitations_note}</p>
            </div>
          )
        )}

        {/* ACTIVITY & AUDIT -- real platform_audit_logs projection */}
        {tab === "activity" && (
          wsActivity.loading || !wsActivity.data ? (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(6)].map((_,i) => <Skeleton key={i} height="2.75rem" />)}
            </div>
          ) : (
            <Card padding="none">
              {(wsActivity.data.items ?? []).length === 0 ? (
                <p style={{ padding:24, textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>No workspace activity recorded yet.</p>
              ) : (wsActivity.data.items as Array<{ id: string; operation: string; actor_name: string; created_at: string }>).map((a, i, arr) => (
                <div key={a.id} style={{ display:"flex", justifyContent:"space-between", padding:"12px 20px", borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                  <div>
                    <p style={{ fontSize:13, fontWeight:600, margin:0 }}>{a.operation.replace(/_/g," ").replace(/\./g," · ")}</p>
                    <p style={{ fontSize:11.5, color:"var(--text-tertiary)", margin:"2px 0 0" }}>by {a.actor_name}</p>
                  </div>
                  <span style={{ fontSize:11.5, color:"var(--text-tertiary)", whiteSpace:"nowrap" }}>{new Date(a.created_at).toLocaleString()}</span>
                </div>
              ))}
            </Card>
          )
        )}

        {/* ADVANCED (legacy General Settings key/value table) */}
        {tab === "general" && (
          settings.loading ? (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(8)].map((_,i) => <Skeleton key={i} height="2.75rem" />)}
            </div>
          ) : (
            <Card padding="none">
              <div style={{ overflowX: "auto" }}>
                <TableSurface style={{ width:"100%", borderCollapse:"collapse" }}>
                  <thead>
                    <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                      {["Setting Key","Value","Source",""].map(h => (
                        <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                          color:"var(--text-tertiary)", letterSpacing:"0.06em", textTransform:"uppercase" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(settings.data?.settings ?? []).map((s: SettingEntry, i: number) => (
                      <tr key={s.key} style={{
                        borderBottom: i < (settings.data?.settings?.length ?? 0)-1 ? "1px solid var(--border)" : "none",
                        background: s.is_override ? "rgba(16,185,129,0.05)" : "transparent",
                      }}>
                        <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, fontFamily:"monospace" }}>{s.key}</td>
                        <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)", maxWidth:240,
                          overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                          {JSON.stringify(s.value)}
                        </td>
                        <td style={{ padding:"11px 16px" }}>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                            <DsStatusBadge status={SOURCE_STATUS[s.source] ?? "neutral"} variant="dot" size="sm"/>
                            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{SOURCE_LABEL[s.source]}</span>
                          </span>
                        </td>
                        <td style={{ padding:"11px 16px" }}>
                          <div style={{ display:"flex", gap:6 }}>
                            <Button variant="icon" size="sm" aria-label="Edit" onClick={() => {
                              setEditKey(s.key);
                              setEditVal(typeof s.value === "string" ? s.value : JSON.stringify(s.value));
                              setEditModal(true);
                            }}>Edit</Button>
                            {s.is_override && (
                              <Button variant="icon" size="sm" aria-label="Reset" onClick={() => {
                                setDeleteKey(s.key);
                                setConfirmDel(true);
                              }}>Reset</Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableSurface>
              </div>
            </Card>
          )
        )}

        {/* WEBHOOKS */}
        {tab === "webhooks" && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ display:"flex", justifyContent:"flex-end" }}>
              <Button variant="primary" size="sm" onClick={() => setWhModal(true)}>+ Add Webhook</Button>
            </div>
            <Card>
              {webhooks.loading ? (
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {[...Array(3)].map((_,i) => <Skeleton key={i} height="4rem" />)}
                </div>
              ) : (
                <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
                  {(webhooks.data?.endpoints ?? []).map((w: Webhook) => (
                    <div key={w.endpoint_id} style={{ padding:"14px 16px", border:"1px solid var(--border)", borderRadius:10 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8 }}>
                        <div>
                          <code style={{ fontSize:13, fontWeight:600 }}>{w.url}</code>
                          <p style={{ margin:"4px 0 0", fontSize:11, color:"var(--text-secondary)" }}>
                            {w.subscribed_events.length > 0
                              ? `Events: ${w.subscribed_events.join(", ")}`
                              : "No events subscribed — this endpoint will never fire."}
                          </p>
                          {w.total_deliveries > 0 && (
                            <p style={{ margin:"2px 0 0", fontSize:11, color:"var(--text-tertiary)" }}>
                              {w.total_deliveries} deliveries
                              {w.last_success_at ? ` · last success ${new Date(w.last_success_at).toLocaleString()}` : ""}
                            </p>
                          )}
                        </div>
                        <div style={{ display:"flex", gap:6, alignItems:"center" }}>
                          <DsStatusBadge status={w.status === "active" ? "active" : w.status === "paused" ? "pending" : "inactive"}/>
                          {w.consecutive_failures > 0 && (
                            <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
                              background: "var(--danger-bg)", color: "var(--danger-text)" }}>
                              {w.consecutive_failures} failures
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                        <Button size="sm" variant="ghost" onClick={() => testWebhook.execute(w.endpoint_id)}>Test</Button>
                        {w.status === "active"
                          ? <Button size="sm" variant="ghost" onClick={() => pauseWebhook.execute(w.endpoint_id)}>Pause</Button>
                          : <Button size="sm" variant="ghost" onClick={() => resumeWebhook.execute(w.endpoint_id)}>Resume</Button>
                        }
                        <Button size="sm" variant="destructive" onClick={() => deleteWebhook.execute(w.endpoint_id)}>Delete</Button>
                      </div>
                    </div>
                  ))}
                  {(webhooks.data?.endpoints ?? []).length === 0 && (
                    <p style={{ color:"var(--text-secondary)", fontSize:13, textAlign:"center", padding:32 }}>
                      No webhooks configured yet.
                    </p>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* DELIVERIES */}
        {tab === "deliveries" && (
          <Card>
            <p style={{ fontWeight:600, margin:"0 0 16px" }}>Recent Webhook Deliveries</p>
            {deliveries.loading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(4)].map((_,i) => <Skeleton key={i} height="3rem" />)}
              </div>
            ) : (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {(deliveries.data?.deliveries ?? []).map((d: WebhookDelivery) => (
                  <div key={d.delivery_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    padding:"10px 14px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)" }}>
                    <div>
                      <div style={{ display:"flex", gap:8, alignItems:"center", marginBottom:4 }}>
                        <DsStatusBadge status={d.status === "success" ? "completed" : "failed"}/>
                        <span style={{ fontSize:12, fontWeight:600 }}>{d.event_type}</span>
                      </div>
                      <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>
                        {new Date(d.created_at).toLocaleString()}
                        &nbsp;·&nbsp;{d.attempts} attempt{d.attempts !== 1 ? "s" : ""}
                        {d.response_status && ` · HTTP ${d.response_status}`}
                      </p>
                    </div>
                  </div>
                ))}
                {(deliveries.data?.deliveries ?? []).length === 0 && (
                  <p style={{ color:"var(--text-secondary)", fontSize:13, textAlign:"center", padding:24 }}>
                    No deliveries yet.
                  </p>
                )}
              </div>
            )}
          </Card>
        )}

        {/* PRIVACY & DATA */}
        {tab === "privacy" && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Card>
              <p style={{ fontWeight:600, margin:"0 0 4px" }}>Consent Preferences</p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Manage what you've consented to under DPDP Act 2023. Withdrawing consent is recorded immediately.
              </p>
              {consents.loading ? (
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {[...Array(5)].map((_,i) => <Skeleton key={i} height="3rem" />)}
                </div>
              ) : (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  {CONSENT_TYPES.map(c => {
                    const status = consents.data?.[c.key];
                    const granted = status?.has_consent ?? false;
                    return (
                      <div key={c.key} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                        padding:"12px 14px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)" }}>
                        <div>
                          <div style={{ display:"flex", gap:8, alignItems:"center", marginBottom:2 }}>
                            <span style={{ fontWeight:600, fontSize:13 }}>{c.label}</span>
                            <DsStatusBadge status={granted ? "active" : "not_granted"}/>
                          </div>
                          <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>{c.hint}</p>
                        </div>
                        <Button variant={granted ? "ghost" : "primary"} size="sm"
                          loading={toggleConsent.loading}
                          onClick={() => toggleConsent.execute(c.key, granted)}>
                          {granted ? "Withdraw" : "Grant"}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>

            <Card>
              <p style={{ fontWeight:600, margin:"0 0 4px" }}>Export Your Data</p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Request a copy of your data (right to data portability). Delivered within 72 hours.
              </p>
              {exportResult ? (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                    <DsStatusBadge status={exportResult.status === "ready" ? "completed" : "pending"}/>
                    <span style={{ fontSize:12, color:"var(--text-secondary)" }}>
                      SLA: {new Date(exportResult.sla_deadline).toLocaleString()}
                    </span>
                  </div>
                  {exportResult.download_url ? (
                    <a href={exportResult.download_url} target="_blank" rel="noreferrer">
                      <Button size="sm">Download Export ({exportResult.record_count} records)</Button>
                    </a>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={refreshExport.execute} loading={refreshExport.loading}>
                      Refresh Status
                    </Button>
                  )}
                </div>
              ) : (
                <Button size="sm" onClick={requestExport.execute} loading={requestExport.loading}>Request Data Export</Button>
              )}
              {requestExport.error && <p style={{ color:"var(--danger)", fontSize:12, marginTop:8 }}>{requestExport.error}</p>}
            </Card>

            <Card>
              <p style={{ fontWeight:600, margin:"0 0 4px", color:"var(--danger-text)" }}>Delete My Account & Data</p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Right to erasure under DPDP Act 2023. PII is anonymised within 72 hours; financial
                records are retained only as legally required and exempted with a stated reason.
              </p>
              {deletionResult ? (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                    <DsStatusBadge status={deletionResult.status === "completed" ? "completed"
                      : deletionResult.sla_breached ? "failed" : "pending"}/>
                    <span style={{ fontSize:12, color:"var(--text-secondary)" }}>
                      {deletionResult.hours_until_sla > 0
                        ? `${deletionResult.hours_until_sla.toFixed(1)}h until SLA deadline`
                        : "SLA deadline passed"}
                    </span>
                  </div>
                  {deletionResult.tables_exempted.length > 0 && (
                    <p style={{ fontSize:11, color:"var(--warning-text)", margin:0 }}>
                      Exempt (legal): {deletionResult.tables_exempted.join(", ")}
                    </p>
                  )}
                  <Button size="sm" variant="ghost" onClick={refreshDeletion.execute} loading={refreshDeletion.loading}>
                    Refresh Status
                  </Button>
                </div>
              ) : (
                <Button variant="destructive" size="sm" onClick={() => setDeleteConfirm(true)}>Request Account Deletion</Button>
              )}
            </Card>
          </div>
        )}

        {/* SECURITY */}
        {tab === "security" && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            {API_KEYS_ENABLED && (
            <Card>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:4 }}>
                <p style={{ fontWeight:600, margin:0 }}>Integration API Keys</p>
                <Button variant="primary" size="sm" onClick={() => { setSecKeyResult(null); setSecKeyModal(true); }}>+ New Key</Button>
              </div>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Keys for third-party integrations. Only a hash is stored — the raw key is shown once.
              </p>
              {secKeys.loading ? (
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {[...Array(3)].map((_,i) => <Skeleton key={i} height="3rem" />)}
                </div>
              ) : (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  {(secKeys.data?.api_keys ?? []).map((k: SecurityApiKey) => (
                    <div key={k.key_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                      padding:"12px 14px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)" }}>
                      <div>
                        <div style={{ display:"flex", gap:8, marginBottom:4 }}>
                          <span style={{ fontWeight:600, fontSize:13 }}>{k.name}</span>
                          <DsStatusBadge status={k.status === "active" ? "active" : "inactive"}/>
                        </div>
                        <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>
                          {k.key_prefix} · {k.scopes.join(", ")} · used {k.use_count}x
                        </p>
                      </div>
                      {k.status === "active" && (
                        <div style={{ display:"flex", gap:6 }}>
                          <Button variant="ghost" size="sm" loading={rotateSecKey.loading}
                            onClick={() => rotateSecKey.execute(k.key_id)}>Rotate</Button>
                          <Button variant="destructive" size="sm" loading={revokeSecKey.loading}
                            onClick={() => revokeSecKey.execute(k.key_id)}>Revoke</Button>
                        </div>
                      )}
                    </div>
                  ))}
                  {(secKeys.data?.api_keys ?? []).length === 0 && (
                    <p style={{ color:"var(--text-secondary)", fontSize:13, textAlign:"center", padding:24 }}>
                      No integration keys yet.
                    </p>
                  )}
                </div>
              )}
            </Card>
            )}

            <Card>
              <p style={{ fontWeight:600, margin:"0 0 4px" }}>Check IP Blocklist</p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Check whether an IP address has been blocked by the platform.
              </p>
              <div style={{ display:"flex", gap:8, alignItems:"flex-end", maxWidth:420 }}>
                <div style={{ flex:1 }}>
                  <Input label="IP Address" placeholder="103.21.45.67" value={ipQuery} onChange={e => setIpQuery(e.target.value)} />
                </div>
                <Button size="sm" onClick={checkIp.execute} loading={checkIp.loading}>Check</Button>
              </div>
              {ipResult && (
                <div style={{ marginTop:12, display:"flex", gap:8, alignItems:"center" }}>
                  <DsStatusBadge status={ipResult.blocked ? "conflict" : "active"}/>
                  {ipResult.reason && <span style={{ fontSize:12, color:"var(--text-secondary)" }}>{ipResult.reason}</span>}
                </div>
              )}
            </Card>

            <Card>
              <p style={{ fontWeight:600, margin:"0 0 4px" }}>Report Suspicious Activity</p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Notice something unusual on your account? Flag it for the security team.
              </p>
              <div style={{ display:"flex", gap:8, alignItems:"flex-end", maxWidth:480, flexWrap:"wrap" }}>
                <select value={reportType} onChange={e => setReportType(e.target.value)}
                  style={{ padding:"8px 10px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)",
                    background:"var(--surface)", color:"var(--text-primary)", fontSize:13, flex:1, minWidth:240 }}>
                  {ACTIVITY_TYPES.map(a => <option key={a.key} value={a.key}>{a.label}</option>)}
                </select>
                <Button size="sm" variant="destructive" onClick={reportActivity.execute} loading={reportActivity.loading}>Report</Button>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Edit modal */}
      <Modal open={editModal} onClose={() => setEditModal(false)} title={`Edit: ${editKey}`}
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setEditModal(false)}>Cancel</Button>
          <Button size="sm" onClick={updateSetting.execute} loading={updateSetting.loading}
            disabled={!editKey.trim() || !editReason.trim()}>Save</Button>
        </>}>
        <Input label="Value" value={editVal} onChange={e => setEditVal(e.target.value)} />
        <Input label="Reason" value={editReason} onChange={e => setEditReason(e.target.value)}
          description="Why this override is being set — stored on the audit record." />
      </Modal>

      {/* Delete/reset modal */}
      <Modal open={confirmDel} onClose={() => setConfirmDel(false)} title="Reset Setting"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setConfirmDel(false)}>Cancel</Button>
          <Button variant="destructive" size="sm" onClick={deleteSetting.execute} loading={deleteSetting.loading}>Reset</Button>
        </>}>
        <p style={{ margin:0, fontSize:13 }}>Remove your override for <code>{deleteKey}</code>? It will revert to the plan/platform default.</p>
      </Modal>

      {/* Webhook modal */}
      <Modal open={whModal} onClose={() => setWhModal(false)} title="Add Webhook Endpoint"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setWhModal(false)}>Cancel</Button>
          <Button size="sm" onClick={createWebhook.execute} loading={createWebhook.loading}
            disabled={!whUrl.trim() || whEvents.length === 0}>Create Webhook</Button>
        </>}>
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Input label="URL" value={whUrl} onChange={e => setWhUrl(e.target.value)}
            description="https://your-server.com/webhook" />
          <Input label="Description (optional)" value={whDesc} onChange={e => setWhDesc(e.target.value)}
            description="What this endpoint is for" />
          <div>
            <p style={{ fontSize:13, fontWeight:600, margin:"0 0 2px" }}>Events</p>
            <p style={{ fontSize:11, color:"var(--text-secondary)", margin:"0 0 10px" }}>
              Pick from the events this platform emits. An endpoint with none selected
              will never fire.
            </p>
            {/* Chosen from the server's own catalogue, so an unknown event name
                can no longer be typed in and rejected — or worse, accepted and
                silently never delivered. */}
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(190px,1fr))", gap:6 }}>
              {(webhooks.data?.available_events ?? []).map(ev => {
                const on = whEvents.includes(ev);
                return (
                  <label key={ev} style={{
                    display:"flex", alignItems:"center", gap:8, fontSize:12,
                    padding:"7px 10px", border:`1px solid ${on ? "var(--brand)" : "var(--border)"}`,
                    borderRadius:"var(--radius-md)", cursor:"pointer",
                    background: on ? "var(--brand-bg, var(--surface-sunken))" : "var(--surface)",
                  }}>
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => setWhEvents(prev =>
                        prev.includes(ev) ? prev.filter(x => x !== ev) : [...prev, ev])}
                    />
                    <code style={{ fontSize:11.5 }}>{ev}</code>
                  </label>
                );
              })}
            </div>
            {(webhooks.data?.available_events ?? []).length === 0 && (
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
                The event catalogue could not be loaded.
              </p>
            )}
          </div>
          {whEvents.length === 0 && (
            <p style={{ fontSize:12, color:"var(--warning-text, var(--text-secondary))", margin:0 }}>
              Select at least one event.
            </p>
          )}
          {createWebhook.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{createWebhook.error}</p>}
        </div>
      </Modal>

      {/* Account deletion confirmation */}
      <Modal open={deleteConfirm} onClose={() => setDeleteConfirm(false)} title="Confirm Account Deletion"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setDeleteConfirm(false)}>Cancel</Button>
          <Button variant="destructive" size="sm" onClick={requestDeletion.execute} loading={requestDeletion.loading}>
            Confirm Deletion
          </Button>
        </>}>
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Alert tone="danger">
            This will anonymise your PII within 72 hours under DPDP Act 2023. Financial records
            required by law (GST Act, 7 years) will be retained with a stated legal exemption.
            This action cannot be undone.
          </Alert>
          {requestDeletion.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{requestDeletion.error}</p>}
        </div>
      </Modal>

      {/* Integration API key create/rotate result modal */}
      {API_KEYS_ENABLED && <Modal open={secKeyModal} onClose={() => { setSecKeyModal(false); setSecKeyResult(null); }}
        title={secKeyResult ? "Key Created" : "New Integration API Key"}
        footer={secKeyResult
          ? <Button size="sm" onClick={() => { setSecKeyModal(false); setSecKeyResult(null); }}>Done</Button>
          : <>
              <Button variant="ghost" size="sm" onClick={() => setSecKeyModal(false)}>Cancel</Button>
              <Button size="sm" onClick={createSecKey.execute} loading={createSecKey.loading}>Create</Button>
            </>}>
        {secKeyResult ? (
          <div style={{ padding:12, background:"var(--success-bg,#d1fae5)", borderRadius:"var(--radius-md)", border:"1px solid var(--success,var(--success))" }}>
            <p style={{ margin:"0 0 8px", fontWeight:600 }}>{secKeyResult.warning}</p>
            <code style={{ display:"block", wordBreak:"break-all", fontSize:12, padding:"8px 10px",
              background:"white", border:"1px solid var(--border)", borderRadius:6 }}>
              {secKeyResult.raw_key}
            </code>
          </div>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Input label="Name" value={secKeyName} onChange={e => setSecKeyName(e.target.value)} />
            <Input label="Scopes (comma-separated)" value={secKeyScopes} onChange={e => setSecKeyScopes(e.target.value)}
              description="e.g. read:jobs,write:bookings,read:analytics" />
            {createSecKey.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{createSecKey.error}</p>}
          </div>
        )}
      </Modal>}
    </TenantLayout>
  );
}
