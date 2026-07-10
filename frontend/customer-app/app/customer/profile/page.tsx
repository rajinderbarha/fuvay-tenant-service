"use client";
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
      <button className="co-btn-secondary" onClick={customerLogout}>Log Out</button>
      <BottomNav />
    </div>
  );
}
