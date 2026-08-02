"use client";
import React, { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Modal, Input, Skeleton, StatCard, EmptyState } from "../../../../components/shared/ui";
import {
  providerOfferingsApi, providerBrandApi, providerServiceOptionApi, offeringCoverageApi,
  offeringPricingApi, providerServiceAreasApi, providerTeamMembersApi, providerAvailabilityApi,
  myStatusApi, customerServiceDiagnosticsApi,
  type AvailableOffering, type EnabledOffering, type EnableOfferingPayload,
  type ProviderAvailableBrand, type CoverageTypeMapping, type CoverageIssueMapping,
  type CoverageServiceOption, type CustomerIssueType, type ProviderAvailableServiceOption,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { useTenant } from "../../../../hooks/useTenant";
import {
  Package, RefreshCw, CheckCircle2, AlertCircle, XCircle, Zap, MapPin, Users2,
  Clock, Activity as ActivityIcon, ShieldCheck, ClipboardList,
} from "lucide-react";

// ── helpers ───────────────────────────────────────────────────────────────────

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  active: "success", draft: "muted", inactive: "warning", suspended: "danger", rejected: "danger",
};
const READINESS_VARIANT: Record<string, "success" | "warning" | "danger" | "muted"> = {
  ready: "success", not_ready: "warning", blocked: "danger",
};

function fmt(v: string | number | null | undefined) {
  if (v === null || v === undefined || v === "") return "—";
  const n = typeof v === "number" ? v : parseFloat(v);
  return Number.isFinite(n) ? `₹${n.toLocaleString("en-IN")}` : "—";
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

// ── Root Page ────────────────────────────────────────────────────────────────

export default function ServiceSetupPage() {
  const tenant = useTenant();
  const [wizardOffering, setWizardOffering] = useState<AvailableOffering | null>(null);
  const [wizardExisting, setWizardExisting] = useState<EnabledOffering | null>(null);
  const [showActivity, setShowActivity] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  const available = useApi(useCallback(() => providerOfferingsApi.listAvailable(), []));
  const enabled = useApi(useCallback(() => providerOfferingsApi.listEnabled(), []));
  const status = useApi(useCallback(() => myStatusApi.getStatus(), []));
  const offeringStatuses = useApi(useCallback(() => myStatusApi.getOfferingStatuses(), []));
  const areas = useApi(useCallback(() => myStatusApi.getServiceAreas(), []));
  const team = useApi(useCallback(() => myStatusApi.getTeamMembers(), []));
  const availability = useApi(useCallback(() => myStatusApi.getAvailability(), []));
  const activity = useApi(useCallback(() => myStatusApi.getAuditLog(15), []));

  const refreshAllAction = useAction(useCallback(async () => {
    const enabledList = enabled.data?.offerings ?? [];
    await Promise.all(enabledList.map(o => providerOfferingsApi.refreshReadiness(o.provider_enabled_offering_id)));
    return true;
  }, [enabled.data]));

  async function handleValidateSetup() {
    await refreshAllAction.execute();
    enabled.refetch(); status.refetch(); offeringStatuses.refetch();
    notify("Setup readiness refreshed for all enabled services.");
  }

  function refetchAll() {
    available.refetch(); enabled.refetch(); status.refetch(); offeringStatuses.refetch();
    areas.refetch(); team.refetch(); availability.refetch(); activity.refetch();
  }

  const enabledIds = new Set((enabled.data?.offerings ?? []).map(o => o.offering_id));
  const enabledCount = enabled.data?.offerings.length ?? 0;
  const bookableCount = (offeringStatuses.data?.statuses ?? []).filter(s => s.is_bookable).length;
  const activeAreas = (areas.data?.areas ?? []).filter(a => a.is_active).length;
  const totalAreas = areas.data?.areas.length ?? 0;
  const activeTechnicians = (team.data?.members ?? []).filter(m => m.status === "active").length;
  const hasAvailability = (availability.data?.rules ?? []).length > 0;
  const setupIssues = (enabled.data?.offerings ?? []).reduce(
    (n, o) => n + (o.readiness_blockers?.length ?? 0), 0);

  // Home Services scope guard — this wizard (platform catalog enable, coverage,
  // technician assignment, Low/Mid/High-style bargain pricing, "customer pays
  // provider directly") only applies to the Home Services vertical. Other
  // verticals (CA/professional services, IELTS/coaching, restaurants, real
  // estate, education, listing/menu/subscription businesses) must not see
  // this flow. The backend catalog query is already vertical-scoped
  // server-side; this is a defense-in-depth UI-level message.
  if (tenant.vertical && tenant.vertical !== "home_services") {
    return (
      <TenantLayout activeNav="provider-service-setup">
        <Card padding={32} style={{ textAlign: "center" }}>
          <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 6px" }}>
            Service Setup is not available for this business type
          </p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            This platform-catalog service enable/coverage wizard is only available for Home Services
            providers. Your business is registered under {tenant.vertical.replace(/_/g, " ")}.
          </p>
        </Card>
      </TenantLayout>
    );
  }

  return (
    <TenantLayout activeNav="provider-service-setup">
      <div style={{ marginBottom: 16, padding: "10px 16px", borderRadius: 10,
        background: "var(--warning-bg, #fffbeb)", border: "1px solid var(--warning-border, #fde68a)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <p style={{ fontSize: 13, color: "var(--warning-text, #92400e)", margin: 0 }}>
          This page has moved. Open the new Home Services setup flow.
        </p>
        <Link href="/tenant/setup/services" style={{
          fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", whiteSpace: "nowrap" }}>
          Go to Service Setup →
        </Link>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          Tenant Portal / Setup / Service Setup [Deprecated]
        </p>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0, color: "var(--text-primary)" }}>Service Setup</h1>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
              Choose platform-approved services, configure coverage, assign staff, and make your business ready for bookings.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn size="sm" onClick={() => {
              const first = (available.data?.offerings ?? []).find(o => !o.is_already_enabled);
              if (first) { setWizardOffering(first); setWizardExisting(null); }
              else notify("All catalog services are already enabled.", false);
            }}>Add Service</Btn>
            <Btn variant="secondary" size="sm" onClick={refetchAll}><RefreshCw size={14} style={{ marginRight: 4 }}/>Refresh Catalog</Btn>
            <Btn variant="secondary" size="sm" loading={refreshAllAction.loading} onClick={handleValidateSetup}>
              <ShieldCheck size={14} style={{ marginRight: 4 }}/>Validate Setup
            </Btn>
            <Btn variant="secondary" size="sm" onClick={() => setShowActivity(s => !s)}>
              <ActivityIcon size={14} style={{ marginRight: 4 }}/>View Activity
            </Btn>
          </div>
        </div>
      </div>

      {toast && (
        <div style={{ padding: "10px 16px", marginBottom: 16, borderRadius: 10,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13 }}>
          {toast.msg}
        </div>
      )}

      {/* Readiness Hero */}
      <Card padding={24} style={{ marginBottom: 20, background: "linear-gradient(135deg, var(--surface) 0%, var(--surface-sunken) 100%)" }}>
        {status.error ? (
          <SectionError title="We couldn't load service setup" message={status.error} section="provider status" onRetry={status.refetch}/>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "flex-start" }}>
            <div style={{ minWidth: 200 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>
                {tenant.tenantName ?? "Your Business"}
              </h2>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0, textTransform: "capitalize" }}>
                {(tenant.vertical ?? "home_services").replace(/_/g, " ")}
              </p>
              {status.data && (
                <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <Badge variant={status.data.is_bookable ? "success" : "warning"}>
                    {status.data.is_bookable ? "Bookable" : "Not Bookable"}
                  </Badge>
                  <Badge variant={status.data.is_visible ? "success" : "muted"}>
                    {status.data.is_visible ? "Visible" : "Hidden"}
                  </Badge>
                </div>
              )}
            </div>
            <div style={{ flex: 1, display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12 }}>
              <MiniStat label="Enabled Services" value={enabledCount}/>
              <MiniStat label="Bookable Services" value={bookableCount}/>
              <MiniStat label="Setup Issues" value={setupIssues} danger={setupIssues > 0}/>
              <MiniStat label="Service Areas" value={`${activeAreas} / ${totalAreas}`}/>
              <MiniStat label="Technicians" value={activeTechnicians}/>
              <MiniStat label="Pricing" value={enabledCount > 0 ? "Ready" : "—"}/>
              <MiniStat label="Availability" value={hasAvailability ? "Ready" : "Missing"} danger={!hasAvailability}/>
            </div>
          </div>
        )}
      </Card>

      {/* Service Catalog Cards */}
      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Service Catalog</p>
      {available.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 16, marginBottom: 24 }}>
          {[...Array(3)].map((_, i) => <Skeleton key={i} height={160} style={{ borderRadius: 14 }}/>)}
        </div>
      ) : available.error ? (
        <SectionError title="We couldn't load the service catalog" message={available.error} section="catalog" onRetry={available.refetch}/>
      ) : (available.data?.offerings ?? []).length === 0 ? (
        <EmptyState title="No platform services available yet" description="Contact your account manager to have services added to your category."/>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 16, marginBottom: 24 }}>
          {(available.data?.offerings ?? []).map(o => {
            const existing = (enabled.data?.offerings ?? []).find(e => e.offering_id === o.offering_id) ?? null;
            return (
              <Card key={o.offering_id} padding={18}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div>
                    <p style={{ fontSize: 15, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{o.name}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{o.service_group_name ?? "General"}</p>
                  </div>
                  {existing && <Badge variant={STATUS_VARIANT[existing.status] ?? "muted"}>{existing.status}</Badge>}
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12, fontSize: 11, color: "var(--text-tertiary)" }}>
                  {o.requires_service_type && <span>Requires type</span>}
                  {o.requires_brand && <span>· Requires brand</span>}
                  {o.requires_staff && <span>· Requires staff</span>}
                </div>
                <Btn size="sm" style={{ width: "100%" }} onClick={() => { setWizardOffering(o); setWizardExisting(existing); }}>
                  {existing ? "Manage Setup" : "Enable Service"}
                </Btn>
              </Card>
            );
          })}
        </div>
      )}

      {/* Enabled Services Table */}
      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Enabled Services</p>
      <Card padding={0} style={{ marginBottom: 24 }}>
        {enabled.loading ? <div style={{ padding: 20 }}><Skeleton height={120}/></div> : enabled.error ? (
          <div style={{ padding: 20 }}>
            <SectionError title="We couldn't load enabled services" message={enabled.error} section="enabled services" onRetry={enabled.refetch}/>
          </div>
        ) : (enabled.data?.offerings ?? []).length === 0 ? (
          <EmptyState title="No services enabled yet" description="Enable a service from the catalog above to start receiving bookings."/>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Service", "Types", "Brands", "Pricing", "Bookable", "Status", "Actions"].map(h => (
                    <th key={h} style={{ textAlign: "left", padding: "10px 14px", color: "var(--text-tertiary)", fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(enabled.data?.offerings ?? []).map(o => {
                  const bs = (offeringStatuses.data?.statuses ?? []).find(s => s.provider_enabled_offering_id === o.provider_enabled_offering_id);
                  return (
                    <tr key={o.provider_enabled_offering_id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 14px", fontWeight: 600 }}>{o.provider_display_name || o.offering_name}</td>
                      <td style={{ padding: "10px 14px" }}>{o.supported_type_ids?.length ?? 0}</td>
                      <td style={{ padding: "10px 14px" }}>{o.supported_brand_ids?.length ?? 0}</td>
                      <td style={{ padding: "10px 14px" }}>{fmt(o.provider_price_override)}</td>
                      <td style={{ padding: "10px 14px" }}>
                        <Badge variant={bs?.is_bookable ? "success" : "warning"}>{bs?.is_bookable ? "Yes" : "No"}</Badge>
                      </td>
                      <td style={{ padding: "10px 14px" }}><Badge variant={STATUS_VARIANT[o.status] ?? "muted"}>{o.status}</Badge></td>
                      <td style={{ padding: "10px 14px" }}>
                        <div style={{ display: "flex", gap: 6 }}>
                          <Btn size="xs" variant="secondary" onClick={() => {
                            const avail = (available.data?.offerings ?? []).find(a => a.offering_id === o.offering_id) ?? null;
                            setWizardOffering(avail); setWizardExisting(o);
                          }}>Manage</Btn>
                          {o.status === "active" ? (
                            <Btn size="xs" variant="danger" onClick={async () => {
                              await providerOfferingsApi.deactivate(o.provider_enabled_offering_id);
                              enabled.refetch(); offeringStatuses.refetch(); notify("Service disabled.");
                            }}>Disable</Btn>
                          ) : (
                            <Btn size="xs" variant="primary" onClick={async () => {
                              await providerOfferingsApi.activate(o.provider_enabled_offering_id);
                              enabled.refetch(); offeringStatuses.refetch(); notify("Service activated.");
                            }}>Activate</Btn>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Readiness Issues Panel */}
      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Readiness Issues</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 24 }}>
        {(enabled.data?.offerings ?? []).flatMap(o => (o.readiness_blockers ?? []).map((b, i) => (
          <Card key={`${o.provider_enabled_offering_id}-${i}`} padding={14}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <AlertCircle size={16} style={{ color: "var(--warning-text)", flexShrink: 0 }}/>
                <div>
                  <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{b.code}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>{b.message}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
                    Affected: {o.provider_display_name || o.offering_name}
                  </p>
                </div>
              </div>
              <Btn size="xs" variant="secondary" onClick={() => {
                const avail = (available.data?.offerings ?? []).find(a => a.offering_id === o.offering_id) ?? null;
                setWizardOffering(avail); setWizardExisting(o);
              }}>Fix</Btn>
            </div>
          </Card>
        )))}
        {enabled.data && (enabled.data.offerings ?? []).every(o => (o.readiness_blockers ?? []).length === 0) && (
          <EmptyState icon={<CheckCircle2 size={28}/>} title="No readiness issues" description="All enabled services are fully configured."/>
        )}
      </div>

      {/* Activity Timeline */}
      {showActivity && (
        <>
          <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Activity</p>
          <Card padding={0} style={{ marginBottom: 24 }}>
            {activity.loading ? <div style={{ padding: 20 }}><Skeleton height={120}/></div> : activity.error ? (
              <div style={{ padding: 20 }}>
                <SectionError title="We couldn't load activity" message={activity.error} section="activity" onRetry={activity.refetch}/>
              </div>
            ) : (activity.data?.logs ?? []).length === 0 ? (
              <EmptyState title="No activity yet" description="Setup changes will appear here."/>
            ) : (activity.data?.logs ?? []).map((log, i, arr) => (
              <div key={log.log_id} style={{ padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                <p style={{ margin: 0, fontSize: 12, fontWeight: 600 }}>{log.action_type}</p>
                {log.notes && <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>{log.notes}</p>}
                <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{new Date(log.created_at).toLocaleString()}</p>
              </div>
            ))}
          </Card>
        </>
      )}

      {wizardOffering && (
        <ServiceSetupWizard
          offering={wizardOffering}
          existing={wizardExisting}
          onClose={() => { setWizardOffering(null); setWizardExisting(null); }}
          onSaved={() => { setWizardOffering(null); setWizardExisting(null); refetchAll(); notify("Service setup saved."); }}
        />
      )}
    </TenantLayout>
  );
}

function MiniStat({ label, value, danger }: { label: string; value: string | number; danger?: boolean }) {
  return (
    <div style={{ padding: "10px 14px", background: "var(--surface-sunken)", borderRadius: 10 }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: danger ? "var(--danger-text)" : "var(--text-primary)" }}>{value}</div>
      <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 2, textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// WIZARD — 10 steps, real APIs at every step
// ─────────────────────────────────────────────────────────────────────────────

type WizardStep = "service" | "type" | "brand" | "issues" | "options" | "areas" | "technician" | "pricing" | "availability" | "review";
const WIZARD_STEPS: { key: WizardStep; label: string }[] = [
  { key: "service", label: "1. Service" }, { key: "type", label: "2. Type" },
  { key: "brand", label: "3. Brands" }, { key: "issues", label: "4. Issues" },
  { key: "options", label: "5. Options" }, { key: "areas", label: "6. Service Areas" },
  { key: "technician", label: "7. Technician" }, { key: "pricing", label: "8. Pricing" },
  { key: "availability", label: "9. Availability" }, { key: "review", label: "10. Review" },
];

function ServiceSetupWizard({ offering, existing, onClose, onSaved }: {
  offering: AvailableOffering; existing: EnabledOffering | null; onClose: () => void; onSaved: () => void;
}) {
  const [step, setStep] = useState<WizardStep>("service");
  const [selectedTypeIds, setSelectedTypeIds] = useState<string[]>(existing?.supported_type_ids ?? []);
  const [selectedBrandIds, setSelectedBrandIds] = useState<string[]>(existing?.supported_brand_ids ?? []);
  const [selectedOptionIds, setSelectedOptionIds] = useState<string[]>([]);
  const [saveError, setSaveError] = useState<string | null>(null);

  const types = useApi(useCallback(() => offeringCoverageApi.getTypes(offering.offering_id), [offering.offering_id]));
  const brands = useApi(useCallback(() =>
    providerBrandApi.getAvailableForService(offering.offering_id), [offering.offering_id]));
  const issues = useApi(useCallback(() =>
    customerServiceDiagnosticsApi.getIssueTypes(offering.offering_id), [offering.offering_id]));
  const options = useApi(useCallback(() =>
    providerServiceOptionApi.getAvailableForService(offering.offering_id), [offering.offering_id]));
  const areas = useApi(useCallback(() => providerServiceAreasApi.list(), []));
  const team = useApi(useCallback(() => providerTeamMembersApi.list(), []));
  const availability = useApi(useCallback(() => providerAvailabilityApi.list(), []));

  const [pricingResult, setPricingResult] = useState<{ final_price: string | number; currency: string; note: string } | null>(null);
  const pricingAction = useAction(useCallback(async () => {
    const firstArea = (areas.data?.areas ?? []).find(a => a.is_active);
    const cityName = firstArea?.city ?? "";
    const pincode = firstArea?.zipcode ?? null;
    const typeId = selectedTypeIds[0] ?? offering.offering_id;
    return offeringPricingApi.preview(typeId, offering.service_group_name ?? "home_services", cityName, pincode);
  }, [areas.data, selectedTypeIds, offering]));

  const saveAction = useAction(useCallback(async (activate: boolean) => {
    const payload: EnableOfferingPayload = {
      offering_id: offering.offering_id,
      supported_type_ids: offering.requires_service_type ? selectedTypeIds : null,
      supported_brand_ids: offering.requires_brand ? selectedBrandIds : null,
      activate_if_ready: activate,
    };
    let result: EnabledOffering;
    if (existing) {
      result = await providerOfferingsApi.update(existing.provider_enabled_offering_id, payload);
    } else {
      result = await providerOfferingsApi.enable(payload);
    }
    if (selectedOptionIds.length > 0) {
      await providerServiceOptionApi.setSupportedForService(offering.offering_id, selectedOptionIds);
    }
    if (activate && result.status !== "active") {
      await providerOfferingsApi.activate(result.provider_enabled_offering_id);
    }
    return result;
  }, [offering, selectedTypeIds, selectedBrandIds, selectedOptionIds, existing]));

  async function handleSave(activate: boolean) {
    setSaveError(null);
    try {
      await saveAction.execute(activate);
      onSaved();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed.");
    }
  }

  const typeOk = !offering.requires_service_type || selectedTypeIds.length > 0;
  const brandOk = !offering.requires_brand || selectedBrandIds.length > 0;
  const issuesOk = true; // optional per catalog — informational step
  const areasOk = (areas.data?.areas ?? []).some(a => a.is_active);
  const technicianOk = !offering.requires_staff || (team.data?.members ?? []).some(m => m.status === "active");
  const availabilityOk = (availability.data?.rules ?? []).length > 0;
  const readyToEnable = typeOk && brandOk && areasOk && technicianOk && availabilityOk;

  const stepIndex = WIZARD_STEPS.findIndex(s => s.key === step);

  return (
    <Modal open onClose={onClose} title={`${existing ? "Manage" : "Enable"} ${offering.name}`} size="lg">
      <div style={{ minWidth: 680, display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {WIZARD_STEPS.map(s => (
            <button key={s.key} onClick={() => setStep(s.key)} style={{
              padding: "6px 10px", fontSize: 10, fontWeight: step === s.key ? 700 : 500,
              border: "none", borderBottom: step === s.key ? "2px solid var(--brand)" : "2px solid var(--border)",
              background: "none", color: step === s.key ? "var(--brand)" : "var(--text-tertiary)", cursor: "pointer",
            }}>{s.label}</button>
          ))}
        </div>

        {step === "service" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{offering.name}</p>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
              Group: {offering.service_group_name ?? "General"} · Category: Home Services
            </p>
            <div style={{ padding: 12, background: "var(--info-bg, #eff6ff)", borderRadius:"var(--radius-md)" }}>
              <p style={{ fontSize: 12, color: "var(--info-text, var(--brand-hover))", margin: 0 }}>
                This service is managed by the platform catalog. You can enable it and configure your coverage below.
              </p>
            </div>
          </div>
        )}

        {step === "type" && (
          <StepPicker
            title="Service Type" required={offering.requires_service_type}
            loading={types.loading} error={types.error} onRetry={types.refetch}
            items={(types.data?.types ?? []).map((t: CoverageTypeMapping) => ({ id: t.service_type_id, label: t.name }))}
            selected={selectedTypeIds} onToggle={id => setSelectedTypeIds(prev =>
              prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])}
            helpText="At least one type is required."
          />
        )}

        {step === "brand" && (
          <StepPicker
            title="Brands" required={offering.requires_brand}
            loading={brands.loading} error={brands.error} onRetry={brands.refetch}
            items={(brands.data?.brands ?? []).map((b: ProviderAvailableBrand) => ({ id: b.brand_id, label: b.display_name || b.name }))}
            selected={selectedBrandIds} onToggle={id => setSelectedBrandIds(prev =>
              prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])}
            helpText="At least one brand is required if this service needs brand coverage."
          />
        )}

        {step === "issues" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Common Customer Issues</p>
            {issues.loading ? <Skeleton height={100}/> : issues.error ? (
              <SectionError title="Couldn't load issue types" message={issues.error} section="issues" onRetry={issues.refetch}/>
            ) : (issues.data ?? []).length === 0 ? (
              <EmptyState title="No issue types mapped" description="This service has no customer-reported issue types configured yet."/>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(issues.data ?? []).map((it: CustomerIssueType) => (
                  <div key={it.issue_type_id} style={{ padding: 10, border: "1px solid var(--border)", borderRadius:"var(--radius-md)" }}>
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{it.name}</p>
                    <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
                      Customer reports this issue with {offering.name.toLowerCase()}.
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === "options" && (
          <StepPicker
            title="Options / Add-ons" required={false}
            loading={options.loading} error={options.error} onRetry={options.refetch}
            items={(options.data ?? []).map((o: ProviderAvailableServiceOption) => ({ id: o.id, label: o.name }))}
            selected={selectedOptionIds} onToggle={id => setSelectedOptionIds(prev =>
              prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])}
            helpText="Options are optional unless required by platform policy."
          />
        )}

        {step === "areas" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Service Areas</p>
            {areas.loading ? <Skeleton height={100}/> : areas.error ? (
              <SectionError title="Couldn't load service areas" message={areas.error} section="service areas" onRetry={areas.refetch}/>
            ) : (areas.data?.areas ?? []).filter(a => a.is_active).length === 0 ? (
              <EmptyState title="No active service areas" description="At least one active service area is required for bookability."
                action={<Btn size="sm" onClick={() => window.open("/provider/service-areas", "_blank")}>Add Service Area</Btn>}/>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(areas.data?.areas ?? []).filter(a => a.is_active).map(a => (
                  <div key={a.id} style={{ padding: 10, border: "1px solid var(--border)", borderRadius:"var(--radius-md)", display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 13 }}>
                      {[a.city, a.zipcode, a.state].filter(Boolean).join(", ") || a.zone_name || "Coverage area"}
                    </span>
                    <Badge variant="success">Active</Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === "technician" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Assign Technician</p>
            {team.loading ? <Skeleton height={100}/> : team.error ? (
              <SectionError title="Couldn't load team" message={team.error} section="team" onRetry={team.refetch}/>
            ) : (team.data?.members ?? []).filter(m => m.status === "active").length === 0 ? (
              <EmptyState title={`No active technician found for ${offering.name}`}
                description="At least one active technician is required if this service requires staff assignment."
                action={<Btn size="sm" onClick={() => window.open("/provider/service-areas", "_blank")}>Add Technician</Btn>}/>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(team.data?.members ?? []).filter(m => m.status === "active").map(m => (
                  <div key={m.member_id} style={{ padding: 10, border: "1px solid var(--border)", borderRadius:"var(--radius-md)" }}>
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{m.full_name}</p>
                    <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {(m.skills ?? []).join(", ") || "No skills listed"} · <Badge variant="success">Active</Badge>
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === "pricing" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Pricing Preview</p>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
              Pricing is resolved by the platform — you cannot set an authoritative price here.
            </p>
            <Btn size="sm" variant="secondary" loading={pricingAction.loading} onClick={async () => {
              const r = await pricingAction.execute();
              if (r) setPricingResult(r as unknown as { final_price: string | number; currency: string; note: string });
            }}>Preview Price</Btn>
            {pricingAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)" }}>{pricingAction.error}</p>}
            {pricingResult && (
              <div style={{ padding: 14, background: "var(--surface-sunken)", borderRadius: 10 }}>
                <p style={{ margin: 0, fontSize: 20, fontWeight: 800 }}>
                  {pricingResult.currency ?? "₹"}{pricingResult.final_price}
                </p>
                <p style={{ margin: "4px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{pricingResult.note}</p>
                <p style={{ margin: "4px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
                  Payment: Customer pays the provider directly on-site.
                </p>
              </div>
            )}
          </div>
        )}

        {step === "availability" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Availability</p>
            {availability.loading ? <Skeleton height={80}/> : availability.error ? (
              <SectionError title="Couldn't load availability" message={availability.error} section="availability" onRetry={availability.refetch}/>
            ) : (availability.data?.rules ?? []).length === 0 ? (
              <EmptyState title="Availability is missing"
                description="Customers cannot book this service until working hours are added."
                action={<Btn size="sm" onClick={() => window.open("/provider/availability", "_blank")}>Add Availability</Btn>}/>
            ) : (
              <div style={{ padding: 12, background: "var(--success-bg)", borderRadius:"var(--radius-md)" }}>
                <p style={{ margin: 0, fontSize: 12, color: "var(--success-text)" }}>
                  Availability configured — {availability.data?.rules.length} rule(s) active.
                </p>
              </div>
            )}
          </div>
        )}

        {step === "review" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Review Checklist</p>
            <ChecklistRow label="Service selected" ok={true}/>
            <ChecklistRow label="Type selected" ok={typeOk}/>
            <ChecklistRow label="Brand selected" ok={brandOk}/>
            <ChecklistRow label="Options selected" ok={true}/>
            <ChecklistRow label="Service area linked" ok={areasOk}/>
            <ChecklistRow label="Technician assigned" ok={technicianOk}/>
            <ChecklistRow label="Availability ready" ok={availabilityOk}/>
            <div style={{ marginTop: 10, padding: 12, borderRadius:"var(--radius-md)",
              background: readyToEnable ? "var(--success-bg)" : "var(--warning-bg)" }}>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 700,
                color: readyToEnable ? "var(--success-text)" : "var(--warning-text)" }}>
                {readyToEnable ? "Ready to enable" : "Will be saved as draft because setup is incomplete"}
              </p>
            </div>
            {saveError && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{saveError}</p>}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <div style={{ display: "flex", gap: 8 }}>
            {stepIndex > 0 && (
              <Btn variant="secondary" size="sm" onClick={() => setStep(WIZARD_STEPS[stepIndex - 1].key)}>Back</Btn>
            )}
            {step !== "review" ? (
              <Btn size="sm" onClick={() => setStep(WIZARD_STEPS[stepIndex + 1].key)}>Next</Btn>
            ) : (
              <>
                <Btn variant="secondary" size="sm" loading={saveAction.loading} onClick={() => handleSave(false)}>Save Draft</Btn>
                <Btn size="sm" loading={saveAction.loading} disabled={!readyToEnable} onClick={() => handleSave(true)}>Enable Service</Btn>
              </>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}

function StepPicker({ title, required, loading, error, onRetry, items, selected, onToggle, helpText }: {
  title: string; required: boolean; loading: boolean; error?: string | null; onRetry: () => void;
  items: { id: string; label: string }[]; selected: string[]; onToggle: (id: string) => void; helpText: string;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>{title}{required && <span style={{ color: "var(--danger)" }}> *</span>}</p>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{helpText}</p>
      {loading ? <Skeleton height={80}/> : error ? (
        <SectionError title={`Couldn't load ${title.toLowerCase()}`} message={error} section={title.toLowerCase()} onRetry={onRetry}/>
      ) : items.length === 0 ? (
        <EmptyState title={`No ${title.toLowerCase()} available`} description="Ask the platform admin to map options for this service."/>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {items.map(it => {
            const active = selected.includes(it.id);
            return (
              <button key={it.id} onClick={() => onToggle(it.id)} style={{
                padding: "8px 14px", borderRadius: 999, fontSize: 12, fontWeight: active ? 700 : 500,
                border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
                background: active ? "var(--brand)" : "var(--surface)",
                color: active ? "white" : "var(--text-secondary)", cursor: "pointer",
              }}>{it.label}</button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ChecklistRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
      {ok ? <CheckCircle2 size={16} style={{ color: "var(--success)" }}/> : <XCircle size={16} style={{ color: "var(--danger)" }}/>}
      <span style={{ color: ok ? "var(--text-primary)" : "var(--danger-text)", fontWeight: ok ? 400 : 600 }}>{label}</span>
    </div>
  );
}
