"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import BottomNav from "../../../../components/BottomNav";
import ErrorBanner from "../../../../components/ErrorBanner";
import {
  getCustomerBookingDetail, getCustomerBookingTracking,
  cancelCustomerBooking, rescheduleCustomerBooking,
} from "../../../../lib/api/customer-home-services";

// Mirrors CUSTOMER_CANCELLABLE_JOB_STATUSES (home_service_assignment/constants.py):
// once real work has progressed further, cancel/reschedule must go through a
// complaint instead — the backend is the enforced source of truth (a stale
// client guess here would just get a 409, handled below).
const CANCELLABLE_STATUSES = new Set(["pending_assignment", "assigned", "accepted", "scheduled"]);

export default function BookingDetailPage() {
  const params = useParams();
  const bookingId = params.bookingId as string;
  const [detail, setDetail] = useState<any>(null);
  const [tracking, setTracking] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState<string | null>(null);
  const [modal, setModal] = useState<"cancel" | "reschedule" | null>(null);
  const [reason, setReason] = useState("");
  const [newDate, setNewDate] = useState("");
  const [newWindow, setNewWindow] = useState("");

  const load = () => {
    getCustomerBookingDetail(bookingId).then(setDetail).catch(setError);
    getCustomerBookingTracking(bookingId).then(setTracking).catch(() => {});
  };
  useEffect(load, [bookingId]);

  async function doCancel() {
    if (!reason.trim()) return;
    setBusy(true); setError(null);
    try {
      await cancelCustomerBooking(bookingId, { reason: reason.trim() });
      setOk("Your booking has been cancelled.");
      setModal(null); setReason("");
      load();
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  async function doReschedule() {
    if (!reason.trim() || !newDate) return;
    setBusy(true); setError(null);
    try {
      await rescheduleCustomerBooking(bookingId, {
        scheduled_date: newDate, scheduled_time_window: newWindow || undefined, reason: reason.trim(),
      });
      setOk("Your booking has been rescheduled.");
      setModal(null); setReason(""); setNewDate(""); setNewWindow("");
      load();
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>Booking Details</h1>
      <ErrorBanner error={error} />
      {ok && <div className="co-card" style={{ background: "#ecfdf3", color: "#0a7c3f", marginBottom: 12 }}>{ok}</div>}
      {!detail && !error && <div className="co-skeleton" style={{ height: 200 }} />}
      {detail?.error && <div className="co-error-banner">{detail.error.message}</div>}
      {detail && !detail.error && (
        <div className="co-card" style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          <div style={{ fontWeight: 700 }}>#{detail.booking_number}</div>
          <div>{detail.issue_summary}</div>
          <div style={{ fontSize: 13 }}>Status: {detail.status}</div>
          {detail.assignment_message && <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{detail.assignment_message}</div>}
          {detail.selected_provider?.provider_name && <div><strong>Provider:</strong> {detail.selected_provider.provider_name}</div>}
          {detail.selected_price_amount && <div><strong>Price:</strong> ₹{detail.selected_price_amount} ({detail.selected_price_option})</div>}
          <div><strong>Payment:</strong> Customer Pays Provider Directly</div>
          {detail.address && <div><strong>Address:</strong> {detail.address.address_line1}, {detail.city}</div>}
          {/* MODULE-L5-16: work quotes for this job (approve/reject). Only when a
              job exists — the provider sends quotes against the job. */}
          {detail.job_id && (
            <Link
              href={`/customer/bookings/${bookingId}/quotes?job_id=${detail.job_id}`}
              className="co-btn-secondary"
              style={{ textAlign: "center" }}
            >
              Work Quotes
            </Link>
          )}
          {/* MODULE-L5-14: message the provider about this booking. The customer
              had no chat surface at all though customer_chat_router exists. */}
          {detail.status !== "cancelled" && (
            <Link
              href={`/customer/chat?record_type=service_booking&record_id=${bookingId}`}
              className="co-btn-secondary"
              style={{ textAlign: "center" }}
            >
              Message Provider
            </Link>
          )}
          {/* MODULE-L5-29: cancel/reschedule a confirmed booking. Only offered
              while the job hasn't progressed past assignment/scheduling — the
              backend re-enforces this and returns 409 past that point. */}
          {CANCELLABLE_STATUSES.has(detail.status) && (
            <div style={{ display: "flex", gap: 8 }}>
              <button className="co-btn-secondary" style={{ flex: 1 }}
                onClick={() => { setModal("reschedule"); setReason(""); }}>Reschedule</button>
              <button className="co-btn-secondary" style={{ flex: 1, color: "#b91c1c" }}
                onClick={() => { setModal("cancel"); setReason(""); }}>Cancel Booking</button>
            </div>
          )}
          {detail.status === "completed" && (
            <Link href={`/customer/bookings/${bookingId}/rate`} className="co-btn-primary" style={{ textAlign: "center" }}>Rate Your Experience</Link>
          )}
          {/* MODULE-L5-02 bug #34: the customer app had no way at all to raise a
              complaint about a job that went wrong — every complaint endpoint
              existed and none was reachable. Deep-links into the complaint form. */}
          {detail.status === "completed" && (
            <Link
              href={`/customer/complaints?record_type=service_booking&record_id=${bookingId}`}
              className="co-btn-secondary"
              style={{ textAlign: "center" }}
            >
              Report a problem
            </Link>
          )}
        </div>
      )}

      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Status Timeline</h2>
      {tracking?.timeline && (
        <div className="co-card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {tracking.timeline.map((t: any, i: number) => (
            <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <div style={{ width: 8, height: 8, borderRadius: 4, background: "var(--success)", marginTop: 6 }} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{t.event}</div>
                {t.created_at && <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{t.created_at}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
      {modal === "cancel" && (
        <div onClick={() => setModal(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200,
            display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()} className="co-card"
            style={{ width: "100%", maxWidth: 480, borderRadius: "16px 16px 0 0", margin: 0 }}>
            <div style={{ fontWeight: 700, marginBottom: 12 }}>Cancel this booking?</div>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3}
              placeholder="Why are you cancelling? (required)"
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="co-btn-secondary" style={{ flex: 1 }} onClick={() => setModal(null)}>Keep booking</button>
              <button className="co-btn-primary" style={{ flex: 1 }} disabled={!reason.trim() || busy}
                onClick={doCancel}>{busy ? "…" : "Cancel booking"}</button>
            </div>
          </div>
        </div>
      )}

      {modal === "reschedule" && (
        <div onClick={() => setModal(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200,
            display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()} className="co-card"
            style={{ width: "100%", maxWidth: 480, borderRadius: "16px 16px 0 0", margin: 0,
              display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontWeight: 700 }}>Reschedule this booking</div>
            <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)}
              style={{ padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
            <input type="text" value={newWindow} onChange={(e) => setNewWindow(e.target.value)}
              placeholder="Time window (optional), e.g. 10am-12pm"
              style={{ padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2}
              placeholder="Why are you rescheduling? (required)"
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
            <div style={{ display: "flex", gap: 8 }}>
              <button className="co-btn-secondary" style={{ flex: 1 }} onClick={() => setModal(null)}>Cancel</button>
              <button className="co-btn-primary" style={{ flex: 1 }} disabled={!reason.trim() || !newDate || busy}
                onClick={doReschedule}>{busy ? "…" : "Reschedule"}</button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
