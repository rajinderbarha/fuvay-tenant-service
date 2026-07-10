"use client";
import React, { useState, useCallback, useEffect, useRef } from "react";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import { Card, Btn, Badge, Skeleton, EmptyState, Modal } from "../../../../../components/shared/ui";
import {
  homeServicesSetupApi, providerServiceAreasApi, providerStatusApi, ServiceOSError,
  isTenantReadOnly,
  type AdminMasterServiceRow, type TenantEnabledService,
  type HsSetupType, type HsSetupBrand,
  type HsTypePricing, type HsBrandPricing, type HsPricePreview,
} from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { useTenant } from "../../../../../hooks/useTenant";
import { isHomeServicesTenant } from "../../../../../lib/verticalGuard";
import {
  Wrench, CheckCircle2, AlertCircle, ArrowRight, Copy,
  RefreshCw, Tag, Users2, MapPin, ChevronLeft, Info,
  Star, Shield, Package, BarChart2,
} from "lucide-react";

// ── Safe helpers ──────────────────────────────────────────────────────────────
const safeText = (v: unknown, fb = "—"): string =>
  typeof v === "string" && v.trim() ? v.trim() : fb;
const safeNum = (v: unknown): number => {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? ""));
  return Number.isFinite(n) ? n : 0;
};
const safeCur = (v: unknown, fb = "—"): string => {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? ""));
  return Number.isFinite(n) ? `₹${n.toLocaleString("en-IN")}` : fb;
};

function copyText(t: string) {
  if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {});
}

// ── Error banner ──────────────────────────────────────────────────────────────
function ErrBanner({ title, error, requestId, onRetry }: {
  title: string; error: string; requestId?: string | null; onRetry?: () => void;
}) {
  return (
    <div style={{
      padding: "16px 20px", borderRadius: 12,
      background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
      display: "flex", flexDirection: "column", gap: 8,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <AlertCircle size={16} style={{ color: "var(--danger-text)", flexShrink: 0 }} />
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--danger-text)", margin: 0 }}>{title}</p>
      </div>
      <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0, opacity: 0.9 }}>{error}</p>
      {requestId && (
        <button onClick={() => copyText(requestId)} style={{
          fontSize: 11, color: "var(--danger-text)", background: "none", border: "none",
          cursor: "pointer", padding: 0, display: "flex", alignItems: "center",
          gap: 4, fontFamily: "inherit", opacity: 0.75,
        }}>
          <Copy size={10} /> Request ID: {requestId}
        </button>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
        {onRetry && (
          <Btn size="sm" variant="secondary" onClick={onRetry}>
            <RefreshCw size={12} style={{ marginRight: 4 }} /> Retry
          </Btn>
        )}
        {requestId && (
          <Btn size="sm" variant="ghost" onClick={() => copyText(requestId)}>
            <Copy size={12} style={{ marginRight: 4 }} /> Copy Request ID
          </Btn>
        )}
      </div>
    </div>
  );
}

// ── Price preview card ────────────────────────────────────────────────────────
function PricePreviewBand({ preview }: { preview: HsPricePreview | null }) {
  if (!preview) return null;
  return (
    <div style={{
      display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8,
      padding: "14px 16px", background: "var(--surface-sunken)", borderRadius: 10,
    }}>
      {(["Low", "Mid", "High"] as const).map(tier => {
        const val = tier === "Low" ? preview.low_price
          : tier === "Mid" ? preview.mid_price : preview.high_price;
        return (
          <div key={tier} style={{
            padding: "10px 12px", background: "var(--surface)", borderRadius: 8,
            border: "1px solid var(--border)", textAlign: "center",
          }}>
            <p style={{ margin: 0, fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: 1 }}>{tier}</p>
            <p style={{ margin: "4px 0 0", fontSize: 17, fontWeight: 800, color: "var(--text-primary)" }}>
              {safeCur(val)}
            </p>
          </div>
        );
      })}
      <p style={{ gridColumn: "1/-1", margin: 0, fontSize: 10, color: "var(--text-tertiary)" }}>
        Platform fee: {safeNum(preview.platform_fee_percent)}% · Customer pays provider directly on-site
      </p>
    </div>
  );
}

// ── Wizard types ──────────────────────────────────────────────────────────────
type WizardStep = "overview" | "types" | "pricing" | "brands" | "review";

const STEP_ORDER: WizardStep[] = ["overview", "types", "pricing", "brands", "review"];

const STEP_LABELS: Record<WizardStep, string> = {
  overview: "1. Service",
  types: "2. Types",
  pricing: "3. Pricing",
  brands: "4. Brands",
  review: "5. Review",
};

// Per-type pricing state
interface TypePricingState {
  typeId: string; typeName: string;
  adminFloor: number; adminCeiling: number;
  platformFeePercent: number;
  tenantMin: string; tenantMax: string;
  preview: HsPricePreview | null;
}

// Per-type, per-brand pricing state. FIX — brand overrides must be scoped
// to a specific service type (Window AC + LG must be independent from
// Split AC + LG) — previously this state had no typeId at all, so one LG
// override applied identically to every type.
interface BrandPricingState {
  typeId: string; typeName: string;
  brandId: string; brandName: string;
  canOverride: boolean;
  enabled: boolean;
  tenantMin: string; tenantMax: string;
  adminFloor: number | null; adminCeiling: number | null;
  preview: HsPricePreview | null;
}

// ── Wizard ────────────────────────────────────────────────────────────────────
function ServiceSetupWizard({
  service, enabled, onClose, onSaved,
}: {
  service: AdminMasterServiceRow;
  enabled: TenantEnabledService | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [step, setStep] = useState<WizardStep>("overview");
  const [completedSteps, setCompletedSteps] = useState<Set<WizardStep>>(new Set());

  // E2E-09B: read-only tenant users (access_scope=customer_support_limited) can
  // view the full setup wizard but every Save/Publish action is disabled here
  // as UX polish — the backend's require_tenant_mutation_permission is the
  // real authorization boundary and returns 403 regardless of this flag.
  const readOnly = isTenantReadOnly();

  // Types
  const [selectedTypeIds, setSelectedTypeIds] = useState<string[]>([]);
  const typePricingRef = useRef<TypePricingState[]>([]);
  const [typePricingState, setTypePricingState] = useState<TypePricingState[]>([]);

  // Brands
  const [brandMode, setBrandMode] = useState<"same" | "override">("same");
  const [brandPricingState, setBrandPricingState] = useState<BrandPricingState[]>([]);

  // Save state
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveRequestId, setSaveRequestId] = useState<string | null>(null);
  const [tenantServiceId, setTenantServiceId] = useState<string | null>(enabled?.tenant_service_id ?? null);

  // HS4B — bookability status shown after publish (real backend computation,
  // not a fabricated "ready" state)
  const [bookabilityStatus, setBookabilityStatus] = useState<{
    is_bookable: boolean; is_visible: boolean;
    bookability_blockers: { code: string; message: string; route?: string | null }[];
  } | null>(null);
  const [bookabilityLoading, setBookabilityLoading] = useState(false);

  // Data hooks
  const typesApi = useApi(useCallback(() =>
    homeServicesSetupApi.getTypes(tenantServiceId ?? "__none__"), [tenantServiceId]));
  const brandsApi = useApi(useCallback(() =>
    homeServicesSetupApi.getBrands(tenantServiceId ?? "__none__"), [tenantServiceId]));
  const typePricingApi = useApi(useCallback(() =>
    tenantServiceId ? homeServicesSetupApi.getTypePricing(tenantServiceId) : Promise.resolve(null),
  [tenantServiceId]));
  // FIX — brand pricing must be fetched per service type (not once,
  // type-agnostically) so Window AC's brand prices never collide with
  // Split AC's. Fires once typePricingState is known.
  const [brandPricingLoading, setBrandPricingLoading] = useState(false);
  const [brandPricingError, setBrandPricingError] = useState<string | null>(null);
  const [brandPricingRequestId, setBrandPricingRequestId] = useState<string | null>(null);
  const fetchBrandPricingForTypes = useCallback(async (tsid: string, typeIds: string[], typeNames: Record<string, string>) => {
    setBrandPricingLoading(true); setBrandPricingError(null);
    try {
      const results = await Promise.all(
        typeIds.map(typeId => homeServicesSetupApi.getBrandPricing(tsid, typeId).then(r => ({ typeId, r })))
      );
      const next: BrandPricingState[] = [];
      for (const { typeId, r } of results) {
        for (const b of (r as { brands: HsBrandPricing[] }).brands) {
          next.push({
            typeId, typeName: typeNames[typeId] ?? "",
            brandId: b.brand_id, brandName: b.name,
            canOverride: b.can_override_price,
            enabled: b.tenant_min_price != null || b.tenant_max_price != null,
            tenantMin: b.tenant_min_price != null ? String(b.tenant_min_price) : "",
            tenantMax: b.tenant_max_price != null ? String(b.tenant_max_price) : "",
            adminFloor: b.admin_floor_price, adminCeiling: b.admin_ceiling_price,
            preview: b.customer_price_preview ?? null,
          });
        }
      }
      setBrandPricingState(next);
    } catch (e) {
      const rid = e instanceof ServiceOSError ? (e.requestId ?? null) : null;
      setBrandPricingError(e instanceof Error ? e.message : "Could not load brand pricing.");
      setBrandPricingRequestId(rid);
    } finally {
      setBrandPricingLoading(false);
    }
  }, []);
  const areasApi = useApi(useCallback(() => providerServiceAreasApi.list(), []));

  // Enable service on first open if not yet enabled
  const enableAction = useAction(useCallback(async () => {
    if (tenantServiceId) return { tenant_service_id: tenantServiceId };
    const result = await homeServicesSetupApi.enable({ master_service_id: service.service_id });
    setTenantServiceId(result.tenant_service_id);
    return result;
  }, [tenantServiceId, service.service_id]));

  useEffect(() => {
    if (!tenantServiceId) {
      enableAction.execute().catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Init selected types from existing data
  useEffect(() => {
    if (typesApi.data?.types && selectedTypeIds.length === 0) {
      const sel = typesApi.data.types.filter(t => t.is_default || t.is_required).map(t => t.service_type_id);
      if (sel.length) setSelectedTypeIds(sel);
    }
  }, [typesApi.data]);

  // Init type pricing state when data loads
  useEffect(() => {
    if (!typePricingApi.data?.types) return;
    const next = typePricingApi.data.types
      .filter(t => selectedTypeIds.includes(t.service_type_id))
      .map(t => ({
        typeId: t.service_type_id,
        typeName: t.name,
        adminFloor: safeNum(t.admin_floor_price),
        adminCeiling: safeNum(t.admin_ceiling_price) || 99999,
        platformFeePercent: safeNum(t.platform_fee_percent),
        tenantMin: t.tenant_min_price != null ? String(t.tenant_min_price) : String(safeNum(t.admin_floor_price)),
        tenantMax: t.tenant_max_price != null ? String(t.tenant_max_price) : String(safeNum(t.admin_ceiling_price) || safeNum(t.admin_floor_price)),
        preview: t.customer_price_preview ?? null,
      }));
    typePricingRef.current = next;
    setTypePricingState(next);
  }, [typePricingApi.data, selectedTypeIds]);

  // Init brand pricing state — per type (see fetchBrandPricingForTypes above).
  useEffect(() => {
    if (!tenantServiceId || typePricingState.length === 0) return;
    const typeNames: Record<string, string> = {};
    for (const tp of typePricingState) typeNames[tp.typeId] = tp.typeName;
    fetchBrandPricingForTypes(tenantServiceId, typePricingState.map(tp => tp.typeId), typeNames);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantServiceId, typePricingState.map(tp => tp.typeId).join(",")]);

  const typesForService = (typesApi.data?.types ?? []) as HsSetupType[];
  const brandsForService = (brandsApi.data?.brands ?? []) as HsSetupBrand[];
  const hasTypes = typesForService.length > 0;
  const hasBrands = brandsForService.some(b => b.is_enabled);
  const hasActiveArea = (areasApi.data?.areas ?? []).some(a => a.is_active);

  // Saving actions
  const saveTypesAction = useAction(useCallback(async () => {
    if (!tenantServiceId) throw new Error("Service not initialized.");
    return homeServicesSetupApi.setTypes(tenantServiceId, selectedTypeIds);
  }, [tenantServiceId, selectedTypeIds]));

  const savePricingAction = useAction(useCallback(async () => {
    if (!tenantServiceId) throw new Error("Service not initialized.");
    for (const tp of typePricingState) {
      const min = parseFloat(tp.tenantMin);
      const max = parseFloat(tp.tenantMax);
      if (Number.isFinite(min) && Number.isFinite(max)) {
        await homeServicesSetupApi.setTypePricing(tenantServiceId, tp.typeId, min, max);
      }
    }
  }, [tenantServiceId, typePricingState]));

  const saveBrandPricingAction = useAction(useCallback(async () => {
    if (!tenantServiceId || brandMode === "same") return;
    // FIX — service_type_id is now always passed: type-specific brand
    // override must never apply to more than the one type it was set on
    // (Window AC + LG must not overwrite Split AC + LG, and vice versa).
    for (const bp of brandPricingState) {
      if (!bp.enabled || !bp.canOverride) continue;
      const min = parseFloat(bp.tenantMin);
      const max = parseFloat(bp.tenantMax);
      if (Number.isFinite(min) && Number.isFinite(max)) {
        await homeServicesSetupApi.setBrandPricing(tenantServiceId, bp.brandId, min, max, bp.typeId);
      }
    }
  }, [tenantServiceId, brandMode, brandPricingState]));

  const saveDraftAction = useAction(useCallback(async () => {
    if (!tenantServiceId) throw new Error("Service not initialized.");
    return homeServicesSetupApi.saveDraft(tenantServiceId);
  }, [tenantServiceId]));

  const publishAction = useAction(useCallback(async () => {
    if (!tenantServiceId) throw new Error("Service not initialized.");
    return homeServicesSetupApi.publish(tenantServiceId);
  }, [tenantServiceId]));

  // Live price preview
  const previewPriceAction = useAction(useCallback(async (min: number, max: number) => {
    return homeServicesSetupApi.pricePreview({ tenant_min_price: min, tenant_max_price: max });
  }, []));

  function updateTypePricing(typeId: string, field: "tenantMin" | "tenantMax", value: string) {
    setTypePricingState(prev => prev.map(tp =>
      tp.typeId === typeId ? { ...tp, [field]: value, preview: null } : tp
    ));
  }

  async function previewTypePrice(tp: TypePricingState) {
    const min = parseFloat(tp.tenantMin);
    const max = parseFloat(tp.tenantMax);
    if (!Number.isFinite(min) || !Number.isFinite(max)) return;
    try {
      const r = await previewPriceAction.execute(min, max);
      if (r) {
        setTypePricingState(prev => prev.map(t =>
          t.typeId === tp.typeId ? { ...t, preview: r as HsPricePreview } : t
        ));
      }
    } catch {
      // non-fatal — preview is optional
    }
  }

  async function handleNext() {
    setSaveError(null); setSaveRequestId(null);
    try {
      if (step === "overview") {
        setCompletedSteps(prev => new Set([...prev, "overview"]));
        setStep(hasTypes ? "types" : "pricing");
      } else if (step === "types") {
        if (hasTypes && selectedTypeIds.length === 0) {
          setSaveError("Select at least one type to continue."); return;
        }
        await saveTypesAction.execute();
        await typePricingApi.refetch();
        setCompletedSteps(prev => new Set([...prev, "types"]));
        setStep("pricing");
      } else if (step === "pricing") {
        // validate ranges
        for (const tp of typePricingState) {
          const min = parseFloat(tp.tenantMin);
          const max = parseFloat(tp.tenantMax);
          if (!Number.isFinite(min) || !Number.isFinite(max)) {
            setSaveError(`Set a valid price range for ${tp.typeName}.`); return;
          }
          if (min < tp.adminFloor) {
            setSaveError(`Min price for ${tp.typeName} cannot be below admin floor ₹${tp.adminFloor}.`); return;
          }
          if (max > tp.adminCeiling) {
            setSaveError(`Max price for ${tp.typeName} cannot exceed admin ceiling ₹${tp.adminCeiling}.`); return;
          }
          if (min > max) {
            setSaveError(`Min must be ≤ Max for ${tp.typeName}.`); return;
          }
        }
        await savePricingAction.execute();
        setCompletedSteps(prev => new Set([...prev, "pricing"]));
        setStep(hasBrands ? "brands" : "review");
      } else if (step === "brands") {
        if (brandMode === "override") {
          await saveBrandPricingAction.execute();
        }
        setCompletedSteps(prev => new Set([...prev, "brands"]));
        setStep("review");
      }
    } catch (e) {
      const rid = e instanceof ServiceOSError ? (e.requestId ?? null) : null;
      setSaveError(e instanceof Error ? e.message : "An error occurred.");
      setSaveRequestId(rid);
    }
  }

  async function handleSaveDraft() {
    setSaveError(null); setSaveRequestId(null);
    try {
      await saveDraftAction.execute();
      onSaved();
    } catch (e) {
      const rid = e instanceof ServiceOSError ? (e.requestId ?? null) : null;
      setSaveError(e instanceof Error ? e.message : "Save failed.");
      setSaveRequestId(rid);
    }
  }

  async function handlePublish() {
    setSaveError(null); setSaveRequestId(null);
    try {
      await publishAction.execute();
      onSaved();
      // HS4B — after a real publish, refresh bookability status so the UI
      // never shows a false "ready"/bookable state. Failure to refresh
      // does not fail the publish itself (publish already succeeded);
      // it just means we show a "couldn't confirm bookability" fallback.
      setBookabilityLoading(true);
      try {
        const status = await providerStatusApi.refresh();
        setBookabilityStatus({
          is_bookable: status.is_bookable, is_visible: status.is_visible,
          bookability_blockers: status.bookability_blockers ?? [],
        });
      } catch {
        setBookabilityStatus(null);
      } finally {
        setBookabilityLoading(false);
      }
    } catch (e) {
      const rid = e instanceof ServiceOSError ? (e.requestId ?? null) : null;
      setSaveError(e instanceof Error ? e.message : "Publish failed.");
      setSaveRequestId(rid);
    }
  }

  const stepIndex = STEP_ORDER.indexOf(step);
  const visibleSteps = hasBrands ? STEP_ORDER : STEP_ORDER.filter(s => s !== "brands");

  return (
    <Modal open onClose={onClose} title="" size="lg">
      <div style={{ display: "flex", minWidth: 800, minHeight: 540, gap: 0 }}>

        {/* LEFT PANEL */}
        <div style={{
          width: 200, flexShrink: 0, padding: "24px 16px",
          borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 16,
        }}>
          <button onClick={onClose} style={{
            display: "flex", alignItems: "center", gap: 6, fontSize: 12,
            color: "var(--text-tertiary)", background: "none", border: "none",
            cursor: "pointer", padding: 0, fontFamily: "inherit",
          }}>
            <ChevronLeft size={14} /> All services
          </button>

          <div>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 2px", color: "var(--text-primary)" }}>
              {safeText(service.service_name)}
            </p>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
              {service.pricing_model === "type_based" ? "Type-based" : "Fixed pricing"}
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {visibleSteps.map((s) => {
              const done = completedSteps.has(s);
              const active = s === step;
              return (
                <div key={s} style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 10px", borderRadius: 8,
                  background: active ? "var(--brand)" : "transparent",
                  cursor: done || active ? "default" : "pointer",
                }}>
                  {done ? (
                    <CheckCircle2 size={14} style={{ color: active ? "#fff" : "var(--success-text)", flexShrink: 0 }} />
                  ) : (
                    <div style={{
                      width: 14, height: 14, borderRadius: "50%", border: `2px solid ${active ? "#fff" : "var(--border)"}`,
                      flexShrink: 0,
                    }} />
                  )}
                  <span style={{
                    fontSize: 12, fontWeight: active ? 700 : 500,
                    color: active ? "#fff" : done ? "var(--success-text)" : "var(--text-secondary)",
                  }}>
                    {STEP_LABELS[s]}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT CONTENT */}
        <div style={{ flex: 1, padding: 28, display: "flex", flexDirection: "column", gap: 20, overflowY: "auto" }}>
          {enableAction.loading && (
            <div style={{ display: "flex", gap: 12, flexDirection: "column" }}>
              <Skeleton height={24} width={200} />
              <Skeleton height={16} width={320} />
            </div>
          )}

          {enableAction.error && (
            <ErrBanner title="We couldn't initialize this service" error={enableAction.error}
              requestId={enableAction.requestId} onRetry={() => enableAction.execute()} />
          )}

          {/* STEP: OVERVIEW */}
          {step === "overview" && !enableAction.loading && (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                <h2 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 4px" }}>
                  Set up {safeText(service.service_name)}
                </h2>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                  Review what you&apos;re configuring and how pricing works for this service.
                </p>
              </div>

              <div style={{
                padding: "12px 16px", borderRadius: 10,
                background: "var(--info-bg, #eff6ff)", border: "1px solid var(--info-border, #bfdbfe)",
                display: "flex", gap: 10,
              }}>
                <Info size={15} style={{ color: "var(--info-text, #1d4ed8)", flexShrink: 0, marginTop: 1 }} />
                <p style={{ fontSize: 12, color: "var(--info-text, #1d4ed8)", margin: 0 }}>
                  You set a price range per type. If brand pricing is enabled, you can optionally set brand-specific overrides.
                  The most specific price wins: <strong>brand → type → base</strong>.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <InfoCard icon={<Tag size={16}/>} label="Pricing Model"
                  value={service.pricing_model === "type_based" ? "Type-based" : "Fixed"} />
                {hasTypes && (
                  <InfoCard icon={<Package size={16}/>} label="Types"
                    value={`${typesForService.length} available`} />
                )}
                {hasBrands && (
                  <InfoCard icon={<Star size={16}/>} label="Brands"
                    value={`${brandsForService.filter(b => b.is_enabled).length} brands`} sub="Brand pricing available" />
                )}
                <InfoCard icon={<MapPin size={16}/>} label="Service Areas"
                  value={hasActiveArea
                    ? `${(areasApi.data?.areas ?? []).filter(a => a.is_active).length} area(s)`
                    : "None set"}
                  warn={!hasActiveArea} />
              </div>

              <Btn onClick={handleNext}>
                Next: {hasTypes ? "Select Types" : "Set Pricing"} <ArrowRight size={14} style={{ marginLeft: 6 }} />
              </Btn>
            </div>
          )}

          {/* STEP: TYPES */}
          {step === "types" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 800, margin: "0 0 4px" }}>Which types do you service?</h2>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                  Select all the types you can handle. You&apos;ll set a price for each one in the next step.
                </p>
              </div>
              {typesApi.loading ? <Skeleton height={200} /> : typesApi.error ? (
                <ErrBanner title="We couldn't load service types" error={typesApi.error}
                  requestId={typesApi.requestId} onRetry={typesApi.refetch} />
              ) : typesForService.length === 0 ? (
                <EmptyState title="No types" description="This service does not have sub-types." />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {typesForService.map(t => {
                    const sel = selectedTypeIds.includes(t.service_type_id);
                    return (
                      <div key={t.service_type_id} onClick={() => {
                        if (t.is_required) return;
                        setSelectedTypeIds(prev =>
                          sel ? prev.filter(x => x !== t.service_type_id) : [...prev, t.service_type_id]
                        );
                      }} style={{
                        padding: "14px 16px", borderRadius: 10,
                        border: `2px solid ${sel ? "var(--brand)" : "var(--border)"}`,
                        background: sel ? "var(--brand-bg, #eff6ff)" : "var(--surface)",
                        cursor: t.is_required ? "default" : "pointer",
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                      }}>
                        <div>
                          <p style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>{safeText(t.name)}</p>
                          {hasBrands && (
                            <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
                              Brand pricing available
                            </p>
                          )}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          {t.is_required && <Badge variant="info">Required</Badge>}
                          <div style={{
                            width: 20, height: 20, borderRadius: 4,
                            border: `2px solid ${sel ? "var(--brand)" : "var(--border)"}`,
                            background: sel ? "var(--brand)" : "transparent",
                            display: "flex", alignItems: "center", justifyContent: "center",
                          }}>
                            {sel && <CheckCircle2 size={14} style={{ color: "#fff" }} />}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {saveError && (
                <ErrBanner title="Cannot continue" error={saveError} requestId={saveRequestId} />
              )}

              <div style={{ display: "flex", gap: 10 }}>
                <Btn variant="ghost" onClick={() => setStep("overview")}>Back</Btn>
                <Btn onClick={handleNext} loading={saveTypesAction.loading} disabled={readOnly}>
                  Next: Set Pricing <ArrowRight size={14} style={{ marginLeft: 6 }} />
                </Btn>
              </div>
            </div>
          )}

          {/* STEP: PRICING */}
          {step === "pricing" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 800, margin: "0 0 4px" }}>Set your price range per type</h2>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                  Your range must stay within the admin-set working range.
                  Customer Low / Mid / High options are generated automatically.
                </p>
              </div>
              {typePricingApi.loading ? <Skeleton height={300} /> : (
                typePricingState.length === 0 ? (
                  <EmptyState title="No types selected" description="Go back and select at least one type." />
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    {typePricingState.map(tp => (
                      <TypePricingCard key={tp.typeId} tp={tp}
                        onUpdate={(field, val) => updateTypePricing(tp.typeId, field, val)}
                        onPreview={() => previewTypePrice(tp)}
                        previewLoading={previewPriceAction.loading} />
                    ))}
                  </div>
                )
              )}

              {saveError && (
                <ErrBanner title="Cannot continue" error={saveError} requestId={saveRequestId} />
              )}

              <div style={{ display: "flex", gap: 10 }}>
                <Btn variant="ghost" onClick={() => setStep(hasTypes ? "types" : "overview")}>Back</Btn>
                <Btn onClick={handleNext} loading={savePricingAction.loading} disabled={readOnly}>
                  Next: {hasBrands ? "Brand Pricing" : "Review"} <ArrowRight size={14} style={{ marginLeft: 6 }} />
                </Btn>
              </div>
            </div>
          )}

          {/* STEP: BRANDS */}
          {step === "brands" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 800, margin: "0 0 4px" }}>Brand pricing</h2>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                  By default all brands use your type range. You can set a different range for specific brands.
                  Brand prices are configured separately for each type — Window AC + LG can be different from Split AC + LG.
                </p>
              </div>

              <div style={{ display: "flex", gap: 10 }}>
                {(["same", "override"] as const).map(m => (
                  <button key={m} onClick={() => setBrandMode(m)} style={{
                    padding: "10px 20px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer",
                    border: `2px solid ${brandMode === m ? "var(--brand)" : "var(--border)"}`,
                    background: brandMode === m ? "var(--brand)" : "var(--surface)",
                    color: brandMode === m ? "#fff" : "var(--text-primary)",
                  }}>
                    {m === "same" ? "Same for all" : "Override some"}
                  </button>
                ))}
              </div>

              {brandMode === "same" ? (
                <div style={{
                  padding: "14px 16px", borderRadius: 10,
                  background: "var(--success-bg)", border: "1px solid var(--success-border)",
                }}>
                  <p style={{ margin: 0, fontSize: 13, color: "var(--success-text)", fontWeight: 600 }}>
                    All approved brands will use your type price range.
                  </p>
                </div>
              ) : brandPricingLoading ? (
                <Skeleton height={200} />
              ) : brandPricingError ? (
                <ErrBanner title="We couldn't load brand pricing" error={brandPricingError} requestId={brandPricingRequestId} />
              ) : (
                // Type-specific brand overrides — one section per selected
                // type, each with its own set of brand override rows. This
                // is the fix: Window AC's LG row and Split AC's LG row are
                // now two entirely separate entries in brandPricingState.
                <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                  {typePricingState.map(tp => {
                    const rowsForType = brandPricingState.filter(b => b.typeId === tp.typeId && b.canOverride);
                    if (rowsForType.length === 0) return null;
                    return (
                      <div key={tp.typeId} style={{
                        padding: "14px 16px", borderRadius: 12, border: "1px solid var(--border)",
                        background: "var(--surface-sunken)",
                      }}>
                        <p style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 700 }}>{safeText(tp.typeName)}</p>
                        <p style={{ margin: "0 0 12px", fontSize: 11, color: "var(--text-tertiary)" }}>
                          Platform Allowed Range: {safeCur(tp.adminFloor)}–{safeCur(tp.adminCeiling)} ·
                          Your Type Range: {safeCur(parseFloat(tp.tenantMin))}–{safeCur(parseFloat(tp.tenantMax))}
                        </p>
                        <p style={{ margin: "0 0 8px", fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
                          Brand Overrides for {safeText(tp.typeName)}
                        </p>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                          {rowsForType.map(bp => (
                            <BrandOverrideRow key={`${bp.typeId}-${bp.brandId}`} bp={bp}
                              onChange={(field, val) => {
                                setBrandPricingState(prev => prev.map(b =>
                                  (b.typeId === bp.typeId && b.brandId === bp.brandId) ? { ...b, [field]: val, preview: null } : b
                                ));
                              }}
                              onPreview={async () => {
                                const min = parseFloat(bp.tenantMin);
                                const max = parseFloat(bp.tenantMax);
                                if (!Number.isFinite(min) || !Number.isFinite(max)) return;
                                try {
                                  const r = await homeServicesSetupApi.pricePreview({ tenant_min_price: min, tenant_max_price: max });
                                  setBrandPricingState(prev => prev.map(b =>
                                    (b.typeId === bp.typeId && b.brandId === bp.brandId) ? { ...b, preview: r as HsPricePreview } : b
                                  ));
                                } catch { /* non-fatal */ }
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {saveError && (
                <ErrBanner title="Cannot continue" error={saveError} requestId={saveRequestId} />
              )}

              <div style={{ display: "flex", gap: 10 }}>
                <Btn variant="ghost" onClick={() => setStep("pricing")}>Back</Btn>
                <Btn onClick={handleNext} loading={saveBrandPricingAction.loading} disabled={readOnly}>
                  Next: Review <ArrowRight size={14} style={{ marginLeft: 6 }} />
                </Btn>
              </div>
            </div>
          )}

          {/* STEP: REVIEW */}
          {step === "review" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 800, margin: "0 0 4px" }}>Review &amp; publish</h2>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                  Your complete pricing matrix. Verify before going live.
                </p>
              </div>

              {/* Review matrix */}
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)" }}>
                      {["Type / Item", "Brand / Variant", "Your Min", "Your Max", "Customer Sees", "Note"].map(h => (
                        <th key={h} style={{
                          padding: "8px 12px", textAlign: "left", fontWeight: 700,
                          color: "var(--text-secondary)", borderBottom: "1px solid var(--border)",
                          whiteSpace: "nowrap",
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {typePricingState.map((tp, i) => (
                      <React.Fragment key={tp.typeId}>
                        <tr style={{ background: i % 2 === 0 ? "transparent" : "var(--surface-sunken)" }}>
                          <td style={{ padding: "10px 12px", fontWeight: 600 }}>{safeText(tp.typeName)}</td>
                          <td style={{ padding: "10px 12px", color: "var(--text-tertiary)" }}>Base / Other</td>
                          <td style={{ padding: "10px 12px", fontVariantNumeric: "tabular-nums" }}>{safeCur(parseFloat(tp.tenantMin))}</td>
                          <td style={{ padding: "10px 12px", fontVariantNumeric: "tabular-nums" }}>{safeCur(parseFloat(tp.tenantMax))}</td>
                          <td style={{ padding: "10px 12px" }}>
                            {tp.preview ? (
                              <span style={{ color: "var(--text-secondary)" }}>
                                Low {safeCur(tp.preview.low_price)} / Mid {safeCur(tp.preview.mid_price)} / High {safeCur(tp.preview.high_price)}
                              </span>
                            ) : <span style={{ color: "var(--text-tertiary)" }}>Preview not loaded</span>}
                          </td>
                          <td style={{ padding: "10px 12px", color: "var(--text-tertiary)", fontSize: 11 }}>Type range</td>
                        </tr>
                        {brandMode === "override" && brandPricingState
                          .filter(b => b.typeId === tp.typeId && b.canOverride)
                          .map(bp => (
                            bp.enabled ? (
                              <tr key={`${bp.typeId}-${bp.brandId}`} style={{ background: "var(--surface-sunken)" }}>
                                <td style={{ padding: "8px 12px", color: "var(--text-tertiary)" }}>↳ {safeText(tp.typeName)}</td>
                                <td style={{ padding: "8px 12px", fontWeight: 600 }}>{safeText(bp.brandName)}</td>
                                <td style={{ padding: "8px 12px", fontVariantNumeric: "tabular-nums" }}>{safeCur(parseFloat(bp.tenantMin))}</td>
                                <td style={{ padding: "8px 12px", fontVariantNumeric: "tabular-nums" }}>{safeCur(parseFloat(bp.tenantMax))}</td>
                                <td style={{ padding: "8px 12px" }}>
                                  {bp.preview ? (
                                    <span style={{ color: "var(--text-secondary)" }}>
                                      Low {safeCur(bp.preview.low_price)} / Mid {safeCur(bp.preview.mid_price)} / High {safeCur(bp.preview.high_price)}
                                    </span>
                                  ) : <span style={{ color: "var(--text-tertiary)" }}>Preview not loaded</span>}
                                </td>
                                <td style={{ padding: "8px 12px", color: "var(--text-tertiary)", fontSize: 11 }}>Type brand override</td>
                              </tr>
                            ) : (
                              <tr key={`${bp.typeId}-${bp.brandId}`} style={{ background: "var(--surface-sunken)" }}>
                                <td style={{ padding: "8px 12px", color: "var(--text-tertiary)" }}>↳ {safeText(tp.typeName)}</td>
                                <td style={{ padding: "8px 12px", fontWeight: 600 }}>{safeText(bp.brandName)}</td>
                                <td colSpan={3} style={{ padding: "8px 12px", color: "var(--text-tertiary)", fontSize: 12 }}>
                                  No brand override — using type price
                                  <button onClick={() => setStep("brands")} style={{
                                    marginLeft: 8, fontSize: 11, fontWeight: 700, color: "var(--brand)",
                                    background: "none", border: "none", cursor: "pointer", padding: 0,
                                  }}>Add override</button>
                                </td>
                                <td style={{ padding: "8px 12px" }}/>
                              </tr>
                            )
                        ))}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{
                padding: "12px 16px", borderRadius: 10,
                background: "var(--surface-sunken)", border: "1px solid var(--border)",
              }}>
                <p style={{ margin: "0 0 6px", fontSize: 12, color: "var(--text-secondary)" }}>
                  <strong>Price resolution:</strong> type-specific brand price → type price → service base price.
                  Customer price options are generated automatically with the platform fee.
                  Customer pays provider directly on-site.
                </p>
                <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>
                  Brand prices are configured separately for each type. Example: Window AC + LG can be different from Split AC + LG.
                </p>
              </div>

              {!hasActiveArea && (
                <div style={{
                  padding: "12px 16px", borderRadius: 10,
                  background: "var(--warning-bg)", border: "1px solid var(--warning-border)",
                }}>
                  <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 700, color: "var(--warning-text)" }}>
                    No active service area
                  </p>
                  <p style={{ margin: "0 0 10px", fontSize: 12, color: "var(--warning-text)" }}>
                    Publish is blocked until you add at least one service area.
                  </p>
                  <Btn size="sm" variant="warning" onClick={() => window.open("/provider/service-areas", "_blank")}>
                    <MapPin size={12} style={{ marginRight: 4 }} /> Add Service Area
                  </Btn>
                </div>
              )}

              {saveError && (
                <ErrBanner title="Action failed" error={saveError} requestId={saveRequestId} />
              )}

              {readOnly && (
                <div style={{
                  padding: "12px 16px", borderRadius: 10,
                  background: "var(--info-bg, #eef2ff)", border: "1px solid var(--info-border, #c7d2fe)",
                }}>
                  <p style={{ margin: 0, fontSize: 12, color: "var(--info-text, #3730a3)" }}>
                    View-only access. You can view this setup but cannot make changes.
                    Contact an owner or manager to update this information.
                  </p>
                </div>
              )}

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <Btn variant="ghost" onClick={() => setStep(hasBrands ? "brands" : "pricing")}>Back</Btn>
                <Btn variant="secondary" onClick={handleSaveDraft} loading={saveDraftAction.loading} disabled={readOnly}>
                  Save Draft
                </Btn>
                <Btn
                  variant={hasActiveArea ? "primary" : "secondary"}
                  disabled={!hasActiveArea || readOnly}
                  onClick={handlePublish}
                  loading={publishAction.loading}
                >
                  {hasActiveArea ? "Publish Service" : "Publish (add area first)"}
                </Btn>
              </div>

              {bookabilityLoading && (
                <p style={{ marginTop: 12, fontSize: 12, color: "var(--text-tertiary)" }}>
                  Checking your bookability status…
                </p>
              )}
              {!bookabilityLoading && bookabilityStatus && (
                <div style={{
                  marginTop: 14, padding: "12px 16px", borderRadius: 10,
                  background: bookabilityStatus.is_bookable ? "var(--success-bg)" : "var(--warning-bg)",
                  border: `1px solid ${bookabilityStatus.is_bookable ? "var(--success-border)" : "var(--warning-border)"}`,
                }}>
                  {bookabilityStatus.is_bookable ? (
                    <>
                      <p style={{ margin: "0 0 4px", fontSize: 13, fontWeight: 700, color: "var(--success-text)" }}>
                        Your Home Services business is now bookable.
                      </p>
                      <p style={{ margin: 0, fontSize: 12, color: "var(--success-text)" }}>
                        Customers can be matched to your services in active service areas.
                      </p>
                    </>
                  ) : (
                    <>
                      <p style={{ margin: "0 0 4px", fontSize: 13, fontWeight: 700, color: "var(--warning-text)" }}>
                        Services published, but your business is not bookable yet.
                      </p>
                      <p style={{ margin: "0 0 8px", fontSize: 12, color: "var(--warning-text)" }}>
                        Complete the remaining setup items below.
                      </p>
                      {bookabilityStatus.bookability_blockers.length > 0 && (
                        <ul style={{ margin: 0, paddingLeft: 18 }}>
                          {bookabilityStatus.bookability_blockers.map(b => (
                            <li key={b.code} style={{ fontSize: 12, color: "var(--warning-text)", marginBottom: 4 }}>
                              {b.message}
                            </li>
                          ))}
                        </ul>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

// ── Helper sub-components ─────────────────────────────────────────────────────
function InfoCard({ icon, label, value, sub, warn }: {
  icon: React.ReactNode; label: string; value: string; sub?: string; warn?: boolean;
}) {
  return (
    <div style={{
      padding: "14px 16px", borderRadius: 10,
      border: `1px solid ${warn ? "var(--warning-border)" : "var(--border)"}`,
      background: warn ? "var(--warning-bg)" : "var(--surface)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ color: warn ? "var(--warning-text)" : "var(--text-tertiary)" }}>{icon}</span>
        <span style={{ fontSize: 10, fontWeight: 700, color: warn ? "var(--warning-text)" : "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: 1 }}>{label}</span>
      </div>
      <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: warn ? "var(--warning-text)" : "var(--text-primary)" }}>{value}</p>
      {sub && <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{sub}</p>}
    </div>
  );
}

function TypePricingCard({ tp, onUpdate, onPreview, previewLoading }: {
  tp: TypePricingState;
  onUpdate: (field: "tenantMin" | "tenantMax", val: string) => void;
  onPreview: () => void;
  previewLoading: boolean;
}) {
  const min = parseFloat(tp.tenantMin);
  const max = parseFloat(tp.tenantMax);
  const minErr = Number.isFinite(min) && min < tp.adminFloor
    ? `Cannot be below ₹${tp.adminFloor}` : null;
  const maxErr = Number.isFinite(max) && max > tp.adminCeiling
    ? `Cannot exceed ₹${tp.adminCeiling}` : null;

  return (
    <div style={{
      padding: "18px 20px", borderRadius: 12, border: "1px solid var(--border)",
      background: "var(--surface)", display: "flex", flexDirection: "column", gap: 14,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <p style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>{safeText(tp.typeName)}</p>
        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
          Working range: {safeCur(tp.adminFloor)} – {safeCur(tp.adminCeiling)}
        </span>
      </div>

      {/* Range slider visual */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>{safeCur(tp.adminFloor)}</span>
        <div style={{ flex: 1, height: 4, background: "var(--border)", borderRadius: 2, position: "relative" }}>
          {Number.isFinite(min) && Number.isFinite(max) && (
            <div style={{
              position: "absolute", top: 0, height: "100%", borderRadius: 2,
              background: "var(--brand)",
              left: `${Math.max(0, ((min - tp.adminFloor) / (tp.adminCeiling - tp.adminFloor)) * 100)}%`,
              right: `${Math.max(0, 100 - ((max - tp.adminFloor) / (tp.adminCeiling - tp.adminFloor)) * 100)}%`,
            }} />
          )}
        </div>
        <span>{safeCur(tp.adminCeiling)}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
            Your Minimum Price (₹)
          </label>
          <input
            type="number" value={tp.tenantMin} min={tp.adminFloor} max={tp.adminCeiling}
            onChange={e => onUpdate("tenantMin", e.target.value)}
            style={{
              width: "100%", padding: "9px 12px", fontSize: 14, boxSizing: "border-box",
              border: `1px solid ${minErr ? "var(--danger-border)" : "var(--border)"}`,
              borderRadius: 8, background: "var(--surface)", color: "var(--text-primary)",
              fontFamily: "inherit", outline: "none",
            }}
          />
          {minErr && <p style={{ margin: "3px 0 0", fontSize: 11, color: "var(--danger-text)" }}>{minErr}</p>}
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
            Your Maximum Price (₹)
          </label>
          <input
            type="number" value={tp.tenantMax} min={tp.adminFloor} max={tp.adminCeiling}
            onChange={e => onUpdate("tenantMax", e.target.value)}
            style={{
              width: "100%", padding: "9px 12px", fontSize: 14, boxSizing: "border-box",
              border: `1px solid ${maxErr ? "var(--danger-border)" : "var(--border)"}`,
              borderRadius: 8, background: "var(--surface)", color: "var(--text-primary)",
              fontFamily: "inherit", outline: "none",
            }}
          />
          {maxErr && <p style={{ margin: "3px 0 0", fontSize: 11, color: "var(--danger-text)" }}>{maxErr}</p>}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Customer Price Options Preview</p>
          <Btn size="sm" variant="ghost" loading={previewLoading} onClick={onPreview}>
            Preview
          </Btn>
        </div>
        {tp.preview ? (
          <PricePreviewBand preview={tp.preview} />
        ) : (
          <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>
            Click Preview to see Low / Mid / High options customers will see.
          </p>
        )}
      </div>
    </div>
  );
}

function BrandOverrideRow({ bp, onChange, onPreview }: {
  bp: BrandPricingState;
  onChange: (field: "enabled" | "tenantMin" | "tenantMax", val: string | boolean) => void;
  onPreview: () => void;
}) {
  return (
    <div style={{
      padding: "14px 16px", borderRadius: 10, border: "1px solid var(--border)",
      background: bp.enabled ? "var(--surface)" : "var(--surface-sunken)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: bp.enabled ? 12 : 0 }}>
        <input type="checkbox" checked={bp.enabled} onChange={e => onChange("enabled", e.target.checked)}
          style={{ width: 16, height: 16, cursor: "pointer" }} />
        <div style={{
          width: 32, height: 32, borderRadius: 8, background: "var(--brand)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 12, fontWeight: 700, color: "#fff",
        }}>
          {safeText(bp.brandName).slice(0, 2).toUpperCase()}
        </div>
        <div>
          <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{safeText(bp.brandName)}</p>
          {!bp.enabled && <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>Using type range</p>}
        </div>
      </div>
      {bp.enabled && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 10, alignItems: "end" }}>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Min (₹)</label>
              <input type="number" value={bp.tenantMin} onChange={e => onChange("tenantMin", e.target.value)}
                style={{
                  width: "100%", padding: "8px 10px", fontSize: 13, boxSizing: "border-box",
                  border: "1px solid var(--border)", borderRadius: 8,
                  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                }} />
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Max (₹)</label>
              <input type="number" value={bp.tenantMax} onChange={e => onChange("tenantMax", e.target.value)}
                style={{
                  width: "100%", padding: "8px 10px", fontSize: 13, boxSizing: "border-box",
                  border: "1px solid var(--border)", borderRadius: 8,
                  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                }} />
            </div>
            <Btn size="sm" variant="ghost" onClick={onPreview}>Preview</Btn>
          </div>
          {bp.preview && <PricePreviewBand preview={bp.preview} />}
        </div>
      )}
    </div>
  );
}

// ── Service catalog card ──────────────────────────────────────────────────────
function ServiceCard({
  service, enabled, onSetup,
}: {
  service: AdminMasterServiceRow;
  enabled: TenantEnabledService | null;
  onSetup: () => void;
}) {
  const isEnabled = enabled?.is_enabled && enabled?.is_active;
  const isPublished = enabled?.setup_status === "published";

  return (
    <div style={{
      padding: "20px", borderRadius: 14, border: "1px solid var(--border)",
      background: "var(--surface)", display: "flex", flexDirection: "column", gap: 12,
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 42, height: 42, borderRadius: 10, background: "var(--brand)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Wrench size={20} style={{ color: "#fff" }} />
          </div>
          <div>
            <p style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>{safeText(service.service_name)}</p>
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
              {service.pricing_model === "type_based" ? "Type-based" : "Fixed"} · {service.job_type}
            </p>
          </div>
        </div>
        {isPublished ? (
          <Badge variant="success">Published</Badge>
        ) : isEnabled ? (
          <Badge variant="warning">Draft</Badge>
        ) : null}
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {service.is_brand_required && (
          <span style={{
            fontSize: 11, padding: "3px 8px", borderRadius: 999,
            background: "var(--surface-sunken)", color: "var(--text-secondary)",
            border: "1px solid var(--border)",
          }}>Brand pricing</span>
        )}
        {service.is_type_required && (
          <span style={{
            fontSize: 11, padding: "3px 8px", borderRadius: 999,
            background: "var(--surface-sunken)", color: "var(--text-secondary)",
            border: "1px solid var(--border)",
          }}>Types required</span>
        )}
        <span style={{
          fontSize: 11, padding: "3px 8px", borderRadius: 999,
          background: "var(--surface-sunken)", color: "var(--text-secondary)",
          border: "1px solid var(--border)",
        }}>
          Admin range: {safeCur(service.min_price)} – {safeCur(service.max_price)}
        </span>
      </div>

      <Btn
        size="sm"
        variant={isEnabled ? "secondary" : "primary"}
        onClick={onSetup}
      >
        {isEnabled ? (isPublished ? "Manage" : "Continue Setup") : "Set Up"}
        <ArrowRight size={13} style={{ marginLeft: 5 }} />
      </Btn>
    </div>
  );
}

// ── Enabled services list ─────────────────────────────────────────────────────
function EnabledServicesList({
  enabledServices, availableServices, onManage, onDisable,
}: {
  enabledServices: TenantEnabledService[];
  availableServices: AdminMasterServiceRow[];
  onManage: (svc: TenantEnabledService) => void;
  onDisable: (masterServiceId: string) => void;
}) {
  if (enabledServices.length === 0) return null;
  const published = enabledServices.filter(s => s.setup_status === "published" && s.is_active);
  if (published.length === 0) return null;

  return (
    <div style={{ marginTop: 32 }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px" }}>
        Your Active Services ({published.length})
      </h2>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)" }}>
              {["Service", "Status", "Setup Status", "Actions"].map(h => (
                <th key={h} style={{
                  padding: "10px 14px", textAlign: "left", fontWeight: 700,
                  color: "var(--text-secondary)", borderBottom: "1px solid var(--border)",
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {enabledServices.map((svc, i) => {
              const master = availableServices.find(a => a.service_id === svc.master_service_id);
              return (
                <tr key={svc.tenant_service_id} style={{ background: i % 2 === 0 ? "transparent" : "var(--surface-sunken)" }}>
                  <td style={{ padding: "12px 14px", fontWeight: 600 }}>
                    {safeText(svc.tenant_display_name ?? master?.service_name)}
                  </td>
                  <td style={{ padding: "12px 14px" }}>
                    <Badge variant={svc.is_active ? "success" : "warning"}>
                      {svc.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td style={{ padding: "12px 14px" }}>
                    <Badge variant={svc.setup_status === "published" ? "success" : "muted"}>
                      {safeText(svc.setup_status, "draft")}
                    </Badge>
                  </td>
                  <td style={{ padding: "12px 14px" }}>
                    <div style={{ display: "flex", gap: 8 }}>
                      <Btn size="sm" variant="secondary" onClick={() => onManage(svc)}>Manage</Btn>
                      <Btn size="sm" variant="ghost" onClick={() => onDisable(svc.master_service_id)}>Disable</Btn>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function HomeServicesServiceSetupPage() {
  const tenant = useTenant();
  const [wizardService, setWizardService] = useState<AdminMasterServiceRow | null>(null);
  const [wizardEnabled, setWizardEnabled] = useState<TenantEnabledService | null>(null);

  const availableApi = useApi(useCallback(() => homeServicesSetupApi.listAvailable(), []), []);
  const enabledApi = useApi(useCallback(() => homeServicesSetupApi.listEnabled(), []), []);

  const disableAction = useAction(useCallback((masterServiceId: string) =>
    homeServicesSetupApi.disable(masterServiceId), []));

  function openWizard(service: AdminMasterServiceRow) {
    const enabled = (enabledApi.data?.services ?? []).find(s => s.master_service_id === service.service_id) ?? null;
    setWizardEnabled(enabled);
    setWizardService(service);
  }

  function openWizardFromEnabled(svc: TenantEnabledService) {
    const master = (availableApi.data?.services ?? []).find(s => s.service_id === svc.master_service_id);
    if (master) {
      setWizardEnabled(svc);
      setWizardService(master);
    }
  }

  async function handleDisable(masterServiceId: string) {
    try {
      await disableAction.execute(masterServiceId);
      await enabledApi.refetch();
    } catch { /* surface via action.error below if needed */ }
  }

  // ── Scope guard ───────────────────────────────────────────────────────────
  if (tenant.loading) {
    return (
      <TenantLayout>
        <div style={{ padding: "48px 0", display: "flex", flexDirection: "column", gap: 12, maxWidth: 600 }}>
          <Skeleton height={32} width={300} />
          <Skeleton height={16} width={480} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginTop: 16 }}>
            {[1,2,3].map(i => <Skeleton key={i} height={160} />)}
          </div>
        </div>
      </TenantLayout>
    );
  }

  if (!isHomeServicesTenant(tenant)) {
    return (
      <TenantLayout>
        <div style={{ maxWidth: 540, padding: "80px 0" }}>
          <div style={{
            padding: "32px 28px", borderRadius: 14,
            border: "1px solid var(--border)", background: "var(--surface)", textAlign: "center",
          }}>
            <Shield size={36} style={{ color: "var(--text-tertiary)", margin: "0 auto 16px" }} />
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px" }}>Setup wizard not available</h2>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>
              This setup wizard is available only for Home Services.
              This vertical uses a different setup model.
            </p>
          </div>
        </div>
      </TenantLayout>
    );
  }

  const availableServices = availableApi.data?.services ?? [];
  const enabledServices = enabledApi.data?.services ?? [];

  return (
    <TenantLayout>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, margin: "0 0 4px" }}>Service Setup</h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>
          Choose the services you provide, select supported types and brands, and set your provider price ranges.
        </p>
      </div>

      {/* Info banner */}
      <div style={{
        padding: "12px 16px", borderRadius: 10, marginBottom: 24,
        background: "var(--info-bg, #eff6ff)", border: "1px solid var(--info-border, #bfdbfe)",
        display: "flex", gap: 10,
      }}>
        <Info size={15} style={{ color: "var(--info-text, #1d4ed8)", flexShrink: 0, marginTop: 1 }} />
        <p style={{ fontSize: 12, color: "var(--info-text, #1d4ed8)", margin: 0 }}>
          You can only select services from the admin-approved catalog.
          Customer Low / Mid / High price options are generated automatically from your price range + platform fee.
        </p>
      </div>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginBottom: 28 }}>
        <MiniStat icon={<Package size={16}/>} label="Available Services"
          value={availableServices.length > 0 ? String(availableServices.length) : "—"} />
        <MiniStat icon={<CheckCircle2 size={16}/>} label="Published"
          value={String(enabledServices.filter(s => s.setup_status === "published" && s.is_active).length)} />
        <MiniStat icon={<BarChart2 size={16}/>} label="Draft / Setup"
          value={String(enabledServices.filter(s => s.setup_status !== "published" || !s.is_active).length)} />
      </div>

      {/* Available services */}
      {availableApi.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {[1,2,3,4].map(i => <Skeleton key={i} height={180} />)}
        </div>
      ) : availableApi.error ? (
        <ErrBanner title="We couldn't load the service catalog" error={availableApi.error}
          requestId={availableApi.requestId} onRetry={availableApi.refetch} />
      ) : availableServices.length === 0 ? (
        <EmptyState
          icon={<Wrench size={32} />}
          title="No services available"
          description="The admin hasn't published any Home Services catalog items yet."
        />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {availableServices.map(svc => (
            <ServiceCard
              key={svc.service_id}
              service={svc}
              enabled={enabledServices.find(e => e.master_service_id === svc.service_id) ?? null}
              onSetup={() => openWizard(svc)}
            />
          ))}
        </div>
      )}

      {/* Enabled services list */}
      {!enabledApi.loading && enabledServices.length > 0 && (
        <EnabledServicesList
          enabledServices={enabledServices}
          availableServices={availableServices}
          onManage={openWizardFromEnabled}
          onDisable={handleDisable}
        />
      )}

      {/* Wizard modal */}
      {wizardService && (
        <ServiceSetupWizard
          service={wizardService}
          enabled={wizardEnabled}
          onClose={() => setWizardService(null)}
          onSaved={async () => {
            setWizardService(null);
            await enabledApi.refetch();
          }}
        />
      )}
    </TenantLayout>
  );
}

function MiniStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div style={{ padding: "16px 18px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ color: "var(--text-tertiary)" }}>{icon}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
      </div>
      <p style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}>{value}</p>
    </div>
  );
}
