"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { customerFlowApi, CustomerBookingDraft } from "../../../../../lib/api";

const STATUS_COLORS: Record<string, string> = {
  draft:     "#f3f4f6",
  estimated: "#fef9c3",
  confirmed: "#dcfce7",
  cancelled: "#fef2f2",
};

const FIELD_LABELS: [keyof CustomerBookingDraft, string][] = [
  ["flow_type",        "Flow Type"],
  ["status",           "Status"],
  ["customer_name",    "Customer Name"],
  ["customer_phone",   "Phone"],
  ["customer_email",   "Email"],
  ["city",             "City"],
  ["zipcode",          "Zipcode"],
  ["address_text",     "Address"],
  ["issue_summary",    "Issue Summary"],
  ["preferred_date",   "Preferred Date"],
  ["preferred_time_slot", "Time Slot"],
  ["estimate_min",     "Est. Min"],
  ["estimate_max",     "Est. Max"],
  ["estimate_currency","Currency"],
];

export default function DraftDetailPage() {
  const { draftId } = useParams<{ draftId: string }>();
  const [draft, setDraft] = useState<CustomerBookingDraft | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await customerFlowApi.adminGetDraft(draftId);
      setDraft(d);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [draftId]);

  if (loading) return <div style={{ padding: "2rem" }}>Loading...</div>;
  if (!draft)  return <div style={{ padding: "2rem" }}>Draft not found.</div>;

  return (
    <div style={{ padding: "1.5rem", maxWidth: "800px" }}>
      <a href="/admin/customer-flow/drafts" style={{ color: "#6b7280", fontSize: "0.85rem", textDecoration: "none" }}>
        ← Back to Drafts
      </a>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginTop: "0.75rem", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.4rem", fontWeight: 700, margin: 0 }}>Booking Draft</h1>
          <code style={{ fontSize: "0.75rem", color: "#9ca3af" }}>{draft.id}</code>
        </div>
        <span style={{ fontSize: "0.8rem", padding: "0.3rem 0.75rem", borderRadius: "9999px", background: STATUS_COLORS[draft.status] ?? "#f3f4f6", fontWeight: 600 }}>
          {draft.status}
        </span>
      </div>

      {/* Main fields */}
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", padding: "1.25rem", marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "0.9rem", fontWeight: 700, margin: "0 0 0.75rem", color: "#374151" }}>Draft Details</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          {FIELD_LABELS.map(([field, label]) => (
            <div key={field}>
              <div style={{ fontSize: "0.7rem", color: "#9ca3af", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
              <div style={{ fontSize: "0.85rem", color: "#111827", marginTop: "0.1rem" }}>
                {draft[field] != null ? String(draft[field]) : <span style={{ color: "#d1d5db" }}>—</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Catalog IDs */}
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", padding: "1.25rem", marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "0.9rem", fontWeight: 700, margin: "0 0 0.75rem", color: "#374151" }}>Catalog Selections</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          {(["category_id", "service_id", "brand_id", "issue_type_id", "selected_tenant_id"] as const).map(field => (
            <div key={field}>
              <div style={{ fontSize: "0.7rem", color: "#9ca3af", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>{field.replace(/_id$/, "")}</div>
              <div style={{ fontSize: "0.78rem", color: "#6b7280", fontFamily: "monospace", marginTop: "0.1rem" }}>
                {draft[field] ?? <span style={{ color: "#d1d5db" }}>—</span>}
              </div>
            </div>
          ))}
        </div>
        {draft.service_option_ids && draft.service_option_ids.length > 0 && (
          <div style={{ marginTop: "0.75rem" }}>
            <div style={{ fontSize: "0.7rem", color: "#9ca3af", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Service Options</div>
            <div style={{ marginTop: "0.25rem", display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
              {draft.service_option_ids.map((id, i) => (
                <span key={i} style={{ fontSize: "0.7rem", fontFamily: "monospace", background: "#f3f4f6", padding: "0.15rem 0.4rem", borderRadius: "0.25rem" }}>{id}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Final records */}
      {(draft.final_job_id || draft.final_appointment_id || draft.final_lead_id) && (
        <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "0.5rem", padding: "1.25rem" }}>
          <h2 style={{ fontSize: "0.9rem", fontWeight: 700, margin: "0 0 0.75rem", color: "#166534" }}>Final Records Created</h2>
          {draft.final_job_id && (
            <div style={{ marginBottom: "0.4rem" }}>
              <span style={{ fontSize: "0.75rem", color: "#166534" }}>Job ID: </span>
              <code style={{ fontSize: "0.78rem" }}>{draft.final_job_id}</code>
            </div>
          )}
          {draft.final_appointment_id && (
            <div style={{ marginBottom: "0.4rem" }}>
              <span style={{ fontSize: "0.75rem", color: "#166534" }}>Appointment ID: </span>
              <code style={{ fontSize: "0.78rem" }}>{draft.final_appointment_id}</code>
            </div>
          )}
          {draft.final_lead_id && (
            <div>
              <span style={{ fontSize: "0.75rem", color: "#166534" }}>Lead ID: </span>
              <code style={{ fontSize: "0.78rem" }}>{draft.final_lead_id}</code>
            </div>
          )}
        </div>
      )}

      {/* Timestamps */}
      <div style={{ marginTop: "1rem", fontSize: "0.72rem", color: "#9ca3af" }}>
        Created: {draft.created_at ? new Date(draft.created_at).toLocaleString() : "—"}
        {" · "}
        Updated: {draft.updated_at ? new Date(draft.updated_at).toLocaleString() : "—"}
      </div>
    </div>
  );
}
