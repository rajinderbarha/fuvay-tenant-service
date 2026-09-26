"use client";

import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useMemo, useState } from "react";
import { Edit3, Eye, History, RefreshCw, Search, ShieldCheck } from "lucide-react";
import {
  Badge, Btn, Card, EmptyState, Input, Modal, Pagination, Select, Skeleton, Textarea,
} from "../../../components/shared/ui";
import {
  notifTemplateAdminApi,
  type AdminNotifTemplate,
  type NotifTemplatePreview,
  type NotifTemplateVersion,
} from "../../../lib/api";
import { useAction, useApi } from "../../../hooks/useApi";

const PAGE_SIZE = 20;
type EditForm = { title: string; body: string; action_label: string; reason: string };

const humanize = (value: string | null | undefined) =>
  (value || "General").replace(/^customer_/, "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

export function ManagedMessagesPanel() {
  const [query, setQuery] = useState("");
  const [channel, setChannel] = useState("");
  const [audience, setAudience] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<AdminNotifTemplate | null>(null);
  const [form, setForm] = useState<EditForm>({ title: "", body: "", action_label: "", reason: "" });
  const [preview, setPreview] = useState<NotifTemplatePreview | null>(null);
  const [versions, setVersions] = useState<{ template: AdminNotifTemplate; rows: NotifTemplateVersion[] } | null>(null);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  const templates = useApi(useCallback(() => notifTemplateAdminApi.listTemplates(), []), []);
  const summary = useApi(useCallback(() => notifTemplateAdminApi.getSummary(), []), []);
  const update = useAction((id: string, data: Record<string, unknown>) => notifTemplateAdminApi.updateTemplate(id, data));
  const previewAction = useAction((id: string, sample: Record<string, string>) => notifTemplateAdminApi.renderPreview(id, sample));
  const historyAction = useAction((id: string) => notifTemplateAdminApi.listVersions(id));
  const activate = useAction((id: string) => notifTemplateAdminApi.activate(id));
  const deactivate = useAction((id: string) => notifTemplateAdminApi.deactivate(id));

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (templates.data?.items ?? []).filter(row =>
      (!channel || row.channel === channel) &&
      (!audience || row.audience === audience) &&
      (!q || `${row.title ?? ""} ${row.body} ${humanize(row.event_type)}`.toLowerCase().includes(q))
    );
  }, [templates.data, query, channel, audience]);
  const rows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const channels = Array.from(new Set((templates.data?.items ?? []).map(row => row.channel))).sort();
  const audiences = Array.from(new Set((templates.data?.items ?? []).map(row => row.audience))).sort();

  function openEdit(row: AdminNotifTemplate) {
    setEditing(row);
    setForm({ title: row.title ?? "", body: row.body, action_label: row.action_label ?? "", reason: "" });
    setNotice(null);
  }

  async function save() {
    if (!editing || !form.title.trim() || !form.body.trim() || !form.reason.trim()) return;
    const result = await update.execute(editing.template_id, {
      title: form.title.trim(), body: form.body, action_label: form.action_label.trim(), reason: form.reason.trim(),
    });
    if (result) {
      setEditing(null);
      setNotice({ ok: true, text: "Message updated. The next matching notification will use this wording." });
      templates.refetch(); summary.refetch();
    }
  }

  async function showPreview(row: AdminNotifTemplate) {
    const sample = Object.fromEntries(row.variables.map(name => [name, humanize(name)]));
    const result = await previewAction.execute(row.template_id, sample);
    if (result) setPreview(result);
  }

  async function showHistory(row: AdminNotifTemplate) {
    const result = await historyAction.execute(row.template_id);
    if (result) setVersions({ template: row, rows: result.items });
  }

  async function changeState(row: AdminNotifTemplate) {
    const result = row.status === "active"
      ? await deactivate.execute(row.template_id)
      : await activate.execute(row.template_id);
    if (result) {
      setNotice({ ok: true, text: `${row.title ?? humanize(row.event_type)} ${row.status === "active" ? "disabled" : "enabled"}. Safe system fallback copy remains available.` });
      templates.refetch(); summary.refetch();
    }
  }

  return <div className="nc-stack">
    <div className="nc-settings-hero">
      <div><span className="nc-eyebrow">ADMIN-MANAGED MESSAGE LIBRARY</span><h2>Customer, provider and reminder wording</h2><p>Edit live message copy without a deployment. Every change is validated, versioned and audited; protected fallback wording keeps operations running.</p></div>
      <div className="nc-health-chip"><strong>{summary.data?.active_templates ?? 0}</strong><span>active of {summary.data?.total_templates ?? 0}</span></div>
    </div>
    {notice && <div className={`nc-message ${notice.ok ? "success" : "danger"}`}>{notice.text}</div>}
    <Card padding={0}>
      <div className="nc-filterbar"><div className="nc-search"><Search size={15}/><Input placeholder="Search message name or wording" value={query} onChange={value => { setQuery(value); setPage(1); }}/></div><Select value={channel} onChange={value => { setChannel(value); setPage(1); }} options={[{ value: "", label: "All channels" }, ...channels.map(value => ({ value, label: humanize(value) }))]}/><Select value={audience} onChange={value => { setAudience(value); setPage(1); }} options={[{ value: "", label: "All recipients" }, ...audiences.map(value => ({ value, label: humanize(value) }))]}/><Btn size="sm" variant="ghost" onClick={() => { templates.refetch(); summary.refetch(); }}><RefreshCw size={14}/></Btn></div>
      {templates.error ? <div className="nc-empty-error">{templates.error}{templates.requestId ? ` · ${templates.requestId}` : ""}</div> : templates.loading ? <div style={{ padding: 18 }}>{Array.from({ length: 7 }, (_, i) => <Skeleton key={i} height={52} style={{ marginBottom: 8 }}/>)}</div> : rows.length === 0 ? <EmptyState title="No messages match" description="Clear the filters or search for another message."/> : <div style={{ overflowX: "auto" }}><TableSurface className="nc-table"><thead><tr><th>Message</th><th>Channel</th><th>Recipient</th><th>Status</th><th>Last changed</th><th></th></tr></thead><tbody>{rows.map(row => <tr key={row.template_id}><td><div className="nc-notif-title">{row.title || humanize(row.event_type)}</div><div className="nc-notif-body">{row.body.replace(/\n/g, " ")}</div></td><td><Badge variant={row.channel === "instagram" ? "success" : "muted"}>{humanize(row.channel)}</Badge></td><td>{humanize(row.audience)}</td><td><Badge variant={row.status === "active" ? "success" : "muted"}>{humanize(row.status)}</Badge></td><td>{row.updated_at ? new Date(row.updated_at).toLocaleString() : "—"}</td><td><div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}><Btn size="xs" variant="secondary" onClick={() => openEdit(row)}><Edit3 size={12}/> Edit</Btn><Btn size="xs" variant="ghost" onClick={() => showPreview(row)}><Eye size={12}/> Preview</Btn><Btn size="xs" variant="ghost" onClick={() => showHistory(row)}><History size={12}/> History</Btn><Btn size="xs" variant="ghost" onClick={() => changeState(row)}>{row.status === "active" ? "Disable" : "Enable"}</Btn></div></td></tr>)}</tbody></TableSurface></div>}
      <Pagination page={page} total={filtered.length} pageSize={PAGE_SIZE} onPage={setPage}/>
    </Card>
    <div className="nc-callout"><ShieldCheck size={17}/><div><strong>Safe editing controls</strong><p>Placeholders shown in the editor are protected. A message with a missing value is rejected at runtime and the approved fallback copy is sent instead.</p></div></div>

    {editing && <Modal open onClose={() => setEditing(null)} title={`Edit ${editing.title ?? humanize(editing.event_type)}`} size="lg"><div className="nc-stack"><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}><Input label="Message heading" value={form.title} onChange={value => setForm(current => ({ ...current, title: value }))}/><Input label="Primary button label" value={form.action_label} onChange={value => setForm(current => ({ ...current, action_label: value }))} hint="Used when this message has an action button"/></div><Textarea label="Message text" value={form.body} onChange={value => setForm(current => ({ ...current, body: value }))} rows={11} required/><div><div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 6 }}>Available placeholders</div><div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{editing.variables.length ? editing.variables.map(value => <Badge key={value} variant="muted">{`{{${value}}}`}</Badge>) : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>This message has no dynamic values.</span>}</div></div><Input label="Reason for change" value={form.reason} onChange={value => setForm(current => ({ ...current, reason: value }))} hint="Required for the audit history"/>{update.error && <div className="nc-message danger">{update.error}</div>}<div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><Btn variant="ghost" onClick={() => setEditing(null)}>Cancel</Btn><Btn onClick={save} loading={update.loading} disabled={!form.title.trim() || !form.body.trim() || !form.reason.trim()}>Save version</Btn></div></div></Modal>}
    {preview && <Modal open onClose={() => setPreview(null)} title="Message preview" size="md"><div className="nc-stack"><div className="nc-callout"><Eye size={17}/><div><strong>{preview.rendered_title}</strong><p style={{ whiteSpace: "pre-wrap" }}>{preview.rendered_body}</p></div></div>{preview.missing_variables.length > 0 && <div className="nc-message danger">Missing values: {preview.missing_variables.map(humanize).join(", ")}</div>}<div style={{ display: "flex", justifyContent: "flex-end" }}><Btn onClick={() => setPreview(null)}>Close</Btn></div></div></Modal>}
    {versions && <Modal open onClose={() => setVersions(null)} title={`History · ${versions.template.title ?? humanize(versions.template.event_type)}`} size="md"><div className="nc-stack">{versions.rows.length === 0 ? <EmptyState title="No earlier versions" description="The first saved change will create version history."/> : versions.rows.sort((a, b) => b.version_number - a.version_number).map(version => <Card key={version.id}><div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}><strong>Version {version.version_number}</strong><span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{new Date(version.created_at).toLocaleString()}</span></div><p style={{ margin: "7px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>{version.change_reason || "Saved change"}</p></Card>)}</div></Modal>}
  </div>;
}
