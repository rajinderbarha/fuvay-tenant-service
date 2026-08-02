"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Input, SectionHeader, Skeleton } from "../../../../components/shared/ui";
import { autoPriceOptionsApi, type PriceExperiencePreviewResult } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Sparkles, CheckCircle2, XCircle } from "lucide-react";

const money = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN")}`;

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

const BLANK_FORM = {
  service_name: "AC Repair", admin_min_price: "300", admin_max_price: "500", admin_base_price: "400",
  selected_min_price: "350", selected_max_price: "420", platform_fee_percent: "10",
};

export default function CustomerPriceExperiencePage() {
  const [form, setForm] = useState(BLANK_FORM);
  const [result, setResult] = useState<PriceExperiencePreviewResult | null>(null);

  const config = useApi(useCallback(() => autoPriceOptionsApi.getConfig(), []));

  const previewAction = useAction(useCallback(async () => {
    return autoPriceOptionsApi.previewPriceExperience({
      service_name: form.service_name || undefined,
      admin_min_price: form.admin_min_price ? Number(form.admin_min_price) : undefined,
      admin_max_price: form.admin_max_price ? Number(form.admin_max_price) : undefined,
      admin_base_price: form.admin_base_price ? Number(form.admin_base_price) : undefined,
      selected_min_price: Number(form.selected_min_price),
      selected_max_price: Number(form.selected_max_price),
      platform_fee_percent: form.platform_fee_percent ? Number(form.platform_fee_percent) : undefined,
    });
  }, [form]));

  async function handlePreview() {
    const r = await previewAction.execute();
    if (r) setResult(r);
  }

  return (
    <AdminLayout activeNav="hs-price-experience">
      <SectionHeader
        title="Customer Price Experience"
        subtitle="Preview how customers see Low, Mid, and High price choices after ServiceOS selects the best Home Services provider."
      />

      {/* Hero */}
      <Card style={{ marginBottom: 20 }}>
        {config.loading ? <Skeleton height={80}/> : config.error ? (
          <SectionError title="Couldn't load configuration" message={config.error} requestId={config.requestId} onRetry={config.refetch}/>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            <ConfigStat label="Automatic Price Options" enabled={config.data?.auto_price_options_enabled ?? true}/>
            <ConfigStat label="Manual Bargain Rules" enabled={config.data?.manual_bargain_rules_enabled ?? false} invert/>
            <ConfigStat label="Provider-First Matching" enabled={config.data?.provider_first_matching_enabled ?? true}/>
            <div>
              <p style={{ fontSize: 11, color: "var(--muted-text)", textTransform: "uppercase", margin: "0 0 4px" }}>Scope</p>
              <Badge variant="info">Home Services only</Badge>
            </div>
          </div>
        )}
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "14px 0 0" }}>
          <strong>Customer Low Rule:</strong> platform fee is applied to the entire Selected Range —
          both its minimum <em>and</em> its maximum. Admin never sees a pre-fee price presented as
          "Low" or "High".
        </p>
      </Card>

      {/* Preview Panel */}
      <Card style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px" }}>Price Preview</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px" }}>
          Test how Low/Mid/High are computed for any Admin Allowed Range + Selected Range + platform fee combination.
          The Selected Range must stay inside the Admin Allowed Range.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, marginBottom: 12 }}>
          <Input label="Service Name" value={form.service_name} onChange={v => setForm(f => ({ ...f, service_name: v }))}/>
          <Input label="Admin Allowed Min (₹)" type="number" value={form.admin_min_price} onChange={v => setForm(f => ({ ...f, admin_min_price: v }))}/>
          <Input label="Admin Allowed Max (₹)" type="number" value={form.admin_max_price} onChange={v => setForm(f => ({ ...f, admin_max_price: v }))}/>
          <Input label="Admin Base Price (₹)" type="number" value={form.admin_base_price} onChange={v => setForm(f => ({ ...f, admin_base_price: v }))}/>
          <Input label="Selected Range Min (₹)" type="number" value={form.selected_min_price} onChange={v => setForm(f => ({ ...f, selected_min_price: v }))}/>
          <Input label="Selected Range Max (₹)" type="number" value={form.selected_max_price} onChange={v => setForm(f => ({ ...f, selected_max_price: v }))}/>
          <Input label="Platform Fee %" type="number" value={form.platform_fee_percent} onChange={v => setForm(f => ({ ...f, platform_fee_percent: v }))}/>
        </div>
        <Btn size="sm" variant="primary" loading={previewAction.loading} onClick={handlePreview}>
          <Sparkles size={13} style={{ marginRight: 4 }}/>Preview Price Options
        </Btn>

        {previewAction.error && (
          <div style={{ marginTop: 12 }}>
            <SectionError title="Preview failed" message={previewAction.error} requestId={previewAction.requestId}/>
          </div>
        )}

        {result && (
          <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div style={{ display: "flex", gap: 10 }}>
              <PriceTierCard label="Low" value={result.customer_low_price} hint="Minimum customer-visible price"/>
              <PriceTierCard label="Mid" value={result.customer_mid_price} hint="Recommended fair price" highlight/>
              <PriceTierCard label="High" value={result.customer_high_price} hint="Maximum customer-visible price"/>
            </div>
            <div style={{ padding: 14, borderRadius: 10, background: "var(--surface-sunken)" }}>
              <p style={{ fontSize: 12, fontWeight: 700, margin: "0 0 8px" }}>Breakdown</p>
              <Row label="Selected Range Minimum" value={money(result.selected_min_price)}/>
              <Row label="Selected Range Maximum" value={money(result.selected_max_price)}/>
              <Row label="Platform Fee on Minimum" value={money(result.platform_fee_on_min)}/>
              <Row label="Platform Fee on Maximum" value={money(result.platform_fee_on_max)}/>
              <Row label="Customer Low" value={money(result.customer_low_price)} strong/>
              <Row label="Customer Mid" value={money(result.customer_mid_price)} strong/>
              <Row label="Customer High" value={money(result.customer_high_price)} strong/>
              <Row label="Payment Mode" value="Customer pays provider directly"/>
            </div>
          </div>
        )}
      </Card>
    </AdminLayout>
  );
}

function ConfigStat({ label, enabled, invert }: { label: string; enabled: boolean; invert?: boolean }) {
  const good = invert ? !enabled : enabled;
  return (
    <div>
      <p style={{ fontSize: 11, color: "var(--muted-text)", textTransform: "uppercase", margin: "0 0 4px" }}>{label}</p>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {good ? <CheckCircle2 size={16} style={{ color: "var(--success-text, var(--success))" }}/> : <XCircle size={16} style={{ color: "var(--danger-text)" }}/>}
        <span style={{ fontSize: 14, fontWeight: 700 }}>{enabled ? "Enabled" : "Disabled"}</span>
      </div>
    </div>
  );
}

function PriceTierCard({ label, value, hint, highlight }: { label: string; value: number; hint: string; highlight?: boolean }) {
  return (
    <div style={{
      flex: 1, padding: 14, borderRadius: 10, textAlign: "center",
      background: highlight ? "var(--brand-muted, rgba(37,99,235,0.08))" : "var(--surface-sunken)",
      border: highlight ? "1px solid var(--brand)" : "1px solid transparent",
    }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", margin: "0 0 4px" }}>{label}</p>
      <p style={{ fontSize: 20, fontWeight: 800, margin: "0 0 2px" }}>{money(value)}</p>
      <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: 0 }}>{hint}</p>
    </div>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 12 }}>
      <span style={{ color: "var(--text-secondary)" }}>{label}</span>
      <span style={{ fontWeight: strong ? 700 : 500 }}>{value}</span>
    </div>
  );
}
