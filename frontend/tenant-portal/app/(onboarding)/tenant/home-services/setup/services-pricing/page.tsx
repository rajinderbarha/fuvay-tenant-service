"use client";
import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search, Info, ArrowRight, Tag, RefreshCw,
} from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { Card, Btn, Badge, Skeleton, Input } from "../../../../../../components/shared/ui";
import {
  homeServicesSetupApi, ServiceOSError,
  type AdminMasterServiceRow, type TenantEnabledService,
  type HsSetupType, type HsSetupAvailableType, type HsSetupBrand, type HsTypePricing, type HsBrandPricing,
} from "../../../../../../lib/api";

const SETUP_STEPS = [
  "overview", "business-profile", "documents", "services-pricing",
  "coverage-availability", "staff", "finance", "review",
] as const;
const STEP_NUMBER = SETUP_STEPS.indexOf("services-pricing") + 1;
const TOTAL_STEPS = SETUP_STEPS.length;

interface ServiceGroup {
  id: string; name: string; services: AdminMasterServiceRow[];
}

function money(v: number | null | undefined) {
  if (v === null || v === undefined) return "—";
  return `₹${v.toLocaleString("en-IN")}`;
}

export default function ServicesPricingPage() {
  return (
    <Suspense fallback={null}>
      <ServicesPricingPageContent />
    </Suspense>
  );
}

function ServicesPricingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Set when this page is opened from the ongoing (post-onboarding)
  // Services & Pricing workspace's "Add services" action rather than the
  // onboarding flow -- Back/Save & continue return there instead of
  // advancing to the next onboarding step, since there IS no "next step"
  // once a tenant is already active.
  const returnTo = searchParams.get("return_to");
  const [available, setAvailable] = useState<AdminMasterServiceRow[] | null>(null);
  const [enabledList, setEnabledList] = useState<TenantEnabledService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [selectedServiceId, setSelectedServiceId] = useState<string | null>(null);

  const [types, setTypes] = useState<HsSetupAvailableType[] | null>(null);
  const [brands, setBrands] = useState<HsSetupBrand[] | null>(null);
  const [typePricing, setTypePricing] = useState<HsTypePricing[] | null>(null);
  // Type-required services scope brand overrides per type (backend rejects
  // brand pricing without a service_type_id in that case) -- keyed by
  // service_type_id. Non-type-required services use the flat, type-less list.
  const [brandPricing, setBrandPricing] = useState<HsBrandPricing[] | null>(null);
  const [brandPricingByType, setBrandPricingByType] = useState<Record<string, HsBrandPricing[]>>({});
  // Per-brand price rows are opt-in per type -- by default every brand under
  // a type simply inherits that type's Min/Max (sparse inheritance, already
  // resolved server-side), so the tenant only has to set ONE price per type
  // unless they deliberately want a brand to differ.
  const [brandOverrideOpen, setBrandOverrideOpen] = useState<Record<string, boolean>>({});
  const [detailLoading, setDetailLoading] = useState(false);

  const [defaultMin, setDefaultMin] = useState("");
  const [defaultMax, setDefaultMax] = useState("");
  const [visitFee, setVisitFee] = useState("");
  const [emergencySurcharge, setEmergencySurcharge] = useState("");
  const [toggling, setToggling] = useState(false);
  const [savingPrice, setSavingPrice] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([homeServicesSetupApi.listAvailable(), homeServicesSetupApi.listEnabled()])
      .then(([a, e]) => {
        setAvailable(a.services);
        setEnabledList(e.services);
      })
      .catch((err: unknown) => setError(err instanceof ServiceOSError ? err.message : "We couldn't load your services catalog."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const groups: ServiceGroup[] = useMemo(() => {
    if (!available) return [];
    const map = new Map<string, ServiceGroup>();
    for (const s of available) {
      const gid = s.service_group_id ?? "ungrouped";
      const gname = s.service_group_name ?? "Other services";
      if (!map.has(gid)) map.set(gid, { id: gid, name: gname, services: [] });
      map.get(gid)!.services.push(s);
    }
    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [available]);

  const filteredGroups = useMemo(() => {
    if (!search.trim()) return groups;
    const q = search.trim().toLowerCase();
    return groups.filter(g => g.name.toLowerCase().includes(q));
  }, [groups, search]);

  const enabledByMasterService = useMemo(() => {
    const map = new Map<string, TenantEnabledService>();
    for (const e of enabledList) map.set(e.master_service_id, e);
    return map;
  }, [enabledList]);

  // Default to the first group/service once data loads.
  useEffect(() => {
    if (!selectedGroupId && groups.length > 0) setSelectedGroupId(groups[0].id);
  }, [groups, selectedGroupId]);
  useEffect(() => {
    const group = groups.find(g => g.id === selectedGroupId);
    if (group && !group.services.some(s => s.service_id === selectedServiceId)) {
      setSelectedServiceId(group.services[0]?.service_id ?? null);
    }
  }, [selectedGroupId, groups, selectedServiceId]);

  const selectedGroup = groups.find(g => g.id === selectedGroupId) ?? null;
  const selectedService = selectedGroup?.services.find(s => s.service_id === selectedServiceId) ?? null;
  const enrolled = selectedService ? enabledByMasterService.get(selectedService.service_id) ?? null : null;
  const isInspectionMode = selectedService?.pricing_model === "inspection_quote" || selectedService?.pricing_model === "quote";

  // Load type/brand detail whenever the enrolled tenant_service changes.
  useEffect(() => {
    setTypes(null); setBrands(null); setTypePricing(null); setBrandPricing(null); setBrandPricingByType({}); setBrandOverrideOpen({});
    if (!enrolled) {
      setDefaultMin(""); setDefaultMax(""); setVisitFee(""); setEmergencySurcharge("");
      return;
    }
    setDefaultMin(enrolled.tenant_min_price != null ? String(enrolled.tenant_min_price) : "");
    setDefaultMax(enrolled.tenant_max_price != null ? String(enrolled.tenant_max_price) : "");
    setVisitFee(enrolled.tenant_visit_fee != null ? String(enrolled.tenant_visit_fee) : "");
    setEmergencySurcharge(enrolled.tenant_emergency_surcharge != null ? String(enrolled.tenant_emergency_surcharge) : "");
    setDetailLoading(true);
    const tsid = enrolled.tenant_service_id;
    Promise.all([
      enrolled.requires_type ? homeServicesSetupApi.getAvailableTypes(tsid) : Promise.resolve({ types: [] }),
      enrolled.requires_brand ? homeServicesSetupApi.getAvailableBrands(tsid) : Promise.resolve({ brands: [] }),
      enrolled.requires_type ? homeServicesSetupApi.getTypePricing(tsid) : Promise.resolve({ types: [] }),
      // Brand pricing must be scoped per type for type-required services
      // (the backend rejects a type-less brand override in that case) --
      // fetched below, once typePricing tells us which types are selected.
      enrolled.requires_brand && !enrolled.requires_type ? homeServicesSetupApi.getBrandPricing(tsid) : Promise.resolve({ brands: [] }),
    ])
      .then(async ([t, b, tp, bp]) => {
        setTypes(t.types); setBrands(b.brands);
        setTypePricing(tp.types); setBrandPricing(bp.brands);
        if (enrolled.requires_brand && enrolled.requires_type && tp.types.length > 0) {
          await reloadBrandPricingByType(tsid, tp.types, b.brands);
        }
      })
      .catch(() => {})
      .finally(() => setDetailLoading(false));
  }, [enrolled?.tenant_service_id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleToggleOffer(next: boolean) {
    if (!selectedService) return;
    setToggling(true);
    setError(null);
    try {
      if (next) {
        await homeServicesSetupApi.enable({ master_service_id: selectedService.service_id });
      } else {
        await homeServicesSetupApi.disable(selectedService.service_id);
      }
      const [a, e] = await Promise.all([homeServicesSetupApi.listAvailable(), homeServicesSetupApi.listEnabled()]);
      setAvailable(a.services); setEnabledList(e.services);
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not update this offering.");
    } finally {
      setToggling(false);
    }
  }

  async function handleSaveDefaultPrice() {
    if (!enrolled) return;
    setSavingPrice(true);
    try {
      const payload: { tenant_min_price?: number; tenant_max_price?: number; tenant_visit_fee?: number; tenant_emergency_surcharge?: number } = {};
      if (defaultMin) payload.tenant_min_price = Number(defaultMin);
      if (defaultMax) payload.tenant_max_price = Number(defaultMax);
      if (visitFee) payload.tenant_visit_fee = Number(visitFee);
      if (emergencySurcharge) payload.tenant_emergency_surcharge = Number(emergencySurcharge);
      const updated = await homeServicesSetupApi.updateEnabledService(enrolled.tenant_service_id, payload);
      setEnabledList(list => list.map(e => e.tenant_service_id === updated.tenant_service_id ? updated : e));
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save pricing.");
    } finally {
      setSavingPrice(false);
    }
  }

  // One row per admin-mapped brand candidate, not just brands that already
  // have a saved price -- selecting a brand for a type-required service
  // happens implicitly by entering its price (the backend upserts the
  // scoped TenantServiceBrand row on save), so every candidate must be
  // fillable from the start, not only ones with an existing override.
  function mergeBrandCandidatesWithPricing(
    candidates: HsSetupBrand[], priced: HsBrandPricing[], typeMin: number | null, typeMax: number | null,
  ): HsBrandPricing[] {
    const byBrandId = new Map(priced.map(p => [p.brand_id, p]));
    // Only brands the tenant has actually enabled (top "Brand" checkboxes) may
    // appear here -- an unchecked brand must never show under any Type.
    return candidates.filter(c => c.is_enabled).map(c => {
      const existing = byBrandId.get(c.brand_id);
      if (existing) return existing;
      // No brand-specific override yet: pre-fill with the Type's own price so
      // the tenant sees what this brand will actually charge (inherited),
      // not a blank box -- editing and saving is what creates a real override.
      return {
        tenant_service_brand_id: c.brand_id, brand_id: c.brand_id, name: c.name,
        can_override_price: c.can_override_price ?? true, is_routing_only: false,
        admin_floor_price: null, admin_ceiling_price: null, platform_fee_percent: 10,
        tenant_min_price: typeMin, tenant_max_price: typeMax, customer_price_preview: null,
      };
    });
  }

  async function reloadBrandPricingByType(tsid: string, typePricingList: HsTypePricing[], brandCandidates: HsSetupBrand[]) {
    if (typePricingList.length === 0) { setBrandPricingByType({}); return; }
    const entries = await Promise.all(typePricingList.map(async pt => {
      const r = await homeServicesSetupApi.getBrandPricing(tsid, pt.service_type_id);
      return [pt.service_type_id,
        mergeBrandCandidatesWithPricing(brandCandidates, r.brands, pt.tenant_min_price, pt.tenant_max_price)] as const;
    }));
    setBrandPricingByType(Object.fromEntries(entries));
  }

  async function toggleType(type: HsSetupAvailableType) {
    if (!enrolled || !types) return;
    const current = types.filter(t => t.is_enabled).map(t => t.service_type_id);
    const next = type.is_enabled
      ? current.filter(id => id !== type.service_type_id)
      : [...current, type.service_type_id];
    await homeServicesSetupApi.setTypes(enrolled.tenant_service_id, next);
    const [avail, tp] = await Promise.all([
      homeServicesSetupApi.getAvailableTypes(enrolled.tenant_service_id),
      homeServicesSetupApi.getTypePricing(enrolled.tenant_service_id),
    ]);
    setTypes(avail.types);
    setTypePricing(tp.types);
    if (enrolled.requires_brand && brands) await reloadBrandPricingByType(enrolled.tenant_service_id, tp.types, brands);
  }

  async function toggleBrand(brand: HsSetupBrand) {
    if (!enrolled || !brands) return;
    const current = brands.filter(b => b.is_enabled).map(b => b.brand_id);
    const next = brand.is_enabled ? current.filter(id => id !== brand.brand_id) : [...current, brand.brand_id];
    await homeServicesSetupApi.setBrands(enrolled.tenant_service_id, next);
    const avail = await homeServicesSetupApi.getAvailableBrands(enrolled.tenant_service_id);
    setBrands(avail.brands);
    if (enrolled.requires_type) {
      await reloadBrandPricingByType(enrolled.tenant_service_id, typePricing ?? [], avail.brands);
    } else {
      const bp = await homeServicesSetupApi.getBrandPricing(enrolled.tenant_service_id);
      setBrandPricing(bp.brands);
    }
  }

  async function handleTypePriceChange(serviceTypeId: string, min: string, max: string) {
    if (!enrolled) return;
    const res = await homeServicesSetupApi.setTypePricing(enrolled.tenant_service_id, serviceTypeId, Number(min || 0), Number(max || 0));
    setTypePricing(res.types);
  }

  async function handleBrandPriceChange(brandId: string, min: string, max: string, serviceTypeId?: string) {
    if (!enrolled) return;
    const res = await homeServicesSetupApi.setBrandPricing(enrolled.tenant_service_id, brandId, Number(min || 0), Number(max || 0), serviceTypeId);
    if (serviceTypeId) {
      const tp = (typePricing ?? []).find(t => t.service_type_id === serviceTypeId);
      setBrandPricingByType(prev => ({
        ...prev,
        [serviceTypeId]: mergeBrandCandidatesWithPricing(
          brands ?? [], res.brands, tp?.tenant_min_price ?? null, tp?.tenant_max_price ?? null),
      }));
      return;
    }
    setBrandPricing(res.brands);
  }

  function handleBack() {
    router.push(returnTo || "/tenant/home-services/setup/overview");
  }

  async function handleSaveDraft() {
    if (!enrolled) return;
    setSaving(true);
    try {
      await homeServicesSetupApi.saveDraft(enrolled.tenant_service_id);
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save draft.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveAndContinue() {
    setSaving(true);
    try {
      if (enrolled) await homeServicesSetupApi.saveDraft(enrolled.tenant_service_id);
      router.push(returnTo || "/tenant/home-services/setup/coverage-availability");
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save your services.");
    } finally {
      setSaving(false);
    }
  }

  const configuredCount = enabledList.filter(e => e.setup_status === "published" || e.is_enabled).length;

  if (loading) {
    return (
      <OnboardingShell activeNav="services-pricing" showProgress={!returnTo}>
        <Skeleton height={70} style={{ marginBottom: 20 }}/>
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 280px", gap: 20 }}>
          <Skeleton height={520}/><Skeleton height={520}/><Skeleton height={520}/>
        </div>
      </OnboardingShell>
    );
  }

  if (error && !available) {
    return (
      <OnboardingShell activeNav="services-pricing" showProgress={!returnTo}>
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your services catalog.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </OnboardingShell>
    );
  }

  if (!available) return null;

  return (
    <OnboardingShell activeNav="services-pricing" showProgress={!returnTo}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap", marginBottom: 4 }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 4px" }}>TENANT ONBOARDING</p>
          <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Services &amp; pricing</h1>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "6px 0 0" }}>Choose what you provide and set your own prices.</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 6px" }}>
            {returnTo ? "Add services" : `Step ${STEP_NUMBER} of ${TOTAL_STEPS}`}
          </p>
          <Badge variant={configuredCount > 0 ? "success" : "muted"} size="lg">
            {configuredCount === 0 ? "No services configured" : `${configuredCount} service${configuredCount === 1 ? "" : "s"} configured`}
          </Badge>
        </div>
      </div>

      {error && (
        <div role="alert" style={{
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
          padding: "10px 14px", marginTop: 14, background: "var(--danger-bg)",
          border: "1px solid var(--danger-border)", borderRadius: "var(--radius-md)",
        }}>
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{error}</p>
          <button onClick={() => setError(null)} style={{ background: "none", border: "none", color: "var(--danger-text)", cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
            Dismiss
          </button>
        </div>
      )}

      <style>{`
        .svc-grid { display: grid; grid-template-columns: 280px 1fr 300px; gap: 20px; align-items: start; margin-top: 20px; }
        @media (max-width: 1200px) { .svc-grid { grid-template-columns: 240px 1fr; } .svc-grid > :nth-child(3) { grid-column: 1 / -1; } }
        @media (max-width: 900px) { .svc-grid { grid-template-columns: 1fr; } .svc-grid > :nth-child(3) { grid-column: auto; } }
        .svc-row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        @media (max-width: 480px) { .svc-row2 { grid-template-columns: 1fr; } }
      `}</style>

      <div className="svc-grid">
        {/* Left: Service Groups */}
        <Card padding={0}>
          <div style={{ padding: "16px 16px 12px" }}>
            <h2 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>Service groups</h2>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input aria-label="Search service groups" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search groups"
                style={{ width: "100%", height: 36, padding: "0 12px 0 32px", fontSize: 13, background: "var(--surface-sunken)",
                  border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }}/>
            </div>
          </div>
          <div style={{ maxHeight: 560, overflowY: "auto" }}>
            {filteredGroups.length === 0 && (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: "16px" }}>No service groups match your search.</p>
            )}
            {filteredGroups.map(g => {
              const configured = g.services.filter(s => enabledByMasterService.has(s.service_id)).length;
              const active = g.id === selectedGroupId;
              return (
                <button key={g.id} onClick={() => setSelectedGroupId(g.id)} style={{
                  display: "flex", alignItems: "center", gap: 12, width: "100%", textAlign: "left",
                  padding: "12px 16px", border: "none", borderLeft: active ? "3px solid var(--brand)" : "3px solid transparent",
                  background: active ? "var(--accent-muted)" : "transparent", cursor: "pointer", fontFamily: "inherit",
                }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 10, background: "var(--surface-sunken)", flexShrink: 0,
                    display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)",
                  }}><Tag size={16}/></div>
                  <div style={{ minWidth: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, margin: 0, color: "var(--text-primary)" }}>{g.name}</p>
                    <p style={{ fontSize: 11.5, margin: "2px 0 0", color: configured > 0 ? "var(--brand)" : "var(--text-tertiary)" }}>
                      {configured} of {g.services.length} configured
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </Card>

        {/* Center: Service configuration */}
        <div style={{ minWidth: 0 }}>
          {!selectedGroup ? (
            <Card><p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Select a service group to configure it.</p></Card>
          ) : (
            <Card>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>{selectedGroup.name}</h2>
              <div role="tablist" style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 16, overflowX: "auto" }}>
                {selectedGroup.services.map(s => {
                  const active = s.service_id === selectedServiceId;
                  return (
                    <button key={s.service_id} role="tab" aria-selected={active} onClick={() => setSelectedServiceId(s.service_id)}
                      style={{
                        padding: "10px 14px", background: "none", border: "none", borderBottom: active ? "2px solid var(--brand)" : "2px solid transparent",
                        color: active ? "var(--brand)" : "var(--text-secondary)", fontWeight: active ? 700 : 500, fontSize: 13,
                        cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap",
                      }}>
                      {s.job_type ? s.job_type.charAt(0).toUpperCase() + s.job_type.slice(1) : s.service_name}
                    </button>
                  );
                })}
              </div>

              {selectedService && (
                <>
                  <div style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", marginBottom: 16,
                    background: "var(--info-bg)", border: "1px solid var(--info-border)", borderRadius: "var(--radius-md)",
                  }}>
                    <Info size={14} style={{ color: "var(--info-text)", flexShrink: 0 }}/>
                    <p style={{ fontSize: 12.5, color: "var(--info-text)", margin: 0 }}>
                      Pricing by {selectedService.is_type_required ? "Type" : ""}{selectedService.is_type_required && selectedService.is_brand_required ? " + " : ""}{selectedService.is_brand_required ? "Brand" : ""}
                      {!selectedService.is_type_required && !selectedService.is_brand_required ? "Fixed offering" : ""}
                      {isInspectionMode ? " · Inspection estimate required" : ""}
                    </p>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>Offer this service</span>
                    <label style={{ position: "relative", display: "inline-block", width: 44, height: 24 }}>
                      <input type="checkbox" aria-label={`Offer ${selectedService.service_name}`} checked={!!enrolled} disabled={toggling}
                        onChange={e => handleToggleOffer(e.target.checked)}
                        style={{ opacity: 0, width: 0, height: 0 }}/>
                      <span onClick={() => !toggling && handleToggleOffer(!enrolled)} style={{
                        position: "absolute", inset: 0, borderRadius: 999, cursor: "pointer",
                        background: enrolled ? "var(--brand)" : "var(--border)", transition: "background 0.15s",
                      }}>
                        <span style={{
                          position: "absolute", top: 3, left: enrolled ? 23 : 3, width: 18, height: 18, borderRadius: "50%",
                          background: "#fff", transition: "left 0.15s",
                        }}/>
                      </span>
                    </label>
                  </div>

                  {!enrolled ? (
                    <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Turn this on to configure pricing for {selectedService.job_type || selectedService.service_name}.</p>
                  ) : detailLoading ? (
                    <Skeleton height={200}/>
                  ) : (
                    <>
                      {isInspectionMode ? (
                        <div className="svc-row2" style={{ marginBottom: 18 }}>
                          <Input label="Visit fee" type="number" value={visitFee} onChange={setVisitFee} placeholder="299"/>
                          <div style={{ display: "flex", alignItems: "flex-end" }}>
                            <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
                              Adjusted in the final bill if the customer approves the estimate.
                            </p>
                          </div>
                        </div>
                      ) : (
                        <div className="svc-row2" style={{ marginBottom: 18 }}>
                          <Input label="Minimum price" type="number" value={defaultMin} onChange={setDefaultMin} placeholder="600"/>
                          <Input label="Maximum price" type="number" value={defaultMax} onChange={setDefaultMax} placeholder="900"/>
                        </div>
                      )}
                      <div className="svc-row2" style={{ marginBottom: 18 }}>
                        <Input label="Emergency service surcharge" type="number" value={emergencySurcharge} onChange={setEmergencySurcharge} placeholder="e.g. 500"/>
                        <div style={{ display: "flex", alignItems: "flex-end" }}>
                          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
                            Added on top of the price when a customer books this as an emergency/priority job. Leave blank for no surcharge.
                          </p>
                        </div>
                      </div>
                      <Btn variant="secondary" size="sm" loading={savingPrice} onClick={handleSaveDefaultPrice} style={{ marginBottom: 20 }}>
                        Save default price
                      </Btn>

                      {selectedService.is_type_required !== undefined && enrolled.requires_type && (
                        <div style={{ marginBottom: 20 }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
                            Type {selectedService.is_type_required ? "(required)" : "(optional)"}
                          </p>
                          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                            {(types ?? []).map(t => (
                              <label key={t.service_type_id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-primary)" }}>
                                <input type="checkbox" checked={t.is_enabled} onChange={() => toggleType(t)}/>
                                {t.name}
                              </label>
                            ))}
                          </div>
                        </div>
                      )}

                      {enrolled.requires_brand && (
                        <div style={{ marginBottom: 20 }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
                            Brand {selectedService.is_brand_required ? "(required)" : "(optional)"}
                          </p>
                          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                            {(brands ?? []).map(b => (
                              <label key={b.brand_id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-primary)" }}>
                                <input type="checkbox" checked={b.is_enabled} onChange={() => toggleBrand(b)}/>
                                {b.name}
                              </label>
                            ))}
                          </div>
                        </div>
                      )}

                      {((typePricing && typePricing.length > 0) || (brandPricing && brandPricing.length > 0)) && (
                        <div>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>Pricing rules</p>
                          <div style={{ overflowX: "auto" }}>
                            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                              <thead>
                                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                  <th style={{ textAlign: "left", padding: "8px", color: "var(--text-tertiary)", fontWeight: 600 }}>Rule</th>
                                  <th style={{ textAlign: "left", padding: "8px", color: "var(--text-tertiary)", fontWeight: 600 }}>Price range</th>
                                  <th style={{ textAlign: "left", padding: "8px", color: "var(--text-tertiary)", fontWeight: 600 }}>Action</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                  <td style={{ padding: "8px", color: "var(--text-primary)" }}>Default</td>
                                  <td style={{ padding: "8px", color: "var(--text-primary)" }}>{money(enrolled.tenant_min_price)} – {money(enrolled.tenant_max_price)}</td>
                                  <td style={{ padding: "8px", color: "var(--text-tertiary)" }}>—</td>
                                </tr>
                                {(typePricing ?? []).map(tp => (
                                  <React.Fragment key={tp.tenant_service_type_id}>
                                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                      <td style={{ padding: "8px", color: "var(--text-primary)" }}>{tp.name}</td>
                                      <td style={{ padding: "8px" }}>
                                        <PriceCell label={tp.name} min={tp.tenant_min_price} max={tp.tenant_max_price}
                                          onSave={(min, max) => handleTypePriceChange(tp.service_type_id, min, max)}/>
                                      </td>
                                      <td style={{ padding: "8px", color: "var(--brand)", fontWeight: 600 }}>Override</td>
                                    </tr>
                                    {enrolled.requires_brand && (brandPricingByType[tp.service_type_id]?.length ?? 0) > 0 && (
                                      <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                        <td colSpan={3} style={{ padding: "4px 8px 8px 24px" }}>
                                          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", cursor: "pointer" }}>
                                            <input type="checkbox" checked={!!brandOverrideOpen[tp.service_type_id]}
                                              onChange={e => setBrandOverrideOpen(prev => ({ ...prev, [tp.service_type_id]: e.target.checked }))}/>
                                            Set different prices per brand for {tp.name} (otherwise every {tp.name} brand uses the {tp.name} price above)
                                          </label>
                                        </td>
                                      </tr>
                                    )}
                                    {enrolled.requires_brand && brandOverrideOpen[tp.service_type_id] && (brandPricingByType[tp.service_type_id] ?? []).map(bp => (
                                      <tr key={bp.tenant_service_brand_id} style={{ borderBottom: "1px solid var(--border)" }}>
                                        <td style={{ padding: "8px 8px 8px 24px", color: "var(--text-secondary)" }}>{tp.name} → {bp.name}</td>
                                        <td style={{ padding: "8px" }}>
                                          <PriceCell label={`${tp.name} ${bp.name}`} min={bp.tenant_min_price} max={bp.tenant_max_price}
                                            onSave={(min, max) => handleBrandPriceChange(bp.brand_id, min, max, tp.service_type_id)}/>
                                        </td>
                                        <td style={{ padding: "8px", color: "var(--brand)", fontWeight: 600 }}>Override</td>
                                      </tr>
                                    ))}
                                  </React.Fragment>
                                ))}
                                {!enrolled.requires_type && (brandPricing ?? []).map(bp => (
                                  <tr key={bp.tenant_service_brand_id} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={{ padding: "8px", color: "var(--text-primary)" }}>{bp.name}</td>
                                    <td style={{ padding: "8px" }}>
                                      <PriceCell label={bp.name} min={bp.tenant_min_price} max={bp.tenant_max_price}
                                        onSave={(min, max) => handleBrandPriceChange(bp.brand_id, min, max)}/>
                                    </td>
                                    <td style={{ padding: "8px", color: "var(--brand)", fontWeight: 600 }}>Override</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </>
              )}
            </Card>
          )}
        </div>

        {/* Right: Readiness / hierarchy / blueprint */}
        <div style={{ minWidth: 0 }}>
          <Card style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>Setup readiness</h3>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{
                width: 64, height: 64, borderRadius: "50%", flexShrink: 0,
                background: `conic-gradient(var(--brand) ${Math.min(100, Math.round((configuredCount / Math.max(1, groups.length)) * 100)) * 3.6}deg, var(--surface-sunken) 0deg)`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <div style={{ width: 50, height: 50, borderRadius: "50%", background: "var(--surface)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                  {Math.min(100, Math.round((configuredCount / Math.max(1, groups.length)) * 100))}%
                </div>
              </div>
              <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: 0, flex: 1 }}>You&apos;re making good progress.</p>
            </div>
          </Card>

          <Card style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>Pricing hierarchy</h3>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", flexWrap: "wrap" }}>
              <span>Default</span><ArrowRight size={12}/><span>Type</span><ArrowRight size={12}/><span>Brand</span>
            </div>
            <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "8px 0 0" }}>Most specific price wins.</p>
          </Card>

          <Card>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>Admin blueprint</h3>
            {selectedService ? (
              <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  { label: "Type", value: selectedService.is_type_required ? "Required" : "Optional" },
                  { label: "Brand", value: selectedService.is_brand_required ? "Required" : "Optional" },
                  { label: "Customer issues", value: selectedService.requires_issue_type ? "Required" : "Optional" },
                  { label: "Checklist", value: selectedService.requires_checklist ? "Required" : "Not required" },
                  { label: "Estimate approval", value: selectedService.requires_estimate_approval ? "Required" : "Not required" },
                  { label: "Technician", value: selectedService.requires_technician ? "Required" : "Optional" },
                  { label: "Schedule", value: selectedService.requires_schedule ? "Required" : "Optional" },
                ].map(row => (
                  <li key={row.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)", flexShrink: 0 }}/>
                    <span style={{ color: "var(--text-secondary)", flex: 1 }}>{row.label}</span>
                    <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{row.value}</span>
                  </li>
                ))}
              </ul>
            ) : <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Select a service to see its rules.</p>}
          </Card>
        </div>
      </div>

      <div style={{
        position: "sticky", bottom: 0, marginTop: 24, padding: "16px 20px",
        background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
        display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap",
      }}>
        <Btn variant="secondary" onClick={handleBack}>Back</Btn>
        <Btn variant="secondary" loading={saving} onClick={handleSaveDraft} disabled={!enrolled}>Save draft</Btn>
        <Btn variant="primary" loading={saving} onClick={handleSaveAndContinue}>
          {returnTo ? "Save & return to workspace" : "Save & continue"}
        </Btn>
      </div>
    </OnboardingShell>
  );
}

function PriceCell({ label, min, max, onSave }: { label: string; min: number | null; max: number | null; onSave: (min: string, max: string) => void }) {
  const [localMin, setLocalMin] = useState(min != null ? String(min) : "");
  const [localMax, setLocalMax] = useState(max != null ? String(max) : "");
  useEffect(() => { setLocalMin(min != null ? String(min) : ""); }, [min]);
  useEffect(() => { setLocalMax(max != null ? String(max) : ""); }, [max]);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <input aria-label={`${label} minimum price`} inputMode="decimal" value={localMin} onChange={e => setLocalMin(e.target.value)} onBlur={() => onSave(localMin, localMax)}
        placeholder="Min" style={{ width: 70, height: 30, fontSize: 12, padding: "0 8px", background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}/>
      <span style={{ color: "var(--text-tertiary)" }}>–</span>
      <input aria-label={`${label} maximum price`} inputMode="decimal" value={localMax} onChange={e => setLocalMax(e.target.value)} onBlur={() => onSave(localMin, localMax)}
        placeholder="Max" style={{ width: 70, height: 30, fontSize: 12, padding: "0 8px", background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}/>
    </div>
  );
}
