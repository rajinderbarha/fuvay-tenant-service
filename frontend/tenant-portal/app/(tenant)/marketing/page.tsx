"use client";
import { useEffect, useState } from "react";
import { providerMarketingApi, ProviderVisibilityStatus } from "../../../lib/api";
import Link from "next/link";

export default function MarketingOverviewPage() {
  const [status, setStatus] = useState<ProviderVisibilityStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    providerMarketingApi.getVisibilityStatus()
      .then(r => setStatus((r as any)?.data ?? r ?? null))
      .catch(() => setStatus(null))
      .finally(() => setLoading(false));
  }, []);

  const cards = [
    { label: "Visibility Status",  href: "/marketing/visibility",       desc: "See your current bookable/visible state and boost expiry" },
    { label: "Campaign Impact",    href: "/marketing/campaign-impact",  desc: "Events from platform campaigns that targeted your profile" },
    { label: "Attributed Leads",   href: "/marketing/leads-attributed", desc: "Bookings and leads converted via marketing campaigns" },
  ];

  const statusVal = (ok: boolean | undefined) => (
    <span style={{ fontSize: 13, fontWeight: 600, color: ok ? "var(--success-text)" : "var(--danger-text)" }}>
      {ok ? "Yes" : "No"}
    </span>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Marketing</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Your marketing visibility and campaign reach on the platform
        </p>
      </div>

      {loading ? (
        <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 12, padding: 16, fontSize: 13, color: "var(--text-tertiary)" }}>
          Loading status…
        </div>
      ) : status ? (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 20,
          display: "flex", flexWrap: "wrap", gap: 24 }}>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2 }}>Bookable</div>
            {statusVal(status.is_bookable)}
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2 }}>Visible in Search</div>
            {statusVal(status.is_visible)}
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2 }}>Visibility Boost</div>
            <span style={{ fontSize: 13, fontWeight: 600, color: status.visibility_boost_active ? "var(--accent)" : "var(--text-tertiary)" }}>
              {status.visibility_boost_active
                ? `Active · Expires ${status.visibility_boost_expires_at ? new Date(status.visibility_boost_expires_at).toLocaleDateString() : "—"}`
                : "Inactive"}
            </span>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2 }}>Account Status</div>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", textTransform: "capitalize" }}>
              {status.provider_status}
            </span>
          </div>
        </div>
      ) : (
        <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 12, padding: 16, fontSize: 13, color: "var(--danger-text)" }}>
          Unable to load visibility status. Please try again.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 16 }}>
        {cards.map(c => (
          <Link key={c.href} href={c.href} style={{
            display: "block", background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 12, padding: 20, textDecoration: "none",
          }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>{c.label}</div>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 12 }}>{c.desc}</div>
            <div style={{ fontSize: 11, color: "var(--accent)" }}>View →</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
