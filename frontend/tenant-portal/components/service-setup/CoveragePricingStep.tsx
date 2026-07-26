"use client";
import React, { useCallback, useState } from "react";
import { useApi, useAction } from "../../hooks/useApi";
import { serviceSetupApi, masterCatalogApi, type TenantEnabledService, type CoverageMode } from "../../lib/api";
import { CoverageSelector } from "./CoverageSelector";
import { PricingInheritanceCard } from "./PricingInheritanceCard";
import { PriceRangeField } from "./PriceRangeField";
import { CombinationOverrideEditor } from "./CombinationOverrideEditor";
import { Skeleton } from "../shared/ui";

/** Step 4: Coverage & Pricing. Renders ONLY the sections the backend
 * blueprint enables for this service (Case A/B/C/D from spec section 9) --
 * never shows Type controls when requires_type is false, never shows Brand
 * controls when requires_brand is false. Admin never sets a price here;
 * every value is tenant-owned. */
export function CoveragePricingStep({ service, onRefetchService }: {
  service: TenantEnabledService;
  onRefetchService: () => void;
}) {
  const tsid = service.tenant_service_id;
  const hasType = service.requires_type;
  const hasBrand = service.requires_brand;

  const typesRes = useApi(useCallback(() => hasType ? serviceSetupApi.getTypes(tsid) : Promise.resolve({ types: [] }), [tsid, hasType]));
  const typePricingRes = useApi(useCallback(() => hasType ? serviceSetupApi.getTypePricing(tsid) : Promise.resolve({ types: [] }), [tsid, hasType]));
  const brandsRes = useApi(useCallback(() => hasBrand ? serviceSetupApi.getBrands(tsid) : Promise.resolve({ brands: [] }), [tsid, hasBrand]));

  const [activeTypeId, setActiveTypeId] = useState<string | null>(null);
  const activeTypeName = typePricingRes.data?.types.find(t => t.service_type_id === activeTypeId)?.name ?? null;
  const brandPricingRes = useApi(useCallback(
    () => hasBrand ? serviceSetupApi.getBrandPricing(tsid, activeTypeId ?? undefined) : Promise.resolve({ brands: [] }),
    [tsid, hasBrand, activeTypeId]));

  const [typeMode, setTypeMode] = useState<CoverageMode>("selected");
  const [brandMode, setBrandMode] = useState<CoverageMode>("selected");

  const coverageModeAction = useAction(useCallback(
    async (dimension: "type" | "brand", mode: CoverageMode) => {
      if (dimension === "type") { setTypeMode(mode); return serviceSetupApi.setTypeCoverageMode(tsid, mode); }
      setBrandMode(mode); return serviceSetupApi.setBrandCoverageMode(tsid, mode);
    }, [tsid]));

  // Default price is set via the existing enabled-service update endpoint.
  async function handleSaveDefault(min: number, max: number) {
    await masterCatalogApi.updateEnabled(tsid, { tenant_min_price: min, tenant_max_price: max });
    onRefetchService();
  }

  async function handleSaveVisitFee(fee: number) {
    await masterCatalogApi.updateEnabled(tsid, { tenant_visit_fee: fee });
    onRefetchService();
  }

  const typePricingAction = useAction(useCallback(
    (serviceTypeId: string, min: number, max: number) => serviceSetupApi.setTypePricing(tsid, serviceTypeId, min, max),
    [tsid]));
  const brandPricingAction = useAction(useCallback(
    (brandId: string, min: number, max: number) => serviceSetupApi.setBrandPricing(tsid, brandId, min, max, activeTypeId ?? undefined),
    [tsid, activeTypeId]));

  const isInspectionWorkflow = service.job_type === "repair" || service.job_type === "inspection";

  // ── Case A: no Type, no Brand ──────────────────────────────────────────
  if (!hasType && !hasBrand) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px" }}>Pricing</h2>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
            This service has no types or brands to configure -- just set your price.
          </p>
        </div>
        {isInspectionWorkflow ? (
          <div style={{ padding: 16, borderRadius: 10, background: "var(--accent-muted)", border: "1px solid var(--border)" }}>
            <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600 }}>Inspection required</p>
            <p style={{ margin: "0 0 12px", fontSize: 12, color: "var(--text-secondary)" }}>
              The technician will inspect the issue and send the customer an estimate. If the customer approves
              the work, your visit fee will be adjusted in the final bill. If declined, only the visit fee applies.
              You set the visit fee -- there is no separate "repair price" to configure here.
            </p>
            <PriceRangeField label="Your visit fee" min={service.tenant_visit_fee ?? null} max={service.tenant_visit_fee ?? null}
              onSave={(min) => handleSaveVisitFee(min)} />
          </div>
        ) : (
          <PriceRangeField label="Your default price" min={service.tenant_min_price ?? null} max={service.tenant_max_price ?? null}
            onSave={handleSaveDefault} />
        )}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {!hasType && (
        <PriceRangeField label="Your default price" min={service.tenant_min_price ?? null} max={service.tenant_max_price ?? null}
          onSave={handleSaveDefault} />
      )}

      {/* ── Type coverage + pricing (Case B / D) ── */}
      {hasType && (
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 8px" }}>Types you support</h2>
          <div style={{ marginBottom: 12 }}>
            <CoverageSelector label="Type" mode={typeMode} onChange={m => coverageModeAction.execute("type", m)} />
          </div>
          {typePricingRes.loading ? <Skeleton height={120} /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(typePricingRes.data?.types ?? []).map(t => {
                const isActive = t.service_type_id === activeTypeId;
                return (
                  <div key={t.tenant_service_type_id} style={{
                    borderRadius: 10, outline: isActive && hasBrand ? "2px solid var(--accent)" : "none", outlineOffset: 2,
                  }}>
                    <PricingInheritanceCard
                      name={t.name}
                      resolved={t.tenant_min_price != null ? {
                        resolved: true, minimum_price: t.tenant_min_price, maximum_price: t.tenant_max_price ?? undefined,
                      } : null}
                      hasOwnOverride={t.tenant_min_price != null}
                      onSaveOverride={(min, max) => typePricingAction.execute(t.service_type_id, min, max)}
                    />
                    {hasBrand && (
                      <button onClick={() => setActiveTypeId(t.service_type_id)}
                        aria-pressed={isActive}
                        style={{
                          marginTop: 6, background: "none", border: "none", padding: 0, cursor: "pointer",
                          fontSize: 12, fontWeight: 600, color: "var(--accent)", fontFamily: "inherit",
                        }}>
                        {isActive ? "✓ Configuring brands for this type" : "Configure brand pricing for this type →"}
                      </button>
                    )}
                  </div>
                );
              })}
              {(typePricingRes.data?.types ?? []).length === 0 && (
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No types selected yet.</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Brand coverage + pricing (Case C / D) ── */}
      {hasBrand && (
        <div>
          {hasType && !activeTypeId ? (
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "var(--accent-muted)", marginBottom: 12 }}>
              <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
                Select a type above to configure its brand pricing. Brand support and pricing can differ per type --
                a brand you support for one type doesn't have to be supported for every type.
              </p>
            </div>
          ) : (
            <h2 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 8px" }}>
              Brands you support{activeTypeName ? ` for ${activeTypeName}` : ""}
            </h2>
          )}
          <div style={{ marginBottom: 12 }}>
            <CoverageSelector label="Brand" mode={brandMode} onChange={m => coverageModeAction.execute("brand", m)} />
          </div>
          {brandPricingRes.loading ? <Skeleton height={120} /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(brandPricingRes.data?.brands ?? []).map(b => (
                <PricingInheritanceCard key={b.tenant_service_brand_id}
                  name={b.name}
                  resolved={b.tenant_min_price != null ? {
                    resolved: true, minimum_price: b.tenant_min_price, maximum_price: b.tenant_max_price ?? undefined,
                  } : null}
                  hasOwnOverride={b.tenant_min_price != null}
                  onSaveOverride={(min, max) => brandPricingAction.execute(b.brand_id, min, max)}
                />
              ))}
              {(brandPricingRes.data?.brands ?? []).length === 0 && (
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No brands selected yet.</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Case D: both Type and Brand -- exact-combination overview (spec
          section 13), letting the tenant price a specific combination
          directly without needing a type or service default. */}
      {hasType && hasBrand && (
        <CombinationOverrideEditor tenantServiceId={tsid} />
      )}
    </div>
  );
}
