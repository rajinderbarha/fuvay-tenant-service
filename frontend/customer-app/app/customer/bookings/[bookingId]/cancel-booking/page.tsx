"use client";
/**
 * CANCEL-RESCHEDULE-FOUNDATION — Cancel Booking.
 *
 * Reasons come from GET .../cancel-reschedule-eligibility
 * (allowed_cancellation_reasons / cancellation_reasons_requiring_detail) —
 * never a client-invented list. cancellation_fee/cancellation_cutoff are
 * always null today (no fee/cutoff policy exists), so no charge or cutoff
 * copy is ever shown — this reads that from the backend, not an assumption.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import ErrorBanner from "../../../../../components/ErrorBanner";
import {
  getCustomerBookingDetail, getCancelRescheduleEligibility,
  cancelCustomerBooking, newIdempotencyKey, CancelRescheduleEligibility,
} from "../../../../../lib/api/customer-home-services";

const REASON_LABELS: Record<string, string> = {
  changed_mind: "Plans changed",
  found_another_provider: "Found another provider",
  price_concern: "Price concern",
  schedule_conflict: "Schedule conflict",
  no_longer_needed: "No longer needed",
  other: "Other",
};

export default function CancelBookingPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = params.bookingId as string;

  const [detail, setDetail] = useState<any>(null);
  const [elig, setElig] = useState<CancelRescheduleEligibility | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState<string | null>(null);

  const [reason, setReason] = useState<string | null>(null);
  const [detailText, setDetailText] = useState("");
  const [step, setStep] = useState<"reason" | "confirm">("reason");
  const [idemKey] = useState(() => newIdempotencyKey());

  const load = useCallback(() => {
    getCustomerBookingDetail(bookingId).then(setDetail).catch(setError);
    getCancelRescheduleEligibility(bookingId).then(setElig).catch(setError);
  }, [bookingId]);
  useEffect(() => { load(); }, [load]);

  const needsDetail = reason ? (elig?.cancellation_reasons_requiring_detail.includes(reason) ?? false) : false;
  const canContinue = !!reason && (!needsDetail || detailText.trim().length > 0);

  async function confirmCancel() {
    if (!reason || !elig) return;
    setBusy(true); setError(null);
    try {
      await cancelCustomerBooking(bookingId, {
        reason, detail: needsDetail ? detailText.trim() : undefined,
        expected_version: elig.version,
      }, idemKey);
      setOk("Your booking has been cancelled.");
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  if (ok) {
    return (
      <div className="co-container">
        <div className="co-card" role="status" aria-live="polite" style={{ textAlign: "center", marginTop: 40 }}>
          <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>Booking cancelled</div>
          <div style={{ color: "var(--text-secondary)", marginBottom: 16 }}>{ok}</div>
          <button className="co-btn-primary" style={{ background: "var(--danger)", boxShadow: "none" }}
            onClick={() => router.replace(`/customer/bookings/${bookingId}`)}>Back to booking</button>
        </div>
      </div>
    );
  }

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 0" }}>
        <button aria-label="Back" className="co-btn-secondary" style={{ minWidth: 44, minHeight: 44, padding: 0 }}
          onClick={() => (step === "confirm" ? setStep("reason") : router.back())}>‹</button>
        <div style={{ flex: 1, textAlign: "center" }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Cancel booking</div>
          {detail && <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{detail.issue_summary} · {detail.booking_number}</div>}
        </div>
        <div style={{ width: 44 }} />
      </div>

      <ErrorBanner error={error} />

      {!detail || !elig ? (
        !error && <div className="co-skeleton" style={{ height: 200 }} />
      ) : !elig.can_cancel ? (
        <div className="co-card">This booking can no longer be cancelled here. Please raise a complaint instead.</div>
      ) : (
        <>
          <div className="co-card" role="alert" style={{ marginBottom: 16, border: "1px solid var(--danger)",
            display: "flex", gap: 10, alignItems: "center" }}>
            <span aria-hidden="true" style={{ fontSize: 20 }}>⊗</span>
            <div>
              <div style={{ fontWeight: 700 }}>Review cancellation</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>This will not cancel your booking yet.</div>
            </div>
          </div>

          <div className="co-card" style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 8 }}>
              <span aria-hidden="true">📅</span>
              <span>{detail.scheduled_date ?? detail.preferred_date ?? "Date to be confirmed"}
                {detail.scheduled_time_window ? ` · ${detail.scheduled_time_window}` : ""}</span>
            </div>
            {detail.address && (
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <span aria-hidden="true">📍</span>
                <span>{detail.address.address_line1}{detail.city ? `, ${detail.city}` : ""}</span>
              </div>
            )}
          </div>

          {step === "reason" ? (
            <>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>Why are you cancelling?</div>
              <div className="co-card" style={{ marginBottom: 16, padding: 0 }}>
                {elig.allowed_cancellation_reasons.map((code, i) => (
                  <label key={code} style={{
                    display: "flex", alignItems: "center", gap: 12, padding: 16, cursor: "pointer",
                    borderBottom: i < elig.allowed_cancellation_reasons.length - 1 ? "1px solid var(--border)" : "none",
                  }}>
                    <input type="radio" name="cancel-reason" checked={reason === code}
                      onChange={() => setReason(code)} style={{ width: 20, height: 20, accentColor: "var(--danger)" }} />
                    <span>{REASON_LABELS[code] ?? code}</span>
                  </label>
                ))}
              </div>
              {needsDetail && (
                <textarea value={detailText} onChange={(e) => setDetailText(e.target.value)} rows={2}
                  placeholder="Please tell us more (required)"
                  style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)",
                    fontSize: 15, marginBottom: 16 }} />
              )}

              <div className="co-card" style={{ marginBottom: 16, display: "flex", gap: 10, alignItems: "flex-start" }}>
                <span aria-hidden="true">ⓘ</span>
                <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  Eligibility and applicable conditions will be shown before confirmation.
                </span>
              </div>

              <button className="co-btn-primary" style={{ background: "var(--danger)", boxShadow: "none", marginBottom: 10 }}
                disabled={!canContinue} onClick={() => setStep("confirm")}>
                Continue to cancellation
              </button>
              <button className="co-btn-secondary" style={{ width: "100%" }} onClick={() => router.back()}>
                Keep my booking
              </button>
            </>
          ) : (
            <>
              <div className="co-card" style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
                  <span>Reason</span>
                  <span style={{ fontWeight: 600 }}>{REASON_LABELS[reason ?? ""] ?? reason}</span>
                </div>
                {elig.cancellation_fee == null && (
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
                    <span>Cancellation fee</span>
                    <span style={{ fontWeight: 600 }}>None</span>
                  </div>
                )}
              </div>

              <button className="co-btn-primary" style={{ background: "var(--danger)", boxShadow: "none", marginBottom: 10 }}
                disabled={busy} onClick={confirmCancel}>
                {busy ? "Cancelling…" : "Confirm cancellation"}
              </button>
              <button className="co-btn-secondary" style={{ width: "100%" }} disabled={busy} onClick={() => setStep("reason")}>
                Back
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
