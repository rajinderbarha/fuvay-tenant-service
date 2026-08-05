"use client";
/**
 * CANCEL-RESCHEDULE-FOUNDATION — Reschedule Visit.
 *
 * Date choices come from GET .../reschedule-availability (real day-level
 * capacity check, the same one the mutation itself enforces) — never a
 * hardcoded date/slot list. No canonical hour-level time-slot catalog
 * exists anywhere in this backend (booking creation itself only ever took
 * free text), so the time window stays a free-text field rather than an
 * invented fixed radio list.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import ErrorBanner from "../../../../../components/ErrorBanner";
import {
  getCustomerBookingDetail, getCancelRescheduleEligibility, getRescheduleAvailability,
  rescheduleCustomerBooking, newIdempotencyKey,
  CancelRescheduleEligibility, RescheduleAvailability,
} from "../../../../../lib/api/customer-home-services";

function fmt(d: string): string {
  const dt = new Date(d + "T00:00:00");
  return dt.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export default function RescheduleVisitPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = params.bookingId as string;

  const [detail, setDetail] = useState<any>(null);
  const [elig, setElig] = useState<CancelRescheduleEligibility | null>(null);
  const [avail, setAvail] = useState<RescheduleAvailability | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState<string | null>(null);

  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState("");
  const [step, setStep] = useState<"select" | "confirm">("select");
  const [reason, setReason] = useState("");
  const [idemKey] = useState(() => newIdempotencyKey());

  const load = useCallback(() => {
    getCustomerBookingDetail(bookingId).then(setDetail).catch(setError);
    getCancelRescheduleEligibility(bookingId).then(setElig).catch(setError);
    getRescheduleAvailability(bookingId).then(setAvail).catch(setError);
  }, [bookingId]);
  useEffect(() => { load(); }, [load]);

  async function confirm() {
    if (!selectedDate || !reason.trim() || !elig) return;
    setBusy(true); setError(null);
    try {
      const res = await rescheduleCustomerBooking(bookingId, {
        scheduled_date: selectedDate,
        scheduled_time_window: timeWindow.trim() || undefined,
        reason: reason.trim(),
        expected_version: elig.version,
      }, idemKey);
      setOk(`Rescheduled to ${fmt(res.scheduled_date)}${res.scheduled_time_window ? ` (${res.scheduled_time_window})` : ""}.`);
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  if (ok) {
    return (
      <div className="co-container">
        <div className="co-card" role="status" aria-live="polite" style={{ textAlign: "center", marginTop: 40 }}>
          <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>Visit rescheduled</div>
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
          onClick={() => (step === "confirm" ? setStep("select") : router.back())}>‹</button>
        <div style={{ flex: 1, textAlign: "center" }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Reschedule visit</div>
          {detail && <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{detail.issue_summary} · {detail.booking_number}</div>}
        </div>
        <div style={{ width: 44 }} />
      </div>

      <ErrorBanner error={error} />

      {!detail || !elig || !avail ? (
        !error && <div className="co-skeleton" style={{ height: 200 }} />
      ) : !elig.can_reschedule ? (
        <div className="co-card">This booking can no longer be rescheduled here. Please raise a complaint instead.</div>
      ) : step === "select" ? (
        <>
          <div className="co-card" style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
            <span>Current time</span>
            <span style={{ fontWeight: 600 }}>
              {detail.scheduled_date ?? "—"}{detail.scheduled_time_window ? ` · ${detail.scheduled_time_window}` : ""}
            </span>
          </div>

          <div style={{ fontWeight: 700, marginBottom: 8 }}>Choose a new date</div>
          <div style={{ display: "flex", gap: 8, overflowX: "auto", marginBottom: 16, paddingBottom: 4 }}>
            {avail.dates.map((d) => (
              <button key={d.date} disabled={!d.available}
                className="co-chip"
                aria-pressed={selectedDate === d.date}
                style={{
                  flexShrink: 0, opacity: d.available ? 1 : 0.4,
                  borderColor: selectedDate === d.date ? "var(--danger)" : undefined,
                  background: selectedDate === d.date ? "var(--danger)" : undefined,
                  color: selectedDate === d.date ? "#fff" : undefined,
                }}
                onClick={() => d.available && setSelectedDate(d.date)}>
                {fmt(d.date)}
              </button>
            ))}
          </div>
          {avail.dates.every((d) => !d.available) && (
            <div className="co-card" style={{ marginBottom: 16 }}>
              No available dates in the next two weeks. Please try again later or keep your current visit.
            </div>
          )}

          <label style={{ display: "block", fontWeight: 700, marginBottom: 8 }} htmlFor="time-window">
            Preferred time (optional)
          </label>
          <input id="time-window" type="text" value={timeWindow} onChange={(e) => setTimeWindow(e.target.value)}
            placeholder="e.g. 10am–12pm"
            style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)",
              fontSize: 15, marginBottom: 16 }} />

          <div className="co-card" style={{ marginBottom: 16, display: "flex", gap: 10, alignItems: "flex-start" }}>
            <span aria-hidden="true">ⓘ</span>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Availability and eligibility are confirmed before submission.
            </span>
          </div>

          <button className="co-btn-primary" style={{ background: "var(--danger)", boxShadow: "none", marginBottom: 10 }}
            disabled={!selectedDate} onClick={() => setStep("confirm")}>
            Continue with new time
          </button>
          <button className="co-btn-secondary" style={{ width: "100%" }} onClick={() => router.back()}>
            Keep current visit
          </button>
        </>
      ) : (
        <>
          <div className="co-card" style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
              <span>Current</span>
              <span style={{ fontWeight: 600 }}>{detail.scheduled_date ?? "—"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
              <span>New</span>
              <span style={{ fontWeight: 600 }}>{fmt(selectedDate!)}{timeWindow ? ` · ${timeWindow}` : ""}</span>
            </div>
          </div>

          <label style={{ display: "block", fontWeight: 700, marginBottom: 8 }} htmlFor="reschedule-reason">
            Reason for rescheduling
          </label>
          <textarea id="reschedule-reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={2}
            placeholder="Required"
            style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)",
              fontSize: 15, marginBottom: 16 }} />

          <button className="co-btn-primary" style={{ background: "var(--danger)", boxShadow: "none", marginBottom: 10 }}
            disabled={!reason.trim() || busy} onClick={confirm}>
            {busy ? "Confirming…" : "Confirm reschedule"}
          </button>
          <button className="co-btn-secondary" style={{ width: "100%" }} disabled={busy} onClick={() => setStep("select")}>
            Back
          </button>
        </>
      )}
    </div>
  );
}
