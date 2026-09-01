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
 * /v1/tenant/catalog/enabled-services/...) -- no new backend mutation
 * surface was invented for this workspace.
 *
 * Add Services and the customer catalog preview are intentionally backed by
 * the same list/enable endpoints as onboarding. Unsupported bulk-import and
 * publication-history controls are not rendered as dead actions.
 *
 * Tenant offerings are scoped per (Master Service, Job Type), so Repair and
 * Installation keep independent setup, publication, and operational data.
 */
import React, { Suspense, useEffect, useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  Eye, Plus, Wrench, CheckCircle2, FileEdit, AlertTriangle, Settings2, Tag, Save,
  Search, ArrowRight, RefreshCw, Trash2,
} from "lucide-react";
import {
  PageShell, PageHeader, Card, StatCard, StatusBadge, Skeleton, Alert, Button, Input, Modal,
} from "@serviceos/design-system";
import {
  servicesWorkspaceApi, homeServicesSetupApi, providerStatusApi,
  type SWCatalogService, type SWCatalogGroup, type SWResolvedPrice, type SWOfferingDetail,
  type AdminMasterServiceRow, type TenantEnabledService,
  type HsSetupAvailableType, type HsSetupBrand,
} from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { ServiceRequirementsPanel } from "../../../../../components/services/ServiceRequirementsPanel";

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

  const allServices = (workspace.data?.catalog_tree ?? []).flatMap(g => g.services);
  const visibleGroups = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return (workspace.data?.catalog_tree ?? [])
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
  }, [workspace.data, query, statusFilter, groupFilter]);
  const visibleServices = visibleGroups.flatMap(group => group.services);
  const selectedExists = !!selectedId && allServices.some(service => service.tenant_service_id === selectedId);
  const selectedVisible = !!selectedId && visibleServices.some(service => service.tenant_service_id === selectedId);
  const filtersActive = !!query.trim() || statusFilter !== "all" || groupFilter !== "all";
  const effectiveId = selectedExists && (!filtersActive || selectedVisible)
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
        <PageHeader
          eyebrow="Business"
          context="Service catalog"
          title="Services & Pricing"
          description="Choose what you provide and configure your own pricing within Admin-approved service blueprints."
          actions={
            <>
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
            </>
          }
        />

        {workspace.error && <Alert tone="danger">{workspace.error}</Alert>}

        <style>{`
          .services-workspace-grid { display: grid; grid-template-columns: minmax(250px, 300px) minmax(0, 1fr); gap: 16px; align-items: start; }
          .services-offering-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(270px, 320px); gap: 16px; align-items: start; }
          .services-filter-grid { display: grid; grid-template-columns: minmax(0, 1fr) 120px; gap: 8px; }
          @media (max-width: 1180px) { .services-offering-grid { grid-template-columns: 1fr; } }
          @media (max-width: 820px) {
            .services-workspace-grid { grid-template-columns: 1fr; }
            .services-catalog-rail { max-height: none !important; position: static !important; }
          }
          @media (max-width: 560px) { .services-filter-grid { grid-template-columns: 1fr; } }
        `}</style>

        {workspace.error && !workspace.data ? (
          <Card>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>The service summary could not be loaded.</span>
              <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={13} />} onClick={workspace.refetch}>Retry</Button>
            </div>
          </Card>
        ) : workspace.loading || !workspace.data ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={80} />)}
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
            <StatCard icon={CheckCircle2} label="Enabled services" value={workspace.data.summary.enabled_services} tone="brand" />
            <StatCard icon={CheckCircle2} label="Published" value={workspace.data.summary.published} tone="success" />
            <StatCard icon={FileEdit} label="Draft" value={workspace.data.summary.draft} tone="warning" />
            <StatCard icon={AlertTriangle} label="Missing pricing" value={workspace.data.summary.missing_pricing} tone="danger" />
            <StatCard icon={Settings2} label="Type overrides" value={workspace.data.summary.type_overrides} tone="info" />
            <StatCard icon={Tag} label="Brand overrides" value={workspace.data.summary.brand_overrides} tone="info" />
          </div>
        )}

        <div className="services-workspace-grid">
          <Card padding="sm" className="services-catalog-rail" style={{ maxHeight: "calc(100vh - 190px)", overflowY: "auto", position: "sticky", top: 84 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, padding: "4px 8px 10px" }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 750, color: "var(--text-primary)" }}>Service catalog</div>
                <div style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 2 }}>{visibleServices.length} of {allServices.length} offerings</div>
              </div>
              {filtersActive && (
                <button type="button" onClick={clearFilters} aria-label="Clear catalog filters" title="Clear filters"
                  style={{ border: "none", background: "transparent", color: "var(--brand)", cursor: "pointer", padding: 4 }}>
                  <RefreshCw size={14} />
                </button>
              )}
            </div>
            <div className="services-filter-grid" style={{ margin: "0 6px 8px" }}>
              <label style={{ position: "relative" }}>
                <Search size={14} aria-hidden style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }} />
                <input aria-label="Search services" value={query} onChange={event => updateQuery({ q: event.target.value || null })} placeholder="Search services"
                  style={{ width: "100%", height: 34, padding: "0 10px 0 31px", boxSizing: "border-box", border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 12 }} />
              </label>
              <select aria-label="Filter by service group" value={groupFilter} onChange={event => updateQuery({ group: event.target.value as string })}
                style={{ height: 34, minWidth: 0, border: "1px solid var(--border)", borderRadius: 8, padding: "0 8px", background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 12 }}>
                <option value="all">All groups</option>
                {(workspace.data?.catalog_tree ?? []).map(group => <option key={group.service_group_id} value={group.service_group_id}>{group.name}</option>)}
              </select>
            </div>
            <div role="group" aria-label="Filter by setup status" style={{ display: "flex", gap: 5, flexWrap: "wrap", padding: "0 6px 10px" }}>
              {CATALOG_STATUS_FILTERS.map(option => (
                <button type="button" key={option.value} aria-pressed={statusFilter === option.value} onClick={() => updateQuery({ status: option.value })}
                  style={{ border: `1px solid ${statusFilter === option.value ? "var(--brand)" : "var(--border)"}`, borderRadius: 999, padding: "4px 8px", background: statusFilter === option.value ? "var(--accent-muted)" : "transparent", color: statusFilter === option.value ? "var(--brand)" : "var(--text-secondary)", cursor: "pointer", fontSize: 10.5, fontWeight: 650 }}>
                  {option.label}
                </button>
              ))}
            </div>
            {workspace.loading ? (
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
                <div key={group.service_group_id} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", padding: "4px 8px" }}>
                    {group.name.toUpperCase()}
                  </div>
                  {group.services.map(s => (
                    <CatalogRow key={s.tenant_service_id} s={s} selected={s.tenant_service_id === effectiveId}
                      onClick={() => openService(s.tenant_service_id)} />
                  ))}
                </div>
              ))
            )}
          </Card>

          {effectiveId ? (
            <OfferingWorkspace key={effectiveId} tenantServiceId={effectiveId} onWorkspaceChanged={workspace.refetch} />
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
          groups={workspace.data?.catalog_tree ?? []}
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
      </PageShell>
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
  return (
    <button type="button" onClick={onClick} aria-current={selected ? "page" : undefined}
      style={{
        display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "8px 8px", borderRadius: 8, cursor: "pointer", textAlign: "left", fontFamily: "inherit",
        background: selected ? "var(--accent-muted)" : "transparent",
        border: selected ? "1px solid var(--brand)" : "1px solid transparent",
      }}>
      <Wrench size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{s.name}</div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{s.job_type_label ?? "—"}</div>
      </div>
      <StatusBadge status={!s.readiness_ready ? "needs_attention" : s.setup_status} size="sm" />
    </button>
  );
}

const TABS = ["overview", "types-brands", "pricing", "visit-fee", "warranty", "requirements"] as const;
type Tab = typeof TABS[number];
const TAB_LABEL: Record<Tab, string> = {
  overview: "Overview", "types-brands": "Types & Brands", pricing: "Pricing",
  "visit-fee": "Visit & estimate", warranty: "Warranty", requirements: "Booking & job requirements",
};

/** Two-column detail+effective-pricing area, driven by one shared refetch so an
 * edit anywhere (pricing/types/brands/publish) reloads both real projections. */
function OfferingWorkspace({ tenantServiceId, onWorkspaceChanged }: { tenantServiceId: string; onWorkspaceChanged: () => void }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const detail = useApi(() => servicesWorkspaceApi.detail(tenantServiceId), [tenantServiceId]);

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
  const ts = data.tenant_service as { setup_status: string; requires_type: boolean; requires_brand: boolean; master_service_id?: string; job_type?: string };
  const inspectionPricing = isInspectionPricing(data.blueprint.pricing_behavior);
  const consultationPricing = String(ts.job_type ?? "").toLowerCase() === "consultation";
  const pricingMode: "inspection" | "consultation" | "dimension" = inspectionPricing
    ? "inspection"
    : consultationPricing ? "consultation" : "dimension";
  const availableTabs: Tab[] = pricingMode === "inspection"
    ? ["overview", "types-brands", "visit-fee", "warranty", "requirements"]
    : pricingMode === "consultation"
      ? ["overview", "types-brands", "warranty", "requirements"]
      : ["overview", "types-brands", "pricing", "warranty", "requirements"];
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
    <div className="services-offering-grid">
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <Wrench size={18} style={{ color: "var(--brand)" }} />
            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)", flex: 1 }}>{data.service_name}</div>
            {data.job_type_label && <StatusBadge status={data.job_type_label} size="sm" />}
            <StatusBadge status={ts.setup_status} size="sm" />
          </div>
          <div role="tablist" aria-label="Service configuration" style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", overflowX: "auto" }}>
            {availableTabs.map(t => (
              <button type="button" role="tab" aria-selected={tab === t} aria-controls={`service-tab-${t}`} key={t} onClick={() => setTab(t)} style={{
                padding: "8px 12px", background: "none", border: "none", cursor: "pointer",
                fontSize: 12.5, fontWeight: 600, whiteSpace: "nowrap",
                color: tab === t ? "var(--brand)" : "var(--text-tertiary)",
                borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
              }}>{TAB_LABEL[t]}</button>
            ))}
          </div>
        </Card>

        <div id={`service-tab-${tab}`} role="tabpanel">
        {tab === "overview" && <OverviewTab data={data} />}
        {tab === "types-brands" && (
          <TypesBrandsTab tenantServiceId={tenantServiceId} data={data} pricingMode={pricingMode} onChanged={refreshAll} />
        )}
        {tab === "pricing" && (
          <DefaultPricingTab tenantServiceId={tenantServiceId} data={data} onChanged={refreshAll} />
        )}
        {tab === "visit-fee" && (
          <VisitFeeTab tenantServiceId={tenantServiceId} data={data} onChanged={refreshAll} />
        )}
        {tab === "warranty" && (
          <WarrantyTab tenantServiceId={tenantServiceId} data={data} onChanged={refreshAll} />
        )}
        {/* Replaced a "not built yet" Activity placeholder with a real,
            read-only view of the admin-authored Problems / Questions /
            Checklists for this service -- previously invisible to tenants
            even though they drive customer booking and technician work. */}
        {tab === "requirements" && (
          <Card title="Configured by the platform (read-only)">
            <ServiceRequirementsPanel
              masterServiceId={String((ts as unknown as { master_service_id?: string }).master_service_id ?? "")}
              jobTypeId={String((ts as unknown as { job_type_id?: string }).job_type_id ?? "")}
            />
          </Card>
        )}
        </div>

        <PublicationCard tenantServiceId={tenantServiceId} data={data} onChanged={refreshAll} />
      </div>

      <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <EffectivePricingPanel data={data} pricingMode={pricingMode} />
        <ConsultationFeeCard />
      </aside>
    </div>
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

function TypesBrandsTab({ tenantServiceId, data, pricingMode, onChanged }: {
  tenantServiceId: string; data: SWOfferingDetail; pricingMode: "inspection" | "consultation" | "dimension"; onChanged: () => void;
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
                  {t.is_enabled && dimensionPricing && (
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
          {dimensionPricing && (availableBrands.data?.brands ?? []).some(brand => brand.is_enabled) && (
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

function PublicationCard({ tenantServiceId, data, onChanged }: {
  tenantServiceId: string; data: SWOfferingDetail; onChanged: () => void;
}) {
  const router = useRouter();
  const ts = data.tenant_service as { setup_status: string; master_service_id?: string; job_type_id?: string };
  const { execute: saveDraft, loading: savingDraft, error: draftError } = useAction(
    () => homeServicesSetupApi.saveDraft(tenantServiceId), { onSuccess: onChanged },
  );
  const { execute: publish, loading: publishing, error: publishError } = useAction(
    async () => {
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
    <Card title="Version & publication">
      {(draftError || publishError || removeError) && <Alert tone="danger">{draftError ?? publishError ?? removeError}</Alert>}
      <div style={{ fontSize: 12.5, marginBottom: 10 }}>
        Current status: <StatusBadge status={ts.setup_status} size="sm" />
      </div>
      {!data.readiness.ready && (
        <div style={{ fontSize: 11.5, color: "var(--warning-text)", marginBottom: 10 }}>
          Resolve the readiness blockers above before publishing.
        </div>
      )}
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <Button variant="secondary" size="sm" loading={savingDraft} onClick={() => saveDraft()}>Save draft</Button>
        <Button variant="primary" size="sm" loading={publishing} disabled={!data.readiness.ready}
          onClick={() => publish()}>Publish</Button>
        <Button variant="destructive" size="sm" leftIcon={<Trash2 size={13} />} loading={removing}
          disabled={!ts.master_service_id || !ts.job_type_id} onClick={confirmRemove} style={{ marginLeft: "auto" }}>
          Remove offering
        </Button>
      </div>
    </Card>
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
