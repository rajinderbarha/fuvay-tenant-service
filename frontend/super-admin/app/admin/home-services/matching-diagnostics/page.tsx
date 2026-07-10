"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Input, SectionHeader } from "../../../../components/shared/ui";
import { autoPriceOptionsApi, type MatchingDiagnosticsResult } from "../../../../lib/api";
import { useAction } from "../../../../hooks/useApi";
import { Search, CheckCircle2, XCircle } from "lucide-react";

const money = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN")}`;

const BLANK_FORM = {
  category_id: "0888d283-9a52-4d7b-8612-9f47fa8357a1",
  master_service_id: "a96e625a-60e1-46c0-bde4-ccbb88da50a2",
  city: "Ludhiana", zipcode: "141001", offering_type_id: "", brand_id: "",
};

export default function MatchingDiagnosticsPage() {
  const [form, setForm] = useState(BLANK_FORM);
  const [result, setResult] = useState<MatchingDiagnosticsResult | null>(null);

  const runAction = useAction(useCallback(async () => {
    return autoPriceOptionsApi.runMatchingDiagnostics({
      category_id: form.category_id, master_service_id: form.master_service_id,
      city: form.city, zipcode: form.zipcode || undefined,
      offering_type_id: form.offering_type_id || undefined, brand_id: form.brand_id || undefined,
    });
  }, [form]));

  async function handleRun() {
    const r = await runAction.execute();
    if (r) setResult(r);
  }

  return (
    <AdminLayout activeNav="hs-matching-diagnostics">
      <SectionHeader
        title="Matching Diagnostics"
        subtitle="Run provider-first matching for any service/area combination and see exactly why a provider was selected — or why nobody was eligible."
      />

      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, marginBottom: 12 }}>
          <Input label="Category ID" value={form.category_id} onChange={v => setForm(f => ({ ...f, category_id: v }))}/>
          <Input label="Master Service ID" value={form.master_service_id} onChange={v => setForm(f => ({ ...f, master_service_id: v }))}/>
          <Input label="City" value={form.city} onChange={v => setForm(f => ({ ...f, city: v }))}/>
          <Input label="Zipcode" value={form.zipcode} onChange={v => setForm(f => ({ ...f, zipcode: v }))}/>
          <Input label="Type ID (optional)" value={form.offering_type_id} onChange={v => setForm(f => ({ ...f, offering_type_id: v }))}/>
          <Input label="Brand ID (optional)" value={form.brand_id} onChange={v => setForm(f => ({ ...f, brand_id: v }))}/>
        </div>
        <Btn size="sm" variant="primary" loading={runAction.loading} onClick={handleRun}>
          <Search size={13} style={{ marginRight: 4 }}/>Run Diagnostics
        </Btn>
        {runAction.error && (
          <p style={{ fontSize: 12, color: "var(--danger-text)", marginTop: 10 }}>
            {runAction.error}{runAction.requestId && ` — Request ID: ${runAction.requestId}`}
          </p>
        )}
      </Card>

      {result && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
            <MiniStat label="Eligible Providers" value={result.eligible_provider_count}/>
            <MiniStat label="Candidate Pool" value={result.candidate_provider_count}/>
            <MiniStat label="Excluded" value={result.excluded_provider_count} danger={result.excluded_provider_count > 0}/>
          </div>

          {/* HS6B — canonical sources this run used */}
          <Card style={{ marginBottom: 20 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Canonical Sources</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8, fontSize: 12 }}>
              <div><span style={{ color: "var(--text-tertiary)" }}>Bookability Source:</span> {result.bookability_source}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Area Coverage Source:</span> {result.area_coverage_source}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Availability Source:</span> {result.availability_source}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Pricing Source:</span> {result.pricing_source}</div>
            </div>
          </Card>

          {result.excluded_providers.length > 0 && (
            <Card style={{ marginBottom: 20 }}>
              <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Excluded Providers</p>
              {result.excluded_providers.map((ep, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0",
                  borderBottom: i < result.excluded_providers.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ fontSize: 12 }}>{ep.provider_name}</span>
                  <Badge variant="danger" size="sm">{ep.reason_code ?? "UNKNOWN"}</Badge>
                </div>
              ))}
            </Card>
          )}

          {!result.selected_provider ? (
            <Card style={{ marginBottom: 20, textAlign: "center", padding: 32 }}>
              <XCircle size={28} style={{ color: "var(--danger-text)", margin: "0 auto 10px" }}/>
              <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px" }}>No eligible provider found</p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                {result.candidate_provider_count} candidate(s) found in the area, all excluded by eligibility
                gates (bookable, coverage, technician, availability, pricing, package, credits, or deposit).
              </p>
            </Card>
          ) : (
            <Card style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <CheckCircle2 size={18} style={{ color: "var(--success-text, #16a34a)" }}/>
                    <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{result.selected_provider.provider_name}</p>
                  </div>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                    {result.selected_provider.customer_visible_reason}
                  </p>
                  <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                    {result.selected_provider.public_badges.map(b => <Badge key={b} variant="info" size="sm">{b}</Badge>)}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <p style={{ fontSize: 10, color: "var(--muted-text)", textTransform: "uppercase", margin: 0 }}>Final Score (admin-only)</p>
                  <p style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>{result.selected_provider.internal_score.toFixed(1)}</p>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8 }}>
                {Object.entries(result.selected_provider.internal_score_breakdown).map(([k, v]) => (
                  <div key={k} style={{ padding: 8, borderRadius: 8, background: "var(--surface-sunken)", textAlign: "center" }}>
                    <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{v}</p>
                    <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: 0, textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {result.top_candidates.length > 1 && (
            <Card style={{ marginBottom: 20 }}>
              <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Top Candidates</p>
              {result.top_candidates.map((c, i) => (
                <div key={c.tenant_id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0",
                  borderBottom: i < result.top_candidates.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ fontSize: 12 }}>{i + 1}. {c.provider_name}</span>
                  <span style={{ fontSize: 12, fontWeight: 700 }}>{c.internal_score.toFixed(1)}</span>
                </div>
              ))}
            </Card>
          )}

          {result.price_options && (
            <Card style={{ marginBottom: 20 }}>
              <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Low / Mid / High Price Preview</p>
              <div style={{ display: "flex", gap: 10 }}>
                <PriceTierCard label="Low" value={result.price_options.low_price}/>
                <PriceTierCard label="Mid" value={result.price_options.mid_price}/>
                <PriceTierCard label="High" value={result.price_options.high_price}/>
              </div>
            </Card>
          )}

          {result.area_market_comparison && (
            <Card>
              <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Area Price Comparison</p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                {result.area_market_comparison.area} — {result.area_market_comparison.competitor_provider_count} provider(s) compared
              </p>
              <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 12 }}>
                <span>Lowest: {money(result.area_market_comparison.area_competitor_min)}</span>
                <span>Average: {money(result.area_market_comparison.area_competitor_avg)}</span>
                <span>Highest: {money(result.area_market_comparison.area_competitor_max)}</span>
              </div>
            </Card>
          )}
        </>
      )}
    </AdminLayout>
  );
}

function MiniStat({ label, value, danger }: { label: string; value: number; danger?: boolean }) {
  return (
    <div style={{ padding: "10px 14px", background: "var(--surface-sunken)", borderRadius: 10 }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: danger ? "var(--danger-text)" : "var(--text-primary)" }}>{value}</div>
      <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 2, textTransform: "uppercase" }}>{label}</div>
    </div>
  );
}

function PriceTierCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ flex: 1, padding: 12, borderRadius: 8, background: "var(--surface-sunken)", textAlign: "center" }}>
      <p style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", margin: "0 0 2px" }}>{label}</p>
      <p style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>{money(value)}</p>
    </div>
  );
}
