"use client";
/**
 * Services & Pricing — 3-panel workspace (catalog tree / offering detail /
 * effective pricing). Reads GET /v1/tenant/home-services/services[/{id}]
 * (admin_catalog/tenant_services_workspace_router.py), a thin aggregator
 * over the existing TenantCatalogService (validate_for_publish,
 * resolve_tenant_price, get_tenant_service_types/brands) -- no second
 * catalog/pricing engine.
 *
 * All mutations (default pricing, type/brand support + pricing, save
 * draft, publish) call the SAME real, already-tested endpoints the
 * onboarding Services & Pricing wizard uses (homeServicesSetupApi ->
 * /v1/tenant/catalog/enabled-services/...). Clear-override endpoints keep
 * the Type/Brand enabled while reverting only its optional price.
 *
 * Add Services and the customer catalog preview are intentionally backed by
 * the same list/enable endpoints as onboarding. Unsupported bulk-import and
 * publication-history controls are not rendered as dead actions.
 *
 * Tenant offerings are scoped per (Master Service, Job Type), so Repair and
 * Installation keep independent setup, publication, and operational data.
 */
import React, {
  forwardRef, Suspense, useEffect, useImperativeHandle, useMemo, useRef, useState,
} from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  Eye, Plus, Save, Search, ArrowRight, RefreshCw, Trash2,
} from "lucide-react";
import {
  PageShell, Card, StatusBadge, Skeleton, Alert, Button, Input, Modal,
} from "@serviceos/design-system";
import {
  servicesWorkspaceApi, homeServicesSetupApi, providerStatusApi,
  providerServiceOptionApi,
  type SWCatalogService, type SWCatalogGroup, type SWResolvedPrice, type SWOfferingDetail,
  type AdminMasterServiceRow, type TenantEnabledService,
  type HsSetupAvailableType, type HsSetupBrand, type HsTypePricing,
  type ProviderAvailableServiceOption, type ProviderSupportedServiceOption,
} from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";
import { ServiceRequirementsPanel } from "./ServiceRequirementsPanel";
import {
  InlineDimensionPricingEditor, type InlineDimensionPricingEditorHandle,
} from "./InlineDimensionPricingEditor";
import { RepairEstimateGuidanceEditor } from "./RepairEstimateGuidanceEditor";

type CatalogStatus = "all" | "published" | "draft" | "needs_attention";
const CATALOG_STATUS_FILTERS: Array<{ value: CatalogStatus; label: string }> = [
  { value: "all", label: "All" },
  { value: "published", label: "Published" },
  { value: "draft", label: "Draft" },
  { value: "needs_attention", label: "Needs attention" },
];

const INSPECTION_PRICING_BEHAVIORS = new Set([
  "inspection_required", "inspection_quote", "visit_fee_plus_quote", "quote", "custom_quote",
]);

function isInspectionPricing(behavior?: string | null) {
  return INSPECTION_PRICING_BEHAVIORS.has(String(behavior ?? "").toLowerCase());
}

export default function ServicesPricingPage() {
  return (
    <Suspense fallback={null}>
      <ServicesPricingPageContent />
    </Suspense>
  );
}

function ServicesPricingPageContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const idParts = params.serviceId as string[] | undefined;
  const selectedId = idParts?.[0] ?? null;
  const [previewOpen, setPreviewOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const query = searchParams.get("q") ?? "";
  const requestedStatus = searchParams.get("status");
  const statusFilter: CatalogStatus = CATALOG_STATUS_FILTERS.some(option => option.value === requestedStatus)
    ? requestedStatus as CatalogStatus
    : "all";
  const groupFilter = searchParams.get("group") ?? "all";

  const workspace = useApi(() => servicesWorkspaceApi.get(), []);
  const setupCatalog = useApi(async () => {
    const [available, enabled] = await Promise.all([
      homeServicesSetupApi.listAvailable(),
      homeServicesSetupApi.listEnabled(),
    ]);
    return { available: available.services, enabled: enabled.services };
  }, []);

  const fallbackGroups = useMemo<SWCatalogGroup[]>(() => {
    if (!setupCatalog.data) return [];
    const availableByPair = new Map(setupCatalog.data.available.map(service => [
      `${service.service_id}:${service.job_type_id ?? ""}`, service,
    ]));
    const groups = new Map<string, SWCatalogGroup>();
    for (const enabled of setupCatalog.data.enabled) {
      const source = availableByPair.get(`${enabled.master_service_id}:${enabled.job_type_id ?? ""}`);
      const groupId = source?.service_group_id ?? enabled.category_id ?? "other";
      const groupName = source?.service_group_name ?? enabled.service_group_name ?? "Other services";
      if (!groups.has(groupId)) groups.set(groupId, { service_group_id: groupId, name: groupName, services: [] });
      const inspection = isInspectionPricing(source?.pricing_model);
      const pricingReady = inspection
        ? !!enabled.tenant_visit_fee
        : String(enabled.job_type).toLowerCase() === "consultation"
          ? true
          : !!enabled.tenant_min_price && !!enabled.tenant_max_price;
      const readinessReady = source?.admin_ready !== false && pricingReady && Number(enabled.warranty_days ?? 0) >= 5;
      groups.get(groupId)!.services.push({
        tenant_service_id: enabled.tenant_service_id,
        master_service_id: enabled.master_service_id,
        name: enabled.tenant_display_name || enabled.service_name || source?.service_name || "Service offering",
        job_type_label: enabled.job_type_label || source?.job_type_label || enabled.job_type,
        setup_status: enabled.setup_status === "published" ? "published" : "draft",
        missing_pricing: !pricingReady,
        readiness_ready: readinessReady,
        blocker_count: readinessReady ? 0 : 1,
        customer_visible: enabled.setup_status === "published" && readinessReady,
        pricing_behavior: source?.pricing_model ?? null,
        tenant_min_price: enabled.tenant_min_price ?? null,
        tenant_max_price: enabled.tenant_max_price ?? null,
        tenant_visit_fee: enabled.tenant_visit_fee ?? null,
      });
    }
    return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [setupCatalog.data]);

  const catalogGroups = workspace.data?.catalog_tree?.length ? workspace.data.catalog_tree : fallbackGroups;

  const allServices = catalogGroups.flatMap(g => g.services);
  const needsAttention = allServices.filter(service => !service.readiness_ready).length;
  const inspectionBased = allServices.filter(service => isInspectionPricing(service.pricing_behavior)).length;
  const summary = workspace.data?.catalog_tree?.length ? workspace.data.summary : {
    enabled_services: allServices.length,
    published: allServices.filter(service => service.setup_status === "published").length,
    draft: allServices.filter(service => service.setup_status !== "published").length,
    missing_pricing: allServices.filter(service => service.missing_pricing).length,
    type_overrides: 0,
    brand_overrides: 0,
  };
  const visibleGroups = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return catalogGroups
      .filter(group => groupFilter === "all" || group.service_group_id === groupFilter)
      .map(group => ({
        ...group,
        services: group.services.filter(service => {
          const matchesQuery = !normalizedQuery
            || `${service.name} ${service.job_type_label ?? ""}`.toLowerCase().includes(normalizedQuery);
          const matchesStatus = statusFilter === "all"
            || (statusFilter === "needs_attention" && !service.readiness_ready)
            || (statusFilter !== "needs_attention" && service.setup_status === statusFilter);
          return matchesQuery && matchesStatus;
        }),
      }))
      .filter(group => group.services.length > 0);
  }, [catalogGroups, query, statusFilter, groupFilter]);
  const visibleServices = visibleGroups.flatMap(group => group.services);
  const selectedVisible = !!selectedId && visibleServices.some(service => service.tenant_service_id === selectedId);
  const filtersActive = !!query.trim() || statusFilter !== "all" || groupFilter !== "all";
  // A bookmarked service detail remains useful even when the catalog summary
  // is temporarily empty/stale; the detail endpoint still validates tenant
  // ownership. Filters only replace it when they intentionally hide it.
  const effectiveId = selectedId && (!filtersActive || selectedVisible)
    ? selectedId
    : (visibleServices[0]?.tenant_service_id ?? (filtersActive ? null : allServices[0]?.tenant_service_id) ?? null);

  function updateQuery(next: { q?: string | null; status?: CatalogStatus | null; group?: string | null }) {
    const queryParams = new URLSearchParams(searchParams.toString());
    Object.entries(next).forEach(([key, value]) => {
      if (!value || value === "all") queryParams.delete(key);
      else queryParams.set(key, value);
    });
    const suffix = queryParams.toString();
    router.replace(`${selectedId ? `/home-services/services/${selectedId}` : "/home-services/services"}${suffix ? `?${suffix}` : ""}`);
  }

  function openService(tenantServiceId: string) {
    const suffix = searchParams.toString();
    router.push(`/home-services/services/${tenantServiceId}${suffix ? `?${suffix}` : ""}`);
  }

  function clearFilters() {
    updateQuery({ q: null, status: null, group: null });
  }

  return (
      <PageShell>
        <div className="pricing-experience">
        <header className="pricing-page-header">
          <div className="pricing-page-heading">
            <span className="pricing-page-eyebrow">Business · Service catalog</span>
            <h1 className="pricing-page-title">Services &amp; pricing</h1>
            <p className="pricing-page-description">Repairs are quoted after inspection — you set the inspection charge. Service and installation use your fixed price.</p>
          </div>
          <div className="pricing-page-actions">
            <Button variant="secondary" size="sm" leftIcon={<Eye size={14} />}
              onClick={() => setPreviewOpen(true)}>Preview customer view</Button>
            <Button variant="secondary" size="sm" leftIcon={<ArrowRight size={14} />}
              onClick={() => router.push("/tenant/home-services/setup/services-pricing?return_to=%2Fhome-services%2Fservices")}>
              Guided setup
            </Button>
            <Button variant="primary" size="sm" leftIcon={<Plus size={14} />}
              onClick={() => setAddOpen(true)}>
              Add services
            </Button>
          </div>
        </header>

        {workspace.error && !setupCatalog.data && <Alert tone="danger">{workspace.error}</Alert>}

        {workspace.error && !workspace.data && !setupCatalog.data ? (
          <Card>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>The service summary could not be loaded.</span>
              <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={13} />} onClick={workspace.refetch}>Retry</Button>
            </div>
          </Card>
        ) : (workspace.loading || !workspace.data) && setupCatalog.loading ? (
          <div className="pricing-stat-grid">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={80} />)}
          </div>
        ) : (
          <div className="pricing-stat-grid">
            <PricingStat label="Live offerings" value={summary.published} note="visible to customers" />
            <PricingStat label="Drafts" value={summary.draft} note="not bookable yet" />
            <PricingStat label="Needs attention" value={needsAttention} note={needsAttention ? "missing charge, warranty or setup" : "all complete"} warning={needsAttention > 0} />
            <PricingStat label="Inspection-based" value={inspectionBased} note="priced after diagnosis" />
            <PricingStat label="Type prices" value={summary.type_overrides} note="across all jobs" />
            <PricingStat label="Brand exceptions" value={summary.brand_overrides} note="kept intentionally rare" />
          </div>
        )}

        <div className="pricing-workspace-grid">
          <aside className="pricing-offerings-rail" aria-label="Your offerings">
            <div className="pricing-rail-head">
              <div className="pricing-rail-title-row">
                <span className="pricing-rail-title">Your offerings</span>
                <span className="pricing-rail-count">{visibleServices.length} of {allServices.length}</span>
              </div>
              {filtersActive && (
                <button type="button" onClick={clearFilters} aria-label="Clear catalog filters" title="Clear filters"
                  style={{ position: "absolute", top: 12, right: 10, border: "none", background: "transparent", color: "var(--brand)", cursor: "pointer", padding: 4 }}>
                  <RefreshCw size={14} />
                </button>
              )}
              <label className="pricing-search">
                <Search size={14} aria-hidden />
                <input aria-label="Search services" value={query} onChange={event => updateQuery({ q: event.target.value || null })} placeholder="Search services"
                />
              </label>
            <div role="group" aria-label="Filter by setup status" className="pricing-filter-row">
              {CATALOG_STATUS_FILTERS.map(option => (
                <button type="button" key={option.value} aria-pressed={statusFilter === option.value} onClick={() => updateQuery({ status: option.value })}
                  className="pricing-filter-pill">
                  {option.label}
                </button>
              ))}
            </div>
            <label style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
              <span>Filter by service group</span>
              <select aria-label="Filter by service group" value={groupFilter} onChange={event => updateQuery({ group: event.target.value as string })}>
                <option value="all">All groups</option>
                {catalogGroups.map(group => <option key={group.service_group_id} value={group.service_group_id}>{group.name}</option>)}
              </select>
            </label>
            </div>
            <div className="pricing-offerings-list">
            {workspace.loading && setupCatalog.loading ? (
              <Skeleton height={200} />
            ) : allServices.length === 0 ? (
              <div style={{ padding: 12, fontSize: 13, color: "var(--text-tertiary)" }}>No services enabled yet. Add your first service to begin.</div>
            ) : visibleGroups.length === 0 ? (
              <div style={{ padding: 12, fontSize: 12.5, color: "var(--text-tertiary)" }}>
                No offerings match these filters.
                <button type="button" onClick={clearFilters} style={{ display: "block", border: "none", background: "none", color: "var(--brand)", cursor: "pointer", padding: "8px 0 0", fontWeight: 650 }}>Clear filters</button>
              </div>
            ) : (
              visibleGroups.map(group => (
                <div key={group.service_group_id}>
                  <span className="pricing-group-label">{group.name}</span>
                  {group.services.map(s => (
                    <CatalogRow key={s.tenant_service_id} s={s} selected={s.tenant_service_id === effectiveId}
                      onClick={() => openService(s.tenant_service_id)} />
                  ))}
                </div>
              ))
            )}
            </div>
          </aside>

          {effectiveId ? (
            <OfferingWorkspace
              key={effectiveId}
              tenantServiceId={effectiveId}
              groupName={catalogGroups.find(group => group.services.some(service => service.tenant_service_id === effectiveId))?.name}
              onWorkspaceChanged={workspace.refetch}
            />
          ) : (
            <Card><div style={{ textAlign: "center", padding: 40, color: "var(--text-tertiary)", fontSize: 13 }}>
              {filtersActive ? "No offering matches the current filters." : "Add a service to start configuring pricing and publication."}
              {filtersActive && <div style={{ marginTop: 10 }}><Button variant="secondary" size="sm" onClick={clearFilters}>Clear filters</Button></div>}
            </div></Card>
          )}
        </div>

        <CustomerCatalogPreview
          open={previewOpen}
          onClose={() => setPreviewOpen(false)}
          groups={catalogGroups}
        />
        {addOpen && (
          <AddServicesModal
            onClose={() => setAddOpen(false)}
            onAdded={(service) => {
              setAddOpen(false);
              workspace.refetch();
              openService(service.tenant_service_id);
            }}
          />
        )}
        </div>
      </PageShell>
  );
}

function PricingStat({ label, value, note, warning = false }: { label: string; value: number; note: string; warning?: boolean }) {
  return (
    <div className={`pricing-stat${warning ? " is-warning" : ""}`}>
      <span className="pricing-stat-label">{label}</span>
      <span className="pricing-stat-value">{value}</span>
      <span className="pricing-stat-note">{note}</span>
    </div>
  );
}

function CustomerCatalogPreview({ open, onClose, groups }: {
  open: boolean; onClose: () => void; groups: SWCatalogGroup[];
}) {
  const publishedGroups = groups
    .map(group => ({ ...group, services: group.services.filter(service => service.customer_visible) }))
    .filter(group => group.services.length > 0);

  return (
    <Modal open={open} onClose={onClose} title="Customer catalog preview"
      footer={<Button variant="secondary" size="sm" onClick={onClose}>Close</Button>}>
      <p style={{ margin: "0 0 14px", fontSize: 12.5, color: "var(--text-tertiary)" }}>
        This is the set of published, fully priced services customers can discover. Draft services stay private.
      </p>
      {publishedGroups.length === 0 ? (
        <Alert tone="info">No services are customer-visible yet. Finish pricing and publish a service to include it here.</Alert>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: "min(34rem, 80vw)" }}>
          {publishedGroups.map(group => (
            <section key={group.service_group_id} aria-labelledby={`preview-${group.service_group_id}`}>
              <h3 id={`preview-${group.service_group_id}`} style={{ margin: "0 0 7px", fontSize: 12, color: "var(--text-tertiary)" }}>
                {group.name}
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {group.services.map(service => (
                  <div key={service.tenant_service_id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
                    padding: "10px 12px", border: "1px solid var(--border)", borderRadius: 8 }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 650, color: "var(--text-primary)" }}>{service.name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{service.job_type_label ?? "Service"}</div>
                    </div>
                    <StatusBadge status="published" size="sm" />
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </Modal>
  );
}

function AddServicesModal({ onClose, onAdded }: {
  onClose: () => void; onAdded: (service: TenantEnabledService) => void;
}) {
  const router = useRouter();
  const available = useApi(() => homeServicesSetupApi.listAvailable(), []);
  const enabled = useApi(() => homeServicesSetupApi.listEnabled(), []);
  const [addingId, setAddingId] = useState<string | null>(null);
  const [addError, setAddError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const candidates = useMemo(() => {
    const enabledKeys = new Set((enabled.data?.services ?? []).map(service =>
      `${service.master_service_id}:${service.job_type_id ?? ""}`));
    const normalizedQuery = search.trim().toLowerCase();
    return (available.data?.services ?? []).filter(service => {
      const key = `${service.service_id}:${service.job_type_id ?? ""}`;
      const matchesQuery = !normalizedQuery
        || `${service.service_name} ${service.job_type_label ?? service.job_type} ${service.service_group_name ?? ""}`.toLowerCase().includes(normalizedQuery);
      return !enabledKeys.has(key) && matchesQuery;
    });
  }, [available.data, enabled.data, search]);
  const grouped = useMemo(() => {
    const groups = new Map<string, { name: string; services: AdminMasterServiceRow[] }>();
    for (const service of candidates) {
      const key = service.service_group_id ?? "ungrouped";
      if (!groups.has(key)) groups.set(key, { name: service.service_group_name ?? "Other services", services: [] });
      groups.get(key)!.services.push(service);
    }
    return Array.from(groups.entries()).sort((a, b) => a[1].name.localeCompare(b[1].name));
  }, [candidates]);

  async function addService(service: AdminMasterServiceRow) {
    const offeringKey = `${service.service_id}:${service.job_type_id ?? ""}`;
    setAddingId(offeringKey);
    setAddError(null);
    try {
      if (service.admin_ready === false) throw new Error(service.admin_blockers?.[0]?.message ?? "Admin must publish this service workflow before it can be added.");
      if (!service.job_type_id) throw new Error("This service has no job type configured.");
      const created = await homeServicesSetupApi.enable({ master_service_id: service.service_id, job_type_id: service.job_type_id });
      onAdded(created);
    } catch (error) {
      setAddError(error instanceof Error ? error.message : "Could not add this service.");
    } finally {
      setAddingId(null);
    }
  }

  return (
    <Modal open onClose={onClose} title="Add services"
      footer={<Button variant="secondary" size="sm" onClick={onClose}>Close</Button>}>
      <div style={{ minWidth: "min(38rem, 82vw)" }}>
        <p style={{ margin: "0 0 14px", fontSize: 12.5, color: "var(--text-tertiary)" }}>
          Add a service from the same Admin-approved catalog used during setup. It will start as a private draft.
        </p>
        <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
          <label style={{ position: "relative", flex: "1 1 230px" }}>
            <Search size={14} aria-hidden style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }} />
            <input aria-label="Search services to add" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search service, group or job type"
              style={{ width: "100%", height: 36, boxSizing: "border-box", padding: "0 10px 0 32px", border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-sunken)", color: "var(--text-primary)" }} />
          </label>
          <Button variant="secondary" size="sm" leftIcon={<ArrowRight size={13} />}
            onClick={() => { onClose(); router.push("/tenant/home-services/setup/services-pricing?return_to=%2Fhome-services%2Fservices"); }}>
            Open guided setup
          </Button>
        </div>
        {addError && <Alert tone="danger">{addError}</Alert>}
        {available.loading || enabled.loading ? <Skeleton height={220} /> : available.error || enabled.error ? (
          <Alert tone="danger">{available.error ?? enabled.error}</Alert>
        ) : grouped.length === 0 ? (
          <Alert tone="info">Every available service is already in your catalog.</Alert>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 14, maxHeight: "55vh", overflowY: "auto" }}>
            {grouped.map(([groupId, group]) => (
              <section key={groupId} aria-labelledby={`add-${groupId}`}>
                <h3 id={`add-${groupId}`} style={{ margin: "0 0 7px", fontSize: 12, color: "var(--text-tertiary)" }}>{group.name}</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                  {group.services.map(service => (
                    <div key={service.service_id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
                      padding: "10px 12px", border: "1px solid var(--border)", borderRadius: 8 }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 650, color: "var(--text-primary)" }}>{service.service_name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                          {service.job_type_label ?? service.job_type.replaceAll("_", " ")} · {service.pricing_model.replaceAll("_", " ")}
                        </div>
                        {service.admin_ready === false && <div style={{ fontSize: 10.5, color: "var(--warning-text)", marginTop: 3 }}>{service.admin_blockers?.[0]?.message ?? "Waiting for Admin workflow"}</div>}
                      </div>
                      <Button variant="secondary" size="sm" loading={addingId === `${service.service_id}:${service.job_type_id ?? ""}`}
                        disabled={addingId !== null || service.admin_ready === false || !service.job_type_id} onClick={() => addService(service)}>
                        Add
                      </Button>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}

function CatalogRow({ s, selected, onClick }: { s: SWCatalogService; selected: boolean; onClick: () => void }) {
  const priceLabel = isInspectionPricing(s.pricing_behavior)
    ? s.tenant_visit_fee != null ? `₹${s.tenant_visit_fee.toLocaleString("en-IN")} inspection` : "No charge set"
    : s.tenant_min_price != null
      ? s.tenant_max_price != null && s.tenant_max_price !== s.tenant_min_price
        ? `₹${s.tenant_min_price.toLocaleString("en-IN")}–₹${s.tenant_max_price.toLocaleString("en-IN")}`
        : `₹${s.tenant_min_price.toLocaleString("en-IN")}`
      : "No price set";
  return (
    <button type="button" onClick={onClick} aria-current={selected ? "page" : undefined}
      className="pricing-offering-row">
      <span className="pricing-offering-copy">
        <span className="pricing-offering-name">{s.name}</span>
        <span className="pricing-offering-meta">{s.job_type_label ?? "Service"} · {priceLabel}</span>
      </span>
      <span className={`pricing-status-chip${!s.readiness_ready ? " is-warning" : s.setup_status === "published" ? " is-live" : ""}`}>
        {!s.readiness_ready ? "Fix" : s.setup_status === "published" ? "Live" : "Draft"}
      </span>
    </button>
  );
}

const TABS = ["overview", "types-brands", "options", "pricing", "visit-fee", "warranty", "requirements"] as const;
type Tab = typeof TABS[number];
/** Two-column detail+effective-pricing area, driven by one shared refetch so an
 * edit anywhere (pricing/types/brands/publish) reloads both real projections. */
function OfferingWorkspace({ tenantServiceId, groupName, onWorkspaceChanged }: {
  tenantServiceId: string;
  groupName?: string;
  onWorkspaceChanged: () => void;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const detail = useApi(() => servicesWorkspaceApi.detail(tenantServiceId), [tenantServiceId]);
  const pricingEditorRef = useRef<PricingEditorHandle>(null);
  const dimensionEditorRef = useRef<InlineDimensionPricingEditorHandle>(null);
  const [pricingDirty, setPricingDirty] = useState(false);
  const [dimensionDirty, setDimensionDirty] = useState(false);
  const hasDraftChanges = pricingDirty || dimensionDirty;

  const refreshAll = () => { detail.refetch(); onWorkspaceChanged(); };

  if (detail.error) return (
    <Card>
      <Alert tone="danger">{detail.error}</Alert>
      <div style={{ marginTop: 10 }}><Button variant="secondary" size="sm" onClick={detail.refetch}>Retry</Button></div>
    </Card>
  );
  if (detail.loading || !detail.data) return (
    <div className="services-offering-grid">
      <Card><Skeleton height={400} /></Card><Card><Skeleton height={300} /></Card>
    </div>
  );

  const data = detail.data;
  const ts = data.tenant_service as { setup_status: string; requires_type: boolean; requires_brand: boolean; master_service_id?: string; job_type_id?: string; job_type?: string };
  const inspectionPricing = isInspectionPricing(data.blueprint.pricing_behavior);
  const consultationPricing = String(ts.job_type ?? "").toLowerCase() === "consultation";
  const pricingMode: "inspection" | "consultation" | "dimension" = inspectionPricing
    ? "inspection"
    : consultationPricing ? "consultation" : "dimension";
  const fixedPricing = pricingMode === "dimension" && data.blueprint.pricing_behavior === "fixed";
  const availableTabs: Tab[] = pricingMode === "inspection"
    ? ["overview", "types-brands", "options", "visit-fee", "warranty", "requirements"]
    : pricingMode === "consultation"
      ? ["overview", "types-brands", "options", "warranty", "requirements"]
      : ["overview", "types-brands", "options", "pricing", "warranty", "requirements"];
  const requestedTab = searchParams.get("tab") as Tab | null;
  const tab: Tab = requestedTab && availableTabs.includes(requestedTab) ? requestedTab : "overview";

  function setTab(nextTab: Tab) {
    const queryParams = new URLSearchParams(searchParams.toString());
    if (nextTab === "overview") queryParams.delete("tab");
    else queryParams.set("tab", nextTab);
    const suffix = queryParams.toString();
    router.replace(`/home-services/services/${tenantServiceId}${suffix ? `?${suffix}` : ""}`);
  }

  return (
    <div className="pricing-detail-stack">
      <section className="pricing-panel pricing-service-head">
        <div className="pricing-service-copy">
          <span className="pricing-service-category">{groupName ?? data.service_group_name ?? "Service offering"}</span>
          <span className="pricing-service-name">{data.service_name}</span>
          <span className="pricing-service-tagline">
            {pricingMode === "inspection" ? "Inspection first, estimate after diagnosis" : pricingMode === "consultation" ? "One provider-wide consultation price" : "Your price is shown to customers at booking"}
          </span>
        </div>
        <div className="pricing-service-badges">
          <span className={`pricing-kind-pill${pricingMode === "inspection" ? " is-inspection" : ""}`}>
            {pricingMode === "inspection" ? "Inspection based" : pricingMode === "consultation" ? "Consultation" : "Fixed price"}
          </span>
          <span className={`pricing-kind-pill is-status${ts.setup_status === "published" ? "" : " is-draft"}`}>
            {ts.setup_status === "published" ? "Live" : "Draft"}
          </span>
        </div>
      </section>

      {pricingMode === "inspection" && (
        <section className="pricing-journey">
          <span className="pricing-journey-title">Why there is no repair price here</span>
          <div className="pricing-journey-grid">
            <PricingJourneyStep number="1" title="Customer books an inspection" copy="They pay your inspection charge to get a technician on site." />
            <PricingJourneyStep number="2" title="You diagnose and quote" copy="Parts and labour are added after the technician has seen the unit." />
            <PricingJourneyStep number="3" title="Estimate approved" copy="The inspection charge is adjusted into the final bill." />
          </div>
        </section>
      )}

      {pricingMode === "consultation" ? (
        <div className="pricing-panel"><ConsultationFeeCard /></div>
      ) : (
        <UnifiedPricingEditor ref={pricingEditorRef} tenantServiceId={tenantServiceId} data={data} pricingMode={pricingMode} onDirtyChange={setPricingDirty}>
          {fixedPricing && <OperationalDimensionPricing editorRef={dimensionEditorRef} tenantServiceId={tenantServiceId} data={data} onDirtyChange={setDimensionDirty} />}
        </UnifiedPricingEditor>
      )}

      <details className="pricing-collapsible" open={tab === "options"}>
        <summary onClick={() => setTab(tab === "options" ? "overview" : "options")}>
          <span>
            <span className="pricing-collapsible-title">Customer-selectable service options</span>
            <span className="pricing-collapsible-copy">Configure the options Admin mapped to this exact job type.</span>
          </span>
        </summary>
        <div className="pricing-collapsible-body">
          <ServiceOptionsTab masterServiceId={String(ts.master_service_id ?? "")} jobTypeId={String(ts.job_type_id ?? "")} />
        </div>
      </details>

      <details className="pricing-collapsible" open={tab === "requirements"}>
        <summary onClick={() => setTab(tab === "requirements" ? "overview" : "requirements")}>
          <span>
            <span className="pricing-collapsible-title">Set by the platform</span>
            <span className="pricing-collapsible-copy">Booking questions, customer problems and technician checklist · Read-only.</span>
          </span>
        </summary>
        <div className="pricing-collapsible-body">
          <ServiceRequirementsPanel masterServiceId={String(ts.master_service_id ?? "")} jobTypeId={String(ts.job_type_id ?? "")} />
        </div>
      </details>

      <PublicationCard tenantServiceId={tenantServiceId} data={data} hasDraftChanges={hasDraftChanges}
        beforeSave={async () => {
          await pricingEditorRef.current?.save();
          await dimensionEditorRef.current?.save();
        }} onChanged={() => { setPricingDirty(false); setDimensionDirty(false); refreshAll(); }} />
    </div>
  );
}

function PricingJourneyStep({ number, title, copy }: { number: string; title: string; copy: string }) {
  return (
    <div className="pricing-journey-step">
      <span className="pricing-journey-number">{number}</span>
      <span><strong>{title}</strong><span>{copy}</span></span>
    </div>
  );
}

interface PricingEditorHandle { save: () => Promise<void> }

const UnifiedPricingEditor = forwardRef<PricingEditorHandle, {
  tenantServiceId: string;
  data: SWOfferingDetail;
  pricingMode: "inspection" | "dimension";
  onDirtyChange?: (dirty: boolean) => void;
  children?: React.ReactNode;
}>(function UnifiedPricingEditor({ tenantServiceId, data, pricingMode, onDirtyChange, children }, ref) {
  const ts = data.tenant_service as {
    tenant_min_price?: number | null;
    tenant_max_price?: number | null;
    tenant_visit_fee?: number | null;
    tenant_emergency_surcharge?: number | null;
    warranty_days?: number | null;
  };
  const [minimum, setMinimum] = useState(ts.tenant_min_price != null ? String(ts.tenant_min_price) : "");
  const [maximum, setMaximum] = useState(ts.tenant_max_price != null ? String(ts.tenant_max_price) : "");
  const [visitFee, setVisitFee] = useState(ts.tenant_visit_fee != null ? String(ts.tenant_visit_fee) : "");
  const [surcharge, setSurcharge] = useState(ts.tenant_emergency_surcharge != null ? String(ts.tenant_emergency_surcharge) : "");
  const [warranty, setWarranty] = useState(String(ts.warranty_days ?? 5));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showEstimateRange, setShowEstimateRange] = useState(
    pricingMode === "inspection" && ts.tenant_min_price != null && ts.tenant_max_price != null,
  );
  const fixedPricing = pricingMode === "dimension" && data.blueprint.pricing_behavior === "fixed";
  useEffect(() => {
    setMinimum(ts.tenant_min_price != null ? String(ts.tenant_min_price) : "");
    setMaximum(ts.tenant_max_price != null ? String(ts.tenant_max_price) : "");
    setVisitFee(ts.tenant_visit_fee != null ? String(ts.tenant_visit_fee) : "");
    setSurcharge(ts.tenant_emergency_surcharge != null ? String(ts.tenant_emergency_surcharge) : "");
    setWarranty(String(ts.warranty_days ?? 5));
    setShowEstimateRange(pricingMode === "inspection" && ts.tenant_min_price != null && ts.tenant_max_price != null);
  }, [pricingMode, ts.tenant_min_price, ts.tenant_max_price, ts.tenant_visit_fee, ts.tenant_emergency_surcharge, ts.warranty_days]);

  const minimumNumber = Number(minimum);
  const maximumNumber = Number(maximum);
  const visitFeeNumber = Number(visitFee);
  const surchargeNumber = surcharge ? Number(surcharge) : null;
  const warrantyNumber = Number(warranty);
  const invalid = pricingMode === "inspection"
    ? !visitFee || !Number.isFinite(visitFeeNumber) || visitFeeNumber <= 0
    : fixedPricing
      ? !minimum || !Number.isFinite(minimumNumber) || minimumNumber <= 0
      : !minimum || !maximum || !Number.isFinite(minimumNumber) || !Number.isFinite(maximumNumber) || minimumNumber <= 0 || maximumNumber < minimumNumber;
  const secondaryInvalid = (surchargeNumber != null && (!Number.isFinite(surchargeNumber) || surchargeNumber < 0))
    || !Number.isInteger(warrantyNumber) || warrantyNumber < 5
    || (pricingMode === "inspection" && showEstimateRange
      && (!minimum || !maximum || !Number.isFinite(minimumNumber) || !Number.isFinite(maximumNumber)
        || minimumNumber <= 0 || maximumNumber < minimumNumber));

  useImperativeHandle(ref, () => ({
    save: async () => {
      if (invalid || secondaryInvalid) throw new Error("Complete the required pricing and warranty fields before publishing.");
      setLoading(true);
      setError("");
      try {
        await homeServicesSetupApi.updateEnabledService(tenantServiceId, {
          ...(pricingMode === "inspection"
            ? {
              tenant_visit_fee: visitFeeNumber,
              tenant_min_price: showEstimateRange ? minimumNumber : null,
              tenant_max_price: showEstimateRange ? maximumNumber : null,
            }
            : { tenant_min_price: minimumNumber, tenant_max_price: fixedPricing ? minimumNumber : maximumNumber }),
          tenant_emergency_surcharge: surchargeNumber ?? undefined,
          warranty_days: warrantyNumber,
        });
      } catch (value) {
        const message = value instanceof Error ? value.message : "Pricing could not be saved.";
        setError(message);
        throw value;
      } finally {
        setLoading(false);
      }
    },
  }), [
    fixedPricing, invalid, maximumNumber, minimumNumber, pricingMode, secondaryInvalid,
    showEstimateRange, surchargeNumber, tenantServiceId, visitFeeNumber, warrantyNumber,
  ]);

  function updateDraft(setter: (value: string) => void, value: string) {
    setter(value);
    onDirtyChange?.(true);
  }

  return (
    <section className="pricing-panel">
      <h2 className="pricing-section-title">{pricingMode === "inspection" ? "Inspection charge & estimate guidance" : "Your price"}</h2>
      <p className="pricing-section-copy">
        {pricingMode === "inspection"
          ? "Repairs cannot be priced before diagnosis. Set the visit charge; the final amount is approved after inspection."
          : fixedPricing ? "Straightforward job with a known scope, so the customer sees and pays a real amount at booking." : "Set the range customers see at booking. A Type or Brand override can replace it when needed."}
      </p>
      {error && <div style={{ marginTop: 12 }}><Alert tone="danger">{error}</Alert></div>}
      <div className="pricing-form-grid">
        {pricingMode === "inspection" ? (
          <PricingMoneyField label="Inspection charge" value={visitFee} onChange={value => updateDraft(setVisitFee, value)} placeholder="249" hint="Payable if the customer declines your estimate." />
        ) : fixedPricing ? (
          <PricingMoneyField label={data.service_name.toLowerCase().includes("installation") ? "Installation price" : "Service price"} value={minimum} onChange={value => updateDraft(setMinimum, value)} placeholder="899" hint="Applies to every booking unless a type or brand price is set below." />
        ) : (
          <>
            <PricingMoneyField label="Minimum price" value={minimum} onChange={value => updateDraft(setMinimum, value)} placeholder="600" hint="Your lowest expected charge." />
            <PricingMoneyField label="Maximum price" value={maximum} onChange={value => updateDraft(setMaximum, value)} placeholder="900" hint="Must be at least the minimum." />
          </>
        )}
        <PricingMoneyField label="Emergency add-on" value={surcharge} onChange={value => updateDraft(setSurcharge, value)} placeholder="0" hint="Nights, Sundays, same-day urgent." />
        <label className="pricing-field-label">
          <span>Warranty</span>
          <span className="pricing-field-control">
            <input aria-label="Warranty days" type="number" min={5} value={warranty} onChange={event => updateDraft(setWarranty, event.target.value)} placeholder="5" />
            <span className="pricing-field-suffix">days</span>
          </span>
          <span className="pricing-field-hint">On the work you did · minimum 5 days.</span>
        </label>
      </div>
      {pricingMode === "inspection" && (
        <RepairEstimateGuidanceEditor
          enabled={showEstimateRange}
          minimum={minimum}
          maximum={maximum}
          disabled={loading}
          onEnabledChange={value => { setShowEstimateRange(value); onDirtyChange?.(true); }}
          onMinimumChange={value => updateDraft(setMinimum, value)}
          onMaximumChange={value => updateDraft(setMaximum, value)}
        />
      )}
      {children}
      {(invalid || secondaryInvalid) && <p className="pricing-unsaved-note" role="alert">Complete the required price and warranty fields before publishing.</p>}
    </section>
  );
});

function PricingMoneyField({ label, value, onChange, placeholder, hint }: {
  label: string; value: string; onChange: (value: string) => void; placeholder: string; hint: string;
}) {
  return (
    <label className="pricing-field-label">
      <span>{label}</span>
      <span className="pricing-field-control">
        <span className="pricing-field-prefix">₹</span>
        <input aria-label={label} type="number" min={0} value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} />
      </span>
      <span className="pricing-field-hint">{hint}</span>
    </label>
  );
}

function OperationalDimensionPricing({ editorRef, tenantServiceId, data, onDirtyChange }: {
  editorRef: React.RefObject<InlineDimensionPricingEditorHandle | null>;
  tenantServiceId: string;
  data: SWOfferingDetail;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const availabilityKey = `${data.types.map(type => type.service_type_id).join(",")}|${data.brands.map(brand => brand.brand_id).join(",")}`;
  const availableTypes = useApi(() => homeServicesSetupApi.getAvailableTypes(tenantServiceId), [tenantServiceId, availabilityKey]);
  const availableBrands = useApi(() => homeServicesSetupApi.getAvailableBrands(tenantServiceId), [tenantServiceId, availabilityKey]);
  const typePricing = useApi(() => homeServicesSetupApi.getTypePricing(tenantServiceId), [tenantServiceId, availabilityKey]);
  const enabledTypeIds = (availableTypes.data?.types ?? []).filter(type => type.is_enabled).map(type => type.service_type_id);
  const typeIdsKey = enabledTypeIds.join(",");
  const brandPricing = useApi(async () => {
    if (enabledTypeIds.length) {
      const groups = await Promise.all(enabledTypeIds.map(async typeId => ({
        typeId,
        rows: (await homeServicesSetupApi.getBrandPricing(tenantServiceId, typeId)).brands,
      })));
      return groups;
    }
    return [{ typeId: undefined, rows: (await homeServicesSetupApi.getBrandPricing(tenantServiceId)).brands }];
  }, [tenantServiceId, typeIdsKey, availabilityKey]);
  const typeRows = typePricing.data?.types ?? [];
  const exceptions = (brandPricing.data ?? []).flatMap(group => group.rows
    .filter(row => row.tenant_min_price != null && row.tenant_max_price != null)
    .map(row => ({
      key: `${group.typeId ?? "default"}:${row.brand_id}`,
      typeId: group.typeId,
      brandId: row.brand_id,
      price: row.tenant_min_price,
      persisted: true,
    })));

  return (
    <>
      <InlineDimensionPricingEditor
        ref={editorRef}
        basePrice={(data.tenant_service as { tenant_min_price?: number | null }).tenant_min_price ?? null}
        types={(availableTypes.data?.types ?? []).map(type => ({
          id: type.service_type_id,
          name: type.name,
          enabled: type.is_enabled,
          price: typeRows.find((priced: HsTypePricing) => priced.service_type_id === type.service_type_id)?.tenant_min_price ?? null,
        }))}
        brands={(availableBrands.data?.brands ?? []).map(brand => ({
          id: brand.brand_id,
          name: brand.name,
          canOverride: brand.can_override_price,
          enabled: brand.is_enabled,
        }))}
        exceptions={exceptions}
        loading={availableTypes.loading || availableBrands.loading || typePricing.loading || brandPricing.loading}
        onSaveTypes={typeIds => homeServicesSetupApi.setTypes(tenantServiceId, typeIds)}
        onSaveBrands={brandIds => homeServicesSetupApi.setBrands(tenantServiceId, brandIds)}
        onSaveType={(typeId, price) => homeServicesSetupApi.setTypePricing(tenantServiceId, typeId, price, price)}
        onClearType={typeId => homeServicesSetupApi.clearTypePricing(tenantServiceId, typeId)}
        onClearTypePrices={() => Promise.all(typeRows.filter(type => type.tenant_min_price != null || type.tenant_max_price != null).map(type => homeServicesSetupApi.clearTypePricing(tenantServiceId, type.service_type_id)))}
        onSaveBrand={(typeId, brandId, price) => homeServicesSetupApi.setBrandPricing(tenantServiceId, brandId, price, price, typeId)}
        onClearBrand={(typeId, brandId) => homeServicesSetupApi.clearBrandPricing(tenantServiceId, brandId, typeId)}
        onDirtyChange={onDirtyChange}
      />
    </>
  );
}

function OverviewTab({ data }: { data: SWOfferingDetail }) {
  return (
    <>
      <Card title="Admin blueprint (read-only)">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12, fontSize: 12.5 }}>
          <BlueprintField label="Pricing behavior" value={(data.blueprint.pricing_behavior ?? "range").replaceAll("_", " ")} />
          <BlueprintField label="Type" value={data.blueprint.type_mode} />
          <BlueprintField label="Brand" value={data.blueprint.brand_mode} />
          <BlueprintField label="Customer issues" value={data.blueprint.requires_issue_type ? "Required" : "Optional"} />
          <BlueprintField label="Checklist" value={data.blueprint.requires_checklist ? "Required" : "Not required"} />
          <BlueprintField label="Estimate approval" value={data.blueprint.requires_estimate_approval ? "Required" : "Not required"} />
          <BlueprintField label="Technician" value={data.blueprint.requires_technician ? "Required" : "Optional"} />
          <BlueprintField label="Schedule" value={data.blueprint.requires_schedule ? "Required" : "Optional"} />
          <BlueprintField label="Service area" value={data.blueprint.requires_service_area ? "Required" : "Optional"} />
          <BlueprintField label="Availability" value={data.blueprint.requires_availability ? "Required" : "Optional"} />
          <BlueprintField label="Workflow version" value={data.blueprint.workflow_version != null ? `v${data.blueprint.workflow_version}` : "Not published"} />
        </div>
        <div style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 8 }}>
          Source: {data.blueprint.source === "service_job_workflow" ? "Job-Type blueprint" : "Master Service (legacy fields)"} — this cannot be edited here. Contact Admin for changes.
        </div>
      </Card>

      <Card title="Your offering">
        <FieldGroup label="Types"><ChipRow items={data.types.map(t => t.name)} empty="No types configured." /></FieldGroup>
        <FieldGroup label="Brands"><ChipRow items={data.brands.map(b => b.name)} empty="No brands configured." /></FieldGroup>
      </Card>

      <Card title="Readiness checklist">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <StatusBadge status={data.readiness.status} />
        </div>
        {data.readiness.blockers.length === 0 ? (
          <div style={{ fontSize: 12.5, color: "var(--success-text)" }}>No blocking issues.</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, color: "var(--danger-text)" }}>
            {data.readiness.blockers.map((b, i) => <li key={i}>{b.message}</li>)}
          </ul>
        )}
      </Card>
    </>
  );
}

type ServiceOptionDraft = {
  enabled: boolean;
  pricingModel: "FIXED" | "PER_UNIT" | "RANGE";
  amount: string;
  minimum: string;
  maximum: string;
};

function ServiceOptionsTab({ masterServiceId, jobTypeId }: { masterServiceId: string; jobTypeId: string }) {
  const available = useApi(
    () => masterServiceId && jobTypeId
      ? providerServiceOptionApi.getAvailableForService(masterServiceId, jobTypeId)
      : Promise.resolve([] as ProviderAvailableServiceOption[]),
    [masterServiceId, jobTypeId],
  );
  const supported = useApi(
    () => masterServiceId
      ? providerServiceOptionApi.getSupportedForService(masterServiceId)
      : Promise.resolve([] as ProviderSupportedServiceOption[]),
    [masterServiceId],
  );
  const [drafts, setDrafts] = useState<Record<string, ServiceOptionDraft>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!available.data || !supported.data) return;
    const configured = new Map(
      supported.data
        .filter(row => row.service_option_mapping_id)
        .map(row => [String(row.service_option_mapping_id), row]),
    );
    const next: Record<string, ServiceOptionDraft> = {};
    for (const option of available.data) {
      const row = configured.get(option.mapping_id);
      const pricingModel = row?.pricing_model ?? "FIXED";
      next[option.mapping_id] = {
        enabled: option.is_required || row?.status === "active",
        pricingModel,
        amount: pricingModel === "PER_UNIT" ? row?.unit_price ?? "" : row?.fixed_price ?? "",
        minimum: row?.minimum_price ?? "",
        maximum: row?.maximum_price ?? "",
      };
    }
    setDrafts(next);
  }, [available.data, supported.data]);

  function update(mappingId: string, patch: Partial<ServiceOptionDraft>) {
    setDrafts(current => ({
      ...current,
      [mappingId]: {
        enabled: false,
        pricingModel: "FIXED",
        amount: "",
        minimum: "",
        maximum: "",
        ...current[mappingId],
        ...patch,
      },
    }));
  }

  async function save() {
    if (!available.data) return;
    setSaving(true); setMessage(""); setError("");
    try {
      for (const option of available.data) {
        const draft = drafts[option.mapping_id] ?? {
          enabled: option.is_required, pricingModel: "FIXED" as const,
          amount: "", minimum: "", maximum: "",
        };
        const enabled = option.is_required || draft.enabled;
        if (!enabled) {
          await providerServiceOptionApi.setOptionPrice(option.mapping_id, { enabled: false });
          continue;
        }
        if (option.affects_estimate) {
          const missingSingle = draft.pricingModel !== "RANGE" && !draft.amount.trim();
          const invalidRange = draft.pricingModel === "RANGE"
            && (!draft.minimum.trim() || !draft.maximum.trim() || Number(draft.maximum) < Number(draft.minimum));
          if (missingSingle || invalidRange) {
            throw new Error(`Enter a valid tenant price for ${option.name}.`);
          }
        }
        await providerServiceOptionApi.setOptionPrice(option.mapping_id, {
          enabled: true,
          pricing_model: option.affects_estimate ? draft.pricingModel : undefined,
          ...(draft.pricingModel === "FIXED" ? { fixed_price: draft.amount } : {}),
          ...(draft.pricingModel === "PER_UNIT" ? { unit_price: draft.amount } : {}),
          ...(draft.pricingModel === "RANGE"
            ? { minimum_price: draft.minimum, maximum_price: draft.maximum }
            : {}),
        });
      }
      setMessage("Service options saved. Customer booking now uses this exact job-type configuration.");
      supported.refetch();
    } catch (value) {
      setError(value instanceof Error ? value.message : "Service options could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  if (available.loading || supported.loading) return <Card><Skeleton height={120} /></Card>;
  if (available.error || supported.error) return <Card><Alert tone="danger">{available.error ?? supported.error}</Alert></Card>;
  const options = available.data ?? [];
  return (
    <Card title="Customer-selectable service options">
      <p style={{ margin: "0 0 14px", color: "var(--text-secondary)", fontSize: 12.5, lineHeight: 1.55 }}>
        These options are created and mapped to this job type by Admin. Select what your business provides and set your own price where the option changes the estimate.
      </p>
      {error && <Alert tone="danger">{error}</Alert>}
      {message && <Alert tone="success">{message}</Alert>}
      {!options.length ? (
        <div style={{ color: "var(--text-tertiary)", fontSize: 12.5 }}>Admin has not mapped any tenant-selectable options to this job type.</div>
      ) : (
        <div style={{ display: "grid", gap: 10 }}>
          {options.map(option => {
            const draft = drafts[option.mapping_id] ?? { enabled: option.is_required, pricingModel: "FIXED" as const, amount: "", minimum: "", maximum: "" };
            const enabled = option.is_required || draft.enabled;
            return (
              <div key={option.mapping_id} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 9, fontSize: 13, fontWeight: 650 }}>
                  <input type="checkbox" checked={enabled} disabled={option.is_required || saving}
                    onChange={event => update(option.mapping_id, { enabled: event.target.checked })} />
                  <span style={{ flex: 1 }}>{option.name}</span>
                  {option.is_required && <StatusBadge status="required" size="sm" />}
                </label>
                {enabled && option.affects_estimate && (
                  <div style={{ display: "grid", gridTemplateColumns: "minmax(120px, .7fr) minmax(160px, 1fr)", gap: 8, marginTop: 10 }}>
                    <select aria-label={`Pricing model for ${option.name}`} value={draft.pricingModel}
                      onChange={event => update(option.mapping_id, { pricingModel: event.target.value as ServiceOptionDraft["pricingModel"] })}
                      style={{ border: "1px solid var(--border)", borderRadius: 7, background: "var(--surface)", color: "var(--text-primary)", padding: "8px 9px" }}>
                      <option value="FIXED">Fixed price</option><option value="PER_UNIT">Per unit</option><option value="RANGE">Price range</option>
                    </select>
                    {draft.pricingModel === "RANGE" ? (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                        <Input aria-label={`Minimum price for ${option.name}`} type="number" min={0} value={draft.minimum} onChange={event => update(option.mapping_id, { minimum: event.target.value })} placeholder="Minimum ₹" />
                        <Input aria-label={`Maximum price for ${option.name}`} type="number" min={0} value={draft.maximum} onChange={event => update(option.mapping_id, { maximum: event.target.value })} placeholder="Maximum ₹" />
                      </div>
                    ) : (
                      <Input aria-label={`Price for ${option.name}`} type="number" min={0} value={draft.amount} onChange={event => update(option.mapping_id, { amount: event.target.value })} placeholder={draft.pricingModel === "PER_UNIT" ? `₹ per ${option.measurement_unit ?? "unit"}` : "Price ₹"} />
                    )}
                  </div>
                )}
              </div>
            );
          })}
          <div><Button variant="primary" loading={saving} onClick={save}>Save service options</Button></div>
        </div>
      )}
    </Card>
  );
}

function TypesBrandsTab({ tenantServiceId, data, pricingMode, onChanged, eligibilityOnly = false }: {
  tenantServiceId: string; data: SWOfferingDetail; pricingMode: "inspection" | "consultation" | "dimension"; onChanged: () => void; eligibilityOnly?: boolean;
}) {
  const dimensionPricing = pricingMode === "dimension";
  const availableTypes = useApi(() => homeServicesSetupApi.getAvailableTypes(tenantServiceId), [tenantServiceId]);
  const availableBrands = useApi(() => homeServicesSetupApi.getAvailableBrands(tenantServiceId), [tenantServiceId]);
  const typePricing = useApi(
    () => dimensionPricing ? homeServicesSetupApi.getTypePricing(tenantServiceId) : Promise.resolve({ types: [] }),
    [tenantServiceId, dimensionPricing],
  );

  const refreshLocal = () => { availableTypes.refetch(); availableBrands.refetch(); typePricing.refetch(); onChanged(); };

  const { execute: saveTypes, loading: savingTypes, error: typesError } = useAction(
    (typeIds: string[]) => homeServicesSetupApi.setTypes(tenantServiceId, typeIds), { onSuccess: refreshLocal },
  );
  const { execute: saveBrands, loading: savingBrands, error: brandsError } = useAction(
    (brandIds: string[]) => homeServicesSetupApi.setBrands(tenantServiceId, brandIds), { onSuccess: refreshLocal },
  );
  const { execute: saveTypePrice, loading: savingTypePrice, error: typePriceError } = useAction(
    (args: { serviceTypeId: string; min: number; max: number }) =>
      homeServicesSetupApi.setTypePricing(tenantServiceId, args.serviceTypeId, args.min, args.max),
    { onSuccess: refreshLocal },
  );
  function toggleType(t: HsSetupAvailableType) {
    const current = (availableTypes.data?.types ?? []).filter(x => x.is_enabled).map(x => x.service_type_id);
    const next = t.is_enabled ? current.filter(id => id !== t.service_type_id) : [...current, t.service_type_id];
    saveTypes(next);
  }
  function toggleBrand(b: HsSetupBrand) {
    const current = (availableBrands.data?.brands ?? []).filter(x => x.is_enabled).map(x => x.brand_id);
    const next = b.is_enabled ? current.filter(id => id !== b.brand_id) : [...current, b.brand_id];
    saveBrands(next);
  }

  if (!data.blueprint) return null;

  return (
    <>
      {(typesError || brandsError || typePriceError) && <Alert tone="danger">{typesError ?? brandsError ?? typePriceError}</Alert>}

      {data.tenant_service.requires_type ? (
        <Card title="Supported types">
          {availableTypes.loading || typePricing.loading ? <Skeleton height={80} /> : availableTypes.error || typePricing.error ? (
            <Alert tone="danger">{availableTypes.error ?? typePricing.error}</Alert>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(availableTypes.data?.types ?? []).map(t => (
                <div key={t.service_type_id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <input type="checkbox" checked={t.is_enabled} disabled={savingTypes} onChange={() => toggleType(t)} />
                  <div style={{ flex: 1, fontSize: 13 }}>{t.name}</div>
                  {t.is_enabled && dimensionPricing && !eligibilityOnly && (
                    <TypePriceRow serviceTypeId={t.service_type_id}
                      current={typePricing.data?.types?.find(x => x.service_type_id === t.service_type_id)}
                      onSave={(min, max) => saveTypePrice({ serviceTypeId: t.service_type_id, min, max })}
                      saving={savingTypePrice} />
                  )}
                  {t.is_enabled && !dimensionPricing && (
                    <span style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>
                      Routing only · {pricingMode === "inspection" ? "uses visit fee and approved estimate" : "uses the provider-wide consultation fee"}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : (
        <Card><div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>This service doesn&apos;t require a Type selection.</div></Card>
      )}

      {data.tenant_service.requires_brand ? (
        <Card title="Supported brands">
          {availableBrands.loading ? <Skeleton height={80} /> : availableBrands.error ? (
            <Alert tone="danger">{availableBrands.error}</Alert>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(availableBrands.data?.brands ?? []).map(b => (
                <div key={b.brand_id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <input type="checkbox" checked={b.is_enabled} disabled={savingBrands} onChange={() => toggleBrand(b)} />
                  <div style={{ flex: 1, fontSize: 13 }}>{b.name}</div>
                </div>
              ))}
            </div>
          )}
          {dimensionPricing && !eligibilityOnly && (availableBrands.data?.brands ?? []).some(brand => brand.is_enabled) && (
            <div style={{ borderTop: "1px solid var(--border)", marginTop: 14, paddingTop: 14 }}>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>Brand price overrides</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 10 }}>
                Optional. Brands inherit the type or default price until you save a more specific amount.
              </div>
              {data.tenant_service.requires_type ? (
                (availableTypes.data?.types ?? []).filter(type => type.is_enabled).map(type => (
                  <BrandPricingRows key={type.service_type_id} tenantServiceId={tenantServiceId}
                    serviceTypeId={type.service_type_id} typeName={type.name}
                    brands={(availableBrands.data?.brands ?? []).filter(brand => brand.is_enabled)} onChanged={refreshLocal} />
                ))
              ) : (
                <BrandPricingRows tenantServiceId={tenantServiceId} typeName="Service default"
                  brands={(availableBrands.data?.brands ?? []).filter(brand => brand.is_enabled)} onChanged={refreshLocal} />
              )}
            </div>
          )}
        </Card>
      ) : (
        <Card><div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>This service doesn&apos;t require a Brand selection.</div></Card>
      )}
      {!dimensionPricing && (
        <Alert tone="info">
          Types and brands control customer selection, technician matching and job routing for this {pricingMode === "inspection" ? "inspection workflow" : "consultation"}.
          They do not create separate prices: {pricingMode === "inspection" ? "the customer pays the visit fee first and receives an estimate after inspection." : "the single provider-wide consultation fee applies."}
        </Alert>
      )}
    </>
  );
}

function BrandPricingRows({ tenantServiceId, serviceTypeId, typeName, brands, onChanged }: {
  tenantServiceId: string; serviceTypeId?: string; typeName: string; brands: HsSetupBrand[]; onChanged: () => void;
}) {
  const pricing = useApi(
    () => homeServicesSetupApi.getBrandPricing(tenantServiceId, serviceTypeId),
    [tenantServiceId, serviceTypeId],
  );
  const { execute: save, loading, error } = useAction(
    (args: { brandId: string; min: number; max: number }) =>
      homeServicesSetupApi.setBrandPricing(tenantServiceId, args.brandId, args.min, args.max, serviceTypeId),
    { onSuccess: () => { pricing.refetch(); onChanged(); } },
  );

  return (
    <div style={{ padding: "10px 0", borderTop: "1px solid var(--border)" }}>
      <div style={{ fontSize: 11.5, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 8 }}>{typeName}</div>
      {error && <Alert tone="danger">{error}</Alert>}
      {pricing.loading ? <Skeleton height={54} /> : brands.map(brand => (
        <div key={brand.brand_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0" }}>
          <div style={{ flex: 1, minWidth: 100, fontSize: 12 }}>{brand.name}</div>
          {brand.can_override_price === false ? (
            <span style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>Admin locked</span>
          ) : (
            <TypePriceRow serviceTypeId={brand.brand_id}
              current={pricing.data?.brands?.find(row => row.brand_id === brand.brand_id)}
              onSave={(min, max) => save({ brandId: brand.brand_id, min, max })} saving={loading} />
          )}
        </div>
      ))}
    </div>
  );
}

function TypePriceRow({ current, onSave, saving }: {
  serviceTypeId: string; current?: { tenant_min_price: number | null; tenant_max_price: number | null }; onSave: (min: number, max: number) => void; saving: boolean;
}) {
  const [min, setMin] = useState(current?.tenant_min_price != null ? String(current.tenant_min_price) : "");
  const [max, setMax] = useState(current?.tenant_max_price != null ? String(current.tenant_max_price) : "");
  useEffect(() => {
    setMin(current?.tenant_min_price != null ? String(current.tenant_min_price) : "");
    setMax(current?.tenant_max_price != null ? String(current.tenant_max_price) : "");
  }, [current?.tenant_min_price, current?.tenant_max_price]);
  const minValue = Number(min);
  const maxValue = Number(max);
  const invalid = !min || !max || !Number.isFinite(minValue) || !Number.isFinite(maxValue) || minValue <= 0 || maxValue < minValue;
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      <input aria-label="Minimum price" value={min} onChange={e => setMin(e.target.value)} placeholder="Min" type="number" min={0}
        style={{ width: 70, padding: "5px 6px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 12 }} />
      <span style={{ color: "var(--text-tertiary)" }}>–</span>
      <input aria-label="Maximum price" value={max} onChange={e => setMax(e.target.value)} placeholder="Max" type="number" min={0}
        style={{ width: 70, padding: "5px 6px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 12 }} />
      <button type="button" aria-label="Save price range" title={maxValue < minValue ? "Maximum price must be at least the minimum price" : "Save price range"}
        disabled={saving || invalid} onClick={() => onSave(minValue, maxValue)}
        style={{ background: "none", border: "1px solid var(--brand)", borderRadius: 6, padding: "4px 6px", cursor: invalid ? "not-allowed" : "pointer", color: "var(--brand)", opacity: invalid ? 0.45 : 1 }}>
        <Save size={12} />
      </button>
    </div>
  );
}

function DefaultPricingTab({ tenantServiceId, data, onChanged }: {
  tenantServiceId: string; data: SWOfferingDetail; onChanged: () => void;
}) {
  const ts = data.tenant_service as { tenant_min_price: number | null; tenant_max_price: number | null; override_allowed: boolean };
  const [min, setMin] = useState(ts.tenant_min_price != null ? String(ts.tenant_min_price) : "");
  const [max, setMax] = useState(ts.tenant_max_price != null ? String(ts.tenant_max_price) : "");
  useEffect(() => {
    setMin(ts.tenant_min_price != null ? String(ts.tenant_min_price) : "");
    setMax(ts.tenant_max_price != null ? String(ts.tenant_max_price) : "");
  }, [ts.tenant_min_price, ts.tenant_max_price]);
  const minValue = Number(min);
  const maxValue = Number(max);
  const invalid = !min || !max || !Number.isFinite(minValue) || !Number.isFinite(maxValue) || minValue <= 0 || maxValue < minValue;

  const { execute: save, loading, error } = useAction(
    () => homeServicesSetupApi.updateEnabledService(tenantServiceId, {
      tenant_min_price: minValue, tenant_max_price: maxValue,
    }),
    { onSuccess: onChanged },
  );

  if (!ts.override_allowed) {
    return <Card><Alert tone="info">Price override is not permitted for this service by the Admin blueprint.</Alert></Card>;
  }

  return (
    <Card title="Default pricing">
      {error && <Alert tone="danger">{error}</Alert>}
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
        <Input label="Minimum price (₹)" type="number" value={min} onChange={e => setMin(e.target.value)} />
        <Input label="Maximum price (₹)" type="number" value={max} onChange={e => setMax(e.target.value)} />
        <Button variant="primary" size="sm" loading={loading} disabled={invalid}
          onClick={() => save()}>Save</Button>
      </div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>
        {max && min && maxValue < minValue ? "Maximum price must be at least the minimum price." : "Used when no Type/Brand override resolves a more specific price."}
      </div>
    </Card>
  );
}

function VisitFeeTab({ tenantServiceId, data, onChanged }: {
  tenantServiceId: string; data: SWOfferingDetail; onChanged: () => void;
}) {
  const ts = data.tenant_service as { tenant_visit_fee: number | null; tenant_emergency_surcharge: number | null };
  const [fee, setFee] = useState(ts.tenant_visit_fee != null ? String(ts.tenant_visit_fee) : "");
  const [surcharge, setSurcharge] = useState(ts.tenant_emergency_surcharge != null ? String(ts.tenant_emergency_surcharge) : "");
  useEffect(() => {
    setFee(ts.tenant_visit_fee != null ? String(ts.tenant_visit_fee) : "");
    setSurcharge(ts.tenant_emergency_surcharge != null ? String(ts.tenant_emergency_surcharge) : "");
  }, [ts.tenant_visit_fee, ts.tenant_emergency_surcharge]);
  const invalid = !fee || !Number.isFinite(Number(fee)) || Number(fee) <= 0
    || (!!surcharge && (!Number.isFinite(Number(surcharge)) || Number(surcharge) < 0));

  const { execute: save, loading, error } = useAction(
    () => homeServicesSetupApi.updateEnabledService(tenantServiceId, {
      tenant_visit_fee: fee ? Number(fee) : undefined,
      tenant_emergency_surcharge: surcharge ? Number(surcharge) : undefined,
    }),
    { onSuccess: onChanged },
  );

  return (
    <Card title="Visit fee & emergency surcharge">
      {error && <Alert tone="danger">{error}</Alert>}
      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 10 }}>
        For inspection-based jobs: a technician inspects first, then an estimate is created. If the customer declines,
        the visit fee remains payable; if they continue, it is adjusted into the final price.
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
        <Input label="Visit fee (₹)" type="number" value={fee} onChange={e => setFee(e.target.value)} />
        <Input label="Emergency surcharge (₹)" type="number" value={surcharge} onChange={e => setSurcharge(e.target.value)} />
        <Button variant="primary" size="sm" loading={loading} disabled={invalid} onClick={() => save()}>Save</Button>
      </div>
    </Card>
  );
}

function WarrantyTab({ tenantServiceId, data, onChanged }: {
  tenantServiceId: string; data: SWOfferingDetail; onChanged: () => void;
}) {
  const ts = data.tenant_service as { warranty_days?: number };
  const [days, setDays] = useState(String(ts.warranty_days ?? 5));
  useEffect(() => setDays(String(ts.warranty_days ?? 5)), [ts.warranty_days]);
  const { execute: save, loading, error } = useAction(
    () => homeServicesSetupApi.updateEnabledService(tenantServiceId, { warranty_days: Number(days) }),
    { onSuccess: onChanged },
  );
  const invalid = !Number.isInteger(Number(days)) || Number(days) < 5;

  return (
    <Card title="Service warranty">
      {error && <Alert tone="danger">{error}</Alert>}
      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 12 }}>
        This warranty is owned by your business and is captured on every completed job. You can extend it at any time;
        completed jobs keep the warranty that applied when the work finished.
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
        <Input label="Warranty period (days)" type="number" min={5} value={days} onChange={e => setDays(e.target.value)} />
        <Button variant="primary" size="sm" loading={loading} disabled={invalid} onClick={() => save()}>Save warranty</Button>
      </div>
      <div style={{ fontSize: 11, color: invalid ? "var(--danger-text)" : "var(--text-tertiary)", marginTop: 8 }}>
        Platform minimum: 5 days. Shorter warranties are rejected by both the API and database.
      </div>
    </Card>
  );
}

function PublicationCard({ tenantServiceId, data, hasDraftChanges, beforeSave, onChanged }: {
  tenantServiceId: string;
  data: SWOfferingDetail;
  hasDraftChanges: boolean;
  beforeSave: () => Promise<void>;
  onChanged: () => void;
}) {
  const router = useRouter();
  const ts = data.tenant_service as { setup_status: string; master_service_id?: string; job_type_id?: string };
  const { execute: saveDraft, loading: savingDraft, error: draftError } = useAction(
    async () => {
      await beforeSave();
      return homeServicesSetupApi.saveDraft(tenantServiceId);
    }, { onSuccess: onChanged },
  );
  const { execute: publish, loading: publishing, error: publishError } = useAction(
    async () => {
      await beforeSave();
      const published = await homeServicesSetupApi.publish(tenantServiceId);
      await providerStatusApi.refresh();
      return published;
    }, { onSuccess: onChanged },
  );
  const { execute: remove, loading: removing, error: removeError } = useAction(
    () => homeServicesSetupApi.disable(ts.master_service_id ?? "", ts.job_type_id ?? ""),
    { onSuccess: () => { onChanged(); router.push("/home-services/services"); } },
  );

  function confirmRemove() {
    if (!ts.master_service_id || !ts.job_type_id) return;
    if (window.confirm(`Remove ${data.service_name} (${data.job_type_label ?? "service"}) from your active catalog? Existing jobs are not deleted.`)) {
      remove();
    }
  }

  return (
    <div className="pricing-publish-bar">
      <div className="pricing-publish-copy">
        <strong>{hasDraftChanges ? "Unsaved changes" : data.readiness.ready ? (ts.setup_status === "published" ? "Live and bookable" : "Ready to publish") : "Needs attention before publishing"}</strong>
        <span>{hasDraftChanges ? "Nothing has been sent yet. Save a draft or publish when you are ready." : data.readiness.ready ? "Customers will see the saved price for this offering." : "Resolve the setup blockers to make this offering bookable."}</span>
        {(draftError || publishError || removeError) && <span style={{ color: "var(--danger-text)" }}>{draftError ?? publishError ?? removeError}</span>}
      </div>
      <div className="pricing-publish-actions">
        <Button variant="secondary" size="sm" loading={savingDraft} onClick={() => saveDraft()}>Save draft</Button>
        <Button variant="primary" size="sm" loading={publishing}
          onClick={() => publish()}>{ts.setup_status === "published" ? "Update live price" : "Publish"}</Button>
        <Button variant="destructive" size="sm" leftIcon={<Trash2 size={13} />} loading={removing}
          disabled={!ts.master_service_id || !ts.job_type_id} onClick={confirmRemove}>
          Remove offering
        </Button>
      </div>
    </div>
  );
}

function ConsultationFeeCard() {
  const policy = useApi(() => homeServicesSetupApi.getPricingPolicy(), []);
  const [fee, setFee] = useState("");
  useEffect(() => {
    if (policy.data?.consultation_fee != null) setFee(String(policy.data.consultation_fee));
  }, [policy.data?.consultation_fee]);
  const parsedFee = Number(fee);
  const invalid = !Number.isFinite(parsedFee) || parsedFee <= 0;
  const { execute: save, loading, error } = useAction(
    () => homeServicesSetupApi.updatePricingPolicy({ consultation_fee: parsedFee }),
    { onSuccess: policy.refetch },
  );

  return (
    <Card title="Provider-wide consultation fee">
      <p style={{ margin: "0 0 10px", fontSize: 11.5, lineHeight: 1.5, color: "var(--text-tertiary)" }}>
        Shared by every Home Services consultation. Repair and installation prices remain specific to each offering.
      </p>
      {policy.loading ? <Skeleton height={60} /> : policy.error ? (
        <Alert tone="danger">{policy.error}</Alert>
      ) : (
        <>
          {error && <Alert tone="danger">{error}</Alert>}
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <Input label="Consultation fee (₹)" type="number" min={1} value={fee} onChange={event => setFee(event.target.value)} />
            <Button variant="secondary" size="sm" loading={loading} disabled={invalid} onClick={() => save()}>Save</Button>
          </div>
        </>
      )}
    </Card>
  );
}

function EffectivePricingPanel({ data, pricingMode }: { data: SWOfferingDetail; pricingMode: "inspection" | "consultation" | "dimension" }) {
  const ts = data.tenant_service as { tenant_visit_fee?: number | null; tenant_emergency_surcharge?: number | null };

  if (pricingMode === "consultation") {
    return (
      <Card title="Consultation pricing">
        <div style={{ fontSize: 12, lineHeight: 1.55, color: "var(--text-secondary)" }}>
          This offering uses the single provider-wide Home Services consultation fee. Type and brand choices affect matching only.
        </div>
      </Card>
    );
  }

  if (pricingMode === "inspection") {
    return (
      <Card title="Repair price journey">
        <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 12 }}>
          The admin blueprint requires inspection before a final repair amount can exist.
        </div>
        <div style={{ display: "grid", gap: 9 }}>
          <JourneyStep number="1" title="Book inspection" detail={ts.tenant_visit_fee != null ? `₹${ts.tenant_visit_fee} visit fee` : "Visit fee needs configuration"} ready={ts.tenant_visit_fee != null} />
          <JourneyStep number="2" title="Technician diagnoses" detail="Customer issue, checklist and evidence are captured on the job." ready />
          <JourneyStep number="3" title="Customer approves estimate" detail="The final repair price is created only after inspection." ready />
        </div>
        {ts.tenant_emergency_surcharge != null && ts.tenant_emergency_surcharge > 0 && (
          <div style={{ marginTop: 12, padding: "8px 10px", borderRadius: 8, background: "var(--surface-sunken)", fontSize: 11.5, color: "var(--text-secondary)" }}>
            Emergency booking surcharge: <strong>₹{ts.tenant_emergency_surcharge}</strong>
          </div>
        )}
        <div style={{ marginTop: 12, padding: "8px 10px", borderRadius: 8, background: "var(--surface-sunken)", fontSize: 11, color: "var(--text-tertiary)" }}>
          Types and brands are routing dimensions, not price overrides, for this workflow.
        </div>
      </Card>
    );
  }

  return (
    <Card title="Effective pricing">
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 10 }}>
        How prices are determined for this service
      </div>
      <PriceRow label="Job Type default" price={data.effective_pricing.default} />
      {data.effective_pricing.by_type.map(t => (
        <div key={t.service_type_id} style={{ marginTop: 10 }}>
          <PriceRow label={`Type: ${t.name}`} price={t} />
          {t.brand_overrides.map(b => (
            <div key={b.brand_id} style={{ marginLeft: 14 }}>
              <PriceRow label="Brand override" price={b} small />
            </div>
          ))}
        </div>
      ))}
      <div style={{ marginTop: 12, padding: "8px 10px", borderRadius: 8, background: "var(--surface-sunken)",
        fontSize: 11, color: "var(--text-tertiary)" }}>
        Tenant owns all price amounts. Admin stores no service price.
      </div>
    </Card>
  );
}

function JourneyStep({ number, title, detail, ready }: { number: string; title: string; detail: string; ready: boolean }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "28px minmax(0, 1fr)", gap: 9, alignItems: "start" }}>
      <div style={{ width: 26, height: 26, borderRadius: 8, display: "grid", placeItems: "center", fontSize: 11, fontWeight: 750,
        border: `1px solid ${ready ? "var(--success)" : "var(--warning)"}`, color: ready ? "var(--success-text)" : "var(--warning-text)", background: "var(--surface-sunken)" }}>{number}</div>
      <div>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{title}</div>
        <div style={{ fontSize: 10.5, lineHeight: 1.45, color: "var(--text-tertiary)", marginTop: 2 }}>{detail}</div>
      </div>
    </div>
  );
}

function PriceRow({ label, price, small }: { label: string; price: SWResolvedPrice; small?: boolean }) {
  return (
    <div style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ fontSize: small ? 11 : 12, color: "var(--text-tertiary)" }}>{label}</div>
      {price.resolved ? (
        <div style={{ fontSize: small ? 12 : 14, fontWeight: 700, color: "var(--text-primary)" }}>
          {price.minimum_price === price.maximum_price
            ? `₹${price.minimum_price}`
            : `₹${price.minimum_price} – ₹${price.maximum_price}`}
          <span style={{ fontSize: 10, fontWeight: 400, color: "var(--text-tertiary)", marginLeft: 6 }}>
            ({price.source})
          </span>
        </div>
      ) : (
        <div style={{ fontSize: 12, color: "var(--warning-text)" }}>Not priced yet</div>
      )}
    </div>
  );
}

function BlueprintField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{label}</div>
      <div style={{ color: "var(--text-primary)", fontWeight: 600, textTransform: "capitalize" }}>{value}</div>
    </div>
  );
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  );
}

function ChipRow({ items, empty }: { items: string[]; empty: string }) {
  if (items.length === 0) return <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{empty}</div>;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {items.map(i => (
        <span key={i} style={{ fontSize: 12, padding: "3px 9px", borderRadius: 999,
          background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>{i}</span>
      ))}
    </div>
  );
}
