"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Modal, Input, Skeleton, StatCard, EmptyState } from "../../../../components/shared/ui";
import {
  providerOfferingsApi, providerOnboardingApi, categoryDashboardApi, providerBrandApi,
  offeringCoverageApi, offeringPricingApi, myStatusApi, authApi, isTenantOwnerRole,
  type AvailableOffering, type EnabledOffering, type EnableOfferingPayload, type ProviderAvailableBrand,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { useTenant } from "../../../../hooks/useTenant";
import {
  Package, RefreshCw, CheckCircle2, AlertCircle, XCircle, Zap, Edit2, Tag,
  ClipboardCheck, Activity as ActivityIcon, MapPin, Users2, Search,
} from "lucide-react";

// ── helpers ───────────────────────────────────────────────────────────────────

const STATUS_VARIANT: Record<string, "success"|"warning"|"danger"|"muted"|"info"> = {
  active: "success", draft: "muted", inactive: "warning",
  suspended: "danger", rejected: "danger",
};

const READINESS_VARIANT: Record<string, "success"|"warning"|"danger"|"muted"> = {
  ready: "success", not_ready: "warning", blocked: "danger",
};

function fmt(v: string | number | null | undefined) {
  if (v === null || v === undefined || v === "") return "—";
  const n = typeof v === "number" ? v : parseFloat(v);
  return Number.isFinite(n) ? `₹${n.toLocaleString("en-IN")}` : "—";
}

async function tryOnboardingRefresh() {
  try { await providerOnboardingApi.refresh(); } catch (e) { console.warn("Onboarding refresh failed", e); }
}

function SectionError({ title, message, requestId, section, onRetry }: {
  title: string; message: string; requestId?: string | null; section: string; onRetry?: () => void;
}) {
  return (
    <div style={{ padding: 16, borderRadius: 10, border: "1px solid var(--danger-border, #fecaca)",
      background: "var(--danger-bg, #fef2f2)", display: "flex", flexDirection: "column", gap: 8 }}>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--danger-text, #b91c1c)", margin: 0 }}>{title}</p>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>{message}</p>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, fontFamily: "monospace" }}>
        Failed section: {section}{requestId && ` · Request ID: ${requestId}`}
      </p>
      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
        {onRetry && (
          <button onClick={onRetry} style={{ fontSize: 12, fontWeight: 600, padding: "6px 12px", borderRadius: 6,
            border: "1px solid var(--danger-border, #fecaca)", background: "transparent", color: "var(--danger-text, #b91c1c)", cursor: "pointer" }}>
            Retry
          </button>
        )}
        {requestId && (
          <button onClick={() => navigator.clipboard?.writeText(requestId)} style={{ fontSize: 12, fontWeight: 600, padding: "6px 12px", borderRadius: 6,
            border: "1px solid var(--border)", background: "transparent", color: "var(--text-secondary)", cursor: "pointer" }}>
            Copy Request ID
          </button>
        )}
      </div>
    </div>
  );
}

// ── Enable/Edit Drawer ────────────────────────────────────────────────────────

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  offering: AvailableOffering | null;
  existing: EnabledOffering | null;
  categoryType: string | null;
  onSaved: () => void;
}

const BLANK_FORM: EnableOfferingPayload = {
  offering_id: "",
  provider_display_name: "",
  provider_description: "",
  supported_type_ids: null,
  supported_brand_ids: null,
  supports_emergency: false,
  provider_price_override: null,
  provider_visit_fee: null,
  provider_appointment_fee: null,
  provider_lead_fee: null,
  activate_if_ready: false,
};

function EnableDrawer({ open, onClose, offering, existing, categoryType, onSaved }: DrawerProps) {
  const isEdit = !!existing;
  const [form, setForm] = useState<EnableOfferingPayload>(BLANK_FORM);
  const [selectedTypeIds, setSelectedTypeIds] = useState<string[]>([]);
  const [selectedBrandIds, setSelectedBrandIds] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [showBrandRequest, setShowBrandRequest] = useState(false);
  const [brandRequestName, setBrandRequestName] = useState("");

  const isHomeServices = categoryType === "home_services";
  const showBrand = isHomeServices && (offering?.requires_brand !== false);
  const showType = isHomeServices && (offering?.requires_service_type !== false);

  const masterServiceId = offering?.offering_id ?? existing?.offering_id ?? null;

  const { data: brandsData } = useApi(
    () => showBrand && open && masterServiceId
      ? providerBrandApi.getAvailableForService(masterServiceId).catch(() =>
          ({ service_id: masterServiceId, brands: [] as ProviderAvailableBrand[] }))
      : Promise.resolve(null),
    [showBrand, open, masterServiceId],
  );
  const availableBrands = brandsData?.brands ?? [];

  const { data: typesData } = useApi(
    () => showType && open && masterServiceId
      ? offeringCoverageApi.getTypes(masterServiceId).catch(() => ({ types: [] }))
      : Promise.resolve(null),
    [showType, open, masterServiceId],
  );
  const availableTypes = typesData?.types ?? [];

  const { data: issuesData } = useApi(
    () => open && masterServiceId
      ? offeringCoverageApi.getIssues(masterServiceId).catch(() => ({ issues: [] }))
      : Promise.resolve(null),
    [open, masterServiceId],
  );
  const availableIssues = issuesData?.issues ?? [];

  const { data: optionsData } = useApi(
    () => open && masterServiceId
      ? offeringCoverageApi.getOptions(masterServiceId).catch(() => ({ service_options: [], total: 0 }))
      : Promise.resolve(null),
    [open, masterServiceId],
  );
  const availableOptions = optionsData?.service_options ?? [];

  // Service areas + technicians (for the wizard's later steps)
  const { data: areasData } = useApi(() => open ? myStatusApi.getServiceAreas() : Promise.resolve(null), [open]);
  const activeAreas = (areasData?.areas ?? []).filter(a => a.is_active);

  const { data: teamData } = useApi(() => open ? myStatusApi.getTeamMembers() : Promise.resolve(null), [open]);
  const activeTechnicians = (teamData?.members ?? []).filter(m => m.status === "active");

  const submitBrandRequest = useAction(async () => {
    if (!brandRequestName.trim()) return;
    await providerBrandApi.requestBrand({ requested_brand_name: brandRequestName.trim() });
    setBrandRequestName("");
    setShowBrandRequest(false);
    setToast("Brand request submitted for admin review.");
  });

  React.useEffect(() => {
    if (!open) return;
    if (existing) {
      setForm({
        offering_id: existing.offering_id,
        provider_display_name: existing.provider_display_name ?? "",
        provider_description: existing.provider_description ?? "",
        supported_type_ids: existing.supported_type_ids,
        supported_brand_ids: existing.supported_brand_ids,
        supports_emergency: existing.supports_emergency,
        provider_price_override: existing.provider_price_override ? parseFloat(existing.provider_price_override) : null,
        provider_visit_fee: existing.provider_visit_fee ? parseFloat(existing.provider_visit_fee) : null,
        provider_appointment_fee: existing.provider_appointment_fee ? parseFloat(existing.provider_appointment_fee) : null,
        provider_lead_fee: existing.provider_lead_fee ? parseFloat(existing.provider_lead_fee) : null,
        activate_if_ready: false,
      });
      setSelectedTypeIds(existing.supported_type_ids ?? []);
      setSelectedBrandIds(existing.supported_brand_ids ?? []);
    } else if (offering) {
      setForm({ ...BLANK_FORM, offering_id: offering.offering_id });
      setSelectedTypeIds([]); setSelectedBrandIds([]);
    }
  }, [open, existing, offering]);

  const saveAction = useAction(useCallback(async (activateIfReady: boolean) => {
    const payload = {
      ...form,
      supported_type_ids: selectedTypeIds.length ? selectedTypeIds : null,
      supported_brand_ids: selectedBrandIds.length ? selectedBrandIds : null,
      activate_if_ready: activateIfReady,
    };
    if (isEdit && existing) {
      await providerOfferingsApi.update(existing.provider_enabled_offering_id, payload);
    } else {
      await providerOfferingsApi.enable(payload);
    }
    await tryOnboardingRefresh();
    onSaved();
    onClose();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form, selectedTypeIds, selectedBrandIds, isEdit, existing]));

  const isCoaching = categoryType === "coaching" || categoryType === "coaching_ielts";

  if (!open) return null;

  return (
    <Modal open title={isEdit ? `Edit: ${existing?.offering_name}` : `Enable: ${offering?.name}`}
      onClose={onClose} size="md">
      <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
        {saveAction.error && (
          <div style={{ padding:"10px 14px", borderRadius:9, background:"rgba(220,38,38,0.08)",
            border:"1px solid rgba(220,38,38,0.25)" }}>
            <p style={{ fontSize:12, color:"var(--danger)", margin:0 }}>{saveAction.error}</p>
            {saveAction.requestId && (
              <p style={{ fontSize: 10, color: "var(--danger)", opacity: 0.7, margin: "2px 0 0", fontFamily: "monospace" }}>
                Request ID: {saveAction.requestId}
              </p>
            )}
          </div>
        )}
        {toast && <div style={{ padding:"10px 14px", borderRadius:9, background:"rgba(5,150,105,0.08)",
          border:"1px solid rgba(5,150,105,0.25)", fontSize:12, color:"var(--success)" }}>{toast}</div>}

        <Input label="Provider Display Name" placeholder="e.g. AC Repair & Installation"
          value={form.provider_display_name ?? ""}
          onChange={v => setForm(f => ({ ...f, provider_display_name: v }))}/>

        <div>
          <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
            marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
            Provider Description
          </label>
          <textarea rows={3} value={form.provider_description ?? ""}
            onChange={e => setForm(f => ({ ...f, provider_description: e.target.value }))}
            style={{ width:"100%", fontSize:13, padding:"8px 10px", borderRadius:"var(--radius-md)",
              border:"1px solid var(--border)", background:"var(--surface)", color:"var(--text-primary)",
              resize:"vertical", boxSizing:"border-box" }}
            placeholder="Brief description for customers…"/>
        </div>

        {showType && (
          <div>
            <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
              marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
              Service Type Coverage {selectedTypeIds.length > 0 && <span style={{ color:"var(--brand)" }}>({selectedTypeIds.length} selected)</span>}
            </label>
            {availableTypes.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                No service types mapped to this service yet. Contact admin to map types.
              </p>
            ) : (
              <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
                {availableTypes.map(t => {
                  const selected = selectedTypeIds.includes(t.service_type_id);
                  return (
                    <button key={t.mapping_id}
                      onClick={() => setSelectedTypeIds(prev => selected ? prev.filter(id => id !== t.service_type_id) : [...prev, t.service_type_id])}
                      style={{
                        display:"flex", alignItems:"center", gap:6, padding:"6px 12px", borderRadius:20, fontSize:13, cursor:"pointer",
                        border: selected ? "2px solid var(--brand)" : "1px solid var(--border)",
                        background: selected ? "var(--brand-muted, rgba(37,99,235,0.1))" : "var(--surface)",
                        color: selected ? "var(--brand)" : "var(--text-primary)",
                        fontWeight: selected ? 600 : 400,
                      }}>
                      {t.name}{t.is_required && <span style={{ fontSize:10, color:"var(--danger)" }}>*</span>}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {showBrand && (
          <div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:6 }}>
              <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)",
                textTransform:"uppercase", letterSpacing:"0.06em" }}>
                Brand Coverage {selectedBrandIds.length > 0 && <span style={{ color:"var(--brand)" }}>({selectedBrandIds.length} selected)</span>}
              </label>
              <button onClick={() => setShowBrandRequest(true)} style={{
                fontSize:11, color:"var(--brand)", background:"none", border:"none", cursor:"pointer", padding:0,
              }}>
                + Request missing brand
              </button>
            </div>
            {availableBrands.length === 0 ? (
              <div style={{ fontSize:12, color:"var(--text-tertiary)", padding:"8px 0" }}>
                No brands configured for this service yet. Contact admin to map brands.
              </div>
            ) : (
              <div style={{ display:"flex", flexWrap:"wrap", gap:8, padding:"8px 0" }}>
                {availableBrands.map(brand => {
                  const selected = selectedBrandIds.includes(brand.brand_id);
                  return (
                    <button
                      key={brand.brand_id}
                      onClick={() => setSelectedBrandIds(prev =>
                        selected ? prev.filter(id => id !== brand.brand_id) : [...prev, brand.brand_id]
                      )}
                      style={{
                        display:"flex", alignItems:"center", gap:6, padding:"6px 12px",
                        borderRadius:20, fontSize:13, cursor:"pointer",
                        border: selected ? "2px solid var(--brand)" : "1px solid var(--border)",
                        background: selected ? "var(--brand-muted, rgba(37,99,235,0.1))" : "var(--surface)",
                        color: selected ? "var(--brand)" : "var(--text-primary)",
                        fontWeight: selected ? 600 : 400,
                      }}
                    >
                      <Tag size={11} />
                      {brand.name}
                      {brand.is_required && <span style={{ fontSize:10, color:"var(--danger)" }}>*</span>}
                    </button>
                  );
                })}
              </div>
            )}
            {showBrandRequest && (
              <div style={{ marginTop:10, padding:10, border:"1px solid var(--border)", borderRadius:"var(--radius-md)", background:"var(--surface)" }}>
                <div style={{ fontSize:12, fontWeight:600, marginBottom:6 }}>Request a Missing Brand</div>
                <input value={brandRequestName} onChange={e => setBrandRequestName(e.target.value)}
                  placeholder="Brand name (e.g. Carrier)"
                  style={{ width:"100%", fontSize:13, padding:"6px 10px", borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)", color:"var(--text-primary)", outline:"none", boxSizing:"border-box", marginBottom:8 }} />
                <div style={{ display:"flex", gap:8 }}>
                  <Btn size="sm" variant="secondary" onClick={() => setShowBrandRequest(false)}>Cancel</Btn>
                  <Btn size="sm" variant="primary" loading={submitBrandRequest.loading}
                    onClick={() => submitBrandRequest.execute()}>Submit Request</Btn>
                </div>
              </div>
            )}
          </div>
        )}

        {availableIssues.length > 0 && (
          <div>
            <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
              marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
              Issue Coverage (read-only, platform-mapped)
            </label>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {availableIssues.map(i => (
                <Badge key={i.mapping_id} variant="muted" size="sm">{i.name}</Badge>
              ))}
            </div>
          </div>
        )}

        {availableOptions.length > 0 && (
          <div>
            <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
              marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
              Service Options (read-only, platform-mapped)
            </label>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {availableOptions.map(o => (
                <Badge key={o.id} variant="info" size="sm">{o.name}</Badge>
              ))}
            </div>
          </div>
        )}

        <div>
          <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
            marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
            <MapPin size={11} style={{ display: "inline", marginRight: 4 }}/> Service Areas ({activeAreas.length} active)
          </label>
          {activeAreas.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--warning)", margin: 0 }}>
              No active service areas. This offering will not be bookable until you add one.
            </p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {activeAreas.map((a, i) => (
                <Badge key={i} variant="success" size="sm">{String(a.city ?? a.zipcode ?? "Area")}</Badge>
              ))}
            </div>
          )}
        </div>

        <div>
          <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
            marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
            <Users2 size={11} style={{ display: "inline", marginRight: 4 }}/> Assigned Technicians ({activeTechnicians.length} active)
          </label>
          {activeTechnicians.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--warning)", margin: 0 }}>
              No active technicians. This offering will not be bookable until you assign one.
            </p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {activeTechnicians.map(t => (
                <Badge key={t.member_id} variant="success" size="sm">{t.full_name}</Badge>
              ))}
            </div>
          )}
        </div>

        {isHomeServices && (
          <label style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer", userSelect:"none" }}>
            <input type="checkbox" checked={form.supports_emergency ?? false}
              onChange={e => setForm(f => ({ ...f, supports_emergency: e.target.checked }))}
              style={{ width:16, height:16, cursor:"pointer" }}/>
            <span style={{ fontSize:13, color:"var(--text-primary)" }}>Supports emergency requests</span>
          </label>
        )}

        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
          <Input label="Price Override (₹)" type="number" placeholder="0.00"
            value={form.provider_price_override != null ? String(form.provider_price_override) : ""}
            onChange={v => setForm(f => ({ ...f, provider_price_override: v ? parseFloat(v) : null }))}/>
          <Input label="Visit Fee (₹)" type="number" placeholder="0.00"
            value={form.provider_visit_fee != null ? String(form.provider_visit_fee) : ""}
            onChange={v => setForm(f => ({ ...f, provider_visit_fee: v ? parseFloat(v) : null }))}/>
          {!isCoaching && (
            <Input label="Appointment Fee (₹)" type="number" placeholder="0.00"
              value={form.provider_appointment_fee != null ? String(form.provider_appointment_fee) : ""}
              onChange={v => setForm(f => ({ ...f, provider_appointment_fee: v ? parseFloat(v) : null }))}/>
          )}
          <Input label="Lead Fee (₹)" type="number" placeholder="0.00"
            value={form.provider_lead_fee != null ? String(form.provider_lead_fee) : ""}
            onChange={v => setForm(f => ({ ...f, provider_lead_fee: v ? parseFloat(v) : null }))}/>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          Final customer pricing is resolved by the platform pricing engine at booking time — this override is a
          request, not the authoritative price. Customer pays provider directly; the platform does not collect
          customer service payment for Home Services.
        </p>

        <div style={{ display:"flex", gap:8, justifyContent:"flex-end", paddingTop:4 }}>
          <Btn size="sm" variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn size="sm" variant="secondary" loading={saveAction.loading}
            onClick={() => saveAction.execute(false)}>
            Save as Draft
          </Btn>
          <Btn size="sm" variant="primary" loading={saveAction.loading}
            onClick={() => saveAction.execute(true)}>
            {isEdit ? "Save & Activate if Ready" : "Enable Offering"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── Readiness blockers list ───────────────────────────────────────────────────

function BlockerList({ blockers }: { blockers: EnabledOffering["readiness_blockers"] }) {
  if (!blockers || blockers.length === 0) return <span style={{ color:"var(--text-tertiary)", fontSize:12 }}>—</span>;
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:3 }}>
      {blockers.map((b, i) => (
        <div key={i} style={{ fontSize:11, color:"var(--danger)", display:"flex", alignItems:"center", gap:4 }}>
          <XCircle size={10}/> {b.message}
        </div>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type PageTab = "available" | "enabled" | "readiness" | "diagnostics";

export default function OfferingsPage() {
  const tenant = useTenant();
  const [tab, setTab] = useState<PageTab>("available");
  const [search, setSearch] = useState("");
  const [drawerOffering, setDrawerOffering] = useState<AvailableOffering | null>(null);
  const [drawerEnabled, setDrawerEnabled] = useState<EnabledOffering | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [toastErr, setToastErr] = useState<string | null>(null);

  const meApi = useApi(useCallback(() => authApi.me(), []));
  const runtime = useApi(useCallback(() => categoryDashboardApi.getRuntime(), []));
  const available = useApi(useCallback(() => providerOfferingsApi.listAvailable(), []));
  const enabled = useApi(useCallback(() => providerOfferingsApi.listEnabled(), []));
  const areasApi = useApi(useCallback(() => myStatusApi.getServiceAreas(), []));
  const teamApi = useApi(useCallback(() => myStatusApi.getTeamMembers(), []));
  const activityApi = useApi(useCallback(() => myStatusApi.getAuditLog(10), []));

  const categoryType: string | null = runtime.data?.tenant?.category?.category_type ?? null;
  const isTenantOwner = isTenantOwnerRole(meApi.data?.role);

  function flash(msg: string, err = false) {
    if (err) { setToastErr(msg); setTimeout(() => setToastErr(null), 4000); }
    else     { setToast(msg);    setTimeout(() => setToast(null), 3000); }
  }

  const activateAction = useAction(useCallback(async (id: string) => {
    await providerOfferingsApi.activate(id);
    enabled.refetch();
    await tryOnboardingRefresh();
    flash("Offering activated.");
  }, [enabled]));

  const deactivateAction = useAction(useCallback(async (id: string) => {
    await providerOfferingsApi.deactivate(id);
    enabled.refetch();
    await tryOnboardingRefresh();
    flash("Offering deactivated.");
  }, [enabled]));

  const refreshReadinessAction = useAction(useCallback(async (id: string) => {
    await providerOfferingsApi.refreshReadiness(id);
    enabled.refetch();
    flash("Readiness refreshed.");
  }, [enabled]));

  const refreshAllAction = useAction(useCallback(async () => {
    available.refetch(); enabled.refetch(); areasApi.refetch(); teamApi.refetch(); activityApi.refetch();
  }, [available, enabled, areasApi, teamApi, activityApi]));

  function handleSaved() {
    available.refetch();
    enabled.refetch();
    activityApi.refetch();
    flash(drawerEnabled ? "Offering updated." : "Offering enabled.");
  }

  const availableListRaw: AvailableOffering[] = available.data?.offerings ?? [];
  const enabledList: EnabledOffering[] = enabled.data?.offerings ?? [];
  const withBlockers = enabledList.filter(o => o.readiness_blockers && o.readiness_blockers.length > 0);
  const bookableEnabled = enabledList.filter(o => o.status === "active" && (!o.readiness_blockers || o.readiness_blockers.length === 0));

  const availableList = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return availableListRaw;
    return availableListRaw.filter(o =>
      o.name.toLowerCase().includes(q) || (o.service_group_name ?? "").toLowerCase().includes(q));
  }, [availableListRaw, search]);

  const activeAreas = (areasApi.data?.areas ?? []).filter(a => a.is_active);
  const activeTechnicians = (teamApi.data?.members ?? []).filter(m => m.status === "active");
  const coverageConfiguredCount = enabledList.filter(o => (o.supported_type_ids?.length ?? 0) > 0 || (o.supported_brand_ids?.length ?? 0) > 0).length;
  const pricingReadyCount = enabledList.filter(o => o.provider_price_override != null).length;

  const TAB_ITEMS: { id: PageTab; label: string; count?: number; error?: boolean }[] = [
    { id: "available",   label: "Available Offerings", count: available.error ? undefined : availableListRaw.length, error: !!available.error },
    { id: "enabled",     label: "My Enabled Offerings", count: enabled.error ? undefined : enabledList.length, error: !!enabled.error },
    { id: "readiness",   label: "Readiness Issues",     count: enabled.error ? undefined : withBlockers.length, error: !!enabled.error },
    { id: "diagnostics", label: "Catalog Diagnostics" },
  ];

  return (
    <TenantLayout activeNav="offerings">
      {/* Breadcrumb */}
      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 12 }}>
        <Link href="/dashboard" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Tenant Portal</Link>
        {" / "}
        <span>Setup</span>
        {" / "}
        <span>My Offerings</span>
      </div>

      {/* Header */}
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between",
        marginBottom:20, flexWrap:"wrap", gap:12 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:800, color:"var(--text-primary)", margin:"0 0 4px" }}>
            My Offerings
          </h1>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Enable platform-approved services, configure coverage, pricing, areas, and readiness for customer bookings.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {categoryType && <Badge variant="info" size="sm">{categoryType.replace(/_/g," ")}</Badge>}
          <Btn size="sm" variant="secondary" onClick={() => refreshAllAction.execute()} disabled={refreshAllAction.loading}>
            <RefreshCw size={13}/> Refresh Catalog
          </Btn>
          <Btn size="sm" variant="secondary" onClick={() => setTab("readiness")}>
            <ClipboardCheck size={13}/> Validate Offerings
          </Btn>
          {isTenantOwner ? (
            <Btn size="sm" variant="primary" onClick={() => setTab("available")}>
              <Zap size={13}/> Enable Offering
            </Btn>
          ) : (
            <span title="Permission required"><Btn size="sm" variant="secondary" disabled>Enable Offering</Btn></span>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast    && <div style={{ padding:"10px 16px", borderRadius:10, marginBottom:12,
        background:"rgba(5,150,105,0.08)", border:"1px solid rgba(5,150,105,0.25)",
        fontSize:13, color:"var(--success)" }}>✓ {toast}</div>}
      {toastErr && <div style={{ padding:"10px 16px", borderRadius:10, marginBottom:12,
        background:"rgba(220,38,38,0.08)", border:"1px solid rgba(220,38,38,0.25)",
        fontSize:13, color:"var(--danger)" }}>✕ {toastErr}</div>}

      {/* Offering Readiness Hero */}
      <Card padding={20} style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-tertiary)", margin: "0 0 4px" }}>
              {tenant.tenantName || "Your Business"} · {(tenant.vertical || "home_services").replace(/_/g, " ")}
            </p>
            <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>Offering Readiness</h2>
          </div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <HeroStat label="Available" value={available.error ? "Unavailable" : String(availableListRaw.length)}/>
            <HeroStat label="Enabled" value={enabled.error ? "Unavailable" : String(enabledList.length)}/>
            <HeroStat label="Bookable" value={enabled.error ? "Unavailable" : String(bookableEnabled.length)}/>
            <HeroStat label="Readiness Issues" value={enabled.error ? "Unavailable" : String(withBlockers.length)}/>
          </div>
        </div>
        {availableListRaw.length === 0 && !available.loading && !available.error && (
          <div style={{ marginTop: 14, padding: "10px 14px", borderRadius:"var(--radius-md)", background: "rgba(217,119,6,0.08)", border: "1px solid rgba(217,119,6,0.2)" }}>
            <p style={{ fontSize: 12, color: "var(--warning)", margin: 0 }}>
              Catalog unavailable or no eligible services found for your vertical. See Catalog Diagnostics before treating this as final.
            </p>
          </div>
        )}
      </Card>

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 20 }}>
        {available.loading || enabled.loading ? (
          Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={92}/>)
        ) : (
          <>
            <StatCard label="Available Offerings" value={available.error ? "Unavailable" : availableListRaw.length} icon={<Package/>}/>
            <StatCard label="Enabled Offerings" value={enabled.error ? "Unavailable" : enabledList.length} icon={<Zap/>}/>
            <StatCard label="Bookable Offerings" value={enabled.error ? "Unavailable" : bookableEnabled.length} icon={<CheckCircle2/>} alert={bookableEnabled.length === 0 && enabledList.length > 0}/>
            <StatCard label="Readiness Issues" value={enabled.error ? "Unavailable" : withBlockers.length} icon={<AlertCircle/>} alert={withBlockers.length > 0}/>
            <StatCard label="Coverage Configured" value={`${coverageConfiguredCount} / ${enabledList.length || 0}`} icon={<Tag/>}/>
            <StatCard label="Pricing Ready" value={`${pricingReadyCount} / ${enabledList.length || 0}`} icon={<ClipboardCheck/>}/>
            <StatCard label="Assigned Technicians" value={teamApi.error ? "Unavailable" : activeTechnicians.length} icon={<Users2/>}/>
            <StatCard label="Service Areas Linked" value={areasApi.error ? "Unavailable" : activeAreas.length} icon={<MapPin/>}/>
          </>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display:"flex", gap:4, marginBottom:16, borderBottom:"1px solid var(--border)",
        paddingBottom:0, overflowX: "auto" }}>
        {TAB_ITEMS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{ padding:"8px 16px", fontSize:13, fontWeight:600, cursor:"pointer", border:"none",
              background:"transparent", borderBottom: tab===t.id ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab===t.id ? "var(--brand)" : "var(--text-secondary)",
              marginBottom:-1, display:"flex", alignItems:"center", gap:6, whiteSpace: "nowrap" }}>
            {t.label}
            {t.error ? (
              <span style={{ fontSize:10, padding:"1px 6px", borderRadius:99, background: "rgba(220,38,38,0.15)", color: "var(--danger)" }}>Unavailable</span>
            ) : t.count !== undefined && (
              <span style={{ fontSize:10, padding:"1px 5px", borderRadius:99,
                background: tab===t.id ? "var(--brand)" : "var(--surface-sunken)",
                color: tab===t.id ? "white" : "var(--text-tertiary)" }}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab: Available */}
      {tab === "available" && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 14, alignItems: "center" }}>
            <div style={{ position: "relative", flex: 1, maxWidth: 320 }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: 10, color: "var(--text-tertiary)" }}/>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search service or group…"
                style={{ width: "100%", padding: "8px 10px 8px 30px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
                  background: "var(--surface)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box" }}/>
            </div>
          </div>

          {available.loading ? (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))", gap:12 }}>
              {[...Array(6)].map((_,i) => <Skeleton key={i} height={190}/>)}
            </div>
          ) : available.error ? (
            <SectionError title="We couldn't load offerings" message="Retry or contact support with the request ID."
              requestId={available.requestId} section="GET /v1/provider/offerings/available" onRetry={() => available.refetch()}/>
          ) : availableList.length === 0 ? (
            <Card><div style={{ textAlign:"center", padding:"40px 24px" }}>
              <Package size={32} style={{ color:"var(--text-tertiary)", display:"block", margin:"0 auto 12px" }}/>
              <p style={{ fontSize:15, fontWeight: 700, color:"var(--text-primary)", margin:"0 0 6px" }}>No eligible offerings found</p>
              <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 16px", maxWidth: 420, marginLeft: "auto", marginRight: "auto" }}>
                No platform-approved services are currently available for your tenant vertical/package. This may be a setup issue.
              </p>
              <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
                <Btn size="sm" variant="primary" onClick={() => available.refetch()}>Refresh Catalog</Btn>
                <Btn size="sm" variant="secondary" onClick={() => setTab("diagnostics")}>Run Catalog Diagnostics</Btn>
              </div>
            </div></Card>
          ) : (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))", gap:12 }}>
              {availableList.map(o => (
                <Card key={o.offering_id} style={{ position:"relative" }}>
                  {o.is_already_enabled && (
                    <div style={{ position:"absolute", top:12, right:12 }}>
                      <Badge variant="success" size="sm"><CheckCircle2 size={10}/> Enabled</Badge>
                    </div>
                  )}
                  <p style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px",
                    paddingRight: o.is_already_enabled ? 80 : 0 }}>
                    {o.name}
                  </p>
                  {o.service_group_name && (
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px" }}>Group: {o.service_group_name}</p>
                  )}
                  <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginBottom:10 }}>
                    {o.offering_type && <Badge variant="muted" size="sm">{o.offering_type.replace(/_/g," ")}</Badge>}
                    {o.pricing_model && <Badge variant="info" size="sm">{o.pricing_model.replace(/_/g," ")}</Badge>}
                  </div>
                  <div style={{ display:"flex", flexDirection:"column", gap:3, marginBottom:12 }}>
                    {o.admin_price && <p style={{ fontSize:11, color:"var(--text-secondary)", margin:0 }}>
                      Base price: {fmt(o.admin_price)}</p>}
                    {o.admin_visit_fee && parseFloat(o.admin_visit_fee) > 0 && <p style={{ fontSize:11, color:"var(--text-secondary)", margin:0 }}>
                      Visit fee: {fmt(o.admin_visit_fee)}</p>}
                    {o.requires_service_type && <p style={{ fontSize:11, color:"var(--warning)", margin:0 }}>
                      ⚠ Requires service type selection</p>}
                    {o.requires_brand && <p style={{ fontSize:11, color:"var(--warning)", margin:0 }}>
                      ⚠ Requires brand selection</p>}
                    {o.requires_staff && <p style={{ fontSize:11, color:"var(--warning)", margin:0 }}>
                      ⚠ Requires assigned technician</p>}
                  </div>
                  <Btn size="sm" variant={o.is_already_enabled ? "secondary" : "primary"}
                    disabled={!isTenantOwner && !o.is_already_enabled}
                    onClick={() => {
                      if (o.is_already_enabled && o.provider_enabled_offering_id) {
                        const ex = enabledList.find(e => e.provider_enabled_offering_id === o.provider_enabled_offering_id);
                        if (ex) { setDrawerEnabled(ex); setDrawerOffering(null); }
                      } else {
                        setDrawerOffering(o); setDrawerEnabled(null);
                      }
                    }}>
                    {o.is_already_enabled ? "View Enabled Offering" : "Enable Offering"}
                  </Btn>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* Tab: Enabled */}
      {tab === "enabled" && (
        enabled.loading ? (
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            {[...Array(4)].map((_,i) => <Skeleton key={i} height={60}/>)}
          </div>
        ) : enabled.error ? (
          <SectionError title="We couldn't load enabled offerings" message="Retry or contact support with the request ID."
            requestId={enabled.requestId} section="GET /v1/provider/offerings/enabled" onRetry={() => enabled.refetch()}/>
        ) : enabledList.length === 0 ? (
          <Card><div style={{ textAlign:"center", padding:"40px 0" }}>
            <Zap size={32} style={{ color:"var(--text-tertiary)", display:"block", margin:"0 auto 12px" }}/>
            <p style={{ fontSize:14, color:"var(--text-secondary)", margin:"0 0 12px" }}>
              No offerings enabled yet.
            </p>
            <Btn size="sm" variant="primary" onClick={() => setTab("available")}>Browse Available</Btn>
          </div></Card>
        ) : (
          <Card padding={0}>
            <div style={{ overflowX:"auto" }}>
              <TableSurface style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead>
                  <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                    {["Offering","Status","Readiness","Coverage","Emergency","Pricing","Blockers","Updated","Actions"].map(h => (
                      <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontSize:10, fontWeight:700,
                        color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em",
                        whiteSpace:"nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {enabledList.map((o, i) => (
                    <tr key={o.provider_enabled_offering_id}
                      style={{ borderBottom: i < enabledList.length-1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding:"10px 12px" }}>
                        <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                          {o.provider_display_name ?? o.offering_name}
                        </p>
                        {o.provider_display_name && o.provider_display_name !== o.offering_name && (
                          <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"1px 0 0" }}>{o.offering_name}</p>
                        )}
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <Badge variant={STATUS_VARIANT[o.status] ?? "muted"} size="sm">
                          {o.status}
                        </Badge>
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        {o.readiness_status ? (
                          <Badge variant={READINESS_VARIANT[o.readiness_status] ?? "muted"} size="sm">
                            {o.readiness_status.replace(/_/g," ")}
                          </Badge>
                        ) : <span style={{ color:"var(--text-tertiary)", fontSize:12 }}>—</span>}
                      </td>
                      <td style={{ padding:"10px 12px", fontSize:11, color:"var(--text-secondary)" }}>
                        {o.supported_type_ids?.length || o.supported_brand_ids?.length
                          ? `${o.supported_type_ids?.length ?? 0} type(s), ${o.supported_brand_ids?.length ?? 0} brand(s)`
                          : "Not configured"}
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <Badge variant={o.supports_emergency ? "success" : "muted"} size="sm">
                          {o.supports_emergency ? "Yes" : "No"}
                        </Badge>
                      </td>
                      <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-primary)" }}>
                        {fmt(o.provider_price_override)}
                      </td>
                      <td style={{ padding:"10px 12px", maxWidth:180 }}>
                        <BlockerList blockers={o.readiness_blockers}/>
                      </td>
                      <td style={{ padding:"10px 12px", fontSize:11, color:"var(--text-tertiary)", whiteSpace: "nowrap" }}>
                        {o.created_at ? new Date(o.created_at).toLocaleDateString("en-IN") : "—"}
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <div style={{ display:"flex", gap:4, flexWrap:"wrap" }}>
                          <Btn size="xs" variant="ghost" onClick={() => {
                            setDrawerEnabled(o); setDrawerOffering(null);
                          }}>
                            <Edit2 size={11}/> Edit
                          </Btn>
                          {o.status === "draft" || o.status === "inactive" ? (
                            <Btn size="xs" variant="ghost"
                              disabled={o.readiness_status !== "ready"}
                              loading={activateAction.loading}
                              onClick={() => activateAction.execute(o.provider_enabled_offering_id)}>
                              Activate
                            </Btn>
                          ) : o.status === "active" ? (
                            <Btn size="xs" variant="ghost" loading={deactivateAction.loading}
                              onClick={() => deactivateAction.execute(o.provider_enabled_offering_id)}>
                              Deactivate
                            </Btn>
                          ) : null}
                          <Btn size="xs" variant="ghost" loading={refreshReadinessAction.loading}
                            onClick={() => refreshReadinessAction.execute(o.provider_enabled_offering_id)}>
                            <RefreshCw size={10}/> Readiness
                          </Btn>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableSurface>
            </div>
          </Card>
        )
      )}

      {/* Tab: Readiness Issues */}
      {tab === "readiness" && (
        enabled.loading ? (
          <Skeleton height={200}/>
        ) : enabled.error ? (
          <SectionError title="We couldn't load readiness issues" message="Retry or contact support with the request ID."
            requestId={enabled.requestId} section="GET /v1/provider/offerings/enabled" onRetry={() => enabled.refetch()}/>
        ) : withBlockers.length === 0 ? (
          <Card><div style={{ textAlign:"center", padding:"40px 0" }}>
            <CheckCircle2 size={32} style={{ color:"var(--success)", display:"block", margin:"0 auto 12px" }}/>
            <p style={{ fontSize:14, fontWeight: 600, color:"var(--success)", margin:"0 0 4px" }}>
              No readiness issues found.
            </p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
              Your enabled offerings satisfy current setup checks.
            </p>
          </div></Card>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
            {withBlockers.map(o => (
              <Card key={o.provider_enabled_offering_id}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start",
                  marginBottom:10, flexWrap:"wrap", gap:8 }}>
                  <div>
                    <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                      {o.provider_display_name ?? o.offering_name} is not bookable
                    </p>
                    <div style={{ display:"flex", gap:6, marginTop:4 }}>
                      <Badge variant={STATUS_VARIANT[o.status] ?? "muted"} size="sm">{o.status}</Badge>
                      <Badge variant="danger" size="sm">
                        {o.readiness_blockers?.length ?? 0} blocker{(o.readiness_blockers?.length ?? 0) !== 1 ? "s" : ""}
                      </Badge>
                    </div>
                  </div>
                  <Btn size="xs" variant="secondary" loading={refreshReadinessAction.loading}
                    onClick={() => refreshReadinessAction.execute(o.provider_enabled_offering_id)}>
                    <RefreshCw size={10}/> Refresh
                  </Btn>
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                  {(o.readiness_blockers ?? []).map((b, i) => (
                    <div key={i} style={{ padding:"8px 12px", borderRadius:"var(--radius-md)",
                      background:"rgba(220,38,38,0.06)", border:"1px solid rgba(220,38,38,0.2)" }}>
                      <p style={{ fontSize:12, color:"var(--danger)", margin:0, fontWeight:500 }}>Reason: {b.message}</p>
                      <p style={{ fontSize:10, fontFamily:"monospace", color:"var(--danger)", opacity:0.7, margin:"2px 0 0" }}>
                        Rule: {b.code}
                      </p>
                      {b.route && (
                        <Link href={b.route} style={{ fontSize:11, color:"var(--brand)", display:"block", marginTop:4 }}>
                          → CTA: Go fix it
                        </Link>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        )
      )}

      {/* Tab: Catalog Diagnostics */}
      {tab === "diagnostics" && (
        <CatalogDiagnosticsPanel
          tenantVertical={tenant.vertical}
          categoryType={categoryType}
          availableCount={availableListRaw.length}
          availableError={available.error}
          availableRequestId={available.requestId}
        />
      )}

      {/* Recent Activity */}
      {tab !== "diagnostics" && (
        <Card padding={0} style={{ marginTop: 20 }}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
            <ActivityIcon size={14}/>
            <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Recent Activity</p>
          </div>
          {activityApi.loading ? <div style={{ padding: 16 }}><Skeleton height={60}/></div> : activityApi.error ? (
            <div style={{ padding: 16 }}>
              <SectionError title="Couldn't load activity" message="Recent activity could not be loaded." requestId={activityApi.requestId} section="GET /v1/tenants/{id}/audit-log" onRetry={() => activityApi.refetch()}/>
            </div>
          ) : (activityApi.data?.logs ?? []).length === 0 ? (
            <EmptyState icon={<ActivityIcon/>} title="No status activity yet." description="Status recalculations and setup changes will appear here."/>
          ) : (
            <div style={{ padding: "8px 0" }}>
              {(activityApi.data?.logs ?? []).slice(0, 8).map((l, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 18px", fontSize: 12, borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontFamily: "monospace" }}>{l.action_type}</span>
                  <span style={{ color: "var(--text-tertiary)" }}>{new Date(l.created_at).toLocaleString("en-IN")}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Enable/Edit Drawer */}
      <EnableDrawer
        open={drawerOffering !== null || drawerEnabled !== null}
        onClose={() => { setDrawerOffering(null); setDrawerEnabled(null); }}
        offering={drawerOffering}
        existing={drawerEnabled}
        categoryType={categoryType}
        onSaved={handleSaved}
      />
    </TenantLayout>
  );
}

function HeroStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "0 0 2px", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
      <p style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{value}</p>
    </div>
  );
}

function CatalogDiagnosticsPanel({ tenantVertical, categoryType, availableCount, availableError, availableRequestId }: {
  tenantVertical: string | null; categoryType: string | null; availableCount: number;
  availableError: string | null; availableRequestId: string | null;
}) {
  const checks = [
    { label: "Tenant vertical is set", pass: !!tenantVertical, detail: tenantVertical ? `Vertical: ${tenantVertical}` : "No vertical set on tenant record." },
    { label: "Category runtime resolved", pass: !!categoryType, detail: categoryType ? `Category type: ${categoryType}` : "No category runtime resolved for this tenant." },
    { label: "Available Offerings API responded", pass: !availableError, detail: availableError ? `Failed: ${availableError}` : `${availableCount} offering(s) returned.` },
    { label: "Catalog has eligible services for this vertical", pass: availableCount > 0, detail: availableCount > 0 ? `${availableCount} platform-approved service(s) found.` : "No services found — check vertical mapping and platform catalog." },
  ];

  return (
    <Card padding={0}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
        <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Catalog Diagnostics</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>
          Live checks confirming why offerings are or are not appearing for your tenant.
        </p>
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {checks.map(c => (
          <div key={c.label} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 20px", borderBottom: "1px solid var(--border)" }}>
            {c.pass ? <CheckCircle2 size={16} style={{ color: "var(--success)", flexShrink: 0, marginTop: 1 }}/> : <XCircle size={16} style={{ color: "var(--danger)", flexShrink: 0, marginTop: 1 }}/>}
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{c.label}</p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>{c.detail}</p>
            </div>
          </div>
        ))}
      </div>
      <div style={{ padding: "12px 20px" }}>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          Historical note: this endpoint previously queried an unpopulated legacy table (master_offerings) instead
          of the real, live platform catalog (master_services). Fixed — see
          TENANT_MY_OFFERINGS_CATALOG_DIAGNOSTIC_REPORT.md for full detail.
          {availableRequestId && ` Last request ID: ${availableRequestId}.`}
        </p>
      </div>
    </Card>
  );
}
