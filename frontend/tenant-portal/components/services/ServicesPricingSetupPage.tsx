"use client";
import { PageHeader, PageShell, TableSurface } from "@serviceos/design-system";
import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search, ArrowRight, RefreshCw, Save,
} from "lucide-react";
import { OnboardingShell } from "../onboarding/OnboardingShell";
import { ServicesSetupProgress } from "./ServicesSetupProgress";
import { ServiceRequirementsPanel } from "./ServiceRequirementsPanel";
import {
  InlineDimensionPricingEditor, type InlineDimensionPricingEditorHandle,
} from "./InlineDimensionPricingEditor";
import { RepairEstimateGuidanceEditor } from "./RepairEstimateGuidanceEditor";
import { Card, Btn, Badge, Skeleton, Input } from "../shared/ui";
import {
  homeServicesSetupApi, homeServicesSetupOverviewApi, ServiceOSError,
  type AdminMasterServiceRow, type TenantEnabledService,
  type HsSetupAvailableType, type HsSetupBrand, type HsTypePricing, type HsBrandPricing,
} from "../../lib/api";

interface ServiceGroup {
  id: string; name: string; services: AdminMasterServiceRow[];
}

function money(v: number | null | undefined) {
  if (v === null || v === undefined) return "—";
  return `₹${v.toLocaleString("en-IN")}`;
}

function isInspectionPricingModel(model?: string | null) {
  return ["inspection_required", "inspection_quote", "visit_fee_plus_quote", "quote", "custom_quote"]
    .includes(model || "");
}

export default function ServicesPricingSetupPage() {
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
  const [setupFilter, setSetupFilter] = useState<"all" | "published" | "draft" | "needs_attention">("all");
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
  const dimensionEditorRef = useRef<InlineDimensionPricingEditorHandle>(null);

  const [defaultMin, setDefaultMin] = useState("");
  const [defaultMax, setDefaultMax] = useState("");
  const [visitFee, setVisitFee] = useState("");
  const [emergencySurcharge, setEmergencySurcharge] = useState("");
  const [warrantyDays, setWarrantyDays] = useState("5");
  const [showEstimateRange, setShowEstimateRange] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [savingPrice, setSavingPrice] = useState(false);
  const [consultationFee, setConsultationFee] = useState("");
  const [savedConsultationFee, setSavedConsultationFee] = useState<number | null>(null);
  const [savingConsultationFee, setSavingConsultationFee] = useState(false);
  const [saving, setSaving] = useState(false);
  const matchingSavePending = useRef(false);
  const [savingMatching, setSavingMatching] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      homeServicesSetupApi.listAvailable(),
      homeServicesSetupApi.listEnabled(),
      homeServicesSetupApi.getPricingPolicy(),
    ])
      .then(([a, e, policy]) => {
        setAvailable(a.services);
        setEnabledList(e.services);
        setConsultationFee(policy.consultation_fee != null ? String(policy.consultation_fee) : "");
        setSavedConsultationFee(policy.consultation_fee);
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
    return groups.map(group => {
      if (group.name.toLowerCase().includes(q)) return group;
      return {
        ...group,
        services: group.services.filter(service =>
          `${service.service_name} ${service.job_type_label ?? service.job_type}`.toLowerCase().includes(q)),
      };
    }).filter(group => group.services.length > 0);
  }, [groups, search]);

  const enabledByMasterService = useMemo(() => {
    const map = new Map<string, TenantEnabledService>();
    for (const e of enabledList) map.set(`${e.master_service_id}:${e.job_type_id}`, e);
    return map;
  }, [enabledList]);

  const displayGroups = useMemo(() => filteredGroups.map(group => ({
    ...group,
    services: group.services.filter(service => {
      if (setupFilter === "all") return true;
      const enabled = enabledByMasterService.get(`${service.service_id}:${service.job_type_id}`);
      if (setupFilter === "published") return enabled?.setup_status === "published";
      if (setupFilter === "draft") return !enabled || enabled.setup_status !== "published";
      return service.admin_ready === false || (!!enabled && (
        Number(enabled.warranty_days ?? 0) < 5
        || (String(service.job_type).toLowerCase() === "consultation"
          ? !(Number(savedConsultationFee) > 0)
          : isInspectionPricingModel(service.pricing_model)
          ? !enabled.tenant_visit_fee
          : !enabled.tenant_min_price || !enabled.tenant_max_price)
      ));
    }),
  })).filter(group => group.services.length > 0), [filteredGroups, setupFilter, enabledByMasterService, savedConsultationFee]);

  // Default to the first group/service once data loads.
  useEffect(() => {
    if (!selectedGroupId && groups.length > 0) setSelectedGroupId(groups[0].id);
  }, [groups, selectedGroupId]);
  useEffect(() => {
    const group = groups.find(g => g.id === selectedGroupId);
    if (group && !group.services.some(s => (s.offering_key ?? s.service_id) === selectedServiceId)) {
      setSelectedServiceId(group.services[0]?.offering_key ?? group.services[0]?.service_id ?? null);
    }
  }, [selectedGroupId, groups, selectedServiceId]);

  const selectedGroup = groups.find(g => g.id === selectedGroupId) ?? null;
  const selectedService = selectedGroup?.services.find(s => (s.offering_key ?? s.service_id) === selectedServiceId) ?? null;
  const enrolled = selectedService ? enabledByMasterService.get(`${selectedService.service_id}:${selectedService.job_type_id}`) ?? null : null;
  const isConsultationMode = String(selectedService?.job_type).toLowerCase() === "consultation";
  const isInspectionMode = !isConsultationMode && isInspectionPricingModel(selectedService?.pricing_model);
  const isFixedPriceMode = !isConsultationMode && selectedService?.pricing_model === "fixed";
  const isMatchingOnly = isInspectionMode || isConsultationMode;

  // Load type/brand detail whenever the enrolled tenant_service changes.
  useEffect(() => {
    setTypes(null); setBrands(null); setTypePricing(null); setBrandPricing(null); setBrandPricingByType({}); setBrandOverrideOpen({});
    if (!enrolled) {
      setDefaultMin(""); setDefaultMax(""); setVisitFee(""); setEmergencySurcharge(""); setWarrantyDays("5"); setShowEstimateRange(false);
      return;
    }
    setDefaultMin(enrolled.tenant_min_price != null ? String(enrolled.tenant_min_price) : "");
    setDefaultMax(enrolled.tenant_max_price != null ? String(enrolled.tenant_max_price) : "");
    setVisitFee(enrolled.tenant_visit_fee != null ? String(enrolled.tenant_visit_fee) : "");
    setEmergencySurcharge(enrolled.tenant_emergency_surcharge != null ? String(enrolled.tenant_emergency_surcharge) : "");
    setWarrantyDays(String(enrolled.warranty_days ?? 5));
    setShowEstimateRange(isInspectionMode && enrolled.tenant_min_price != null && enrolled.tenant_max_price != null);
    setDetailLoading(true);
    const tsid = enrolled.tenant_service_id;
    Promise.all([
      enrolled.requires_type ? homeServicesSetupApi.getAvailableTypes(tsid) : Promise.resolve({ types: [] }),
      enrolled.requires_brand ? homeServicesSetupApi.getAvailableBrands(tsid) : Promise.resolve({ brands: [] }),
      enrolled.requires_type && !isMatchingOnly ? homeServicesSetupApi.getTypePricing(tsid) : Promise.resolve({ types: [] }),
      // Brand pricing must be scoped per type for type-required services
      // (the backend rejects a type-less brand override in that case) --
      // fetched below, once typePricing tells us which types are selected.
      enrolled.requires_brand && !enrolled.requires_type && !isMatchingOnly ? homeServicesSetupApi.getBrandPricing(tsid) : Promise.resolve({ brands: [] }),
    ])
      .then(async ([t, b, tp, bp]) => {
        setTypes(t.types); setBrands(b.brands);
        setTypePricing(tp.types); setBrandPricing(bp.brands);
        if (!isMatchingOnly && enrolled.requires_brand && enrolled.requires_type && tp.types.length > 0) {
          await reloadBrandPricingByType(tsid, tp.types, b.brands);
        }
      })
      .catch((err: unknown) => {
        setTypes([]); setBrands([]); setTypePricing([]); setBrandPricing([]);
        setError(err instanceof ServiceOSError
          ? err.message
          : "We couldn't load the Admin-approved Types and Brands for this service.");
      })
      .finally(() => setDetailLoading(false));
  }, [enrolled?.tenant_service_id, isMatchingOnly]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSaveConsultationFee() {
    const fee = Number(consultationFee);
    if (!Number.isFinite(fee) || fee <= 0) {
      setError("Enter a consultation fee greater than zero.");
      return;
    }
    setSavingConsultationFee(true);
    setError(null);
    try {
      const policy = await homeServicesSetupApi.updatePricingPolicy({ consultation_fee: fee });
      setConsultationFee(String(policy.consultation_fee ?? fee));
      setSavedConsultationFee(policy.consultation_fee ?? fee);
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save the consultation fee.");
    } finally {
      setSavingConsultationFee(false);
    }
  }

  async function handleToggleOffer(next: boolean) {
    if (!selectedService) return;
    if (next && selectedService.admin_ready === false) {
      setError(selectedService.admin_blockers?.[0]?.message || "This service is waiting for Admin to finish its booking workflow.");
      return;
    }
    setToggling(true);
    setError(null);
    try {
      if (next) {
        if (!selectedService.job_type_id) throw new Error("This service has no job type configured.");
        await homeServicesSetupApi.enable({ master_service_id: selectedService.service_id, job_type_id: selectedService.job_type_id });
      } else {
        if (!selectedService.job_type_id) throw new Error("This service has no job type configured.");
        await homeServicesSetupApi.disable(selectedService.service_id, selectedService.job_type_id);
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
    if (!enrolled) return false;
    const parsedWarrantyDays = Number(warrantyDays);
    if (!Number.isInteger(parsedWarrantyDays) || parsedWarrantyDays < 5) {
      setError("Service warranty must be a whole number of at least 5 days.");
      return false;
    }
    const parsedSurcharge = emergencySurcharge ? Number(emergencySurcharge) : null;
    if (parsedSurcharge != null && (!Number.isFinite(parsedSurcharge) || parsedSurcharge < 0)) {
      setError("Emergency surcharge cannot be negative.");
      return false;
    }
    if (isInspectionMode) {
      const parsedVisitFee = Number(visitFee);
      if (!Number.isFinite(parsedVisitFee) || parsedVisitFee <= 0) {
        setError("Enter a visit fee greater than zero for this inspection workflow.");
        return false;
      }
      if (showEstimateRange) {
        const parsedMin = Number(defaultMin);
        const parsedMax = Number(defaultMax);
        if (!defaultMin || !defaultMax || !Number.isFinite(parsedMin) || !Number.isFinite(parsedMax) || parsedMin <= 0 || parsedMax < parsedMin) {
          setError("Enter a valid rough repair range. Maximum must be at least the minimum.");
          return false;
        }
      }
    } else if (isFixedPriceMode) {
      const parsedPrice = Number(defaultMin);
      if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) {
        setError("Enter a fixed price greater than zero.");
        return false;
      }
    } else if (!isConsultationMode) {
      const parsedMin = Number(defaultMin);
      const parsedMax = Number(defaultMax);
      if (!Number.isFinite(parsedMin) || !Number.isFinite(parsedMax) || parsedMin <= 0 || parsedMax < parsedMin) {
        setError("Enter a valid price range greater than zero. Maximum must be at least the minimum.");
        return false;
      }
    }
    setError(null);
    setSavingPrice(true);
    try {
      const payload: { tenant_min_price?: number | null; tenant_max_price?: number | null; tenant_visit_fee?: number; tenant_emergency_surcharge?: number; warranty_days:number } = {
        warranty_days: parsedWarrantyDays,
      };
      if (isInspectionMode) {
        payload.tenant_min_price = showEstimateRange ? Number(defaultMin) : null;
        payload.tenant_max_price = showEstimateRange ? Number(defaultMax) : null;
      } else if (!isConsultationMode) {
        if (defaultMin) payload.tenant_min_price = Number(defaultMin);
        if (defaultMin && isFixedPriceMode) payload.tenant_max_price = Number(defaultMin);
        else if (defaultMax) payload.tenant_max_price = Number(defaultMax);
      }
      if (isInspectionMode && visitFee) payload.tenant_visit_fee = Number(visitFee);
      payload.tenant_emergency_surcharge = parsedSurcharge ?? 0;
      const updated = await homeServicesSetupApi.updateEnabledService(enrolled.tenant_service_id, payload);
      return updated;
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save pricing.");
      return false;
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
        is_inherited: true,
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

  async function saveMatchingSelection(action: () => Promise<void>) {
    if (matchingSavePending.current) return;
    matchingSavePending.current = true;
    setSavingMatching(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save the matching selection. Please retry.");
    } finally {
      matchingSavePending.current = false;
      setSavingMatching(false);
    }
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
      isMatchingOnly ? Promise.resolve({ types: [] }) : homeServicesSetupApi.getTypePricing(enrolled.tenant_service_id),
    ]);
    setTypes(avail.types);
    setTypePricing(tp.types);
    if (!isMatchingOnly && enrolled.requires_brand && brands) await reloadBrandPricingByType(enrolled.tenant_service_id, tp.types, brands);
  }

  async function toggleBrand(brand: HsSetupBrand) {
    if (!enrolled || !brands) return;
    const current = brands.filter(b => b.is_enabled).map(b => b.brand_id);
    const next = brand.is_enabled ? current.filter(id => id !== brand.brand_id) : [...current, brand.brand_id];
    await homeServicesSetupApi.setBrands(enrolled.tenant_service_id, next);
    const avail = await homeServicesSetupApi.getAvailableBrands(enrolled.tenant_service_id);
    setBrands(avail.brands);
    if (isMatchingOnly) {
      setBrandPricing([]);
      setBrandPricingByType({});
    } else if (enrolled.requires_type) {
      await reloadBrandPricingByType(enrolled.tenant_service_id, typePricing ?? [], avail.brands);
    } else {
      const bp = await homeServicesSetupApi.getBrandPricing(enrolled.tenant_service_id);
      setBrandPricing(bp.brands);
    }
  }

  async function handleTypePriceChange(serviceTypeId: string, min: string, max: string) {
    if (!enrolled) return;
    const minValue = Number(min);
    const maxValue = Number(max);
    if (!min || !max || !Number.isFinite(minValue) || !Number.isFinite(maxValue) || minValue <= 0 || maxValue < minValue) {
      setError("Enter a valid type price range greater than zero before saving.");
      return;
    }
    try {
      setError(null);
      const res = await homeServicesSetupApi.setTypePricing(enrolled.tenant_service_id, serviceTypeId, minValue, maxValue);
      setTypePricing(res.types);
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save type pricing.");
    }
  }

  async function handleBrandPriceChange(brandId: string, min: string, max: string, serviceTypeId?: string) {
    if (!enrolled) return;
    const minValue = Number(min);
    const maxValue = Number(max);
    if (!min || !max || !Number.isFinite(minValue) || !Number.isFinite(maxValue) || minValue <= 0 || maxValue < minValue) {
      setError("Enter a valid brand price range greater than zero before saving.");
      return;
    }
    let res;
    try {
      setError(null);
      res = await homeServicesSetupApi.setBrandPricing(enrolled.tenant_service_id, brandId, minValue, maxValue, serviceTypeId);
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save brand pricing.");
      return;
    }
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

  async function handleClearTypePrices() {
    if (!enrolled) return;
    try {
      setError(null);
      const priced = (typePricing ?? []).filter(type => type.tenant_min_price != null || type.tenant_max_price != null);
      await Promise.all(priced.map(type => homeServicesSetupApi.clearTypePricing(enrolled.tenant_service_id, type.service_type_id)));
      const refreshed = await homeServicesSetupApi.getTypePricing(enrolled.tenant_service_id);
      setTypePricing(refreshed.types);
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not clear type prices.");
      throw err;
    }
  }

  async function handleClearBrandPrice(brandId: string, serviceTypeId?: string) {
    if (!enrolled) return;
    try {
      setError(null);
      const res = await homeServicesSetupApi.clearBrandPricing(enrolled.tenant_service_id, brandId, serviceTypeId);
      if (serviceTypeId) {
        const type = (typePricing ?? []).find(row => row.service_type_id === serviceTypeId);
        setBrandPricingByType(current => ({
          ...current,
          [serviceTypeId]: mergeBrandCandidatesWithPricing(
            brands ?? [], res.brands, type?.tenant_min_price ?? null, type?.tenant_max_price ?? null),
        }));
      } else {
        setBrandPricing(res.brands);
      }
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not remove brand exception.");
      throw err;
    }
  }

  function handleBack() {
    router.push(returnTo || "/tenant/home-services/setup/overview");
  }

  async function handleSaveDraft() {
    if (!enrolled) return;
    setSaving(true);
    try {
      const updated = await handleSaveDefaultPrice();
      if (!updated) return;
      await dimensionEditorRef.current?.save();
      await homeServicesSetupApi.saveDraft(enrolled.tenant_service_id);
      setEnabledList(list => list.map(e => e.tenant_service_id === updated.tenant_service_id ? updated : e));
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save draft.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveAndContinue() {
    setSaving(true);
    try {
      if (enrolled) {
        const updated = await handleSaveDefaultPrice();
        if (!updated) return;
        await dimensionEditorRef.current?.save();
        await homeServicesSetupApi.saveDraft(enrolled.tenant_service_id);
        setEnabledList(list => list.map(e => e.tenant_service_id === updated.tenant_service_id ? updated : e));
      }
      const overview = await homeServicesSetupOverviewApi.getOverview();
      window.dispatchEvent(new Event("home-services-setup-updated"));
      const serviceStep = overview.sections.find(section => section.key === "SERVICES_PRICING");
      if (!(returnTo && overview.vertical?.status === "active") && serviceStep?.status !== "complete") {
        setError(serviceStep?.blocking_reasons.map(reason => reason.message).join(" ") || "Choose and fully configure at least one service before continuing.");
        return;
      }
      router.push(returnTo || "/tenant/home-services/setup/plan");
    } catch (err) {
      setError(err instanceof ServiceOSError ? err.message : "Could not save your services.");
    } finally {
      setSaving(false);
    }
  }

  const configuredCount = available
    ? available.filter(s => enabledByMasterService.has(`${s.service_id}:${s.job_type_id}`)).length
    : enabledList.filter(e => e.setup_status === "published" || e.is_enabled).length;

  if (loading) {
    return (
      <OnboardingShell activeNav="services-pricing" showProgress={!returnTo}>
        <PageShell>
          <PageHeader title="Services & pricing" description="Choose what you provide and set your own prices." />
          {!returnTo && <ServicesSetupProgress revision={enabledList} consultationFee={savedConsultationFee} />}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(280px, 100%), 1fr))", gap: 20 }}>
            <Skeleton height={520}/><Skeleton height={520}/><Skeleton height={520}/>
          </div>
        </PageShell>
      </OnboardingShell>
    );
  }

  if (error && !available) {
    return (
      <OnboardingShell activeNav="services-pricing" showProgress={!returnTo}>
        <PageShell>
          <PageHeader title="Services & pricing" description="Choose what you provide and set your own prices." />
          {!returnTo && <ServicesSetupProgress revision={enabledList} consultationFee={savedConsultationFee} />}
          <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your services catalog.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
          </Card>
        </PageShell>
      </OnboardingShell>
    );
  }

  if (!available) return null;

  const publishedCount = enabledList.filter(service => service.setup_status === "published").length;
  const draftCount = enabledList.length - publishedCount;
  const attentionCount = available.filter(service => {
    const enabled = enabledByMasterService.get(`${service.service_id}:${service.job_type_id}`);
    return service.admin_ready === false || (!!enabled && (
      Number(enabled.warranty_days ?? 0) < 5
      || (String(service.job_type).toLowerCase() === "consultation"
        ? !(Number(savedConsultationFee) > 0)
        : isInspectionPricingModel(service.pricing_model)
        ? !enabled.tenant_visit_fee
        : !enabled.tenant_min_price || !enabled.tenant_max_price)
    ));
  }).length;
  const inspectionCount = available.filter(service => isInspectionPricingModel(service.pricing_model)).length;

  return (
    <OnboardingShell activeNav="services-pricing" showProgress={!returnTo}>
      <PageShell>
        <PageHeader
          eyebrow={!returnTo ? "Tenant onboarding · Step 3 of 8" : undefined}
          title="Services & pricing"
          description="Choose what you provide and set your own prices. Repairs start with an inspection; fixed-scope jobs show a real price at booking."
          actions={<>
            <Badge variant={configuredCount > 0 ? "success" : "muted"} size="lg">
              {configuredCount === 0 ? "No services configured" : `${configuredCount} service${configuredCount === 1 ? "" : "s"} configured`}
            </Badge>
            {returnTo && <Btn variant="secondary" onClick={handleBack}>Back to workspace</Btn>}
          </>}
        />
        {!returnTo && <ServicesSetupProgress revision={enabledList} consultationFee={savedConsultationFee} />}
      <div className="pricing-experience">
        {error && (
          <div role="alert" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "10px 14px", marginTop: 14, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 12 }}>
            <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{error}</p>
            <button onClick={() => setError(null)} style={{ background: "none", border: "none", color: "var(--danger-text)", cursor: "pointer", fontSize: 13, fontWeight: 600 }}>Dismiss</button>
          </div>
        )}

        <div className="pricing-stat-grid">
          <SetupPricingStat label="Live offerings" value={publishedCount} note="ready after activation" />
          <SetupPricingStat label="Drafts" value={draftCount} note="saved privately" />
          <SetupPricingStat label="Needs attention" value={attentionCount} note={attentionCount ? "waiting on setup" : "all available"} warning={attentionCount > 0} />
          <SetupPricingStat label="Inspection-based" value={inspectionCount} note="priced after diagnosis" />
          <SetupPricingStat label="Type prices" value={typePricing?.length ?? 0} note="for selected offering" />
          <SetupPricingStat label="Brand exceptions" value={(brandPricing ?? []).filter(row => row.tenant_min_price != null).length + Object.values(brandPricingByType).reduce((count, rows) => count + rows.filter(row => !(row as HsBrandPricing & { is_inherited?: boolean }).is_inherited && row.tenant_min_price != null).length, 0)} note="for selected offering" />
        </div>

        <section id="provider-consultation-fee" className="pricing-panel" aria-label="Provider-wide consultation fee" style={{ marginBottom: 16 }}>
          <h2 className="pricing-section-title">Provider-wide consultation fee</h2>
          <p className="pricing-section-copy">Set this once for all your Home Services consultations. Repair and installation prices are configured separately below.</p>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10, maxWidth: 420 }}>
            <div style={{ flex: 1 }}><Input label="Consultation fee" type="number" value={consultationFee} onChange={setConsultationFee} placeholder="299"/></div>
            <Btn variant="secondary" loading={savingConsultationFee} onClick={handleSaveConsultationFee}>Save fee</Btn>
          </div>
          {savedConsultationFee != null && Number(consultationFee) === savedConsultationFee && <p role="status" className="pricing-section-copy">Saved for all consultations.</p>}
        </section>

        <div className="pricing-workspace-grid">
          <aside className="pricing-offerings-rail" aria-label="Your offerings">
            <div className="pricing-rail-head">
              <div className="pricing-rail-title-row"><span className="pricing-rail-title">Your offerings</span><span className="pricing-rail-count">{displayGroups.reduce((count, group) => count + group.services.length, 0)} of {available.length}</span></div>
              <label className="pricing-search"><Search size={14}/><input aria-label="Search service groups" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search services" /></label>
              <div className="pricing-filter-row" aria-label="Filter by setup status" role="group">
                {([ ["all", "All"], ["published", "Published"], ["draft", "Draft"], ["needs_attention", "Needs attention"] ] as const).map(([value, label]) => (
                  <button key={value} className="pricing-filter-pill" aria-pressed={setupFilter === value} onClick={() => setSetupFilter(value)}>{label}</button>
                ))}
              </div>
            </div>
            <div className="pricing-offerings-list">
              {displayGroups.length === 0 && <p style={{ padding: 16, color: "var(--text-tertiary)", fontSize: 13 }}>No offerings match these filters.</p>}
              {displayGroups.map(group => (
                <div key={group.id}>
                  <span className="pricing-group-label">{group.name}</span>
                  {group.services.map(service => {
                    const key = service.offering_key ?? service.service_id;
                    const serviceEnabled = enabledByMasterService.get(`${service.service_id}:${service.job_type_id}`);
                    const selected = group.id === selectedGroupId && key === selectedServiceId;
                    const warning = service.admin_ready === false;
                    return (
                      <button key={key} className="pricing-offering-row" aria-current={selected ? "page" : undefined} onClick={() => { setSelectedGroupId(group.id); setSelectedServiceId(key); }}>
                        <span className="pricing-offering-copy">
                          <span className="pricing-offering-name">{service.service_name}</span>
                          <span className="pricing-offering-meta">{service.job_type_label ?? service.job_type} · {String(service.job_type).toLowerCase() === "consultation" ? (Number(savedConsultationFee) > 0 ? "Provider-wide fee configured" : "Set provider-wide fee above") : isInspectionPricingModel(service.pricing_model) ? (serviceEnabled?.tenant_visit_fee ? `${money(serviceEnabled.tenant_visit_fee)} inspection` : "No charge set") : serviceEnabled?.tenant_min_price ? `${money(serviceEnabled.tenant_min_price)}–${money(serviceEnabled.tenant_max_price)}` : "No price set"}</span>
                        </span>
                        <span className={`pricing-status-chip${warning ? " is-warning" : serviceEnabled?.setup_status === "published" ? " is-live" : ""}`}>{warning ? "Fix" : serviceEnabled?.setup_status === "published" ? "Live" : "Draft"}</span>
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </aside>

          <div className="pricing-detail-stack">
            {!selectedService ? (
              <div className="pricing-panel"><p style={{ margin: 0, color: "var(--text-tertiary)" }}>Select an offering to configure it.</p></div>
            ) : (
              <>
                <section className="pricing-panel pricing-service-head">
                  <div className="pricing-service-copy">
                    <span className="pricing-service-category">{selectedGroup?.name ?? "Service offering"}</span>
                    <span className="pricing-service-name">{selectedService.service_name}</span>
                    <span className="pricing-service-tagline">{isConsultationMode ? "Uses your shared provider-wide fee" : isInspectionMode ? "Inspection first, estimate after diagnosis" : "Set the price customers see at booking"}</span>
                  </div>
                  <div className="pricing-service-badges">
                    <span className={`pricing-kind-pill${isInspectionMode ? " is-inspection" : ""}`}>{isConsultationMode ? "Consultation" : isInspectionMode ? "Inspection based" : isFixedPriceMode ? "Fixed price" : "Price range"}</span>
                    <span className={`pricing-kind-pill is-status${enrolled?.setup_status === "published" ? "" : " is-draft"}`}>{enrolled?.setup_status === "published" ? "Live" : "Draft"}</span>
                    <label style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)", fontSize: 12 }}>
                      <input type="checkbox" aria-label={`Offer ${selectedService.service_name}`} checked={!!enrolled} disabled={toggling || selectedService.admin_ready === false} onChange={event => handleToggleOffer(event.target.checked)} /> Offer this service
                    </label>
                  </div>
                </section>

                {selectedService.admin_ready === false && <div role="alert" className="pricing-journey" style={{ color: "var(--warning-text)", background: "var(--warning-bg)", borderColor: "var(--warning-border)" }}>This offering is waiting for Admin configuration. {selectedService.admin_blockers?.[0]?.message}</div>}
                {selectedService.setup_update_required && <div role="status" className="pricing-journey">Admin updated this service&apos;s setup rules. Review and save this offering again.</div>}

                {isInspectionMode && enrolled && (
                  <section className="pricing-journey">
                    <span className="pricing-journey-title">Why there is no repair price here</span>
                    <div aria-label="Repair pricing flow" style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)", fontSize: 12 }}><span>Visit fee</span><ArrowRight size={12}/><span>Diagnosis</span><ArrowRight size={12}/><span>Approved estimate</span></div>
                    <div className="pricing-journey-grid">
                      <SetupJourneyStep number="1" title="Customer books an inspection" copy="They pay your inspection charge to get a technician on site." />
                      <SetupJourneyStep number="2" title="You diagnose and quote" copy="Parts and labour are added after you have seen the unit." />
                      <SetupJourneyStep number="3" title="Estimate approved" copy="The inspection charge is adjusted into the final bill." />
                    </div>
                  </section>
                )}

                {!enrolled ? (
                  <section className="pricing-panel"><h2 className="pricing-section-title">Start pricing this offering</h2><p className="pricing-section-copy">Turn on “Offer this service” above to add pricing, warranty and matching choices.</p></section>
                ) : detailLoading ? <Skeleton height={280}/> : (
                  <>
                    <section className="pricing-panel">
                      <h2 className="pricing-section-title">{isConsultationMode ? "Offering settings" : isInspectionMode ? "Inspection charge & estimate guidance" : "Your price"}</h2>
                      <p className="pricing-section-copy">{isConsultationMode ? "This offering uses the shared fee configured above. Type and Brand affect matching only." : isInspectionMode ? "Set what the visit costs. The final repair amount is approved after diagnosis. Type and Brand never change the Repair price. Type and Brand control eligibility and matching only." : isFixedPriceMode ? "Straightforward job with a known scope, so the customer sees and pays a real amount at booking." : "Set the default range. Type and Brand overrides are optional and stay below."}</p>
                      <div className="pricing-form-grid">
                        {isConsultationMode ? null : isInspectionMode ? <SetupPricingMoneyField label="Inspection charge" value={visitFee} onChange={setVisitFee} placeholder="249" hint="Payable if the customer declines your estimate." /> : isFixedPriceMode ? <SetupPricingMoneyField label={selectedService.service_name.toLowerCase().includes("installation") ? "Installation price" : "Service price"} value={defaultMin} onChange={setDefaultMin} placeholder="899" hint="Applies to every booking unless a type or brand price is set below."/> : <><SetupPricingMoneyField label="Minimum price" value={defaultMin} onChange={setDefaultMin} placeholder="600" hint="Your lowest expected charge."/><SetupPricingMoneyField label="Maximum price" value={defaultMax} onChange={setDefaultMax} placeholder="900" hint="Must be at least the minimum."/></>}
                        <SetupPricingMoneyField label="Emergency add-on" value={emergencySurcharge} onChange={setEmergencySurcharge} placeholder="0" hint="Nights, Sundays, same-day urgent."/>
                        <label className="pricing-field-label"><span>Warranty</span><span className="pricing-field-control"><input aria-label="Service warranty days" type="number" min={5} value={warrantyDays} onChange={event => setWarrantyDays(event.target.value)} placeholder="5"/><span className="pricing-field-suffix">days</span></span><span className="pricing-field-hint">On the work you did · platform minimum is 5 days.</span></label>
                      </div>
                      {isInspectionMode && <RepairEstimateGuidanceEditor enabled={showEstimateRange} minimum={defaultMin} maximum={defaultMax} disabled={savingPrice} onEnabledChange={setShowEstimateRange} onMinimumChange={setDefaultMin} onMaximumChange={setDefaultMax}/>} 
                      {!isMatchingOnly && <SetupDimensionsInlineEditor editorRef={dimensionEditorRef} selectedService={selectedService} enrolled={enrolled} isInspectionMode={false} types={types ?? []} brands={brands ?? []} typePricing={typePricing ?? []} brandPricing={brandPricing ?? []} brandPricingByType={brandPricingByType} handleTypePriceChange={handleTypePriceChange} handleBrandPriceChange={handleBrandPriceChange} handleClearTypePrices={handleClearTypePrices} handleClearBrandPrice={handleClearBrandPrice} setTypes={setTypes} setBrands={setBrands}/>}
                      {isMatchingOnly && <fieldset disabled={savingMatching} style={{ border: 0, padding: 0, margin: 0 }}><SetupDimensionsEditor selectedService={selectedService} enrolled={enrolled} isInspectionMode={true} types={types ?? []} brands={brands ?? []} typePricing={[]} brandPricing={[]} brandPricingByType={{}} brandOverrideOpen={brandOverrideOpen} setBrandOverrideOpen={setBrandOverrideOpen} toggleType={type => saveMatchingSelection(() => toggleType(type))} toggleBrand={brand => saveMatchingSelection(() => toggleBrand(brand))} handleTypePriceChange={handleTypePriceChange} handleBrandPriceChange={handleBrandPriceChange}/></fieldset>}
                    </section>

                    {selectedService.job_type_id && <details className="pricing-collapsible"><summary><span><span className="pricing-collapsible-title">Set by the platform</span><span className="pricing-collapsible-copy">Booking questions, customer problems and technician checklist · Read-only.</span></span></summary><div className="pricing-collapsible-body"><ServiceRequirementsPanel masterServiceId={selectedService.service_id} jobTypeId={selectedService.job_type_id}/></div></details>}

                  </>
                )}

                <div className="pricing-publish-bar">
                  <span className="pricing-publish-copy"><strong>{enrolled ? "Keep your setup progress" : "Choose this offering to continue"}</strong><span>{enrolled ? "Save now, then continue when all required offerings are ready." : "Turn on the offering before saving a draft."}</span></span>
                  <span className="pricing-publish-actions"><Btn variant="secondary" onClick={handleBack}>Back</Btn><Btn variant="secondary" loading={saving} onClick={handleSaveDraft} disabled={!enrolled}>Save as draft</Btn><Btn variant="primary" loading={saving} onClick={handleSaveAndContinue}>{returnTo ? "Save & return to workspace" : "Save & continue"}</Btn></span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
      </PageShell>
    </OnboardingShell>
  );
}

function SetupPricingStat({ label, value, note, warning = false }: { label: string; value: number; note: string; warning?: boolean }) {
  return <div className={`pricing-stat${warning ? " is-warning" : ""}`}><span className="pricing-stat-label">{label}</span><span className="pricing-stat-value">{value}</span><span className="pricing-stat-note">{note}</span></div>;
}

function SetupJourneyStep({ number, title, copy }: { number: string; title: string; copy: string }) {
  return <div className="pricing-journey-step"><span className="pricing-journey-number">{number}</span><span><strong>{title}</strong><span>{copy}</span></span></div>;
}

function SetupPricingMoneyField({ label, value, onChange, placeholder, hint }: {
  label: string; value: string; onChange: (value: string) => void; placeholder: string; hint: string;
}) {
  return (
    <label className="pricing-field-label">
      <span>{label}</span>
      <span className="pricing-field-control"><span className="pricing-field-prefix">₹</span><input aria-label={label} type="number" min={0} value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder}/></span>
      <span className="pricing-field-hint">{hint}</span>
    </label>
  );
}

function SetupDimensionsEditor({ selectedService, enrolled, isInspectionMode, types, brands, typePricing, brandPricing, brandPricingByType, brandOverrideOpen, setBrandOverrideOpen, toggleType, toggleBrand, handleTypePriceChange, handleBrandPriceChange }: {
  selectedService: AdminMasterServiceRow;
  enrolled: TenantEnabledService;
  isInspectionMode: boolean;
  types: HsSetupAvailableType[];
  brands: HsSetupBrand[];
  typePricing: HsTypePricing[];
  brandPricing: HsBrandPricing[];
  brandPricingByType: Record<string, HsBrandPricing[]>;
  brandOverrideOpen: Record<string, boolean>;
  setBrandOverrideOpen: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  toggleType: (type: HsSetupAvailableType) => Promise<void>;
  toggleBrand: (brand: HsSetupBrand) => Promise<void>;
  handleTypePriceChange: (serviceTypeId: string, min: string, max: string) => Promise<void>;
  handleBrandPriceChange: (brandId: string, min: string, max: string, serviceTypeId?: string) => Promise<void>;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {enrolled.requires_type && (
        <section>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>Type {selectedService.is_type_required ? "(required)" : "(optional)"}{isInspectionMode ? " for matching" : ""}</p>
          <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
            {types.map(type => <label key={type.service_type_id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}><input type="checkbox" checked={type.is_enabled} onChange={() => toggleType(type)}/>{type.name}</label>)}
            {!types.length && <p style={{ margin: 0, color: "var(--warning-text)", fontSize: 12.5 }}>No Types are mapped yet. Ask an administrator to complete this blueprint.</p>}
          </div>
        </section>
      )}
      {enrolled.requires_brand && (
        <section>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>Brand {selectedService.is_brand_required ? "(required)" : "(optional)"}{isInspectionMode ? " for matching" : ""}</p>
          <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
            {brands.map(brand => <label key={brand.brand_id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}><input type="checkbox" checked={brand.is_enabled} onChange={() => toggleBrand(brand)}/>{brand.name}</label>)}
            {!brands.length && <p style={{ margin: 0, color: "var(--warning-text)", fontSize: 12.5 }}>No Brands are mapped yet. Ask an administrator to complete this blueprint.</p>}
          </div>
        </section>
      )}
      {!isInspectionMode && ((typePricing.length > 0) || (brandPricing.length > 0)) && (
        <section>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>Pricing rules</p>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr><th>Rule</th><th>Price range</th><th>Action</th></tr></thead>
            <tbody>
              <tr><td>Default</td><td>{money(enrolled.tenant_min_price)} – {money(enrolled.tenant_max_price)}</td><td style={{ color: "var(--text-tertiary)" }}>—</td></tr>
              {typePricing.map(type => (
                <React.Fragment key={type.tenant_service_type_id}>
                  <tr><td>{type.name}</td><td><PriceCell label={type.name} min={type.tenant_min_price} max={type.tenant_max_price} onSave={(min, max) => handleTypePriceChange(type.service_type_id, min, max)}/></td><td style={{ color: "var(--brand)", fontWeight: 600 }}>Override</td></tr>
                  {enrolled.requires_brand && (brandPricingByType[type.service_type_id]?.length ?? 0) > 0 && <tr><td colSpan={3}><label style={{ display: "flex", gap: 7, alignItems: "center", fontSize: 12, color: "var(--text-secondary)" }}><input type="checkbox" checked={!!brandOverrideOpen[type.service_type_id]} onChange={event => setBrandOverrideOpen(current => ({ ...current, [type.service_type_id]: event.target.checked }))}/>Set different prices per brand for {type.name}; otherwise every brand uses the {type.name} price.</label></td></tr>}
                  {enrolled.requires_brand && brandOverrideOpen[type.service_type_id] && (brandPricingByType[type.service_type_id] ?? []).map(brand => <tr key={brand.tenant_service_brand_id}><td>{type.name} → {brand.name}</td><td><PriceCell label={`${type.name} ${brand.name}`} min={brand.tenant_min_price} max={brand.tenant_max_price} onSave={(min, max) => handleBrandPriceChange(brand.brand_id, min, max, type.service_type_id)}/></td><td style={{ color: "var(--brand)", fontWeight: 600 }}>Override</td></tr>)}
                </React.Fragment>
              ))}
              {!enrolled.requires_type && brandPricing.map(brand => <tr key={brand.tenant_service_brand_id}><td>{brand.name}</td><td><PriceCell label={brand.name} min={brand.tenant_min_price} max={brand.tenant_max_price} onSave={(min, max) => handleBrandPriceChange(brand.brand_id, min, max)}/></td><td style={{ color: "var(--brand)", fontWeight: 600 }}>Override</td></tr>)}
            </tbody>
          </TableSurface>
        </section>
      )}
      {!enrolled.requires_type && !enrolled.requires_brand && <p style={{ margin: 0, color: "var(--text-tertiary)", fontSize: 12.5 }}>This offering has no Type or Brand choices. Its default price applies to every booking.</p>}
    </div>
  );
}

function SetupDimensionsInlineEditor({ editorRef, selectedService, enrolled, isInspectionMode, types, brands, typePricing, brandPricing, brandPricingByType, toggleType, toggleBrand, handleTypePriceChange, handleBrandPriceChange, handleClearTypePrices, handleClearBrandPrice, setTypes: updateTypesState, setBrands: updateBrandsState }: {
  editorRef?: React.RefObject<InlineDimensionPricingEditorHandle | null>;
  selectedService: AdminMasterServiceRow;
  enrolled: TenantEnabledService;
  isInspectionMode: boolean;
  types: HsSetupAvailableType[];
  brands: HsSetupBrand[];
  typePricing: HsTypePricing[];
  brandPricing: HsBrandPricing[];
  brandPricingByType: Record<string, HsBrandPricing[]>;
  toggleType?: (type: HsSetupAvailableType) => Promise<void>;
  toggleBrand?: (brand: HsSetupBrand) => Promise<void>;
  handleTypePriceChange: (serviceTypeId: string, min: string, max: string) => Promise<void>;
  handleBrandPriceChange: (brandId: string, min: string, max: string, serviceTypeId?: string) => Promise<void>;
  handleClearTypePrices: () => Promise<void>;
  handleClearBrandPrice: (brandId: string, serviceTypeId?: string) => Promise<void>;
  setTypes?: React.Dispatch<React.SetStateAction<HsSetupAvailableType[] | null>>;
  setBrands?: React.Dispatch<React.SetStateAction<HsSetupBrand[] | null>>;
}) {
  const exceptions = enrolled.requires_type
    ? typePricing.flatMap(type => (brandPricingByType[type.service_type_id] ?? [])
      .filter(brand => !(brand as HsBrandPricing & { is_inherited?: boolean }).is_inherited && brand.tenant_min_price != null)
      .map(brand => ({ key: `${type.service_type_id}:${brand.brand_id}`, typeId: type.service_type_id, brandId: brand.brand_id, price: brand.tenant_min_price, persisted: true })))
    : brandPricing.filter(brand => brand.tenant_min_price != null)
      .map(brand => ({ key: `default:${brand.brand_id}`, typeId: undefined, brandId: brand.brand_id, price: brand.tenant_min_price, persisted: true }));

  return (
    <div>
      {!isInspectionMode && (
        <InlineDimensionPricingEditor
          ref={editorRef}
          basePrice={enrolled.tenant_min_price ?? null}
          types={types.map(type => ({
            id: type.service_type_id,
            name: type.name,
            enabled: type.is_enabled,
            price: typePricing.find(priced => priced.service_type_id === type.service_type_id)?.tenant_min_price ?? null,
          }))}
          brands={brands.map(brand => ({
            id: brand.brand_id,
            name: brand.name,
            canOverride: brand.can_override_price,
            enabled: brand.is_enabled,
          }))}
          exceptions={exceptions}
          onSaveTypes={async typeIds => {
            const result = await homeServicesSetupApi.setTypes(enrolled.tenant_service_id, typeIds);
            updateTypesState?.(result.types);
          }}
          onSaveBrands={async brandIds => {
            const result = await homeServicesSetupApi.setBrands(enrolled.tenant_service_id, brandIds);
            updateBrandsState?.(result.brands);
          }}
          onSaveType={(typeId, price) => handleTypePriceChange(typeId, String(price), String(price))}
          onClearType={typeId => homeServicesSetupApi.clearTypePricing(enrolled.tenant_service_id, typeId)}
          onClearTypePrices={handleClearTypePrices}
          onSaveBrand={(typeId, brandId, price) => handleBrandPriceChange(brandId, String(price), String(price), typeId)}
          onClearBrand={(typeId, brandId) => handleClearBrandPrice(brandId, typeId)}
        />
      )}
      {!enrolled.requires_type && !enrolled.requires_brand && <p style={{ margin: "14px 0 0", color: "var(--text-tertiary)", fontSize: 12.5 }}>This offering has no Type or Brand choices. Its default price applies to every booking.</p>}
    </div>
  );
}

function PriceCell({ label, min, max, onSave }: { label: string; min: number | null; max: number | null; onSave: (min: string, max: string) => void }) {
  const [localMin, setLocalMin] = useState(min != null ? String(min) : "");
  const [localMax, setLocalMax] = useState(max != null ? String(max) : "");
  useEffect(() => { setLocalMin(min != null ? String(min) : ""); }, [min]);
  useEffect(() => { setLocalMax(max != null ? String(max) : ""); }, [max]);
  const minValue = Number(localMin);
  const maxValue = Number(localMax);
  const invalid = !localMin || !localMax || !Number.isFinite(minValue) || !Number.isFinite(maxValue)
    || minValue <= 0 || maxValue < minValue;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <input aria-label={`${label} minimum price`} inputMode="decimal" type="number" min={1} value={localMin} onChange={e => setLocalMin(e.target.value)}
        placeholder="Min" style={{ width: 70, height: 30, fontSize: 12, padding: "0 8px", background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}/>
      <span style={{ color: "var(--text-tertiary)" }}>–</span>
      <input aria-label={`${label} maximum price`} inputMode="decimal" type="number" min={1} value={localMax} onChange={e => setLocalMax(e.target.value)}
        placeholder="Max" style={{ width: 70, height: 30, fontSize: 12, padding: "0 8px", background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}/>
      <button type="button" aria-label={`Save ${label} price range`} title={invalid ? "Enter a valid range greater than zero" : "Save price range"}
        disabled={invalid} onClick={() => onSave(localMin, localMax)}
        style={{ height: 30, width: 30, display: "grid", placeItems: "center", borderRadius: 6, border: "1px solid var(--brand)", background: "transparent", color: "var(--brand)", cursor: invalid ? "not-allowed" : "pointer", opacity: invalid ? 0.45 : 1 }}>
        <Save size={13}/>
      </button>
    </div>
  );
}
