"use client";
/**
 * CANCEL-RESCHEDULE-FOUNDATION — Manage Booking entry screen.
 *
 * Everything here is driven by GET .../cancel-reschedule-eligibility — this
 * screen never guesses whether cancel/reschedule is allowed from a locally
 * mirrored status set; it renders exactly what the backend says, including
 * the block reason when an action isn't available.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ErrorBanner from "../../../../../components/ErrorBanner";
import {
  getCustomerBookingDetail, getCancelRescheduleEligibility, CancelRescheduleEligibility,
} from "../../../../../lib/api/customer-home-services";

const BLOCK_REASON_LABELS: Record<string, string> = {
  booking_not_in_cancellable_state: "This booking has progressed too far to cancel here — please raise a complaint instead.",
  booking_not_in_reschedulable_state: "This booking has progressed too far to reschedule here — please raise a complaint instead.",
  reschedule_limit_reached: "You've used all your reschedules for this booking.",
};

export default function ManageBookingPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = params.bookingId as string;

  const [detail, setDetail] = useState<any>(null);
  const [elig, setElig] = useState<CancelRescheduleEligibility | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    getCustomerBookingDetail(bookingId).then(setDetail).catch(setError);
    getCancelRescheduleEligibility(bookingId).then(setElig).catch(setError);
  }, [bookingId]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 0" }}>
        <button aria-label="Back" className="co-btn-secondary" style={{ minWidth: 44, minHeight: 44, padding: 0 }}
          onClick={() => router.back()}>‹</button>
        <div style={{ flex: 1, textAlign: "center" }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Manage booking</div>
          {detail && (
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              {detail.issue_summary} · {detail.booking_number}
            </div>
          )}
        </div>
        <div style={{ width: 44 }} />
      </div>

      <ErrorBanner error={error} />

      {!detail || !elig ? (
        !error && <div className="co-skeleton" style={{ height: 160, marginBottom: 16 }} />
      ) : (
        <>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Current visit</div>
          <div className="co-card" style={{ marginBottom: 16, display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
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

          <div className="co-card" style={{ marginBottom: 16, padding: 0 }}>
            {elig.can_reschedule ? (
              <Link href={`/customer/bookings/${bookingId}/reschedule-visit`}
                style={{ display: "flex", alignItems: "center", gap: 12, padding: 16, borderBottom: "1px solid var(--border)" }}>
                <span aria-hidden="true" style={{ fontSize: 20 }}>🗓️</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700 }}>Reschedule visit</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Choose another available time.</div>
                </div>
                <span aria-hidden="true">›</span>
              </Link>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 16, borderBottom: "1px solid var(--border)", opacity: 0.5 }}>
                <span aria-hidden="true" style={{ fontSize: 20 }}>🗓️</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700 }}>Reschedule visit</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                    {BLOCK_REASON_LABELS[elig.reschedule_block_reason ?? ""] ?? "Not available for this booking right now."}
                  </div>
                </div>
              </div>
            )}
            {elig.can_cancel ? (
              <Link href={`/customer/bookings/${bookingId}/cancel-booking`}
                style={{ display: "flex", alignItems: "center", gap: 12, padding: 16 }}>
                <span aria-hidden="true" style={{ fontSize: 20 }}>⊗</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700 }}>Cancel booking</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Review eligibility and cancellation details.</div>
                </div>
                <span aria-hidden="true">›</span>
              </Link>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 16, opacity: 0.5 }}>
                <span aria-hidden="true" style={{ fontSize: 20 }}>⊗</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700 }}>Cancel booking</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                    {BLOCK_REASON_LABELS[elig.cancel_block_reason ?? ""] ?? "Not available for this booking right now."}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="co-card" style={{ marginBottom: 16, display: "flex", gap: 10, alignItems: "flex-start" }}>
            <span aria-hidden="true">ⓘ</span>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Eligibility and applicable conditions are checked before confirmation.
            </span>
          </div>

          <div style={{ textAlign: "center" }}>
            <button className="co-btn-secondary" style={{ border: "none", color: "var(--danger)", background: "transparent" }}
              onClick={() => router.push(`/customer/bookings/${bookingId}`)}>
              Keep current booking
            </button>
          </div>
        </>
      )}
    </div>
  );
}
