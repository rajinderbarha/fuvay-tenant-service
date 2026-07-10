"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ErrorBanner from "../../../../../components/ErrorBanner";
import { getCustomerBookingDetail, getCustomerBookingReview, submitCustomerBookingReview } from "../../../../../lib/api/customer-home-services";

export default function RateBookingPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = params.bookingId as string;
  const [booking, setBooking] = useState<any>(null);
  const [existingReview, setExistingReview] = useState<any>(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    getCustomerBookingDetail(bookingId).then(setBooking).catch(setError);
    getCustomerBookingReview(bookingId).then((r) => setExistingReview(r.review)).catch(() => {});
  }, [bookingId]);

  async function handleSubmit() {
    if (rating < 1 || rating > 5) { setError(new Error("Please select a rating from 1 to 5.")); return; }
    setLoading(true); setError(null);
    try {
      await submitCustomerBookingReview(bookingId, { rating, comment: comment || undefined });
      setSubmitted(true);
    } catch (e) { setError(e); } finally { setLoading(false); }
  }

  if (booking && booking.status !== "completed" && !submitted && !existingReview) {
    return (
      <div className="co-container">
        <div className="co-card">You can review this service after it is completed.</div>
      </div>
    );
  }

  if (existingReview || submitted) {
    return (
      <div className="co-container">
        <div className="co-card" style={{ textAlign: "center" }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Thanks for your feedback!</div>
          <div>A review has already been submitted for this booking.</div>
          <button className="co-btn-secondary" style={{ marginTop: 16 }} onClick={() => router.push(`/customer/bookings/${bookingId}`)}>Back to Booking</button>
        </div>
      </div>
    );
  }

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>Rate Your Experience</h1>
      <ErrorBanner error={error} />
      <div className="co-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} onClick={() => setRating(n)} style={{ fontSize: 32, background: "none", border: "none", cursor: "pointer", color: n <= rating ? "var(--accent)" : "var(--border-strong)" }}>★</button>
          ))}
        </div>
        <textarea placeholder="Comment (optional)" value={comment} onChange={(e) => setComment(e.target.value)} rows={4}
          style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
        <button className="co-btn-primary" disabled={loading} onClick={handleSubmit}>{loading ? "Submitting..." : "Submit"}</button>
      </div>
    </div>
  );
}
