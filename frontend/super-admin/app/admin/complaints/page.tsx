"use client";
/**
 * Complaint policies -- the deadlines providers must meet on customer
 * complaints.
 *
 * The sidebar has always linked "Complaints" to /admin/complaints, but no page
 * existed, and the policy endpoints (/v1/admin/complaint-policies) had no UI at
 * all. The response window, resolution window and penalty could only be
 * changed by hand in the database -- and until the backend started reading
 * them, changing them did nothing anyway.
 *
 * Providers resolve complaints themselves; the platform does not adjudicate.
 * What the platform owns is the clock, and this page is where it is set.
 */
import { useCallback, useState, type CSSProperties } from "react";
import { adminComplaintPolicyApi, type ComplaintPolicyRecord } from "../../../lib/api";
import { Card, Badge, Btn, Skeleton, Toaster, SectionHeader, type ToastItem } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { AlertTriangle, RefreshCw, Save, Plus } from "lucide-react";

type Editable = Pick<ComplaintPolicyRecord,
  | "policy_name" | "complaint_window_hours" | "default_provider_response_hours"
  | "default_resolution_hours" | "provider_sla_breach_penalty"
  | "require_provider_response" | "allow_customer_complaints"
  | "allow_rework" | "allow_refund_request" | "allow_duplicate_open_complaints" | "is_active">;

const HOUR_FIELDS: { key: keyof Editable; label: string; help: string }[] = [
  { key: "default_provider_response_hours", label: "Reply within (hours)",
    help: "Time the provider has to send a first reply. Safety concerns always get 1 hour." },
  { key: "default_resolution_hours", label: "Resolve within (hours)",
    help: "Time the provider has to propose a resolution or finish the agreed rework/refund. Restarts each time the case comes back to them." },
  { key: "complaint_window_hours", label: "Customer filing window (hours)",
    help: "How long after the service a customer can still file a complaint." },
];

const TOGGLES: { key: keyof Editable; label: string }[] = [
  { key: "require_provider_response", label: "Enforce the reply deadline" },
  { key: "allow_customer_complaints", label: "Customers can file complaints" },
  { key: "allow_rework", label: "Providers can offer free rework" },
  { key: "allow_refund_request", label: "Refunds can be requested or offered" },
  { key: "allow_duplicate_open_complaints", label: "Allow a second open complaint of the same type" },
  { key: "is_active", label: "Policy active" },
];

function scopeLabel(p: ComplaintPolicyRecord): string {
  if (p.tenant_id) return "Single provider";
  if (p.category_id) return "Single category";
  return "All providers";
}

function editableOf(p: ComplaintPolicyRecord): Editable {
  return {
    policy_name: p.policy_name,
    complaint_window_hours: p.complaint_window_hours,
    default_provider_response_hours: p.default_provider_response_hours,
    default_resolution_hours: p.default_resolution_hours,
    provider_sla_breach_penalty: p.provider_sla_breach_penalty,
    require_provider_response: p.require_provider_response,
    allow_customer_complaints: p.allow_customer_complaints,
    allow_rework: p.allow_rework,
    allow_refund_request: p.allow_refund_request,
    allow_duplicate_open_complaints: p.allow_duplicate_open_complaints,
    is_active: p.is_active,
  };
}

function validationError(d: Editable): string | null {
  for (const f of HOUR_FIELDS) {
    const v = d[f.key] as number;
    if (!Number.isInteger(v) || v < 1 || v > 2160) return `${f.label} must be a whole number from 1 to 2160.`;
  }
  const penalty = Number(d.provider_sla_breach_penalty);
  if (!Number.isFinite(penalty) || penalty < 0 || penalty > 100000) return "Penalty must be between 0 and 100000.";
  if (!d.policy_name.trim()) return "Give the policy a name.";
  return null;
}

const inputStyle: CSSProperties = {
  padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)",
  background: "var(--surface)", color: "var(--text-primary)", fontSize: 13, width: "100%", boxSizing: "border-box",
};

export default function AdminComplaintPoliciesPage() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Editable | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const { data, loading, error, refetch } = useApi(useCallback(() => adminComplaintPolicyApi.list(), []));
  const policies: ComplaintPolicyRecord[] = Array.isArray(data) ? data : [];

  const updateAction = useAction(
    useCallback((id: string, body: Partial<ComplaintPolicyRecord>) => adminComplaintPolicyApi.update(id, body), []),
  );
  const createAction = useAction(
    useCallback(() => adminComplaintPolicyApi.create({ policy_key: "default", policy_name: "Default complaint policy" }), []),
  );

  async function save(id: string) {
    if (!draft) return;
    const problem = validationError(draft);
    if (problem) { setFormError(problem); return; }
    const result = await updateAction.execute(id, { ...draft, policy_name: draft.policy_name.trim() });
    if (result) {
      addToast("Complaint policy updated. New deadlines apply to complaints filed from now on.");
      setEditing(null); setDraft(null); setFormError(null);
      refetch();
    } else {
      setFormError(updateAction.error ?? "The policy could not be saved.");
    }
  }

  async function createDefault() {
    const result = await createAction.execute();
    if (result) { addToast("Default complaint policy created."); refetch(); }
    else addToast(createAction.error ?? "The policy could not be created.", "danger");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))} />

      <SectionHeader eyebrow="Trust & quality" title="Complaint Policies"
        description="Providers resolve complaints themselves. These deadlines keep every case moving: a missed reply or resolution deadline escalates the case, charges the penalty once and counts against the provider's health."
        icon={<AlertTriangle />}
        actions={<Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>} />

      <Card padding={16}>
        <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
          Always applied: a proposed resolution the customer does not answer within 7 days resolves the case
          (with a reminder after 2 days), and a resolved case closes 72 hours after resolution. The at-risk
          warning window is the <code>complaint_sla_warning_threshold_hours</code> setting.
        </p>
      </Card>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[0, 1].map(i => <Skeleton key={i} height={140} />)}
        </div>
      ) : error ? (
        <Card padding={24} style={{ textAlign: "center" }}>
          <p style={{ color: "var(--text-secondary)", margin: "0 0 12px" }}>{error}</p>
          <Btn variant="secondary" onClick={refetch}><RefreshCw size={14} /> Retry</Btn>
        </Card>
      ) : policies.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <AlertTriangle size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: "0 0 6px" }}>No complaint policy exists yet.</p>
          <p style={{ color: "var(--text-tertiary)", fontSize: 12.5, margin: "0 0 16px" }}>
            Built-in defaults apply: reply within 24 hours, resolve within 72 hours, ₹50 penalty per missed deadline.
          </p>
          <Btn onClick={createDefault} loading={createAction.loading}><Plus size={14} /> Create default policy</Btn>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {policies.map(p => (
            <Card key={p.id} padding={18}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12, gap: 12 }}>
                <div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <p style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)", margin: 0 }}>{p.policy_name}</p>
                    <Badge variant={p.is_active ? "success" : "default"}>{p.is_active ? "Active" : "Inactive"}</Badge>
                    <Badge variant="info">{scopeLabel(p)}</Badge>
                  </div>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>Key: {p.policy_key}</p>
                </div>
                {editing !== p.id && (
                  <Btn size="sm" variant="ghost" onClick={() => { setEditing(p.id); setDraft(editableOf(p)); setFormError(null); }}>Edit</Btn>
                )}
              </div>

              {editing === p.id && draft ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <label style={{ display: "block" }}>
                    <span style={{ display: "block", fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>Policy name</span>
                    <input value={draft.policy_name} onChange={e => setDraft(d => d && ({ ...d, policy_name: e.target.value }))} style={inputStyle} />
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                    {HOUR_FIELDS.map(f => (
                      <label key={f.key} style={{ display: "block" }}>
                        <span style={{ display: "block", fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>{f.label}</span>
                        <input type="number" min={1} max={2160} step={1}
                          value={Number.isFinite(draft[f.key] as number) ? String(draft[f.key]) : ""}
                          onChange={e => setDraft(d => d && ({ ...d, [f.key]: e.target.value === "" ? NaN : Number(e.target.value) }))}
                          style={inputStyle} />
                        <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginTop: 4, lineHeight: 1.4 }}>{f.help}</span>
                      </label>
                    ))}
                    <label style={{ display: "block" }}>
                      <span style={{ display: "block", fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>Penalty per missed deadline (credits)</span>
                      <input type="number" min={0} max={100000} step="0.01"
                        value={String(draft.provider_sla_breach_penalty)}
                        onChange={e => setDraft(d => d && ({ ...d, provider_sla_breach_penalty: Number(e.target.value) }))}
                        style={inputStyle} />
                      <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginTop: 4, lineHeight: 1.4 }}>
                        Charged once for a missed reply and once per missed resolution deadline. 0 turns penalties off.
                      </span>
                    </label>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 8 }}>
                    {TOGGLES.map(t => (
                      <label key={t.key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
                        <input type="checkbox" checked={Boolean(draft[t.key])}
                          onChange={e => setDraft(d => d && ({ ...d, [t.key]: e.target.checked }))} />
                        {t.label}
                      </label>
                    ))}
                  </div>
                  {formError && <p role="alert" style={{ fontSize: 12.5, color: "var(--danger-text)", margin: 0 }}>{formError}</p>}
                  <div style={{ display: "flex", gap: 8 }}>
                    <Btn size="sm" onClick={() => save(p.id)} loading={updateAction.loading}><Save size={12} /> Save</Btn>
                    <Btn size="sm" variant="ghost" onClick={() => { setEditing(null); setDraft(null); setFormError(null); }}>Cancel</Btn>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", gap: 14, fontSize: 12, color: "var(--text-tertiary)", flexWrap: "wrap" }}>
                  <span>Reply: {p.require_provider_response ? `${p.default_provider_response_hours}h` : "not enforced"}</span>
                  <span>Resolve: {p.default_resolution_hours}h</span>
                  <span>Filing window: {p.complaint_window_hours}h</span>
                  <span>Penalty: {p.provider_sla_breach_penalty}</span>
                  <span>Complaints: {p.allow_customer_complaints ? "On" : "Off"}</span>
                  <span>Rework: {p.allow_rework ? "Allowed" : "Off"}</span>
                  <span>Refunds: {p.allow_refund_request ? "Allowed" : "Off"}</span>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
