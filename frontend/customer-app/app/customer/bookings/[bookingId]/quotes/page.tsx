"use client";
/**
 * MODULE-L5-16 — Customer quote approval.
 *
 * A provider sends a quote when a job needs extra work/parts. Here the customer
 * reviews the line items and approves, rejects, or asks for a revision. Without
 * this the job stalled at "waiting for customer approval". Wired to the
 * quote_checklist customer engine.
 *
 * Reached from the booking detail with the job id: /customer/bookings/{id}/quotes?job_id=…
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import ErrorBanner from "../../../../../components/ErrorBanner";
import {
  listJobQuotes, approveQuote, rejectQuote, requestQuoteRevision, Quote,
} from "../../../../../lib/api/customer-quotes";

const STATUS_LABEL: Record<string, string> = {
  sent_to_customer: "Awaiting your approval",
  customer_approved: "Approved",
  customer_rejected: "Rejected",
  revision_requested: "Revision requested",
  expired: "Expired", cancelled: "Cancelled",
};
function statusColor(s: string): string {
  if (s === "customer_approved") return "#0a7c3f";
  if (s === "customer_rejected" || s === "cancelled" || s === "expired") return "#b91c1c";
  return "#b45309";
}
const money = (v?: string | null, ccy?: string | null) =>
  v == null ? "—" : `${ccy ?? "₹"}${Number(v).toLocaleString()}`;

export default function CustomerQuotesPage() {
  const params = useParams();
  const search = useSearchParams();
  const router = useRouter();
  const bookingId = params.bookingId as string;
  const jobId = search?.get("job_id") ?? "";

  const [quotes, setQuotes] = useState<Quote[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<Quote | null>(null);
  const [reason, setReason] = useState("");
  const [mode, setMode] = useState<"reject" | "revision">("reject");

  const load = useCallback(() => {
    if (!jobId) { setQuotes([]); return; }
    listJobQuotes(jobId).then(setQuotes).catch(setError);
  }, [jobId]);
  useEffect(() => { load(); }, [load]);

  async function doApprove(q: Quote) {
    setBusy(q.id); setError(null);
    try { await approveQuote(q.id); load(); }
    catch (e) { setError(e); } finally { setBusy(null); }
  }
  async function submitReason() {
    if (!rejecting || !reason.trim()) return;
    setBusy(rejecting.id); setError(null);
    try {
      if (mode === "reject") await rejectQuote(rejecting.id, reason.trim());
      else await requestQuoteRevision(rejecting.id, reason.trim());
      setRejecting(null); setReason(""); load();
    } catch (e) { setError(e); } finally { setBusy(null); }
  }

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 0" }}>
        <button onClick={() => router.push(`/customer/bookings/${bookingId}`)}
          style={{ background: "none", border: "none", fontSize: 22, cursor: "pointer" }}>‹</button>
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Work Quotes</h1>
      </div>
      <ErrorBanner error={error} />

      {quotes === null ? (
        <div className="co-card">Loading…</div>
      ) : quotes.length === 0 ? (
        <div className="co-card" style={{ textAlign: "center", padding: 24, color: "var(--text-tertiary)" }}>
          No quotes for this job.
        </div>
      ) : (
        quotes.map((q) => {
          // Phase 2A: only the current (non-superseded) quote is actionable
          // -- an older revision that's since been replaced by a newer one
          // is kept visible for history but can no longer be approved.
          const actionable = q.status === "sent_to_customer" && q.is_current !== false;
          return (
            <div key={q.id} className="co-card" style={{ marginBottom: 12, opacity: q.is_current === false ? 0.7 : 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
                  Quote #{q.quote_number}
                  {q.version_number ? <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-tertiary)" }}>v{q.version_number}</span> : null}
                  {q.is_current === false && (
                    <span style={{ fontSize: 11, fontWeight: 600, color: "#b45309", background: "#fef3c7", padding: "1px 6px", borderRadius: 4 }}>
                      Superseded
                    </span>
                  )}
                </div>
                <span style={{ fontSize: 12, fontWeight: 600, color: statusColor(q.status) }}>
                  {STATUS_LABEL[q.status] ?? q.status}
                </span>
              </div>

              <div style={{ margin: "10px 0", display: "flex", flexDirection: "column", gap: 4 }}>
                {(q.items ?? []).map((it) => (
                  <div key={it.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}>
                    <span>{it.description ?? it.item_type ?? "Item"}
                      {it.quantity ? ` ×${it.quantity}` : ""}</span>
                    <span>{money(String(it.amount ?? it.unit_price ?? ""), q.currency)}</span>
                  </div>
                ))}
                {q.labour_amount && Number(q.labour_amount) > 0 && (
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}>
                    <span>Labour</span><span>{money(q.labour_amount, q.currency)}</span></div>
                )}
                {q.parts_amount && Number(q.parts_amount) > 0 && (
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}>
                    <span>Parts</span><span>{money(q.parts_amount, q.currency)}</span></div>
                )}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700,
                borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                <span>Total</span><span>{money(q.total_amount, q.currency)}</span>
              </div>
              {q.notes && (
                <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 8 }}>{q.notes}</p>
              )}

              {actionable && (
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <button className="co-btn-primary" style={{ flex: 1 }} disabled={busy === q.id}
                    onClick={() => doApprove(q)}>{busy === q.id ? "…" : "Approve"}</button>
                  <button className="co-btn-secondary" disabled={busy === q.id}
                    onClick={() => { setRejecting(q); setMode("revision"); setReason(""); }}>Ask changes</button>
                  <button className="co-btn-secondary" disabled={busy === q.id}
                    onClick={() => { setRejecting(q); setMode("reject"); setReason(""); }}>Reject</button>
                </div>
              )}
            </div>
          );
        })
      )}

      {rejecting && (
        <div onClick={() => setRejecting(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200,
            display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()} className="co-card"
            style={{ width: "100%", maxWidth: 480, borderRadius: "16px 16px 0 0", margin: 0 }}>
            <div style={{ fontWeight: 700, marginBottom: 12 }}>
              {mode === "reject" ? "Reject quote" : "Request changes"}
            </div>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3}
              placeholder={mode === "reject" ? "Why are you rejecting? (required)" : "What should change? (required)"}
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="co-btn-secondary" style={{ flex: 1 }} onClick={() => setRejecting(null)}>Cancel</button>
              <button className="co-btn-primary" style={{ flex: 1 }} disabled={!reason.trim() || busy === rejecting.id}
                onClick={submitReason}>{busy === rejecting.id ? "…" : "Submit"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
