"use client";
import Link from "next/link";
import BottomNav from "../../../components/BottomNav";
import { getCustomerName, getCustomerId } from "../../../lib/api/client";
import { customerLogout } from "../../../lib/api/auth";

export default function ProfilePage() {
  const name = typeof window !== "undefined" ? getCustomerName() : null;
  const id = typeof window !== "undefined" ? getCustomerId() : null;

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>Profile</h1>
      <div className="co-card" style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
        <div style={{ fontWeight: 700 }}>{name || "Customer"}</div>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>ID: {id}</div>
      </div>
      {/* MODULE-L5-02/L5-10/L5-11: surfaces that exist in the backend but had no
          reachable home in the app. Give them permanent entries here. */}
      <div className="co-card" style={{ marginBottom: 16, padding: 0 }}>
        <Link href="/customer/notifications"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                   padding: "14px 16px", textDecoration: "none", color: "inherit",
                   borderBottom: "1px solid #f0f0f0" }}>
          <span style={{ fontWeight: 600 }}>Notifications</span>
          <span style={{ color: "var(--text-tertiary)" }}>›</span>
        </Link>
        <Link href="/customer/complaints"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                   padding: "14px 16px", textDecoration: "none", color: "inherit" }}>
          <span style={{ fontWeight: 600 }}>My Complaints</span>
          <span style={{ color: "var(--text-tertiary)" }}>›</span>
        </Link>
      </div>
      <button className="co-btn-secondary" onClick={customerLogout}>Log Out</button>
      <BottomNav />
    </div>
  );
}
