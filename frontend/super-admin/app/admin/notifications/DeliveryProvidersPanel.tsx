"use client";
import React, { useCallback, useState } from "react";
import { Bell, CheckCircle2, CircleOff, Clock3, Eye, EyeOff, History, Info, Mail, MessageCircle, Plus, RefreshCw, Settings2, ShieldCheck, Smartphone, TestTube2 } from "lucide-react";
import { Badge, Btn, Card, EmptyState, Input, Modal, Select, Skeleton } from "../../../components/shared/ui";
import { sprint27AdminApi, type NotificationChannelAudit, type NotificationChannelField, type NotificationChannelStatus } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";

const LABEL: Record<string, string> = { in_app: "In-app inbox", email: "Email", sms: "SMS", whatsapp: "WhatsApp", push: "Mobile push" };
const ICON: Record<string, React.ReactNode> = { in_app: <Bell size={18}/>, email: <Mail size={18}/>, sms: <Smartphone size={18}/>, whatsapp: <MessageCircle size={18}/>, push: <Smartphone size={18}/> };
const errorText = (value: unknown) => value instanceof Error ? value.message : "The operation could not be completed.";

export function DeliveryProvidersPanel() {
  const api = useApi(useCallback(() => sprint27AdminApi.getChannelStatus(), []), []);
  const rows = api.data?.items ?? [];
  const [selected, setSelected] = useState<NotificationChannelStatus | null>(null);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ tone: "success" | "danger" | "info"; text: string } | null>(null);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [audit, setAudit] = useState<NotificationChannelAudit[] | null>(null);
  const [chooserOpen, setChooserOpen] = useState(false);
  const live = rows.filter(r => r.configured).length;
  const needsAction = rows.filter(r => r.managed && !r.configured).length;
  const failed = rows.filter(r => r.state === "Failed").length;

  const openConfiguration = (row: NotificationChannelStatus) => {
    setSelected(row); setMessage(null); setAudit(null); setShowSecrets({});
    setValues(Object.fromEntries(row.fields.map(field => [field.key, field.secret ? "" : field.value])));
  };
  const run = async (key: string, action: () => Promise<NotificationChannelStatus>, success: string) => {
    setBusy(key); setMessage(null);
    try {
      const next = await action();
      if (selected) {
        setSelected(next); setMessage({ tone: "success", text: success });
        setValues(Object.fromEntries(next.fields.map(field => [field.key, field.secret ? "" : field.value])));
      }
      await api.refetch();
    } catch (error) { setMessage({ tone: "danger", text: errorText(error) }); }
    finally { setBusy(null); }
  };
  const loadAudit = async () => {
    if (!selected) return;
    setBusy("audit");
    try { setAudit((await sprint27AdminApi.getChannelAudit(selected.channel)).items); }
    catch (error) { setMessage({ tone: "danger", text: errorText(error) }); }
    finally { setBusy(null); }
  };

  if (api.error) return <EmptyState title="Channel health is unavailable" description={`${api.error}${api.requestId ? ` · ${api.requestId}` : ""}`} action={<Btn size="sm" onClick={api.refetch}>Retry</Btn>}/>;
  return <div className="nc-stack">
    <div className="nc-kpis">{api.loading ? Array.from({ length: 4 }, (_, i) => <Skeleton key={i} height={84}/>) : <>
      <div className="nc-kpi brand"><strong>{live}</strong><span>Active channels</span></div>
      <div className="nc-kpi"><strong>{rows.filter(r => r.setup_complete).length}</strong><span>Configured providers</span></div>
      <div className="nc-kpi"><strong>{needsAction}</strong><span>Need configuration</span></div>
      <div className={`nc-kpi ${failed ? "danger" : ""}`}><strong>{failed}</strong><span>Failed health checks</span></div>
    </>}</div>

    <Card style={{ padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 18 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}><ShieldCheck size={18} color="var(--info-text)"/><div><strong style={{ fontSize: 13 }}>Secure provider control plane</strong><p style={{ margin: "3px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>Configure credentials, verify the connection, then enable delivery. Secrets are encrypted and are never returned to this browser.</p></div></div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Btn size="sm" variant="secondary" onClick={api.refetch}><RefreshCw size={14}/> Refresh health</Btn>
        <Btn size="sm" onClick={() => setChooserOpen(true)}><Plus size={14}/> Configure channel</Btn>
      </div>
    </Card>
    {message && !selected && <div className={`nc-message ${message.tone}`}>{message.text}</div>}

    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 12 }}>
      {api.loading ? Array.from({ length: 5 }, (_, i) => <Skeleton key={i} height={270}/>) : rows.map(row => <Card key={row.channel} style={{ padding: 18 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}><div style={{ width: 40, height: 40, borderRadius: 11, display: "grid", placeItems: "center", background: row.configured ? "var(--success-bg)" : "var(--surface-sunken)", color: row.configured ? "var(--success-text)" : "var(--text-tertiary)" }}>{ICON[row.channel]}</div><Badge variant={row.configured ? "success" : row.state === "Failed" ? "danger" : row.setup_complete ? "warning" : "muted"}>{row.state}</Badge></div>
        <h3 style={{ margin: "13px 0 2px", fontSize: 15 }}>{LABEL[row.channel] ?? row.channel}</h3>
        <p style={{ margin: 0, minHeight: 32, fontSize: 11, color: "var(--text-tertiary)" }}>{row.description}</p>
        <div style={{ borderTop: "1px solid var(--border)", marginTop: 14, paddingTop: 12, display: "grid", gap: 8 }}><Line label="Provider" value={row.provider ?? "Not selected"}/><Line label="Connection test" value={row.last_health_check ? `${row.last_test_status} · ${new Date(row.last_health_check).toLocaleString()}` : row.channel === "in_app" ? "Built in" : "Not tested"}/><Line label="Last delivery" value={row.last_successful_delivery ? new Date(row.last_successful_delivery).toLocaleString() : "No successful attempts"}/><Line label="Failure rate" value={row.failure_rate_pct === null ? "No attempts" : `${row.failure_rate_pct}%`}/></div>
        <div style={{ marginTop: 14, display: "flex", gap: 7, flexWrap: "wrap" }}>
          {row.managed ? <Btn size="sm" variant="secondary" onClick={() => openConfiguration(row)}><Settings2 size={14}/>{row.setup_complete ? "Manage" : "Configure"}</Btn> : <Badge variant="info">Platform managed</Badge>}
          {row.managed && row.setup_complete && <Btn size="sm" variant="ghost" loading={busy === `test-${row.channel}`} onClick={() => run(`test-${row.channel}`, () => sprint27AdminApi.testChannelConfiguration(row.channel), `${LABEL[row.channel]} connection verified.`)}><TestTube2 size={14}/> Test</Btn>}
          {row.managed && row.verified && <Btn size="sm" variant={row.enabled ? "ghost" : "primary"} loading={busy === `toggle-${row.channel}`} onClick={() => run(`toggle-${row.channel}`, () => sprint27AdminApi.setChannelEnabled(row.channel, !row.enabled), `${LABEL[row.channel]} ${row.enabled ? "disabled" : "enabled"}.`)}>{row.enabled ? <CircleOff size={14}/> : <CheckCircle2 size={14}/>} {row.enabled ? "Disable" : "Enable"}</Btn>}
        </div>
      </Card>)}
    </div>
    <div className="nc-callout"><Info size={17}/><div><strong>Activation is intentionally gated</strong><p>Saving credentials does not send notifications. A successful provider test is required before Enable becomes available; changing a secret automatically disables the channel until it is tested again.</p></div></div>

    <Modal open={chooserOpen} onClose={() => setChooserOpen(false)} title="Configure a delivery channel" size="lg">
      <div style={{ display: "grid", gap: 16 }}>
        <div style={{ padding: 14, borderRadius: 12, background: "var(--info-bg)", border: "1px solid var(--info-border)", color: "var(--info-text)", fontSize: 12 }}>
          Choose a provider below. You will save its credentials, test the connection, and then explicitly enable delivery.
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 10 }}>
          {rows.filter(row => row.managed).map(row => <button key={row.channel} type="button" onClick={() => { setChooserOpen(false); openConfiguration(row); }} style={{ padding: 16, textAlign: "left", borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", cursor: "pointer", display: "flex", gap: 12, alignItems: "flex-start" }}>
            <span style={{ width: 36, height: 36, borderRadius: 10, display: "grid", placeItems: "center", background: row.configured ? "var(--success-bg)" : "var(--surface-sunken)", color: row.configured ? "var(--success-text)" : "var(--text-secondary)", flexShrink: 0 }}>{ICON[row.channel]}</span>
            <span style={{ display: "grid", gap: 3 }}><strong style={{ fontSize: 13 }}>{LABEL[row.channel]}</strong><span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{row.provider}</span><Badge variant={row.configured ? "success" : row.setup_complete ? "warning" : "muted"}>{row.state}</Badge></span>
          </button>)}
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end" }}><Btn variant="ghost" onClick={() => setChooserOpen(false)}>Cancel</Btn></div>
      </div>
    </Modal>

    {selected && <Modal open onClose={() => setSelected(null)} title={`Configure ${LABEL[selected.channel]}`} size="lg"><div style={{ display: "grid", gap: 18 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8 }}><Step number="1" label="Save configuration" complete={selected.setup_complete}/><Step number="2" label="Test connection" complete={selected.verified}/><Step number="3" label="Enable delivery" complete={selected.enabled}/></div>
      {message && <div className={`nc-message ${message.tone}`}>{message.text}</div>}
      <div style={{ padding: 14, borderRadius: 12, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}><strong style={{ fontSize: 13 }}>{selected.provider}</strong><p style={{ margin: "3px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>{selected.description}</p></div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 14 }}>{selected.fields.map(field => <FieldInput key={field.key} field={field} value={values[field.key]} show={!!showSecrets[field.key]} onShow={() => setShowSecrets(current => ({ ...current, [field.key]: !current[field.key] }))} onChange={value => setValues(current => ({ ...current, [field.key]: value }))}/>)}</div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", paddingTop: 4 }}><Btn variant="ghost" onClick={loadAudit} loading={busy === "audit"}><History size={14}/> Configuration history</Btn><div style={{ display: "flex", gap: 8 }}><Btn variant="ghost" onClick={() => setSelected(null)}>Close</Btn><Btn variant="secondary" disabled={!selected.setup_complete} loading={busy === "test"} onClick={() => run("test", () => sprint27AdminApi.testChannelConfiguration(selected.channel), "Connection verified. You can now enable delivery.")}><TestTube2 size={14}/> Test connection</Btn><Btn loading={busy === "save"} onClick={() => run("save", () => sprint27AdminApi.saveChannelConfiguration(selected.channel, values), "Configuration saved. Test the connection before enabling delivery.")}><ShieldCheck size={14}/> Save securely</Btn></div></div>
      {audit && <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}><strong style={{ fontSize: 12 }}>Recent configuration activity</strong>{audit.length === 0 ? <p style={{ color: "var(--text-tertiary)", fontSize: 11 }}>No configuration changes recorded.</p> : <div style={{ display: "grid", gap: 7, marginTop: 9 }}>{audit.slice(0, 10).map(item => <div key={item.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 11 }}><span><History size={12} style={{ verticalAlign: "middle", marginRight: 6 }}/>{item.action.replace(/_/g, " ")}</span><span style={{ color: "var(--text-tertiary)" }}>{new Date(item.created_at).toLocaleString()}</span></div>)}</div>}</div>}
    </div></Modal>}
  </div>;
}

function FieldInput({ field, value, show, onShow, onChange }: { field: NotificationChannelField; value: string | boolean | undefined; show: boolean; onShow: () => void; onChange: (value: string) => void }) {
  const hint = field.secret && field.has_value ? "A credential is stored. Leave blank to keep it unchanged." : field.required ? "Required" : "Optional";
  if (field.type === "select") return <Select label={field.label} value={String(value ?? "")} onChange={onChange} options={field.options ?? []}/>;
  return <div style={{ position: "relative" }}><Input label={field.label} required={field.required} type={field.secret && !show ? "password" : field.type} value={String(value ?? "")} placeholder={field.secret && field.has_value ? "Stored securely — enter only to rotate" : field.placeholder} hint={hint} onChange={onChange}/>{field.secret && <button type="button" onClick={onShow} aria-label={show ? "Hide credential" : "Show credential"} style={{ position: "absolute", right: 9, top: 31, border: 0, background: "transparent", color: "var(--text-tertiary)", cursor: "pointer" }}>{show ? <EyeOff size={15}/> : <Eye size={15}/>}</button>}</div>;
}
function Step({ number, label, complete }: { number: string; label: string; complete: boolean }) { return <div style={{ padding: 10, borderRadius: 10, border: `1px solid ${complete ? "var(--success-border)" : "var(--border)"}`, background: complete ? "var(--success-bg)" : "var(--surface)", display: "flex", gap: 8, alignItems: "center", fontSize: 11, color: complete ? "var(--success-text)" : "var(--text-secondary)" }}>{complete ? <CheckCircle2 size={15}/> : <Clock3 size={15}/>}<span>{number}. {label}</span></div>; }
function Line({ label, value }: { label: string; value: string }) { return <div style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 11 }}><span style={{ color: "var(--text-tertiary)" }}>{label}</span><span style={{ color: "var(--text-primary)", textAlign: "right" }}>{value}</span></div>; }
