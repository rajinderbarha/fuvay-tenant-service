"use client";
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Skeleton, EmptyState } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import { useTenant } from "../../../../hooks/useTenant";
import { providerOfferingsApi, tenantAutoPriceOptionsApi } from "../../../../lib/api";
import { Sparkles, CheckCircle2, XCircle } from "lucide-react";

const money = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN")}`;

function SectionError({ title, message: _message, requestId, onRetry }: {
  title: string; message?: string; requestId?: string | null; onRetry?: () => void;
}) {
  return (
    <Card>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--danger-text)", margin: "0 0 6px" }}>{title}</p>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 8px" }}>Retry or contact support with the request ID.</p>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px", fontFamily: "monospace" }}>
        {requestId && `Request ID: ${requestId}`}
      </p>
      {onRetry && <Btn size="sm" variant="secondary" onClick={onRetry}>Retry</Btn>}
    </Card>
  );
}

export default function CustomerPricePreviewPage() {
  const tenant = useTenant();
  const [selectedServiceId, setSelectedServiceId] = useState<string | null>(null);

  const enabled = useApi(useCallback(() => providerOfferingsApi.listEnabled(), []));
  const activeOffering = selectedServiceId
    ? enabled.data?.offerings.find(o => o.offering_id === selectedServiceId)
    : enabled.data?.offerings[0];
  const offeringId = activeOffering?.offering_id ?? null;

  const preview = useApi(
    () => offeringId ? tenantAutoPriceOptionsApi.getCustomerPricePreview(offeringId) : Promise.resolve(null),
    [offeringId],
  );
  const readiness = useApi(
    () => offeringId ? tenantAutoPriceOptionsApi.getMatchingReadiness(offeringId) : Promise.resolve(null),
    [offeringId],
  );

  // Home Services scope guard — same defense-in-depth pattern as My Offerings / Service Setup.
  if (tenant.vertical && tenant.vertical !== "home_services") {
    return (
      <TenantLayout activeNav="provider-services">
        <Card padding={32} style={{ textAlign: "center" }}>
          <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 6px" }}>
            Automatic price options are not available for this business type
          </p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Automatic Low/Mid/High price options are available only for Home Services.
          </p>
        </Card>
      </TenantLayout>
    );
  }

  return (
    <TenantLayout activeNav="provider-services">
      <div style={{ marginBottom: 16, padding: "10px 16px", borderRadius: 10,
        background: "var(--info-bg, #eff6ff)", border: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <p style={{ fontSize: 13, color: "var(--info-text, var(--brand-hover))", margin: 0 }}>
          This preview has moved into the Home Services setup flow.
        </p>
        <Link href="/tenant/setup/services" style={{
          fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", whiteSpace: "nowrap" }}>
          Go to Service Setup →
        </Link>
      </div>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>Customer Price Preview</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          See exactly what customers will see when ServiceOS selects you as the best-matched provider.
        </p>
      </div>

      <Card style={{ marginBottom: 20, background: "var(--info-bg, #eff6ff)" }}>
        <p style={{ fontSize: 12, color: "var(--info-text, var(--brand-hover))", margin: 0 }}>
          ServiceOS automatically creates customer price options from platform pricing and platform
          fee. You do not need to set up bargaining manually.
        </p>
      </Card>

      {enabled.loading ? (
        <Skeleton height={200}/>
      ) : enabled.error ? (
        <SectionError title="We couldn't load customer price preview" requestId={enabled.requestId} onRetry={enabled.refetch}/>
      ) : (enabled.data?.offerings ?? []).length === 0 ? (
        <EmptyState title="No services enabled yet" description="Enable a service from Service Setup to see its customer price preview."/>
      ) : (
        <>
          {(enabled.data?.offerings.length ?? 0) > 1 && (
            <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
              {enabled.data!.offerings.map(o => (
                <button key={o.provider_enabled_offering_id} onClick={() => setSelectedServiceId(o.offering_id)}
                  style={{
                    padding: "6px 14px", borderRadius:"var(--radius-md)", fontSize: 12, fontWeight: 600, cursor: "pointer",
                    border: "1px solid var(--border)",
                    background: offeringId === o.offering_id ? "var(--brand)" : "var(--surface)",
                    color: offeringId === o.offering_id ? "white" : "var(--text-primary)",
                  }}>
                  {o.provider_display_name || o.offering_name}
                </button>
              ))}
            </div>
          )}

          {preview.loading ? <Skeleton height={220}/> : preview.error ? (
            <SectionError title="We couldn't load customer price preview" requestId={preview.requestId} onRetry={preview.refetch}/>
          ) : !preview.data?.available ? (
            <Card padding={28} style={{ textAlign: "center" }}>
              <Sparkles size={26} style={{ color: "var(--text-tertiary)", margin: "0 auto 10px" }}/>
              <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px" }}>Price options not ready yet</p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                {preview.data?.message ?? "The platform has not configured a customer price range for this service yet."}
              </p>
            </Card>
          ) : (
            <Card>
              <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 4px" }}>
                {preview.data.service_name} {tenant.city ? `— ${tenant.city}` : ""}
              </p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px" }}>Customer will see:</p>
              <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
                <PriceTierCard label="Low" value={preview.data.low_price}/>
                <PriceTierCard label="Mid" value={preview.data.mid_price} highlight/>
                <PriceTierCard label="High" value={preview.data.high_price}/>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, padding: 14, borderRadius: 10, background: "var(--surface-sunken)" }}>
                <Row label="Payment" value="Customer pays provider directly after service."/>
                {preview.data.completed_job_deduction_credits != null && (
                  <Row label="After completion" value={`${preview.data.completed_job_deduction_credits} usage credits will be deducted.`}/>
                )}
              </div>
            </Card>
          )}

          <Card style={{ marginTop: 20 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Provider Matching Readiness</p>
            {readiness.loading ? <Skeleton height={40}/> : readiness.error ? (
              <SectionError title="Couldn't load matching readiness" requestId={readiness.requestId} onRetry={readiness.refetch}/>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {readiness.data?.matching_ready ? (
                  <CheckCircle2 size={18} style={{ color: "var(--success-text, var(--success))" }}/>
                ) : (
                  <XCircle size={18} style={{ color: "var(--danger-text)" }}/>
                )}
                <p style={{ fontSize: 12, margin: 0 }}>{readiness.data?.message}</p>
              </div>
            )}
          </Card>
        </>
      )}
    </TenantLayout>
  );
}

function PriceTierCard({ label, value, highlight }: { label: string; value?: number; highlight?: boolean }) {
  return (
    <div style={{
      flex: 1, padding: 14, borderRadius: 10, textAlign: "center",
      background: highlight ? "var(--brand-muted, rgba(37,99,235,0.08))" : "var(--surface-sunken)",
      border: highlight ? "1px solid var(--brand)" : "1px solid transparent",
    }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "0 0 4px" }}>{label}</p>
      <p style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{money(value)}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ fontSize: 12 }}>
      <span style={{ color: "var(--text-secondary)" }}>{label}: </span>
      <span style={{ fontWeight: 600 }}>{value}</span>
    </div>
  );
}
