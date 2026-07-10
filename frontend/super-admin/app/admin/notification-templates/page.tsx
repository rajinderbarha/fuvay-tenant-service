"use client";
import { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Btn, Modal, SectionHeader } from "../../../components/shared/ui";
import { sprint27AdminApi, type NotifEventTemplate } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const CHANNELS = ["in_app", "email", "sms", "whatsapp", "push"];

const th: React.CSSProperties = {
  padding: "10px 16px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

const inputStyle: React.CSSProperties = {
  width: "100%", height: 36, padding: "0 12px", fontSize: 13, borderRadius: 8,
  border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)",
  fontFamily: "inherit", boxSizing: "border-box",
};

const selStyle: React.CSSProperties = {
  width: "100%", height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 8,
  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit", boxSizing: "border-box",
};

const labelStyle: React.CSSProperties = { fontSize: 11, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 4 };

export default function NotificationTemplatesPage() {
  const [channelFilter, setChannelFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editItem, setEditItem] = useState<NotifEventTemplate | null>(null);
  const [form, setForm] = useState({
    template_key: "", template_name: "", channel: "in_app",
    subject_template: "", body_template: "",
    action_label_template: "", action_url_template: "", is_active: true,
  });

  const templates = useApi(
    useCallback(() => sprint27AdminApi.listTemplates(channelFilter || undefined), [channelFilter])
  );

  const createAction = useAction(
    useCallback((data: Partial<NotifEventTemplate>) => sprint27AdminApi.createTemplate(data), [])
  );
  const updateAction = useAction(
    useCallback((id: string, data: Partial<NotifEventTemplate>) => sprint27AdminApi.updateTemplate(id, data), [])
  );
  const toggleAction = useAction(
    useCallback((id: string, active: boolean) =>
      active ? sprint27AdminApi.activateTemplate(id) : sprint27AdminApi.deactivateTemplate(id), [])
  );

  const items: NotifEventTemplate[] = templates.data?.items ?? [];

  function openEdit(t: NotifEventTemplate) {
    setEditItem(t);
    setForm({
      template_key: t.template_key, template_name: t.template_name,
      channel: t.channel, subject_template: t.subject_template ?? "",
      body_template: t.body_template,
      action_label_template: t.action_label_template ?? "",
      action_url_template: t.action_url_template ?? "",
      is_active: t.is_active,
    });
  }

  const FormFields = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div>
        <label style={labelStyle}>Template Key *</label>
        <input style={{ ...inputStyle, fontFamily: "'JetBrains Mono', monospace" }}
          value={form.template_key}
          onChange={e => setForm(f => ({ ...f, template_key: e.target.value }))}
          placeholder="booking.confirmed.in_app" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label style={labelStyle}>Template Name *</label>
          <input style={inputStyle}
            value={form.template_name}
            onChange={e => setForm(f => ({ ...f, template_name: e.target.value }))} />
        </div>
        <div>
          <label style={labelStyle}>Channel *</label>
          <select style={selStyle}
            value={form.channel}
            onChange={e => setForm(f => ({ ...f, channel: e.target.value }))}>
            {CHANNELS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>
      <div>
        <label style={labelStyle}>Subject Template</label>
        <input style={inputStyle}
          value={form.subject_template}
          onChange={e => setForm(f => ({ ...f, subject_template: e.target.value }))}
          placeholder="Use {{variable}} for interpolation" />
      </div>
      <div>
        <label style={labelStyle}>Body Template *</label>
        <textarea style={{ ...inputStyle, height: "auto", padding: "8px 12px", resize: "vertical" }} rows={4}
          value={form.body_template}
          onChange={e => setForm(f => ({ ...f, body_template: e.target.value }))}
          placeholder="Your booking {{booking_number}} is confirmed." />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label style={labelStyle}>Action Label</label>
          <input style={inputStyle}
            value={form.action_label_template}
            onChange={e => setForm(f => ({ ...f, action_label_template: e.target.value }))} />
        </div>
        <div>
          <label style={labelStyle}>Action URL</label>
          <input style={inputStyle}
            value={form.action_url_template}
            onChange={e => setForm(f => ({ ...f, action_url_template: e.target.value }))}
            placeholder="/bookings/{{booking_id}}" />
        </div>
      </div>
    </div>
  );

  return (
    <AdminLayout>
      <SectionHeader title="Notification Templates" subtitle="Event-driven notification templates" />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <select style={{ height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 8,
          background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit" }}
          value={channelFilter}
          onChange={e => setChannelFilter(e.target.value)}>
          <option value="">All Channels</option>
          {CHANNELS.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <Btn onClick={() => { setShowCreate(true); setForm({ template_key:"", template_name:"", channel:"in_app", subject_template:"", body_template:"", action_label_template:"", action_url_template:"", is_active:true }); }}>
          + New Template
        </Btn>
      </div>

      <Card>
        {templates.loading ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  {["Template Key", "Name", "Channel", "Status", "Actions"].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map(t => (
                  <tr key={t.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-primary)" }}>
                      {t.template_key}
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--text-primary)" }}>{t.template_name}</td>
                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{t.channel}</td>
                    <td style={{ padding: "10px 16px" }}>
                      <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                        background: t.is_active ? "var(--success-bg)" : "var(--surface-sunken)",
                        color: t.is_active ? "var(--success-text)" : "var(--text-tertiary)" }}>
                        {t.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", display: "flex", gap: 8 }}>
                      <Btn size="xs" variant="ghost" onClick={() => openEdit(t)}>Edit</Btn>
                      <Btn size="xs" variant={t.is_active ? "danger" : "ghost"}
                        onClick={() => toggleAction.execute(t.id, !t.is_active).then(() => templates.refetch())}
                        loading={toggleAction.loading}>
                        {t.is_active ? "Deactivate" : "Activate"}
                      </Btn>
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                      No templates found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {showCreate && (
        <Modal open={showCreate} title="Create Notification Template" onClose={() => setShowCreate(false)}>
          <FormFields />
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <Btn onClick={() => createAction.execute(form).then(() => { setShowCreate(false); templates.refetch(); })} loading={createAction.loading}>Create</Btn>
            <Btn variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Btn>
          </div>
        </Modal>
      )}

      {editItem && (
        <Modal open={!!editItem} title="Edit Template" onClose={() => setEditItem(null)}>
          <FormFields />
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <Btn onClick={() => updateAction.execute(editItem.id, form).then(() => { setEditItem(null); templates.refetch(); })} loading={updateAction.loading}>Save</Btn>
            <Btn variant="ghost" onClick={() => setEditItem(null)}>Cancel</Btn>
          </div>
        </Modal>
      )}
    </AdminLayout>
  );
}
