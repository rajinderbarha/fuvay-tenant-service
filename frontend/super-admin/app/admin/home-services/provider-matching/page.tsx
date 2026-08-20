"use client";
import React, { useCallback } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Skeleton } from "../../../../components/shared/ui";
import { autoPriceOptionsApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { CheckCircle2, XCircle, Search, ShieldCheck } from "lucide-react";

function SectionError({ title, message, requestId, onRetry }: {
  title: string; message: string; requestId?: string | null; onRetry?: () => void;
}) {
  return (
    <Card>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--danger-text)", margin: "0 0 6px" }}>{title}</p>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 8px" }}>{message}</p>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px", fontFamily: "monospace" }}>
        {requestId && `Request ID: ${requestId}`}
      </p>
      {onRetry && <Btn size="sm" variant="secondary" onClick={onRetry}>Retry</Btn>}
    </Card>
  );
}

export default function ProviderMatchingPage() {
  const config = useApi(useCallback(() => autoPriceOptionsApi.getConfig(), []));
  const policy = useApi(useCallback(() => autoPriceOptionsApi.getMatchingPolicy(), []));

  return (
    <AdminLayout activeNav="bookability">
      <SectionHeader
        title="Booking Match Policy"
        subtitle="Fuvay selects the best eligible Home Services provider from tenant-owned service areas, bookability, availability, finance, and Trust & Quality signals."
      />

      <Card style={{ marginBottom: 20 }}>
        {config.loading ? <Skeleton height={60}/> : config.error ? (
          <SectionError title="Couldn't load configuration" message={config.error} requestId={config.requestId} onRetry={config.refetch}/>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
            <StatusRow label="Provider-first booking" enabled={config.data?.provider_first_matching_enabled ?? true}/>
            <StatusRow label="Customer manual provider selection" enabled={false} invert label2="Disabled for this flow"/>
            <div>
              <p style={{ fontSize: 11, color: "var(--muted-text)", textTransform: "uppercase", margin: "0 0 4px" }}>Scope</p>
              <Badge variant="info">Home Services only</Badge>
            </div>
          </div>
        )}
      </Card>

      <Card style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px" }}>Ranking Factors</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px" }}>
          When more than one provider is eligible, Fuvay ranks them using this weighted score.
          Provider eligibility itself is a hard gate (bookable, coverage, technician, availability,
          pricing, package, credits, deposit) — only eligible providers are ever scored.
        </p>
        {policy.loading ? <Skeleton height={112}/> : policy.error ? (
          <SectionError title="Couldn't load matching policy" message={policy.error} requestId={policy.requestId} onRetry={policy.refetch}/>
        ) : (
          <>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
              <Badge variant="info">Policy v{policy.data?.version ?? "—"}</Badge>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-tertiary)" }}>
                <ShieldCheck size={13}/> Platform-governed scoring policy
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
              {(policy.data?.factors ?? []).map(w => (
                <div key={w.factor_key} style={{ padding: 14, borderRadius: 10, background: "var(--surface-sunken)", textAlign: "center", border: "1px solid var(--border)" }}>
                  <p style={{ fontSize: 20, fontWeight: 800, margin: "0 0 2px" }}>{Math.round(Number(w.weight) * 100)}%</p>
                  <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0 }}>{w.label}</p>
                  <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "3px 0 0" }}>{w.source_engine}</p>
                </div>
              ))}
            </div>
          </>
        )}
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "12px 0 0" }}>
          Fair distribution / anti-monopoly rotation: ties are broken deterministically, and repeated
          selection is naturally dampened by the Capacity factor (open-job load vs. active technicians).
        </p>
      </Card>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link href="/admin/home-services/matching-diagnostics">
          <Btn size="sm" variant="primary"><Search size={13} style={{ marginRight: 4 }}/>Preview Match</Btn>
        </Link>
        <Link href="/admin/home-services/matching-diagnostics">
          <Btn size="sm" variant="secondary"><Search size={13} style={{ marginRight: 4 }}/>View Diagnostics</Btn>
        </Link>
      </div>
    </AdminLayout>
  );
}

function StatusRow({ label, enabled, invert, label2 }: { label: string; enabled: boolean; invert?: boolean; label2?: string }) {
  const good = invert ? !enabled : enabled;
  return (
    <div>
      <p style={{ fontSize: 11, color: "var(--muted-text)", textTransform: "uppercase", margin: "0 0 4px" }}>{label}</p>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {good ? <CheckCircle2 size={16} style={{ color: "var(--success-text, var(--success))" }}/> : <XCircle size={16} style={{ color: "var(--danger-text)" }}/>}
        <span style={{ fontSize: 14, fontWeight: 700 }}>{label2 ?? (enabled ? "Enabled" : "Disabled")}</span>
      </div>
    </div>
  );
}
