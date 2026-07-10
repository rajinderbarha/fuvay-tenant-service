"use client";
import { useCallback } from "react";
import { adminFinancialEventsApi, type FinancialEventRecord } from "../../../lib/api";
import { Card, Badge, Btn, Skeleton } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { Activity, RefreshCw } from "lucide-react";

function eventVariant(t: string): "success" | "warning" | "danger" | "info" | "default" {
  if (t?.includes("deducted") || t?.includes("credited")) return "success";
  if (t?.includes("failed") || t?.includes("insufficient")) return "danger";
  if (t?.includes("issued") || t?.includes("created")) return "info";
  if (t?.includes("reversed")) return "warning";
  return "default";
}

export default function AdminFinancialEventsPage() {
  const { data, loading, refetch } = useApi(
    useCallback(() => adminFinancialEventsApi.list(), [])
  );

  const events: FinancialEventRecord[] = (Array.isArray(data) ? data : []) as FinancialEventRecord[];

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 24, maxWidth: 1100 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
            display: "flex", alignItems: "center", gap: 10 }}>
            <Activity size={22} /> Financial Events
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Append-only audit log of all financial events across invoices, payments, and commissions.
          </p>
        </div>
        <Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {[0,1,2,3,4].map(i => <Skeleton key={i} height={52} />)}
        </div>
      ) : events.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <Activity size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No financial events recorded yet.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {events.map((ev: FinancialEventRecord) => (
            <Card key={ev.id} padding={12}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <Badge variant={eventVariant(ev.event_type)}>{ev.event_type?.replace(/_/g, " ")}</Badge>
                  <div>
                    <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0 }}>
                      {ev.description ?? ev.event_type}
                    </p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                      Tenant: {ev.tenant_id?.slice(0, 8)} · Ref: {ev.reference_id?.slice(0, 8) ?? "—"}
                    </p>
                  </div>
                </div>
                <div style={{ textAlign: "right", fontSize: 11, color: "var(--text-tertiary)" }}>
                  {ev.amount && <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)", margin: 0 }}>{ev.amount}</p>}
                  <p style={{ margin: 0 }}>{ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
