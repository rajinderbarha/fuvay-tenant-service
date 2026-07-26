"use client";
import React, { useState, useCallback, useMemo } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, Input, SectionHeader, DataTable, EmptyState, StatCard, Skeleton,
} from "../../../../components/shared/ui";
import {
  bargainRulesApi, catalogApi,
  type BargainRule, type BargainEvaluationResult, type BargainRuleValidation,
  type ServiceCategory, type MasterService, type AuditEntry,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { usePermissions } from "../../../../hooks/usePermissions";
import {
  Plus, Power, PowerOff, FlaskConical, AlertTriangle, ShieldCheck, Eye,
  Pencil, Copy, ClipboardCheck, History, RefreshCw,
} from "lucide-react";

const READINESS_BADGE: Record<string, { variant: "success" | "warning" | "danger" | "muted"; label: string }> = {
  ready:                 { variant: "success", label: "Ready" },
  missing_pricing_rule:  { variant: "warning", label: "Missing Pricing Rule" },
  invalid_floor:         { variant: "danger",  label: "Invalid Floor" },
  inactive:              { variant: "muted",   label: "Inactive" },
  conflict:              { variant: "danger",  label: "Conflict" },
};

const money = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN")}`;

const BLANK_FORM = {
  rule_name: "", rule_code: "", master_service_id: "", floor_amount: "",
  floor_type: "fixed", below_floor_action: "reject",
  bargain_enabled: true, provider_approval_required: false,
  // Customer Range + Platform Fee Floor Fix
  customer_min_price: "", customer_max_price: "", platform_fee_percent: "",
};

export default function BargainRulesPage() {
  const perm = usePermissions();
  const [modal, setModal] = useState<"none" | "create" | "edit" | "preview" | "detail">("none");
  const [form, setForm] = useState(BLANK_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState("");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  // ── filters ──────────────────────────────────────────────────────────────
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [readinessFilter, setReadinessFilter] = useState("");
  const [bargainEnabledFilter, setBargainEnabledFilter] = useState("");

  // ── evaluate offer ──────────────────────────────────────────────────────
  const [previewRuleId, setPreviewRuleId] = useState("");
  const [previewOffer, setPreviewOffer] = useState("500");
  const [previewResult, setPreviewResult] = useState<BargainEvaluationResult | null>(null);

  // ── detail drawer ────────────────────────────────────────────────────────
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<"overview" | "validation" | "audit">("overview");

  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const catList: ServiceCategory[] = cats.data?.categories ?? [];
  const svcs = useApi(useCallback(
    () => categoryId ? catalogApi.listMasterServices(categoryId) : Promise.resolve({ services: [] as MasterService[] }),
    [categoryId]), [categoryId]);
  const svcList: MasterService[] = svcs.data?.services ?? [];

  const summary = useApi(useCallback(() => bargainRulesApi.summary(), []));

  const list = useApi(useCallback(() => bargainRulesApi.list({
    status: statusFilter || undefined, search: search || undefined,
    bargainEnabled: bargainEnabledFilter ? bargainEnabledFilter === "true" : undefined,
    pageSize: 100,
  }), [statusFilter, search, bargainEnabledFilter]), [statusFilter, search, bargainEnabledFilter]);
  const rawItems: BargainRule[] = list.data?.items ?? [];
  const items = useMemo(
    () => readinessFilter ? rawItems.filter(r => r.readiness === readinessFilter) : rawItems,
    [rawItems, readinessFilter]);

  const detail = useApi(useCallback(
    () => detailId ? bargainRulesApi.get(detailId) : Promise.resolve(null as unknown as BargainRule),
    [detailId]), [detailId]);
  const audit = useApi(useCallback(
    () => detailId ? bargainRulesApi.audit(detailId) : Promise.resolve({ items: [] as AuditEntry[] }),
    [detailId]), [detailId]);
  const [validationResult, setValidationResult] = useState<BargainRuleValidation | null>(null);
  const validateAction = useAction(useCallback(async (id: string) => {
    const r = await bargainRulesApi.validate(id); setValidationResult(r); return r;
  }, []));

  const createAction = useAction(useCallback(async () => {
    const usingCustomerRange = !!(form.customer_min_price && form.customer_max_price);
    const payload = {
      rule_name: form.rule_name || undefined, rule_code: form.rule_code || undefined,
      master_service_id: form.master_service_id || undefined,
      category_id: categoryId || undefined,
      floor_type: form.floor_type,
      // floor_amount is only required/used directly when no customer range is set —
      // the backend computes floor_amount from customer_min_price + platform fee instead.
      floor_amount: form.floor_amount ? Number(form.floor_amount) : undefined,
      below_floor_action: form.below_floor_action,
      bargain_enabled: form.bargain_enabled,
      provider_approval_required: form.provider_approval_required,
      customer_min_price: usingCustomerRange ? Number(form.customer_min_price) : undefined,
      customer_max_price: usingCustomerRange ? Number(form.customer_max_price) : undefined,
      platform_fee_percent: form.platform_fee_percent ? Number(form.platform_fee_percent) : undefined,
    };
    if (editingId) { await bargainRulesApi.update(editingId, payload); notify("Bargain rule updated."); }
    else { await bargainRulesApi.create(payload); notify("Bargain rule created."); }
    list.refetch(); summary.refetch(); setModal("none"); setForm(BLANK_FORM); setEditingId(null);
  }, [form, categoryId, editingId, list, summary]));

  const activateAction = useAction(useCallback(async (id: string) => {
    await bargainRulesApi.activate(id); list.refetch(); summary.refetch(); notify("Activated.");
  }, [list, summary]));
  const deactivateAction = useAction(useCallback(async (id: string) => {
    await bargainRulesApi.deactivate(id); list.refetch(); summary.refetch(); notify("Deactivated.");
  }, [list, summary]));

  const previewAction = useAction(useCallback(async () => {
    const result = await bargainRulesApi.evaluatePreview({
      pricing_rule_id: previewRuleId || undefined,
      offer_price: Number(previewOffer),
    });
    setPreviewResult(result);
  }, [previewRuleId, previewOffer]));

  const openEdit = (row: BargainRule) => {
    setEditingId(row.id);
    setCategoryId(row.category_id || "");
    setForm({
      rule_name: row.rule_name || "", rule_code: row.rule_code || "",
      master_service_id: row.master_service_id || "", floor_amount: String(row.floor_amount),
      floor_type: row.floor_type, below_floor_action: row.below_floor_action,
      bargain_enabled: row.bargain_enabled, provider_approval_required: row.provider_approval_required,
      customer_min_price: row.customer_min_price != null ? String(row.customer_min_price) : "",
      customer_max_price: row.customer_max_price != null ? String(row.customer_max_price) : "",
      platform_fee_percent: row.platform_fee_percent != null ? String(row.platform_fee_percent) : "",
    });
    setModal("edit");
  };
  const openDetail = (row: BargainRule) => {
    setDetailId(row.id); setDetailTab("overview"); setValidationResult(null); setModal("detail");
  };
  const cloneRule = (row: BargainRule) => {
    setEditingId(null);
    setCategoryId(row.category_id || "");
    setForm({
      rule_name: `${row.rule_name || "Rule"} (Copy)`, rule_code: "",
      master_service_id: row.master_service_id || "", floor_amount: String(row.floor_amount),
      floor_type: row.floor_type, below_floor_action: row.below_floor_action,
      bargain_enabled: row.bargain_enabled, provider_approval_required: row.provider_approval_required,
      customer_min_price: row.customer_min_price != null ? String(row.customer_min_price) : "",
      customer_max_price: row.customer_max_price != null ? String(row.customer_max_price) : "",
      platform_fee_percent: row.platform_fee_percent != null ? String(row.platform_fee_percent) : "",
    });
    setModal("create");
  };

  const columns = [
    { key: "rule_name", label: "Rule", render: (_: unknown, row: BargainRule) => (
      <div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{row.rule_name || "Unnamed rule"}</div>
        {row.rule_code && <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.rule_code}</div>}
      </div>
    )},
    { key: "master_service_name", label: "Service", render: (_: unknown, row: BargainRule) => (
      <div>
        <div style={{ fontSize: 12 }}>{row.master_service_name || "—"}</div>
        {row.category_name && <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.category_name}</div>}
      </div>
    )},
    { key: "base_price", label: "Price Context", width: 150, render: (_: unknown, row: BargainRule) => (
      <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>
        <div>Base: {money(row.base_price)}</div>
        <div>Min {money(row.min_price)} · Max {money(row.max_price)}</div>
      </div>
    )},
    { key: "floor_amount", label: "Bargain Floor", width: 130, render: (_: unknown, row: BargainRule) => (
      <div>
        <span style={{ fontWeight: 600 }}>{money(row.floor_amount)}</span>
        <div style={{ fontSize: 10, color: "var(--muted-text)" }}>{row.floor_type}</div>
      </div>
    )},
    { key: "below_floor_action", label: "Below Floor", width: 130, render: (_: unknown, row: BargainRule) => (
      <Badge variant="danger" size="sm">{row.below_floor_action}</Badge>
    )},
    { key: "provider_approval_required", label: "Provider Approval", width: 130, render: (_: unknown, row: BargainRule) => (
      <span style={{ fontSize: 12 }}>{row.provider_approval_required ? "Required" : "Not required"}</span>
    )},
    { key: "bargain_enabled", label: "Bargaining", width: 110, render: (_: unknown, row: BargainRule) => (
      <Badge variant={row.bargain_enabled ? "success" : "muted"} size="sm">{row.bargain_enabled ? "Enabled" : "Disabled"}</Badge>
    )},
    { key: "readiness", label: "Readiness", width: 150, render: (_: unknown, row: BargainRule) => {
      const r = READINESS_BADGE[row.readiness ?? "inactive"];
      return (
        <div>
          <Badge variant={r.variant} size="sm">{r.label}</Badge>
          {row.warning && (
            <div style={{ display: "flex", gap: 4, alignItems: "flex-start", marginTop: 4, fontSize: 10, color: "var(--warning-text)" }}>
              <AlertTriangle size={11} style={{ flexShrink: 0, marginTop: 1 }}/>
              <span>{row.warning}</span>
            </div>
          )}
        </div>
      );
    }},
    { key: "status", label: "Status", width: 90, render: (_: unknown, row: BargainRule) => (
      <Badge variant={row.status === "active" ? "success" : "muted"} size="sm">{row.status}</Badge>
    )},
    { key: "id", label: "Actions", width: 170, render: (_: unknown, row: BargainRule) => (
      <div style={{ display: "flex", gap: 4 }} onClick={e => e.stopPropagation()}>
        <Btn size="xs" variant="ghost" onClick={() => openDetail(row)}><Eye size={11}/></Btn>
        {perm.has("pricing.bargain_rules.update") && (
          <Btn size="xs" variant="ghost" onClick={() => openEdit(row)}><Pencil size={11}/></Btn>
        )}
        {perm.has("pricing.bargain_rules.create") && (
          <Btn size="xs" variant="ghost" onClick={() => cloneRule(row)}><Copy size={11}/></Btn>
        )}
        {perm.has("pricing.bargain_rules.activate") && perm.has("pricing.bargain_rules.deactivate") && (
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
    <AdminLayout activeNav="bargain-rules">
      <div style={{ padding: "12px 16px", marginBottom: 16, borderRadius: 10,
        background: "var(--warning-bg, #fffbeb)", border: "1px solid var(--warning-border, #fde68a)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <AlertTriangle size={16} style={{ color: "var(--warning-text, #92400e)", flexShrink: 0 }}/>
          <p style={{ fontSize: 13, color: "var(--warning-text, #92400e)", margin: 0 }}>
            Manual Bargain Rules are disabled. ServiceOS now automatically creates Low, Mid, and High
            customer price options for Home Services. This page is kept for backward-compatible debug
            access only — new rules should not be created here.
          </p>
        </div>
      </div>
      <SectionHeader
        title="Bargain Rules [Deprecated]"
        subtitle="Configure customer counter-offer rules, bargain floors, provider approval requirements, and evaluation policies. Superseded by automatic Low/Mid/High price options."
        actions={
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn size="sm" variant="secondary" onClick={() => { list.refetch(); summary.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }}/> Refresh
            </Btn>
            {perm.has("pricing.bargain_rules.evaluate_preview") && (
              <Btn size="sm" variant="secondary" onClick={() => { setPreviewResult(null); setModal("preview"); }}>
                <FlaskConical size={14} style={{ marginRight: 4 }}/> Evaluate Offer
              </Btn>
            )}
            {perm.has("pricing.bargain_rules.create") && (
              <Btn size="sm" variant="primary" onClick={() => { setEditingId(null); setForm(BLANK_FORM); setCategoryId(""); setModal("create"); }}>
                <Plus size={14} style={{ marginRight: 4 }}/> New Bargain Rule
              </Btn>
            )}
          </div>
        }
      />

      <p style={{ fontSize: 11, color: "var(--muted-text)", margin: "-8px 0 14px" }}>Pricing & Rules / Bargain Rules</p>

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
            <StatCard label="Total Bargain Rules" value={summary.data?.total_bargain_rules ?? 0} onClick={() => setStatusFilter("")}/>
            <StatCard label="Active Rules" value={summary.data?.active_rules ?? 0} onClick={() => setStatusFilter("active")}/>
            <StatCard label="Inactive Rules" value={summary.data?.inactive_rules ?? 0} onClick={() => setStatusFilter("inactive")}/>
            <StatCard label="Bargain Enabled Services" value={summary.data?.bargain_enabled_services ?? 0} onClick={() => setBargainEnabledFilter("true")}/>
            <StatCard label="Below-Floor Rejections" value={summary.data?.below_floor_rejections ?? 0}/>
            <StatCard label="Provider Approval Required" value={summary.data?.provider_approval_required ?? 0}/>
            <StatCard label="Avg Accepted Offer" value={summary.data?.avg_accepted_offer != null ? money(summary.data.avg_accepted_offer) : "—"}/>
            <StatCard label="Validation Issues" value={summary.data?.validation_issues ?? 0}
              alert={(summary.data?.validation_issues ?? 0) > 0} onClick={() => setReadinessFilter("invalid_floor")}/>
          </>
        )}
      </div>

      {/* ── Toolbar filters ── */}
      <Card padding={14} style={{ marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ minWidth: 220 }}>
            <Input label="Search" placeholder="Rule name, code, or service" value={search} onChange={setSearch}/>
          </div>
          <FilterSelect label="Status" value={statusFilter} onChange={setStatusFilter}
            options={[["", "All"], ["active", "Active"], ["inactive", "Inactive"]]}/>
          <FilterSelect label="Bargaining Enabled" value={bargainEnabledFilter} onChange={setBargainEnabledFilter}
            options={[["", "All"], ["true", "Enabled"], ["false", "Disabled"]]}/>
          <FilterSelect label="Readiness" value={readinessFilter} onChange={setReadinessFilter}
            options={[["", "All"], ["ready", "Ready"], ["missing_pricing_rule", "Missing Pricing Rule"],
              ["invalid_floor", "Invalid Floor"], ["inactive", "Inactive"], ["conflict", "Conflict"]]}/>
          {(search || statusFilter || readinessFilter || bargainEnabledFilter) && (
            <Btn size="sm" variant="ghost" onClick={() => { setSearch(""); setStatusFilter(""); setReadinessFilter(""); setBargainEnabledFilter(""); }}>
              Clear filters
            </Btn>
          )}
        </div>
      </Card>

      <Card padding={0}>
        {list.error ? (
          <EmptyState icon={<AlertTriangle/>} title="Could not load bargain rules."
            description={`${list.error}${list.requestId ? ` — Request ID: ${list.requestId}` : ""}`}
            action={<Btn size="sm" variant="secondary" onClick={() => list.refetch()}>Retry</Btn>}/>
        ) : !list.loading && items.length === 0 ? (
          <EmptyState icon={<FlaskConical/>} title="No bargain rules found."
            description="Create a rule to control customer counter-offers and bargain floors."
            action={perm.has("pricing.bargain_rules.create") ? (
              <Btn size="sm" variant="primary" onClick={() => setModal("create")}>New Bargain Rule</Btn>
            ) : undefined}/>
        ) : (
          <DataTable
            columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={items as unknown as Record<string, unknown>[]}
            loading={list.loading}
            onRowClick={(row) => openDetail(row as unknown as BargainRule)}
          />
        )}
      </Card>

      {/* ── Create / Edit wizard-style modal ── */}
      <Modal open={modal === "create" || modal === "edit"} onClose={() => setModal("none")}
        title={editingId ? "Edit Bargain Rule" : "New Bargain Rule"} size="lg">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {createAction.error && (
            <ErrorBlock message={createAction.error} errorCode={createAction.errorCode} requestId={createAction.requestId} context={createAction.context}/>
          )}

          <WizardSection step={1} title="Basic Details">
            <Input label="Rule Name *" placeholder="AC Repair Bargain" value={form.rule_name}
              onChange={v => setForm(f => ({ ...f, rule_name: v }))}/>
            <Input label="Rule Code" placeholder="ac_repair_bargain" value={form.rule_code}
              onChange={v => setForm(f => ({ ...f, rule_code: v }))}/>
          </WizardSection>

          <WizardSection step={2} title="Scope">
            <SelectField label="Category" value={categoryId} onChange={setCategoryId}
              options={catList.map(c => [c.category_id, c.name] as [string, string])}/>
            {categoryId && (
              <SelectField label="Master Service *" value={form.master_service_id}
                onChange={v => setForm(f => ({ ...f, master_service_id: v }))}
                options={svcList.map(s => [s.service_id, s.service_name] as [string, string])}/>
            )}
          </WizardSection>

          <WizardSection step={3} title="Customer Range + Platform Fee (recommended)">
            <p style={{ fontSize: 11, color: "var(--muted-text)", margin: "0 0 8px" }}>
              Set a customer-facing display/negotiation range — the real bargain floor is computed
              as customer_min_price + platform fee, not a flat admin amount. Leave blank to fall
              back to the legacy fixed Bargain Floor below.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <Input label="Customer Min Price (₹)" type="number" placeholder="350" value={form.customer_min_price}
                onChange={v => setForm(f => ({ ...f, customer_min_price: v }))}/>
              <Input label="Customer Max Price (₹)" type="number" placeholder="450" value={form.customer_max_price}
                onChange={v => setForm(f => ({ ...f, customer_max_price: v }))}/>
            </div>
            <Input label="Platform Fee (%)" type="number" placeholder="10" value={form.platform_fee_percent}
              onChange={v => setForm(f => ({ ...f, platform_fee_percent: v }))}/>
            {form.customer_min_price && form.customer_max_price && form.platform_fee_percent && (
              <p style={{ fontSize: 12, color: "var(--text-primary)", margin: "4px 0 0", fontWeight: 600 }}>
                Computed bargain floor: {money(Number(form.customer_min_price) * (1 + Number(form.platform_fee_percent) / 100))}
              </p>
            )}
          </WizardSection>

          <WizardSection step={4} title="Legacy Fixed Floor (fallback only)">
            <SelectField label="Floor Type" value={form.floor_type}
              onChange={v => setForm(f => ({ ...f, floor_type: v }))}
              options={[
                ["fixed", "Fixed Amount"], ["percentage_of_base_price", "Percentage of Base Price"],
                ["percentage_above_min_price", "Percentage Above Min Price"], ["use_pricing_rule_floor", "Use Pricing Rule Floor"],
              ]}/>
            <Input label="Bargain Floor (₹)" type="number" placeholder="650" value={form.floor_amount}
              onChange={v => setForm(f => ({ ...f, floor_amount: v }))}/>
            <SelectField label="Below Floor Action" value={form.below_floor_action}
              onChange={v => setForm(f => ({ ...f, below_floor_action: v }))}
              options={[["reject", "Reject"], ["counter_with_floor", "Counter With Floor"], ["send_to_provider_approval", "Send to Provider Approval"]]}/>
          </WizardSection>

          <WizardSection step={5} title="Provider Approval">
            <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                <input type="checkbox" checked={form.bargain_enabled}
                  onChange={e => setForm(f => ({ ...f, bargain_enabled: e.target.checked }))}/>
                Bargaining enabled
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                <input type="checkbox" checked={form.provider_approval_required}
                  onChange={e => setForm(f => ({ ...f, provider_approval_required: e.target.checked }))}/>
                Provider approval required
              </label>
            </div>
          </WizardSection>

          <WizardSection step={6} title="Validation & Review">
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
              {form.rule_name || "Unnamed rule"} — Floor {money(Number(form.floor_amount) || null)} ·
              {" "}{form.below_floor_action.replace(/_/g, " ")} ·{" "}
              {form.provider_approval_required ? "Provider approval required" : "No approval required"}
            </p>
            {!form.master_service_id && (
              <p style={{ fontSize: 11, color: "var(--warning-text)", margin: 0 }}>⚠ Select a Master Service before saving.</p>
            )}
          </WizardSection>

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm"
              disabled={!form.master_service_id || !form.rule_name ||
                (!form.floor_amount && !(form.customer_min_price && form.customer_max_price))}
              loading={createAction.loading} onClick={() => createAction.execute()}>
              {editingId ? "Save Changes" : "Create"}
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Evaluate Offer Modal ── */}
      <Modal open={modal === "preview"} onClose={() => { setModal("none"); setPreviewResult(null); }} title="Evaluate Bargain Offer" size="md">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Input label="Pricing Rule ID" placeholder="paste rule_id from Pricing Rules page" value={previewRuleId}
            onChange={setPreviewRuleId}/>
          <Input label="Customer Offer Amount (₹)" type="number" value={previewOffer} onChange={setPreviewOffer}/>
          {previewAction.error && (
            <ErrorBlock message={previewAction.error} errorCode={previewAction.errorCode} requestId={previewAction.requestId} context={previewAction.context}/>
          )}
          <Btn variant="primary" size="sm" loading={previewAction.loading}
            onClick={() => previewAction.execute()}>Evaluate</Btn>
          {previewResult && (
            <div style={{ padding: "14px 16px", borderRadius: 10,
              background: previewResult.decision === "accepted" ? "var(--success-bg,rgba(34,197,94,.08))"
                : previewResult.decision === "provider_approval_required" ? "var(--warning-bg)" : "var(--danger-bg)",
              border: `1px solid ${previewResult.decision === "accepted" ? "var(--success-border)"
                : previewResult.decision === "provider_approval_required" ? "var(--warning-border)" : "var(--danger-border)"}` }}>
              <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 6px",
                color: previewResult.decision === "accepted" ? "var(--success-text,#166534)"
                  : previewResult.decision === "provider_approval_required" ? "var(--warning-text)" : "var(--danger-text)" }}>
                {previewResult.decision === "accepted" ? "✓ Accepted" :
                 previewResult.decision === "provider_approval_required" ? "⏳ Pending Provider Approval" : "✗ Rejected"}
              </p>
              <p style={{ fontSize: 12, margin: "0 0 8px", color: "var(--text-secondary)" }}>{previewResult.reason}</p>
              {/* Full admin/customer/fee breakdown per the Customer Range + Platform Fee model —
                  the customer-facing app must never show the pre-fee ₹350; this admin/tenant
                  view shows the complete breakdown for transparency. */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 11, color: "var(--muted-text)" }}>
                <div>Admin Range: {money(previewResult.admin_min_price ?? previewResult.min_price)} – {money(previewResult.admin_max_price ?? previewResult.max_price)}</div>
                <div>Admin Base Price (fallback only): {money(previewResult.admin_base_price ?? previewResult.base_price)}</div>
                <div>Customer Selected Range: {money(previewResult.customer_min_price)} – {money(previewResult.customer_max_price)}</div>
                <div>Platform Fee: {previewResult.platform_fee_percent ?? 0}% = {money(previewResult.platform_fee_amount)}</div>
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>Minimum Allowed Customer Offer: {money(previewResult.allowed_offer_min ?? previewResult.bargain_floor)}</div>
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>Maximum Allowed Customer Offer: {money(previewResult.allowed_offer_max ?? previewResult.customer_max_price)}</div>
                <div>Customer Offer: {money(previewResult.customer_offer)}</div>
                <div>Payment Mode: {previewResult.payment_mode ?? "customer_pays_provider_directly"}</div>
                {previewResult.rule_used && <div>Rule Used: {previewResult.rule_used}</div>}
                {previewResult.pricing_source && <div>Pricing Source: {previewResult.pricing_source}</div>}
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* ── Detail drawer (as full-width modal — see PHASE_3C_BARGAIN_FRONTEND_REPORT.md scope note) ── */}
      <Modal open={modal === "detail"} onClose={() => { setModal("none"); setDetailId(null); }} title="Bargain Rule Detail" size="xl">
        {detail.loading ? <Skeleton height={200}/> : detail.error ? (
          <EmptyState icon={<AlertTriangle/>} title="Could not load rule detail."
            description={`${detail.error}${detail.requestId ? ` — Request ID: ${detail.requestId}` : ""}`}/>
        ) : detail.data ? (
          <div>
            <div style={{ display: "flex", gap: 8, marginBottom: 16, borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
              {(["overview", "validation", "audit"] as const).map(t => (
                <Btn key={t} size="sm" variant={detailTab === t ? "primary" : "ghost"} onClick={() => setDetailTab(t)}>
                  {t === "overview" ? "Overview / Scope / Pricing / Provider Approval" : t === "validation" ? "Validation" : "Audit Logs"}
                </Btn>
              ))}
            </div>

            {detailTab === "overview" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
                <Field label="Rule Name" value={detail.data.rule_name}/>
                <Field label="Rule Code" value={detail.data.rule_code}/>
                <Field label="Status" value={detail.data.status}/>
                <Field label="Bargaining Enabled" value={detail.data.bargain_enabled ? "Yes" : "No"}/>
                <Field label="Below Floor Action" value={detail.data.below_floor_action}/>
                <Field label="Provider Approval Required" value={detail.data.provider_approval_required ? "Yes" : "No"}/>
                <Field label="Readiness Status" value={READINESS_BADGE[detail.data.readiness ?? "inactive"].label}/>
                <Field label="Readiness Warning" value={detail.data.warning || "None"}/>
                <Field label="Category" value={detail.data.category_name}/>
                <Field label="Master Service" value={detail.data.master_service_name}/>
                <Field label="Base Price" value={money(detail.data.base_price)}/>
                <Field label="Min / Max Price" value={`${money(detail.data.min_price)} / ${money(detail.data.max_price)}`}/>
                <Field label="Bargain Floor" value={money(detail.data.floor_amount)}/>
                <Field label="Pricing Source" value={detail.data.pricing_source}/>
                <Field label="Created At" value={detail.data.created_at}/>
                <Field label="Updated At" value={detail.data.updated_at}/>
              </div>
            )}

            {detailTab === "validation" && (
              <div>
                <Btn size="sm" variant="secondary" loading={validateAction.loading}
                  onClick={() => detailId && validateAction.execute(detailId)}>
                  <ClipboardCheck size={13} style={{ marginRight: 4 }}/> Run Validation
                </Btn>
                {validateAction.error && (
                  <div style={{ marginTop: 10 }}>
                    <ErrorBlock message={validateAction.error} errorCode={validateAction.errorCode} requestId={validateAction.requestId} context={null}/>
                  </div>
                )}
                {validationResult && (
                  <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 8 }}>
                    <ValidationRow label="Floor >= Min Price" ok={validationResult.checks.floor_gte_min_price}/>
                    <ValidationRow label="Floor <= Max Price" ok={validationResult.checks.floor_lte_max_price}/>
                    <ValidationRow label="Active Pricing Rule Exists" ok={validationResult.checks.active_pricing_rule_exists}/>
                    <ValidationRow label="No Duplicate Active Bargain Rule" ok={validationResult.checks.no_duplicate_active_bargain_rule}/>
                    <ValidationRow label="Provider Approval Rule Valid" ok={validationResult.checks.provider_approval_rule_valid}/>
                  </div>
                )}
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

// ── Shared small components (scoped to this page + provider-overrides sibling) ──
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
export function ErrorBlock({ message, errorCode, requestId, context }: {
  message: string; errorCode?: string | null; requestId?: string | null; context?: Record<string, unknown> | null;
}) {
  return (
    <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
      <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0, fontWeight: 600 }}>{message}</p>
      {(errorCode || requestId) && (
        <p style={{ fontSize: 10, color: "var(--danger-text)", margin: "4px 0 0", opacity: 0.8 }}>
          {errorCode && <>Error Code: {errorCode} </>}
          {requestId && <>· Request ID: {requestId}</>}
        </p>
      )}
      {context && Object.keys(context).length > 0 && (
        <p style={{ fontSize: 10, color: "var(--danger-text)", margin: "4px 0 0", opacity: 0.8 }}>
          {Object.entries(context).map(([k, v]) => `${k}: ${v}`).join(" · ")}
        </p>
      )}
    </div>
  );
}
function ValidationRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
      <ShieldCheck size={14} color={ok ? "var(--success-text)" : "var(--danger-text)"}/>
      <span>{label}</span>
      <Badge variant={ok ? "success" : "danger"} size="sm">{ok ? "Pass" : "Fail"}</Badge>
    </div>
  );
}
export function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
      <div style={{ fontSize: 13, color: "var(--text-primary)" }}>{value === null || value === undefined || value === "" ? "—" : String(value)}</div>
    </div>
  );
}
