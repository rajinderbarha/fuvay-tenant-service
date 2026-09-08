"use client";
import React, { useCallback, useState } from "react";
import { CheckCircle2, CircleOff, Clock3, Eye, EyeOff, History, HardDrive, Info, ShieldCheck, TestTube2 } from "lucide-react";
import { Badge, Btn, Card, EmptyState, Input, Skeleton } from "../../../components/shared/ui";
import { sprint27AdminApi, type NotificationChannelAudit, type NotificationChannelField, type NotificationChannelStatus } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";

const errorText = (value: unknown) => value instanceof Error ? value.message : "The operation could not be completed.";

/** Cloudinary credentials, configured the same way as Razorpay/WhatsApp:
 * saved encrypted, connection-tested, then explicitly enabled. Once enabled
 * and passing, every new upload (provider logos, service icons, business
 * documents, ...) prefers this over the CLOUDINARY_* env vars -- no restart
 * needed. Files already stored locally are NOT moved automatically; use the
 * one-off backfill script to migrate them once this is enabled. */
export function StorageConfigPanel() {
  const api = useApi(useCallback(() => sprint27AdminApi.getChannelConfiguration("cloudinary"), []), []);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ tone: "success" | "danger" | "info"; text: string } | null>(null);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [audit, setAudit] = useState<NotificationChannelAudit[] | null>(null);

  const row = api.data;
  const sync = (next: NotificationChannelStatus) => setValues(Object.fromEntries(next.fields.map(field => [field.key, field.secret ? "" : field.value])));

  React.useEffect(() => { if (row) sync(row); }, [row?.channel, row?.credential_fingerprint]); // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (key: string, action: () => Promise<NotificationChannelStatus>, success: string) => {
    setBusy(key); setMessage(null);
    try { sync(await action()); setMessage({ tone: "success", text: success }); await api.refetch(); }
    catch (error) { setMessage({ tone: "danger", text: errorText(error) }); }
    finally { setBusy(null); }
  };
  const loadAudit = async () => {
    setBusy("audit");
    try { setAudit((await sprint27AdminApi.getChannelAudit("cloudinary")).items); }
    catch (error) { setMessage({ tone: "danger", text: errorText(error) }); }
    finally { setBusy(null); }
  };

  if (api.loading) return <Skeleton height={360}/>;
  if (api.error || !row) return <EmptyState title="Cloudinary configuration is unavailable" description={`${api.error ?? "Unknown error"}${api.requestId ? ` · ${api.requestId}` : ""}`} action={<Btn size="sm" onClick={api.refetch}>Retry</Btn>}/>;

  return <div className="nc-stack">
    <Card style={{ padding: 16, display: "flex", gap: 12, alignItems: "flex-start" }}>
      <ShieldCheck size={19} color="var(--info-text)"/>
      <div><strong style={{ fontSize: 13 }}>Media storage credentials</strong><p style={{ margin: "4px 0 0", color: "var(--text-secondary)", fontSize: 12 }}>Rotate the Cloudinary Cloud name / API key / API secret from here instead of editing the server .env. Secrets are encrypted at rest, never returned to this browser, and changing any credential disables uploads to this storage until a new connection test passes.</p></div>
    </Card>

    <Card style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div style={{ width: 42, height: 42, borderRadius: 12, display: "grid", placeItems: "center", background: row.enabled ? "var(--success-bg)" : "var(--surface-sunken)", color: row.enabled ? "var(--success-text)" : "var(--text-tertiary)" }}><HardDrive size={20}/></div>
          <div><h3 style={{ margin: 0, fontSize: 16 }}>{row.provider}</h3><p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-tertiary)" }}>{row.description}</p></div>
        </div>
        <Badge variant={row.enabled ? "success" : row.state === "Failed" ? "danger" : row.setup_complete ? "warning" : "muted"}>{row.state}</Badge>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8, margin: "18px 0" }}>
        <Step number="1" label="Save configuration" complete={row.setup_complete}/>
        <Step number="2" label="Test connection" complete={row.verified}/>
        <Step number="3" label="Enable storage" complete={row.enabled}/>
      </div>

      {message && <div className={`nc-message ${message.tone}`} style={{ marginBottom: 14 }}>{message.text}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 14 }}>
        {row.fields.map(field => <FieldInput key={field.key} field={field} value={values[field.key]} show={!!showSecrets[field.key]} onShow={() => setShowSecrets(current => ({ ...current, [field.key]: !current[field.key] }))} onChange={value => setValues(current => ({ ...current, [field.key]: value }))}/>)}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
        <Btn variant="ghost" onClick={loadAudit} loading={busy === "audit"}><History size={14}/> Configuration history</Btn>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn variant="secondary" disabled={!row.setup_complete} loading={busy === "test"} onClick={() => run("test", () => sprint27AdminApi.testChannelConfiguration("cloudinary"), "Cloudinary credentials verified. You can now enable storage.")}><TestTube2 size={14}/> Test connection</Btn>
          {row.verified && <Btn variant={row.enabled ? "ghost" : "primary"} loading={busy === "toggle"} onClick={() => run("toggle", () => sprint27AdminApi.setChannelEnabled("cloudinary", !row.enabled), `Cloudinary storage ${row.enabled ? "disabled" : "enabled"}.`)}>{row.enabled ? <CircleOff size={14}/> : <CheckCircle2 size={14}/>} {row.enabled ? "Disable storage" : "Enable storage"}</Btn>}
          <Btn loading={busy === "save"} onClick={() => run("save", () => sprint27AdminApi.saveChannelConfiguration("cloudinary", values), "Configuration encrypted and saved. Test it before enabling storage.")}><ShieldCheck size={14}/> Save securely</Btn>
        </div>
      </div>

      {audit && <div style={{ borderTop: "1px solid var(--border)", marginTop: 16, paddingTop: 14 }}>
        <strong style={{ fontSize: 12 }}>Recent configuration activity</strong>
        {audit.length === 0 ? <p style={{ color: "var(--text-tertiary)", fontSize: 11 }}>No configuration changes recorded.</p> : <div style={{ display: "grid", gap: 7, marginTop: 9 }}>{audit.slice(0, 10).map(item => <div key={item.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 11 }}><span><History size={12} style={{ verticalAlign: "middle", marginRight: 6 }}/>{item.action.replace(/_/g, " ")}</span><span style={{ color: "var(--text-tertiary)" }}>{new Date(item.created_at).toLocaleString()}</span></div>)}</div>}
      </div>}
    </Card>

    <div className="nc-callout"><Info size={17}/><div><strong>What moves to Cloudinary once enabled</strong><p>Every new upload -- provider/business logos, service &amp; category icons, brand logos, business verification documents, profile photos -- is stored on Cloudinary and served over HTTPS from its CDN the moment this passes its connection test, no restart needed. Files already sitting on local disk stay there until migrated; ask an engineer to run the one-off Cloudinary backfill script to move them. The browser-tab favicon is a separate, build-time asset and is never affected by this setting.</p></div></div>
  </div>;
}

function FieldInput({ field, value, show, onShow, onChange }: { field: NotificationChannelField; value: string | boolean | undefined; show: boolean; onShow: () => void; onChange: (value: string) => void }) {
  const hint = field.secret && field.has_value ? "A credential is stored. Leave blank to keep it unchanged." : field.required ? "Required" : "Optional";
  return <div style={{ position: "relative" }}>
    <Input label={field.label} required={field.required} type={field.secret && !show ? "password" : field.type} value={String(value ?? "")} placeholder={field.secret && field.has_value ? "Stored securely — enter only to rotate" : field.placeholder} hint={hint} onChange={onChange}/>
    {field.secret && <button type="button" onClick={onShow} aria-label={show ? "Hide credential" : "Show credential"} style={{ position: "absolute", right: 9, top: 31, border: 0, background: "transparent", color: "var(--text-tertiary)", cursor: "pointer" }}>{show ? <EyeOff size={15}/> : <Eye size={15}/>}</button>}
  </div>;
}
function Step({ number, label, complete }: { number: string; label: string; complete: boolean }) {
  return <div style={{ padding: 10, borderRadius: 10, border: `1px solid ${complete ? "var(--success-border)" : "var(--border)"}`, background: complete ? "var(--success-bg)" : "var(--surface)", display: "flex", gap: 8, alignItems: "center", fontSize: 11, color: complete ? "var(--success-text)" : "var(--text-secondary)" }}>{complete ? <CheckCircle2 size={15}/> : <Clock3 size={15}/>}<span>{number}. {label}</span></div>;
}
