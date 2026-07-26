"use client";
import React, { useCallback, useState } from "react";
import { useApi, useAction } from "../../hooks/useApi";
import { serviceSetupApi, type TenantEnabledService, type PriceResolution } from "../../lib/api";
import { Btn, Skeleton } from "../shared/ui";
import { CheckCircle2, XCircle } from "lucide-react";

/** Spec section 16: "Pricing-resolution test" -- lets the tenant pick a
 * real type/brand combination and see exactly what the backend resolver
 * (the same one customers hit) returns, before publishing. Never computes
 * anything client-side. */
export function PricingResolutionTest({ service }: { service: TenantEnabledService }) {
  const tsid = service.tenant_service_id;
  const [typeId, setTypeId] = useState<string>("");
  const [brandId, setBrandId] = useState<string>("");
  const [result, setResult] = useState<PriceResolution | null>(null);

  const typesRes = useApi(useCallback(
    () => service.requires_type ? serviceSetupApi.getTypes(tsid) : Promise.resolve({ types: [] }), [tsid, service.requires_type]));
  const brandsRes = useApi(useCallback(
    () => service.requires_brand ? serviceSetupApi.getBrands(tsid) : Promise.resolve({ brands: [] }), [tsid, service.requires_brand]));

  const testAction = useAction(useCallback(
    () => serviceSetupApi.resolvePrice(tsid, typeId || undefined, brandId || undefined),
    [tsid, typeId, brandId]));

  async function handleTest() {
    const r = await testAction.execute();
    setResult(r);
  }

  if (!service.requires_type && !service.requires_brand) return null; // nothing to test combinations of

  return (
    <div style={{ padding: 14, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
      <p style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 700 }}>Test a customer's price</p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
        {service.requires_type && (
          <select value={typeId} onChange={e => setTypeId(e.target.value)}
            style={{ height: 34, borderRadius: 7, border: "1px solid var(--border)", background: "var(--input-bg)",
              color: "var(--text-primary)", fontSize: 12, padding: "0 8px" }}>
            <option value="">Any type</option>
            {(typesRes.data?.types ?? []).map(t => <option key={t.service_type_id} value={t.service_type_id}>{t.name}</option>)}
          </select>
        )}
        {service.requires_brand && (
          <select value={brandId} onChange={e => setBrandId(e.target.value)}
            style={{ height: 34, borderRadius: 7, border: "1px solid var(--border)", background: "var(--input-bg)",
              color: "var(--text-primary)", fontSize: 12, padding: "0 8px" }}>
            <option value="">Any brand</option>
            {(brandsRes.data?.brands ?? []).map(b => <option key={b.brand_id} value={b.brand_id}>{b.name}</option>)}
          </select>
        )}
        <Btn size="sm" onClick={handleTest} loading={testAction.loading}>Test</Btn>
      </div>
      {testAction.loading && <Skeleton height={20} />}
      {testAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)" }}>{testAction.error}</p>}
      {result && (
        result.resolved ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--success-text)" }}>
            <CheckCircle2 size={15} />
            Resolves to ₹{result.minimum_price}–₹{result.maximum_price}
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>({result.source})</span>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--danger-text)" }}>
            <XCircle size={15} />
            {result.reason === "COMBINATION_NOT_SUPPORTED"
              ? "This combination is not supported for customers."
              : "No price is configured for this combination yet."}
          </div>
        )
      )}
    </div>
  );
}
