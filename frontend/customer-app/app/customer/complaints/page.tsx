"use client";
/**
 * MODULE-L5-02 bug #34 — Customer Complaints list + file a complaint.
 *
 * The customer app had NO complaint surface at all. The person who actually
 * files a complaint could not file one, read it, or act on it — every endpoint
 * existed and none was reachable.
 */
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import {
  listComplaints, createComplaint, checkComplaintEligibility,
  Complaint,
} from "../../../lib/api/customer-complaints";

const COMPLAINT_TYPES = [
  { value: "poor_work_quality",     label: "Poor work quality" },
  { value: "service_not_completed", label: "Service not completed" },
  { value: "technician_behaviour",  label: "Technician behaviour" },
  { value: "billing_issue",         label: "Billing issue" },
  { value: "delay",                 label: "Delay" },
  { value: "property_damage",       label: "Property damage" },
  { value: "other",                 label: "Other" },
];

const STATUS_LABEL: Record<string, string> = {
  open: "Open",
  awaiting_provider_response: "Awaiting provider",
  awaiting_customer_response: "Your response needed",
  under_admin_review: "Under review",
  resolution_proposed: "Resolution offered",
  rework_approved: "Rework scheduled",
  refund_requested: "Refund requested",
  refund_approved: "Refund approved",
  refund_recorded: "Refund paid",
  resolved: "Resolved",
  settled: "Settled",
  closed: "Closed",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

function statusColor(s: string): string {
  if (["resolved", "settled", "closed"].includes(s)) return "#0a7c3f";
  if (["rejected", "cancelled"].includes(s)) return "#8a8a8a";
  if (s === "awaiting_customer_response" || s === "resolution_proposed") return "#b45309";
  return "#1d4ed8";
}

export default function CustomerComplaintsPage() {
  const searchParams = useSearchParams();
  // Deep link from a job/booking: /customer/complaints?record_type=service_job&record_id=…
  const presetType = searchParams?.get("record_type") ?? "";
  const presetId   = searchParams?.get("record_id") ?? "";

  const [complaints, setComplaints] = useState<Complaint[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const [showForm, setShowForm] = useState(!!presetId);
  const [eligible, setEligible] = useState<boolean | null>(null);
  const [eligReason, setEligReason] = useState<string | null>(null);
  const [complaintType, setComplaintType] = useState("poor_work_quality");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<unknown>(null);

  const load = useCallback(() => {
    listComplaints().then(setComplaints).catch(setError);
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!presetId || !presetType) return;
    checkComplaintEligibility(presetType, presetId)
      .then(r => { setEligible(r.eligible); setEligReason(r.reason ?? null); })
      .catch(() => { setEligible(null); });
  }, [presetType, presetId]);

  async function submit() {
    if (!description.trim()) return;
    setSubmitting(true); setFormError(null);
    try {
      await createComplaint({
        record_type: presetType,
        record_id: presetId,
        complaint_type: complaintType,
        description: description.trim(),
        ...(title.trim() ? { title: title.trim() } : {}),
      });
      setShowForm(false); setDescription(""); setTitle("");
      load();
    } catch (e) {
      setFormError(e);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>My Complaints</h1>
      <ErrorBanner error={error} />

      {presetId && showForm && (
        <div className="co-card" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Raise a complaint</div>

          {eligible === false && (
            <div className="co-error-banner" style={{ marginBottom: 10 }}>
              {eligReason ?? "This job cannot be complained about."}
            </div>
          )}

          {eligible !== false && (
            <>
              <label style={{ fontSize: 12, fontWeight: 600 }}>What went wrong?</label>
              <select
                value={complaintType}
                onChange={e => setComplaintType(e.target.value)}
                style={{ width: "100%", padding: 10, marginBottom: 10, borderRadius: 8 }}
              >
                {COMPLAINT_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>

              <label style={{ fontSize: 12, fontWeight: 600 }}>Title (optional)</label>
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Short summary"
                style={{ width: "100%", padding: 10, marginBottom: 10, borderRadius: 8 }}
              />

              <label style={{ fontSize: 12, fontWeight: 600 }}>Describe the problem</label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                rows={4}
                placeholder="Tell us what happened…"
                style={{ width: "100%", padding: 10, marginBottom: 10, borderRadius: 8 }}
              />

              <ErrorBanner error={formError} />

              <div style={{ display: "flex", gap: 8 }}>
                <button
                  className="co-btn"
                  disabled={!description.trim() || submitting}
                  onClick={submit}
                >
                  {submitting ? "Submitting…" : "Submit complaint"}
                </button>
                <button className="co-btn co-btn-secondary" onClick={() => setShowForm(false)}>
                  Cancel
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {!complaints && !error && <div className="co-skeleton" style={{ height: 160 }} />}

      {complaints && complaints.length === 0 && (
        <div className="co-card" style={{ textAlign: "center", padding: 24 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>No complaints</div>
          <div style={{ fontSize: 13, color: "#666" }}>
            If something goes wrong with a job, you can raise a complaint from the job page.
          </div>
        </div>
      )}

      {complaints?.map(c => (
        <Link key={c.id} href={`/customer/complaints/${c.id}`} style={{ textDecoration: "none", color: "inherit" }}>
          <div className="co-card" style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <div style={{ fontWeight: 700 }}>{c.complaint_number}</div>
              <span style={{
                fontSize: 11, fontWeight: 700, padding: "3px 8px", borderRadius: 999,
                background: `${statusColor(c.status)}18`, color: statusColor(c.status),
              }}>
                {STATUS_LABEL[c.status] ?? c.status.replace(/_/g, " ")}
              </span>
            </div>
            <div style={{ fontSize: 14, marginBottom: 4 }}>
              {c.title || c.complaint_type.replace(/_/g, " ")}
            </div>
            <div style={{ fontSize: 12, color: "#666" }}>
              Raised {String(c.created_at).slice(0, 10)}
              {c.resolved_at ? ` · Resolved ${String(c.resolved_at).slice(0, 10)}` : ""}
            </div>
          </div>
        </Link>
      ))}

      <BottomNav />
    </div>
  );
}
