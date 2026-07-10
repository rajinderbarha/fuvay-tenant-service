"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, Bell } from "lucide-react";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import { getCustomerHomeServicesCatalog, CatalogCategory } from "../../../lib/api/customer-home-services";
import { getCustomerName, isLoggedIn } from "../../../lib/api/client";

export default function HomeServicesLandingPage() {
  const [categories, setCategories] = useState<CatalogCategory[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [search, setSearch] = useState("");
  const name = typeof window !== "undefined" ? getCustomerName() : null;

  useEffect(() => {
    getCustomerHomeServicesCatalog()
      .then((res) => setCategories(res.categories.filter((c) => c.is_customer_visible !== false)))
      .catch((e) => setError(e));
  }, []);

  const filtered = categories?.filter((c) => c.name.toLowerCase().includes(search.toLowerCase())) ?? [];

  return (
    <div className="co-container">
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0 16px" }}>
        <div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Good day{name ? "," : ""}</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{name || "Welcome"}</div>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Bell size={22} />
          <Link href="/customer/bookings" style={{ fontSize: 12, color: "var(--brand)", fontWeight: 600 }}>My Bookings</Link>
        </div>
      </div>

      {/* Search */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: "12px 16px", marginBottom: 20 }}>
        <Search size={18} color="var(--text-tertiary)" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search for a service..."
          style={{ border: "none", outline: "none", flex: 1, fontSize: 15, background: "transparent" }}
        />
      </div>

      <ErrorBanner error={error} />

      {/* Category cards */}
      {categories === null && !error && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="co-skeleton" style={{ height: 96 }} />)}
        </div>
      )}
      {categories !== null && filtered.length === 0 && (
        <div className="co-empty">No services found. Try a different search.</div>
      )}
      {filtered.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
          {filtered.map((c) => (
            <Link key={c.category_id} href={`/customer/home-services/book?category_id=${c.category_id}`} className="co-card" style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-start" }}>
              <div style={{ width: 40, height: 40, borderRadius: 12, background: "var(--info-bg)" }} />
              <div style={{ fontWeight: 600, fontSize: 14 }}>{c.name}</div>
            </Link>
          ))}
        </div>
      )}

      <BottomNav />
    </div>
  );
}
