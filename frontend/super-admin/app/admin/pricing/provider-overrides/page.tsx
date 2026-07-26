"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, Input, SectionHeader, DataTable, EmptyState, StatCard, Skeleton,
} from "../../../../components/shared/ui";
import {
  providerOverridesApi, catalogApi, adminTenantsApi,
  type ProviderPricingOverride, type ServiceCategory, type MasterService,
  type OverrideValidationResult, type AuditEntry,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { usePermissions } from "../../../../hooks/usePermissions";
import { ErrorBlock, Field } from "../bargain-rules/page";
import {
  Plus, Check, X, AlertTriangle, Eye, Pencil, Power, PowerOff,
  ClipboardCheck, History, RefreshCw,
} from "lucide-react";

const APPROVAL_BADGE: Record<string, "success" | "warning" | "danger" | "muted"> = {
  approved: "success", pending: "warning", rejected: "danger", not_required: "muted",
};

const money = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN")}`;

const BLANK_FORM = {
  tenant_id: "", master_service_id: "", override_price: "", reason: "",
};

export default function ProviderOverridesPage() {
  const perm = usePermissions();
  const [modal, setModal] = useState<"none" | "create" | "edit" | "reject" | "detail">("none");
  const [form, setForm] = useState(BLANK_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState("");
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  // ── filters ──────────────────────────────────────────────────────────────
  const [search, setSearch] = useState("");
  const [approvalFilter, setApprovalFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // ── validate preview (wizard step + row action) ─────────────────────────
  const [validation, setValidation] = useState<OverrideValidationResult | null>(null);

  // ── detail drawer ────────────────────────────────────────────────────────
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<"overview" | "validation" | "audit">("overview");

  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const catList: ServiceCategory[] = cats.data?.categories ?? [];
  const svcs = useApi(useCallback(
    () => categoryId ? catalogApi.listMasterServices(categoryId) : Promise.resolve({ services: [] as MasterService[] }),
    [categoryId]), [categoryId]);
  const svcList: MasterService[] = svcs.data?.services ?? [];
  const tenants = useApi(useCallback(() => adminTenantsApi.list({ page_size: 100 }), []), []);
  const tenantList = (tenants.data as { items?: { tenant_id: string; tenant_name: string }[] } | null)?.items ?? [];

  const summary = useApi(useCallback(() => providerOverridesApi.summary(), []));

  const list = useApi(useCallback(() => providerOverridesApi.list({
    approvalStatus: approvalFilter || undefined, status: statusFilter || undefined,
    search: search || undefined, pageSize: 100,
  }), [approvalFilter, statusFilter, search]), [approvalFilter, statusFilter, search]);
  const items: ProviderPricingOverride[] = list.data?.items ?? [];

  const detail = useApi(useCallback(
    () => detailId ? providerOverridesApi.get(detailId) : Promise.resolve(null as unknown as ProviderPricingOverride),
    [detailId]), [detailId]);
  const audit = useApi(useCallback(
    () => detailId ? providerOverridesApi.audit(detailId) : Promise.resolve({ items: [] as AuditEntry[] }),
    [detailId]), [detailId]);

  const validateAction = useAction(useCallback(async () => {
    const r = await providerOverridesApi.validatePreview({
      tenant_id: form.tenant_id, master_service_id: form.master_service_id,
      override_price: Number(form.override_price), reason: form.reason || undefined,
    });
    setValidation(r); return r;
  }, [form]));

  const createAction = useAction(useCallback(async () => {
    const payload = {
      tenant_id: form.tenant_id, master_service_id: form.master_service_id,
      category_id: categoryId || undefined,
      override_price: Number(form.override_price), reason: form.reason || undefined,
    };
    if (editingId) { await providerOverridesApi.update(editingId, payload); notify("Override updated."); }
    else { await providerOverridesApi.create(payload); notify("Override created — pending approval."); }
    list.refetch(); summary.refetch(); setModal("none"); setForm(BLANK_FORM); setEditingId(null); setValidation(null);
  }, [form, categoryId, editingId, list, summary]));

  const approveAction = useAction(useCallback(async (id: string) => {
    await providerOverridesApi.approve(id); list.refetch(); summary.refetch(); notify("Approved.");
  }, [list, summary]));
  const rejectAction = useAction(useCallback(async () => {
    if (!rejectingId) return;
    await providerOverridesApi.reject(rejectingId, rejectReason);
    list.refetch(); summary.refetch(); setModal("none"); setRejectingId(null); setRejectReason(""); notify("Rejected.");
  }, [rejectingId, rejectReason, list, summary]));
  const activateAction = useAction(useCallback(async (id: string) => {
    await providerOverridesApi.activate(id); list.refetch(); summary.refetch(); notify("Activated.");
  }, [list, summary]));
  const deactivateAction = useAction(useCallback(async (id: string) => {
    await providerOverridesApi.deactivate(id); list.refetch(); summary.refetch(); notify("Deactivated.");
  }, [list, summary]));

  const openEdit = (row: ProviderPricingOverride) => {
    setEditingId(row.id); setCategoryId(row.category_id || ""); setValidation(null);
    setForm({ tenant_id: row.tenant_id, master_service_id: row.master_service_id,
      override_price: String(row.override_price), reason: row.reason || "" });
    setModal("edit");
  };
  const openDetail = (row: ProviderPricingOverride) => {
    setDetailId(row.id); setDetailTab("overview"); setModal("detail");
  };

  const columns = [
    { key: "tenant_name", label: "Tenant", width: 170, render: (_: unknown, row: ProviderPricingOverride) => (
      <div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{row.tenant_name || "Unknown tenant"}</div>
        <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.tenant_code || "—"}</div>
        <div style={{ fontSize: 9, color: "var(--muted-text)", fontFamily: "monospace" }}>{row.tenant_id.slice(0, 8)}…</div>
      </div>
    )},
    { key: "master_service_name", label: "Service", render: (_: unknown, row: ProviderPricingOverride) => (
      <div style={{ fontSize: 12 }}>
        <div>{row.master_service_name || "—"}</div>
        <div style={{ fontSize: 10, color: "var(--muted-text)" }}>
          {[row.service_type_name, row.brand_name, row.issue_type_name].filter(Boolean).join(" · ") || "—"}
        </div>
        {row.zipcode && <div style={{ fontSize: 10, color: "var(--muted-text)" }}>{row.zipcode}{row.tier_name ? ` / ${row.tier_name}` : ""}</div>}
      </div>
    )},
    { key: "override_price", label: "Override Price", width: 130, render: (_: unknown, row: ProviderPricingOverride) => (
      <span style={{ fontWeight: 600 }}>{row.currency} {row.override_price.toLocaleString("en-IN")}</span>
    )},
    { key: "platform_min_price", label: "Platform Range", width: 150, render: (_: unknown, row: ProviderPricingOverride) => (
      <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
        <div>{money(row.platform_min_price)} – {money(row.platform_max_price)}</div>
        <div style={{ color: "var(--muted-text)" }}>Base {money(row.platform_base_price)}</div>
      </div>
    )},
    { key: "delta_from_base", label: "Delta", width: 130, render: (_: unknown, row: ProviderPricingOverride) => {
      const d = row.delta_from_base;
      if (d == null) return <span style={{ fontSize: 11, color: "var(--muted-text)" }}>—</span>;
      const inRange = row.platform_min_price != null && row.platform_max_price != null
        && row.override_price >= row.platform_min_price && row.override_price <= row.platform_max_price;
      return (
        <div style={{ fontSize: 11 }}>
          <span style={{ color: d >= 0 ? "var(--success-text)" : "var(--danger-text)", fontWeight: 600 }}>
            {d >= 0 ? "+" : ""}{money(d)} {d >= 0 ? "above" : "below"} base
          </span>
          <div style={{ color: inRange ? "var(--success-text)" : "var(--danger-text)" }}>{inRange ? "Within range" : "Out of range"}</div>
        </div>
      );
    }},
    { key: "approval_status", label: "Approval", width: 110, render: (_: unknown, row: ProviderPricingOverride) => (
      <Badge variant={APPROVAL_BADGE[row.approval_status] ?? "muted"} size="sm">{row.approval_status}</Badge>
    )},
    { key: "status", label: "Status", width: 90, render: (_: unknown, row: ProviderPricingOverride) => (
      <Badge variant={row.status === "active" ? "success" : "muted"} size="sm">{row.status}</Badge>
    )},
    { key: "reason", label: "Reason", render: (_: unknown, row: ProviderPricingOverride) => (
      <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{row.reason || "—"}</span>
    )},
    { key: "id", label: "Actions", width: 190, render: (_: unknown, row: ProviderPricingOverride) => (
      <div style={{ display: "flex", gap: 4 }} onClick={e => e.stopPropagation()}>
        <Btn size="xs" variant="ghost" onClick={() => openDetail(row)}><Eye size={11}/></Btn>
        {perm.has("pricing.provider_overrides.update") && (
          <Btn size="xs" variant="ghost" onClick={() => openEdit(row)}><Pencil size={11}/></Btn>
        )}
        {row.approval_status === "pending" && perm.has("pricing.provider_overrides.approve") && (
          <Btn size="xs" variant="ghost" loading={approveAction.loading} onClick={() => approveAction.execute(row.id)}><Check size={11}/></Btn>
        )}
        {row.approval_status === "pending" && perm.has("pricing.provider_overrides.reject") && (
          <Btn size="xs" variant="ghost" onClick={() => { setRejectingId(row.id); setModal("reject"); }}><X size={11}/></Btn>
        )}
        {perm.has("pricing.provider_overrides.activate") && perm.has("pricing.provider_overrides.deactivate") && (
          row.status === "active" ? (
            <Btn size="xs" variant="ghost" loading={deactivateAction.loading} onClick={() => deactivateAction.execute(row.id)}><PowerOff size={11}/></Btn>
          ) : (
            <Btn size="xs" variant="ghost" loading={activateAction.loading} onClick={() => activateAction.execute(row.id)}><Power size={11}/></Btn>
          )
        )}
      </div>
    )},
  ];

  return (
    <AdminLayout activeNav="provider-overrides">
      <SectionHeader
        title="Provider Pricing Overrides"
        subtitle="Review tenant-scoped service price overrides while enforcing platform min/max pricing rules."
        actions={
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn size="sm" variant="secondary" onClick={() => { list.refetch(); summary.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }}/> Refresh
            </Btn>
            {perm.has("pricing.provider_overrides.create") && (
              <Btn size="sm" variant="primary" onClick={() => { setEditingId(null); setForm(BLANK_FORM); setCategoryId(""); setValidation(null); setModal("create"); }}>
                <Plus size={14} style={{ marginRight: 4 }}/> New Override
              </Btn>
            )}
          </div>
        }
      />
      <p style={{ fontSize: 11, color: "var(--muted-text)", margin: "-8px 0 14px" }}>Pricing & Rules / Provider Pricing Overrides</p>

      {toast && (
        <div style={{ padding: "10px 16px", borderRadius: 10, marginBottom: 12,
          background: toast.ok ? "var(--success-bg,rgba(34,197,94,.08))" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text,#166534)" : "var(--danger-text)", fontSize: 13 }}>
          {toast.ok ? "✓" : "✗"} {toast.msg}
        </div>
      )}

      {/* ── Summary cards ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 18 }}>
        {summary.loading ? (
          Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={92}/>)
        ) : summary.error ? (
          <div style={{ gridColumn: "1 / -1" }}>
            <EmptyState icon={<AlertTriangle/>} title="Could not load summary."
              description={`${summary.error}${summary.requestId ? ` — Request ID: ${summary.requestId}` : ""}`}/>
          </div>
        ) : (
          <>
            <StatCard label="Total Overrides" value={summary.data?.total_overrides ?? 0} onClick={() => { setApprovalFilter(""); setStatusFilter(""); }}/>
            <StatCard label="Active Overrides" value={summary.data?.active_overrides ?? 0} onClick={() => setStatusFilter("active")}/>
            <StatCard label="Pending Approval" value={summary.data?.pending_approval ?? 0} onClick={() => setApprovalFilter("pending")}/>
            <StatCard label="Rejected Overrides" value={summary.data?.rejected_overrides ?? 0} onClick={() => setApprovalFilter("rejected")}/>
            <StatCard label="Out-of-Range Attempts" value={summary.data?.out_of_range_attempts ?? 0}
              alert={(summary.data?.out_of_range_attempts ?? 0) > 0}/>
            <StatCard label="Avg Override Price" value={summary.data?.avg_override_price != null ? money(summary.data.avg_override_price) : "—"}/>
            <StatCard label="Tenants With Overrides" value={summary.data?.tenants_with_overrides ?? 0}/>
            <StatCard label="Validation Issues" value={summary.data?.validation_issues ?? 0}
              alert={(summary.data?.validation_issues ?? 0) > 0}/>
          </>
        )}
      </div>

      {/* ── Toolbar filters ── */}
      <Card padding={14} style={{ marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ minWidth: 220 }}>
            <Input label="Search" placeholder="Tenant or service" value={search} onChange={setSearch}/>
          </div>
          <FilterSelect label="Approval Status" value={approvalFilter} onChange={setApprovalFilter}
            options={[["", "All"], ["pending", "Pending"], ["approved", "Approved"], ["rejected", "Rejected"]]}/>
          <FilterSelect label="Status" value={statusFilter} onChange={setStatusFilter}
            options={[["", "All"], ["active", "Active"], ["inactive", "Inactive"]]}/>
          {(search || approvalFilter || statusFilter) && (
            <Btn size="sm" variant="ghost" onClick={() => { setSearch(""); setApprovalFilter(""); setStatusFilter(""); }}>
              Clear filters
            </Btn>
          )}
        </div>
      </Card>

      <Card padding={0}>
        {list.error ? (
          <EmptyState icon={<AlertTriangle/>} title="Could not load provider overrides."
            description={`${list.error}${list.requestId ? ` — Request ID: ${list.requestId}` : ""}`}
            action={<Btn size="sm" variant="secondary" onClick={() => list.refetch()}>Retry</Btn>}/>
        ) : !list.loading && items.length === 0 ? (
          <EmptyState icon={<AlertTriangle/>} title="No provider pricing overrides found."
            description="Tenant-specific overrides will appear here after creation or approval."
            action={perm.has("pricing.provider_overrides.create") ? (
              <Btn size="sm" variant="primary" onClick={() => setModal("create")}>New Override</Btn>
            ) : undefined}/>
        ) : (
          <DataTable
            columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={items as unknown as Record<string, unknown>[]}
            loading={list.loading}
            onRowClick={(row) => openDetail(row as unknown as ProviderPricingOverride)}
          />
        )}
      </Card>

      {/* ── Create / Edit wizard-style modal ── */}
      <Modal open={modal === "create" || modal === "edit"} onClose={() => setModal("none")}
        title={editingId ? "Edit Provider Pricing Override" : "New Provider Pricing Override"} size="lg">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {createAction.error && (
            <ErrorBlock message={createAction.error} errorCode={createAction.errorCode} requestId={createAction.requestId} context={createAction.context}/>
          )}

          <WizardSection step={1} title="Tenant">
            <SelectField label="Tenant *" value={form.tenant_id} onChange={v => setForm(f => ({ ...f, tenant_id: v }))}
              options={tenantList.map(t => [t.tenant_id, t.tenant_name] as [string, string])}/>
          </WizardSection>

          <WizardSection step={2} title="Service Scope">
            <SelectField label="Category *" value={categoryId} onChange={setCategoryId}
              options={catList.map(c => [c.category_id, c.name] as [string, string])}/>
            {categoryId && (
              <SelectField label="Master Service *" value={form.master_service_id}
                onChange={v => setForm(f => ({ ...f, master_service_id: v }))}
                options={svcList.map(s => [s.service_id, s.service_name] as [string, string])}/>
            )}
          </WizardSection>

          <WizardSection step={3} title="Override Price">
            <Input label="Override Price (₹) *" type="number" placeholder="900" value={form.override_price}
              onChange={v => setForm(f => ({ ...f, override_price: v }))}/>
            <p style={{ fontSize: 11, color: "var(--muted-text)", margin: 0 }}>
              The backend rejects any override below Platform Min Price or above Platform Max Price.
            </p>
            <Input label="Reason *" placeholder="Why this tenant needs a different price" value={form.reason}
              onChange={v => setForm(f => ({ ...f, reason: v }))}/>
            <Btn size="sm" variant="secondary" loading={validateAction.loading}
              disabled={!form.tenant_id || !form.master_service_id || !form.override_price}
              onClick={() => validateAction.execute()}>
              <ClipboardCheck size={13} style={{ marginRight: 4 }}/> Validate
            </Btn>
            {validateAction.error && (
              <ErrorBlock message={validateAction.error} errorCode={validateAction.errorCode} requestId={validateAction.requestId} context={null}/>
            )}
            {validation && <ValidationPreviewBlock v={validation} price={Number(form.override_price)}/>}
          </WizardSection>

          <WizardSection step={4} title="Approval">
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
              New overrides are created with Approval Status = <strong>pending</strong> and require an admin
              with <code>pricing.provider_overrides.approve</code> to approve before taking effect.
            </p>
          </WizardSection>

          <WizardSection step={5} title="Review">
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
              Tenant: {tenantList.find(t => t.tenant_id === form.tenant_id)?.tenant_name || "—"} ·
              {" "}Service: {svcList.find(s => s.service_id === form.master_service_id)?.service_name || "—"} ·
              {" "}Override Price: {money(Number(form.override_price) || null)}
            </p>
          </WizardSection>

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm" disabled={!form.tenant_id || !form.master_service_id || !form.override_price || !form.reason}
              loading={createAction.loading} onClick={() => createAction.execute()}>
              {editingId ? "Save Changes" : "Create"}
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Reject Modal ── */}
      <Modal open={modal === "reject"} onClose={() => { setModal("none"); setRejectingId(null); }} title="Reject Override" size="sm">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {rejectAction.error && <ErrorBlock message={rejectAction.error} errorCode={rejectAction.errorCode} requestId={rejectAction.requestId} context={null}/>}
          <Input label="Rejection Reason *" placeholder="Explain why this override is rejected" value={rejectReason}
            onChange={setRejectReason}/>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="danger" size="sm" disabled={!rejectReason.trim()}
              loading={rejectAction.loading} onClick={() => rejectAction.execute()}>Reject</Btn>
          </div>
        </div>
      </Modal>

      {/* ── Detail drawer ── */}
      <Modal open={modal === "detail"} onClose={() => { setModal("none"); setDetailId(null); }} title="Provider Pricing Override Detail" size="xl">
        {detail.loading ? <Skeleton height={200}/> : detail.error ? (
          <EmptyState icon={<AlertTriangle/>} title="Could not load override detail."
            description={`${detail.error}${detail.requestId ? ` — Request ID: ${detail.requestId}` : ""}`}/>
        ) : detail.data ? (
          <div>
            <div style={{ display: "flex", gap: 8, marginBottom: 16, borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
              {(["overview", "validation", "audit"] as const).map(t => (
                <Btn key={t} size="sm" variant={detailTab === t ? "primary" : "ghost"} onClick={() => setDetailTab(t)}>
                  {t === "overview" ? "Overview / Tenant / Service & Pricing" : t === "validation" ? "Validation & Approval Timeline" : "Audit Logs"}
                </Btn>
              ))}
            </div>

            {detailTab === "overview" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
                <Field label="Override ID" value={detail.data.id}/>
                <Field label="Tenant Name" value={detail.data.tenant_name}/>
                <Field label="Tenant Code" value={detail.data.tenant_code}/>
                <Field label="Override Price" value={money(detail.data.override_price)}/>
                <Field label="Currency" value={detail.data.currency}/>
                <Field label="Approval Status" value={detail.data.approval_status}/>
                <Field label="Status" value={detail.data.status}/>
                <Field label="Reason" value={detail.data.reason}/>
                <Field label="Master Service" value={detail.data.master_service_name}/>
                <Field label="Category" value={detail.data.category_name}/>
                <Field label="Service Type / Brand / Issue" value={[detail.data.service_type_name, detail.data.brand_name, detail.data.issue_type_name].filter(Boolean).join(" · ") || "—"}/>
                <Field label="Zipcode / Tier" value={[detail.data.zipcode, detail.data.tier_name].filter(Boolean).join(" / ") || "—"}/>
                <Field label="Platform Base Price" value={money(detail.data.platform_base_price)}/>
                <Field label="Platform Min / Max Price" value={`${money(detail.data.platform_min_price)} / ${money(detail.data.platform_max_price)}`}/>
                <Field label="Delta From Base" value={detail.data.delta_from_base != null ? `${detail.data.delta_from_base >= 0 ? "+" : ""}${money(detail.data.delta_from_base)}` : "—"}/>
                <Field label="Created At" value={detail.data.created_at}/>
                <Field label="Updated At" value={detail.data.updated_at}/>
              </div>
            )}

            {detailTab === "validation" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <ValidationRow label="Within Platform Min/Max Range"
                  ok={detail.data.platform_min_price == null || detail.data.platform_max_price == null ||
                    (detail.data.override_price >= detail.data.platform_min_price && detail.data.override_price <= detail.data.platform_max_price)}/>
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
                  <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", margin: "0 0 8px" }}>Approval Timeline</p>
                  <TimelineStep label="Submitted" done at={detail.data.created_at}/>
                  <TimelineStep label="Approved / Rejected" done={detail.data.approval_status !== "pending"}
                    at={detail.data.approved_at} failed={detail.data.approval_status === "rejected"}/>
                  <TimelineStep label="Activated" done={detail.data.status === "active"} at={detail.data.updated_at}/>
                </div>
              </div>
            )}

            {detailTab === "audit" && (
              audit.loading ? <Skeleton height={140}/> : (audit.data?.items.length ?? 0) === 0 ? (
                <EmptyState icon={<History/>} title="No audit entries yet."/>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {audit.data!.items.map(a => (
                    <div key={a.id} style={{ padding: "10px 12px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", fontSize: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <strong>{a.action}</strong>
                        <span style={{ color: "var(--muted-text)" }}>{a.created_at}</span>
                      </div>
                      <div style={{ color: "var(--text-secondary)", marginTop: 2 }}>{a.change_summary}</div>
                      {a.request_id && <div style={{ color: "var(--muted-text)", fontSize: 10, marginTop: 2 }}>Request ID: {a.request_id}</div>}
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        ) : null}
      </Modal>
    </AdminLayout>
  );
}

function FilterSelect({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: [string, string][];
}) {
  return (
    <div>
      <label style={{ fontSize: 11, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)}
        style={{ padding: "7px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 12, minWidth: 150 }}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );
}
function SelectField({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: [string, string][];
}) {
  return (
    <div>
      <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)}
        style={{ width: "100%", padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13 }}>
        <option value="">— Select —</option>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );
}
function WizardSection({ step, title, children }: { step: number; title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, paddingBottom: 14, borderBottom: "1px solid var(--border)" }}>
      <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
        Step {step} · {title}
      </p>
      {children}
    </div>
  );
}
function ValidationRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
      <ClipboardCheck size={14} color={ok ? "var(--success-text)" : "var(--danger-text)"}/>
      <span>{label}</span>
      <Badge variant={ok ? "success" : "danger"} size="sm">{ok ? "Pass" : "Fail"}</Badge>
    </div>
  );
}
function TimelineStep({ label, done, at, failed }: { label: string; done?: boolean; at?: string | null; failed?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, padding: "4px 0" }}>
      <div style={{ width: 8, height: 8, borderRadius: "50%",
        background: failed ? "var(--danger-text)" : done ? "var(--success-text)" : "var(--border)" }}/>
      <span style={{ fontWeight: 600 }}>{label}</span>
      <span style={{ color: "var(--muted-text)" }}>{at || (done ? "—" : "Not yet")}</span>
    </div>
  );
}
function ValidationPreviewBlock({ v, price }: { v: OverrideValidationResult; price: number }) {
  if (v.valid) {
    return (
      <div style={{ padding: "12px 14px", borderRadius: 10, background: "var(--success-bg,rgba(34,197,94,.08))", border: "1px solid var(--success-border)" }}>
        <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 6px", color: "var(--success-text,#166534)" }}>✓ Valid Override</p>
        <p style={{ fontSize: 12, margin: "0 0 8px", color: "var(--text-secondary)" }}>Override price is within platform range.</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 11, color: "var(--muted-text)" }}>
          <div>Platform Base Price: {money(v.platform_base_price)}</div>
          <div>Platform Min Price: {money(v.platform_min_price)}</div>
          <div>Platform Max Price: {money(v.platform_max_price)}</div>
          <div>Override Price: {money(price)}</div>
          {v.platform_base_price != null && (
            <div>Delta From Base: {price - v.platform_base_price >= 0 ? "+" : ""}{money(price - v.platform_base_price)}</div>
          )}
        </div>
      </div>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {v.errors.map((e, i) => (
        <div key={i} style={{ padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
          <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 6px", color: "var(--danger-text)" }}>
            ✗ Invalid Override — {e.error_code}
          </p>
          <p style={{ fontSize: 12, margin: "0 0 8px", color: "var(--text-secondary)" }}>{e.message}</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 11, color: "var(--muted-text)" }}>
            {e.platform_min_price != null && <div>Platform Min Price: {money(e.platform_min_price)}</div>}
            {e.platform_max_price != null && <div>Platform Max Price: {money(e.platform_max_price)}</div>}
            {e.override_price != null && <div>Override Price: {money(e.override_price)}</div>}
            {e.existing_override_id && <div>Existing Override: {e.existing_override_id.slice(0, 8)}…</div>}
          </div>
        </div>
      ))}
    </div>
  );
}
