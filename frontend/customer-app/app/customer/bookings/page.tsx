"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import { getCustomerBookings } from "../../../lib/api/customer-home-services";

type Filter = "active" | "completed" | "cancelled" | "all";

export default function BookingsListPage() {
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => {
    getCustomerBookings({ page: 1, page_size: 50 }).then((r) => setItems(r.items || [])).catch(setError);
  }, []);

  const filtered = (items || []).filter((b) => {
    if (filter === "all") return true;
    if (filter === "active") return !["completed", "cancelled"].includes(b.status);
    return b.status === filter;
  });

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>My Bookings</h1>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {(["active", "completed", "cancelled", "all"] as Filter[]).map((f) => (
          <button key={f} className={`co-chip ${filter === f ? "selected" : ""}`} onClick={() => setFilter(f)}>
            {f[0].toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      <ErrorBanner error={error} />
      {items === null && !error && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {Array.from({ length: 3 }).map((_, i) => <div key={i} className="co-skeleton" style={{ height: 80 }} />)}
        </div>
      )}
      {items !== null && filtered.length === 0 && (
        <div className="co-empty">
          <p>No bookings yet. Book your first home service.</p>
          <Link href="/customer/home-services/book" className="co-btn-primary" style={{ display: "inline-block", marginTop: 12 }}>Book Now</Link>
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {filtered.map((b) => (
          <Link key={b.booking_id} href={`/customer/bookings/${b.booking_id}`} className="co-card" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontWeight: 700 }}>{b.issue_summary || "Home Service"} — #{b.booking_number}</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{b.selected_provider?.provider_name || "Provider assigning"}</div>
            <div style={{ fontSize: 13 }}>Status: {b.status}</div>
            {b.selected_price_amount && <div style={{ fontSize: 13 }}>₹{b.selected_price_amount} ({b.selected_price_option})</div>}
          </Link>
        ))}
      </div>
      <BottomNav />
    </div>
  );
}
