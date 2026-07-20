"use client";
/**
 * MODULE-L5-13 — Customer "My Reviews".
 *
 * The customer could leave a rating but had no way to see, edit, or report its
 * own reviews, though the customer_reviews engine exposes all of it. This is the
 * customer's review list with in-place edit and a flag action.
 */
import { useEffect, useState, useCallback } from "react";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import {
  listMyReviews, editReview, flagReview, CustomerReview,
} from "../../../lib/api/customer-reviews";

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending review", approved: "Published", rejected: "Rejected",
  hidden: "Hidden", flagged: "Under review",
};
function statusColor(s: string): string {
  if (s === "approved") return "#0a7c3f";
  if (s === "rejected" || s === "hidden") return "#8a8a8a";
  return "#b45309";
}

function Stars({ value, onChange }: { value: number; onChange?: (n: number) => void }) {
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} disabled={!onChange} onClick={() => onChange?.(n)}
          style={{ fontSize: onChange ? 28 : 18, background: "none", border: "none",
            cursor: onChange ? "pointer" : "default", padding: 0,
            color: n <= value ? "var(--accent)" : "var(--border-strong)" }}>★</button>
      ))}
    </div>
  );
}

export default function CustomerReviewsPage() {
  const [reviews, setReviews] = useState<CustomerReview[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const [editing, setEditing] = useState<CustomerReview | null>(null);
  const [eRating, setERating] = useState(0);
  const [eText, setEText] = useState("");
  const [saving, setSaving] = useState(false);

  const [flagging, setFlagging] = useState<CustomerReview | null>(null);
  const [flagReason, setFlagReason] = useState("");

  const load = useCallback(() => {
    listMyReviews().then(setReviews).catch(setError);
  }, []);
  useEffect(() => { load(); }, [load]);

  function openEdit(r: CustomerReview) {
    setEditing(r); setERating(r.overall_rating); setEText(r.review_text ?? ""); setError(null);
  }
  async function saveEdit() {
    if (!editing) return;
    setSaving(true); setError(null);
    try {
      await editReview(editing.id, { overall_rating: eRating, review_text: eText || undefined });
      setEditing(null); load();
    } catch (e) { setError(e); } finally { setSaving(false); }
  }

  async function submitFlag() {
    if (!flagging || !flagReason) return;
    setSaving(true); setError(null);
    try {
      // Slice 2F-24: tenant argument removed -- the backend derives the flag's
      // tenant from the review and rejects a client-supplied tenant_id.
      await flagReview(flagging.id, "other", flagReason);
      setFlagging(null); setFlagReason("");
    } catch (e) { setError(e); } finally { setSaving(false); }
  }

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>My Reviews</h1>
      <ErrorBanner error={error} />

      {reviews === null ? (
        <div className="co-card">Loading…</div>
      ) : reviews.length === 0 ? (
        <div className="co-card" style={{ textAlign: "center", padding: 24 }}>
          You haven&apos;t written any reviews yet. Rate a completed booking to leave one.
        </div>
      ) : (
        reviews.map((r) => (
          <div key={r.id} className="co-card" style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Stars value={r.overall_rating} />
              <span style={{ fontSize: 12, fontWeight: 600, color: statusColor(r.status) }}>
                {STATUS_LABEL[r.status] ?? r.status}
              </span>
            </div>
            {r.review_text && (
              <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "8px 0 0" }}>{r.review_text}</p>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button className="co-btn-secondary" style={{ fontSize: 13, padding: "6px 12px" }}
                onClick={() => openEdit(r)}>Edit</button>
              <button className="co-btn-secondary" style={{ fontSize: 13, padding: "6px 12px" }}
                onClick={() => { setFlagging(r); setFlagReason(""); setError(null); }}>Report</button>
            </div>
          </div>
        ))
      )}

      {/* Edit modal */}
      {editing && (
        <div className="co-modal-backdrop" onClick={() => setEditing(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200,
            display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()} className="co-card"
            style={{ width: "100%", maxWidth: 480, borderRadius: "16px 16px 0 0", margin: 0 }}>
            <div style={{ fontWeight: 700, marginBottom: 12 }}>Edit your review</div>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
              <Stars value={eRating} onChange={setERating} />
            </div>
            <textarea value={eText} onChange={(e) => setEText(e.target.value)} rows={4}
              placeholder="Update your comment (optional)"
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="co-btn-secondary" style={{ flex: 1 }} onClick={() => setEditing(null)}>Cancel</button>
              <button className="co-btn-primary" style={{ flex: 1 }} disabled={saving || eRating < 1}
                onClick={saveEdit}>{saving ? "Saving…" : "Save"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Flag modal */}
      {flagging && (
        <div onClick={() => setFlagging(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200,
            display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()} className="co-card"
            style={{ width: "100%", maxWidth: 480, borderRadius: "16px 16px 0 0", margin: 0 }}>
            <div style={{ fontWeight: 700, marginBottom: 12 }}>Report this review</div>
            <textarea value={flagReason} onChange={(e) => setFlagReason(e.target.value)} rows={3}
              placeholder="Tell us what's wrong…"
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="co-btn-secondary" style={{ flex: 1 }} onClick={() => setFlagging(null)}>Cancel</button>
              <button className="co-btn-primary" style={{ flex: 1 }} disabled={saving || !flagReason}
                onClick={submitFlag}>{saving ? "Sending…" : "Report"}</button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
