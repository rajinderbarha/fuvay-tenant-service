"use client";
import { useApi, useAction } from "../../../hooks/useApi";
import { adminComplaintPolicyApi, ComplaintPolicyRecord } from "../../../lib/api";
import { useState, useCallback } from "react";

const inputStyle: React.CSSProperties = {
  border: "1px solid var(--border)", borderRadius: 8, padding: "6px 12px",
  fontSize: 13, background: "var(--bg)", color: "var(--text-primary)", fontFamily: "inherit",
};

export default function AdminComplaintPoliciesPage() {
  const { data: policies, loading, error, refetch } = useApi(() => adminComplaintPolicyApi.list(), []);
  const [editing, setEditing] = useState<ComplaintPolicyRecord | null>(null);
  const [form, setForm] = useState<Partial<ComplaintPolicyRecord>>({});

  const saveAction = useAction(useCallback(async () => {
    if (!editing) return;
    await adminComplaintPolicyApi.update(editing.id, form);
    setEditing(null);
    refetch();
  }, [editing, form, refetch]));

  const startEdit = (p: ComplaintPolicyRecord) => {
    setEditing(p);
    setForm({
      complaint_window_hours:          p.complaint_window_hours,
      allow_duplicate_open_complaints: p.allow_duplicate_open_complaints,
      allow_rework_request:            p.allow_rework_request,
      allow_refund_request:            p.allow_refund_request,
      require_admin_review:            p.require_admin_review,
      is_active:                       p.is_active,
    });
  };

  const BoolField = ({ label, field }: { label: string; field: keyof ComplaintPolicyRecord }) => (
    <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
      <input
        type="checkbox"
        checked={!!(form as Record<string, unknown>)[field]}
        onChange={e => setForm(prev => ({ ...prev, [field]: e.target.checked }))}
        style={{ width: 16, height: 16 }}
      />
      {label}
    </label>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 900, margin: "0 auto" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Complaint Policies</h1>

      {loading && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p>}
      {error   && <p style={{ fontSize: 13, color: "var(--danger-text)" }}>{error}</p>}
      {policies && policies.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No policies configured.</p>}

      {policies && policies.map((p: ComplaintPolicyRecord) => (
        <div key={p.id} style={{ border: "1px solid var(--border)", borderRadius: 12, padding: 20,
          background: "var(--surface)", display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{p.policy_key}</p>
              {p.category_id && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Category: {p.category_id}</p>}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                background: p.is_active ? "var(--success-bg)" : "var(--surface-sunken)",
                color: p.is_active ? "var(--success-text)" : "var(--text-tertiary)" }}>
                {p.is_active ? "Active" : "Inactive"}
              </span>
              <button onClick={() => startEdit(p)} style={{ fontSize: 13, color: "var(--accent)", background: "none",
                border: "none", cursor: "pointer", padding: 0, fontFamily: "inherit" }}>Edit</button>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              { label: "Complaint Window", val: `${p.complaint_window_hours}h` },
              { label: "Allow Duplicates",  val: p.allow_duplicate_open_complaints ? "Yes" : "No" },
              { label: "Allow Rework",      val: p.allow_rework_request ? "Yes" : "No" },
              { label: "Allow Refund",      val: p.allow_refund_request ? "Yes" : "No" },
            ].map(({ label, val }) => (
              <div key={label} style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: 10 }}>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>{label}</p>
                <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>{val}</p>
              </div>
            ))}
            <div style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: 10, gridColumn: "span 2" }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>Require Admin Review</p>
              <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>
                {p.require_admin_review ? "Yes" : "No"}
              </p>
            </div>
          </div>
        </div>
      ))}

      {editing && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex",
          alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "var(--surface)", borderRadius: 12, padding: 24, width: "100%",
            maxWidth: 480, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                Edit Policy: {editing.policy_key}
              </h2>
              <button onClick={() => setEditing(null)} style={{ fontSize: 18, background: "none", border: "none",
                cursor: "pointer", color: "var(--text-tertiary)" }}>✕</button>
            </div>
            <div>
              <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Complaint Window (hours)
              </label>
              <input type="number" min={1} style={{ ...inputStyle, width: "100%", boxSizing: "border-box" }}
                value={form.complaint_window_hours ?? ""}
                onChange={e => setForm(prev => ({ ...prev, complaint_window_hours: +e.target.value }))}
              />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <BoolField label="Allow Duplicate Open Complaints" field="allow_duplicate_open_complaints" />
              <BoolField label="Allow Rework Requests"           field="allow_rework_request" />
              <BoolField label="Allow Refund Requests"           field="allow_refund_request" />
              <BoolField label="Require Admin Review"            field="require_admin_review" />
              <BoolField label="Is Active"                       field="is_active" />
            </div>
            <button onClick={() => saveAction.execute()} disabled={saveAction.loading}
              style={{ padding: "8px 0", fontSize: 13, fontWeight: 600, borderRadius: 8, border: "none",
                cursor: "pointer", fontFamily: "inherit", background: "var(--brand)", color: "white",
                opacity: saveAction.loading ? 0.5 : 1 }}>
              {saveAction.loading ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
