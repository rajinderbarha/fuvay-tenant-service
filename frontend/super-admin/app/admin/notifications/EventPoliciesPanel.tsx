"use client";
import React, { useCallback, useState } from "react";
import {
  Card, Badge, Btn, Select, Input,
} from "../../../components/shared/ui";
import {
  notificationPolicyApi,
  type NotificationPolicyListItem, type NotificationPolicy, type NotificationPolicyDetail,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { ShieldCheck, Lock, FileText, Sparkles, AlertTriangle, CheckCircle2 } from "lucide-react";

const VERTICAL_LABEL: Record<string, string> = {
  home_services: "Home Services", coaching: "Coaching / IELTS",
  real_estate: "Real Estate", restaurant: "Restaurant / Food",
};
const ALL_CHANNELS = ["in_app", "email", "sms", "whatsapp", "push"];
const RECIPIENT_ROLES = [
  "customer", "provider", "assigned_staff", "technician",
  "operations_admin", "finance_admin", "security_admin", "escalation",
];

type DraftForm = Omit<Partial<NotificationPolicy>, "recipient_rules"> & {
  recipient_rules?: { recipient_role: string; is_required: boolean }[];
};

export function EventPoliciesPanel() {
  const [verticalFilter, setVerticalFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selectedKey, setSelectedKey] = useState<{ event_key: string; vertical_key: string | null } | null>(null);
  const [tab, setTab] = useState<"table" | "history" | "audit">("table");

  const listApi = useApi(useCallback(() => notificationPolicyApi.list({
    vertical_key: verticalFilter || undefined, channel: channelFilter || undefined,
    status: statusFilter || undefined, search: search || undefined,
  }), [verticalFilter, channelFilter, statusFilter, search]));

  const rows = listApi.data?.items ?? [];
  const summary = listApi.data?.summary;
  const selectedRow = rows.find(r => r.event_key === selectedKey?.event_key && r.vertical_key === selectedKey?.vertical_key)
    ?? rows[0] ?? null;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 16px", borderRadius: "var(--radius-lg)",
        background: "var(--info-bg, rgba(59,130,246,0.08))", border: "1px solid var(--info-border, rgba(59,130,246,0.3))", marginBottom: 16 }}>
        <AlertTriangle size={16} style={{ color: "var(--brand)", flexShrink: 0, marginTop: 1 }}/>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Policies are isolated by vertical. Disabling a vertical hides new notifications for that vertical only
          and preserves delivery history and unresolved alerts. Mandatory events cannot have their in-app copy disabled.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(110px, 1fr))", gap: 10, marginBottom: 18 }}>
        <Metric icon={<ShieldCheck size={16}/>} value={summary?.delivery_engine_active ? "Active" : "Down"} label="Delivery Engine"/>
        <Metric icon={<FileText size={16}/>} value={summary?.registered_events} label="Registered Events"/>
        <Metric icon={<CheckCircle2 size={16}/>} value={summary?.active_policies} label="Active Policies"/>
        <Metric icon={<AlertTriangle size={16}/>} value={summary?.need_review} label="Need Review"/>
        <Metric icon={<AlertTriangle size={16}/>} value={summary?.failed_deliveries} label="Failed Deliveries"/>
        <Metric icon={<CheckCircle2 size={16}/>}
          value={summary?.delivery_rate_pct !== null && summary?.delivery_rate_pct !== undefined ? `${summary.delivery_rate_pct}%` : "—"}
          label="Delivery Rate"/>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Card style={{ padding: 0 }}>
            <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", gap: 8, flexWrap: "wrap" }}>
              <p style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)", flex: "1 1 160px" }}>Event policies</p>
              <div style={{ flex: "1 1 180px" }}>
                <Input placeholder="Search event…" value={search} onChange={setSearch}/>
              </div>
              <Select value={verticalFilter} onChange={setVerticalFilter} placeholder="Vertical" options={[
                { value: "", label: "All Verticals" },
                { value: "__global__", label: "Global" },
                ...Object.entries(VERTICAL_LABEL).map(([value, label]) => ({ value, label })),
              ]}/>
              <Select value={channelFilter} onChange={setChannelFilter} placeholder="Channel" options={[
                { value: "", label: "All Channels" },
                ...ALL_CHANNELS.map(c => ({ value: c, label: c })),
              ]}/>
              <Select value={statusFilter} onChange={setStatusFilter} placeholder="Status" options={[
                { value: "", label: "All Statuses" },
                { value: "active", label: "Active" },
                { value: "draft", label: "Draft" },
                { value: "needs_review", label: "Needs Review" },
              ]}/>
            </div>

            {listApi.loading ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading policies…</div>
            ) : rows.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No events match this filter.</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                      {["Event", "Vertical", "Severity", "Channels", "Status", "Version", ""].map(h => (
                        <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(row => (
                      <tr key={`${row.event_key}::${row.vertical_key}`}
                        onClick={() => setSelectedKey({ event_key: row.event_key, vertical_key: row.vertical_key })}
                        style={{ borderBottom: "1px solid var(--border)", cursor: "pointer",
                          background: (selectedRow?.event_key === row.event_key && selectedRow?.vertical_key === row.vertical_key) ? "var(--surface-sunken)" : "transparent",
                          borderLeft: (selectedRow?.event_key === row.event_key && selectedRow?.vertical_key === row.vertical_key) ? "3px solid var(--brand)" : "3px solid transparent" }}>
                        <td style={{ padding: "10px 14px" }}>
                          <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 5 }}>
                            {row.event_name}
                            {row.is_mandatory && <Lock size={11} style={{ color: "var(--warning-text)" }}/>}
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{row.event_key}</div>
                        </td>
                        <td style={{ padding: "10px 14px" }}>{row.vertical_key ? (VERTICAL_LABEL[row.vertical_key] ?? row.vertical_key) : "Global"}</td>
                        <td style={{ padding: "10px 14px" }}><Badge variant={row.severity === "critical" ? "danger" : row.severity === "warning" ? "warning" : "muted"} size="sm">{row.severity}</Badge></td>
                        <td style={{ padding: "10px 14px" }}>{row.default_channels.join(", ")}</td>
                        <td style={{ padding: "10px 14px" }}>
                          <Badge variant={row.status === "Active" ? "success" : row.status === "Draft" ? "warning" : "muted"} size="sm">{row.status}</Badge>
                        </td>
                        <td style={{ padding: "10px 14px" }}>{row.version ? `v${row.version}` : "—"}</td>
                        <td style={{ padding: "10px 14px", textAlign: "right", color: "var(--text-tertiary)" }}>⋮</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div style={{ padding: "8px 14px", fontSize: 12, color: "var(--text-tertiary)" }}>Showing 1 to {rows.length} of {summary?.registered_events ?? rows.length} registered events</div>
          </Card>
        </div>

        {selectedRow && (
          <div style={{ width: 400, flexShrink: 0 }}>
            <PolicyInspector row={selectedRow} onChanged={() => listApi.refetch()}/>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ icon, value, label }: { icon: React.ReactNode; value: React.ReactNode; label: string }) {
  return (
    <div style={{ padding: "12px 14px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface)" }}>
      <div style={{ color: "var(--text-tertiary)", marginBottom: 6 }}>{icon}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>{value ?? "—"}</div>
      <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{label}</div>
    </div>
  );
}

function PolicyInspector({ row, onChanged }: { row: NotificationPolicyListItem; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [showPublish, setShowPublish] = useState(false);
  const [reason, setReason] = useState("");
  const [form, setForm] = useState<DraftForm>({});
  const [errors, setErrors] = useState<string[]>([]);

  const detailApi = useApi(useCallback(() => notificationPolicyApi.getDetail(row.event_key, row.vertical_key), [row.event_key, row.vertical_key]),
    [row.event_key, row.vertical_key]);
  const saveDraftAction = useAction((payload: DraftForm) => notificationPolicyApi.saveDraft(row.event_key, row.vertical_key, payload));
  const publishAction = useAction((r: string) => notificationPolicyApi.publish(row.event_key, row.vertical_key, r));

  const detail: NotificationPolicyDetail | undefined = detailApi.data;
  const current = detail?.current;
  const draft = detail?.draft;
  const active = draft ?? current;

  function startEdit() {
    setForm(active ?? {
      delivery_mode: "immediate", required_channels: row.default_channels, primary_channels: row.default_channels,
      fallback_channels: [], recipient_rules: [], retry_interval_seconds: 300, max_attempts: 3,
      dedup_window_seconds: 600, severity_override_bypasses_quiet_hours: true,
    });
    setEditing(true);
    setErrors([]);
  }

  async function validate() {
    const v = await notificationPolicyApi.validate(row.event_key, form);
    setErrors(v.errors);
  }

  async function saveDraft() {
    const result = await saveDraftAction.execute(form);
    if (result) { detailApi.refetch(); onChanged(); }
  }

  async function confirmPublish() {
    if (!reason.trim()) return;
    const result = await publishAction.execute(reason.trim());
    if (result) { setShowPublish(false); setReason(""); setEditing(false); detailApi.refetch(); onChanged(); }
  }

  return (
    <Card style={{ padding: 16, position: "sticky", top: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{row.event_name}</h2>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0", fontFamily: "monospace" }}>{row.event_key}</p>
        </div>
        <div style={{ display: "flex", gap: 4, flexDirection: "column", alignItems: "flex-end" }}>
          <Badge variant={current ? "success" : "muted"} size="sm">{current ? "Active" : "Needs review"}</Badge>
          {current && <Badge variant="muted" size="sm">v{current.version_number}</Badge>}
        </div>
      </div>

      {!editing ? (
        <>
          <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "14px 0 8px" }}>Policy identity</p>
          <SummaryRow label="Source engine" value={row.source_engine}/>
          <SummaryRow label="Vertical scope" value={row.vertical_key ? (VERTICAL_LABEL[row.vertical_key] ?? row.vertical_key) : "Global"}/>
          <SummaryRow label="Severity" value={row.severity}/>
          <SummaryRow label="Delivery mode" value={active?.delivery_mode ?? "—"}/>

          {active && (
            <>
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Recipients</p>
              {active.recipient_rules.length === 0 ? (
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No recipient rules configured yet.</p>
              ) : active.recipient_rules.map(r => (
                <div key={r.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                  <span style={{ color: "var(--text-secondary)" }}>{r.recipient_role.replace(/_/g, " ")}</span>
                  <Badge variant={r.is_required ? "warning" : "muted"} size="sm">{r.is_required ? "Required" : "Optional"}</Badge>
                </div>
              ))}

              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Channels and fallback</p>
              <SummaryRow label="Required" value={active.required_channels.join(", ") || "—"}/>
              <SummaryRow label="Primary" value={active.primary_channels.join(", ") || "—"}/>
              <SummaryRow label="Fallback" value={active.fallback_channels.join(", ") || "—"}/>
              <SummaryRow label="Escalation delay" value={active.escalation_delay_minutes ? `${active.escalation_delay_minutes}m` : "None"}/>
              <SummaryRow label="Consent required" value={active.consent_required ? "Yes" : "No"}/>

              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Delivery controls</p>
              <SummaryRow label="Retry" value={`Every ${active.retry_interval_seconds}s, max ${active.max_attempts}`}/>
              <SummaryRow label="Dedup window" value={`${active.dedup_window_seconds}s`}/>
              <SummaryRow label="Rate limit" value={active.rate_limit_per_hour ? `${active.rate_limit_per_hour}/hr` : "None"}/>
              <SummaryRow label="Quiet hours" value={active.quiet_hours_start ? `${active.quiet_hours_start}–${active.quiet_hours_end}` : "None"}/>
              <SummaryRow label="Expiry" value={active.expiry_minutes ? `${active.expiry_minutes}m` : "Never"}/>
            </>
          )}

          {detail?.safety && (
            <>
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "16px 0 8px" }}>Safety</p>
              {Object.entries(detail.safety).map(([k, v]) => (
                <div key={k} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>
                  <CheckCircle2 size={12} style={{ color: v ? "var(--success-text)" : "var(--danger-text)" }}/>
                  {k.replace(/_/g, " ")}
                </div>
              ))}
            </>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
            <Btn variant="primary" size="sm" onClick={startEdit}>{draft ? "Edit Draft" : "Create Draft"}</Btn>
          </div>
        </>
      ) : (
        <>
          <PolicyEditorForm form={form} setForm={setForm} mandatory={row.is_mandatory}/>
          {errors.length > 0 && (
            <div style={{ marginTop: 10, padding: "8px 10px", borderRadius: "var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              {errors.map(e => <p key={e} style={{ fontSize: 11, color: "var(--danger-text)", margin: "2px 0" }}>{e}</p>)}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            <Btn variant="ghost" size="sm" onClick={() => setEditing(false)}>Cancel</Btn>
            <Btn variant="secondary" size="sm" onClick={validate}>Validate</Btn>
            <Btn variant="secondary" size="sm" onClick={saveDraft} disabled={saveDraftAction.loading}>Save Draft</Btn>
            <Btn variant="primary" size="sm" onClick={() => setShowPublish(true)} disabled={errors.length > 0 || !draft}>Review &amp; Publish</Btn>
          </div>
        </>
      )}

      {showPublish && (
        <div role="dialog" aria-modal="true" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <Card style={{ padding: 20, width: 400 }}>
            <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
              <ShieldCheck size={16}/> Publish {row.event_name} policy
            </p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>
              This creates a new immutable policy version. In-flight notifications keep their snapshotted version.
            </p>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Reason (required)</label>
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, marginBottom: 14, boxSizing: "border-box" }}/>
            {publishAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "0 0 10px" }}>{publishAction.error}</p>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Btn variant="ghost" size="sm" onClick={() => setShowPublish(false)}>Cancel</Btn>
              <Btn variant="primary" size="sm" disabled={!reason.trim() || publishAction.loading} onClick={confirmPublish}>
                {publishAction.loading ? "Publishing…" : "Confirm Publish"}
              </Btn>
            </div>
          </Card>
        </div>
      )}
    </Card>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function PolicyEditorForm({ form, setForm, mandatory }: {
  form: DraftForm; setForm: (f: DraftForm) => void; mandatory: boolean;
}) {
  const toggleChannel = (field: "required_channels" | "primary_channels" | "fallback_channels", ch: string) => {
    const cur = new Set(form[field] ?? []);
    if (cur.has(ch)) cur.delete(ch); else cur.add(ch);
    setForm({ ...form, [field]: Array.from(cur) });
  };
  const toggleRole = (role: string) => {
    const rules = form.recipient_rules ?? [];
    const exists = rules.find(r => r.recipient_role === role);
    setForm({
      ...form,
      recipient_rules: exists ? rules.filter(r => r.recipient_role !== role) : [...rules, { recipient_role: role, is_required: true }],
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {mandatory && (
        <p style={{ fontSize: 11, color: "var(--warning-text)", margin: 0, display: "flex", alignItems: "center", gap: 4 }}>
          <Lock size={11}/> Mandatory event — in_app must remain a required channel.
        </p>
      )}
      {(["required_channels", "primary_channels", "fallback_channels"] as const).map(field => (
        <Field key={field} label={field.replace(/_/g, " ")}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {ALL_CHANNELS.map(ch => (
              <button key={ch} type="button" onClick={() => toggleChannel(field, ch)}
                style={{
                  padding: "4px 9px", borderRadius: 999, fontSize: 11, cursor: "pointer",
                  border: "1px solid var(--border)",
                  background: (form[field] ?? []).includes(ch) ? "var(--brand)" : "var(--surface-sunken)",
                  color: (form[field] ?? []).includes(ch) ? "#fff" : "var(--text-secondary)",
                }}>{ch}</button>
            ))}
          </div>
        </Field>
      ))}
      <Field label="Recipient roles">
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {RECIPIENT_ROLES.map(role => (
            <button key={role} type="button" onClick={() => toggleRole(role)}
              style={{
                padding: "4px 9px", borderRadius: 999, fontSize: 11, cursor: "pointer",
                border: "1px solid var(--border)",
                background: (form.recipient_rules ?? []).some(r => r.recipient_role === role) ? "var(--brand)" : "var(--surface-sunken)",
                color: (form.recipient_rules ?? []).some(r => r.recipient_role === role) ? "#fff" : "var(--text-secondary)",
              }}>{role.replace(/_/g, " ")}</button>
          ))}
        </div>
      </Field>
      <Field label="Escalation delay (minutes)">
        <input type="number" value={form.escalation_delay_minutes ?? ""} onChange={e => setForm({ ...form, escalation_delay_minutes: e.target.value ? Number(e.target.value) : null })} style={inputStyle}/>
      </Field>
      <Field label="Retry interval (seconds)">
        <input type="number" value={form.retry_interval_seconds ?? 300} onChange={e => setForm({ ...form, retry_interval_seconds: Number(e.target.value) })} style={inputStyle}/>
      </Field>
      <Field label="Max attempts">
        <input type="number" value={form.max_attempts ?? 3} onChange={e => setForm({ ...form, max_attempts: Number(e.target.value) })} style={inputStyle}/>
      </Field>
      <Field label="Change summary">
        <textarea value={form.change_summary ?? ""} onChange={e => setForm({ ...form, change_summary: e.target.value })} rows={2} style={{ ...inputStyle, resize: "vertical" }}/>
      </Field>
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: "100%", padding: "7px 9px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box" };

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textTransform: "capitalize" }}>
      {label}
      <div style={{ marginTop: 4 }}>{children}</div>
    </label>
  );
}
