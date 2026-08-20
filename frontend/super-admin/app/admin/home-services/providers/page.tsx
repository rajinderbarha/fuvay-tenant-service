"use client";
/**
 * Home Services Providers — one consolidated workspace with 3 tabs:
 * Provider Directory, Onboarding Queue, Suspended & Archived. Replaces the
 * need for separate "All Providers" / "New Business Requests" / "Provider
 * Onboarding Queue" pages for Home Services -- the Onboarding Queue tab
 * reuses the existing, real provider_portal onboarding engine
 * (/v1/admin/onboarding/providers, already vertical-capable via
 * vertical_type) rather than duplicating it.
 *
 * Real bug fixed in this pass (app/engines/tenant_engine/admin_service.py):
 * verify_tenant/reject_verification/request_changes previously allowed
 * action on "not_started" (Not Submitted) providers -- the backend now
 * rejects with PROVIDER_NOT_SUBMITTED; this page mirrors that by hiding
 * the actions rather than just disabling them, but the backend guard is
 * the actual authority, not this frontend check.
 *
 * Multi-vertical membership: Tenant.vertical is a single string column
 * today (no TenantBusinessVertical join table exists yet), so "Home
 * Services membership" is Tenant.vertical == "home_services" -- correct
 * for the current schema and isolated by construction.
 */
import { useCallback, useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { FileText, Search, SlidersHorizontal } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Input, DataTable, Skeleton, Modal, Pagination, SummaryCard, Select } from "../../../../components/shared/ui";
import { PageHeader } from "../../../../components/shared/layout";
import OperationsDirectoryControls from "../../../../components/enterprise/OperationsDirectoryControls";
import type { ColumnDef } from "../../../../components/enterprise/EnterpriseColumnManager";
import { hsProviderDirectoryApi, adminOnboardingProvidersApi, adminTenantApi } from "../../../../lib/api";
import { openAdminMediaPreview } from "../../../../lib/open-admin-media-preview";
import { useApi } from "../../../../hooks/useApi";

function dt(v?: string | null) {
  return v ? new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}
type TabKey = "directory" | "onboarding" | "changes" | "suspended";
const TABS: { key: TabKey; label: string }[] = [
  { key: "directory", label: "Provider Directory" },
  { key: "onboarding", label: "Onboarding Queue" },
  { key: "changes", label: "Profile Change Requests" },
  { key: "suspended", label: "Suspended & Archived" },
];

export default function HomeServicesProvidersPage() {
  return (
    <Suspense fallback={<Skeleton height={400} />}>
      <HomeServicesProvidersWorkspace />
    </Suspense>
  );
}

function HomeServicesProvidersWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const tab = (params.get("tab") as TabKey) || "directory";

  function setTab(t: TabKey) {
    router.replace(`/admin/home-services/providers?tab=${t}`);
  }

  return (
    <AdminLayout activeNav="home_services-providers">
      <PageHeader title="Home Services Providers"
        description="One operational workspace for provider verification, health, lifecycle and approved profile changes."
        breadcrumbs={[{ label: "Home Services", href: "/admin/home-services/dashboard" }, { label: "Providers" }]}
        statusBadge={<Badge variant="info">Vertical scoped</Badge>}
        primaryAction={<Link href="/admin/audit-logs?resource_type=tenant_onboarding" style={{ display:"inline-flex", alignItems:"center", gap:6, height:34, padding:"0 12px", border:"1px solid var(--border)", borderRadius:8, color:"var(--text-secondary)", textDecoration:"none", fontSize:12, fontWeight:600 }}><FileText size={14}/>Audit trail</Link>} />

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", margin: "16px 0" }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{ padding: "10px 14px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === t.key ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === t.key ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer" }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "directory" && <DirectoryTab />}
      {tab === "onboarding" && <OnboardingQueueTab />}
      {tab === "changes" && <ProfileChangeRequestsTab />}
      {tab === "suspended" && <SuspendedArchivedTab />}

    </AdminLayout>
  );
}

function RuntimeDot({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: ok ? "var(--success-text, #0a7c3f)" : "var(--warning-text, #b45309)" }} />
      <div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{label}</div>
        <div style={{ fontSize: 12, fontWeight: 600 }}>{value}</div>
      </div>
    </div>
  );
}
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 2 }}>{label}</div>
      <div style={{ fontWeight: 600 }}>{value}</div>
    </div>
  );
}

// ── Tab 1: Provider Directory ────────────────────────────────────────────────

function DirectoryTab() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") || "";
  const [inputQ, setInputQ] = useState(q);
  const status = params.get("status") || undefined;
  const verification = params.get("verification") || undefined;
  const city = params.get("city") || undefined;
  const state = params.get("state") || undefined;
  const healthBand = params.get("health_band") || undefined;
  const sortBy = params.get("sort_by") || "created_at";
  const sortDir = params.get("sort_dir") || "desc";
  const page = Number(params.get("page") || "1");
  const pageSize = Number(params.get("page_size") || "25");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [columnState, setColumnState] = useState<ColumnDef[]>([
    { key:"business_name", label:"Provider", visible:true, order:0 },
    { key:"registration_status", label:"Registration", visible:true, order:1 },
    { key:"verification_status", label:"Verification", visible:true, order:2 },
    { key:"credit_status", label:"Credits", visible:true, order:3 },
    { key:"deposit_status", label:"Deposit", visible:true, order:4 },
    { key:"health_score", label:"Health", visible:true, order:5 },
    { key:"city", label:"City", visible:true, order:6 },
    { key:"created_at", label:"Registered", visible:true, order:7 },
    { key:"provider_id", label:"Actions", visible:true, order:8 },
  ]);

  function setListState(next: Record<string, string | number | undefined>) {
    const sp = new URLSearchParams(params.toString());
    sp.set("tab", "directory");
    Object.entries(next).forEach(([key, value]) => value === undefined || value === "" ? sp.delete(key) : sp.set(key, String(value)));
    router.replace(`/admin/home-services/providers?${sp.toString()}`);
  }

  useEffect(() => {
    const id = setTimeout(() => { if (inputQ !== q) setListState({ q: inputQ, page: 1 }); }, 350);
    return () => clearTimeout(id);
    // setListState depends on the current URL snapshot; q is the committed value.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputQ, q]);

  const summary = useApi(useCallback(() => hsProviderDirectoryApi.getSummary(q || undefined), [q]), [q]);
  const providers = useApi(useCallback(
    () => hsProviderDirectoryApi.list({ q: q || undefined, status, verification_status: verification,
      city, state, health_band: healthBand, page, page_size: pageSize, sort_by: sortBy, sort_dir: sortDir }),
    [q, status, verification, city, state, healthBand, page, pageSize, sortBy, sortDir]),
    [q, status, verification, city, state, healthBand, page, pageSize, sortBy, sortDir]);
  const s = summary.data as Record<string, unknown> | undefined;

  function filterBy(newStatus: string | undefined) {
    setListState({ status: newStatus, page: 1 });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding={16} style={{ display: "flex", flexWrap: "wrap", gap: 28, alignItems:"center" }}>
        <RuntimeDot label="Directory scope" value="Home Services" ok />
        <RuntimeDot label="Data mode" value="Server paginated" ok />
        <RuntimeDot label="Registration Review" value={`${(s?.pending_verification as number) ?? 0} pending`} ok={((s?.pending_verification as number) ?? 0) === 0} />
        <RuntimeDot label="Active Providers" value={`${(s?.active as number) ?? 0} ready`} ok />
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
        <SummaryCard label="Total Providers" value={(s?.total_providers as number) ?? 0} onClick={() => filterBy(undefined)} />
        <SummaryCard label="Pending Verification" value={(s?.pending_verification as number) ?? 0} tone="warning" />
        <SummaryCard label="Active" value={(s?.active as number) ?? 0} tone="success" onClick={() => filterBy("active")} />
        <SummaryCard label="Setup Incomplete" value={(s?.setup_incomplete as number) ?? 0} tone="warning" />
        <SummaryCard label="Changes Requested" value={(s?.changes_requested as number) ?? 0} tone="warning" />
        <SummaryCard label="Suspended" value={(s?.suspended as number) ?? 0} tone="danger" onClick={() => filterBy("suspended")} />
        <SummaryCard label="Rejected" value={(s?.rejected as number) ?? 0} tone="danger" onClick={() => filterBy("rejected")} />
        <SummaryCard label="Needs Attention" value={(s?.needs_attention as number) ?? 0} tone="danger" />
      </div>

      <OperationsDirectoryControls resourceKey="admin_tenants"
        filters={{ q, vertical:"home_services", status, verification_status:verification, city, state, health_band:healthBand }}
        sort={{ sort_by:sortBy, sort_direction:sortDir }} columns={columnState}
        onApplyView={(f, sort) => { const search = String(f.q ?? f.search ?? ""); setInputQ(search); setListState({ q:search, status:String(f.status ?? ""), verification:String(f.verification_status ?? ""), city:String(f.city ?? ""), state:String(f.state ?? ""), health_band:String(f.health_band ?? ""), sort_by:String(sort.sort_by ?? "created_at"), sort_dir:String(sort.sort_direction ?? "desc"), page:1 }); }}
        onColumnsChange={setColumnState} />

      <Card padding={14} style={{ display:"flex", flexDirection:"column", gap:12 }}>
        <div style={{ display:"flex", gap:10, flexWrap:"wrap", alignItems:"center" }}>
          <div style={{ flex:"1 1 320px", position:"relative" }}><Search size={14} style={{ position:"absolute", left:12, top:11, color:"var(--text-tertiary)" }}/><input aria-label="Search providers" placeholder="Search business, owner, email, phone or provider ID" value={inputQ} onChange={e=>setInputQ(e.target.value)} style={{ width:"100%", height:36, padding:"0 12px 0 34px", border:"1px solid var(--border)", borderRadius:8, background:"var(--surface)", color:"var(--text-primary)" }}/></div>
          <Select value={status ?? ""} onChange={v=>setListState({ status:v, page:1 })} options={[{value:"",label:"All statuses"},{value:"active",label:"Active"},{value:"onboarding_pending",label:"Setup incomplete"},{value:"under_review",label:"Under review"},{value:"suspended",label:"Suspended"},{value:"archived",label:"Archived"},{value:"rejected",label:"Rejected"}]}/>
          <Select value={verification ?? ""} onChange={v=>setListState({ verification:v, page:1 })} options={[{value:"",label:"All verification"},{value:"approved",label:"Approved"},{value:"pending",label:"Pending"},{value:"changes_requested",label:"Changes requested"},{value:"rejected",label:"Rejected"}]}/>
          <Btn variant="ghost" icon={<SlidersHorizontal size={14}/>} onClick={()=>setShowAdvanced(v=>!v)}>More filters</Btn>
        </div>
        {showAdvanced && <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))", gap:10, paddingTop:10, borderTop:"1px solid var(--border)" }}>
          <Input placeholder="City" value={city ?? ""} onChange={v=>setListState({ city:v, page:1 })}/><Input placeholder="State" value={state ?? ""} onChange={v=>setListState({ state:v, page:1 })}/>
          <Select value={healthBand ?? ""} onChange={v=>setListState({ health_band:v, page:1 })} options={[{value:"",label:"Any health band"},{value:"gold",label:"Gold"},{value:"silver",label:"Silver"},{value:"bronze",label:"Bronze"},{value:"at_risk",label:"At risk"}]}/>
          <Select value={sortBy} onChange={v=>setListState({ sort_by:v, page:1 })} options={[{value:"created_at",label:"Newest registered"},{value:"business_name",label:"Business name"},{value:"health_score",label:"Health score"},{value:"rating_average",label:"Rating"},{value:"city",label:"City"}]}/>
          <Select value={sortDir} onChange={v=>setListState({ sort_dir:v, page:1 })} options={[{value:"desc",label:"Descending"},{value:"asc",label:"Ascending"}]}/>
        </div>}
      </Card>

      <DataTable
        loading={providers.loading}
        rows={(providers.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No Home Services providers match this view."
        onRowClick={row => router.push(`/admin/home-services/providers/${(row as Record<string, unknown>).provider_id}`)}
        columns={[
          { key: "business_name", label: "Provider" },
          { key: "registration_status", label: "Registration", render: v => <Badge variant={v === "active" ? "success" : v === "suspended" || v === "rejected" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "verification_status", label: "Verification", render: v => <Badge variant={v === "approved" ? "success" : v === "rejected" ? "danger" : v === "changes_requested" ? "warning" : "default"}>{String(v)}</Badge> },
          { key: "credit_status", label: "Credits", render: v => <Badge variant={v === "healthy" ? "success" : "warning"}>{String(v)}</Badge> },
          { key: "deposit_status", label: "Deposit", render: v => <Badge variant={v === "paid" ? "success" : "default"}>{String(v)}</Badge> },
          { key: "health_score", label: "Health", render: v => <span>{Number(v).toFixed(0)}%</span> },
          { key: "city", label: "City" },
          { key: "created_at", label: "Registered", render: v => dt(v as string) },
          { key: "provider_id", label: "Actions", render: v => (
            <span onClick={e => e.stopPropagation()}>
              <Btn variant="ghost" onClick={() => router.push(`/admin/home-services/providers/${v}`)}>View 360°</Btn>
            </span>
          ) },
        ].filter(c => columnState.find(x => x.key === c.key)?.visible)}
      />
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", flexWrap:"wrap", gap:10 }}><Select value={String(pageSize)} onChange={v=>setListState({ page_size:Number(v), page:1 })} options={[{value:"25",label:"25 per page"},{value:"50",label:"50 per page"},{value:"100",label:"100 per page"}]}/><Pagination page={page} total={providers.data?.total ?? 0} pageSize={pageSize} onPage={p => setListState({ page: p })} /></div>
    </div>
  );
}

// ── Tab 2: Onboarding Queue (reuses provider_portal's onboarding engine) ────

function OnboardingQueueTab() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [reviewStatus, setReviewStatus] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);

  const providers = useApi(useCallback(
    () => adminOnboardingProvidersApi.list({ q: q || undefined, vertical_type: "home_services", review_status: reviewStatus, page, page_size: 20 }),
    [q, reviewStatus, page]), [q, reviewStatus, page]);
  const summary = providers.data?.summary;

  function filterBy(rs: string | undefined) { setReviewStatus(rs); setPage(1); }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
        <SummaryCard label="Total in Queue" value={summary?.total ?? 0} onClick={() => filterBy(undefined)} />
        <SummaryCard label="Not Submitted" value={summary?.not_submitted ?? 0} onClick={() => filterBy("not_submitted")} />
        <SummaryCard label="Pending Review" value={summary?.pending_review ?? 0} tone="warning" onClick={() => filterBy("pending_review")} />
        <SummaryCard label="Changes Requested" value={summary?.changes_requested ?? 0} tone="warning" onClick={() => filterBy("changes_requested")} />
        <SummaryCard label="Rejected" value={summary?.rejected ?? 0} tone="danger" onClick={() => filterBy("rejected")} />
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        A &quot;New Business Request&quot; is a provider that registered and holds a Home Services assignment but
        has not yet submitted for review — shown here as Not Submitted, view-only until they submit.
      </p>

      <div style={{ display: "flex", gap: 10 }}>
        <div style={{ flex: 1, maxWidth: 360 }}>
          <Input placeholder="Search business, owner or email..." value={q} onChange={v => { setQ(v); setPage(1); }} />
        </div>
        {reviewStatus && <Btn variant="ghost" onClick={() => filterBy(undefined)}>Clear filter: {reviewStatus} ×</Btn>}
      </div>

      <DataTable
        loading={providers.loading}
        rows={(providers.data?.providers ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No Home Services onboarding records match this view."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).tenant_id))}
        columns={[
          { key: "business_name", label: "Provider", render: (v, row) => String(v ?? (row as Record<string, unknown>).tenant_name ?? "—") },
          { key: "owner_name", label: "Owner", render: v => v ? String(v) : "—" },
          { key: "review_status", label: "Review Status", render: v => (
            <Badge variant={v === "approved" ? "success" : v === "rejected" ? "danger" : v === "changes_requested" ? "warning" : "default"}>
              {String(v).replace(/_/g, " ")}
            </Badge>
          ) },
          { key: "profile_completion_percentage", label: "Completion", render: v => `${v ?? 0}%` },
          { key: "city", label: "City", render: v => v ? String(v) : "—" },
          { key: "created_at", label: "Registered", render: v => dt(v as string) },
          { key: "tenant_id", label: "Actions", render: v => (
            <span onClick={e => e.stopPropagation()}>
              <Btn variant="ghost" onClick={() => router.push(`/admin/home-services/providers/${v}`)}>View 360°</Btn>
            </span>
          ) },
        ]}
      />
      <Pagination page={page} total={providers.data?.total ?? 0} pageSize={20} onPage={setPage} />

      <Modal open={!!selected} onClose={() => setSelected(null)} title="Review Provider" size="lg">
        {selected && <OnboardingReviewPanel tenantId={selected} onDone={() => { setSelected(null); providers.refetch(); }} />}
      </Modal>
    </div>
  );
}

function OnboardingReviewPanel({ tenantId, onDone }: { tenantId: string; onDone: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [decision, setDecision] = useState<"changes" | "reject" | null>(null);
  const [documentDecision, setDocumentDecision] = useState<{ documentId: string; decision: "changes_requested" | "rejected" } | null>(null);
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  // Re-fetch the single record fresh so actions reflect the latest server state.
  const record = useApi(useCallback(() => adminOnboardingProvidersApi.get(tenantId), [tenantId]), [tenantId]);

  async function run(action: string, fn: () => Promise<unknown>) {
    setBusy(action);
    setActionError(null);
    try { await fn(); onDone(); }
    catch (e) { setActionError(e instanceof Error ? e.message : `Failed to ${action}.`); }
    finally { setBusy(null); }
  }

  function openDecision(nextDecision: "changes" | "reject") {
    setDocumentDecision(null);
    setDecision(nextDecision);
    setReason("");
    setActionError(null);
  }

  function submitDecision() {
    const notes = reason.trim();
    if (!decision || !notes) {
      setActionError(decision === "reject" ? "Enter a rejection reason." : "Describe the changes the provider needs to make.");
      return;
    }
    if (decision === "changes") {
      void run("changes", () => adminOnboardingProvidersApi.requestChanges(tenantId, notes));
    } else {
      void run("reject", () => adminOnboardingProvidersApi.reject(tenantId, notes));
    }
  }

  async function reviewDocument(documentId: string, nextDecision: "verified" | "changes_requested" | "rejected", notes = "") {
    setBusy(`document-${documentId}`);
    setActionError(null);
    try {
      await adminOnboardingProvidersApi.reviewDocument(tenantId, documentId, nextDecision, notes);
      setDocumentDecision(null);
      setReason("");
      await record.refetch();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not save the document review.");
    } finally {
      setBusy(null);
    }
  }

  if (record.loading) return <Skeleton height={200} />;
  const r = record.data;
  if (!r) return <p>Provider not found in the onboarding queue.</p>;

  // Mirrors the backend's own gate (verify_tenant/reject_verification/
  // request_changes all now reject "not_started" as PROVIDER_NOT_SUBMITTED)
  // -- this is a UI convenience, the backend is the actual authority.
  const canAct = r.review_status === "pending_review";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, fontSize: 12 }}>
        <Field label="Business" value={r.business_name ?? r.tenant_name ?? "—"} />
        <Field label="Owner" value={r.owner_name ?? "—"} />
        <Field label="Email" value={r.owner_email ?? "—"} />
        <Field label="Review Status" value={r.review_status.replace(/_/g, " ")} />
        <Field label="Profile Completion" value={`${r.profile_completion_percentage}%`} />
        <Field label="City" value={r.city ?? "—"} />
      </div>

      <Card padding={14}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 13 }}>Setup readiness</h3>
            <p style={{ margin: "3px 0 0", color: "var(--text-tertiary)", fontSize: 11 }}>Server-validated submission snapshot</p>
          </div>
          <Badge variant={r.can_approve ? "success" : "warning"}>{r.can_approve ? "Ready to approve" : `${r.approval_blockers?.length ?? 0} blockers`}</Badge>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 8 }}>
          {(r.setup_sections ?? []).map(section => (
            <div key={section.key} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "9px 10px", display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600 }}>{section.label}</span>
              <Badge variant={section.status === "complete" ? "success" : "warning"}>{section.status.replace(/_/g, " ")}</Badge>
            </div>
          ))}
        </div>
        {(r.approval_blockers?.length ?? 0) > 0 && (
          <div style={{ marginTop: 10, padding: 10, borderRadius: 8, background: "var(--surface-raised)" }}>
            {(r.approval_blockers ?? []).map((blocker, index) => (
              <p key={`${blocker.code}-${index}`} style={{ margin: index ? "5px 0 0" : 0, color: "var(--status-warning)", fontSize: 11 }}>• {blocker.message}</p>
            ))}
          </div>
        )}
      </Card>

      <Card padding={14}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 13 }}>Verification documents</h3>
            <p style={{ margin: "3px 0 0", color: "var(--text-tertiary)", fontSize: 11 }}>Required files must be reviewed individually before approval.</p>
          </div>
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{r.document_summary?.verified ?? 0}/{r.document_summary?.required ?? 0} verified</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {(r.documents ?? []).map(document => {
            const reviewable = Boolean(document.document_id) && ["pending_review", "changes_requested"].includes(document.status);
            return (
              <div key={document.document_id ?? document.doc_type} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 10 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <div style={{ minWidth: 180 }}>
                    <div style={{ fontSize: 12, fontWeight: 700 }}>{document.label}{document.required ? " *" : ""}</div>
                    <div style={{ marginTop: 3, fontSize: 11, color: "var(--text-tertiary)" }}>Version {document.version ?? "—"} · {document.uploaded_at ? dt(document.uploaded_at) : "Not uploaded"}</div>
                  </div>
                  <Badge variant={document.status === "verified" ? "success" : document.status === "rejected" ? "danger" : "warning"}>{document.status.replace(/_/g, " ")}</Badge>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {document.media_asset_id && <Btn variant="ghost" onClick={async () => {
                      setActionError(null);
                      try { await openAdminMediaPreview(document.media_asset_id!); }
                      catch (error) { setActionError(error instanceof Error ? error.message : "Could not open this document."); }
                    }}>View</Btn>}
                    {reviewable && <Btn variant="ghost" disabled={busy !== null} onClick={() => void reviewDocument(document.document_id!, "verified")}>Verify</Btn>}
                    {reviewable && <Btn variant="ghost" disabled={busy !== null} onClick={() => { setDocumentDecision({ documentId: document.document_id!, decision: "changes_requested" }); setReason(""); setDecision(null); }}>Request changes</Btn>}
                    {reviewable && <Btn variant="ghost" disabled={busy !== null} onClick={() => { setDocumentDecision({ documentId: document.document_id!, decision: "rejected" }); setReason(""); setDecision(null); }}>Reject</Btn>}
                  </div>
                </div>
                {documentDecision?.documentId === document.document_id && (
                  <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
                    <textarea value={reason} onChange={event => setReason(event.target.value)} rows={3} autoFocus
                      placeholder={documentDecision.decision === "rejected" ? "Explain why this document is invalid." : "Explain exactly what must be replaced or corrected."}
                      style={{ width: "100%", resize: "vertical", border: "1px solid var(--border-default)", borderRadius: 8, padding: 10, background: "var(--surface-raised)", color: "var(--text-primary)", font: "inherit" }} />
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                      <Btn variant="primary" disabled={!reason.trim() || busy !== null} onClick={() => void reviewDocument(document.document_id!, documentDecision.decision, reason.trim())}>Save review</Btn>
                      <Btn variant="ghost" disabled={busy !== null} onClick={() => { setDocumentDecision(null); setReason(""); }}>Cancel</Btn>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          {!r.documents?.length && <p style={{ margin: 0, color: "var(--text-tertiary)", fontSize: 12 }}>No document manifest is available.</p>}
        </div>
      </Card>

      {!canAct && (
        <Card padding={14}>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
            {r.review_status === "not_submitted"
              ? "This provider has not submitted onboarding for review yet — view only until they submit."
              : r.review_status === "changes_requested"
              ? "Changes were requested. Review actions will reopen after the provider updates and resubmits."
              : r.review_status === "approved"
              ? "Already approved and active."
              : "No review action available for this status."}
          </p>
        </Card>
      )}

      {canAct && !decision && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn variant="primary" disabled={busy === "approve" || !r.can_approve}
            onClick={() => run("approve", () => adminOnboardingProvidersApi.approve(tenantId))}>
            {busy === "approve" ? "Approving…" : "Approve setup"}
          </Btn>
          <Btn variant="ghost" disabled={busy === "changes"}
            onClick={() => openDecision("changes")}>
            {busy === "changes" ? "Requesting…" : "Request Changes"}
          </Btn>
          <Btn variant="ghost" disabled={busy === "reject"}
            onClick={() => openDecision("reject")}>
            {busy === "reject" ? "Rejecting…" : "Reject"}
          </Btn>
        </div>
      )}

      {canAct && decision && (
        <Card padding={14}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <label htmlFor="provider-review-reason" style={{ fontSize: 12, fontWeight: 700 }}>
              {decision === "reject" ? "Rejection reason" : "Changes required"}
            </label>
            <textarea
              id="provider-review-reason"
              value={reason}
              onChange={event => { setReason(event.target.value); setActionError(null); }}
              rows={4}
              autoFocus
              placeholder={decision === "reject"
                ? "Explain why this setup cannot be approved."
                : "Tell the provider exactly what to update before resubmitting."}
              style={{
                width: "100%",
                resize: "vertical",
                border: "1px solid var(--border-default)",
                borderRadius: 8,
                padding: 10,
                background: "var(--surface-raised)",
                color: "var(--text-primary)",
                font: "inherit",
              }}
            />
            {actionError && <p role="alert" style={{ margin: 0, color: "var(--status-danger)", fontSize: 12 }}>{actionError}</p>}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Btn variant={decision === "reject" ? "ghost" : "primary"} disabled={busy !== null} onClick={submitDecision}>
                {busy ? "Saving…" : decision === "reject" ? "Confirm rejection" : "Send change request"}
              </Btn>
              <Btn variant="ghost" disabled={busy !== null} onClick={() => { setDecision(null); setReason(""); setActionError(null); }}>
                Cancel
              </Btn>
            </div>
          </div>
        </Card>
      )}

      {canAct && !decision && actionError && (
        <p role="alert" style={{ margin: 0, color: "var(--status-danger)", fontSize: 12 }}>{actionError}</p>
      )}
    </div>
  );
}

// ── Profile change requests ──────────────────────────────────────────────────

function ProfileChangeRequestsTab() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const requests = useApi(useCallback(() => adminTenantApi.listProfileChangeRequests({ q:q || undefined, vertical_type:"home_services", page, page_size:20 }), [q, page]), [q, page]);
  const [busy, setBusy] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function approve(tenantId: string) {
    setBusy(tenantId); setError(null);
    try { await adminTenantApi.approveProfileChangeRequest(tenantId); await requests.refetch(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not approve this request."); }
    finally { setBusy(null); }
  }
  async function reject() {
    if (!rejecting || !reason.trim()) { setError("Enter a rejection reason."); return; }
    setBusy(rejecting); setError(null);
    try {
      await adminTenantApi.rejectProfileChangeRequest(rejecting, reason.trim());
      setRejecting(null); setReason(""); await requests.refetch();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not reject this request."); }
    finally { setBusy(null); }
  }

  if (requests.loading) return <Skeleton height={300}/>;
  if (requests.error) return <Card padding={24}><p role="alert" style={{ margin: 0, color: "var(--status-danger)", fontSize: 12 }}>Could not load profile change requests: {requests.error}</p></Card>;
  const items = requests.data?.change_requests ?? [];
  return <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
    <Card padding={14}><p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>Approved identity stays published until the requested fields and fresh supporting documents are reviewed together.</p></Card>
    <div style={{ maxWidth:380 }}><Input placeholder="Search profile change requests" value={q} onChange={v=>{setQ(v);setPage(1)}}/></div>
    {error && <p role="alert" style={{ margin: 0, color: "var(--status-danger)", fontSize: 12 }}>{error}</p>}
    {items.length === 0 ? <Card padding={30}><p style={{ textAlign: "center", margin: 0, color: "var(--text-tertiary)" }}>No profile changes are awaiting review.</p></Card> : items.map(item => <Card key={item.tenant_id} padding={18}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 14, flexWrap: "wrap" }}>
        <div><h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{item.current_business_name ?? "Unnamed provider"}</h3><p style={{ margin: 0, color: "var(--text-tertiary)", fontSize: 11.5 }}>Submitted {dt(item.submitted_at)}</p></div>
        <Badge variant={item.documents_ready ? "success" : "warning"}>{item.documents_ready ? "Ready for decision" : "Waiting for documents"}</Badge>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 10, marginTop: 14 }}>
        {Object.entries(item.requested_fields).map(([field, value]) => <div key={field} style={{ padding: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 8 }}><div style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{field.replace(/_/g, " ")}</div><div style={{ marginTop: 3, fontSize: 12.5, fontWeight: 600 }}>{String(value ?? "—")}</div></div>)}
      </div>
      {item.documents.length > 0 && <div style={{ marginTop: 14 }}><p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700 }}>Supporting documents</p>{item.documents.map(doc => <div key={doc.doc_type} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, padding: "8px 0", borderTop: "1px solid var(--border)", fontSize: 12 }}><span>{doc.doc_type.replace(/_/g, " ")}</span><Badge variant={doc.submitted_for_request && ["pending_review", "verified"].includes(doc.status) ? "success" : "warning"}>{doc.status.replace(/_/g, " ")}</Badge></div>)}</div>}
      <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}><Btn variant="primary" disabled={!item.documents_ready || busy === item.tenant_id} onClick={() => approve(item.tenant_id)}>{busy === item.tenant_id ? "Approving…" : "Approve & publish"}</Btn><Btn variant="ghost" disabled={busy === item.tenant_id} onClick={() => { setRejecting(item.tenant_id); setReason(""); setError(null); }}>Reject</Btn></div>
    </Card>)}
    <Pagination page={page} total={requests.data?.total ?? requests.data?.count ?? 0} pageSize={20} onPage={setPage}/>
    <Modal open={!!rejecting} onClose={() => setRejecting(null)} title="Reject profile change"><div style={{ display: "flex", flexDirection: "column", gap: 10 }}><label htmlFor="profile-change-reason" style={{ fontSize: 12, fontWeight: 700 }}>Reason for the tenant</label><textarea id="profile-change-reason" rows={4} value={reason} onChange={e => setReason(e.target.value)} style={{ padding: 10, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-raised)", color: "var(--text-primary)", font: "inherit" }}/><div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><Btn variant="ghost" onClick={() => setRejecting(null)}>Cancel</Btn><Btn variant="primary" onClick={reject}>Reject request</Btn></div></div></Modal>
  </div>;
}

// ── Tab 4: Suspended & Archived ──────────────────────────────────────────────

function SuspendedArchivedTab() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const records = useApi(useCallback(() => hsProviderDirectoryApi.list({ q:q || undefined, status_in:"suspended,archived", page, page_size:25 }), [q, page]), [q, page]);
  const summary = useApi(useCallback(() => hsProviderDirectoryApi.getSummary(q || undefined), [q]), [q]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <SummaryCard label="Suspended" value={summary.data?.suspended ?? 0} tone="danger" />
        <SummaryCard label="Archived" value={summary.data?.archived ?? 0} />
      </div>
      <div style={{ maxWidth: 360 }}>
        <Input placeholder="Search business, owner, email or phone..." value={q} onChange={v=>{setQ(v);setPage(1)}} />
      </div>
      <DataTable
        loading={records.loading}
        rows={(records.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No suspended or archived Home Services providers."
        onRowClick={row => router.push(`/admin/home-services/providers/${(row as Record<string, unknown>).provider_id}`)}
        columns={[
          { key: "business_name", label: "Provider" },
          { key: "registration_status", label: "Status", render: v => <Badge variant="danger">{String(v)}</Badge> },
          { key: "suspension_reason", label: "Reason", render: v => v ? String(v) : "—" },
          { key: "suspended_at", label: "Suspended At", render: v => dt(v as string) },
          { key: "city", label: "City" },
          { key: "provider_id", label: "Actions", render: v => (
            <span onClick={e => e.stopPropagation()}>
              <Btn variant="ghost" onClick={() => router.push(`/admin/home-services/providers/${v}`)}>View 360°</Btn>
            </span>
          ) },
        ]}
      />
      <Pagination page={page} total={records.data?.total ?? 0} pageSize={25} onPage={setPage}/>
    </div>
  );
}
