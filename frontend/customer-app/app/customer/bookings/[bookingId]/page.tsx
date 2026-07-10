"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import BottomNav from "../../../../components/BottomNav";
import ErrorBanner from "../../../../components/ErrorBanner";
import { getCustomerBookingDetail, getCustomerBookingTracking } from "../../../../lib/api/customer-home-services";

export default function BookingDetailPage() {
  const params = useParams();
  const bookingId = params.bookingId as string;
  const [detail, setDetail] = useState<any>(null);
  const [tracking, setTracking] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    getCustomerBookingDetail(bookingId).then(setDetail).catch(setError);
    getCustomerBookingTracking(bookingId).then(setTracking).catch(() => {});
  }, [bookingId]);

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>Booking Details</h1>
      <ErrorBanner error={error} />
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
          {detail.status === "completed" && (
            <Link href={`/customer/bookings/${bookingId}/rate`} className="co-btn-primary" style={{ textAlign: "center" }}>Rate Your Experience</Link>
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
      <BottomNav />
    </div>
  );
}
