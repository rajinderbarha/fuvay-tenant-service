"use client";
import { useEffect, useState } from "react";
import { providerMarketingApi, ProviderVisibilityStatus } from "../../../../lib/api";

function StatusBadge({ ok }: { ok: boolean }) {
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 600,
      background: ok ? "var(--success-bg)" : "var(--danger-bg)",
      color: ok ? "var(--success-text)" : "var(--danger-text)",
    }}>
      {ok ? "Active" : "Inactive"}
    </span>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "6px 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit",
};
const row: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "space-between",
  padding: "16px 24px", borderBottom: "1px solid var(--border)",
};

export default function VisibilityStatusPage() {
  const [status, setStatus] = useState<ProviderVisibilityStatus | null>(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    providerMarketingApi.getVisibilityStatus()
      .then(r => setStatus((r as any)?.data ?? r ?? null))
      .catch(() => setStatus(null))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Visibility Status</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Your current platform discoverability and marketing boost status</p>
        </div>
        <button onClick={load} disabled={loading} style={btnStyle}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
      ) : !status ? (
        <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-lg)", padding: 24, fontSize: 13, color: "var(--danger-text)" }}>
          Unable to load status. Please try again.
        </div>
      ) : (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
          <div style={row}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>Bookable</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                Customers can place bookings with you via the platform
              </div>
            </div>
            <StatusBadge ok={status.is_bookable} />
          </div>

          <div style={row}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>Visible in Search</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                Your profile appears in category and location search results
              </div>
            </div>
            <StatusBadge ok={status.is_visible} />
          </div>

          <div style={row}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>Visibility Boost</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                Admin-granted boost that increases your ranking in search results.
                Contact support to request a boost package.
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <StatusBadge ok={status.visibility_boost_active} />
              {status.visibility_boost_active && status.visibility_boost_expires_at && (
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>
                  Expires {new Date(status.visibility_boost_expires_at).toLocaleDateString()}
                </div>
              )}
            </div>
          </div>

          <div style={{ ...row, borderBottom: "none" }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>Account Status</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                Your overall provider account standing
              </div>
            </div>
            <span style={{ padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 600,
              background: "var(--surface-sunken)", color: "var(--text-secondary)", textTransform: "capitalize" }}>
              {status.provider_status}
            </span>
          </div>
        </div>
      )}

      <div style={{ background: "var(--info-bg)", border: "1px solid var(--info-border)", borderRadius:"var(--radius-lg)", padding: 16, fontSize: 13, color: "var(--info-text)" }}>
        <strong>Note:</strong> Visibility and bookable status are determined by the platform's
        eligibility engine based on your onboarding completion, subscription, offerings, and operating areas.
        Contact support if you believe your status is incorrect.
      </div>
    </div>
  );
}
