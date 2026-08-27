"use client";
import { TableSurface } from "@serviceos/design-system";

import React, { useCallback, useMemo, useState } from "react";
import { CheckCircle2, Edit3, FileText, Plus, Power, RefreshCw, Search } from "lucide-react";
import { Badge, Btn, Card, EmptyState, Input, Modal, Pagination, Select, Skeleton, Textarea } from "../../../components/shared/ui";
import { sprint27AdminApi, type NotifEventTemplate } from "../../../lib/api";
import { useAction, useApi } from "../../../hooks/useApi";

const PAGE_SIZE = 20;
type Form = { template_key: string; template_name: string; channel: string; subject_template: string; body_template: string; action_label_template: string; action_url_template: string };
const EMPTY: Form = { template_key: "", template_name: "", channel: "in_app", subject_template: "", body_template: "", action_label_template: "", action_url_template: "" };

export function RuntimeTemplatesPanel() {
  const templates = useApi(useCallback(() => sprint27AdminApi.listTemplates(), []), []);
  const [query, setQuery] = useState(""); const [status, setStatus] = useState(""); const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<NotifEventTemplate | "new" | null>(null); const [form, setForm] = useState<Form>(EMPTY);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const createAction = useAction((body: Partial<NotifEventTemplate>) => sprint27AdminApi.createTemplate(body));
  const updateAction = useAction((id: string, body: Partial<NotifEventTemplate>) => sprint27AdminApi.updateTemplate(id, body));
  const activateAction = useAction((id: string) => sprint27AdminApi.activateTemplate(id));
  const deactivateAction = useAction((id: string) => sprint27AdminApi.deactivateTemplate(id));
  const filtered = useMemo(() => { const q = query.trim().toLowerCase(); return (templates.data?.items ?? []).filter(t => (!status || (status === "active" ? t.is_active : !t.is_active)) && (!q || t.template_name.toLowerCase().includes(q) || t.template_key.toLowerCase().includes(q) || t.body_template.toLowerCase().includes(q))); }, [templates.data, query, status]);
  const rows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE); const active = (templates.data?.items ?? []).filter(t => t.is_active).length;
  function edit(row: NotifEventTemplate) { setEditing(row); setForm({ template_key: row.template_key, template_name: row.template_name, channel: row.channel, subject_template: row.subject_template ?? "", body_template: row.body_template, action_label_template: row.action_label_template ?? "", action_url_template: row.action_url_template ?? "" }); }
  function create() { setEditing("new"); setForm(EMPTY); }
  async function save() {
    if (!form.template_name.trim() || !form.body_template.trim() || !form.template_key.trim()) return;
    const payload = { ...form, subject_template: form.subject_template || null, action_label_template: form.action_label_template || null, action_url_template: form.action_url_template || null };
    const result = editing === "new" ? await createAction.execute(payload) : editing ? await updateAction.execute(editing.id, payload) : null;
    if (result) { setEditing(null); templates.refetch(); setNotice({ ok: true, text: "Runtime template saved." }); }
  }
  async function changeState(row: NotifEventTemplate) { const result = row.is_active ? await deactivateAction.execute(row.id) : await activateAction.execute(row.id); if (result) { templates.refetch(); setNotice({ ok: true, text: `${row.template_name} ${row.is_active ? "deactivated" : "activated"}.` }); } }
  return <div className="nc-stack">
    <div className="nc-settings-hero"><div><span className="nc-eyebrow">CANONICAL RUNTIME LIBRARY</span><h2>Delivery templates</h2><p>These records are resolved by fire_event() and rendered into the live notification outbox.</p></div><div style={{ display: "flex", gap: 9 }}><div className="nc-health-chip"><strong>{active}</strong><span>active of {templates.data?.total ?? 0}</span></div><Btn size="sm" onClick={create}><Plus size={14}/> New template</Btn></div></div>
    {notice && <div className={`nc-message ${notice.ok ? "success" : "danger"}`}>{notice.text}</div>}
    <Card padding={0}><div className="nc-filterbar"><div className="nc-search"><Search size={15}/><Input placeholder="Search key, title, or body" value={query} onChange={v => { setQuery(v); setPage(1); }}/></div><Select value={status} onChange={v => { setStatus(v); setPage(1); }} options={[{ value: "", label: "All states" }, { value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]}/><Btn size="sm" variant="ghost" onClick={templates.refetch}><RefreshCw size={14}/></Btn></div>
      {templates.error ? <div className="nc-empty-error">{templates.error}{templates.requestId ? ` · ${templates.requestId}` : ""}</div> : templates.loading ? <div style={{ padding: 18 }}>{Array.from({ length: 7 }, (_, i) => <Skeleton key={i} height={48} style={{ marginBottom: 8 }}/>)}</div> : rows.length === 0 ? <EmptyState title="No runtime templates match" description="Change the filters or create an in-app template." icon={<FileText size={34}/>}/> : <div style={{ overflowX: "auto" }}><TableSurface className="nc-table"><thead><tr><th>Template</th><th>Channel</th><th>Status</th><th>Action target</th><th>Created</th><th></th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><div className="nc-notif-title">{row.template_name}</div><code style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{row.template_key}</code></td><td><Badge variant="muted">{row.channel.replace("_", "-")}</Badge></td><td><Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge></td><td>{row.action_label_template ? <>{row.action_label_template}<div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{row.action_url_template}</div></> : "No action"}</td><td>{new Date(row.created_at).toLocaleDateString()}</td><td><div style={{ display: "flex", gap: 5 }}><Btn size="xs" variant="secondary" onClick={() => edit(row)}><Edit3 size={12}/> Edit</Btn><Btn size="xs" variant="ghost" onClick={() => changeState(row)}><Power size={12}/> {row.is_active ? "Disable" : "Enable"}</Btn></div></td></tr>)}</tbody></TableSurface></div>}
      <Pagination page={page} total={filtered.length} pageSize={PAGE_SIZE} onPage={setPage}/>
    </Card>
    <div className="nc-callout"><CheckCircle2 size={17}/><div><strong>One source of delivery copy</strong><p>The retired empty template workspace is no longer shown here. This table is backed by notif_event_templates, the same table used by the canonical event and outbox engine.</p></div></div>
    {editing && <Modal open onClose={() => setEditing(null)} title={editing === "new" ? "New runtime template" : "Edit runtime template"} size="lg"><div className="nc-stack"><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}><Input label="Template key" value={form.template_key} onChange={v => setForm(f => ({ ...f, template_key: v }))} disabled={editing !== "new"} hint="Use event.key.in_app"/><Input label="Display name" value={form.template_name} onChange={v => setForm(f => ({ ...f, template_name: v }))}/><Select label="Channel" value={form.channel} onChange={v => setForm(f => ({ ...f, channel: v }))} disabled options={[{ value: "in_app", label: "In-app · connected" }]}/><Input label="Subject / title" value={form.subject_template} onChange={v => setForm(f => ({ ...f, subject_template: v }))} hint="Supports {{variable}} placeholders"/></div><Textarea label="Message body" value={form.body_template} onChange={v => setForm(f => ({ ...f, body_template: v }))} rows={5} required/><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}><Input label="Action label" value={form.action_label_template} onChange={v => setForm(f => ({ ...f, action_label_template: v }))}/><Input label="Action URL" value={form.action_url_template} onChange={v => setForm(f => ({ ...f, action_url_template: v }))} hint="Internal app route only"/></div>{(createAction.error || updateAction.error) && <div className="nc-message danger">{createAction.error || updateAction.error}</div>}<div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><Btn variant="ghost" onClick={() => setEditing(null)}>Cancel</Btn><Btn onClick={save} loading={createAction.loading || updateAction.loading} disabled={!form.template_key.trim() || !form.template_name.trim() || !form.body_template.trim()}>Save template</Btn></div></div></Modal>}
  </div>;
}
