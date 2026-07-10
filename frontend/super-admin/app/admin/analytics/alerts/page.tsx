"use client";
import { useEffect, useState } from "react";
import { adminAnalyticsApi } from "@/lib/api";
import { OperationalAlertList } from "@/components/analytics";

const btnStyle: React.CSSProperties = {
  padding: "6px 12px", fontSize: 13, border: "1px solid var(--border)",
  borderRadius: 8, background: "var(--surface)", color: "var(--text-secondary)",
  cursor: "pointer", fontFamily: "inherit",
};

export default function AlertsPage() {
  const [alerts, setAlerts]   = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAnalyticsApi.getOperationalAlerts();
      setAlerts(r?.breakdown ?? []);
    } catch { setAlerts([]); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Operational Alerts</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Live platform health signals</p>
        </div>
        <button onClick={load} disabled={loading} style={btnStyle}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 20 }}>
        <OperationalAlertList alerts={alerts} loading={loading} />
      </div>

      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
        Alerts refresh on page load. Critical alerts require immediate action.
      </div>
    </div>
  );
}
