"use client";

import React, { useCallback, useState } from "react";
import { Bot, CheckCircle2, Instagram, MessageCircle, RefreshCw, ShieldCheck, Sparkles, TestTube2, UserRoundCog } from "lucide-react";
import { TableSurface } from "@serviceos/design-system";

import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Badge, Btn, Card, EmptyState, Modal, Skeleton } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import {
  messagingChannelsApi,
  type MessagingChannelStatus,
  type MessagingThreadRecord,
} from "../../../lib/api";


const iconFor = (channel: string) => channel === "instagram" ? <Instagram size={20}/> : <MessageCircle size={20}/>;
const errorText = (value: unknown) => value instanceof Error ? value.message : "The operation could not be completed.";


export default function MessagingChannelsPage() {
  const channels = useApi(useCallback(() => messagingChannelsApi.list(), []), []);
  const threads = useApi(useCallback(() => messagingChannelsApi.threads(), []), []);
  const [selected, setSelected] = useState<MessagingChannelStatus | null>(null);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const open = (channel: MessagingChannelStatus) => {
    setSelected(channel);
    setMessage(null);
    setValues(Object.fromEntries(channel.fields.map(field => [field.key, field.secret ? "" : field.value])));
  };

  const run = async (key: string, action: () => Promise<MessagingChannelStatus>, success: string) => {
    setBusy(key); setMessage(null);
    try {
      const next = await action();
      setSelected(next);
      setValues(Object.fromEntries(next.fields.map(field => [field.key, field.secret ? "" : field.value])));
      setMessage({ ok: true, text: success });
      await channels.refetch();
    } catch (error) {
      setMessage({ ok: false, text: errorText(error) });
    } finally { setBusy(null); }
  };

  const setHandoff = async (thread: MessagingThreadRecord) => {
    setBusy(`thread-${thread.id}`);
    try {
      await messagingChannelsApi.setHandoff(thread.id, !thread.human_handoff);
      await threads.refetch();
    } finally { setBusy(null); }
  };

  const rows = channels.data?.items ?? [];
  const conversations = threads.data?.items ?? [];

  return <AdminLayout activeNav="messaging-channels">
    <div style={{ display: "grid", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div><h1 style={{ margin: 0, fontSize: 24 }}>Social booking</h1><p style={{ margin: "6px 0 0", color: "var(--text-secondary)", fontSize: 13 }}>Let customers book and track services through WhatsApp and Instagram using the same backend booking engine as the customer app.</p></div>
        <Btn variant="secondary" size="sm" onClick={() => { channels.refetch(); threads.refetch(); }}><RefreshCw size={14}/> Refresh</Btn>
      </div>

      <Card style={{ padding: 16, display: "flex", gap: 12, alignItems: "flex-start" }}>
        <ShieldCheck size={19} color="var(--success-text)"/>
        <div><strong style={{ fontSize: 13 }}>Credentials stay server-side</strong><p style={{ margin: "4px 0 0", color: "var(--text-secondary)", fontSize: 12 }}>Secrets are encrypted at rest, never returned to this browser, and changing any credential disables the channel until a new connection test passes.</p></div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))", gap: 14 }}>
        {channels.loading ? [0, 1].map(i => <Skeleton key={i} height={260}/>) : rows.map(channel => <Card key={channel.channel} style={{ padding: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <div style={{ width: 42, height: 42, borderRadius: 12, display: "grid", placeItems: "center", color: channel.enabled ? "var(--success-text)" : "var(--text-secondary)", background: channel.enabled ? "var(--success-bg)" : "var(--surface-sunken)" }}>{iconFor(channel.channel)}</div>
            <Badge variant={channel.enabled ? "success" : channel.state === "Failed" ? "danger" : channel.configured ? "warning" : "muted"}>{channel.state}</Badge>
          </div>
          <h2 style={{ margin: "13px 0 3px", fontSize: 16 }}>{channel.label}</h2>
          <p style={{ margin: 0, minHeight: 36, color: "var(--text-secondary)", fontSize: 12 }}>{channel.description}</p>
          <div style={{ borderTop: "1px solid var(--border)", marginTop: 14, paddingTop: 12, display: "grid", gap: 7, fontSize: 11 }}>
            {channel.channel === "whatsapp" && <Line label="Appointment Flow" value={channel.booking_flow_configured ? "Configured" : "List fallback"}/>}
            <Line label="Provider" value={channel.provider}/><Line label="Webhook" value={channel.webhook_path}/><Line label="Conversations" value={String(channel.thread_count)}/><Line label="Last test" value={channel.last_test_message ?? "Not tested"}/>{channel.channel === "instagram" && <Line label="Chat entry" value={channel.profile_sync_message ?? "Not published"}/>} 
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            <Btn size="sm" variant="secondary" onClick={() => open(channel)}>{channel.configured ? "Manage" : "Configure"}</Btn>
            {channel.configured && <Btn size="sm" variant="ghost" loading={busy === `test-${channel.channel}`} onClick={() => run(`test-${channel.channel}`, () => messagingChannelsApi.test(channel.channel), "Meta connection verified.")}><TestTube2 size={14}/> Test</Btn>}
            {channel.channel === "instagram" && channel.verified && <Btn size="sm" variant="ghost" loading={busy === "profile-instagram"} onClick={() => run("profile-instagram", () => messagingChannelsApi.syncProfile("instagram"), "Instagram icebreakers published.")}><Sparkles size={14}/> Publish chat entry</Btn>}
            {channel.verified && <Btn size="sm" variant={channel.enabled ? "ghost" : "primary"} loading={busy === `enable-${channel.channel}`} onClick={() => run(`enable-${channel.channel}`, () => messagingChannelsApi.setEnabled(channel.channel, !channel.enabled), `${channel.label} ${channel.enabled ? "disabled" : "enabled"}.`)}>{channel.enabled ? "Disable" : "Enable"}</Btn>}
          </div>
        </Card>)}
      </div>

      <div><h2 style={{ margin: "4px 0 10px", fontSize: 17 }}>Recent conversations</h2>
        {threads.error ? <EmptyState title="Conversations unavailable" description={threads.error}/> : conversations.length === 0 ? <Card style={{ padding: 28 }}><EmptyState title="No social booking conversations yet" description="Signed webhook messages will appear here after a channel is enabled."/></Card> : <Card style={{ overflow: "hidden" }}><TableSurface density="compact" style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}><thead><tr><Th>Channel</Th><Th>Customer</Th><Th>Last inbound</Th><Th>Mode</Th><Th>Sessions</Th><Th>Control</Th></tr></thead><tbody>{conversations.map(thread => <tr key={thread.id} style={{ borderTop: "1px solid var(--border)" }}><Td><Badge variant="muted">{thread.channel}</Badge></Td><Td>{thread.display_name ?? thread.channel_user_id}<div style={{ color: "var(--text-tertiary)", fontSize: 10 }}>{thread.customer_id ? "Account linked" : "Unlinked"}</div></Td><Td>{thread.last_inbound_at ? new Date(thread.last_inbound_at).toLocaleString() : "—"}</Td><Td><Badge variant={thread.human_handoff ? "warning" : thread.opted_out ? "muted" : "success"}>{thread.opted_out ? "Opted out" : thread.human_handoff ? "Human" : "Bot"}</Badge></Td><Td>{thread.session_count}</Td><Td><Btn size="xs" variant="ghost" disabled={thread.opted_out} loading={busy === `thread-${thread.id}`} onClick={() => setHandoff(thread)}>{thread.human_handoff ? <Bot size={13}/> : <UserRoundCog size={13}/>} {thread.human_handoff ? "Return to bot" : "Take over"}</Btn></Td></tr>)}</tbody></TableSurface></Card>}
      </div>
    </div>

    {selected && <Modal open title={`Configure ${selected.label}`} size="lg" onClose={() => setSelected(null)}><div style={{ display: "grid", gap: 16 }}>
      <div style={{ padding: 12, borderRadius: 10, background: "var(--info-bg)", color: "var(--info-text)", fontSize: 12 }}><strong>Meta callback path</strong><div style={{ marginTop: 4, fontFamily: "monospace" }}>{selected.webhook_path}</div><div style={{ marginTop: 5 }}>Use your public API origin plus this path in Meta. Subscribe WhatsApp to <code>messages</code>; subscribe Instagram to <code>messages</code> and <code>messaging_postbacks</code>.</div></div>
      {message && <div style={{ padding: 10, borderRadius: 8, background: message.ok ? "var(--success-bg)" : "var(--danger-bg)", color: message.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 12 }}>{message.text}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 12 }}>{selected.fields.map(field => <label key={field.key} style={{ display: "grid", gap: 5, fontSize: 12 }}><span style={{ fontWeight: 650 }}>{field.label}{field.required ? " *" : ""}</span><input type={field.secret ? "password" : field.type} value={String(values[field.key] ?? "")} placeholder={field.secret && field.has_value ? "Stored securely — enter only to rotate" : field.placeholder} onChange={event => setValues(current => ({ ...current, [field.key]: event.target.value }))} style={{ height: 38, padding: "0 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--input-bg)", color: "var(--text-primary)" }}/>{field.secret && field.has_value && <span style={{ color: "var(--text-tertiary)", fontSize: 10 }}>A value is stored. Leave blank to keep it.</span>}</label>)}</div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, flexWrap: "wrap" }}><Btn variant="ghost" onClick={() => setSelected(null)}>Close</Btn><Btn variant="secondary" disabled={!selected.configured} loading={busy === "test"} onClick={() => run("test", () => messagingChannelsApi.test(selected.channel), "Meta connection verified. You can enable booking now.")}><TestTube2 size={14}/> Test connection</Btn><Btn loading={busy === "save"} onClick={() => run("save", () => messagingChannelsApi.save(selected.channel, values), "Configuration encrypted and saved. Test it before enabling.")}><CheckCircle2 size={14}/> Save securely</Btn></div>
    </div></Modal>}
  </AdminLayout>;
}

function Line({ label, value }: { label: string; value: string }) { return <div style={{ display: "flex", justifyContent: "space-between", gap: 14 }}><span style={{ color: "var(--text-tertiary)" }}>{label}</span><span style={{ textAlign: "right", overflowWrap: "anywhere" }}>{value}</span></div>; }
function Th({ children }: { children: React.ReactNode }) { return <th style={{ padding: "10px 12px", textAlign: "left", color: "var(--text-tertiary)", fontWeight: 650 }}>{children}</th>; }
function Td({ children }: { children: React.ReactNode }) { return <td style={{ padding: "11px 12px", verticalAlign: "middle" }}>{children}</td>; }
