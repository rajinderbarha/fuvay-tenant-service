"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Skeleton, SectionHeader, Modal, Input, Spinner, EditBtn, DeleteBtn, AddBtn } from "../../../components/shared/ui";
import {
  settingsApi, complianceApi, securityApi,
  type SettingEntry, type Webhook, type WebhookDelivery,
  type ConsentCheck, type DeletionRequestResult, type ExportRequestResult,
  type SecurityApiKey, type SecurityApiKeyCreated, type IpBlockCheck,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const SOURCE_BADGE: Record<string,string> = { tenant:"success", plan:"info", platform:"muted", code_default:"muted" };
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

export default function SettingsPage() {
  const [tab, setTab] = useState<"general"|"webhooks"|"deliveries"|"privacy"|"security">("general");

  // General settings
  const settings = useApi(() => settingsApi.get(), []);
  const [editKey,    setEditKey]    = useState("");
  const [editVal,    setEditVal]    = useState("");
  const [editModal,  setEditModal]  = useState(false);
  const [deleteKey,  setDeleteKey]  = useState("");
  const [confirmDel, setConfirmDel] = useState(false);
  const [toast,      setToast]      = useState("");

  // Webhooks
  const webhooks   = useApi(() => settingsApi.listWebhooks(), []);
  const deliveries = useApi(() => settingsApi.listDeliveries({ limit: 30 }), [tab === "deliveries"]);
  const [whModal,  setWhModal]  = useState(false);
  const [whUrl,    setWhUrl]    = useState("");
  const [whEvents, setWhEvents] = useState("job.completed,booking.confirmed");

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const updateSetting = useAction(async () => {
    await settingsApi.update(editKey, editVal);
    await settings.refetch();
    setEditModal(false);
    notify("Setting saved.");
  });

  const deleteSetting = useAction(async () => {
    await settingsApi.delete(deleteKey);
    await settings.refetch();
    setConfirmDel(false);
    notify("Override removed.");
  });

  const createWebhook = useAction(async () => {
    const events = whEvents.split(",").map(e => e.trim()).filter(Boolean);
    await settingsApi.createWebhook(whUrl, events);
    await webhooks.refetch();
    setWhModal(false);
    setWhUrl(""); setWhEvents("job.completed,booking.confirmed");
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
  const secKeys = useApi(useCallback(() => securityApi.listApiKeys(), []));
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
    { id:"general",   label:"General Settings" },
    { id:"webhooks",  label:"Webhooks"         },
    { id:"deliveries",label:"Delivery Log"     },
    { id:"privacy",   label:"Privacy & Data"   },
    { id:"security",  label:"Security"         },
  ] as const;

  return (
    <TenantLayout activeNav="settings">
      <div style={{ display:"flex", flexDirection:"column", gap:24 }}>
        <SectionHeader title="Settings" subtitle="Configure your tenant settings, webhooks and integrations" />

        {toast && (
          <div style={{ padding:"10px 16px", background:"var(--success-bg,#d1fae5)", border:"1px solid var(--success,#10b981)",
            borderRadius:8, color:"var(--success-text,#065f46)", fontSize:13 }}>
            {toast}
          </div>
        )}

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

        {/* GENERAL */}
        {tab === "general" && (
          settings.loading ? (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(8)].map((_,i) => <Skeleton key={i} height={44} />)}
            </div>
          ) : (
            <Card padding={0}>
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
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
                      borderBottom: i < (settings.data?.settings.length ?? 0)-1 ? "1px solid var(--border)" : "none",
                      background: s.is_override ? "rgba(16,185,129,0.05)" : "transparent",
                    }}>
                      <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, fontFamily:"monospace" }}>{s.key}</td>
                      <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)", maxWidth:240,
                        overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                        {JSON.stringify(s.value)}
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        <Badge variant={SOURCE_BADGE[s.source] as "success"} size="sm">{SOURCE_LABEL[s.source]}</Badge>
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        <div style={{ display:"flex", gap:6 }}>
                          <EditBtn tooltip="Edit" onClick={() => {
                            setEditKey(s.key);
                            setEditVal(typeof s.value === "string" ? s.value : JSON.stringify(s.value));
                            setEditModal(true);
                          }}/>
                          {s.is_override && (
                            <DeleteBtn tooltip="Reset" onClick={() => {
                              setDeleteKey(s.key);
                              setConfirmDel(true);
                            }}/>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )
        )}

        {/* WEBHOOKS */}
        {tab === "webhooks" && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ display:"flex", justifyContent:"flex-end" }}>
              <AddBtn label="Add Webhook" size="sm" onClick={() => setWhModal(true)}/>
            </div>
            <Card>
              {webhooks.loading ? <Spinner /> : (
                <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
                  {(webhooks.data?.webhooks ?? []).map((w: Webhook) => (
                    <div key={w.id} style={{ padding:"14px 16px", border:"1px solid var(--border)", borderRadius:10 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8 }}>
                        <div>
                          <code style={{ fontSize:13, fontWeight:600 }}>{w.url}</code>
                          <p style={{ margin:"4px 0 0", fontSize:11, color:"var(--text-secondary)" }}>
                            Events: {w.events.join(", ")}
                          </p>
                        </div>
                        <div style={{ display:"flex", gap:6, alignItems:"center" }}>
                          <Badge variant={w.status === "active" ? "success" : w.status === "paused" ? "warning" : "danger"}>
                            {w.status}
                          </Badge>
                          {w.consecutive_failures > 0 && (
                            <Badge variant="danger" size="sm">{w.consecutive_failures} failures</Badge>
                          )}
                        </div>
                      </div>
                      <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                        <Btn size="xs" variant="ghost" onClick={() => testWebhook.execute(w.id)}>Test</Btn>
                        {w.status === "active"
                          ? <Btn size="xs" variant="ghost" onClick={() => pauseWebhook.execute(w.id)}>Pause</Btn>
                          : <Btn size="xs" variant="ghost" onClick={() => resumeWebhook.execute(w.id)}>Resume</Btn>
                        }
                        <Btn size="xs" variant="danger" onClick={() => deleteWebhook.execute(w.id)}>Delete</Btn>
                      </div>
                    </div>
                  ))}
                  {(webhooks.data?.webhooks ?? []).length === 0 && (
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
            {deliveries.loading ? <Spinner /> : (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {(deliveries.data?.deliveries ?? []).map((d: WebhookDelivery) => (
                  <div key={d.delivery_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    padding:"10px 14px", border:"1px solid var(--border)", borderRadius:8 }}>
                    <div>
                      <div style={{ display:"flex", gap:8, alignItems:"center", marginBottom:4 }}>
                        <Badge variant={d.status === "success" ? "success" : "danger"}>{d.status}</Badge>
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
                  {[...Array(5)].map((_,i) => <Skeleton key={i} height={48} />)}
                </div>
              ) : (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  {CONSENT_TYPES.map(c => {
                    const status = consents.data?.[c.key];
                    const granted = status?.has_consent ?? false;
                    return (
                      <div key={c.key} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                        padding:"12px 14px", border:"1px solid var(--border)", borderRadius:8 }}>
                        <div>
                          <div style={{ display:"flex", gap:8, alignItems:"center", marginBottom:2 }}>
                            <span style={{ fontWeight:600, fontSize:13 }}>{c.label}</span>
                            <Badge variant={granted ? "success" : "muted"}>{granted ? "Granted" : "Not granted"}</Badge>
                          </div>
                          <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>{c.hint}</p>
                        </div>
                        <Btn variant={granted ? "ghost" : "primary"} size="sm"
                          loading={toggleConsent.loading}
                          onClick={() => toggleConsent.execute(c.key, granted)}>
                          {granted ? "Withdraw" : "Grant"}
                        </Btn>
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
                    <Badge variant={exportResult.status === "ready" ? "success" : "warning"}>{exportResult.status}</Badge>
                    <span style={{ fontSize:12, color:"var(--text-secondary)" }}>
                      SLA: {new Date(exportResult.sla_deadline).toLocaleString()}
                    </span>
                  </div>
                  {exportResult.download_url ? (
                    <a href={exportResult.download_url} target="_blank" rel="noreferrer">
                      <Btn size="sm">Download Export ({exportResult.record_count} records)</Btn>
                    </a>
                  ) : (
                    <Btn size="sm" variant="ghost" onClick={refreshExport.execute} loading={refreshExport.loading}>
                      Refresh Status
                    </Btn>
                  )}
                </div>
              ) : (
                <Btn size="sm" onClick={requestExport.execute} loading={requestExport.loading}>Request Data Export</Btn>
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
                    <Badge variant={deletionResult.status === "completed" ? "success"
                      : deletionResult.sla_breached ? "danger" : "warning"}>{deletionResult.status}</Badge>
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
                  <Btn size="sm" variant="ghost" onClick={refreshDeletion.execute} loading={refreshDeletion.loading}>
                    Refresh Status
                  </Btn>
                </div>
              ) : (
                <Btn variant="danger" size="sm" onClick={() => setDeleteConfirm(true)}>Request Account Deletion</Btn>
              )}
            </Card>
          </div>
        )}

        {/* SECURITY */}
        {tab === "security" && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Card>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:4 }}>
                <p style={{ fontWeight:600, margin:0 }}>Integration API Keys</p>
                <AddBtn label="New Key" size="sm" onClick={() => { setSecKeyResult(null); setSecKeyModal(true); }}/>
              </div>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Keys for third-party integrations. Only a hash is stored — the raw key is shown once.
              </p>
              {secKeys.loading ? <Spinner /> : (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  {(secKeys.data?.api_keys ?? []).map((k: SecurityApiKey) => (
                    <div key={k.key_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                      padding:"12px 14px", border:"1px solid var(--border)", borderRadius:8 }}>
                      <div>
                        <div style={{ display:"flex", gap:8, marginBottom:4 }}>
                          <span style={{ fontWeight:600, fontSize:13 }}>{k.name}</span>
                          <Badge variant={k.status === "active" ? "success" : "muted"}>{k.status}</Badge>
                        </div>
                        <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>
                          {k.key_prefix} · {k.scopes.join(", ")} · used {k.use_count}x
                        </p>
                      </div>
                      {k.status === "active" && (
                        <div style={{ display:"flex", gap:6 }}>
                          <Btn variant="ghost" size="sm" loading={rotateSecKey.loading}
                            onClick={() => rotateSecKey.execute(k.key_id)}>Rotate</Btn>
                          <Btn variant="danger" size="sm" loading={revokeSecKey.loading}
                            onClick={() => revokeSecKey.execute(k.key_id)}>Revoke</Btn>
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

            <Card>
              <p style={{ fontWeight:600, margin:"0 0 4px" }}>Check IP Blocklist</p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Check whether an IP address has been blocked by the platform.
              </p>
              <div style={{ display:"flex", gap:8, alignItems:"flex-end", maxWidth:420 }}>
                <div style={{ flex:1 }}>
                  <Input label="IP Address" placeholder="103.21.45.67" value={ipQuery} onChange={setIpQuery} />
                </div>
                <Btn size="sm" onClick={checkIp.execute} loading={checkIp.loading}>Check</Btn>
              </div>
              {ipResult && (
                <div style={{ marginTop:12, display:"flex", gap:8, alignItems:"center" }}>
                  <Badge variant={ipResult.blocked ? "danger" : "success"}>
                    {ipResult.blocked ? "Blocked" : "Not blocked"}
                  </Badge>
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
                  style={{ padding:"8px 10px", border:"1px solid var(--border)", borderRadius:8,
                    background:"var(--surface)", color:"var(--text-primary)", fontSize:13, flex:1, minWidth:240 }}>
                  {ACTIVITY_TYPES.map(a => <option key={a.key} value={a.key}>{a.label}</option>)}
                </select>
                <Btn size="sm" variant="danger" onClick={reportActivity.execute} loading={reportActivity.loading}>Report</Btn>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Edit modal */}
      <Modal open={editModal} onClose={() => setEditModal(false)} title={`Edit: ${editKey}`} size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Input label="Value" value={editVal} onChange={v => setEditVal(v)} />
          <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
            <Btn variant="ghost" onClick={() => setEditModal(false)}>Cancel</Btn>
            <Btn onClick={updateSetting.execute} loading={updateSetting.loading}>Save</Btn>
          </div>
        </div>
      </Modal>

      {/* Delete/reset modal */}
      <Modal open={confirmDel} onClose={() => setConfirmDel(false)} title="Reset Setting" size="sm">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <p style={{ margin:0, fontSize:13 }}>Remove your override for <code>{deleteKey}</code>? It will revert to the plan/platform default.</p>
          <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
            <Btn variant="ghost" onClick={() => setConfirmDel(false)}>Cancel</Btn>
            <Btn variant="danger" onClick={deleteSetting.execute} loading={deleteSetting.loading}>Reset</Btn>
          </div>
        </div>
      </Modal>

      {/* Webhook modal */}
      <Modal open={whModal} onClose={() => setWhModal(false)} title="Add Webhook Endpoint" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Input label="URL" value={whUrl} onChange={v => setWhUrl(v)}
            hint="https://your-server.com/webhook" />
          <Input label="Events (comma-separated)" value={whEvents} onChange={v => setWhEvents(v)}
            hint="e.g. job.completed,booking.confirmed,payment.received" />
          <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
            <Btn variant="ghost" onClick={() => setWhModal(false)}>Cancel</Btn>
            <Btn onClick={createWebhook.execute} loading={createWebhook.loading}>Create Webhook</Btn>
          </div>
          {createWebhook.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{createWebhook.error}</p>}
        </div>
      </Modal>

      {/* Account deletion confirmation */}
      <Modal open={deleteConfirm} onClose={() => setDeleteConfirm(false)} title="Confirm Account Deletion" size="sm">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ padding:12, background:"var(--danger-bg)", border:"1px solid var(--danger-border)", borderRadius:8 }}>
            <p style={{ margin:0, fontSize:12, color:"var(--danger-text)" }}>
              This will anonymise your PII within 72 hours under DPDP Act 2023. Financial records
              required by law (GST Act, 7 years) will be retained with a stated legal exemption.
              This action cannot be undone.
            </p>
          </div>
          <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
            <Btn variant="ghost" onClick={() => setDeleteConfirm(false)}>Cancel</Btn>
            <Btn variant="danger" onClick={requestDeletion.execute} loading={requestDeletion.loading}>
              Confirm Deletion
            </Btn>
          </div>
          {requestDeletion.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{requestDeletion.error}</p>}
        </div>
      </Modal>

      {/* Integration API key create/rotate result modal */}
      <Modal open={secKeyModal} onClose={() => { setSecKeyModal(false); setSecKeyResult(null); }}
        title={secKeyResult ? "Key Created" : "New Integration API Key"} size="md">
        {secKeyResult ? (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ padding:12, background:"var(--success-bg,#d1fae5)", borderRadius:8, border:"1px solid var(--success,#10b981)" }}>
              <p style={{ margin:"0 0 8px", fontWeight:600 }}>{secKeyResult.warning}</p>
              <code style={{ display:"block", wordBreak:"break-all", fontSize:12, padding:"8px 10px",
                background:"white", border:"1px solid var(--border)", borderRadius:6 }}>
                {secKeyResult.raw_key}
              </code>
            </div>
            <Btn onClick={() => { setSecKeyModal(false); setSecKeyResult(null); }}>Done</Btn>
          </div>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Input label="Name" value={secKeyName} onChange={v => setSecKeyName(v)} />
            <Input label="Scopes (comma-separated)" value={secKeyScopes} onChange={v => setSecKeyScopes(v)}
              hint="e.g. read:jobs,write:bookings,read:analytics" />
            <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
              <Btn variant="ghost" onClick={() => setSecKeyModal(false)}>Cancel</Btn>
              <Btn onClick={createSecKey.execute} loading={createSecKey.loading}>Create</Btn>
            </div>
            {createSecKey.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{createSecKey.error}</p>}
          </div>
        )}
      </Modal>
    </TenantLayout>
  );
}
