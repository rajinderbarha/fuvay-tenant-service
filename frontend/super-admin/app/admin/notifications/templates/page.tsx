"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader, Skeleton, EmptyState, SummaryCard,} from "../../../../components/shared/ui";
import { notifTemplateAdminApi } from "../../../../lib/api";
import type { AdminNotifTemplate } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  Plus, RefreshCw, Sparkles, Send, History, ShieldAlert, Copy, Ban,
} from "lucide-react";

const EVENT_TYPES = [
  "booking_confirmed", "booking_cancelled", "booking_rescheduled", "provider_assigned",
  "job_assigned", "job_status_changed", "payment_recorded", "review_requested",
  "complaint_created", "dispute_created", "customer_service_credit_issued", "tenant_approved",
  "tenant_changes_requested", "staff_invited", "package_expiring", "usage_credit_low",
  "security_deposit_required", "document_expiring", "login_otp", "password_reset",
  "marketing_post_scheduled",
];
const CHANNELS = ["in_app", "email", "sms", "whatsapp", "push"];
const AUDIENCES = ["admin", "tenant_owner", "tenant_staff", "technician", "customer", "support_admin", "finance_admin"];
const APP_SCOPES = ["admin_app", "tenant_app", "staff_app", "customer_app", "system"];
const STATUS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  active: "success", draft: "warning", inactive: "muted", deprecated: "muted",
  validation_failed: "danger", archived: "muted",
};

type Tab = "all" | "platform" | "vertical" | "tenant" | "drafts" | "audit";

export function NotificationTemplatesContent() {
  const [tab, setTab] = useState<Tab>("all");
  const [eventFilter, setEventFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<AdminNotifTemplate | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [seedOpen, setSeedOpen] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  const scopeTypeForTab: Record<Tab, string | undefined> = {
    all: undefined, platform: "platform_default", vertical: "vertical", tenant: "tenant",
    drafts: undefined, audit: undefined,
  };

  const summary = useApi(useCallback(() => notifTemplateAdminApi.getSummary(), []));
  const templates = useApi(useCallback(() => notifTemplateAdminApi.listTemplates({
    event_type: eventFilter || undefined, channel: channelFilter || undefined,
    scope_type: scopeTypeForTab[tab], status: tab === "drafts" ? "draft" : undefined,
    search: search || undefined,
  }), [eventFilter, channelFilter, tab, search]));
  const auditLogs = useApi(useCallback(() => notifTemplateAdminApi.listAuditLogs(), []));

  const seedAction = useAction(useCallback(() => notifTemplateAdminApi.seedDefaults(), []));
  const activateAction = useAction(useCallback((id: string) => notifTemplateAdminApi.activate(id), []));
  const deactivateAction = useAction(useCallback((id: string) => notifTemplateAdminApi.deactivate(id), []));
  const archiveAction = useAction(useCallback((id: string) => notifTemplateAdminApi.archive(id), []));
  const cloneAction = useAction(useCallback((id: string) => notifTemplateAdminApi.clone(id), []));
  const deleteAction = useAction(useCallback((id: string) => notifTemplateAdminApi.deleteTemplate(id), []));

  async function handleSeed() {
    const res = await seedAction.execute();
    if (res) { templates.refetch(); summary.refetch(); setSeedOpen(false); notify(`Seeded ${res.created} templates.`); }
  }
  async function handleClone(id: string) {
    const res = await cloneAction.execute(id);
    if (res) { templates.refetch(); summary.refetch(); notify("Cloned as draft."); }
  }
  async function handleActivate(id: string) {
    const res = await activateAction.execute(id);
    if (res) { templates.refetch(); summary.refetch(); notify("Template activated."); }
  }
  async function handleDeactivate(id: string) {
    const res = await deactivateAction.execute(id);
    if (res) { templates.refetch(); summary.refetch(); notify("Template deactivated."); }
  }
  async function handleArchive(id: string) {
    const res = await archiveAction.execute(id);
    if (res) { templates.refetch(); summary.refetch(); notify("Template archived."); }
  }
  async function handleDelete(id: string) {
    const res = await deleteAction.execute(id);
    if (res) { templates.refetch(); summary.refetch(); notify("Draft deleted."); }
    else if (deleteAction.error) notify(deleteAction.error, false);
  }

  const s = summary.data;
  const items = templates.data?.items ?? [];

  const columns = [
    {
      key: "template", label: "Template",
      render: (_: unknown, row: AdminNotifTemplate) => (
        <div>
          <p style={{ margin: 0, fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{row.name}</p>
          <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{row.template_key}</p>
        </div>
      ),
    },
    { key: "event_type", label: "Event", render: (_: unknown, row: AdminNotifTemplate) =>
      <span style={{ fontSize: 12 }}>{row.event_type}</span> },
    { key: "channel", label: "Channel", render: (_: unknown, row: AdminNotifTemplate) =>
      <Badge variant="muted">{row.channel}</Badge> },
    { key: "audience", label: "Audience", render: (_: unknown, row: AdminNotifTemplate) =>
      <span style={{ fontSize: 12 }}>{row.audience.replace(/_/g, " ")}</span> },
    { key: "scope_type", label: "Source", render: (_: unknown, row: AdminNotifTemplate) => (
      <Badge variant={row.is_platform_default ? "success" : row.tenant_id ? "warning" : "muted"}>
        {row.is_platform_default ? "Platform Default" : row.tenant_id ? "Tenant Override" : row.vertical_key ? "Vertical Override" : "Custom"}
      </Badge>
    ) },
    { key: "status", label: "Status", render: (_: unknown, row: AdminNotifTemplate) =>
      <Badge variant={STATUS_VARIANT[row.status] ?? "muted"}>{row.status}</Badge> },
    { key: "updated_at", label: "Updated", render: (_: unknown, row: AdminNotifTemplate) =>
      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{new Date(row.updated_at).toLocaleDateString()}</span> },
    {
      key: "actions", label: "Actions",
      render: (_: unknown, row: AdminNotifTemplate) => (
        <div style={{ display: "flex", gap: 4 }} onClick={e => e.stopPropagation()}>
          <Btn size="xs" variant="secondary" onClick={() => setSelected(row)}>View</Btn>
          <Btn size="xs" variant="secondary" onClick={() => handleClone(row.template_id)}><Copy size={12}/></Btn>
          {row.status === "active"
            ? <Btn size="xs" variant="secondary" onClick={() => handleDeactivate(row.template_id)}>Deactivate</Btn>
            : <Btn size="xs" variant="primary" onClick={() => handleActivate(row.template_id)}>Activate</Btn>}
          {!row.is_platform_default && row.status !== "active" && (
            <Btn size="xs" variant="danger" onClick={() => handleDelete(row.template_id)}>Delete</Btn>
          )}
          {row.status !== "archived" && (
            <Btn size="xs" variant="secondary" onClick={() => handleArchive(row.template_id)}><Ban size={12}/></Btn>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <SectionHeader
        title="Notification Templates"
        subtitle="Manage platform, vertical, tenant, and channel-specific notification templates."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" onClick={() => setSeedOpen(true)}><Sparkles size={14} style={{ marginRight: 4 }}/> Seed Defaults</Btn>
            <Btn size="sm" onClick={() => setCreateOpen(true)}><Plus size={14} style={{ marginRight: 4 }}/> New Template</Btn>
            <Btn variant="ghost" size="sm" onClick={() => { templates.refetch(); summary.refetch(); }}><RefreshCw size={14}/></Btn>
          </div>
        }
      />

      {toast && (
        <div style={{ padding: "10px 16px", marginBottom: 16, borderRadius: 10,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13 }}>
          {toast.msg}
        </div>
      )}

      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 20 }}>
        {summary.loading ? [...Array(4)].map((_, i) => <Skeleton key={i} height={90} style={{ borderRadius:"var(--radius-lg)" }}/>) : <>
          <SummaryCard label="Total Templates" value={s?.total_templates ?? 0}/>
          <SummaryCard label="Active" value={s?.active_templates ?? 0} accent/>
          <SummaryCard label="Drafts" value={s?.draft_templates ?? 0}/>
          <SummaryCard label="Platform Defaults" value={s?.platform_defaults ?? 0}/>
        </>}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 20 }}>
        {summary.loading ? [...Array(4)].map((_, i) => <Skeleton key={i} height={90} style={{ borderRadius:"var(--radius-lg)" }}/>) : <>
          <SummaryCard label="Tenant Overrides" value={s?.tenant_overrides ?? 0}/>
          <SummaryCard label="Validation Errors" value={s?.validation_errors ?? 0} tone={(!!s?.validation_errors) ? "danger" : undefined}/>
          <SummaryCard label="Failed Deliveries" value={s?.failed_deliveries ?? 0} tone={(!!s?.failed_deliveries) ? "danger" : undefined}/>
          <SummaryCard label="Missing Translations" value={s?.missing_translations ?? 0}/>
        </>}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 2, borderBottom: "2px solid var(--border)", marginBottom: 16 }}>
        {([
          { id: "all", label: "All Templates" }, { id: "platform", label: "Platform Defaults" },
          { id: "vertical", label: "Vertical Templates" }, { id: "tenant", label: "Tenant Overrides" },
          { id: "drafts", label: "Drafts" }, { id: "audit", label: "Audit Logs" },
        ] as { id: Tab; label: string }[]).map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding: "10px 16px", border: "none", background: "none", cursor: "pointer",
            fontSize: 13, fontWeight: tab === t.id ? 700 : 500,
            color: tab === t.id ? "var(--brand)" : "var(--text-secondary)",
            borderBottom: tab === t.id ? "2px solid var(--brand)" : "2px solid transparent", marginBottom: -2,
          }}>{t.label}</button>
        ))}
      </div>

      {tab === "audit" ? (
        <Card padding={0}>
          {auditLogs.loading ? <div style={{ padding: 20 }}><Skeleton height={200}/></div> : (auditLogs.data?.items ?? []).length === 0 ? (
            <EmptyState title="No audit events yet" description="Template changes will appear here."/>
          ) : (auditLogs.data?.items ?? []).map((a, i, arr) => (
            <div key={a.id} style={{ padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{a.action_type}</p>
              {a.reason && <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>{a.reason}</p>}
              <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{new Date(a.created_at).toLocaleString()}</p>
            </div>
          ))}
        </Card>
      ) : (
        <>
          {/* Toolbar */}
          <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 220px" }}>
              <Input placeholder="Search by key, title, body, event…" value={search} onChange={setSearch}/>
            </div>
            <Select value={eventFilter} onChange={setEventFilter} placeholder="Event Type"
              options={[{ value: "", label: "All Events" }, ...EVENT_TYPES.map(e => ({ value: e, label: e }))]}/>
            <Select value={channelFilter} onChange={setChannelFilter} placeholder="Channel"
              options={[{ value: "", label: "All Channels" }, ...CHANNELS.map(c => ({ value: c, label: c }))]}/>
          </div>

          {templates.loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[...Array(5)].map((_, i) => <Skeleton key={i} height={48}/>)}
            </div>
          ) : items.length === 0 ? (
            <EmptyState title="No templates found"
              description="Seed platform defaults to get started, or create a new template."
              action={<Btn size="sm" onClick={() => setSeedOpen(true)}>Seed Default Templates</Btn>}/>
          ) : (
            <DataTable
              columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
              rows={items as unknown as Record<string, unknown>[]}
              onRowClick={(row) => setSelected(row as unknown as AdminNotifTemplate)}
            />
          )}
        </>
      )}

      {/* Seed defaults confirm */}
      <Modal open={seedOpen} onClose={() => setSeedOpen(false)} title="Seed Default Templates" size="sm">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Seeds 20 platform-default event templates across in-app, email, and push channels.
            Running this again will not create duplicates.
          </p>
          {seedAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{seedAction.error}</p>}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setSeedOpen(false)}>Cancel</Btn>
            <Btn size="sm" loading={seedAction.loading} onClick={handleSeed}>Seed Defaults</Btn>
          </div>
        </div>
      </Modal>

      {createOpen && (
        <CreateTemplateWizard
          onClose={() => setCreateOpen(false)}
          onCreated={() => { setCreateOpen(false); templates.refetch(); summary.refetch(); notify("Template created as draft."); }}
        />
      )}

      {selected && (
        <TemplateDetailDrawer
          template={selected}
          onClose={() => setSelected(null)}
          onChanged={() => { templates.refetch(); summary.refetch(); }}
          notify={notify}
        />
      )}
    </>
  );
}

// Standalone route -- deep links (/admin/notifications/templates) still work.
export default function NotificationTemplatesPage() {
  return (
    <AdminLayout activeNav="notifications">
      <NotificationTemplatesContent />
    </AdminLayout>
  );
}


function AnalyticsStat({ label, value, danger }: { label: string; value: number | string; danger?: boolean }) {
  return (
    <div style={{ padding: "12px 16px", background: "var(--surface-sunken)", borderRadius: 10 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: danger ? "var(--danger-text)" : "var(--text-primary)" }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{label}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CREATE TEMPLATE WIZARD (multi-step)
// ─────────────────────────────────────────────────────────────────────────────
type WizardStep = "basic" | "scope" | "content" | "review";

function CreateTemplateWizard({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [step, setStep] = useState<WizardStep>("basic");
  const [eventType, setEventType] = useState(EVENT_TYPES[0]);
  const [channel, setChannel] = useState(CHANNELS[0]);
  const [audience, setAudience] = useState(AUDIENCES[0]);
  const [appScope, setAppScope] = useState(APP_SCOPES[0]);
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  const createAction = useAction(useCallback(() => notifTemplateAdminApi.createTemplate({
    event_type: eventType, channel, audience, app_scope: appScope,
    title, subject: channel === "email" ? subject : undefined, body,
  }), [eventType, channel, audience, appScope, title, subject, body]));

  const steps: { key: WizardStep; label: string }[] = [
    { key: "basic", label: "1. Basic Details" }, { key: "scope", label: "2. Audience & Scope" },
    { key: "content", label: "3. Channel Content" }, { key: "review", label: "4. Review & Publish" },
  ];

  async function handleSubmit() {
    const res = await createAction.execute();
    if (res) onCreated();
  }

  return (
    <Modal open onClose={onClose} title="New Notification Template" size="lg">
      <div style={{ minWidth: 640, display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", gap: 4 }}>
          {steps.map(s => (
            <button key={s.key} onClick={() => setStep(s.key)} style={{
              flex: 1, padding: "8px 4px", fontSize: 11, fontWeight: step === s.key ? 700 : 500,
              border: "none", borderBottom: step === s.key ? "2px solid var(--brand)" : "2px solid var(--border)",
              background: "none", color: step === s.key ? "var(--brand)" : "var(--text-tertiary)", cursor: "pointer",
            }}>{s.label}</button>
          ))}
        </div>

        {step === "basic" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Select label="Event Type *" value={eventType} onChange={setEventType}
              options={EVENT_TYPES.map(e => ({ value: e, label: e }))}/>
            <Input label="Template Name *" placeholder="e.g. Booking Confirmed" value={title} onChange={setTitle}/>
          </div>
        )}
        {step === "scope" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Select label="Audience *" value={audience} onChange={setAudience}
              options={AUDIENCES.map(a => ({ value: a, label: a.replace(/_/g, " ") }))}/>
            <Select label="App Scope *" value={appScope} onChange={setAppScope}
              options={APP_SCOPES.map(a => ({ value: a, label: a.replace(/_/g, " ") }))}/>
            <Select label="Channel *" value={channel} onChange={setChannel}
              options={CHANNELS.map(c => ({ value: c, label: c }))}/>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
              New templates without a tenant/vertical are created as platform defaults. Use "Create Override" on an
              existing template to scope to a specific tenant or vertical instead.
            </p>
          </div>
        )}
        {step === "content" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {channel === "email" && <Input label="Subject *" value={subject} onChange={setSubject}/>}
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                Body * <span style={{ fontWeight: 400, color: "var(--text-tertiary)" }}>(use {"{{variable}}"})</span>
              </label>
              <textarea value={body} onChange={e => setBody(e.target.value)} rows={5}
                placeholder="Hi {{customer_name}}, ..."
                style={{ width: "100%", padding: "10px 12px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
                  background: "var(--surface)", color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit", boxSizing: "border-box" }}/>
            </div>
          </div>
        )}
        {step === "review" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
            <p><strong>Event:</strong> {eventType}</p>
            <p><strong>Audience:</strong> {audience} · <strong>Channel:</strong> {channel} · <strong>Scope:</strong> {appScope}</p>
            <p><strong>Title:</strong> {title || "—"}</p>
            <p><strong>Body:</strong> {body || "—"}</p>
            {createAction.error && <p style={{ color: "var(--danger-text)" }}>{createAction.error}</p>}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, justifyContent: "space-between", borderTop: "1px solid var(--border)", paddingTop: 16 }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <div style={{ display: "flex", gap: 8 }}>
            {step !== "basic" && (
              <Btn variant="secondary" size="sm" onClick={() => setStep(steps[steps.findIndex(s => s.key === step) - 1].key)}>Back</Btn>
            )}
            {step !== "review" ? (
              <Btn size="sm" onClick={() => setStep(steps[steps.findIndex(s => s.key === step) + 1].key)}>Next</Btn>
            ) : (
              <Btn size="sm" loading={createAction.loading} disabled={!body.trim()} onClick={handleSubmit}>Create as Draft</Btn>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TEMPLATE DETAIL DRAWER — Preview / Test Send / Versions
// ─────────────────────────────────────────────────────────────────────────────
function TemplateDetailDrawer({ template, onClose, onChanged, notify }: {
  template: AdminNotifTemplate; onClose: () => void; onChanged: () => void;
  notify: (msg: string, ok?: boolean) => void;
}) {
  const [tab, setTab] = useState<"overview" | "preview" | "versions" | "analytics">("overview");
  const [sampleJson, setSampleJson] = useState('{"customer_name": "Test User"}');
  const [recipient, setRecipient] = useState("qa@example.com");
  const [preview, setPreview] = useState<{ rendered_title: string; rendered_body: string; missing_variables: string[] } | null>(null);
  const [previewError, setPreviewError] = useState("");

  const versions = useApi(useCallback(() => notifTemplateAdminApi.listVersions(template.template_id), [template.template_id]));
  const analytics = useApi(useCallback(() => notifTemplateAdminApi.deliveryAnalytics(template.template_id), [template.template_id]));
  const previewAction = useAction(useCallback((data: Record<string, string>) =>
    notifTemplateAdminApi.renderPreview(template.template_id, data), [template.template_id]));
  const testSendAction = useAction(useCallback((data: Record<string, string>) =>
    notifTemplateAdminApi.testSend(template.template_id, recipient, data), [template.template_id, recipient]));

  async function handlePreview() {
    setPreviewError("");
    try {
      const data = JSON.parse(sampleJson);
      const res = await previewAction.execute(data);
      if (res) setPreview(res);
    } catch {
      setPreviewError("Sample payload must be valid JSON.");
    }
  }
  async function handleTestSend() {
    try {
      const data = JSON.parse(sampleJson);
      const res = await testSendAction.execute(data);
      if (res) notify("Test notification sent (marked as test, not a real trigger).");
    } catch {
      setPreviewError("Sample payload must be valid JSON.");
    }
  }

  return (
    <Modal open onClose={onClose} title={template.name} size="lg">
      <div style={{ minWidth: 640, display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Badge variant="muted">{template.event_type}</Badge>
          <Badge variant="muted">{template.channel}</Badge>
          <Badge variant={STATUS_VARIANT[template.status] ?? "muted"}>{template.status}</Badge>
          {template.is_platform_default && <Badge variant="success">Platform Default</Badge>}
        </div>

        <div style={{ display: "flex", gap: 2, borderBottom: "2px solid var(--border)" }}>
          {(["overview", "preview", "versions", "analytics"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "8px 14px", border: "none", background: "none", cursor: "pointer",
              fontSize: 12, fontWeight: tab === t ? 700 : 500,
              color: tab === t ? "var(--brand)" : "var(--text-secondary)",
              borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent", marginBottom: -2,
              textTransform: "capitalize",
            }}>{t}</button>
          ))}
        </div>

        {tab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
            <p><strong>Template Key:</strong> <code>{template.template_key}</code></p>
            <p><strong>Audience:</strong> {template.audience} · <strong>App Scope:</strong> {template.app_scope}</p>
            <p><strong>Language:</strong> {template.language} · <strong>Priority:</strong> {template.priority}</p>
            {template.subject && <p><strong>Subject:</strong> {template.subject}</p>}
            <p><strong>Body:</strong></p>
            <p style={{ padding: 12, background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", whiteSpace: "pre-wrap" }}>{template.body}</p>
            <p><strong>Variables:</strong> {template.variables.map(v => `{{${v}}}`).join(", ") || "—"}</p>
          </div>
        )}

        {tab === "preview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                Sample Event Payload (JSON)
              </label>
              <textarea value={sampleJson} onChange={e => setSampleJson(e.target.value)} rows={3}
                style={{ width: "100%", padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
                  background: "var(--surface)", color: "var(--text-primary)", fontSize: 12, fontFamily: "monospace", boxSizing: "border-box" }}/>
            </div>
            <Input label="Test Recipient" value={recipient} onChange={setRecipient}/>
            {previewError && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{previewError}</p>}
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="secondary" size="sm" loading={previewAction.loading} onClick={handlePreview}>Generate Preview</Btn>
              <Btn size="sm" icon={<Send size={14}/>} loading={testSendAction.loading} onClick={handleTestSend}>Send Test</Btn>
            </div>
            {preview && (
              <div style={{ padding: 14, background: "var(--surface-sunken)", borderRadius: 10 }}>
                {preview.rendered_title && <p style={{ fontWeight: 700, margin: "0 0 6px" }}>{preview.rendered_title}</p>}
                <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{preview.rendered_body}</p>
                {preview.missing_variables.length > 0 && (
                  <p style={{ marginTop: 8, fontSize: 12, color: "var(--warning-text)" }}>
                    <ShieldAlert size={12} style={{ marginRight: 4 }}/>
                    Missing sample values for: {preview.missing_variables.join(", ")}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {tab === "versions" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {versions.loading ? <Skeleton height={120}/> : (versions.data?.items ?? []).length === 0 ? (
              <EmptyState title="No version history yet" description="Versions are created every time this template is updated."/>
            ) : (versions.data?.items ?? []).map(v => (
              <div key={v.id} style={{ padding: 10, border: "1px solid var(--border)", borderRadius:"var(--radius-md)", display: "flex", justifyContent: "space-between" }}>
                <div>
                  <p style={{ margin: 0, fontSize: 12, fontWeight: 600 }}><History size={12} style={{ marginRight: 4 }}/> v{v.version_number}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{v.change_reason || "—"}</p>
                </div>
                <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{new Date(v.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}

        {tab === "analytics" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {analytics.loading ? <Skeleton height={140}/> : !analytics.data || analytics.data.sent === 0 ? (
              <EmptyState title="No deliveries yet"
                description="Delivery analytics appear here once this template has been used to send real notifications."/>
            ) : (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
                  <AnalyticsStat label="Sent" value={analytics.data.sent}/>
                  <AnalyticsStat label="Delivered" value={analytics.data.delivered}/>
                  <AnalyticsStat label="Failed" value={analytics.data.failed} danger={analytics.data.failed > 0}/>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }}>
                  <AnalyticsStat label="Delivery Rate" value={`${analytics.data.delivery_rate}%`}/>
                  <AnalyticsStat label="Failure Rate" value={`${analytics.data.failure_rate}%`} danger={analytics.data.failure_rate > 0}/>
                </div>
                {analytics.data.last_failure_reason && (
                  <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>
                    <ShieldAlert size={12} style={{ marginRight: 4 }}/>
                    Last failure: {analytics.data.last_failure_reason}
                  </p>
                )}
              </>
            )}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", borderTop: "1px solid var(--border)", paddingTop: 12 }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Close</Btn>
        </div>
      </div>
    </Modal>
  );
}
