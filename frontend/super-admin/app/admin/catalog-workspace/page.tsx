"use client";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { IconPicker } from "../../../components/shared/IconPicker";
import {
  homeServicesCatalogConsoleApi, catalogWorkspaceApi, checklistCatalogApi,
  type HsConsoleService, type CatalogJobType, type DimensionGridRow, type CatalogDimensionDef,
  type BlueprintReadiness, type BlueprintImpactReport, type BlueprintDraftStatus, type CatalogQuestionItem,
  type CatalogIssueTypeMapping, type CatalogOptionMapping, type ServiceJobWorkflow,
  type ChecklistTemplateRow, type JobTypeChecklistMappingRow, type ChecklistUsage, type ChecklistActor,
  type ChecklistCompletionGate, type ChecklistPurpose, type ChecklistItemType,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { usePermissions } from "../../../hooks/usePermissions";
import {
  ChevronRight, RefreshCw, XCircle, CheckCircle2, Layers, Lock, Plus,
  CircleDot, ListChecks, SlidersHorizontal, HelpCircle, Search, ClipboardList,
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

const WORKSPACE_TABS = [
  { key: "overview", label: "Overview", icon: ClipboardList },
  { key: "problems", label: "Problems & Questions", icon: HelpCircle },
  { key: "dimensions", label: "Dimensions", icon: SlidersHorizontal },
  { key: "options", label: "Options & Add-ons", icon: ListChecks },
  { key: "checklist", label: "Checklist", icon: ListChecks },
  { key: "workflow", label: "Workflow", icon: SlidersHorizontal },
  { key: "preview", label: "Preview", icon: Search },
  { key: "tenant_rules", label: "Tenant Setup Rules", icon: ListChecks },
] as const;
type WorkspaceTabKey = typeof WORKSPACE_TABS[number]["key"];

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AdminCatalogWorkspacePage() {
  const perm = usePermissions();
  const canRead = perm.loading || perm.has("catalog:services:read");
  const canWrite = perm.has("catalog:services:write");

  const listApi = useApi(useCallback(() => homeServicesCatalogConsoleApi.listServices(), []), []);
  // Global job-type catalog (platform-wide definitions) -- used only to pick
  // from when attaching a job type to a service, never as the tab source.
  const jobTypesApi = useApi(useCallback(() => catalogWorkspaceApi.listJobTypes(), []), []);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedJobTypeId, setSelectedJobTypeId] = useState<string | null>(null);
  const [showAddJobType, setShowAddJobType] = useState(false);
  const [tab, setTab] = useState<WorkspaceTabKey>("dimensions");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  function notify(msg: string, type: "success" | "error" = "success") {
    setToast({ msg, type }); setTimeout(() => setToast(null), 3500);
  }

  const services = listApi.data?.services ?? [];
  const groups = listApi.data?.groups ?? [];
  const grouped = groups.map(g => ({ group: g, services: services.filter(s => s.service_group_id === g.group_id) }));
  const ungrouped = services.filter(s => !s.service_group_id);
  const jobTypes = jobTypesApi.data?.items ?? [];

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
  const unlinkedJobTypes = jobTypes.filter(jt => jt.is_active && !serviceJobTypeLinks.some(l => l.job_type_id === jt.id));

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
    setSelectedId(id); setSelectedJobTypeId(null); setTab("dimensions");
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
        .cw-shell{display:grid;grid-template-columns:260px 1fr 300px;gap:16px;align-items:start}
        @media(max-width:1300px){.cw-shell{grid-template-columns:220px 1fr 280px}}
        @media(max-width:1000px){.cw-shell{grid-template-columns:1fr}}
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

      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Admin</span><ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Catalog Workspace</span>
      </div>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px", letterSpacing: "-0.01em" }}>
            Catalog Workspace
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Structural configuration only — pricing is never set here. Choose a service, then a job type, to configure
            its generic dimensions, customer problems &amp; questions, and see live blueprint readiness.
          </p>
        </div>
        <button onClick={() => { listApi.refetch(); jobTypesApi.refetch(); serviceJobTypesApi.refetch(); readinessApi.refetch(); impactApi.refetch(); draftApi.refetch(); }}
          style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-secondary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
          <RefreshCw size={12}/> Refresh
        </button>
      </div>

      <div className="cw-shell">
        {/* ── Column 1: Catalog Structure ─────────────────────────────────── */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: 14, maxHeight: 760, overflowY: "auto" }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px", padding: "0 4px" }}>
            Catalog Structure
          </p>
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
        </div>

        {/* ── Column 2: Service Workspace ──────────────────────────────────── */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: "20px 22px", minHeight: 500 }}>
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
                        Draft changes · {draftApi.data.pending_change_count}
                      </span>
                      {canWrite && (
                        <button onClick={handlePublish} disabled={publishAction.loading}
                          style={{ fontSize: 12, fontWeight: 700, padding: "6px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white", cursor: publishAction.loading ? "default" : "pointer" }}>
                          {publishAction.loading ? "Publishing…" : "Publish"}
                        </button>
                      )}
                    </div>
                  )}
                </div>
                {serviceJobTypesApi.loading ? <Skeleton height={30}/> : (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                    <button className={`cw-jt-tab ${selectedJobTypeId === null ? "active" : ""}`} onClick={() => setSelectedJobTypeId(null)}>
                      All job types
                    </button>
                    {serviceJobTypeLinks.map(link => (
                      <button key={link.job_type_id} className={`cw-jt-tab ${selectedJobTypeId === link.job_type_id ? "active" : ""}`} onClick={() => setSelectedJobTypeId(link.job_type_id)}
                        title={link.job_type.runtime_supported ? undefined : "Not yet wired into field_ops runtime transitions"}>
                        {link.job_type.label}{!link.job_type.runtime_supported && " *"}
                      </button>
                    ))}
                    {canWrite && (
                      <button onClick={() => setShowAddJobType(v => !v)} className="cw-jt-tab" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <Plus size={12}/> Add Job Type
                      </button>
                    )}
                  </div>
                )}
                {showAddJobType && (
                  <AddJobTypeToServicePicker masterServiceId={selectedId}
                    unlinkedJobTypes={unlinkedJobTypes}
                    onAdded={() => { setShowAddJobType(false); serviceJobTypesApi.refetch(); notify("Job type added to this service."); }}
                    onNewJobTypeCreated={() => jobTypesApi.refetch()}
                    onError={(msg) => notify(msg, "error")}/>
                )}
              </div>

              <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 16, overflowX: "auto" }}>
                {WORKSPACE_TABS.map(t => (
                  <button key={t.key} className={`cw-wtab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
                    <t.icon size={13}/> {t.label}
                  </button>
                ))}
              </div>

              {tab === "overview" && (
                <OverviewTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId}
                  serviceName={safeText(services.find(s => s.service_id === selectedId)?.service_name, "Service")}
                  jobTypeLink={serviceJobTypeLinks.find(l => l.job_type_id === selectedJobTypeId) ?? null}
                  readiness={readinessApi.data} draft={draftApi.data}/>
              )}
              {tab === "dimensions" && (
                <DimensionsTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId} canWrite={canWrite}
                  notify={notify} onChanged={() => { readinessApi.refetch(); }}/>
              )}
              {tab === "problems" && (
                <ProblemsQuestionsTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId} canWrite={canWrite}
                  notify={notify} onChanged={() => { readinessApi.refetch(); }}/>
              )}
              {tab === "options" && (
                <OptionsTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId} canWrite={canWrite}
                  notify={notify} onChanged={() => { readinessApi.refetch(); }}/>
              )}
              {tab === "checklist" && (
                <ChecklistTab masterServiceJobTypeId={serviceJobTypeLinks.find(l => l.job_type_id === selectedJobTypeId)?.id ?? null}
                  canWrite={canWrite} notify={notify} onChanged={() => { readinessApi.refetch(); }}/>
              )}
              {tab === "workflow" && (
                <WorkflowTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId} canWrite={canWrite}
                  notify={notify} onChanged={() => { readinessApi.refetch(); }}/>
              )}
              {tab === "preview" && (
                <PreviewTab masterServiceId={selectedId} jobTypeId={selectedJobTypeId}/>
              )}
              {tab === "tenant_rules" && (
                <TenantSetupRulesTab s={services.find(s => s.service_id === selectedId)} canWrite={canWrite}
                  notify={notify} onChanged={() => { listApi.refetch(); readinessApi.refetch(); impactApi.refetch(); draftApi.refetch(); }}/>
              )}
            </>
          )}
        </div>

        {/* ── Column 3: Readiness + Impact ─────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: 16 }}>
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

          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: 16 }}>
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
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
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
                  <td style={{ padding: "9px 10px" }}>
                    <button onClick={() => setExpandedValuesFor(expandedValuesFor === row.dimension.id ? null : row.dimension.id)}
                      style={{ fontSize: 11, fontWeight: 600, color: "var(--brand)", background: "none", border: "none", cursor: "pointer", whiteSpace: "nowrap" }}>
                      {expandedValuesFor === row.dimension.id ? "Hide" : "Manage values"}
                    </button>
                  </td>
                </tr>
                {expandedValuesFor === row.dimension.id && (
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <td colSpan={7} style={{ padding: "0 10px 12px" }}>
                      <DimensionValuesPanel dimension={row.dimension} canWrite={canWrite}
                        onChanged={() => gridApi.refetch()} notify={notify}/>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={7} style={{ padding: 16, textAlign: "center", fontSize: 12, color: "var(--text-tertiary)" }}>No dimensions defined yet.</td></tr>
            )}
          </tbody>
        </table>
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
function AddJobTypeToServicePicker({ masterServiceId, unlinkedJobTypes, onAdded, onNewJobTypeCreated, onError }: {
  masterServiceId: string; unlinkedJobTypes: CatalogJobType[];
  onAdded: () => void; onNewJobTypeCreated: () => void; onError: (msg: string) => void;
}) {
  const [mode, setMode] = useState<"attach" | "define">("attach");
  const [pickedId, setPickedId] = useState("");
  const attachAction = useAction(catalogWorkspaceApi.addServiceJobType);

  const [label, setLabel] = useState("");
  const [requiresAssessment, setRequiresAssessment] = useState(true);
  const [allowsQuote, setAllowsQuote] = useState(true);
  const [requiresChecklist, setRequiresChecklist] = useState(false);
  const createAction = useAction(catalogWorkspaceApi.createJobType);

  async function attachExisting() {
    if (!pickedId) return;
    const result = await attachAction.execute(masterServiceId, pickedId);
    if (result) { setPickedId(""); onAdded(); }
    else onError(attachAction.error ?? "Couldn't add job type to this service.");
  }

  async function defineAndAttach() {
    const key = slugifyKey(label);
    if (!label.trim() || !key) return;
    const created = await createAction.execute({
      key, label: label.trim(),
      requires_assessment: requiresAssessment, allows_quote: allowsQuote, requires_checklist: requiresChecklist,
    });
    if (!created) { onError(createAction.error ?? "Couldn't create job type."); return; }
    onNewJobTypeCreated();
    const attached = await attachAction.execute(masterServiceId, created.id);
    if (attached) { setLabel(""); onAdded(); }
    else onError(attachAction.error ?? "Job type created but couldn't be added to this service.");
  }

  return (
    <div style={{ marginTop: 10, padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
        <button onClick={() => setMode("attach")} style={{ fontSize: 11, fontWeight: 600, padding: "5px 10px", borderRadius: 999, border: "1px solid var(--border)", cursor: "pointer",
          background: mode === "attach" ? "var(--brand)" : "var(--surface)", color: mode === "attach" ? "white" : "var(--text-secondary)" }}>
          Attach existing
        </button>
        <button onClick={() => setMode("define")} style={{ fontSize: 11, fontWeight: 600, padding: "5px 10px", borderRadius: 999, border: "1px solid var(--border)", cursor: "pointer",
          background: mode === "define" ? "var(--brand)" : "var(--surface)", color: mode === "define" ? "white" : "var(--text-secondary)" }}>
          Define new
        </button>
      </div>

      {mode === "attach" ? (
        unlinkedJobTypes.length === 0 ? (
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Every platform job type is already added to this service.</p>
        ) : (
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>
              Job type
              <select value={pickedId} onChange={e => setPickedId(e.target.value)}
                style={{ display: "block", marginTop: 4, fontSize: 13, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", minWidth: 180 }}>
                <option value="">Select…</option>
                {unlinkedJobTypes.map(jt => <option key={jt.id} value={jt.id}>{jt.label}</option>)}
              </select>
            </label>
            <button onClick={attachExisting} disabled={!pickedId || attachAction.loading}
              style={{ fontSize: 12, fontWeight: 600, padding: "7px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white",
                cursor: !pickedId || attachAction.loading ? "default" : "pointer", opacity: !pickedId || attachAction.loading ? 0.6 : 1 }}>
              {attachAction.loading ? "Adding…" : "Add to Service"}
            </button>
          </div>
        )
      ) : (
        <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>
            Job type name
            <input value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. Deep Cleaning"
              style={{ display: "block", marginTop: 4, fontSize: 13, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", minWidth: 200 }}/>
          </label>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 5 }}>
            <input type="checkbox" checked={requiresAssessment} onChange={e => setRequiresAssessment(e.target.checked)}/> Requires assessment
          </label>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 5 }}>
            <input type="checkbox" checked={allowsQuote} onChange={e => setAllowsQuote(e.target.checked)}/> Allows quote
          </label>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 5 }}>
            <input type="checkbox" checked={requiresChecklist} onChange={e => setRequiresChecklist(e.target.checked)}/> Requires checklist
          </label>
          <button onClick={defineAndAttach} disabled={!label.trim() || createAction.loading || attachAction.loading}
            style={{ fontSize: 12, fontWeight: 600, padding: "7px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white",
              cursor: !label.trim() || createAction.loading || attachAction.loading ? "default" : "pointer",
              opacity: !label.trim() || createAction.loading || attachAction.loading ? 0.6 : 1 }}>
            {createAction.loading || attachAction.loading ? "Working…" : "Create & Add"}
          </button>
          <p style={{ width: "100%", fontSize: 10, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
            This defines a new platform-wide job type (available to every service) and adds it to this one.
            New job types aren't automatically wired into field_ops's runtime transition graph — they'll show a * marker until that's done separately.
          </p>
        </div>
      )}
    </div>
  );
}

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

function DimensionValuesPanel({ dimension, canWrite, onChanged, notify }: {
  dimension: CatalogDimensionDef; canWrite: boolean;
  onChanged: () => void; notify: (m: string, t?: "success" | "error") => void;
}) {
  const valuesApi = useApi(useCallback(() => catalogWorkspaceApi.listDimensionValues(dimension.id), [dimension.id]), [dimension.id]);
  const addAction = useAction(catalogWorkspaceApi.addDimensionValue);
  const [label, setLabel] = useState("");
  const isLegacy = !!dimension.legacy_source;
  const values = valuesApi.data?.values ?? [];

  async function addValue() {
    const code = slugifyKey(label);
    if (!label.trim() || !code) return;
    const result = await addAction.execute(dimension.id, { code, label: label.trim() });
    if (result) { setLabel(""); valuesApi.refetch(); onChanged(); notify("Value added."); }
    else notify("Couldn't add value.", "error");
  }

  if (valuesApi.error) return <SectionError title="Couldn't load values" error={valuesApi.error} requestId={valuesApi.requestId} onRetry={valuesApi.refetch}/>;
  if (valuesApi.loading) return <Skeleton height={60}/>;

  return (
    <div style={{ padding: 10, borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)" }}>
      {isLegacy ? (
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          Values for {dimension.name} are managed in the {dimension.legacy_source} catalog, not here.
        </p>
      ) : (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {values.map(v => (
              <span key={v.id} style={{ fontSize: 11, padding: "3px 9px", borderRadius: 999, background: "var(--surface-sunken)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                {v.label}
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
      icon_url: newIconUrl || undefined,
    });
    if (!created) { onError(); return; }
    const issueId = String((created as { id?: string }).id ?? "");
    if (!issueId) { onError(); return; }
    const attached = await addAction.execute(masterServiceId, { issue_type_id: issueId, job_type_id: jobTypeId });
    if (attached) { setNewName(""); setNewCode(""); setNewIconUrl(null); setShowCreate(false); onAdded(); } else onError();
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
          <div style={{ marginBottom: 8 }}>
            <IconPicker context="issue_icon" value={newIconUrl} onChange={setNewIconUrl}/>
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

// ── Options & Add-ons tab — HOME-SERVICES-CATALOG ownership correction.
// Maps a reusable Service Option template to the EXACT selected Job Type;
// customer/technician selectability and usage are configured per mapping
// here, never on the global template. No price field anywhere on this tab
// -- tenant pricing lives in Tenant Setup > Options & Add-ons, resolved
// against the mapping created here. ─────────────────────────────────────────
function OptionsTab({ masterServiceId, jobTypeId, canWrite, notify, onChanged }: {
  masterServiceId: string; jobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const mappingsApi = useApi(
    useCallback(() => catalogWorkspaceApi.listServiceOptionMappings(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId],
  );
  const linksApi = useApi(useCallback(() => catalogWorkspaceApi.listServiceJobTypes(masterServiceId), [masterServiceId]), [masterServiceId]);
  const removeAction = useAction(catalogWorkspaceApi.removeServiceOptionMapping);
  const updateAction = useAction(catalogWorkspaceApi.updateServiceOptionMapping);
  const addAction = useAction(catalogWorkspaceApi.addServiceOptionMapping);
  const mappings = mappingsApi.data ?? [];
  const [showAdd, setShowAdd] = useState(false);
  const [showCopy, setShowCopy] = useState(false);
  const [copying, setCopying] = useState(false);
  const otherJobTypes = (linksApi.data?.items ?? []).filter(l => l.job_type_id !== jobTypeId && l.is_active);

  async function copyFrom(sourceJobTypeId: string) {
    if (!canWrite || !jobTypeId) return;
    setCopying(true);
    try {
      const source = await catalogWorkspaceApi.listServiceOptionMappings(masterServiceId, sourceJobTypeId);
      const existingIds = new Set(mappings.map(m => m.service_option_id));
      let copied = 0;
      for (const m of source) {
        if (existingIds.has(m.service_option_id)) continue;
        // Explicit, independent new mapping row -- editing this Job Type's
        // copy never mutates the source Job Type's published mapping.
        const result = await addAction.execute(masterServiceId, {
          service_option_id: m.service_option_id, job_type_id: jobTypeId,
          usage: m.usage, customer_selectable: m.customer_selectable,
          technician_selectable: m.technician_selectable,
        });
        if (result) copied++;
      }
      setShowCopy(false); mappingsApi.refetch(); onChanged();
      notify(copied > 0 ? `Copied ${copied} option(s) into this Job Type.` : "Nothing new to copy — all options already mapped here.");
    } finally {
      setCopying(false);
    }
  }

  async function handleRemove(m: CatalogOptionMapping) {
    if (!canWrite) return;
    const result = await removeAction.execute(masterServiceId, m.id);
    if (result) { notify(`${m.option.name} detached from this Job Type.`); mappingsApi.refetch(); onChanged(); }
    else notify("Couldn't detach this option.", "error");
  }

  async function toggleFlag(m: CatalogOptionMapping, flag: "customer_selectable" | "technician_selectable") {
    if (!canWrite) return;
    const result = await updateAction.execute(masterServiceId, m.id, { [flag]: !m[flag] });
    if (result) mappingsApi.refetch(); else notify("Couldn't update this option.", "error");
  }

  if (mappingsApi.error) return <SectionError title="Couldn't load options" error={mappingsApi.error} requestId={mappingsApi.requestId} onRetry={mappingsApi.refetch}/>;
  if (mappingsApi.loading) return <Skeleton height={140}/>;

  if (!jobTypeId) {
    return (
      <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
        Select a specific Job Type above to attach and configure Service Options —
        an option must be mapped to an exact Job Type, not the service as a whole
        (the same option can be Optional under Installation and unavailable under Repair).
      </p>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 12 }}>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
          Add-ons and options attached to this exact Job Type. Price is set by the tenant
          (Tenant Setup &gt; Options &amp; Add-ons), never here.
        </p>
        {canWrite && (
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            {otherJobTypes.length > 0 && (
              <button onClick={() => setShowCopy(v => !v)} style={{ fontSize: 12, fontWeight: 600, padding: "6px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer" }}>
                Copy from Job Type
              </button>
            )}
            <button onClick={() => setShowAdd(v => !v)} style={{ fontSize: 12, fontWeight: 600, padding: "6px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
              <Plus size={13}/> Add Option
            </button>
          </div>
        )}
      </div>
      {showCopy && (
        <div style={{ marginBottom: 14, padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 8px" }}>
            Copies each option as a new, independent mapping for this Job Type — editing it here will never change the source Job Type's published options.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {otherJobTypes.map(l => (
              <button key={l.job_type_id} onClick={() => copyFrom(l.job_type_id)} disabled={copying}
                style={{ fontSize: 12, padding: "6px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", cursor: copying ? "default" : "pointer" }}>
                {l.job_type.label}
              </button>
            ))}
          </div>
        </div>
      )}
      {showAdd && (
        <AddOptionPicker masterServiceId={masterServiceId} jobTypeId={jobTypeId}
          existingOptionIds={mappings.map(m => m.service_option_id)}
          onAdded={() => { setShowAdd(false); mappingsApi.refetch(); onChanged(); notify("Option attached to this Job Type."); }}
          onError={(msg) => notify(msg, "error")}/>
      )}
      {mappings.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No options mapped to this Job Type yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {mappings.map(m => (
            <div key={m.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", flexWrap: "wrap", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{m.option.name}</span>
                <code style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{m.option.code}</code>
                <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 7px", borderRadius: 999,
                  background: m.usage === "REQUIRED" ? "var(--brand)" : "var(--surface)", color: m.usage === "REQUIRED" ? "white" : "var(--text-secondary)",
                  border: "1px solid var(--border)" }}>{m.usage}</span>
                <Chip>{m.available_after_inspection ? "Inspection" : "Customer booking"}</Chip>
                {m.quantity_supported && (
                  <Chip>Qty {m.minimum_quantity ?? 1}–{m.maximum_quantity ?? "∞"}{m.measurement_unit ? ` ${m.measurement_unit}` : ""}</Chip>
                )}
                {canWrite ? (
                  <>
                    <label style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
                      <input type="checkbox" checked={m.customer_selectable} onChange={() => toggleFlag(m, "customer_selectable")}/> Customer
                    </label>
                    <label style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
                      <input type="checkbox" checked={m.technician_selectable} onChange={() => toggleFlag(m, "technician_selectable")}/> Technician (post-inspection)
                    </label>
                  </>
                ) : (
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                    {m.customer_selectable ? "Customer-selectable" : "Not customer-selectable"}
                    {m.technician_selectable ? " · Technician post-inspection" : ""}
                  </span>
                )}
              </div>
              {canWrite && (
                <button onClick={() => handleRemove(m)} style={{ fontSize: 11, fontWeight: 600, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer" }}>
                  Detach
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Checklist tab -- maps a PUBLISHED checklist template version (owned by
// the standalone Checklist Library, /admin/checklists) to this exact
// Job-Type Blueprint. Does not re-implement template authoring here --
// only mapping (phase/actor/usage/gate/conditions). ───────────────────────
function ChecklistTab({ masterServiceJobTypeId, canWrite, notify, onChanged }: {
  masterServiceJobTypeId: string | null; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const templatesApi = useApi(useCallback(() => checklistCatalogApi.listTemplates(), []), []);
  const mappingsApi = useApi(useCallback(() => checklistCatalogApi.listMappings(), []), []);
  const [showAdd, setShowAdd] = useState(false);
  const disableAction = useAction(checklistCatalogApi.disableMapping);
  const [disablingId, setDisablingId] = useState<string | null>(null);

  if (!masterServiceJobTypeId) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-tertiary)" }}>
        <ListChecks size={28} style={{ opacity: 0.3, marginBottom: 10 }}/>
        <p style={{ fontSize: 13, margin: 0 }}>Select a specific job type above, and add it to this service, to map checklists.</p>
      </div>
    );
  }
  if (templatesApi.error) return <SectionError title="Couldn't load checklist templates" error={templatesApi.error} requestId={templatesApi.requestId} onRetry={templatesApi.refetch}/>;
  if (mappingsApi.error) return <SectionError title="Couldn't load checklist mappings" error={mappingsApi.error} requestId={mappingsApi.requestId} onRetry={mappingsApi.refetch}/>;
  if (templatesApi.loading || mappingsApi.loading) return <Skeleton height={140}/>;

  const published = (templatesApi.data ?? []).filter(t => t.latest_version?.status === "PUBLISHED");
  const ownMappings = (mappingsApi.data ?? []).filter(m => m.master_service_job_type_id === masterServiceJobTypeId);
  const templateByVersion = new Map(published.map(t => [t.latest_version!.id, t]));

  async function disable(mappingId: string) {
    if (!canWrite) return;
    setDisablingId(mappingId);
    const result = await disableAction.execute(mappingId);
    setDisablingId(null);
    if (result) { mappingsApi.refetch(); onChanged(); notify("Checklist mapping disabled."); }
    else notify(disableAction.error || "Couldn't disable this mapping.", "error");
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
        <AddChecklistMappingForm masterServiceJobTypeId={masterServiceJobTypeId} publishedTemplates={published}
          onAdded={() => { setShowAdd(false); mappingsApi.refetch(); onChanged(); notify("Checklist mapped to this Job Type."); }}
          onError={(msg) => notify(msg, "error")}/>
      )}
      {ownMappings.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No checklists mapped to this Job Type yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {ownMappings.map(m => {
            const template = templateByVersion.get(m.checklist_template_version_id);
            return (
              <div key={m.id} style={{ padding: "10px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, flexWrap: "wrap" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{template?.name ?? "Checklist"}</span>
                    <Chip>{m.phase}</Chip>
                    <Chip tone={m.usage === "REQUIRED" ? "brand" : "default"}>{m.usage}</Chip>
                    <Chip>{m.actor}</Chip>
                    <Chip>{m.completion_gate.replace(/^REQUIRE_/, "").replace(/_/g, " ")}</Chip>
                  </div>
                  {canWrite && m.status === "active" && (
                    <button onClick={() => disable(m.id)} disabled={disablingId === m.id}
                      style={{ fontSize: 11, fontWeight: 600, color: "var(--danger-text)", background: "none", border: "none", cursor: disablingId === m.id ? "default" : "pointer", opacity: disablingId === m.id ? 0.6 : 1 }}>
                      {disablingId === m.id ? "Disabling…" : "Disable"}
                    </button>
                  )}
                </div>
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

function AddChecklistMappingForm({ masterServiceJobTypeId, publishedTemplates, onAdded, onError }: {
  masterServiceJobTypeId: string; publishedTemplates: ChecklistTemplateRow[];
  onAdded: () => void; onError: (msg: string) => void;
}) {
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [versionId, setVersionId] = useState("");
  const [phase, setPhase] = useState("inspection");
  const [usage, setUsage] = useState<ChecklistUsage>("REQUIRED");
  const [actor, setActor] = useState<ChecklistActor>("TECHNICIAN");
  const [gate, setGate] = useState<ChecklistCompletionGate>("NONE");
  const [newName, setNewName] = useState("");
  const [newItemLabel, setNewItemLabel] = useState("");
  const create = useAction(useCallback(async (vId: string) => {
    return checklistCatalogApi.createMapping({
      master_service_job_type_id: masterServiceJobTypeId, checklist_template_version_id: vId,
      phase, usage, actor, completion_gate: gate,
    });
  }, [masterServiceJobTypeId, phase, usage, actor, gate]));
  const quickCreate = useAction(useCallback(async () => {
    const code = newName.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_").slice(0, 60);
    const template = await checklistCatalogApi.createTemplate({ name: newName.trim(), code, purpose: "EXECUTION" as ChecklistPurpose });
    const draft = await checklistCatalogApi.getOrCreateDraftVersion(template.id);
    const section = await checklistCatalogApi.addSection(draft.id, "Checklist");
    await checklistCatalogApi.addItem(section.id, { item_type: "CHECKBOX" as ChecklistItemType, label: newItemLabel.trim() || "Completed" });
    const published = await checklistCatalogApi.publishVersion(draft.id, "Created from Catalog Workspace");
    return published;
  }, [newName, newItemLabel]));

  async function submit() {
    if (!versionId) return;
    const result = await create.execute(versionId);
    if (result) onAdded(); else onError(create.error || "Couldn't map this checklist.");
  }

  async function submitNew() {
    if (!newName.trim()) return;
    const published = await quickCreate.execute();
    if (!published) { onError(quickCreate.error || "Couldn't create the checklist template."); return; }
    const result = await create.execute(published.id);
    if (result) onAdded(); else onError(create.error || "Template created, but mapping it failed.");
  }

  const smallSelect: React.CSSProperties = { fontSize: 12, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" };

  return (
    <div style={{ marginBottom: 14, padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 6 }}>
        <button onClick={() => setMode("existing")} style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 999, border: "1px solid var(--border)", background: mode === "existing" ? "var(--brand)" : "var(--surface)", color: mode === "existing" ? "white" : "var(--text-secondary)", cursor: "pointer" }}>Use existing</button>
        <button onClick={() => setMode("new")} style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 999, border: "1px solid var(--border)", background: mode === "new" ? "var(--brand)" : "var(--surface)", color: mode === "new" ? "white" : "var(--text-secondary)", cursor: "pointer" }}>Create new</button>
      </div>

      {mode === "existing" ? (
        <select value={versionId} onChange={e => setVersionId(e.target.value)} style={smallSelect}>
          <option value="">— Select published checklist —</option>
          {publishedTemplates.map(t => <option key={t.id} value={t.latest_version!.id}>{t.name} (v{t.latest_version!.version_number})</option>)}
        </select>
      ) : (
        <>
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="New checklist name (e.g. Pre-Installation Safety Check)" style={{ ...smallSelect, width: "100%", boxSizing: "border-box" }}/>
          <input value={newItemLabel} onChange={e => setNewItemLabel(e.target.value)} placeholder="First checklist item (e.g. Power supply verified)" style={{ ...smallSelect, width: "100%", boxSizing: "border-box" }}/>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Creates a single-item published checklist; add more items later from the Checklist Library.</p>
        </>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input value={phase} onChange={e => setPhase(e.target.value)} placeholder="Phase (e.g. inspection)" style={{ ...smallSelect, flex: 1, minWidth: 120 }}/>
        <select value={usage} onChange={e => setUsage(e.target.value as ChecklistUsage)} style={smallSelect}>
          <option value="DISABLED">DISABLED</option><option value="OPTIONAL">OPTIONAL</option><option value="REQUIRED">REQUIRED</option>
        </select>
        <select value={actor} onChange={e => setActor(e.target.value as ChecklistActor)} style={smallSelect}>
          <option value="TECHNICIAN">TECHNICIAN</option><option value="STAFF">STAFF</option><option value="TENANT_ADMIN">TENANT_ADMIN</option><option value="CUSTOMER">CUSTOMER</option>
        </select>
        <select value={gate} onChange={e => setGate(e.target.value as ChecklistCompletionGate)} style={smallSelect}>
          <option value="NONE">No gate</option>
          <option value="REQUIRE_BEFORE_INSPECTION_COMPLETE">Before inspection complete</option>
          <option value="REQUIRE_BEFORE_ESTIMATE_SUBMISSION">Before estimate submission</option>
          <option value="REQUIRE_BEFORE_WORK_START">Before work start</option>
          <option value="REQUIRE_BEFORE_JOB_COMPLETION">Before job completion</option>
          <option value="REQUIRE_BEFORE_HANDOVER">Before handover</option>
        </select>
      </div>
      {mode === "existing" ? (
        <button onClick={submit} disabled={!versionId || create.loading}
          style={{ alignSelf: "flex-start", fontSize: 12, fontWeight: 700, padding: "6px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white", cursor: !versionId || create.loading ? "default" : "pointer" }}>
          {create.loading ? "Mapping…" : "Map Checklist"}
        </button>
      ) : (
        <button onClick={submitNew} disabled={!newName.trim() || quickCreate.loading || create.loading}
          style={{ alignSelf: "flex-start", fontSize: 12, fontWeight: 700, padding: "6px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white", cursor: !newName.trim() || quickCreate.loading || create.loading ? "default" : "pointer" }}>
          {quickCreate.loading || create.loading ? "Creating…" : "Create & Map"}
        </button>
      )}
    </div>
  );
}

// ── Preview tab -- simulates tenant setup / customer booking / technician
// execution from real DRAFT configuration. Read-only; persists nothing. ───
function PreviewTab({ masterServiceId, jobTypeId }: { masterServiceId: string; jobTypeId: string | null }) {
  const dimApi = useApi(useCallback(() => catalogWorkspaceApi.getDimensionGrid(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]), [masterServiceId, jobTypeId]);
  const optionsApi = useApi(useCallback(() => jobTypeId ? catalogWorkspaceApi.listServiceOptionMappings(masterServiceId, jobTypeId) : Promise.resolve([]), [masterServiceId, jobTypeId]), [masterServiceId, jobTypeId]);
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
  const requiredDims = enabledDims.filter(d => d.config.required);
  const options = optionsApi.data ?? [];
  const questions = questionsApi.data?.questions ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        Preview simulates the derived experience from current draft configuration. Nothing here is saved or booked.
      </p>
      <PreviewSection title="Tenant Setup Preview">
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)" }}>
          {enabledDims.length === 0 && <li>No dimension step (Type/Brand disabled for this job type).</li>}
          {enabledDims.map(d => <li key={d.dimension.id}>{d.dimension.name} — {d.config.required ? "required" : "optional"} for tenant setup</li>)}
          {options.length === 0 && <li>No options step (no options mapped to this job type).</li>}
          {options.length > 0 && <li>{options.length} option(s) available for the tenant to enable and price.</li>}
        </ul>
      </PreviewSection>
      <PreviewSection title="Customer Booking Preview">
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)" }}>
          {requiredDims.map(d => <li key={d.dimension.id}>Customer selects {d.dimension.name}</li>)}
          {questions.filter(q => q.customer_visible).map(q => <li key={q.id}>{q.label}{q.required ? " (required)" : ""}</li>)}
          {options.filter(o => o.customer_selectable).map(o => <li key={o.id}>Customer may add: {o.option.name}</li>)}
        </ul>
      </PreviewSection>
      <PreviewSection title="Technician Execution Preview">
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)" }}>
          {options.filter(o => o.technician_selectable).map(o => <li key={o.id}>Technician may add post-inspection: {o.option.name}</li>)}
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

// ── Add Option picker — attaches an existing reusable option template to
// this exact Job Type. Does not create new global option templates here. ──
function AddOptionPicker({ masterServiceId, jobTypeId, existingOptionIds, onAdded, onError }: {
  masterServiceId: string; jobTypeId: string; existingOptionIds: string[];
  onAdded: () => void; onError: (msg: string) => void;
}) {
  const [search, setSearch] = useState("");
  const searchApi = useApi(
    useCallback(() => catalogWorkspaceApi.searchServiceOptionTemplates(search.trim()), [search]),
    [search],
  );
  const addAction = useAction(catalogWorkspaceApi.addServiceOptionMapping);
  const results = (searchApi.data?.items ?? []).filter(
    it => !existingOptionIds.includes(String(it.id))) as { id: string; name: string; code: string }[];

  async function attach(serviceOptionId: string) {
    const result = await addAction.execute(masterServiceId, {
      service_option_id: serviceOptionId, job_type_id: jobTypeId,
      usage: "OPTIONAL", customer_selectable: true,
    });
    if (result) onAdded();
    else onError(addAction.error || "Couldn't attach this option.");
  }

  return (
    <div style={{ marginBottom: 14, padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <Search size={13} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search the option library…"
          aria-label="Search options"
          style={{ flex: 1, fontSize: 13, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}/>
      </div>
      {searchApi.error ? (
        <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{searchApi.error}</p>
      ) : searchApi.loading ? (
        <Skeleton height={60}/>
      ) : results.length === 0 ? (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          No matching options{existingOptionIds.length > 0 ? " (already-mapped options are hidden)" : ""}.
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
    </div>
  );
}

const QUESTION_INPUT_TYPES = ["single_select", "multi_select", "boolean", "number", "text", "photo", "date", "time", "address"] as const;
const QUESTION_ANSWER_SOURCES = ["static", "free"] as const; // dimension/problem sources need a picked dimension/problem -- out of scope for this minimal form, still creatable via the API directly.

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
  const [iconUrl, setIconUrl] = useState<string | null>(null);
  const createAction = useAction(catalogWorkspaceApi.createQuestion);

  async function submit() {
    const key = slugifyKey(label);
    if (!label.trim() || !key) return;
    const result = await createAction.execute({
      master_service_id: masterServiceId, job_type_id: jobTypeId,
      question_key: key, label: label.trim(), input_type: inputType,
      answer_source: answerSource, required, icon_url: iconUrl || undefined,
    });
    if (result) { setLabel(""); setRequired(false); setIconUrl(null); onAdded(); } else onError();
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
      <IconPicker context="question_icon" value={iconUrl} onChange={setIconUrl}/>
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
  const questions = questionsApi.data?.questions ?? [];
  const [showAdd, setShowAdd] = useState(false);
  const [expandedRulesFor, setExpandedRulesFor] = useState<string | null>(null);

  // Fetched once per sub-tab visit -- the reference lists the rule builder
  // needs to resolve condition_type -> a concrete picker (job type / problem
  // mapped to this service / dimension / another question on this service).
  const jobTypesApi = useApi(useCallback(() => catalogWorkspaceApi.listJobTypes(), []), []);
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
                <div>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 3px" }}>{q.label}</p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                    {q.input_type} · {q.answer_source}
                    {q.rules.length > 0 && ` · ${q.rules.length} show-when rule${q.rules.length === 1 ? "" : "s"}`}
                    {q.deepseek_enabled && " · DeepSeek"}
                  </p>
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
// These 5 flags are real, individually-editable columns on the master service
// record (app/engines/admin_catalog/service.py update_master_service). There
// is still no unified, independently-versioned "Tenant Setup Rules" resource
// distinct from the master service (a real, smaller remaining gap versus a
// dedicated sub-entity) -- but the values below are live and this tab writes
// them for real, not a read-only mock.
const TENANT_SETUP_RULES: { field: keyof HsConsoleService; label: string }[] = [
  { field: "is_type_required",   label: "Provider must select service type" },
  { field: "is_brand_required",  label: "Provider must select supported brands" },
  { field: "requires_address",   label: "Provider must configure service area" },
  { field: "requires_schedule",  label: "Provider must configure availability" },
  { field: "requires_issue_type", label: "Customer photo/issue upload allowed" },
];

function TenantSetupRulesTab({ s, canWrite, notify, onChanged }: {
  s: HsConsoleService | undefined; canWrite: boolean;
  notify: (m: string, t?: "success" | "error") => void; onChanged: () => void;
}) {
  const updateAction = useAction(homeServicesCatalogConsoleApi.updateService);
  if (!s) return <Skeleton height={140}/>;

  async function toggle(field: keyof HsConsoleService, label: string) {
    if (!canWrite || !s) return;
    const result = await updateAction.execute(s.service_id, { [field]: !s[field] });
    if (result) { notify(`${label} updated.`); onChanged(); }
    else notify("Couldn't update this rule.", "error");
  }

  return (
    <div>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>
        What a tenant must configure before this service can be published and bookable. Changing a rule here
        publishes a new blueprint version, the same as any other structural edit.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {TENANT_SETUP_RULES.map(r => (
          <div key={r.field} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{r.label}</span>
            <FlagPill on={!!s[r.field]} onClick={() => toggle(r.field, r.label)} disabled={!canWrite || updateAction.loading}/>
          </div>
        ))}
      </div>
    </div>
  );
}
