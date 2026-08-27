"use client";
import { useEffect, useState } from "react";
import { adminAnalyticsApi } from "@/lib/api";
import { OperationalAlertList } from "@/components/analytics";
import { PageHeader } from "@serviceos/design-system";
import { Btn } from "@/components/shared/ui";

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
      <PageHeader
        title="Operational Alerts"
        description="Live platform health signals and conditions requiring administrator attention."
        eyebrow="Analytics"
        actions={<Btn variant="secondary" size="sm" onClick={load} loading={loading}>Refresh</Btn>}
      />

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
        <OperationalAlertList alerts={alerts} loading={loading} />
      </div>

      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
        Alerts refresh on page load. Critical alerts require immediate action.
      </div>
    </div>
  );
}
