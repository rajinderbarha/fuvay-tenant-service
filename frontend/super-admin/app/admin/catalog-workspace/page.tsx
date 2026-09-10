"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../components/catalog/HomeServicesCatalogNav";
import { BLUEPRINT_SETUP_STEPS } from "../../../components/catalog/catalog-setup-sequence";
import { AddServiceJobType } from "../../../components/catalog/AddServiceJobType";
import { preferredJobType } from "../../../components/catalog/service-family";
import { ServiceFamilyIdentity } from "../../../components/catalog/ServiceFamilyIdentity";
import { AddChecklistMappingForm } from "../../../components/catalog/AddChecklistMappingForm";
import { IconPicker } from "../../../components/shared/IconPicker";
import {
  homeServicesCatalogConsoleApi, catalogWorkspaceApi, checklistCatalogApi, catalogApi,
  type HsConsoleService, type CatalogJobType, type DimensionGridRow, type CatalogDimensionDef,
  type BlueprintReadiness, type BlueprintImpactReport, type BlueprintDraftStatus, type CatalogQuestionItem,
  type CatalogIssueTypeMapping, type ServiceJobWorkflow, type MasterServiceJobTypeLink,
  type CatalogDimensionValueItem,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { usePermissions } from "../../../hooks/usePermissions";
import { WorkflowStepBuilder } from "./WorkflowStepBuilder";
import { Btn, Pagination, SectionHeader } from "../../../components/shared/ui";
import {
  ChevronRight, RefreshCw, XCircle, CheckCircle2, Layers, Lock, Plus,
  CircleDot, ListChecks, SlidersHorizontal, HelpCircle, Search, ClipboardList, Trash2,
} from "lucide-react";

// ── Shared formatters (same convention as the rest of this app) ─────────────
const safeText = (v: unknown, fb = "Not configured"): string =>
  (typeof v === "string" && v.trim()) ? v.trim() : fb;

function SectionError({ title, error, requestId, onRetry }: {
  title: string; error: string; requestId?: string | null; onRetry: () => void;
}) {
  return (
    <div style={{ padding: "14px 16px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: "var(--radius-lg)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--danger-text)", margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6 }}>
            <XCircle size={14}/> {title}
          </p>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0, opacity: 0.85 }}>{error}</p>
          {requestId && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: "4px 0 0", opacity: 0.7 }}>Request ID: {requestId}</p>}
        </div>
        <button onClick={onRetry} style={{ padding: "6px 12px", fontSize: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--danger-border)", background: "transparent", color: "var(--danger-text)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
          <RefreshCw size={11}/> Retry
        </button>
      </div>
    </div>
  );
}

function Skeleton({ height = 60 }: { height?: number }) {
  return <div style={{ height, background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", animation: "pulse 1.5s ease-in-out infinite" }}/>;
}

const WORKSPACE_TABS = BLUEPRINT_SETUP_STEPS.map(step => ({ ...step,
  icon: step.key === "overview" ? ClipboardList : step.key === "preview" ? Search : step.key === "problems" ? HelpCircle : ListChecks,
}));
type WorkspaceTabKey = typeof WORKSPACE_TABS[number]["key"];

function isWorkspaceTabKey(value: string | null): value is WorkspaceTabKey {
  return !!value && WORKSPACE_TABS.some(tab => tab.key === value);
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AdminCatalogWorkspacePage() {
  const searchParams = useSearchParams();
  const perm = usePermissions();
  const canRead = perm.loading || perm.has("catalog:services:read");
  const canWrite = perm.has("catalog:services:write");

  const [serviceQuery, setServiceQuery] = useState("");
  const [debouncedServiceQuery, setDebouncedServiceQuery] = useState("");
  const [serviceGroupFilter, setServiceGroupFilter] = useState("");
  const [servicePage, setServicePage] = useState(1);
  const [servicePageSize, setServicePageSize] = useState(25);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedServiceQuery(serviceQuery.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [serviceQuery]);
  const listApi = useApi(useCallback(() => homeServicesCatalogConsoleApi.listServices({
    q: debouncedServiceQuery || undefined,
    service_id: searchParams.get("service_id") || undefined,
    service_group_id: serviceGroupFilter || undefined,
    limit: servicePageSize,
    offset: (servicePage - 1) * servicePageSize,
  }), [debouncedServiceQuery, serviceGroupFilter, servicePage, servicePageSize, searchParams]), [debouncedServiceQuery, serviceGroupFilter, servicePage, servicePageSize, searchParams]);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedJobTypeId, setSelectedJobTypeId] = useState<string | null>(null);
  const [showAddJobType, setShowAddJobType] = useState(false);
  const [tab, setTab] = useState<WorkspaceTabKey>("overview");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  function notify(msg: string, type: "success" | "error" = "success") {
    setToast({ msg, type }); setTimeout(() => setToast(null), 3500);
  }
  const requestedTab = searchParams.get("tab");

  const services = listApi.data?.services ?? [];
  const groups = listApi.data?.groups ?? [];
  const grouped = groups.map(g => ({ group: g, services: services.filter(s => s.service_group_id === g.group_id) }));
  const ungrouped = services.filter(s => !s.service_group_id);

  useEffect(() => {
    const requested = searchParams.get("service_id");
    if (requested && services.some(service => service.service_id === requested)) {
      setSelectedId(requested);
    }
  }, [searchParams, services]);

  useEffect(() => {
    if (isWorkspaceTabKey(requestedTab)) {
      setTab(requestedTab);
    }
  }, [requestedTab]);

  // Job types actually added to the SELECTED service (master_service_job_types)
  // -- the real, per-service tab source. Fixes a gap where the tabs used to
  // list every global job type regardless of whether it applied to this
  // service (Dimensions/Problems tabs already tolerated that; the workflow
  // Overview tab added in migration 160 made the gap concrete).
  const serviceJobTypesApi = useApi(
    useCallback(() => selectedId ? catalogWorkspaceApi.listServiceJobTypes(selectedId) : Promise.resolve({ items: [] }),
      [selectedId]),
    [selectedId], { enabled: !!selectedId },
  );
  const serviceJobTypeLinks = (serviceJobTypesApi.data?.items ?? []).filter(l => l.is_active);
  const initializedService = useRef<string | null>(null);
  useEffect(() => {
    const first = serviceJobTypeLinks.find(link => link.master_service_id === selectedId);
    if (selectedId && first && initializedService.current !== selectedId) {
      initializedService.current = selectedId;
      setSelectedJobTypeId(preferredJobType(services.find(service => service.service_id === selectedId)?.service_name ?? "", serviceJobTypeLinks));
    }
  }, [selectedId, serviceJobTypeLinks, services]);

  const readinessApi = useApi(
    useCallback(() => selectedId ? catalogWorkspaceApi.getReadiness(selectedId, selectedJobTypeId) : Promise.resolve(null as unknown as BlueprintReadiness),
      [selectedId, selectedJobTypeId]),
    [selectedId, selectedJobTypeId], { enabled: !!selectedId },
  );
  const impactApi = useApi(
    useCallback(() => selectedId ? catalogWorkspaceApi.getImpactReport(selectedId) : Promise.resolve(null as unknown as BlueprintImpactReport),
      [selectedId]),
    [selectedId], { enabled: !!selectedId },
  );
  const draftApi = useApi(
    useCallback(() => selectedId ? catalogWorkspaceApi.getDraftStatus(selectedId) : Promise.resolve(null as unknown as BlueprintDraftStatus),
      [selectedId]),
    [selectedId], { enabled: !!selectedId },
  );
  const publishAction = useAction(catalogWorkspaceApi.publishDraft);
  const removeJobTypeAction = useAction(catalogWorkspaceApi.removeServiceJobType);

  async function handleRemoveJobType(link: MasterServiceJobTypeLink) {
    if (!selectedId || !canWrite) return;
    if (!window.confirm(`Remove ${link.job_type.label} from this service? Any tenant currently offering it returns to draft for re-review.`)) return;
    const result = await removeJobTypeAction.execute(selectedId, link.id);
    if (result) {
      notify(`${link.job_type.label} removed from this service.`);
      if (selectedJobTypeId === link.job_type_id) setSelectedJobTypeId(null);
      serviceJobTypesApi.refetch();
    } else {
      notify(removeJobTypeAction.error ?? "Couldn't remove this job type.", "error");
    }
  }

  async function handlePublish() {
    if (!selectedId || !canWrite) return;
    const result = await publishAction.execute(selectedId);
    if (result) {
      notify(`Published blueprint v${result.version_number}.`);
      draftApi.refetch(); impactApi.refetch(); readinessApi.refetch();
    } else {
      notify(publishAction.error ?? "Couldn't publish.", "error");
    }
  }

  function selectService(id: string) {
    setSelectedId(id);
    setSelectedJobTypeId(null);
    initializedService.current = null;
    setTab(isWorkspaceTabKey(requestedTab) ? requestedTab : "overview");
  }

  if (!perm.loading && !canRead) {
    return (
      <AdminLayout activeNav="catalog-workspace">
        <div style={{ padding: "60px 24px", textAlign: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}>
          <Lock size={28} style={{ color: "var(--danger-text)", marginBottom: 10 }}/>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>You don't have access to the Catalog Workspace</p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Contact an administrator to request catalog read access.</p>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout activeNav="catalog-workspace">
      <style>{`
        @keyframes fadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        .cw-shell{display:grid;grid-template-columns:minmax(240px,280px) minmax(0,1fr) minmax(280px,320px);gap:16px;align-items:start}
        @media(max-width:1300px){.cw-shell{grid-template-columns:220px minmax(0,1fr) 280px}}
        @media(max-width:1000px){.cw-shell{grid-template-columns:1fr}}
        .cw-panel{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);box-shadow:var(--shadow-sm)}
        .cw-side{position:sticky;top:76px;max-height:calc(100vh - 96px);overflow:auto}
        @media(max-width:1000px){.cw-side{position:static;max-height:none}}
        .cw-jt-tab{padding:7px 12px;font-size:12px;font-weight:600;white-space:nowrap;border-radius:999px;border:1px solid var(--border);background:var(--surface-sunken);cursor:pointer;color:var(--text-secondary)}
        .cw-jt-tab.active{color:white;background:var(--brand);border-color:var(--brand)}
        .cw-wtab{padding:9px 14px;font-size:12px;font-weight:600;white-space:nowrap;border:none;background:none;cursor:pointer;color:var(--text-secondary);border-bottom:2px solid transparent;display:flex;align-items:center;gap:6}
        .cw-wtab.active{color:var(--brand);border-bottom-color:var(--brand)}
      `}</style>

      {toast && (
        <div style={{ position: "fixed", top: 72, right: 24, zIndex: 9999, maxWidth: 380, padding: "12px 18px", borderRadius: 10, boxShadow: "0 4px 24px rgba(0,0,0,0.15)", animation: "fadeIn 0.2s ease",
          background: toast.type === "success" ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.type === "success" ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.type === "success" ? "var(--success-text)" : "var(--danger-text)", fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 8 }}>
          {toast.type === "success" ? <CheckCircle2 size={14}/> : <XCircle size={14}/>}
          {toast.msg}
        </div>
      )}

      <div style={{ marginBottom: "var(--layout-page-gap)" }}>
        <SectionHeader eyebrow="Catalog setup · Step 6" context="Home Services" title="Job-Type Blueprints"
          description="Configure platform-owned service behavior, customer questions, checklists, and tenant setup rules. Price amounts remain tenant-owned."
          actions={<Btn variant="secondary" onClick={() => { listApi.refetch(); serviceJobTypesApi.refetch(); readinessApi.refetch(); impactApi.refetch(); draftApi.refetch(); }}>
            <RefreshCw size={12}/> Refresh
          </Btn>} />
      </div>

      <HomeServicesCatalogNav active="workspace" />

      <div className="cw-shell">
        {/* ── Column 1: Catalog Structure ─────────────────────────────────── */}
        <div className="cw-panel cw-side" style={{ padding: 14 }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px", padding: "0 4px" }}>
            Catalog Structure
          </p>
          <div style={{ position: "relative", marginBottom: 8 }}>
            <Search size={13} style={{ position: "absolute", left: 10, top: 9, color: "var(--text-tertiary)" }}/>
            <input aria-label="Search master services" value={serviceQuery}
              onChange={e => { setServiceQuery(e.target.value); setServicePage(1); }}
              placeholder="Search services…" style={{ width: "100%", boxSizing: "border-box", padding: "7px 9px 7px 30px", border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 12 }}/>
          </div>
          <select aria-label="Filter service group" value={serviceGroupFilter}
            onChange={e => { setServiceGroupFilter(e.target.value); setServicePage(1); }}
            style={{ width: "100%", padding: "7px 9px", marginBottom: 10, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 12 }}>
            <option value="">All service groups</option>
            {groups.map(group => <option key={group.group_id} value={group.group_id}>{group.name}</option>)}
          </select>
          {listApi.error ? (
            <SectionError title="Couldn't load catalog" error={listApi.error} requestId={listApi.requestId} onRetry={listApi.refetch}/>
          ) : listApi.loading ? (
            [...Array(5)].map((_, i) => <div key={i} style={{ marginBottom: 6 }}><Skeleton height={36}/></div>)
          ) : (
            <>
              {grouped.map(({ group, services: gs }) => gs.length > 0 && (
                <div key={group.group_id} style={{ marginBottom: 12 }}>
                  <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 6px", padding: "0 4px" }}>{group.name}</p>
                  {gs.map(s => <ServiceRow key={s.service_id} s={s} active={s.service_id === selectedId} onClick={() => selectService(s.service_id)}/>)}
                </div>
              ))}
              {ungrouped.length > 0 && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 6px", padding: "0 4px" }}>Other</p>
                  {ungrouped.map(s => <ServiceRow key={s.service_id} s={s} active={s.service_id === selectedId} onClick={() => selectService(s.service_id)}/>)}
                </div>
              )}
              {services.length === 0 && <p style={{ fontSize: 12, color: "var(--text-tertiary)", padding: 8 }}>No services configured yet.</p>}
            </>
          )}
          <Pagination page={servicePage} pageSize={servicePageSize} total={listApi.data?.total ?? 0}
            navigationMode="adjacent" onPage={setServicePage} pageSizes={[25, 50, 100]}
            onPageSize={size => { setServicePageSize(size); setServicePage(1); }}
            itemLabel="services" pageSizeLabel="Services per page" />
        </div>

        {/* ── Column 2: Service Workspace ──────────────────────────────────── */}
        <div className="cw-panel" style={{ padding: "20px 22px", minHeight: 500, minWidth: 0 }}>
          {!selectedId ? (
            <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--text-tertiary)" }}>
              <Layers size={30} style={{ opacity: 0.3, marginBottom: 10 }}/>
              <p style={{ fontSize: 13, margin: 0 }}>Select a service on the left to configure its blueprint.</p>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
                  <h2 style={{ fontSize: 17, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                    {safeText(services.find(s => s.service_id === selectedId)?.service_name, "Service")}
                  </h2>
                  {draftApi.data && draftApi.data.has_pending_changes && (
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: "var(--warning-bg, var(--surface-sunken))", color: "var(--warning-text, var(--text-secondary))", border: "1px solid var(--border)" }}>
                        Unreleased changes · {draftApi.data.pending_change_count}
                      </span>
                      {canWrite && (
                        <button onClick={handlePublish} disabled={publishAction.loading}
                          style={{ fontSize: 12, fontWeight: 700, padding: "6px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white", cursor: publishAction.loading ? "default" : "pointer" }}>
                          {publishAction.loading ? "Publishing..." : "Publish reviewed blueprint"}
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <ServiceFamilyIdentity serviceId={selectedId} name={services.find(service => service.service_id === selectedId)?.service_name ?? ""} canWrite={canWrite}
                  onSaved={() => { listApi.refetch(); notify("Family name updated. Existing mappings and prices are unchanged."); }} />
                {serviceJobTypesApi.loading ? <Skeleton height={30}/> : (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                    <details><summary>Advanced defaults</summary><button className={`cw-jt-tab ${selectedJobTypeId === null ? "active" : ""}`} onClick={() => setSelectedJobTypeId(null)}>Shared defaults — not a job type</button></details>
                    {serviceJobTypeLinks.map(link => (
                      <span key={link.job_type_id} style={{ display: "inline-flex", alignItems: "center" }}>
                        <button className={`cw-jt-tab ${selectedJobTypeId === link.job_type_id ? "active" : ""}`} onClick={() => setSelectedJobTypeId(link.job_type_id)}
                          style={canWrite ? { borderTopRightRadius: 0, borderBottomRightRadius: 0 } : undefined}
                          title={link.job_type.runtime_supported ? undefined : "Not yet wired into field_ops runtime transitions"}>
                          {link.job_type.label}{!link.job_type.runtime_supported && " *"}
                        </button>
                        {canWrite && (
                          <button onClick={() => handleRemoveJobType(link)} disabled={removeJobTypeAction.loading}
                            aria-label={`Remove ${link.job_type.label} from this service`}
                            title={`Remove ${link.job_type.label} from this service`}
                            className={selectedJobTypeId === link.job_type_id ? "cw-jt-tab active" : "cw-jt-tab"}
                            style={{ borderTopLeftRadius: 0, borderBottomLeftRadius: 0, borderLeft: "1px solid color-mix(in srgb, currentColor 25%, transparent)", padding: "7px 8px", display: "flex" }}>
                            <Trash2 size={12}/>
                          </button>
                        )}
                      </span>
                    ))}
                    {canWrite && (
                      <button onClick={() => setShowAddJobType(v => !v)} className="cw-jt-tab" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <Plus size={12}/> Add Job Type
                      </button>
                    )}
                  </div>
                )}
                {showAddJobType && (
                  <AddServiceJobType masterServiceId={selectedId}
                    linkedJobTypeIds={serviceJobTypeLinks.map(link => link.job_type_id)}
                    onAdded={() => { setShowAddJobType(false); serviceJobTypesApi.refetch(); notify("Job type added to this service."); }}
                    onError={(msg) => notify(msg, "error")}/>
                )}
              </div>

              <div role="tablist" aria-label="Blueprint setup sections" style={{ display: "flex", flexWrap: "wrap", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 12 }}>
                {WORKSPACE_TABS.map((t, index) => (
                  <button role="tab" aria-selected={tab === t.key} key={t.key} className={`cw-wtab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
                    <t.icon size={13}/> {index + 1}. {t.label}
                  </button>
                ))}
              </div>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px", lineHeight: 1.6 }}>
                {WORKSPACE_TABS.find(item => item.key === tab)?.help}
              </p>

              {tab === "overview" && (
                <OverviewTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId}
                  serviceName={safeText(services.find(s => s.service_id === selectedId)?.service_name, "Service")}
                  jobTypeLink={serviceJobTypeLinks.find(l => l.job_type_id === selectedJobTypeId) ?? null}
                  readiness={readinessApi.data} draft={draftApi.data}/>
              )}
              {tab === "dimensions" && (
                <DimensionsTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId} canWrite={canWrite}
                  notify={notify} onChanged={() => { readinessApi.refetch(); draftApi.refetch(); }}/>
              )}
              {tab === "problems" && (
                <ProblemsQuestionsTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId} canWrite={canWrite}
                  notify={notify} onChanged={() => { readinessApi.refetch(); draftApi.refetch(); }}/>
              )}

              {tab === "checklist" && (
                <ChecklistTab masterServiceJobTypeId={serviceJobTypeLinks.find(l => l.job_type_id === selectedJobTypeId)?.id ?? null}
                  canWrite={canWrite} notify={notify} onChanged={() => { readinessApi.refetch(); draftApi.refetch(); }}/>
              )}
              {tab === "workflow" && (
                <WorkflowTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId} canWrite={canWrite}
                  notify={notify} onChanged={() => { readinessApi.refetch(); draftApi.refetch(); }}/>
              )}
              {tab === "preview" && (
                <>
                  <PreviewTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId}/>
                  <section aria-label="Publishing checklist" style={{ marginTop: 18, padding: 16, border: "1px solid var(--border)", borderRadius: 10 }}>
                    <h3 style={{ margin: "0 0 10px", fontSize: 14 }}>How to finish and publish</h3>
                    <ol style={{ paddingLeft: 20, fontSize: 12, lineHeight: 1.8 }}>
                      <li>Confirm each section has saved successfully. Most settings save individually; they are not held for one final release.</li>
                      <li>In Workflow, save the journey and check its audience warnings. Existing jobs keep their recorded journey version.</li>
                      <li>If a checklist is needed, publish its library version and map that version in Checklist.</li>
                      <li>Finish these checks for every active job type, then publish the reviewed blueprint below. The server validates workflows and checklist mappings and records the configuration in one service-wide release version.</li>
                      <li>Providers must still configure their prices and meet their own setup/approval requirements.</li>
                    </ol>
                    <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>This creates a validated release record, not an atomic go-live switch: individual settings still take effect when saved. Existing jobs retain their workflow snapshot. Readiness is not a substitute for testing a booking.</p>
                    {publishAction.error && <div role="alert"><p>{publishAction.error}</p>{Array.isArray(publishAction.context?.blockers) && <ul>{publishAction.context.blockers.map((blocker, i) => <li key={i}>{String(blocker)}</li>)}</ul>}</div>}
                    {draftApi.loading ? <p>Loading blueprint publication status…</p> : draftApi.error ? <SectionError title="Could not load publication status" error={draftApi.error} onRetry={draftApi.refetch}/> : draftApi.data && <>
                      <p style={{ fontSize: 12 }}>Published blueprint: {draftApi.data.current_published_version == null ? "None" : `v${draftApi.data.current_published_version}`} · {draftApi.data.has_pending_changes ? `${draftApi.data.pending_change_count} changed sections` : "No pending changes"}</p>
                      {canWrite && <Btn variant="primary" disabled={!draftApi.data.has_pending_changes || publishAction.loading} onClick={handlePublish}>{publishAction.loading ? "Publishing blueprint…" : "Publish reviewed blueprint"}</Btn>}
                    </>}
                  </section>
                </>
              )}
              {tab === "tenant_rules" && (
                <TenantSetupRulesTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId} canWrite={canWrite}
                  notify={notify} onChanged={() => { listApi.refetch(); readinessApi.refetch(); impactApi.refetch(); draftApi.refetch(); }}/>
              )}
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginTop: 22, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
                <Btn variant="secondary" disabled={tab === WORKSPACE_TABS[0].key} onClick={() => setTab(WORKSPACE_TABS[WORKSPACE_TABS.findIndex(item => item.key === tab) - 1].key)}>Previous section</Btn>
                {tab !== "preview" && <Btn variant="secondary" onClick={() => setTab(WORKSPACE_TABS[WORKSPACE_TABS.findIndex(item => item.key === tab) + 1].key)}>Next: {WORKSPACE_TABS[WORKSPACE_TABS.findIndex(item => item.key === tab) + 1]?.label}</Btn>}
              </div>
            </>
          )}
        </div>

        {/* ── Column 3: Readiness + Impact ─────────────────────────────────── */}
        <div className="cw-side" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="cw-panel" style={{ padding: 16 }}>
            <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>
              Blueprint Readiness
            </p>
            {!selectedId ? (
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Select a service to see readiness.</p>
            ) : readinessApi.error ? (
              <SectionError title="Couldn't load readiness" error={readinessApi.error} requestId={readinessApi.requestId} onRetry={readinessApi.refetch}/>
            ) : readinessApi.loading || !readinessApi.data ? (
              <Skeleton height={140}/>
            ) : (
              <ReadinessPanel r={readinessApi.data}/>
            )}
          </div>

          <div className="cw-panel" style={{ padding: 16 }}>
            <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>
              Last Publish Impact
            </p>
            {!selectedId ? (
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Select a service to see impact.</p>
            ) : impactApi.error ? (
              <SectionError title="Couldn't load impact report" error={impactApi.error} requestId={impactApi.requestId} onRetry={impactApi.refetch}/>
            ) : impactApi.loading || !impactApi.data ? (
              <Skeleton height={100}/>
            ) : (
              <ImpactPanel r={impactApi.data}/>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}

function ServiceRow({ s, active, onClick }: { s: HsConsoleService; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{ width: "100%", textAlign: "left", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid", cursor: "pointer", marginBottom: 3, fontFamily: "inherit",
      borderColor: active ? "var(--brand)" : "transparent", background: active ? "rgba(37,99,235,0.08)" : "transparent" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: active ? 700 : 500, color: active ? "var(--brand)" : "var(--text-primary)" }}>{s.service_name}</span>
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: s.is_active ? "var(--success)" : "var(--border)", flexShrink: 0 }}/>
      </div>
    </button>
  );
}

// ── Readiness panel ───────────────────────────────────────────────────────────
function ReadinessPanel({ r }: { r: BlueprintReadiness }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color: r.ready ? "var(--success-text)" : "var(--text-primary)" }}>{r.percent}%</span>
        <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
          background: r.ready ? "var(--success-bg)" : "var(--warning-bg, var(--surface-sunken))",
          color: r.ready ? "var(--success-text)" : "var(--warning-text, var(--text-secondary))" }}>
          {r.ready ? "Ready to publish" : "Needs attention"}
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
        {r.checks.map(c => (
          <div key={c.key} style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "7px 9px", background: "var(--surface-sunken)", borderRadius: 8 }}>
            {c.passed ? <CheckCircle2 size={14} style={{ color: "var(--success-text)", flexShrink: 0, marginTop: 1 }}/> : <CircleDot size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: 1 }}/>}
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{c.label}</p>
              {c.detail && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{c.detail}</p>}
            </div>
          </div>
        ))}
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        {r.tenant_setups_affected} tenant setup{r.tenant_setups_affected === 1 ? "" : "s"} using this blueprint.
      </p>
    </div>
  );
}

// ── Impact panel — honest about the draft-model gap ──────────────────────────
function ImpactPanel({ r }: { r: BlueprintImpactReport }) {
  if (r.current_version === null) {
    return <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No blueprint version published yet.</p>;
  }
  const hasChanges = r.changed_requirements.length > 0 || r.added_dimensions.length > 0 || r.removed_dimensions.length > 0;
  return (
    <div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
        v{r.previous_version ?? "—"} → v{r.current_version}
        {r.last_published_at && ` · ${new Date(r.last_published_at).toLocaleDateString("en-IN", { dateStyle: "medium" })}`}
      </p>
      {!hasChanges ? (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 10px" }}>No structural change on the last publish.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
          {r.changed_requirements.map(c => (
            <div key={c.field} style={{ fontSize: 12, color: "var(--text-primary)", padding: "6px 9px", background: "var(--surface-sunken)", borderRadius: 8 }}>
              <strong>{c.label}</strong>: {String(c.from)} → {String(c.to)}
            </div>
          ))}
          {r.added_dimensions.map(d => (
            <div key={`add-${d}`} style={{ fontSize: 12, color: "var(--success-text)", padding: "6px 9px", background: "var(--success-bg)", borderRadius: 8 }}>+ {d} dimension added</div>
          ))}
          {r.removed_dimensions.map(d => (
            <div key={`rm-${d}`} style={{ fontSize: 12, color: "var(--danger-text)", padding: "6px 9px", background: "var(--danger-bg)", borderRadius: 8 }}>− {d} dimension removed</div>
          ))}
        </div>
      )}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-secondary)", marginBottom: 10 }}>
        <span>{r.tenants_affected} tenant setup(s)</span>
        <span>{r.setups_need_review} need review</span>
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        This shows what the last <em>publish</em> changed. Structural edits since then show as "Draft changes" above the job-type tabs until published.
      </p>
    </div>
  );
}

// ── Dimensions tab (the grid) ─────────────────────────────────────────────────
const PRICING_BEHAVIOR_OPTIONS = [
  { value: "fixed", label: "Fixed price (tenant sets the amount)" },
  { value: "range", label: "Price range (tenant sets min/max)" },
  { value: "inspection_required", label: "Inspection required (visit fee, quote after)" },
  { value: "custom_quote", label: "Custom quote (no upfront price)" },
] as const;
const WORKFLOW_FLAGS: { key: keyof ServiceJobWorkflow; label: string }[] = [
  { key: "inspection_required", label: "Inspection required" },
  { key: "quote_approval_required", label: "Quote approval required" },
  { key: "checklist_required", label: "Checklist required" },
  { key: "schedule_required", label: "Schedule required" },
  { key: "address_required", label: "Address required" },
  { key: "technician_required", label: "Technician required" },
  { key: "service_area_required", label: "Service area required" },
  { key: "availability_required", label: "Availability required" },
];

// ── Overview tab -- job-type identity, status and readiness ONLY. No
// Brand/Type/Issue/Checklist-required toggles and no price fields here --
// those live in Dimensions, Problems & Questions, Checklist and tenant
// pricing respectively. This tab used to hold the full ServiceJobWorkflow
// flag set; that content moved to the dedicated Workflow tab below. ───────
function OverviewTab({ jobTypeId, serviceName, jobTypeLink, readiness, draft }: {
  masterServiceId: string; jobTypeId: string | null; serviceName: string;
  jobTypeLink: { job_type: CatalogJobType } | null;
  readiness: BlueprintReadiness | null | undefined; draft: BlueprintDraftStatus | null | undefined;
}) {
  if (!jobTypeId) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-tertiary)" }}>
        <ClipboardList size={28} style={{ opacity: 0.3, marginBottom: 10 }}/>
        <p style={{ fontSize: 13, margin: 0 }}>Select a specific job type above to view its blueprint overview.</p>
      </div>
    );
  }
  const jt = jobTypeLink?.job_type;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Home Services</span><ChevronRight size={12}/>
        <span>{serviceName}</span><ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{jt?.label ?? "Job Type"}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10 }}>
        <InfoTile label="Job Type" value={jt?.label ?? "—"}/>
        <InfoTile label="Key" value={jt?.key ?? "—"}/>
        <InfoTile label="Status" value={jt?.is_active ? "Active" : "Inactive"}/>
        <InfoTile label="Current Published" value={draft?.current_published_version != null ? `v${draft.current_published_version}` : "None yet"}/>
        <InfoTile label="Draft" value={draft?.has_pending_changes ? `${draft.pending_change_count} pending change(s)` : "No pending changes"}/>
      </div>
      {jt?.description && (
        <div>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 6px" }}>Customer-facing description</p>
          <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0 }}>{jt.description}</p>
        </div>
      )}
      <div>
        <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 8px" }}>Readiness</p>
        {readiness ? <ReadinessPanel r={readiness}/> : <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Loading…</p>}
      </div>
    </div>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ padding: "10px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 4px" }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{value}</p>
    </div>
  );
}

// ── Workflow tab -- Job-Type Blueprint workflow ownership (migration 160):
// inspection/quote-approval/checklist/schedule/address/technician/service-
// area/availability requirements + permitted pricing BEHAVIOR (never an
// amount). Reuses the existing ServiceJobWorkflow model and the canonical
// execution transition graph -- no second state machine. ──────────────────
function WorkflowTab({ masterServiceId, jobTypeId, canWrite, notify, onChanged }: {
  masterServiceId: string; jobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const linksApi = useApi(
    useCallback(() => catalogWorkspaceApi.listServiceJobTypes(masterServiceId), [masterServiceId]),
    [masterServiceId],
  );
  const workflowApi = useApi(
    useCallback(() => jobTypeId ? catalogWorkspaceApi.getJobTypeWorkflow(masterServiceId, jobTypeId) : Promise.resolve(null as unknown as ServiceJobWorkflow),
      [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId], { enabled: !!jobTypeId },
  );
  const addLinkAction = useAction(catalogWorkspaceApi.addServiceJobType);
  const setWorkflowAction = useAction(catalogWorkspaceApi.setJobTypeWorkflow);

  if (!jobTypeId) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-tertiary)" }}>
        <ClipboardList size={28} style={{ opacity: 0.3, marginBottom: 10 }}/>
        <p style={{ fontSize: 13, margin: 0 }}>Select a specific job type above to configure its workflow blueprint.</p>
      </div>
    );
  }

  const isAdded = (linksApi.data?.items ?? []).some(l => l.job_type_id === jobTypeId && l.is_active);

  async function addToService() {
    if (!jobTypeId) return;
    const result = await addLinkAction.execute(masterServiceId, jobTypeId);
    if (result) { linksApi.refetch(); notify("Job type added to this service."); }
    else notify("Couldn't add job type to this service.", "error");
  }

  async function toggle(flag: keyof ServiceJobWorkflow) {
    if (!canWrite || !workflowApi.data || !jobTypeId) return;
    const result = await setWorkflowAction.execute(masterServiceId, jobTypeId, { [flag]: !workflowApi.data[flag] });
    if (result) { workflowApi.refetch(); onChanged(); }
    else notify("Couldn't update workflow.", "error");
  }

  async function setPricingBehavior(behavior: ServiceJobWorkflow["pricing_behavior"]) {
    if (!canWrite || !jobTypeId) return;
    const result = await setWorkflowAction.execute(masterServiceId, jobTypeId, { pricing_behavior: behavior });
    if (result) { workflowApi.refetch(); onChanged(); notify("Pricing behavior updated."); }
    else notify("Couldn't update pricing behavior.", "error");
  }

  return (
    <div>
      {!isAdded && !linksApi.loading && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", marginBottom: 14, borderRadius: "var(--radius-md)", background: "var(--warning-bg, var(--surface-sunken))", border: "1px solid var(--border)" }}>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
            This job type isn't added to this service yet — its workflow can still be previewed below.
          </p>
          {canWrite && (
            <button onClick={addToService} disabled={addLinkAction.loading}
              style={{ fontSize: 12, fontWeight: 700, padding: "6px 12px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white", cursor: "pointer", flexShrink: 0 }}>
              Add to Service
            </button>
          )}
        </div>
      )}

      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>
        Workflow requirements for this job type. Never an amount — the tenant sets actual prices in Tenant Setup.
      </p>

      {workflowApi.error ? (
        <SectionError title="Couldn't load workflow" error={workflowApi.error} requestId={workflowApi.requestId} onRetry={workflowApi.refetch}/>
      ) : workflowApi.loading || !workflowApi.data ? (
        <Skeleton height={220}/>
      ) : (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 18 }}>
            {WORKFLOW_FLAGS.map(f => (
              <div key={f.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{f.label}</span>
                <FlagPill on={!!workflowApi.data![f.key]} onClick={() => toggle(f.key)} disabled={!canWrite || setWorkflowAction.loading}/>
              </div>
            ))}
          </div>

          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 8px" }}>
            Permitted Pricing Behavior
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {PRICING_BEHAVIOR_OPTIONS.map(opt => (
              <label key={opt.value} style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: `1px solid ${workflowApi.data!.pricing_behavior === opt.value ? "var(--brand)" : "var(--border)"}`, cursor: canWrite ? "pointer" : "default" }}>
                <input type="radio" name="pricing_behavior" checked={workflowApi.data!.pricing_behavior === opt.value}
                  disabled={!canWrite || setWorkflowAction.loading}
                  onChange={() => setPricingBehavior(opt.value)}/>
                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{opt.label}</span>
              </label>
            ))}
          </div>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
            This is a permission, not a price. The tenant enters the actual fixed amount, range, or visit fee in Tenant Setup.
          </p>

          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "18px 0 8px" }}>
            Allowed Job Status Transitions (reference)
          </p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px" }}>
            Read-only — this is the same execution transition graph and Work Start Approval Gate enforced by the
            backend (app/engines/execution). It is not editable here and this tab does not implement a second
            state machine.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
            {["assigned", "accepted", "scheduled", "on_the_way", "reached_site", "inspection_started", "inspection_done",
              "service_started", "work_done", "completed"].map((s, i, arr) => (
              <React.Fragment key={s}>
                <span style={{ fontSize: 11, padding: "3px 9px", borderRadius: 999, background: "var(--surface-sunken)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>{s}</span>
                {i < arr.length - 1 && <ChevronRight size={11} style={{ color: "var(--text-tertiary)" }}/>}
              </React.Fragment>
            ))}
          </div>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Side branches: quote_required, customer_not_available, cancelled. Work start additionally requires an
            approved current estimate whenever this job type's quote approval requirement is on.
          </p>

          {/* Cross-app journey (migration 274). The graph above is the platform's
              fixed status vocabulary; this is the per-job-type sequence built on
              top of it — which app owns each stage, who acts, and who sees it. */}
          <WorkflowStepBuilder
            masterServiceId={masterServiceId} jobTypeId={jobTypeId}
            workflow={workflowApi.data!} canWrite={canWrite} notify={notify}
            onSaved={() => { workflowApi.refetch(); onChanged(); }}
          />
        </>
      )}
    </div>
  );
}

function DimensionsTab({ masterServiceId, jobTypeId, canWrite, notify, onChanged }: {
  masterServiceId: string; jobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const gridApi = useApi(
    useCallback(() => catalogWorkspaceApi.getDimensionGrid(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId],
  );
  const setFlag = useAction(catalogWorkspaceApi.setDimensionConfig);
  const deleteDimensionAction = useAction(catalogWorkspaceApi.deleteDimension);
  const rows = gridApi.data?.dimensions ?? [];
  const [showAddDimension, setShowAddDimension] = useState(false);
  const [expandedValuesFor, setExpandedValuesFor] = useState<string | null>(null);

  async function toggle(row: DimensionGridRow, flag: keyof DimensionGridRow["config"]) {
    if (!canWrite) return;
    const result = await setFlag.execute(masterServiceId, jobTypeId, row.dimension.id, { [flag]: !row.config[flag] });
    if (result) {
      notify(`${row.dimension.name} updated.`);
      gridApi.refetch(); onChanged();
    } else {
      notify("Couldn't update dimension.", "error");
    }
  }

  async function handleDeleteDimension(row: DimensionGridRow) {
    if (!canWrite) return;
    if (!window.confirm(`Delete the "${row.dimension.name}" dimension? It stops being offered on every service that uses it.`)) return;
    const result = await deleteDimensionAction.execute(row.dimension.id);
    if (result) { gridApi.refetch(); onChanged(); notify(`"${row.dimension.name}" deleted.`); }
    else notify(deleteDimensionAction.error ?? "Couldn't delete this dimension.", "error");
  }

  if (gridApi.error) return <SectionError title="Couldn't load dimensions" error={gridApi.error} requestId={gridApi.requestId} onRetry={gridApi.refetch}/>;
  if (gridApi.loading) return <Skeleton height={220}/>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 12 }}>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
          Every generic dimension (Type, Brand, and any admin-defined custom attribute) as it applies to this
          service{jobTypeId ? " and job type" : ""}. No monetary fields are configured here.
        </p>
        {canWrite && (
          <button onClick={() => setShowAddDimension(v => !v)} style={{ fontSize: 12, fontWeight: 600, padding: "6px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
            <Plus size={13}/> Add Dimension
          </button>
        )}
      </div>
      {showAddDimension && (
        <AddDimensionForm onAdded={() => { setShowAddDimension(false); gridApi.refetch(); notify("Dimension created."); }}
          onError={(msg) => notify(msg, "error")}/>
      )}
      <div style={{ overflowX: "auto" }}>
        <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
              {["Dimension", "Values", "Enabled", "Required", "Ask Customer", "Affects Price", ""].map(h => (
                <th key={h} style={{ padding: "8px 10px", textAlign: "left", fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <React.Fragment key={row.dimension.id}>
                <tr style={{ borderBottom: expandedValuesFor === row.dimension.id ? "none" : "1px solid var(--border)" }}>
                  <td style={{ padding: "9px 10px", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                    {row.dimension.name}
                    {row.dimension.legacy_source && <span style={{ fontSize: 10, color: "var(--text-tertiary)", marginLeft: 6 }}>(legacy)</span>}
                  </td>
                  <td style={{ padding: "9px 10px", fontSize: 12, color: "var(--text-secondary)" }}>{row.value_count}</td>
                  <td style={{ padding: "9px 10px" }}><FlagPill on={row.config.enabled} onClick={() => toggle(row, "enabled")} disabled={!canWrite}/></td>
                  <td style={{ padding: "9px 10px" }}><FlagPill on={row.config.required} onClick={() => toggle(row, "required")} disabled={!canWrite}/></td>
                  <td style={{ padding: "9px 10px" }}><FlagPill on={row.config.ask_customer} onClick={() => toggle(row, "ask_customer")} disabled={!canWrite}/></td>
                  <td style={{ padding: "9px 10px" }}><FlagPill on={row.config.affects_price} onClick={() => toggle(row, "affects_price")} disabled={!canWrite}/></td>
                  <td style={{ padding: "9px 10px", whiteSpace: "nowrap" }}>
                    <button onClick={() => setExpandedValuesFor(expandedValuesFor === row.dimension.id ? null : row.dimension.id)}
                      style={{ fontSize: 11, fontWeight: 600, color: "var(--brand)", background: "none", border: "none", cursor: "pointer", whiteSpace: "nowrap" }}>
                      {expandedValuesFor === row.dimension.id ? "Hide" : "Manage values"}
                    </button>
                    {canWrite && !row.dimension.legacy_source && (
                      <button onClick={() => handleDeleteDimension(row)} disabled={deleteDimensionAction.loading}
                        aria-label={`Delete ${row.dimension.name} dimension`} title={`Delete ${row.dimension.name} dimension`}
                        style={{ marginLeft: 8, display: "inline-flex", padding: 3, borderRadius: "50%", border: "none", background: "none", color: "var(--danger-text)", cursor: deleteDimensionAction.loading ? "default" : "pointer", verticalAlign: "middle" }}>
                        <Trash2 size={13}/>
                      </button>
                    )}
                  </td>
                </tr>
                {expandedValuesFor === row.dimension.id && (
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <td colSpan={7} style={{ padding: "0 10px 12px" }}>
                      <DimensionValuesPanel dimension={row.dimension} masterServiceId={masterServiceId} canWrite={canWrite}
                        onChanged={() => { gridApi.refetch(); onChanged(); }} notify={notify}/>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={7} style={{ padding: 16, textAlign: "center", fontSize: 12, color: "var(--text-tertiary)" }}>No dimensions defined yet.</td></tr>
            )}
          </tbody>
        </TableSurface>
      </div>
    </div>
  );
}

const DIMENSION_DATA_TYPES = ["single_select", "multi_select", "boolean", "number", "text"] as const;

// ── Add Job Type to this service -- two modes: attach an existing global
// job type (the common case: Repair/Installation/... already exist, this
// service just needs them as a master_service_job_types child record), or
// define a brand-new platform-wide job type (rare) and auto-attach it here
// so it doesn't just vanish into the global catalog with no visible effect.

function AddDimensionForm({ onAdded, onError }: { onAdded: () => void; onError: (msg: string) => void }) {
  const [name, setName] = useState("");
  const [dataType, setDataType] = useState<typeof DIMENSION_DATA_TYPES[number]>("single_select");
  const createAction = useAction(catalogWorkspaceApi.createDimension);

  async function submit() {
    const key = slugifyKey(name);
    if (!name.trim() || !key) return;
    const result = await createAction.execute({ key, name: name.trim(), data_type: dataType });
    if (result) { setName(""); onAdded(); }
    else onError(createAction.error ?? "Couldn't create dimension.");
  }

  return (
    <div style={{ marginBottom: 14, padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
      <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>
        Dimension name
        <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Fuel Type"
          style={{ display: "block", marginTop: 4, fontSize: 13, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", minWidth: 200 }}/>
      </label>
      <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>
        Data type
        <select value={dataType} onChange={e => setDataType(e.target.value as typeof dataType)}
          style={{ display: "block", marginTop: 4, fontSize: 12, padding: "5px 7px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
          {DIMENSION_DATA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </label>
      <button onClick={submit} disabled={!name.trim() || createAction.loading}
        style={{ fontSize: 12, fontWeight: 600, padding: "7px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white",
          cursor: !name.trim() || createAction.loading ? "default" : "pointer", opacity: !name.trim() || createAction.loading ? 0.6 : 1 }}>
        {createAction.loading ? "Creating…" : "Create"}
      </button>
    </div>
  );
}

function DimensionValuesPanel({ dimension, masterServiceId, canWrite, onChanged, notify }: {
  dimension: CatalogDimensionDef; masterServiceId: string; canWrite: boolean;
  onChanged: () => void; notify: (m: string, t?: "success" | "error") => void;
}) {
  const valuesApi = useApi(useCallback(
    () => dimension.legacy_source ? Promise.resolve({ dimension, legacy: true, values: [] }) : catalogWorkspaceApi.listDimensionValues(dimension.id),
    [dimension.id, dimension.legacy_source]), [dimension.id, dimension.legacy_source]);
  const addAction = useAction(catalogWorkspaceApi.addDimensionValue);
  const deleteValueAction = useAction(catalogWorkspaceApi.deleteDimensionValue);
  const [label, setLabel] = useState("");
  const isLegacy = !!dimension.legacy_source;
  const values = valuesApi.data?.values ?? [];

  async function handleDeleteValue(v: CatalogDimensionValueItem) {
    if (!canWrite) return;
    if (!window.confirm(`Delete "${v.label}" from ${dimension.name}? Any tenant currently using this value keeps their existing selection, but it will no longer be offered.`)) return;
    const result = await deleteValueAction.execute(dimension.id, v.id);
    if (result) { valuesApi.refetch(); onChanged(); notify(`"${v.label}" deleted.`); }
    else notify(deleteValueAction.error ?? "Couldn't delete this value.", "error");
  }
  const exactValues = useApi(useCallback(async () => {
    if (dimension.legacy_source === "brands") {
      const [library, mapped] = await Promise.all([
        catalogApi.listBrands({ status: "active", page: 1, page_size: 200, masterServiceId }),
        catalogApi.listBrandMappings(masterServiceId),
      ]);
      return {
        options: library.brands.map(row => ({ id: row.brand_id, label: row.display_name || row.name })),
        mapped: mapped.brands.map(row => ({ id: row.brand_id, mappingId: row.mapping_id })),
      };
    }
    if (dimension.legacy_source === "service_types") {
      const [library, mapped] = await Promise.all([
        catalogApi.listServiceTypes(undefined, masterServiceId), catalogApi.listServiceTypeMappings(masterServiceId),
      ]);
      return {
        options: library.types.filter(row => row.is_active).map(row => ({ id: row.type_id, label: row.name })),
        mapped: mapped.types.map(row => ({ id: row.service_type_id, mappingId: row.mapping_id })),
      };
    }
    return { options: [] as { id: string; label: string }[], mapped: [] as { id: string; mappingId: string }[] };
  }, [dimension.legacy_source, masterServiceId]), [dimension.legacy_source, masterServiceId], { enabled: isLegacy });
  const toggleLegacy = useAction(useCallback(async (id: string, mappingId?: string) => {
    if (dimension.legacy_source === "brands") {
      if (mappingId) await catalogApi.unmapBrand(masterServiceId, mappingId);
      else await catalogApi.mapBrand(masterServiceId, id);
    } else if (dimension.legacy_source === "service_types") {
      if (mappingId) await catalogApi.unmapServiceType(masterServiceId, mappingId);
      else await catalogApi.mapServiceType(masterServiceId, id);
    }
    await exactValues.refetch();
    onChanged();
  }, [dimension.legacy_source, masterServiceId, exactValues, onChanged]));

  async function addValue() {
    const code = slugifyKey(label);
    if (!label.trim() || !code) return;
    const result = await addAction.execute(dimension.id, { code, label: label.trim() });
    if (result) { setLabel(""); valuesApi.refetch(); onChanged(); notify("Value added."); }
    else notify("Couldn't add value.", "error");
  }

  if (valuesApi.error || exactValues.error) return <SectionError title="Couldn't load values" error={valuesApi.error || exactValues.error || "Unknown error"} requestId={valuesApi.requestId || exactValues.requestId} onRetry={() => { valuesApi.refetch(); exactValues.refetch(); }}/>;
  if (valuesApi.loading || (isLegacy && exactValues.loading)) return <Skeleton height={60}/>;

  return (
    <div style={{ padding: 10, borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)" }}>
      {isLegacy ? (
        <div style={{ display: "grid", gap: 10 }}>
          <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0 }}>
            Select the {dimension.name.toLowerCase()} values supported by this service. These exact choices are what providers receive during setup; the setting applies to every job type under this service where the dimension is enabled.
          </p>
          {toggleLegacy.error && <p role="alert" style={{ color: "var(--danger-text)", margin: 0, fontSize: 12 }}>{toggleLegacy.error}</p>}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {(exactValues.data?.options ?? []).map(option => {
              const mapped = exactValues.data?.mapped.find(row => row.id === option.id);
              return <label key={option.id} style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 9px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12, cursor: canWrite ? "pointer" : "default" }}>
                <input type="checkbox" checked={!!mapped} disabled={!canWrite || toggleLegacy.loading}
                  onChange={() => toggleLegacy.execute(option.id, mapped?.mappingId)}/>
                {option.label}
              </label>;
            })}
            {(exactValues.data?.options ?? []).length === 0 && <span style={{ fontSize: 12, color: "var(--warning-text)" }}>No active {dimension.name.toLowerCase()} values exist. Create them in Types & Brands first.</span>}
          </div>
          <Link href={`/admin/types-brands?tab=${dimension.legacy_source === "brands" ? "brands" : "types"}`} style={{ fontSize: 12 }}>
            Open the {dimension.name} library
          </Link>
        </div>
      ) : (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {values.map(v => (
              <span key={v.id} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, padding: "3px 4px 3px 9px", borderRadius: 999, background: "var(--surface-sunken)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                {v.label}
                {canWrite && (
                  <button onClick={() => handleDeleteValue(v)} disabled={deleteValueAction.loading} aria-label={`Delete ${v.label}`} title={`Delete ${v.label}`}
                    style={{ display: "flex", padding: 3, borderRadius: "50%", border: "none", background: "transparent", color: "var(--danger-text)", cursor: deleteValueAction.loading ? "default" : "pointer" }}>
                    <Trash2 size={11}/>
                  </button>
                )}
              </span>
            ))}
            {values.length === 0 && <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>No values yet.</span>}
          </div>
          {canWrite && (
            <div style={{ display: "flex", gap: 6 }}>
              <input value={label} onChange={e => setLabel(e.target.value)} placeholder="New value name" aria-label="New value name"
                style={{ fontSize: 12, padding: "5px 8px", borderRadius: 7, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", minWidth: 160 }}/>
              <button onClick={addValue} disabled={!label.trim() || addAction.loading}
                style={{ fontSize: 11, fontWeight: 600, padding: "5px 10px", borderRadius: 7, border: "none", background: "var(--brand)", color: "white",
                  cursor: !label.trim() || addAction.loading ? "default" : "pointer" }}>
                + Add
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FlagPill({ on, onClick, disabled }: { on: boolean; onClick: () => void; disabled?: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{ fontSize: 10, fontWeight: 700, padding: "2px 10px", borderRadius: 999, border: "none",
      cursor: disabled ? "default" : "pointer", opacity: disabled ? 0.6 : 1,
      background: on ? "var(--success-bg)" : "var(--surface-sunken)", color: on ? "var(--success-text)" : "var(--text-tertiary)" }}>
      {on ? "Yes" : "No"}
    </button>
  );
}

// ── Problems & Questions tab ──────────────────────────────────────────────────
function ProblemsQuestionsTab({ masterServiceId, jobTypeId, canWrite, notify, onChanged }: {
  masterServiceId: string; jobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const [sub, setSub] = useState<"problems" | "questions">("problems");
  return (
    <div>
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {(["problems", "questions"] as const).map(k => (
          <button key={k} onClick={() => setSub(k)} style={{ padding: "6px 12px", fontSize: 12, fontWeight: 600, borderRadius: 999,
            border: "1px solid var(--border)", cursor: "pointer",
            background: sub === k ? "var(--brand)" : "var(--surface-sunken)", color: sub === k ? "white" : "var(--text-secondary)" }}>
            {k === "problems" ? "Problems" : "Questions"}
          </button>
        ))}
      </div>
      {sub === "problems"
        ? <ProblemsSubTab masterServiceId={masterServiceId} jobTypeId={jobTypeId} canWrite={canWrite} notify={notify} onChanged={onChanged}/>
        : <QuestionsSubTab masterServiceId={masterServiceId} jobTypeId={jobTypeId} canWrite={canWrite} notify={notify} onChanged={onChanged}/>}
    </div>
  );
}

function ProblemsSubTab({ masterServiceId, jobTypeId, canWrite, notify, onChanged }: {
  masterServiceId: string; jobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const issuesApi = useApi(
    useCallback(() => catalogWorkspaceApi.listServiceIssues(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId],
  );
  const removeAction = useAction(catalogWorkspaceApi.removeServiceIssue);
  const issues = issuesApi.data?.issues ?? [];
  const [showAdd, setShowAdd] = useState(false);

  async function handleRemove(m: CatalogIssueTypeMapping) {
    if (!canWrite) return;
    const result = await removeAction.execute(masterServiceId, m.mapping_id);
    if (result) {
      notify(`${m.name} removed from this service.`);
      issuesApi.refetch(); onChanged();
    } else {
      notify("Couldn't remove this problem.", "error");
    }
  }

  if (issuesApi.error) return <SectionError title="Couldn't load problems" error={issuesApi.error} requestId={issuesApi.requestId} onRetry={issuesApi.refetch}/>;
  if (issuesApi.loading) return <Skeleton height={140}/>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 12 }}>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
          Customer-facing problems mapped to this service{jobTypeId ? " (this job type + service-wide problems)" : ""}.
        </p>
        {canWrite && (
          <button onClick={() => setShowAdd(v => !v)} style={{ fontSize: 12, fontWeight: 600, padding: "6px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
            <Plus size={13}/> Add Problem
          </button>
        )}
      </div>
      {showAdd && (
        <AddProblemPicker masterServiceId={masterServiceId} jobTypeId={jobTypeId} existingIssueIds={issues.map(i => i.issue_type_id)}
          onAdded={() => { setShowAdd(false); issuesApi.refetch(); onChanged(); notify("Problem added to this service."); }}
          onError={() => notify("Couldn't add this problem.", "error")}/>
      )}
      {issues.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No problems mapped to this service yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {issues.map(i => (
            <div key={i.mapping_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {i.issue_type?.icon_url && (
                  <img src={i.issue_type.icon_url} alt="" style={{ width: 32, height: 32, borderRadius: 8, objectFit: "cover", border: "1px solid var(--border)" }}/>
                )}
                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{i.name}</span>
                {i.is_common && <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 7px", borderRadius: 999, background: "var(--brand)", color: "white" }}>Common</span>}
                {i.is_default && <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 7px", borderRadius: 999, background: "var(--surface)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>Default</span>}
              </div>
              {canWrite && (
                <button onClick={() => handleRemove(i)} style={{ fontSize: 11, fontWeight: 600, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer" }}>
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Add Problem picker — searches the platform-wide issue-type catalog and
// attaches an existing one to this service (job-type scoped if a tab is
// active); it never creates a new global issue type here, that stays in
// Service Options & Issue Types to avoid duplicating that CRUD surface. ─────
function AddProblemPicker({ masterServiceId, jobTypeId, existingIssueIds, onAdded, onError }: {
  masterServiceId: string; jobTypeId: string | null; existingIssueIds: string[];
  onAdded: () => void; onError: () => void;
}) {
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCode, setNewCode] = useState("");
  const [newIconUrl, setNewIconUrl] = useState<string | null>(null);
  const [newInstagramImageUrl, setNewInstagramImageUrl] = useState<string | null>(null);
  const searchApi = useApi(
    useCallback(() => catalogWorkspaceApi.listIssueTypesV2({ search: search.trim() || undefined }), [search]),
    [search],
  );
  const addAction = useAction(catalogWorkspaceApi.addServiceIssue);
  const createAction = useAction(catalogWorkspaceApi.createIssueType);
  const results = (searchApi.data?.items ?? []).filter(
    it => !existingIssueIds.includes(String(it.id))) as { id: string; name: string; code: string }[];

  async function attach(issueTypeId: string) {
    const result = await addAction.execute(masterServiceId, { issue_type_id: issueTypeId, job_type_id: jobTypeId });
    if (result) onAdded(); else onError();
  }

  async function createAndAttach() {
    if (!newName.trim()) return;
    const code = (newCode.trim() || newName.trim()).toUpperCase().replace(/[^A-Z0-9]+/g, "_").slice(0, 60);
    const created = await createAction.execute({
      name: newName.trim(), code, master_service_id: masterServiceId,
      icon_url: newIconUrl, image_url: newInstagramImageUrl,
    });
    if (!created) { onError(); return; }
    const issueId = String((created as { id?: string }).id ?? "");
    if (!issueId) { onError(); return; }
    const attached = await addAction.execute(masterServiceId, { issue_type_id: issueId, job_type_id: jobTypeId });
    if (attached) {
      setNewName(""); setNewCode(""); setNewIconUrl(null); setNewInstagramImageUrl(null);
      setShowCreate(false); onAdded();
    } else onError();
  }

  return (
    <div style={{ marginBottom: 14, padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <Search size={13} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search the problem catalog…"
          aria-label="Search problems"
          style={{ flex: 1, fontSize: 13, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}/>
      </div>
      {searchApi.error ? (
        <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{searchApi.error}</p>
      ) : searchApi.loading ? (
        <Skeleton height={60}/>
      ) : results.length === 0 ? (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          No matching problems{existingIssueIds.length > 0 ? " (already-mapped problems are hidden)" : ""}.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 180, overflowY: "auto" }}>
          {results.map(it => (
            <button key={it.id} onClick={() => attach(it.id)} disabled={addAction.loading}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 9px", borderRadius: 7, border: "1px solid var(--border)", background: "var(--surface)", cursor: addAction.loading ? "default" : "pointer", textAlign: "left" }}>
              <span style={{ fontSize: 12, color: "var(--text-primary)" }}>{it.name}</span>
              <Plus size={13} style={{ color: "var(--brand)", flexShrink: 0 }}/>
            </button>
          ))}
        </div>
      )}

      {showCreate ? (
        <div style={{ marginTop: 10, padding: 10, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)" }}>
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="New problem name"
            style={{ width: "100%", fontSize: 12, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", marginBottom: 6, boxSizing: "border-box" }}/>
          <input value={newCode} onChange={e => setNewCode(e.target.value)} placeholder="Code (optional, auto-generated from name)"
            style={{ width: "100%", fontSize: 12, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", marginBottom: 8, boxSizing: "border-box" }}/>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 10, marginBottom: 10 }}>
            <div>
              <IconPicker label="Fuvay app icon" noun="problem app icon" context="issue_type_image" value={newIconUrl} onChange={setNewIconUrl}/>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "5px 0 0" }}>Used in the app and catalog lists.</p>
            </div>
            <div>
              <IconPicker label="Instagram card image" noun="Instagram problem image" context="instagram_card_image" value={newInstagramImageUrl} onChange={setNewInstagramImageUrl}/>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "5px 0 0" }}>Public HTTPS artwork; falls back to the app icon.</p>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button onClick={createAndAttach} disabled={!newName.trim() || createAction.loading || addAction.loading}
              style={{ fontSize: 12, padding: "5px 10px", borderRadius: 6, border: "1px solid var(--brand)", background: "var(--brand)", color: "#fff", cursor: "pointer" }}>
              {createAction.loading || addAction.loading ? "Creating…" : "Create & Attach"}
            </button>
            <button onClick={() => setShowCreate(false)}
              style={{ fontSize: 12, padding: "5px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-secondary)", cursor: "pointer" }}>
              Cancel
            </button>
          </div>
          {createAction.error && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: "6px 0 0" }}>{createAction.error}</p>}
        </div>
      ) : (
        <button onClick={() => setShowCreate(true)}
          style={{ marginTop: 8, fontSize: 12, color: "var(--brand)", background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex", alignItems: "center", gap: 4 }}>
          <Plus size={12}/> New problem not in the catalog? Create one here
        </button>
      )}
    </div>
  );
}

function ChecklistTab({ masterServiceJobTypeId, canWrite, notify, onChanged }: {
  masterServiceJobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const mappingsApi = useApi(useCallback(
    () => masterServiceJobTypeId
      ? checklistCatalogApi.listMappingsDirectory({ master_service_job_type_id: masterServiceJobTypeId, page_size: 100 })
      : Promise.resolve({ items: [], total: 0, page: 1, page_size: 100, pages: 1 }),
    [masterServiceJobTypeId]), [masterServiceJobTypeId], { enabled: !!masterServiceJobTypeId });
  const [showAdd, setShowAdd] = useState(false);
  const [disableTarget, setDisableTarget] = useState<string | null>(null);
  const [disableReason, setDisableReason] = useState("");
  const disableAction = useAction((mappingId: string, reason: string) => checklistCatalogApi.disableMapping(mappingId, reason));
  const enableAction = useAction(checklistCatalogApi.enableMapping);
  const [disablingId, setDisablingId] = useState<string | null>(null);

  if (!masterServiceJobTypeId) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-tertiary)" }}>
        <ListChecks size={28} style={{ opacity: 0.3, marginBottom: 10 }}/>
        <p style={{ fontSize: 13, margin: 0 }}>Select a specific job type above, and add it to this service, to map checklists.</p>
      </div>
    );
  }
  if (mappingsApi.error) return <SectionError title="Couldn't load checklist mappings" error={mappingsApi.error} requestId={mappingsApi.requestId} onRetry={mappingsApi.refetch}/>;
  if (mappingsApi.loading) return <Skeleton height={140}/>;

  const ownMappings = mappingsApi.data?.items ?? [];

  async function disable(mappingId: string, reason: string) {
    if (!canWrite) return;
    setDisablingId(mappingId);
    const result = await disableAction.execute(mappingId, reason);
    setDisablingId(null);
    if (result) { setDisableTarget(null); setDisableReason(""); mappingsApi.refetch(); onChanged(); notify("Checklist mapping disabled."); }
    else notify(disableAction.error || "Couldn't disable this mapping.", "error");
  }

  async function enable(mappingId: string) {
    const result = await enableAction.execute(mappingId);
    if (result) { mappingsApi.refetch(); onChanged(); notify("Checklist mapping enabled."); }
    else notify(enableAction.error || "Couldn't enable this mapping.", "error");
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 12 }}>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
          Maps a published checklist version to this exact Job Type. Use an existing template, or create a
          simple one right here — multi-section/multi-item templates are still easiest to build in the
          Checklist Library, but that's no longer required for a basic checklist.
        </p>
        {canWrite && (
          <button onClick={() => setShowAdd(v => !v)} style={{ fontSize: 12, fontWeight: 600, padding: "6px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
            <Plus size={13}/> Map Checklist
          </button>
        )}
      </div>
      {showAdd && (
        <AddChecklistMappingForm key={masterServiceJobTypeId} masterServiceJobTypeId={masterServiceJobTypeId}
          onAdded={() => { setShowAdd(false); mappingsApi.refetch(); onChanged(); notify("Checklist mapped to this Job Type."); }}
          onError={(msg) => notify(msg, "error")}/>
      )}
      {ownMappings.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No checklists mapped to this Job Type yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {ownMappings.map(m => {
            return (
              <div key={m.id} style={{ padding: "10px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, flexWrap: "wrap" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{m.template_name ?? "Checklist"}{m.template_version ? ` v${m.template_version}` : ""}</span>
                    <Chip>{m.phase}</Chip>
                    <Chip tone={m.usage === "REQUIRED" ? "brand" : "default"}>{m.usage}</Chip>
                    <Chip>{m.actor}</Chip>
                    <Chip>{m.completion_gate.replace(/^REQUIRE_/, "").replace(/_/g, " ")}</Chip>
                  </div>
                  {canWrite && m.status === "active" && disableTarget !== m.id && (
                    <button onClick={() => setDisableTarget(m.id)} disabled={disablingId === m.id}
                      style={{ fontSize: 11, fontWeight: 600, color: "var(--danger-text)", background: "none", border: "none", cursor: disablingId === m.id ? "default" : "pointer", opacity: disablingId === m.id ? 0.6 : 1 }}>
                      {disablingId === m.id ? "Disabling…" : "Disable"}
                    </button>
                  )}
                  {canWrite && m.status === "disabled" && (
                    <button onClick={() => enable(m.id)} disabled={enableAction.loading}
                      style={{ fontSize: 11, fontWeight: 600, color: "var(--success-text)", background: "none", border: "none", cursor: "pointer" }}>
                      {enableAction.loading ? "Enabling..." : "Enable"}
                    </button>
                  )}
                </div>
                {disableTarget === m.id && (
                  <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <input autoFocus value={disableReason} onChange={event => setDisableReason(event.target.value)} placeholder="Reason for disabling (minimum 5 characters)"
                      style={{ flex: 1, minWidth: 260, padding: "7px 9px", border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", color: "var(--text-primary)", fontSize: 12 }}/>
                    <button onClick={() => disable(m.id, disableReason.trim())} disabled={disableReason.trim().length < 5 || disablingId === m.id}
                      style={{ fontSize: 11, fontWeight: 700, padding: "7px 10px", borderRadius: 8, border: "1px solid var(--danger-border)", background: "var(--danger-bg)", color: "var(--danger-text)" }}>Confirm disable</button>
                    <button onClick={() => { setDisableTarget(null); setDisableReason(""); }} style={{ fontSize: 11, border: 0, background: "none", color: "var(--text-secondary)" }}>Cancel</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Chip({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "brand" }) {
  return (
    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
      background: tone === "brand" ? "var(--brand)" : "var(--surface)",
      color: tone === "brand" ? "white" : "var(--text-secondary)", border: "1px solid var(--border)" }}>
      {children}
    </span>
  );
}

function PreviewTab({ masterServiceId, jobTypeId }: { masterServiceId: string; jobTypeId: string | null }) {
  const dimApi = useApi(useCallback(() => catalogWorkspaceApi.getDimensionGrid(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]), [masterServiceId, jobTypeId]);
  const questionsApi = useApi(useCallback(() => catalogWorkspaceApi.listQuestions(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]), [masterServiceId, jobTypeId]);

  if (!jobTypeId) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-tertiary)" }}>
        <Search size={28} style={{ opacity: 0.3, marginBottom: 10 }}/>
        <p style={{ fontSize: 13, margin: 0 }}>Select a specific job type above to preview its derived experience.</p>
      </div>
    );
  }

  const enabledDims = (dimApi.data?.dimensions ?? []).filter(d => d.config.enabled);
  const tenantDims = enabledDims.filter(d => d.config.show_during_tenant_setup);
  const customerDims = enabledDims.filter(d => d.config.ask_customer);
  const questions = questionsApi.data?.questions ?? [];
  if (dimApi.error || questionsApi.error) return <SectionError
    title="Could not load the complete review" error={dimApi.error || questionsApi.error || "Unknown error"}
    onRetry={() => { dimApi.refetch(); questionsApi.refetch(); }}/>;
  if (dimApi.loading || questionsApi.loading) return <Skeleton height={220}/>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        Read-only configuration summary, not an interactive booking test. Conditional question rules are not evaluated here. Nothing here is saved or booked.
      </p>
      <PreviewSection title="Tenant Setup Preview">
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)" }}>
          {tenantDims.length === 0 && <li>No provider-facing dimension step for this job type.</li>}
          {tenantDims.map(d => <li key={d.dimension.id}>{d.dimension.name} — {d.config.required ? "required" : "optional"} for tenant setup</li>)}
        </ul>
      </PreviewSection>
      <PreviewSection title="Customer Booking Preview">
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)" }}>
          {customerDims.map(d => <li key={d.dimension.id}>Customer selects {d.dimension.name}{d.config.required ? " (required)" : " (optional)"}</li>)}
          {questions.filter(q => q.customer_visible && q.is_active).map(q => <li key={q.id}>{q.label}{q.required ? " (required)" : ""}{q.rules.length > 0 ? " · conditional" : ""}</li>)}
        </ul>
      </PreviewSection>
      <PreviewSection title="Technician Execution Preview">
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)" }}>
          <li>Checklist instances resolve from the Checklist tab's mappings for this exact job type.</li>
        </ul>
      </PreviewSection>
    </div>
  );
}

function PreviewSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: 14, background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", margin: "0 0 8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</p>
      {children}
    </div>
  );
}

const QUESTION_INPUT_TYPES = ["single_select", "multi_select", "boolean", "number", "text", "photo", "date", "time", "address"] as const;
const QUESTION_ANSWER_SOURCES = ["static", "free"] as const;

function slugifyKey(label: string): string {
  return label.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 60);
}

function AddQuestionForm({ masterServiceId, jobTypeId, onAdded, onError }: {
  masterServiceId: string; jobTypeId: string | null; onAdded: () => void; onError: () => void;
}) {
  const [label, setLabel] = useState("");
  const [inputType, setInputType] = useState<typeof QUESTION_INPUT_TYPES[number]>("text");
  const [answerSource, setAnswerSource] = useState<typeof QUESTION_ANSWER_SOURCES[number]>("free");
  const [required, setRequired] = useState(false);
  const createAction = useAction(catalogWorkspaceApi.createQuestion);

  async function submit() {
    const key = slugifyKey(label);
    if (!label.trim() || !key) return;
    const result = await createAction.execute({
      master_service_id: masterServiceId, job_type_id: jobTypeId,
      question_key: key, label: label.trim(), input_type: inputType,
      answer_source: answerSource, required,
    });
    if (result) { setLabel(""); setRequired(false); onAdded(); } else onError();
  }

  return (
    <div style={{ marginBottom: 14, padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", display: "flex", flexDirection: "column", gap: 8 }}>
      <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>
        Question text
        <input value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. Is an error code visible?"
          style={{ width: "100%", marginTop: 4, fontSize: 13, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}/>
      </label>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>
          Answer type
          <select value={inputType} onChange={e => setInputType(e.target.value as typeof inputType)}
            style={{ display: "block", marginTop: 4, fontSize: 12, padding: "5px 7px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
            {QUESTION_INPUT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>
          Answer source
          <select value={answerSource} onChange={e => setAnswerSource(e.target.value as typeof answerSource)}
            style={{ display: "block", marginTop: 4, fontSize: 12, padding: "5px 7px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
            {QUESTION_ANSWER_SOURCES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 5, marginTop: 18 }}>
          <input type="checkbox" checked={required} onChange={e => setRequired(e.target.checked)}/> Required
        </label>
      </div>
      <button onClick={submit} disabled={!label.trim() || createAction.loading}
        style={{ alignSelf: "flex-start", fontSize: 12, fontWeight: 600, padding: "7px 14px", borderRadius: 8, border: "none",
          background: "var(--brand)", color: "white", cursor: !label.trim() || createAction.loading ? "default" : "pointer",
          opacity: !label.trim() || createAction.loading ? 0.6 : 1 }}>
        {createAction.loading ? "Adding…" : "Add Question"}
      </button>
      {createAction.error && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: 0 }}>{createAction.error}</p>}
    </div>
  );
}

const CONDITION_TYPES = ["job_type", "problem", "dimension_enabled", "answer_equals"] as const;
const CONDITION_LABELS: Record<string, string> = {
  job_type: "Job type is", problem: "Problem is",
  dimension_enabled: "Dimension is enabled", answer_equals: "A prior answer equals",
};

// ── Show-when rule builder — the conditional gate the question engine's
// resolver ANDs together (job_type / problem / dimension_enabled / answer_equals).
// Refs resolve against real data already loaded for this service: job types,
// problems mapped to this service, and admin-defined dimensions. ────────────
function RuleBuilder({ question, canWrite, jobTypes, problems, dimensions, onChanged, notify }: {
  question: CatalogQuestionItem; canWrite: boolean;
  jobTypes: CatalogJobType[]; problems: CatalogIssueTypeMapping[]; dimensions: { id: string; name: string }[];
  onChanged: () => void; notify: (m: string, t?: "success" | "error") => void;
}) {
  const [conditionType, setConditionType] = useState<typeof CONDITION_TYPES[number]>("job_type");
  const [refId, setRefId] = useState("");
  const [expectedValue, setExpectedValue] = useState("");
  const addAction = useAction(catalogWorkspaceApi.addQuestionRule);
  const deleteAction = useAction(catalogWorkspaceApi.deleteQuestionRule);

  function refOptions(): { id: string; label: string }[] {
    if (conditionType === "job_type") return jobTypes.map(jt => ({ id: jt.id, label: jt.label }));
    if (conditionType === "problem") return problems.map(p => ({ id: p.issue_type_id, label: p.name }));
    if (conditionType === "dimension_enabled") return dimensions.map(d => ({ id: d.id, label: d.name }));
    return []; // answer_equals uses expected_value directly, no ref picker
  }

  function labelForRule(condition_type: string, ref_id: string | null, expected_value: string | null): string {
    if (condition_type === "job_type") return `Job type = ${jobTypes.find(jt => jt.id === ref_id)?.label ?? ref_id}`;
    if (condition_type === "problem") return `Problem = ${problems.find(p => p.issue_type_id === ref_id)?.name ?? ref_id}`;
    if (condition_type === "dimension_enabled") return `Dimension enabled = ${dimensions.find(d => d.id === ref_id)?.name ?? ref_id}`;
    return `Prior answer = ${expected_value}`;
  }

  async function addRule() {
    const payload: Record<string, unknown> = { condition_type: conditionType };
    if (conditionType === "answer_equals") payload.expected_value = expectedValue.trim();
    else payload.ref_id = refId;
    if (conditionType !== "answer_equals" && !refId) return;
    if (conditionType === "answer_equals" && !expectedValue.trim()) return;
    const result = await addAction.execute(question.id, payload);
    if (result) { setRefId(""); setExpectedValue(""); onChanged(); notify("Rule added."); }
    else notify("Couldn't add rule.", "error");
  }

  async function removeRule(ruleId: string) {
    const result = await deleteAction.execute(ruleId);
    if (result) { onChanged(); notify("Rule removed."); }
    else notify("Couldn't remove rule.", "error");
  }

  const options = refOptions();

  return (
    <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
      {question.rules.length === 0 ? (
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px" }}>No rules — question always applies (ANDed with other rules if added).</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
          {question.rules.map(r => (
            <div key={r.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 8px", background: "var(--surface)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <span style={{ fontSize: 11, color: "var(--text-primary)" }}>{labelForRule(r.condition_type, r.ref_id, r.expected_value)}</span>
              {canWrite && (
                <button onClick={() => removeRule(r.id)} disabled={deleteAction.loading} style={{ fontSize: 10, fontWeight: 600, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer" }}>Remove</button>
              )}
            </div>
          ))}
        </div>
      )}
      {canWrite && (
        <div style={{ display: "flex", gap: 6, alignItems: "flex-end", flexWrap: "wrap" }}>
          <label style={{ fontSize: 10, fontWeight: 600, color: "var(--text-secondary)" }}>
            Condition
            <select value={conditionType} onChange={e => { setConditionType(e.target.value as typeof conditionType); setRefId(""); }}
              style={{ display: "block", marginTop: 3, fontSize: 11, padding: "4px 6px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
              {CONDITION_TYPES.map(c => <option key={c} value={c}>{CONDITION_LABELS[c]}</option>)}
            </select>
          </label>
          {conditionType === "answer_equals" ? (
            <label style={{ fontSize: 10, fontWeight: 600, color: "var(--text-secondary)" }}>
              Expected value
              <input value={expectedValue} onChange={e => setExpectedValue(e.target.value)}
                style={{ display: "block", marginTop: 3, fontSize: 11, padding: "4px 6px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}/>
            </label>
          ) : (
            <label style={{ fontSize: 10, fontWeight: 600, color: "var(--text-secondary)" }}>
              Value
              <select value={refId} onChange={e => setRefId(e.target.value)}
                style={{ display: "block", marginTop: 3, fontSize: 11, padding: "4px 6px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", minWidth: 140 }}>
                <option value="">Select…</option>
                {options.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
              </select>
            </label>
          )}
          <button onClick={addRule} disabled={addAction.loading}
            style={{ fontSize: 11, fontWeight: 600, padding: "5px 10px", borderRadius: 6, border: "none", background: "var(--brand)", color: "white", cursor: addAction.loading ? "default" : "pointer" }}>
            + Add
          </button>
        </div>
      )}
    </div>
  );
}

function QuestionsSubTab({ masterServiceId, jobTypeId, canWrite, notify, onChanged }: {
  masterServiceId: string; jobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const questionsApi = useApi(
    useCallback(() => catalogWorkspaceApi.listQuestions(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId],
  );
  const toggleAction = useAction(catalogWorkspaceApi.updateQuestion);
  const deleteAction = useAction(catalogWorkspaceApi.deleteQuestion);
  const questions = questionsApi.data?.questions ?? [];
  const [showAdd, setShowAdd] = useState(false);
  const [expandedRulesFor, setExpandedRulesFor] = useState<string | null>(null);

  async function handleDelete(q: CatalogQuestionItem) {
    if (!canWrite) return;
    if (!window.confirm(`Delete "${q.label}"? DeepSeek and the customer flow will stop asking it, and any tenant setup relying on it returns to draft for re-review.`)) return;
    const result = await deleteAction.execute(q.id);
    if (result) {
      notify(`"${q.label}" deleted.`);
      questionsApi.refetch(); onChanged();
    } else {
      notify(deleteAction.error ?? "Couldn't delete this question.", "error");
    }
  }

  // Fetched once per sub-tab visit -- the reference lists the rule builder
  // needs to resolve condition_type -> a concrete picker (job type / problem
  // mapped to this service / dimension / another question on this service).
  const jobTypesApi = useApi(useCallback(async () => {
    const result = await catalogWorkspaceApi.getJobTypesForService(masterServiceId);
    return { items: result.items.map(link => link.job_type) };
  }, [masterServiceId]), [masterServiceId]);
  const issuesApi = useApi(
    useCallback(() => catalogWorkspaceApi.listServiceIssues(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId],
  );
  const dimensionsApi = useApi(useCallback(() => catalogWorkspaceApi.listDimensions(), []), []);

  async function toggleActive(q: CatalogQuestionItem) {
    if (!canWrite) return;
    const result = await toggleAction.execute(q.id, { is_active: !q.is_active });
    if (result) {
      notify(`"${q.label}" ${q.is_active ? "disabled" : "enabled"}.`);
      questionsApi.refetch(); onChanged();
    } else {
      notify("Couldn't update question.", "error");
    }
  }

  if (questionsApi.error) return <SectionError title="Couldn't load questions" error={questionsApi.error} requestId={questionsApi.requestId} onRetry={questionsApi.refetch}/>;
  if (questionsApi.loading) return <Skeleton height={140}/>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 12 }}>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
          Conditional questions DeepSeek and the customer flow may ask for this service{jobTypeId ? " + job type" : ""}.
          Show-when rules gate each question by job type, problem, dimension, or a prior answer.
        </p>
        {canWrite && (
          <button onClick={() => setShowAdd(v => !v)} style={{ fontSize: 12, fontWeight: 600, padding: "6px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
            <Plus size={13}/> Add Question
          </button>
        )}
      </div>
      {showAdd && (
        <AddQuestionForm masterServiceId={masterServiceId} jobTypeId={jobTypeId}
          onAdded={() => { setShowAdd(false); questionsApi.refetch(); onChanged(); notify("Question added."); }}
          onError={() => notify("Couldn't add this question.", "error")}/>
      )}
      {questions.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No conditional questions configured yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {questions.map(q => (
            <div key={q.id} style={{ padding: "10px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                <div style={{ display: "flex", gap: 10, alignItems: "flex-start", minWidth: 0 }}>
                  <div>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 3px" }}>{q.label}</p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                    {q.input_type} · {q.answer_source}
                    {q.rules.length > 0 && ` · ${q.rules.length} show-when rule${q.rules.length === 1 ? "" : "s"}`}
                    {q.deepseek_enabled && " · DeepSeek"}
                  </p>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  <button onClick={() => setExpandedRulesFor(expandedRulesFor === q.id ? null : q.id)}
                    style={{ fontSize: 10, fontWeight: 700, padding: "2px 10px", borderRadius: 999, border: "1px solid var(--border)", cursor: "pointer", background: "var(--surface)", color: "var(--text-secondary)" }}>
                    Rules ({q.rules.length})
                  </button>
                  {canWrite && (
                    <button onClick={() => toggleActive(q)} style={{ fontSize: 10, fontWeight: 700, padding: "2px 10px", borderRadius: 999, border: "none", cursor: "pointer",
                      background: q.is_active ? "var(--success-bg)" : "var(--surface)", color: q.is_active ? "var(--success-text)" : "var(--text-tertiary)" }}>
                      {q.is_active ? "Active" : "Inactive"}
                    </button>
                  )}
                  {canWrite && (
                    <button onClick={() => handleDelete(q)} disabled={deleteAction.loading} aria-label={`Delete "${q.label}"`} title={`Delete "${q.label}"`}
                      style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, border: "none", cursor: deleteAction.loading ? "default" : "pointer",
                        background: "var(--surface)", color: "var(--danger-text)", display: "flex", alignItems: "center" }}>
                      <Trash2 size={12}/>
                    </button>
                  )}
                </div>
              </div>
              {expandedRulesFor === q.id && (
                <RuleBuilder question={q} canWrite={canWrite}
                  jobTypes={jobTypesApi.data?.items ?? []}
                  problems={issuesApi.data?.issues ?? []}
                  dimensions={dimensionsApi.data?.items ?? []}
                  onChanged={() => { questionsApi.refetch(); }}
                  notify={notify}/>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Tenant Setup Rules tab ────────────────────────────────────────────────────
// This is a focused view over the same normalized dimension and workflow
// records used by the other tabs. It never writes deprecated service flags.
function TenantSetupRulesTab({ masterServiceId, jobTypeId, canWrite, notify, onChanged }: {
  masterServiceId: string; jobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const dimensionsApi = useApi(
    useCallback(() => catalogWorkspaceApi.getDimensionGrid(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId], { enabled: !!jobTypeId },
  );
  const workflowApi = useApi(
    useCallback(() => jobTypeId ? catalogWorkspaceApi.getJobTypeWorkflow(masterServiceId, jobTypeId) : Promise.resolve(null as unknown as ServiceJobWorkflow),
      [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId], { enabled: !!jobTypeId },
  );
  const setDimension = useAction(catalogWorkspaceApi.setDimensionConfig);
  const setWorkflow = useAction(catalogWorkspaceApi.setJobTypeWorkflow);

  if (!jobTypeId) {
    return <div style={{ padding: "36px 20px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
      Select a job type above. Tenant setup rules are job-type specific.
    </div>;
  }
  if (dimensionsApi.error || workflowApi.error) {
    return <SectionError title="Couldn't load tenant setup rules" error={dimensionsApi.error || workflowApi.error || "Unknown error"}
      requestId={dimensionsApi.requestId || workflowApi.requestId}
      onRetry={() => { dimensionsApi.refetch(); workflowApi.refetch(); }}/>;
  }
  if (dimensionsApi.loading || workflowApi.loading || !workflowApi.data) return <Skeleton height={210}/>;

  const setupDimensions = (dimensionsApi.data?.dimensions ?? []).filter(row =>
    row.dimension.key === "type" || row.dimension.key === "brand");

  async function toggleRequiredDimension(row: DimensionGridRow) {
    if (!canWrite) return;
    const nextRequired = !(row.config.enabled && row.config.show_during_tenant_setup && row.config.required);
    const result = await setDimension.execute(masterServiceId, jobTypeId, row.dimension.id, {
      enabled: nextRequired ? true : row.config.enabled,
      show_during_tenant_setup: nextRequired ? true : row.config.show_during_tenant_setup,
      required: nextRequired,
    });
    if (result) {
      notify(`${row.dimension.name} setup requirement updated.`);
      dimensionsApi.refetch(); onChanged();
    } else notify("Couldn't update this setup requirement.", "error");
  }

  async function toggleWorkflow(field: "service_area_required" | "availability_required", label: string) {
    if (!canWrite || !workflowApi.data) return;
    const result = await setWorkflow.execute(masterServiceId, jobTypeId, { [field]: !workflowApi.data[field] });
    if (result) {
      notify(`${label} updated.`);
      workflowApi.refetch(); onChanged();
    } else notify("Couldn't update this setup requirement.", "error");
  }

  return (
    <div>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>
        These are the requirements the tenant publish endpoint enforces for this exact job type. Type and Brand
        reuse Dimensions; Service Area and Availability reuse Workflow. Customer questions and photo capture are
        configured under Problems & Questions because they are booking rules, not tenant setup tasks.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {setupDimensions.map(row => {
          const on = row.config.enabled && row.config.show_during_tenant_setup && row.config.required;
          return (
          <div key={row.dimension.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 13, color: "var(--text-primary)" }}>Provider must select {row.dimension.name.toLowerCase()}</span>
            <FlagPill on={on} onClick={() => toggleRequiredDimension(row)} disabled={!canWrite || setDimension.loading}/>
          </div>
        )})}
        {([
          ["service_area_required", "Provider must configure service area"],
          ["availability_required", "Provider must configure availability"],
        ] as const).map(([field, label]) => (
          <div key={field} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{label}</span>
            <FlagPill on={workflowApi.data![field]} onClick={() => toggleWorkflow(field, label)} disabled={!canWrite || setWorkflow.loading}/>
          </div>
        ))}
      </div>
    </div>
  );
}
