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
import { useCallback, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, FileText } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Input, DataTable, Skeleton, Modal, Pagination, SummaryCard,} from "../../../../components/shared/ui";
import { hsProviderDirectoryApi, adminOnboardingProvidersApi, adminTenantApi } from "../../../../lib/api";
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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>Home Services Providers</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
            Review, verify and operate businesses registered for Home Services.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge variant="info">Home Services only</Badge>
          <Btn variant="ghost" icon={<FileText size={14} />}
            onClick={() => router.push("/admin/audit-logs?resource_type=tenant_onboarding")}>View Audit</Btn>
          <Btn variant="ghost" icon={<Download size={14} />} onClick={async () => {
            const data = await hsProviderDirectoryApi.export();
            if (data.items.length === 0) { alert("Nothing to export."); return; }
            const headers = Object.keys(data.items[0]);
            const csv = [headers.join(","), ...data.items.map(r => headers.map(h => JSON.stringify(r[h] ?? "")).join(","))].join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url; a.download = "home-services-providers.csv"; a.click();
            URL.revokeObjectURL(url);
          }}>Export</Btn>
        </div>
      </div>

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
  const status = params.get("status") || undefined;
  const page = Number(params.get("page") || "1");

  function setListState(next: { q?: string; status?: string | undefined; page?: number }) {
    const sp = new URLSearchParams(params.toString());
    sp.set("tab", "directory");
    if (next.q !== undefined) { if (next.q) sp.set("q", next.q); else sp.delete("q"); }
    if (next.status !== undefined) { if (next.status) sp.set("status", next.status); else sp.delete("status"); }
    if (next.page !== undefined) sp.set("page", String(next.page));
    router.replace(`/admin/home-services/providers?${sp.toString()}`);
  }

  const summary = useApi(useCallback(() => hsProviderDirectoryApi.getSummary(q || undefined), [q]), [q]);
  const providers = useApi(useCallback(
    () => hsProviderDirectoryApi.list({ q: q || undefined, status, page, pageSize: 20 }),
    [q, status, page]), [q, status, page]);
  const s = summary.data as Record<string, unknown> | undefined;

  function filterBy(newStatus: string | undefined) {
    setListState({ status: newStatus, page: 1 });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding={16} style={{ display: "flex", flexWrap: "wrap", gap: 24 }}>
        <RuntimeDot label="Home Services" value="Active" ok />
        <RuntimeDot label="Directory Scope" value="Vertical locked" ok />
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

      <div style={{ display: "flex", gap: 10 }}>
        <div style={{ flex: 1, maxWidth: 360 }}>
          <Input placeholder="Search business, owner, email, phone or registration ID..." value={q}
            onChange={v => setListState({ q: v, page: 1 })} />
        </div>
        {status && <Btn variant="ghost" onClick={() => filterBy(undefined)}>Clear filter: {status} ×</Btn>}
      </div>

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
        ]}
      />
      <Pagination page={page} total={providers.data?.total ?? 0} pageSize={20} onPage={p => setListState({ page: p })} />
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
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  // Re-fetch the single record fresh so actions reflect the latest server state.
  const record = useApi(useCallback(async () => {
    const all = await adminOnboardingProvidersApi.list({ page_size: 200 });
    return all.providers.find(p => p.tenant_id === tenantId) ?? null;
  }, [tenantId]), [tenantId]);

  async function run(action: string, fn: () => Promise<unknown>) {
    setBusy(action);
    setActionError(null);
    try { await fn(); onDone(); }
    catch (e) { setActionError(e instanceof Error ? e.message : `Failed to ${action}.`); }
    finally { setBusy(null); }
  }

  function openDecision(nextDecision: "changes" | "reject") {
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
          <Btn variant="primary" disabled={busy === "approve"}
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
  const requests = useApi(useCallback(() => adminTenantApi.listProfileChangeRequests(), []), []);
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
    <Modal open={!!rejecting} onClose={() => setRejecting(null)} title="Reject profile change"><div style={{ display: "flex", flexDirection: "column", gap: 10 }}><label htmlFor="profile-change-reason" style={{ fontSize: 12, fontWeight: 700 }}>Reason for the tenant</label><textarea id="profile-change-reason" rows={4} value={reason} onChange={e => setReason(e.target.value)} style={{ padding: 10, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-raised)", color: "var(--text-primary)", font: "inherit" }}/><div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><Btn variant="ghost" onClick={() => setRejecting(null)}>Cancel</Btn><Btn variant="primary" onClick={reject}>Reject request</Btn></div></div></Modal>
  </div>;
}

// ── Tab 4: Suspended & Archived ──────────────────────────────────────────────

function SuspendedArchivedTab() {
  const router = useRouter();
  const [q, setQ] = useState("");
  // Two dedicated fetches merged client-side (suspended/archived is a small
  // dataset in practice) rather than adding status_in to the typed helper.
  const suspended = useApi(useCallback(() => hsProviderDirectoryApi.list({ q: q || undefined, status: "suspended", page: 1, pageSize: 100 }), [q]), [q]);
  const archived = useApi(useCallback(() => hsProviderDirectoryApi.list({ q: q || undefined, status: "archived", page: 1, pageSize: 100 }), [q]), [q]);
  const items = [...(suspended.data?.items ?? []), ...(archived.data?.items ?? [])];
  const loading = suspended.loading || archived.loading;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <SummaryCard label="Suspended" value={suspended.data?.total ?? 0} tone="danger" />
        <SummaryCard label="Archived" value={archived.data?.total ?? 0} />
      </div>
      <div style={{ maxWidth: 360 }}>
        <Input placeholder="Search business, owner, email or phone..." value={q} onChange={setQ} />
      </div>
      <DataTable
        loading={loading}
        rows={items as unknown as Record<string, unknown>[]}
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
    </div>
  );
}
