"use client";
import { useCallback } from "react";
import { providerSubscriptionApi } from "../../../../lib/api";
import { Card, Badge, Btn, Skeleton } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import { Star, RefreshCw, AlertCircle, CheckCircle2 } from "lucide-react";

interface SubStatus {
  tenant_id: string;
  status: string;
  plan_type?: string;
  billing_cycle?: string;
  amount?: string;
  currency?: string;
  is_active: boolean;
  current_period_start?: string;
  expires_at?: string;
  expiring_soon?: boolean;
  renewal_required?: boolean;
}

export default function ProviderSubscriptionStatusPage() {
  const { data, loading, refetch } = useApi(
    useCallback(() => providerSubscriptionApi.getStatus(), [])
  );

  const sub = (data as unknown) as SubStatus | null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 700 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
            display: "flex", alignItems: "center", gap: 10 }}>
            <Star size={22} /> Subscription Status
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Your active plan and renewal information.
          </p>
        </div>
        <Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>
      </div>

      {loading ? (
        <Skeleton height={140} />
      ) : !sub ? (
        <Card padding={32} style={{ textAlign: "center" }}>
          <p style={{ color: "var(--text-tertiary)", margin: 0 }}>No subscription data available.</p>
        </Card>
      ) : (
        <Card padding={20}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            {sub.is_active
              ? <CheckCircle2 size={24} style={{ color: "var(--success)" }} />
              : <AlertCircle size={24} style={{ color: "var(--danger)" }} />}
            <div>
              <p style={{ fontWeight: 600, fontSize: 16, color: "var(--text-primary)", margin: 0 }}>
                {sub.is_active ? "Active Subscription" : "Subscription Inactive"}
              </p>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                {sub.plan_type ?? "—"} · {sub.billing_cycle ?? "—"}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-tertiary)" }}>Status</span>
              <Badge variant={sub.is_active ? "success" : "danger"}>{sub.status?.replace(/_/g, " ") ?? "—"}</Badge>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-tertiary)" }}>Amount</span>
              <span style={{ fontWeight: 500 }}>{sub.amount ?? "—"} {sub.currency ?? ""}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-tertiary)" }}>Period Start</span>
              <span>{sub.current_period_start ? new Date(sub.current_period_start).toLocaleDateString() : "—"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-tertiary)" }}>Expires At</span>
              <span>{sub.expires_at ? new Date(sub.expires_at).toLocaleDateString() : "—"}</span>
            </div>
          </div>

          {sub.expiring_soon && (
            <div style={{ display: "flex", alignItems: "flex-start", gap: 8, background: "var(--warning-bg)",
              borderRadius:"var(--radius-md)", padding: "10px 12px", fontSize: 13, color: "var(--warning-text)", marginTop: 16 }}>
              <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
              <span>Your subscription expires soon. Please renew to continue receiving bookings.</span>
            </div>
          )}

          {!sub.is_active && sub.status !== "no_subscription" && (
            <div style={{ display: "flex", alignItems: "flex-start", gap: 8, background: "var(--danger-bg)",
              borderRadius:"var(--radius-md)", padding: "10px 12px", fontSize: 13, color: "var(--danger-text)", marginTop: 16 }}>
              <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
              <span>Subscription is not active. Contact admin to reactivate.</span>
            </div>
          )}

          {sub.status === "no_subscription" && (
            <div style={{ display: "flex", alignItems: "flex-start", gap: 8, background: "var(--surface-sunken)",
              borderRadius:"var(--radius-md)", padding: "10px 12px", fontSize: 13, color: "var(--text-secondary)", marginTop: 16 }}>
              <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
              <span>No subscription found. Contact admin to set up your plan.</span>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
