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
 * NOT built this pass: Add Services wizard (enabling a brand-new master
 * service), import pricing, customer preview, publish version/snapshot
 * history UI. Those are reported as open gaps, not faked.
 *
 * Known gap (see backend module docstring): TenantService is scoped per
 * Master Service, not per (Master Service, Job Type) -- this workspace
 * reflects that live limitation rather than inventing UI for a hierarchy
 * the schema can't yet support for every tenant.
 */
import React, { Suspense, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Eye, Upload, Plus, Wrench, CheckCircle2, FileEdit, AlertTriangle, Settings2, Tag, Save,
} from "lucide-react";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import {
  PageShell, PageHeader, Card, StatCard, StatusBadge, Skeleton, Alert, Button, Input,
} from "@serviceos/design-system";
import {
  servicesWorkspaceApi, homeServicesSetupApi,
  type SWCatalogService, type SWResolvedPrice, type SWOfferingDetail,
  type HsSetupAvailableType, type HsSetupBrand,
} from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";

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
  const idParts = params.serviceId as string[] | undefined;
  const selectedId = idParts?.[0] ?? null;

  const workspace = useApi(() => servicesWorkspaceApi.get(), []);

  const allServices = (workspace.data?.catalog_tree ?? []).flatMap(g => g.services);
  const effectiveId = selectedId ?? allServices[0]?.tenant_service_id ?? null;

  return (
    <TenantLayout activeNav="provider-services">
      <PageShell>
        <PageHeader
          title="Services & Pricing"
          description="Choose what you provide and configure your own pricing within Admin-approved service blueprints."
          actions={
            <>
              <Button variant="secondary" size="sm" leftIcon={<Eye size={14} />}>Preview customer view</Button>
              <Button variant="secondary" size="sm" leftIcon={<Upload size={14} />} disabled title="Not available — bulk import is not built on the backend yet">
                Import pricing
              </Button>
              <Button variant="primary" size="sm" leftIcon={<Plus size={14} />}
                onClick={() => router.push("/tenant/home-services/setup/services-pricing?return_to=/home-services/services")}>
                Add services
              </Button>
            </>
          }
        />

        {workspace.error && <Alert tone="danger">{workspace.error}</Alert>}

        {workspace.loading || !workspace.data ? (
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

        {/* Real bug fixed here: this grid declared a THIRD 320px column that
            no child was ever placed into -- OfferingWorkspace below already
            renders its own nested detail+pricing split, so that reserved
            column sat permanently empty, squeezing the real content (catalog
            + detail + pricing) into roughly the left two-thirds of the page
            and leaving a dead gutter on the right ("container not full
            width"). Two real columns now: catalog rail + everything else. */}
        <div style={{ display: "grid", gridTemplateColumns: "280px minmax(0, 1fr)", gap: 16, alignItems: "start" }}>
          <Card padding="sm" style={{ maxHeight: 640, overflowY: "auto" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", padding: "4px 8px 8px" }}>SERVICE CATALOG</div>
            {workspace.loading ? (
              <Skeleton height={200} />
            ) : (workspace.data?.catalog_tree ?? []).length === 0 ? (
              <div style={{ padding: 12, fontSize: 13, color: "var(--text-tertiary)" }}>No services enabled yet.</div>
            ) : (
              (workspace.data?.catalog_tree ?? []).map(group => (
                <div key={group.service_group_id} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", padding: "4px 8px" }}>
                    {group.name.toUpperCase()}
                  </div>
                  {group.services.map(s => (
                    <CatalogRow key={s.tenant_service_id} s={s} selected={s.tenant_service_id === effectiveId}
                      onClick={() => router.push(`/home-services/services/${s.tenant_service_id}`)} />
                  ))}
                </div>
              ))
            )}
          </Card>

          {effectiveId ? (
            <OfferingWorkspace key={effectiveId} tenantServiceId={effectiveId} onWorkspaceChanged={workspace.refetch} />
          ) : (
            <Card><div style={{ textAlign: "center", padding: 40, color: "var(--text-tertiary)", fontSize: 13 }}>
              Select a service to view its setup.
            </div></Card>
          )}
        </div>
      </PageShell>
    </TenantLayout>
  );
}

function CatalogRow({ s, selected, onClick }: { s: SWCatalogService; selected: boolean; onClick: () => void }) {
  return (
    <div onClick={onClick} role="button" tabIndex={0}
      onKeyDown={e => { if (e.key === "Enter" || e.key === " ") onClick(); }}
      style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 8px", borderRadius: 8, cursor: "pointer",
        background: selected ? "var(--accent-muted)" : "transparent",
        border: selected ? "1px solid var(--brand)" : "1px solid transparent",
      }}>
      <Wrench size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{s.name}</div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{s.job_type_label ?? "—"}</div>
      </div>
      <StatusBadge status={s.missing_pricing ? "needs_pricing" : s.setup_status} size="sm" />
    </div>
  );
}

const TABS = ["overview", "types-brands", "pricing", "visit-fee", "activity"] as const;
type Tab = typeof TABS[number];
const TAB_LABEL: Record<Tab, string> = {
  overview: "Overview", "types-brands": "Types & Brands", pricing: "Pricing",
  "visit-fee": "Visit Fee", activity: "Activity & Audit",
};

/** Two-column detail+effective-pricing area, driven by one shared refetch so an
 * edit anywhere (pricing/types/brands/publish) reloads both real projections. */
function OfferingWorkspace({ tenantServiceId, onWorkspaceChanged }: { tenantServiceId: string; onWorkspaceChanged: () => void }) {
  const [tab, setTab] = useState<Tab>("overview");
  const detail = useApi(() => servicesWorkspaceApi.detail(tenantServiceId), [tenantServiceId]);

  const refreshAll = () => { detail.refetch(); onWorkspaceChanged(); };

  if (detail.loading || !detail.data) return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.4fr) 320px", gap: 16 }}>
      <Card><Skeleton height={400} /></Card><Card><Skeleton height={300} /></Card>
    </div>
  );
  if (detail.error) return <Card><Alert tone="danger">{detail.error}</Alert></Card>;

  const data = detail.data;
  const ts = data.tenant_service as { setup_status: string; requires_type: boolean; requires_brand: boolean };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.4fr) 320px", gap: 16, alignItems: "start" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <Wrench size={18} style={{ color: "var(--brand)" }} />
            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)", flex: 1 }}>{data.service_name}</div>
            {data.job_type_label && <StatusBadge status={data.job_type_label} size="sm" />}
            <StatusBadge status={ts.setup_status} size="sm" />
          </div>
          <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", overflowX: "auto" }}>
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)} style={{
                padding: "8px 12px", background: "none", border: "none", cursor: "pointer",
                fontSize: 12.5, fontWeight: 600, whiteSpace: "nowrap",
                color: tab === t ? "var(--brand)" : "var(--text-tertiary)",
                borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
              }}>{TAB_LABEL[t]}</button>
            ))}
          </div>
        </Card>

        {tab === "overview" && <OverviewTab data={data} />}
        {tab === "types-brands" && (
          <TypesBrandsTab tenantServiceId={tenantServiceId} data={data} onChanged={refreshAll} />
        )}
        {tab === "pricing" && (
          <DefaultPricingTab tenantServiceId={tenantServiceId} data={data} onChanged={refreshAll} />
        )}
        {tab === "visit-fee" && (
          <VisitFeeTab tenantServiceId={tenantServiceId} data={data} onChanged={refreshAll} />
        )}
        {tab === "activity" && (
          <Card><div style={{ textAlign: "center", padding: 28, color: "var(--text-tertiary)", fontSize: 13 }}>
            Activity & audit isn&apos;t built yet — coming in a follow-up pass.
          </div></Card>
        )}

        <PublicationCard tenantServiceId={tenantServiceId} data={data} onChanged={refreshAll} />
      </div>

      <EffectivePricingPanel data={data} />
    </div>
  );
}

function OverviewTab({ data }: { data: SWOfferingDetail }) {
  return (
    <>
      <Card title="Admin blueprint (read-only)">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, fontSize: 12.5 }}>
          <BlueprintField label="Type" value={data.blueprint.type_mode} />
          <BlueprintField label="Brand" value={data.blueprint.brand_mode} />
          <BlueprintField label="Checklist" value={data.blueprint.requires_checklist ? "Required" : "Not required"} />
          <BlueprintField label="Estimate approval" value={data.blueprint.requires_estimate_approval ? "Required" : "Not required"} />
          <BlueprintField label="Technician" value={data.blueprint.requires_technician ? "Required" : "Optional"} />
          <BlueprintField label="Schedule" value={data.blueprint.requires_schedule ? "Required" : "Optional"} />
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

function TypesBrandsTab({ tenantServiceId, data, onChanged }: {
  tenantServiceId: string; data: SWOfferingDetail; onChanged: () => void;
}) {
  const availableTypes = useApi(() => homeServicesSetupApi.getAvailableTypes(tenantServiceId), [tenantServiceId]);
  const availableBrands = useApi(() => homeServicesSetupApi.getAvailableBrands(tenantServiceId), [tenantServiceId]);
  const typePricing = useApi(() => homeServicesSetupApi.getTypePricing(tenantServiceId), [tenantServiceId]);
  const brandPricing = useApi(() => homeServicesSetupApi.getBrandPricing(tenantServiceId), [tenantServiceId]);

  const refreshLocal = () => { availableTypes.refetch(); availableBrands.refetch(); typePricing.refetch(); brandPricing.refetch(); onChanged(); };

  const { execute: saveTypes, loading: savingTypes, error: typesError } = useAction(
    (typeIds: string[]) => homeServicesSetupApi.setTypes(tenantServiceId, typeIds), { onSuccess: refreshLocal },
  );
  const { execute: saveBrands, loading: savingBrands, error: brandsError } = useAction(
    (brandIds: string[]) => homeServicesSetupApi.setBrands(tenantServiceId, brandIds), { onSuccess: refreshLocal },
  );
  const { execute: saveTypePrice, loading: savingTypePrice } = useAction(
    (args: { serviceTypeId: string; min: number; max: number }) =>
      homeServicesSetupApi.setTypePricing(tenantServiceId, args.serviceTypeId, args.min, args.max),
    { onSuccess: refreshLocal },
  );
  const { execute: saveBrandPrice, loading: savingBrandPrice } = useAction(
    (args: { brandId: string; min: number; max: number }) =>
      homeServicesSetupApi.setBrandPricing(tenantServiceId, args.brandId, args.min, args.max),
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
      {(typesError || brandsError) && <Alert tone="danger">{typesError ?? brandsError}</Alert>}

      {data.tenant_service.requires_type ? (
        <Card title="Supported types">
          {availableTypes.loading ? <Skeleton height={80} /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(availableTypes.data?.types ?? []).map(t => (
                <div key={t.service_type_id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <input type="checkbox" checked={t.is_enabled} disabled={savingTypes} onChange={() => toggleType(t)} />
                  <div style={{ flex: 1, fontSize: 13 }}>{t.name}</div>
                  {t.is_enabled && (
                    <TypePriceRow serviceTypeId={t.service_type_id}
                      current={typePricing.data?.types?.find(x => x.service_type_id === t.service_type_id)}
                      onSave={(min, max) => saveTypePrice({ serviceTypeId: t.service_type_id, min, max })}
                      saving={savingTypePrice} />
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
          {availableBrands.loading ? <Skeleton height={80} /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(availableBrands.data?.brands ?? []).map(b => (
                <div key={b.brand_id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <input type="checkbox" checked={b.is_enabled} disabled={savingBrands} onChange={() => toggleBrand(b)} />
                  <div style={{ flex: 1, fontSize: 13 }}>{b.name}</div>
                  {b.is_enabled && (
                    <TypePriceRow serviceTypeId={b.brand_id}
                      current={brandPricing.data?.brands?.find(x => x.brand_id === b.brand_id)}
                      onSave={(min, max) => saveBrandPrice({ brandId: b.brand_id, min, max })}
                      saving={savingBrandPrice} />
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : (
        <Card><div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>This service doesn&apos;t require a Brand selection.</div></Card>
      )}
    </>
  );
}

function TypePriceRow({ current, onSave, saving }: {
  serviceTypeId: string; current?: { tenant_min_price: number | null; tenant_max_price: number | null }; onSave: (min: number, max: number) => void; saving: boolean;
}) {
  const [min, setMin] = useState(current?.tenant_min_price != null ? String(current.tenant_min_price) : "");
  const [max, setMax] = useState(current?.tenant_max_price != null ? String(current.tenant_max_price) : "");
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      <input value={min} onChange={e => setMin(e.target.value)} placeholder="Min" type="number"
        style={{ width: 70, padding: "5px 6px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 12 }} />
      <span style={{ color: "var(--text-tertiary)" }}>–</span>
      <input value={max} onChange={e => setMax(e.target.value)} placeholder="Max" type="number"
        style={{ width: 70, padding: "5px 6px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 12 }} />
      <button disabled={saving || !min || !max} onClick={() => onSave(Number(min), Number(max))}
        style={{ background: "none", border: "1px solid var(--brand)", borderRadius: 6, padding: "4px 6px", cursor: "pointer", color: "var(--brand)" }}>
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

  const { execute: save, loading, error } = useAction(
    () => homeServicesSetupApi.updateEnabledService(tenantServiceId, {
      tenant_min_price: Number(min), tenant_max_price: Number(max),
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
        <Button variant="primary" size="sm" loading={loading} disabled={!min || !max}
          onClick={() => save()}>Save</Button>
      </div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>
        Used when no Type/Brand override resolves a more specific price.
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
        <Button variant="primary" size="sm" loading={loading} onClick={() => save()}>Save</Button>
      </div>
    </Card>
  );
}

function PublicationCard({ tenantServiceId, data, onChanged }: {
  tenantServiceId: string; data: SWOfferingDetail; onChanged: () => void;
}) {
  const ts = data.tenant_service as { setup_status: string };
  const { execute: saveDraft, loading: savingDraft, error: draftError } = useAction(
    () => homeServicesSetupApi.saveDraft(tenantServiceId), { onSuccess: onChanged },
  );
  const { execute: publish, loading: publishing, error: publishError } = useAction(
    () => homeServicesSetupApi.publish(tenantServiceId), { onSuccess: onChanged },
  );

  return (
    <Card title="Version & publication">
      {(draftError || publishError) && <Alert tone="danger">{draftError ?? publishError}</Alert>}
      <div style={{ fontSize: 12.5, marginBottom: 10 }}>
        Current status: <StatusBadge status={ts.setup_status} size="sm" />
      </div>
      {!data.readiness.ready && (
        <div style={{ fontSize: 11.5, color: "var(--warning-text)", marginBottom: 10 }}>
          Resolve the readiness blockers above before publishing.
        </div>
      )}
      <div style={{ display: "flex", gap: 8 }}>
        <Button variant="secondary" size="sm" loading={savingDraft} onClick={() => saveDraft()}>Save draft</Button>
        <Button variant="primary" size="sm" loading={publishing} disabled={!data.readiness.ready}
          onClick={() => publish()}>Publish</Button>
      </div>
    </Card>
  );
}

function EffectivePricingPanel({ data }: { data: SWOfferingDetail }) {
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
