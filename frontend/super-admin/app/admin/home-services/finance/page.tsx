"use client";
/**
 * Home Services Finance — single consolidated workspace.
 *
 * One canonical route (/admin/home-services/finance?tab=...). Home Services
 * customers pay the PROVIDER directly (cash/UPI/card/bank transfer) --
 * Fuvay never collects the job payment itself, holds provider earnings,
 * or pays out providers. "Direct Customer Payments" (ServicePaymentRecord,
 * invoice_payment.payment_service.record_onsite_payment) is the provider's
 * on-record of what the customer paid; a separate customer-confirmation
 * step and a separate provider completion charge (commission) exist as
 * distinct, never-merged records. No Payouts tab: confirmed structurally
 * absent for Home Services (vertical_catalog's own rules comment). A
 * provider credit recovery lives under Provider Charges and is
 * never a payout. The Monetization tab configures the Home-Services-only
 * platform charge policy (customer platform charge + provider completion
 * charge) via /v1/admin/home-services/finance/monetization/* -- it reuses
 * the same VerticalMonetizationPolicyService as the generic Platform >
 * Finance > Vertical Monetization page, hardcoded server-side to
 * "home_services", never a second monetization engine.
 */
import { useCallback, useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, FileText, GitCompare, Sparkles, CheckCircle2, Circle, ShieldCheck, Wallet, Plus, Trash2 } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Input, Select, DataTable, Skeleton, Modal, Pagination, Toaster, type ToastItem, SummaryCard,} from "../../../../components/shared/ui";
import { PageHeader } from "@serviceos/design-system";
import { homeServicesFinanceApi, homeServicesFinanceMonetizationApi, homeServicesTopupPlanApi, commerceApi, catalogWorkspaceApi, type CatalogJobType, type MonetizationJobTypeRule, type MonetizationPolicy, type TopupPlan, type CreditPackage } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
// `TopupPlan` here is the finance POLICY type (versioned thresholds) already
// imported from api-hs-finance. The catalogue item is a different record, so
// it is aliased rather than shadowing it.
import { topupPlanApi, type TopupPlan as TopupPlanCatalogItem,
         type TopupPlanInput } from "../../../../lib/api-topup-plans";

let _toastId = 0;
function useToasts() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const push = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = String(++_toastId);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);
  return { toasts, push, remove: (id: string) => setToasts(prev => prev.filter(t => t.id !== id)) };
}

type TabKey =
  | "overview" | "monetization" | "provider-charges" | "credits"
  | "invoices" | "financial-events" | "direct-payments";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "monetization", label: "Monetization" },
  { key: "provider-charges", label: "Provider Charges" },
  { key: "credits", label: "Credits & Top-ups" },
  { key: "direct-payments", label: "Direct Payments" },
  { key: "invoices", label: "Invoices" },
  { key: "financial-events", label: "Financial Events" },
];
const TAB_KEYS = new Set<TabKey>(TABS.map(item => item.key));

function money(v?: string | number | null) {
  const n = Number(v ?? 0);
  return `₹${n.toLocaleString("en-IN")}`;
}
function dt(v?: string | null) {
  return v ? new Date(v).toLocaleString("en-IN") : "—";
}

function useDebouncedValue<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(handle);
  }, [value, delay]);
  return debounced;
}

function QueryError({ message, onRetry }: { message: string | null; onRetry: () => void }) {
  if (!message) return null;
  return (
    <div role="alert" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
      padding: "10px 12px", border: "1px solid var(--danger-border)", borderRadius: 8,
      background: "var(--danger-bg)", color: "var(--danger-text)", fontSize: 12 }}>
      <span>{message}</span>
      <Btn variant="ghost" onClick={onRetry}>Retry</Btn>
    </div>
  );
}
export default function HomeServicesFinancePage() {
  return (
    <Suspense fallback={<Skeleton height={400} />}>
      <HomeServicesFinanceWorkspace />
    </Suspense>
  );
}

function HomeServicesFinanceWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const requestedTab = params.get("tab") as TabKey | null;
  const tab: TabKey = requestedTab && TAB_KEYS.has(requestedTab) ? requestedTab : "overview";
  const [auditOpen, setAuditOpen] = useState(false);

  function setTab(t: TabKey) {
    router.replace(`/admin/home-services/finance?tab=${t}`);
  }

  return (
    <AdminLayout activeNav="hs-finance">
      <div className="hs-finance-shell">
      <PageHeader
        title="Home Services Finance"
        description="Provider charges, usage credits, and customer financial operations for Home Services."
        eyebrow="Financial Control"
        context="Home Services"
        actions={<div style={{ display: "flex", gap: "var(--layout-control-gap)" }}>
          <Btn variant="ghost" icon={<FileText size={14} />} onClick={() => setAuditOpen(true)}>View Audit</Btn>
          <ExportButton tab={tab} />
        </div>}
      />

      <StatusStrip />

      <div className="hs-finance-tabs" role="tablist" aria-label="Finance workspace sections">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className="hs-finance-tab" data-active={tab === t.key} role="tab" aria-selected={tab === t.key}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab onNavigate={setTab} />}
      {tab === "monetization" && <MonetizationTab />}
      {tab === "provider-charges" && <ProviderChargesTab />}
      {tab === "credits" && <CreditsTab params={params} />}
      {tab === "direct-payments" && <DirectPaymentsTab />}
      {tab === "invoices" && <InvoicesTab />}
      {tab === "financial-events" && <FinancialEventsTab />}

      <Modal open={auditOpen} onClose={() => setAuditOpen(false)} title="Audit Trail" size="lg">
        <AuditPanel />
      </Modal>
      </div>
    </AdminLayout>
  );
}

function ExportButton({ tab }: { tab: TabKey }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  if (tab === "overview" || tab === "monetization") return null;

  function csvCell(value: unknown): string {
    let text = value === null || value === undefined ? "" :
      typeof value === "object" ? JSON.stringify(value) : String(value);
    // Prevent spreadsheet applications from interpreting exported user data
    // as a formula when a CSV is opened directly.
    if (/^[=+\-@]/.test(text)) text = `'${text}`;
    return `"${text.replace(/"/g, '""')}"`;
  }

  async function doExport() {
    setBusy(true);
    setMessage("");
    try {
    let rows: Record<string, unknown>[] = [];
    if (tab === "provider-charges") rows = (await homeServicesFinanceApi.listProviderCharges({ pageSize: 200 })).items;
    else if (tab === "credits") rows = (await homeServicesFinanceApi.listTopups({ pageSize: 200 })).items;
    else if (tab === "invoices") rows = (await homeServicesFinanceApi.listInvoices({ pageSize: 200 })).items;
    else if (tab === "financial-events") rows = (await homeServicesFinanceApi.listFinancialEvents({ pageSize: 200 })).items;
    else { const ov = await homeServicesFinanceApi.getOverview(); rows = [ov as Record<string, unknown>]; }

    if (rows.length === 0) { setMessage("No rows available."); return; }
    const headers = Array.from(new Set(rows.flatMap(row => Object.keys(row))));
    const csv = [headers.map(csvCell).join(","), ...rows.map(r => headers.map(h => csvCell(r[h])).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `home-services-finance-${tab}.csv`; a.click();
    URL.revokeObjectURL(url);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Export failed.");
    } finally { setBusy(false); }
  }
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <Btn variant="ghost" icon={<Download size={14} />} onClick={doExport} loading={busy}>
        {tab === "credits" ? "Quick CSV · top-ups" : "Quick CSV · 200 max"}
      </Btn>
      {message && <span role="status" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{message}</span>}
    </div>
  );
}

function StatusStrip() {
  const ledger = useApi(useCallback(() => homeServicesFinanceApi.getLedgerHealth(), []));
  const reconcile = useAction(() => homeServicesFinanceApi.runReconciliation());
  const h = ledger.data;
  return (
    <Card padding={16} style={{ display: "flex", flexWrap: "wrap", gap: 24 }}>
      <StatusDot ok={Boolean(h?.idempotency_protected)} label="Credit ledger idempotency" value={h?.idempotency_protected ? "Protected" : "Checking"} />
      <StatusDot ok={Boolean(h?.append_only)} label="Credit ledger writes" value={h?.append_only ? "Append-only" : "Checking"} />
      <StatusDot ok={Boolean(h?.atomic_balance_update)} label="Balance updates" value={h?.atomic_balance_update ? "Atomic" : "Checking"} />
      <StatusDot ok={Boolean(h?.last_reconciliation)} label="Reconciliation" value={h?.last_reconciliation ? dt(h.last_reconciliation) : "Not yet run"} />
      <Btn variant="ghost" loading={reconcile.loading}
        onClick={async () => { if (await reconcile.execute()) ledger.refetch(); }}>Run reconciliation</Btn>
      {reconcile.error && <span role="alert" style={{ color: "var(--danger-text)", fontSize: 12 }}>{reconcile.error}</span>}
    </Card>
  );
}
function StatusDot({ ok, label, value }: { ok: boolean; label: string; value: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: ok ? "var(--success-text, #0a7c3f)" : "var(--danger-text)" }} />
      <div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{label}</div>
        <div style={{ fontSize: 12, fontWeight: 600 }}>{value}</div>
      </div>
    </div>
  );
}


// ── Overview ─────────────────────────────────────────────────────────────────

type OverviewData = {
  group_a_customer_to_provider: {
    provider_collected_customer_payments: string; payment_confirmations_pending: number;
    customer_platform_charges_recorded: string; payment_disputes: number;
  };
  group_b_serviceos_financial_position: {
    platform_charges_recovered: string | null; platform_charge_recovery_tracked: boolean;
    provider_completion_charges: { posted: number; total_credit_units: string; ledger: string };
    active_usage_credit_balance: string;
  };
  secondary: {
    low_credit_providers: number; failed_charge_recoveries: number;
    warranty_financial_exposure: string; finance_exceptions: number;
  };
  audit_note: string;
};

function OverviewTab({ onNavigate }: { onNavigate: (t: TabKey) => void }) {
  const overview = useApi(useCallback(() => homeServicesFinanceApi.getOverview() as Promise<OverviewData>, []));

  if (overview.loading) return <Skeleton height={300} />;
  if (overview.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Failed to load overview: {overview.error}</p></Card>;
  const o = overview.data;
  if (!o) return null;
  const a = o.group_a_customer_to_provider;
  const b = o.group_b_serviceos_financial_position;
  const sec = o.secondary;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h3 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>
          Customer-to-provider payment records
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
          <SummaryCard label="Collected Directly by Providers" value={money(a.provider_collected_customer_payments)} />
          <SummaryCard label="Confirmations Pending" value={a.payment_confirmations_pending}
            tone={a.payment_confirmations_pending > 0 ? "warning" : undefined} />
          <SummaryCard label="Customer Platform Charges Recorded" value={money(a.customer_platform_charges_recorded)} />
          <SummaryCard label="Payment Disputes" value={a.payment_disputes}
            tone={a.payment_disputes > 0 ? "danger" : undefined} onClick={() => onNavigate("financial-events")} />
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
          Provider-collected customer payments are records, not Fuvay-held funds.
        </p>
      </div>

      <div>
        <h3 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>
          Fuvay financial position
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
          <NotTrackedCard label="Platform-Charge Credits Recovered" tracked={b.platform_charge_recovery_tracked} value={b.platform_charges_recovered} asCredits />
          <SummaryCard label="Provider-Charge Credits Deducted" value={units(b.provider_completion_charges.total_credit_units)} onClick={() => onNavigate("provider-charges")} />
          <SummaryCard label="Provider Charges Posted" value={b.provider_completion_charges.posted} onClick={() => onNavigate("provider-charges")} />
          <SummaryCard label="Available Usage Credits" value={units(b.active_usage_credit_balance)} onClick={() => onNavigate("credits")} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <SummaryCard label="Low-Credit Providers" value={sec.low_credit_providers} tone={sec.low_credit_providers > 0 ? "warning" : undefined} onClick={() => onNavigate("credits")} />
        <SummaryCard label="Failed Charge Recoveries" value={sec.failed_charge_recoveries} tone={sec.failed_charge_recoveries > 0 ? "danger" : undefined} onClick={() => onNavigate("provider-charges")} />
        <SummaryCard label="Provider Warranty Exposure" value={money(sec.warranty_financial_exposure)} />
        <SummaryCard label="Finance Exceptions" value={sec.finance_exceptions} tone={sec.finance_exceptions > 0 ? "danger" : undefined}
          onClick={() => onNavigate("financial-events")} />
      </div>

      <Card padding={16}>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>How Home Services money flows</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", fontSize: 12 }}>
          {["Customer pays provider directly", "Provider records payment", "Customer confirms payment",
            "Customer platform charge recovered from provider credits", "Provider completion charge deducted separately",
            "Ledger entries posted"].map((step, i, arr) => (
            <span key={step} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {step}{i < arr.length - 1 && <span style={{ color: "var(--text-tertiary)" }}>→</span>}
            </span>
          ))}
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 10, marginBottom: 0 }}>
          Fuvay does not hold or pay out provider service earnings.
        </p>
      </Card>

      <Card padding={16} style={{ borderColor: "var(--warning-text, #b45309)" }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 6px" }}>Audit note</h3>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>{o.audit_note}</p>
      </Card>
    </div>
  );
}

function NotTrackedCard({ label, tracked, value, asCredits = false }: { label: string; tracked: boolean; value: string | null; asCredits?: boolean }) {
  return (
    <Card padding={16}>
      <div style={{ fontSize: 22, fontWeight: 800, color: tracked ? "var(--text-primary)" : "var(--text-tertiary)" }}>
        {tracked ? (asCredits ? units(value) : money(value)) : "Not tracked"}
      </div>
      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>{label}</div>
    </Card>
  );
}

// ── Monetization ─────────────────────────────────────────────────────────────
// Home-Services-only policy workspace: reuses the same monetization engine as
// Platform > Finance > Vertical Monetization, hardcoded server-side to
// "home_services" so it can never read or mutate another vertical's policy.

// All values are real enum values on the shared cross-vertical policy.
// Completion credits, fixed completion charges and percentage commission
// are wired to the Home Services completed-job usage-credit ledger. For
// PERCENTAGE_COMMISSION,
// execution/usage_credit_deduction.py::resolve_commission_credits charges
// this % of the final invoiced service value. This policy's
// provider_percentage is the only Home Services rate. Subscription
// and lead-fee models remain draftable for forward planning; server-side
// validation prevents publishing them until their runtime engines exist.
const PROVIDER_MODELS = [
  { value: "NONE", label: "No provider charge" },
  { value: "PERCENTAGE_COMMISSION", label: "Percentage commission" },
  { value: "COMPLETION_CREDITS", label: "Fixed credits per completed job" },
] as const;
// WHEN the provider is charged. Each value is a real lifecycle hook that
// attempts the deduction, so an admin can only pick a moment the runtime
// actually reaches. The deduction is idempotent per job, so a job passing
// several of these is still charged exactly once -- at the configured one.
const PROVIDER_CHARGE_EVENTS = [
  { value: "job_completed",          label: "When the job is completed" },
  { value: "consultation_completed", label: "When a consultation is completed" },
  { value: "work_done",              label: "When the technician marks work done" },
  { value: "work_started",           label: "When the technician starts work" },
] as const;
// Only `before_work_start` is enforced today -- it blocks work start until the
// fee is paid. The others are recorded on the charge but gate nothing yet, so
// they are labelled honestly rather than implying an enforcement that is absent.
const COLLECTION_STAGES = [
  { value: "before_work_start",          label: "Before work starts — blocks work until paid", enforced: true },
  { value: "before_booking_confirmation", label: "At booking confirmation (recorded, not enforced)", enforced: false },
  { value: "after_estimate_approval",     label: "After estimate approval (recorded, not enforced)", enforced: false },
  { value: "on_completion",               label: "On completion (recorded, not enforced)", enforced: false },
] as const;
const CUSTOMER_FEE_MODELS = [
  { value: "NONE", label: "No customer charge" },
  { value: "PERCENTAGE", label: "Percentage added to service price" },
  { value: "FIXED", label: "Fixed amount added to service price" },
  { value: "PERCENTAGE_WITH_MIN_MAX", label: "Percentage with minimum / maximum" },
] as const;

function fmt(v: unknown): string {
  return v === null || v === undefined ? "—" : String(v);
}

function MonetizationTab() {
  const { toasts, push, remove } = useToasts();
  const [showDraftDrawer, setShowDraftDrawer] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [previewAmount, setPreviewAmount] = useState("500");
  const [previewResult, setPreviewResult] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState<Partial<MonetizationPolicy>>({});
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [ruleJobTypeId, setRuleJobTypeId] = useState("");
  const [ruleCredits, setRuleCredits] = useState("");
  const [ruleProviderEnabled, setRuleProviderEnabled] = useState(true);
  const [ruleCustomerEnabled, setRuleCustomerEnabled] = useState(true);

  const currentApi = useApi(useCallback(() => homeServicesFinanceMonetizationApi.getCurrent(), []));
  const draftApi = useApi(useCallback(() => homeServicesFinanceMonetizationApi.getDraft(), []));
  const historyApi = useApi(useCallback(() => homeServicesFinanceMonetizationApi.getHistory(), []), [showCompare], { enabled: showCompare });

  const saveDraftAction = useAction((p: Partial<MonetizationPolicy>) => homeServicesFinanceMonetizationApi.saveDraft(p));
  const publishAction = useAction((r: string) => homeServicesFinanceMonetizationApi.publish(r));
  const discardDraftAction = useAction(() => homeServicesFinanceMonetizationApi.discardDraft());

  const current = currentApi.data as MonetizationPolicy | null;
  const draft = draftApi.data as MonetizationPolicy | null;
  const jobTypesApi = useApi(
    useCallback(() => catalogWorkspaceApi.listJobTypes({ includeInactive: false, pageSize: 100 }), []),
    [], { enabled: true },
  );
  const draftRulesApi = useApi(
    useCallback(() => homeServicesFinanceMonetizationApi.listJobTypeRules(draft?.id ?? ""), [draft?.id]),
    [draft?.id], { enabled: showDraftDrawer && !!draft?.id },
  );
  const currentRulesApi = useApi(
    useCallback(() => homeServicesFinanceMonetizationApi.listJobTypeRules(current?.id ?? ""), [current?.id]),
    [current?.id], { enabled: !!current?.id },
  );
  const saveRuleAction = useAction((policyId: string, jobTypeId: string, payload: Partial<MonetizationJobTypeRule>) =>
    homeServicesFinanceMonetizationApi.upsertJobTypeRule(policyId, jobTypeId, payload));
  const providerModelLive = ["COMPLETION_CREDITS", "PERCENTAGE_COMMISSION", "FIXED_COMPLETION_CHARGE"]
    .includes(current?.provider_model ?? "");
  const providerStatusLabel = !current ? "Not configured"
    : providerModelLive ? "Live" : current.provider_model === "NONE" ? "Disabled" : "Not enforceable";
  const providerStatusVariant = providerModelLive ? "success"
    : current?.provider_model === "NONE" || !current ? "muted" : "warning";
  const customerFeeLive = !!current && current.customer_fee_model !== "NONE";

  function startDraft() {
    setForm(draft ?? current ?? { provider_model: "COMPLETION_CREDITS", customer_fee_model: "NONE", currency: "INR" });
    setErrors([]); setPreviewResult(null);
    setShowDraftDrawer(true);
  }

  async function runPreview() {
    const v = await homeServicesFinanceMonetizationApi.validate(form);
    setErrors(v.errors);
    if (v.errors.length === 0) {
      const p = await homeServicesFinanceMonetizationApi.preview(form, previewAmount);
      setPreviewResult(p);
    } else {
      push("Fix validation errors before previewing.", "warning");
    }
  }

  async function saveDraft() {
    const r = await saveDraftAction.execute(form);
    if (r) { draftApi.refetch(); push("Draft saved."); }
    else push(saveDraftAction.error ?? "Failed to save draft.", "danger");
  }

  async function confirmPublish() {
    if (!reason.trim()) return;
    const validation = await homeServicesFinanceMonetizationApi.validate(form);
    setErrors(validation.errors);
    if (!validation.valid) {
      push("This draft cannot be published until its validation errors are resolved.", "warning");
      return;
    }
    // Publish only takes a reason -- it publishes whatever draft is already
    // saved server-side. If the on-screen form was edited but never sent via
    // "Save Draft", those edits were silently lost (or, with no draft ever
    // saved, publish 404'd outright). Always sync the current form first so
    // Publish reflects exactly what's on screen, edit-then-publish in one step.
    const saved = await saveDraftAction.execute(form);
    if (!saved) {
      push(saveDraftAction.error ?? "Failed to save your changes before publishing.", "danger");
      return;
    }
    const r = await publishAction.execute(reason.trim());
    if (r) {
      setShowDraftDrawer(false); setReason(""); currentApi.refetch(); draftApi.refetch();
      push("Policy published — now live.");
    } else {
      push(publishAction.error ?? "Failed to publish.", "danger");
    }
  }

  async function discardDraft() {
    const r = await discardDraftAction.execute();
    if (r) { setShowDraftDrawer(false); draftApi.refetch(); push("Draft discarded."); }
    else push(discardDraftAction.error ?? "Failed to discard draft.", "danger");
  }

  async function saveJobTypeRule() {
    if (!draft?.id || !ruleJobTypeId) return;
    const parsedCredits = ruleCredits.trim() === "" ? null : Number(ruleCredits);
    if (parsedCredits != null && (!Number.isFinite(parsedCredits) || parsedCredits < 0)) {
      push("Fixed credit override must be zero or greater.", "warning");
      return;
    }
    const selectedJobType = jobTypesApi.data?.items?.find((item: CatalogJobType) => item.id === ruleJobTypeId);
    const providerChargeableEvent = selectedJobType?.key === "consultation"
      ? "consultation_completed" : "job_completed";
    const providerChargeModel = parsedCredits == null ? "INHERIT" : "FIXED_CREDITS";
    const saved = await saveRuleAction.execute(draft.id, ruleJobTypeId, {
      job_type_id: ruleJobTypeId,
      provider_charge_enabled: ruleProviderEnabled,
      provider_charge_model: providerChargeModel,
      provider_charge_credit_units: parsedCredits == null ? null : String(parsedCredits),
      provider_chargeable_event: providerChargeableEvent,
      customer_charge_enabled: ruleCustomerEnabled,
      customer_charge_basis: "booking_price_snapshot",
      status: "active",
    });
    if (saved) {
      draftRulesApi.refetch();
      setRuleJobTypeId(""); setRuleCredits("");
      setRuleProviderEnabled(true); setRuleCustomerEnabled(true);
      push("Job Type rule saved to this draft.");
    } else {
      push(saveRuleAction.error ?? "Could not save the Job Type rule.", "danger");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Toaster toasts={toasts} onRemove={remove} />
      <Card padding={16} style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "center" }}>
        <StatusDot ok={!!current} label="Published Policy" value={current ? `v${current.version_number}` : "None"} />
        <StatusDot ok label="Settlement" value="Provider Direct" />
        <StatusDot ok label="Recovery" value="Usage Credits" />
        <StatusDot ok={!draft} label="Draft" value={draft ? `v${draft.version_number}` : "None"} />
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Btn variant="ghost" icon={<GitCompare size={14} />} onClick={() => setShowCompare(true)}>Compare Versions</Btn>
          {draft && (
            <Btn variant="ghost" icon={<Trash2 size={14} />} onClick={discardDraft} disabled={discardDraftAction.loading}
              style={{ color: "var(--danger-text)" }}>
              {discardDraftAction.loading ? "Deleting…" : "Delete Draft"}
            </Btn>
          )}
          <Btn variant="primary" icon={<Sparkles size={14} />} onClick={startDraft}>{draft ? "Edit Draft" : "Create Draft"}</Btn>
        </div>
      </Card>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <div style={{ flex: 2, minWidth: 320, display: "flex", flexDirection: "column", gap: 14 }}>
          <Card padding={16}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <p style={{ fontSize: 14, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                Provider-side charge <Badge variant={providerStatusVariant}>{providerStatusLabel}</Badge>
              </p>
              <Btn variant="ghost" onClick={startDraft}>Edit in Draft</Btn>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 14, fontSize: 12 }}>
              <KV label="Revenue model" value={fmt(current?.provider_model)} />
              <KV label="Trigger" value="Eligible job completion" />
              <KV label="Configured charge" value={
                current?.provider_model === "PERCENTAGE_COMMISSION"
                  ? (current.provider_percentage != null ? `${current.provider_percentage}%` : "Not configured")
                  : current?.provider_model === "COMPLETION_CREDITS"
                    ? units(current.provider_credit_units ?? 0)
                    : current?.provider_model === "FIXED_COMPLETION_CHARGE"
                      ? units(Number(current.provider_fixed_amount_minor ?? 0) / 100)
                      : "—"
              } />
              <KV label="Recovery source" value="Provider usage credits" />
              <KV label="Job Type rules" value={String(currentRulesApi.data?.items?.length ?? 0)} />
            </div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
              {current?.provider_model === "PERCENTAGE_COMMISSION"
                ? "This is the single provider commission rate for Home Services. It is charged as a percentage of the final invoiced service value, excluding the customer platform fee."
                : current?.provider_model === "COMPLETION_CREDITS"
                  ? "A fixed number of usage-credit units is deducted for each eligible completed job."
                  : current?.provider_model === "FIXED_COMPLETION_CHARGE"
                    ? "The configured fixed amount is converted to rupee-equivalent usage-credit units at job completion."
                    : "No provider-side completion charge is active."}
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", flexWrap: "wrap" }}>
              <CheckCircle2 size={13} /> Eligible completion → <CheckCircle2 size={13} /> Idempotency check → <CheckCircle2 size={13} /> Credits deducted → <CheckCircle2 size={13} /> Ledger posted
            </div>
          </Card>

          <Card padding={16}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10 }}>
              <div>
                <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Job Type charge rules</p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "3px 0 0" }}>
                  Published exceptions for repair, consultation and other Job Types.
                </p>
              </div>
              <Btn variant="ghost" onClick={startDraft}>{draft ? "Edit rules" : "Create rules"}</Btn>
            </div>
            {currentRulesApi.loading ? (
              <p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)" }}>Loading published rules…</p>
            ) : (currentRulesApi.data?.items ?? []).length === 0 ? (
              <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>
                No published Job Type overrides. Every Job Type currently inherits the default provider and customer charge policy.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(currentRulesApi.data?.items ?? []).map((rule: MonetizationJobTypeRule) => {
                  const jt = jobTypesApi.data?.items?.find((item: CatalogJobType) => item.id === rule.job_type_id);
                  return (
                    <div key={rule.job_type_id} style={{ display: "flex", justifyContent: "space-between", gap: 10, padding: "10px 12px", border: "1px solid var(--border)", borderRadius: 9, fontSize: 12 }}>
                      <span>
                        <strong>{jt?.label ?? rule.job_type_id}</strong>
                        {jt?.key ? <span style={{ color: "var(--text-tertiary)" }}> · {jt.key}</span> : null}
                        <br />
                        Provider {rule.provider_charge_enabled ? (rule.provider_charge_model === "FIXED_CREDITS" ? `${rule.provider_charge_credit_units} fixed credits` : "inherits default") : "disabled"}
                        {" · "}Trigger {rule.provider_chargeable_event === "consultation_completed" ? "consultation completed" : "job completed"}
                        {" · "}Customer {rule.customer_charge_enabled ? "enabled" : "disabled"}
                      </span>
                      <Badge variant={rule.status === "active" ? "success" : "muted"}>{rule.status}</Badge>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          <Card padding={16}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <p style={{ fontSize: 14, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                Customer platform charge <Badge variant={customerFeeLive ? "success" : "muted"}>{customerFeeLive ? "Live" : "Disabled"}</Badge>
              </p>
              <Btn variant="ghost" onClick={startDraft}>Edit in Draft</Btn>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 12, fontSize: 12 }}>
              <KV label="Fee model" value={fmt(current?.customer_fee_model)} />
              <KV label="Configured charge" value={
                current?.customer_fee_model === "FIXED"
                  ? money(Number(current.customer_fee_fixed_amount_minor ?? 0) / 100)
                  : current?.customer_fee_percentage ? `${current.customer_fee_percentage}%` : "—"
              } />
              <KV label="Minimum" value={current?.customer_fee_min_minor != null ? money(current.customer_fee_min_minor / 100) : "—"} />
              <KV label="Maximum" value={current?.customer_fee_max_minor != null ? money(current.customer_fee_max_minor / 100) : "—"} />
              <KV label="Collection" value="Provider collects directly" />
              <KV label="Recovery" value="Deducted from usage credits" />
            </div>
            <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>
              The customer pays the inclusive amount to the provider. At job completion, Fuvay recovers this customer charge from the provider&apos;s usage credits in addition to the provider-side charge.
            </div>
          </Card>
        </div>

        <div style={{ flex: 1, minWidth: 280, display: "flex", flexDirection: "column", gap: 14 }}>
          <Card padding={16}>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px" }}>Calculation preview</p>
            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>Service amount</label>
            <div style={{ display: "flex", gap: 8, margin: "4px 0 12px" }}>
              <Input value={previewAmount} onChange={setPreviewAmount} />
              <Btn variant="primary" onClick={async () => setPreviewResult(await homeServicesFinanceMonetizationApi.preview(current ?? {}, previewAmount))}>Go</Btn>
            </div>
            {previewResult && (
              <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12 }}>
                <PreviewRow label="Customer platform charge" value={`₹${fmt(previewResult.customer_platform_fee)}`} />
                <PreviewRow label="Customer pays provider directly" value={`₹${fmt(previewResult.total_payable)}`} strong />
                <PreviewRow label="Provider-side credit deduction" value={units(previewResult.provider_charge_credit_units as string)} />
                <PreviewRow label="Customer-charge credit recovery" value={units(previewResult.customer_charge_recovery_credit_units as string)} />
                <PreviewRow label="Total credits deducted at completion" value={units(previewResult.total_credit_deduction as string)} strong />
                <PreviewRow label="Provider calculation" value={fmt(previewResult.provider_charge_note)} />
                <PreviewRow label="Fuvay holds provider earnings" value="₹0" />
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>Preview only — does not change tenant pricing.</p>
              </div>
            )}
          </Card>

          <Card padding={16}>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px" }}>Policy lifecycle</p>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, fontSize: 12,
              color: draft ? "var(--warning-text)" : "var(--text-tertiary)" }}>
              {draft ? <Circle size={13} /> : <CheckCircle2 size={13} />} Draft {draft ? `v${draft.version_number} awaiting publication` : "none"}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, fontSize: 12,
              color: previewResult ? "var(--success-text)" : "var(--text-tertiary)" }}>
              {previewResult ? <CheckCircle2 size={13} /> : <Circle size={13} />} Impact preview {previewResult ? "completed this session" : "not run this session"}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, fontSize: 12,
              color: current ? "var(--success-text)" : "var(--text-tertiary)" }}>
              {current ? <CheckCircle2 size={13} /> : <Circle size={13} />} Published version {current ? `v${current.version_number}` : "none"}
            </div>
            <Badge variant={current ? "success" : "muted"}>{current ? `v${current.version_number} Published` : "No published policy"}</Badge>
          </Card>

          <Card padding={16}>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px", display: "flex", alignItems: "center", gap: 6 }}>
              <ShieldCheck size={15} /> Safety &amp; scope
            </p>
            {["Home Services only", "Provider direct settlement", "Two independent ledger entries",
              "Tenant prices not editable", "Other verticals unaffected"].map(item => (
              <div key={item} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", marginBottom: 5 }}>
                <CheckCircle2 size={12} style={{ color: "var(--success-text)" }} /> {item}
              </div>
            ))}
          </Card>
        </div>
      </div>

      {showDraftDrawer && (
        <Modal open onClose={() => setShowDraftDrawer(false)} title="Create Draft — Home Services Monetization" size="md">
          <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
            Provider-side charge — deducted from the provider
          </label>
          <select value={form.provider_model ?? "NONE"} onChange={e => setForm({ ...form, provider_model: e.target.value })}
            style={{ width: "100%", padding: "7px 9px", margin: "4px 0 10px" }}>
            {PROVIDER_MODELS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
          {form.provider_model !== "NONE" && (
            <>
              <label style={{ fontSize: 12, fontWeight: 600 }}>When to charge the provider</label>
              <select value={form.provider_chargeable_event ?? "job_completed"}
                onChange={e => setForm({ ...form, provider_chargeable_event: e.target.value })}
                style={{ width: "100%", padding: "7px 9px", margin: "4px 0 4px" }}>
                {PROVIDER_CHARGE_EVENTS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
              {form.provider_model === "PERCENTAGE_COMMISSION"
                && ["work_started", "work_done"].includes(form.provider_chargeable_event ?? "") ? (
                <p style={{ fontSize: 11, color: "var(--danger-text)", margin: "0 0 10px" }}>
                  A percentage needs the final invoiced value, which does not exist before the job
                  completes — on an inspection job the booking price is only the visit fee. Charge at
                  completion, or use a fixed credit model to charge earlier.
                </p>
              ) : (
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
                  Charged once per job, at this moment. A job that passes several stages is still
                  charged exactly once.
                </p>
              )}
            </>
          )}
          {form.provider_model === "PERCENTAGE_COMMISSION" ? (
            <>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px" }}>
                Deduct this percentage of the provider&apos;s final service price. The customer charge is calculated separately and never increases this commission base.
              </p>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Provider commission (%)</label>
              <Input placeholder="e.g. 10" value={String(form.provider_percentage ?? "")}
                onChange={v => setForm({ ...form, provider_percentage: v })} />
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Minimum credits (optional)</label>
                  <Input placeholder="No minimum" value={form.provider_min_charge_minor != null ? String(form.provider_min_charge_minor / 100) : ""}
                    onChange={v => setForm({ ...form, provider_min_charge_minor: v === "" ? null : Math.round(Number(v) * 100) })} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Maximum credits (optional)</label>
                  <Input placeholder="No maximum" value={form.provider_max_charge_minor != null ? String(form.provider_max_charge_minor / 100) : ""}
                    onChange={v => setForm({ ...form, provider_max_charge_minor: v === "" ? null : Math.round(Number(v) * 100) })} />
                </div>
              </div>
            </>
          ) : null}
          {["COMPLETION_CREDITS", "PERCENTAGE_COMMISSION"].includes(form.provider_model ?? "") && (
            <>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px" }}>
                Deduct the same fixed number of usage credits whenever an eligible job is completed. Add Job Type rules below when some work types need a different fixed deduction.
              </p>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Default fixed credit deduction</label>
              <Input placeholder="e.g. 100 credits" value={String(form.provider_credit_units ?? "")}
                onChange={v => setForm({ ...form, provider_credit_units: v === "" ? null : Number(v) })} />
            </>
          )}

          <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.03em", marginTop: 16, display: "block" }}>
            Customer-side charge — added to what the customer pays
          </label>
          <select value={form.customer_fee_model ?? "NONE"} onChange={e => setForm({ ...form, customer_fee_model: e.target.value })}
            style={{ width: "100%", padding: "7px 9px", margin: "4px 0 10px" }}>
            {CUSTOMER_FEE_MODELS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
          {form.customer_fee_model !== "NONE" && (
            <>
              <label style={{ fontSize: 12, fontWeight: 600 }}>When to collect from the customer</label>
              <select value={form.collection_stage ?? "after_estimate_approval"}
                onChange={e => setForm({ ...form, collection_stage: e.target.value })}
                style={{ width: "100%", padding: "7px 9px", margin: "4px 0 4px" }}>
                {COLLECTION_STAGES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
              {!COLLECTION_STAGES.find(x => x.value === (form.collection_stage ?? "after_estimate_approval"))?.enforced && (
                <p style={{ fontSize: 11, color: "var(--warning-text, var(--text-tertiary))", margin: "0 0 10px" }}>
                  The charge is created and recorded at this stage, but nothing blocks the customer
                  from proceeding without paying it. Only &quot;before work starts&quot; is enforced today.
                </p>
              )}
            </>
          )}
          {(form.customer_fee_model === "PERCENTAGE" || form.customer_fee_model === "PERCENTAGE_WITH_MIN_MAX") && (
            <>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px" }}>
                Added on top of the provider&apos;s service price. The customer pays this inclusive total to the provider, and the same charge is recovered from provider usage credits at completion.
              </p>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Customer charge (%)</label>
              <Input placeholder="e.g. 10" value={String(form.customer_fee_percentage ?? "")}
                onChange={v => setForm({ ...form, customer_fee_percentage: v })} />
            </>
          )}
          {form.customer_fee_model === "FIXED" && (
            <>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Fixed customer charge (₹)</label>
              <Input placeholder="e.g. 50" value={form.customer_fee_fixed_amount_minor != null ? String(form.customer_fee_fixed_amount_minor / 100) : ""}
                onChange={v => setForm({ ...form, customer_fee_fixed_amount_minor: v === "" ? null : Math.round(Number(v) * 100) })} />
            </>
          )}
          {form.customer_fee_model === "PERCENTAGE_WITH_MIN_MAX" && (
            <div style={{ display: "flex", gap: 8 }}>
              <Input placeholder="Min fee (₹)" value={form.customer_fee_min_minor != null ? String(form.customer_fee_min_minor / 100) : ""}
                onChange={v => setForm({ ...form, customer_fee_min_minor: Math.round(Number(v) * 100) })} />
              <Input placeholder="Max fee (₹)" value={form.customer_fee_max_minor != null ? String(form.customer_fee_max_minor / 100) : ""}
                onChange={v => setForm({ ...form, customer_fee_max_minor: Math.round(Number(v) * 100) })} />
            </div>
          )}

          {previewResult && (
            <div style={{ marginTop: 14, padding: 12, border: "1px solid var(--border)", borderRadius: 10, background: "var(--surface-sunken)" }}>
              <p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700 }}>Combined completion impact</p>
              <PreviewRow label="Provider service price" value={`₹${previewAmount}`} />
              <PreviewRow label="Customer charge added" value={`₹${fmt(previewResult.customer_platform_fee)}`} />
              <PreviewRow label="Customer sees and pays" value={`₹${fmt(previewResult.total_payable)}`} strong />
              <PreviewRow label="Provider-side deduction" value={units(previewResult.provider_charge_credit_units as string)} />
              <PreviewRow label="Customer-charge recovery" value={units(previewResult.customer_charge_recovery_credit_units as string)} />
              <PreviewRow label="Total credits deducted when job completes" value={units(previewResult.total_credit_deduction as string)} strong />
            </div>
          )}

          {(
            <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
              <p style={{ margin: "0 0 4px", fontSize: 12, fontWeight: 700 }}>Job Type charge rules</p>
              <p style={{ margin: "0 0 10px", fontSize: 11, color: "var(--text-tertiary)" }}>
                Repair and fixed-price jobs can inherit the default policy. Consultation can use a fixed credit price charged when the consultation is completed. Save the base draft first; rules are versioned and publish with it.
              </p>
              {!draft?.id ? (
                <div style={{ padding: 10, borderRadius: 8, background: "var(--surface-sunken)", fontSize: 11, color: "var(--text-secondary)" }}>
                  Save Draft to enable Job Type rules.
                </div>
              ) : (
                <>
                  <select value={ruleJobTypeId} onChange={e => setRuleJobTypeId(e.target.value)}
                    disabled={jobTypesApi.loading || !!jobTypesApi.error}
                    style={{ width: "100%", padding: "7px 9px", marginBottom: 8 }}>
                    <option value="">
                      {jobTypesApi.loading ? "Loading Job Types…" : jobTypesApi.error ? "Could not load Job Types" : (jobTypesApi.data?.items ?? []).filter((jt: CatalogJobType) => jt.runtime_supported).length === 0 ? "No execution-enabled Job Types" : "Select Job Type"}
                    </option>
                    {(jobTypesApi.data?.items ?? []).filter((jt: CatalogJobType) => jt.runtime_supported).map((jt: CatalogJobType) => (
                      <option key={jt.id} value={jt.id}>{jt.label} · {jt.key}</option>
                    ))}
                  </select>
                  {jobTypesApi.error ? (
                    <p style={{ margin: "-2px 0 8px", fontSize: 11, color: "var(--danger-text)" }}>
                      {jobTypesApi.error}
                    </p>
                  ) : null}
                  <Input
                    placeholder={jobTypesApi.data?.items?.find((jt: CatalogJobType) => jt.id === ruleJobTypeId)?.key === "consultation"
                      ? "Consultation credits deducted when consultation is done"
                      : "Fixed credits deducted when job is completed (blank uses default)"}
                    value={ruleCredits}
                    onChange={setRuleCredits}
                  />
                  <div style={{ display: "flex", gap: 16, margin: "10px 0", flexWrap: "wrap", fontSize: 12 }}>
                    <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <input type="checkbox" checked={ruleProviderEnabled} onChange={e => setRuleProviderEnabled(e.target.checked)} />
                      Apply provider deduction
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <input type="checkbox" checked={ruleCustomerEnabled} onChange={e => setRuleCustomerEnabled(e.target.checked)} />
                      Apply customer charge
                    </label>
                  </div>
                  <Btn variant="secondary" size="sm" disabled={!ruleJobTypeId || saveRuleAction.loading} onClick={saveJobTypeRule}>
                    {saveRuleAction.loading ? "Saving…" : "Add / update rule"}
                  </Btn>
                  {(draftRulesApi.data?.items ?? []).length > 0 && (
                    <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
                      {(draftRulesApi.data?.items ?? []).map((rule: MonetizationJobTypeRule) => {
                        const jt = jobTypesApi.data?.items?.find((item: CatalogJobType) => item.id === rule.job_type_id);
                        return (
                          <div key={rule.job_type_id} style={{ display: "flex", justifyContent: "space-between", gap: 8, padding: "7px 9px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 11 }}>
                            <span><strong>{jt?.label ?? rule.job_type_id}</strong><br />Provider {rule.provider_charge_enabled ? (rule.provider_charge_model === "FIXED_CREDITS" ? `${rule.provider_charge_credit_units} fixed credits` : "inherits default") : "disabled"} · Trigger {rule.provider_chargeable_event === "consultation_completed" ? "consultation completed" : "job completed"} · Customer {rule.customer_charge_enabled ? "enabled" : "disabled"}</span>
                            <Badge variant={rule.status === "active" ? "success" : "muted"}>{rule.status}</Badge>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
          {/* ── SLA breach & penalty ──────────────────────────────────────
              Every lever here is policy rather than code, so a penalty can be
              retuned, reviewed and rolled back like a commission rate. */}
          <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
            <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 2 }}>
              Late jobs — SLA breach &amp; penalty
            </label>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
              Measured from the scheduled slot, so a job booked well in advance is never
              late early. Leave the hours blank to disable this entirely.
            </p>

            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600 }}>Breach after (hours)</label>
                <Input placeholder="e.g. 24" value={String(form.sla_breach_hours ?? "")}
                  onChange={v => setForm({ ...form, sla_breach_hours: v === "" ? null : Number(v) })} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600 }}>Penalty type</label>
                <select value={form.sla_penalty_type ?? "fixed"}
                  onChange={e => setForm({ ...form, sla_penalty_type: e.target.value })}
                  style={{ width: "100%", padding: "7px 9px", marginTop: 4 }}>
                  <option value="fixed">Fixed amount</option>
                  <option value="percentage">Percentage of job value</option>
                </select>
              </div>
            </div>

            {form.sla_penalty_type === "percentage" ? (
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 12, fontWeight: 600 }}>Percentage (%)</label>
                  <Input placeholder="e.g. 5" value={String(form.sla_penalty_percentage ?? "")}
                    onChange={v => setForm({ ...form, sla_penalty_percentage: v })} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 12, fontWeight: 600 }}>Minimum (₹)</label>
                  <Input value={String(form.sla_penalty_min ?? "")}
                    onChange={v => setForm({ ...form, sla_penalty_min: v === "" ? null : Number(v) })} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 12, fontWeight: 600 }}>Maximum (₹)</label>
                  <Input value={String(form.sla_penalty_max ?? "")}
                    onChange={v => setForm({ ...form, sla_penalty_max: v === "" ? null : Number(v) })} />
                </div>
              </div>
            ) : (
              <div style={{ marginTop: 8 }}>
                <label style={{ fontSize: 12, fontWeight: 600 }}>Penalty amount (₹)</label>
                <Input placeholder="e.g. 50" value={String(form.sla_penalty_amount ?? "")}
                  onChange={v => setForm({ ...form, sla_penalty_amount: v === "" ? null : Number(v) })} />
              </div>
            )}

            <div style={{ marginTop: 8 }}>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Maximum penalty debt (₹)</label>
              <Input placeholder="e.g. 500" value={String(form.sla_penalty_debt_cap ?? "")}
                onChange={v => setForm({ ...form, sla_penalty_debt_cap: v === "" ? null : Number(v) })} />
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                A penalty may take a balance negative — a provider already at zero would
                otherwise face no penalty at all. This is how far that can go before
                further penalties stop being charged.
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
              <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={form.sla_auto_cancel !== false}
                  onChange={e => setForm({ ...form, sla_auto_cancel: e.target.checked })} />
                Cancel the job so the customer can rebook
              </label>
              <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={!!form.sla_penalty_to_customer}
                  onChange={e => setForm({ ...form, sla_penalty_to_customer: e.target.checked })} />
                Give the penalty to the customer as service credit
              </label>
              <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={form.sla_notify_provider !== false}
                  onChange={e => setForm({ ...form, sla_notify_provider: e.target.checked })} />
                Tell the provider why they were charged
              </label>
            </div>
          </div>

          {/* ── Health suspension ─────────────────────────────────────────── */}
          <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
            <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 2 }}>
              Health suspension
            </label>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
              Health is already 20% of provider ranking, so a falling score costs a provider
              work before this ever applies. Leave blank to never suspend anyone.
            </p>
            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600 }}>Suspend below</label>
                <Input placeholder="e.g. 40" value={String(form.health_suspension_threshold ?? "")}
                  onChange={v => setForm({ ...form, health_suspension_threshold: v === "" ? null : Number(v) })} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600 }}>For (days)</label>
                <Input placeholder="e.g. 90" value={String(form.health_suspension_days ?? "")}
                  onChange={v => setForm({ ...form, health_suspension_days: v === "" ? null : Number(v) })} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600 }}>Return at</label>
                <Input placeholder="e.g. 55" value={String(form.health_reinstatement_score ?? "")}
                  onChange={v => setForm({ ...form, health_reinstatement_score: v === "" ? null : Number(v) })} />
              </div>
            </div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
              Return-at must be above the threshold. Health is earned from work a suspended
              provider cannot do, so reinstating them at the same score would re-suspend
              them the same day, permanently.
            </p>
          </div>

          {errors.length > 0 && errors.map(e => <p key={e} style={{ fontSize: 11, color: "var(--danger-text)" }}>{e}</p>)}
          <div style={{ display: "flex", gap: 8, margin: "14px 0" }}>
            <Btn variant="secondary" onClick={runPreview}>Validate &amp; Preview</Btn>
            <Btn variant="secondary" onClick={saveDraft} disabled={saveDraftAction.loading}>Save Draft</Btn>
            {draft && (
              <Btn variant="ghost" onClick={discardDraft} disabled={discardDraftAction.loading}
                style={{ color: "var(--danger-text)" }}>
                {discardDraftAction.loading ? "Discarding…" : "Discard Draft"}
              </Btn>
            )}
          </div>
          <label style={{ fontSize: 12, fontWeight: 600 }}>Publish reason (required)</label>
          <Input value={reason} onChange={setReason} />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
            <Btn variant="ghost" onClick={() => setShowDraftDrawer(false)}>Cancel</Btn>
            <Btn variant="primary" disabled={!reason.trim() || errors.length > 0} onClick={confirmPublish}>
              {publishAction.loading ? "Publishing…" : "Review & Publish"}
            </Btn>
          </div>
        </Modal>
      )}

      <Modal open={showCompare} onClose={() => setShowCompare(false)} title="Compare Versions" size="md">
        {((historyApi.data as { items: MonetizationPolicy[] } | null)?.items ?? []).map(v => (
          <div key={v.id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
            <p style={{ margin: 0, fontWeight: 600 }}>v{v.version_number} · {v.status}</p>
            <p style={{ margin: "2px 0", color: "var(--text-secondary)" }}>{v.provider_model} / {v.customer_fee_model}</p>
          </div>
        ))}
      </Modal>
    </div>
  );
}

// ── Credit thresholds ───────────────────────────────────────────────────────
// The two numbers that decide when a provider is warned and when their
// bookings stop. They live on the activation finance policy, which is a
// different versioned record from the monetization policy above -- so this
// card drives its own draft/publish cycle rather than sharing that form.
//
// They had no admin surface at all: the only card that ever edited this policy
// set the starter-purchase fields, which were retired with the activation
// requirement. The floor is what protects the platform now, so it needs to be
// something an operator can actually change.
function CreditThresholdsSection({ onToast }: { onToast: (msg: string, variant?: ToastItem["variant"]) => void }) {
  const [open, setOpen] = useState(false);
  const [warn, setWarn] = useState("");
  const [floor, setFloor] = useState("");
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<string[]>([]);

  const currentApi = useApi(useCallback(() => homeServicesTopupPlanApi.getCurrent(), []));
  const saveDraftAction = useAction((p: Record<string, unknown>) => homeServicesTopupPlanApi.saveDraft(p));
  const publishAction = useAction((r: string) => homeServicesTopupPlanApi.publish(r));
  const current = currentApi.data as TopupPlan | null;

  function startEdit() {
    setWarn(String(current?.credit_warning_threshold ?? ""));
    setFloor(String(current?.credit_booking_floor ?? ""));
    setReason(""); setErrors([]); setOpen(true);
  }

  async function saveAndPublish() {
    const payload = {
      credit_warning_threshold: Number(warn),
      credit_booking_floor: Number(floor),
      change_summary: reason.trim() || "Credit thresholds updated",
    };
    const draft = await saveDraftAction.execute(payload);
    if (!draft) {
      setErrors([saveDraftAction.error ?? "Could not save the draft."]);
      return;
    }
    const published = await publishAction.execute(reason.trim());
    if (!published) {
      setErrors([publishAction.error ?? "Could not publish."]);
      return;
    }
    setOpen(false); currentApi.refetch();
    onToast("Credit thresholds published.");
  }

  return (
    <Card padding={16}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Credit thresholds</p>
        <Btn variant="ghost" size="sm" icon={<Sparkles size={14} />} onClick={startEdit}>Edit</Btn>
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
        When a provider is warned, and the balance below which they stop receiving new
        bookings. Work already booked always finishes — the floor stops the hole being dug
        deeper, it never strands a customer who has already booked.
      </p>
      {currentApi.loading ? <Skeleton height={54} /> : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, fontSize: 12 }}>
          <KV label="Warn below" value={current ? money(current.credit_warning_threshold) : "—"} />
          <KV label="Stop new bookings below" value={current ? money(current.credit_booking_floor) : "—"} />
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Edit credit thresholds" size="sm">
        <label style={{ fontSize: 12, fontWeight: 600 }}>Warn below (₹)</label>
        <Input value={warn} onChange={setWarn} placeholder="e.g. 300" />
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginTop: 10 }}>
          Stop new bookings below (₹)
        </label>
        <Input value={floor} onChange={setFloor} placeholder="e.g. 100" />
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
          The warning must be at or above the floor — a warning below it would only fire
          after bookings had already stopped.
        </p>
        {errors.map(e => <p key={e} style={{ fontSize: 11, color: "var(--danger-text)", margin: "6px 0 0" }}>{e}</p>)}
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginTop: 12 }}>
          Publish reason (required)
        </label>
        <Input value={reason} onChange={setReason} />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
          <Btn variant="ghost" onClick={() => setOpen(false)}>Cancel</Btn>
          <Btn variant="primary" disabled={!reason.trim() || !warn.trim() || !floor.trim()}
            loading={saveDraftAction.loading || publishAction.loading}
            onClick={saveAndPublish}>Publish</Btn>
        </div>
      </Modal>
    </Card>
  );
}

// ── Top-up Plans ────────────────────────────────────────────────────────────
// Lives under Credits & Top-ups > "Top-up Plans" sub-tab.
//
// The "Provider Activation Requirement" card that used to sit above this was
// removed: activation no longer blocks on buying anything, so a one-time
// starter purchase an admin could configure no longer had a job. A provider is
// offered a top-up plan during onboarding and from their header, and that plan
// is the only thing sold. The finance policy row still carries the credit
// FLOOR and warning threshold, which are what actually protect the platform.

function TopupPackagesPanel() {
  const { toasts, push, remove } = useToasts();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Toaster toasts={toasts} onRemove={remove} />
      <CreditThresholdsSection onToast={push} />
      <TopupPackagesSection onToast={push} />
    </div>
  );
}

// ── Top-up Plans (multiple named, purchasable price tiers) ─────────────────
// Backed by the CANONICAL catalogue (`hs_topup_plans`, migration 317/319) --
// the same one /admin/topup-plans edits, the provider onboarding offer reads,
// and the tenant header credit pill shows.
//
// This panel used to manage `credit_packages` (platform_commerce,
// /v1/commerce/packages) instead: a second, parallel catalogue that had 0 rows
// and no GST or seat fields, so a plan authored here priced nothing a provider
// could actually buy and the create form had nowhere to put tax. Two price
// authorities for one purchase is exactly the split this codebase has been
// removing, so the tab now points at the real one.
const EMPTY_PKG_FORM = {
  name: "", description: "", base_amount: "1000", gst_percent: "18",
  seats: "1", validity_days: "0",
};

function TopupPackagesSection({ onToast }: { onToast: (msg: string, variant?: ToastItem["variant"]) => void }) {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_PKG_FORM);

  const pkgsApi = useApi(useCallback(() => topupPlanApi.list(), []), []);
  const createAction = useAction((body: Record<string, unknown>) => topupPlanApi.create(body as unknown as TopupPlanInput));
  const updateAction = useAction((id: string, body: Record<string, unknown>) => topupPlanApi.update(id, body as Partial<TopupPlanInput>));
  const archiveAction = useAction((id: string) => topupPlanApi.update(id, { is_active: false }));
  const deleteAction = useAction((id: string) => topupPlanApi.remove(id));

  const packages = pkgsApi.data?.plans ?? [];

  function startCreate() {
    setEditingId(null);
    setForm(EMPTY_PKG_FORM);
    setShowForm(true);
  }
  function startEdit(pkg: TopupPlanCatalogItem) {
    setEditingId(pkg.id);
    setForm({
      name: pkg.name, description: pkg.description ?? "",
      base_amount: String(pkg.base_amount), gst_percent: String(pkg.gst_percent),
      seats: String(pkg.seats), validity_days: String(pkg.validity_days ?? 0),
    });
    setShowForm(true);
  }

  // Priced exactly the way the server prices it, so the admin sees the real
  // total before saving rather than after.
  const previewBase = Number(form.base_amount) || 0;
  const previewGstPct = Number(form.gst_percent) || 0;
  const previewGst = Math.round(previewBase * previewGstPct) / 100;
  const previewTotal = previewBase + previewGst;

  async function submit() {
    if (!form.name.trim() || !form.base_amount.trim()) return;
    const body = {
      name: form.name.trim(), description: form.description.trim() || undefined,
      base_amount: Number(form.base_amount), gst_percent: Number(form.gst_percent) || 0,
      seats: Number(form.seats) || 0, validity_days: Number(form.validity_days) || 0,
    };
    const result = editingId ? await updateAction.execute(editingId, body) : await createAction.execute(body);
    if (result) {
      setShowForm(false); setEditingId(null); pkgsApi.refetch();
      onToast(editingId ? "Plan updated." : "Plan created.");
    } else {
      onToast((editingId ? updateAction.error : createAction.error) ?? "Failed to save plan.", "danger");
    }
  }

  async function archive(pkg: TopupPlanCatalogItem) {
    if (!confirm(`Retire plan "${pkg.name}"? Tenants will no longer be able to buy it.`)) return;
    const result = await archiveAction.execute(pkg.id);
    if (result === null) onToast(archiveAction.error ?? "Failed to retire plan.", "danger");
    else { pkgsApi.refetch(); onToast("Plan retired."); }
  }

  async function deletePermanently(pkg: TopupPlanCatalogItem) {
    if (!confirm(`Permanently delete plan "${pkg.name}"? This cannot be undone.`)) return;
    const result = await deleteAction.execute(pkg.id);
    // The API refuses to delete a plan any payment order references; it must be
    // retired instead, so the tenant's receipt keeps resolving to a real plan.
    if (result === null) onToast(deleteAction.error ?? "Failed to delete plan.", "danger");
    else { pkgsApi.refetch(); onToast("Plan deleted."); }
  }

  const activePkgs = packages.filter(p => p.is_active);
  const archivedPkgs = packages.filter(p => !p.is_active);

  const validityText = (p: TopupPlanCatalogItem) =>
    p.validity_days > 0 ? `Valid ${p.validity_days} days` : "Never expires";

  return (
    <Card padding={16}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Top-up Plans</p>
        <Btn variant="primary" icon={<Plus size={14} />} onClick={startCreate}>Create Plan</Btn>
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 14px" }}>
        What a provider buys to operate: wallet credit plus the technician seats that decide how many
        jobs they can run in one slot. Offered during onboarding and from the provider&apos;s header —
        never required to activate. Edited here or at <code>/admin/topup-plans</code>; both are the same catalogue.
      </p>

      {pkgsApi.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
          {[0, 1, 2].map(i => <Skeleton key={i} height={130} />)}
        </div>
      ) : packages.length === 0 ? (
        <div style={{ padding: "28px 0", textAlign: "center" }}>
          <Wallet size={28} style={{ color: "var(--text-tertiary)", margin: "0 auto 10px", display: "block" }} />
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 4px" }}>No top-up plans created yet.</p>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Click &quot;Create Plan&quot; to add your first one — providers can&apos;t buy credit or seats until at least one plan exists.</p>
        </div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
            {activePkgs.map(pkg => (
              <div key={pkg.id} style={{
                display: "flex", flexDirection: "column", gap: 8, padding: 16, borderRadius: 12,
                border: "1px solid var(--border)", background: "var(--surface-elevated, var(--surface))",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{pkg.name}</span>
                  {pkg.is_default && <Badge variant="success">Default</Badge>}
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--brand)" }}>{money(pkg.total_amount)}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {money(pkg.base_amount)} + {pkg.gst_percent}% GST
                  <span style={{ color: "var(--text-tertiary)" }}> ({money(pkg.credited_amount)} to wallet)</span>
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <Badge>{pkg.seats} seat{pkg.seats === 1 ? "" : "s"}</Badge>
                  <Badge variant={pkg.validity_days > 0 ? "warning" : undefined}>{validityText(pkg)}</Badge>
                </div>
                {pkg.description && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{pkg.description}</p>}
                <div style={{ display: "flex", gap: 6, marginTop: "auto", paddingTop: 10, borderTop: "1px solid var(--border)" }}>
                  <Btn variant="ghost" size="sm" onClick={() => startEdit(pkg)} style={{ flex: 1, justifyContent: "center" }}>Edit</Btn>
                  <Btn variant="ghost" size="sm" onClick={() => archive(pkg)} style={{ flex: 1, justifyContent: "center", color: "var(--danger-text)" }}>Retire</Btn>
                </div>
              </div>
            ))}
          </div>

          {archivedPkgs.length > 0 && (
            <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
              <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.03em", color: "var(--text-tertiary)", margin: "0 0 8px" }}>
                Retired
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {archivedPkgs.map(pkg => (
                  <div key={pkg.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "8px 12px", borderRadius: 8, background: "var(--surface-sunken)", opacity: 0.7 }}>
                    <span style={{ fontSize: 12 }}>{pkg.name} — {money(pkg.total_amount)} for {pkg.seats} seat{pkg.seats === 1 ? "" : "s"}</span>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <Badge>Retired</Badge>
                      <Btn variant="ghost" size="sm" onClick={() => deletePermanently(pkg)} style={{ color: "var(--danger-text)" }}>Delete</Btn>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <Modal open={showForm} onClose={() => setShowForm(false)} title={editingId ? "Edit Plan" : "Create Plan"} size="sm">
        <label style={{ fontSize: 12, fontWeight: 600 }}>Plan name</label>
        <Input value={form.name} onChange={v => setForm({ ...form, name: v })} placeholder="e.g. Starter, Growth, Monthly" />
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginTop: 10 }}>Description (optional)</label>
        <Input value={form.description} onChange={v => setForm({ ...form, description: v })} />
        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Price before GST (₹)</label>
            <Input value={form.base_amount} onChange={v => setForm({ ...form, base_amount: v })} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>GST %</label>
            <Input value={form.gst_percent} onChange={v => setForm({ ...form, gst_percent: v })} placeholder="18" />
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Technician seats</label>
            <Input value={form.seats} onChange={v => setForm({ ...form, seats: v })} placeholder="1" />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Validity (days)</label>
            <Input value={form.validity_days} onChange={v => setForm({ ...form, validity_days: v })} placeholder="0" />
          </div>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
          {Number(form.validity_days) > 0
            ? `Seats and unspent credit lapse ${form.validity_days} days after purchase.`
            : "0 = the purchase never lapses. Seats and credit stay until used."}
        </p>

        <div style={{ marginTop: 12, padding: 10, borderRadius: 8, background: "var(--surface-sunken)" }}>
          <PreviewRow label="Price before GST" value={money(previewBase)} />
          <PreviewRow label={`GST @ ${previewGstPct}%`} value={money(previewGst)} />
          <PreviewRow label="Provider pays" value={money(previewTotal)} strong />
          {/* GST is tax, never spendable balance -- the same split the capture
              path enforces, shown here so the number is never a surprise. */}
          <PreviewRow label="Reaches wallet" value={money(previewBase)} />
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
          <Btn variant="ghost" onClick={() => setShowForm(false)}>Cancel</Btn>
          <Btn variant="primary" loading={createAction.loading || updateAction.loading}
            disabled={!form.name.trim() || !form.base_amount.trim()}
            onClick={submit}>
            {editingId ? "Save Changes" : "Create Plan"}
          </Btn>
        </div>
      </Modal>
    </Card>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2 }}>{label}</div>
      <div style={{ fontWeight: 500 }}>{value}</div>
    </div>
  );
}
function PreviewRow({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ fontWeight: strong ? 700 : 500 }}>{value}</span>
    </div>
  );
}

// ── Provider Charges ─────────────────────────────────────────────────────────

function ProviderChargesTab() {
  const [q, setQ] = useState("");
  const query = useDebouncedValue(q);
  const [chargeModel, setChargeModel] = useState<string | undefined>(undefined);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const charges = useApi(useCallback(
    () => homeServicesFinanceApi.listProviderCharges({ q: query || undefined, chargeModel, status: status || undefined, page, pageSize: 20 }),
    [query, chargeModel, status, page]), [query, chargeModel, status, page]);
  const usageStatusOptions = [{ value: "posted", label: "Posted usage credits" }];
  const legacyStatusOptions = [
    { value: "pending", label: "Legacy commission pending" },
    { value: "calculated", label: "Legacy commission calculated" },
    { value: "deducted", label: "Legacy commission deducted" },
    { value: "insufficient_credit", label: "Insufficient legacy wallet credit" },
    { value: "failed", label: "Legacy commission failed" },
    { value: "reversed", label: "Legacy commission reversed" },
    { value: "not_required", label: "Not required" },
  ];
  const statusOptions = chargeModel === "usage_credit" ? usageStatusOptions
    : chargeModel === "commission" ? legacyStatusOptions : [...usageStatusOptions, ...legacyStatusOptions];

  function chooseModel(model: string | undefined) {
    setChargeModel(model);
    setStatus("");
    setPage(1);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding={14} style={{ borderColor: "var(--border-strong, var(--border))" }}>
        <div style={{ fontSize: 13, fontWeight: 700 }}>One live Home Services charge ledger</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
          New provider charges are posted only to the usage-credit ledger at job completion. Legacy invoice-commission
          records remain searchable for audit, but the invoice path can no longer debit Home Services providers again.
        </div>
      </Card>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div style={{ flex: 1, maxWidth: 320 }}><Input placeholder="Search tenant or job..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
        <Select value={status} onChange={v => { setStatus(v); setPage(1); }} placeholder="All statuses" options={statusOptions} />
        <Btn variant={chargeModel === undefined ? "primary" : "ghost"} onClick={() => chooseModel(undefined)}>All records</Btn>
        <Btn variant={chargeModel === "usage_credit" ? "primary" : "ghost"} onClick={() => chooseModel("usage_credit")}>Usage Credit</Btn>
        <Btn variant={chargeModel === "commission" ? "primary" : "ghost"} onClick={() => chooseModel("commission")}>Legacy Invoice Commission</Btn>
      </div>
      <QueryError message={charges.error} onRetry={charges.refetch} />
      <DataTable
        loading={charges.loading}
        rows={(charges.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No provider charges found for this filter."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).charge_ref))}
        columns={[
          { key: "charge_ref", label: "Charge Ref", render: v => <span style={{ fontFamily: "monospace", fontSize: 12 }}>{String(v).split(":")[1]?.slice(0, 8)}</span> },
          { key: "charge_model", label: "Record source", render: v => <Badge variant={v === "commission" ? "info" : "default"}>{v === "commission" ? "legacy invoice commission" : "usage-credit ledger"}</Badge> },
          { key: "tenant_name", label: "Tenant" },
          { key: "job_id", label: "Job", render: v => v ? String(v).slice(0, 8) : "—" },
          { key: "amount", label: "Charge", render: (v, row) => (row as Record<string, unknown>).charge_model === "commission" ? money(v as string) : units(v as string) },
          { key: "status", label: "Status", render: v => <Badge variant={v === "posted" || v === "deducted" ? "success" : v === "failed" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "triggered_at", label: "Triggered", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={charges.data?.total ?? 0} pageSize={20} onPage={setPage} alwaysShow />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Provider Charge Detail" size="lg">
        {selected && <ProviderChargeDetail chargeRef={selected} />}
      </Modal>

    </div>
  );
}
function ProviderChargeDetail({ chargeRef }: { chargeRef: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getProviderChargeDetail(chargeRef), [chargeRef]), [chargeRef]);
  if (detail.loading) return <Skeleton height={120} />;
  return <KeyValueGrid data={detail.data} />;
}

// ── Credits & Top-ups ────────────────────────────────────────────────────────
// Single Home Services workspace for provider Usage Credits (Credit Account /
// Credit Balance / Available / Reserved / Consumed) and Credit Top-up Orders.
// "Provider Wallet" no longer exists as a distinct concept here -- the
// canonical balance is tenant_billing.credit_balance (usage_credit_ledger).
// Credit units are platform usage units, never displayed with a ₹ symbol;
// only actual top-up payment amounts (a provider's rupee payment to
// Fuvay to purchase credits) use money().

function units(v: unknown): string {
  const n = Number(v ?? 0);
  return `${n.toLocaleString("en-IN")} credits`;
}

function ledgerEventLabel(v: unknown): string {
  return String(v ?? "")
    .split("_")
    .filter(Boolean)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

const CREDIT_SUBTABS = ["accounts", "topups", "packages", "ledger", "adjustments"] as const;
type CreditSubTab = typeof CREDIT_SUBTABS[number];

function CreditsTab({ params }: { params: ReturnType<typeof useSearchParams> }) {
  const router = useRouter();
  const requestedSubTab = params.get("credits_tab") as CreditSubTab | null;
  const subTab: CreditSubTab = requestedSubTab && CREDIT_SUBTABS.includes(requestedSubTab)
    ? requestedSubTab
    : "accounts";
  const tenantId = params.get("tenant_id") || undefined;
  const jobId = params.get("job_id") || undefined;
  const [selectedTopup, setSelectedTopup] = useState<string | null>(null);
  const [selectedLedgerEntry, setSelectedLedgerEntry] = useState<string | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<Record<string, unknown> | null>(null);

  const summary = useApi(useCallback(() => homeServicesFinanceApi.getCreditsSummary(), []));
  const totals = (summary.data ?? {}) as Record<string, unknown>;

  const setSubTab = useCallback((nextTab: CreditSubTab) => {
    const next = new URLSearchParams(params.toString());
    next.set("tab", "credits");
    next.set("credits_tab", nextTab);
    // A job is a ledger-only scope. Do not carry an invisible job filter
    // into another operational view.
    if (nextTab !== "ledger") next.delete("job_id");
    router.replace(`/admin/home-services/finance?${next.toString()}`, { scroll: false });
  }, [params, router]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Credit units are not a cash wallet.</p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <SummaryCard label="Providers" value={Number(totals.providers ?? 0)} />
        <SummaryCard label="Low-Balance Providers" value={Number(totals.low_balance_providers ?? 0)} tone={Number(totals.low_balance_providers ?? 0) > 0 ? "warning" : undefined} onClick={() => setSubTab("accounts")} />
        <SummaryCard label="Credits Purchased" value={units(totals.credits_purchased)} onClick={() => setSubTab("topups")} />
        <SummaryCard label="Pending Top-ups" value={Number(totals.pending_topups ?? 0)} tone={Number(totals.pending_topups ?? 0) > 0 ? "warning" : undefined} onClick={() => setSubTab("topups")} />
        <SummaryCard label="Failed Top-ups" value={Number(totals.failed_topups ?? 0)} tone={Number(totals.failed_topups ?? 0) > 0 ? "danger" : undefined} onClick={() => setSubTab("topups")} />
      </div>

      <div className="hs-finance-credit-tabs" role="tablist" aria-label="Credits and top-ups sections">
        {([
          ["accounts", "Credit Accounts"], ["topups", "Top-up Orders"], ["packages", "Top-up Plans"],
          ["ledger", "Credit Ledger"], ["adjustments", "Adjustments"],
        ] as [CreditSubTab, string][]).map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={subTab === key}
            onClick={() => setSubTab(key)}
            style={{ padding: "8px 12px", fontSize: 12, fontWeight: 600, background: "none", border: "none",
              borderBottom: subTab === key ? "2px solid var(--brand)" : "2px solid transparent",
              color: subTab === key ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer" }}>
            {label}
          </button>
        ))}
      </div>

      {subTab === "accounts" && <CreditAccountsView onSelect={setSelectedAccount} />}
      {subTab === "topups" && <TopupOrdersView onSelect={setSelectedTopup} />}
      {subTab === "packages" && <TopupPackagesPanel />}
      {subTab === "ledger" && <CreditLedgerView onSelect={setSelectedLedgerEntry} tenantId={tenantId} jobId={jobId} />}
      {subTab === "adjustments" && <AdjustmentsView onCreated={() => summary.refetch()} />}

      <Modal open={!!selectedTopup} onClose={() => setSelectedTopup(null)} title="Top-up Order Detail" size="lg">
        {selectedTopup && <TopupDetail topupId={selectedTopup} onChanged={() => summary.refetch()} />}
      </Modal>
      <Modal open={!!selectedLedgerEntry} onClose={() => setSelectedLedgerEntry(null)} title="Ledger Entry Detail" size="lg">
        {selectedLedgerEntry && <LedgerEntryDetail entryId={selectedLedgerEntry} />}
      </Modal>
      <Modal open={!!selectedAccount} onClose={() => setSelectedAccount(null)} title="Credit Account Detail" size="lg">
        {selectedAccount && <CreditAccountDetail account={selectedAccount} />}
      </Modal>
    </div>
  );
}

// ── Credit Accounts ──────────────────────────────────────────────────────────

function creditAccountStatus(a: Record<string, unknown>): { label: string; variant: "success" | "warning" | "danger" | "muted" } {
  if (a.low_balance) return { label: "LOW_BALANCE", variant: "warning" };
  if (Number(a.credit_balance ?? 0) <= 0) return { label: "INSUFFICIENT", variant: "danger" };
  return { label: "ACTIVE", variant: "success" };
}

function CreditAccountsView({ onSelect }: { onSelect: (a: Record<string, unknown>) => void }) {
  const [q, setQ] = useState("");
  const query = useDebouncedValue(q);
  const [lowOnly, setLowOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const accounts = useApi(useCallback(
    () => homeServicesFinanceApi.listCreditAccounts({ q: query || undefined, lowBalanceOnly: lowOnly, page, pageSize }),
    [query, lowOnly, page, pageSize]), [query, lowOnly, page, pageSize]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="hs-finance-filterbar">
        <div style={{ flex: "1 1 300px", minWidth: 260 }}><Input label="Search" placeholder="Provider or account ID..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
        <div style={{ minWidth: 125 }}><Select label="Rows" value={String(pageSize)} onChange={v => { setPageSize(Number(v)); setPage(1); }} options={[
          { value: "25", label: "25 rows" }, { value: "50", label: "50 rows" }, { value: "100", label: "100 rows" },
        ]} /></div>
        <div style={{ alignSelf: "flex-end" }}><Btn variant={lowOnly ? "primary" : "ghost"} onClick={() => { setLowOnly(v => !v); setPage(1); }}>Low balance only</Btn></div>
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Scoped to Home Services. Business Vertical is fixed and cannot be changed here.</p>
      <QueryError message={accounts.error} onRetry={accounts.refetch} />
      <DataTable
        loading={accounts.loading}
        rows={(accounts.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No Home Services credit accounts found."
        onRowClick={row => onSelect(row as Record<string, unknown>)}
        columns={[
          { key: "tenant_name", label: "Provider" },
          { key: "credit_balance", label: "Available Credits", render: v => units(v) },
          { key: "low_balance_threshold", label: "Low-Balance Threshold", render: v => units(v) },
          { key: "low_balance", label: "Credit Status", render: (_v, row) => {
            const s = creditAccountStatus(row as Record<string, unknown>);
            return <Badge variant={s.variant}>{s.label}</Badge>;
          } },
        ]}
      />
      <Pagination page={page} total={accounts.data?.total ?? 0} pageSize={pageSize} onPage={setPage} alwaysShow />
    </div>
  );
}

function CreditAccountDetail({ account }: { account: Record<string, unknown> }) {
  const ledger = useApi(useCallback(
    () => homeServicesFinanceApi.listCreditLedger({ tenantId: String(account.tenant_id), pageSize: 20 }),
    [account.tenant_id]), [account.tenant_id]);
  const s = creditAccountStatus(account);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <SummaryCard label="Available Credits" value={units(account.credit_balance)} />
        <SummaryCard label="Low-Balance Threshold" value={units(account.low_balance_threshold)} />
        <SummaryCard label="Credit Status" value={s.label} tone={s.variant === "danger" || s.variant === "warning" ? s.variant : undefined} />
      </div>
      <div>
        <h4 style={{ fontSize: 12, fontWeight: 700, margin: "0 0 8px", textTransform: "uppercase", color: "var(--text-tertiary)" }}>Recent ledger activity</h4>
        <DataTable
          loading={ledger.loading}
          rows={(ledger.data?.items ?? []) as unknown as Record<string, unknown>[]}
          emptyText="No ledger entries yet for this provider."
          columns={[
            { key: "created_at", label: "Time", render: v => dt(v as string) },
            { key: "event_type", label: "Entry Type", render: v => <span style={{ fontFamily: "monospace", fontSize: 11 }}>{String(v).toUpperCase()}</span> },
            { key: "credit_delta", label: "Credits", render: v => (Number(v) >= 0 ? "+" : "") + units(v) },
            { key: "balance_after", label: "Balance After", render: v => units(v) },
          ]}
        />
      </div>
    </div>
  );
}

// ── Top-up Orders ─────────────────────────────────────────────────────────────

function TopupOrdersView({ onSelect }: { onSelect: (id: string) => void }) {
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [q, setQ] = useState("");
  const query = useDebouncedValue(q);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const topups = useApi(useCallback(() => homeServicesFinanceApi.listTopups({
    q: query || undefined, paymentStatus: status,
    dateFrom: dateFrom || undefined, dateTo: dateTo || undefined,
    page, pageSize,
  }), [query, status, dateFrom, dateTo, page, pageSize]), [query, status, dateFrom, dateTo, page, pageSize]);
  const hasFilters = Boolean(q || status || dateFrom || dateTo);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="hs-finance-filterbar">
        <div style={{ minWidth: 260, flex: "1 1 300px" }}><Input label="Search" placeholder="Order, provider or gateway reference..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
        <div style={{ minWidth: 190 }}><Select label="Payment status" value={status ?? ""} onChange={v => { setStatus(v || undefined); setPage(1); }} options={[
          { value: "", label: "All statuses" },
          { value: "initiated", label: "Initiated" },
          { value: "paid_pending_credit", label: "Paid, credit pending" },
          { value: "credited", label: "Credited" },
          { value: "failed", label: "Failed" },
          { value: "cancelled", label: "Cancelled" },
          { value: "refunded", label: "Refunded" },
          { value: "partially_refunded", label: "Partially refunded" },
        ]} /></div>
        <div style={{ minWidth: 155 }}><Input label="From" type="date" value={dateFrom} onChange={v => { setDateFrom(v); setPage(1); }} /></div>
        <div style={{ minWidth: 155 }}><Input label="To" type="date" value={dateTo} onChange={v => { setDateTo(v); setPage(1); }} /></div>
        <div style={{ minWidth: 125 }}><Select label="Rows" value={String(pageSize)} onChange={v => { setPageSize(Number(v)); setPage(1); }} options={[
          { value: "25", label: "25 rows" }, { value: "50", label: "50 rows" }, { value: "100", label: "100 rows" },
        ]} /></div>
        {hasFilters && <div style={{ alignSelf: "flex-end" }}><Btn variant="ghost" onClick={() => { setQ(""); setStatus(undefined); setDateFrom(""); setDateTo(""); setPage(1); }}>Clear filters</Btn></div>}
      </div>
      <QueryError message={topups.error} onRetry={topups.refetch} />
      <DataTable
        loading={topups.loading}
        rows={(topups.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No Home Services top-up orders found."
        onRowClick={row => onSelect(String((row as Record<string, unknown>).topup_id ?? (row as Record<string, unknown>).id))}
        columns={[
          { key: "order_ref", label: "Top-up Order" },
          { key: "tenant_name", label: "Provider" },
          { key: "credits_purchased", label: "Units", render: v => units(v) },
          { key: "amount_paid", label: "Payment Amount", render: v => money(v as string) },
          { key: "payment_method", label: "Payment Method" },
          { key: "gateway_payment_id", label: "Gateway Reference", render: v => v ? <span style={{ fontFamily: "monospace", fontSize: 11 }}>{String(v).slice(0, 14)}</span> : "—" },
          { key: "payment_status", label: "Payment Status", render: v => <Badge variant={v === "credited" ? "success" : v === "failed" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "created_at", label: "Created", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={topups.data?.total ?? 0} pageSize={pageSize} onPage={setPage} alwaysShow />
    </div>
  );
}
function TopupDetail({ topupId, onChanged }: { topupId: string; onChanged: () => void }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getTopupDetail(topupId), [topupId]), [topupId]);
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [showRefund, setShowRefund] = useState(false);
  const retryAction = useAction((id: string) => homeServicesFinanceApi.retryTopupCredit(id));
  const refundAction = useAction((id: string, amount: number, reason: string) => homeServicesFinanceApi.refundTopup(id, amount, reason));

  if (detail.loading) return <Skeleton height={120} />;
  const d = detail.data as Record<string, unknown> | undefined;
  const topup = (d?.topup ?? d) as Record<string, unknown> | undefined;
  const status = topup?.payment_status as string | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <KeyValueGrid data={detail.data} />
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        A top-up is a provider payment to Fuvay to purchase platform Usage Credits -- distinct from a customer
        paying the provider for a service job.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {(status === "paid_pending_credit" || status === "failed") && (
          <Btn variant="secondary" loading={retryAction.loading}
            onClick={async () => { if (await retryAction.execute(topupId)) { detail.refetch(); onChanged(); } }}>
            Retry Credit Posting
          </Btn>
        )}
        {(status === "credited" || status === "partially_refunded") && (
          <Btn variant="ghost" onClick={() => setShowRefund(v => !v)}>Refund</Btn>
        )}
      </div>
      {showRefund && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, background: "var(--surface-sunken)", borderRadius: 8 }}>
          <Input placeholder="Amount" value={refundAmount} onChange={setRefundAmount} />
          <Input placeholder="Reason" value={refundReason} onChange={setRefundReason} />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="primary" loading={refundAction.loading}
              disabled={!Number.isFinite(Number(refundAmount)) || Number(refundAmount) <= 0 || !refundReason.trim()}
              onClick={async () => {
                if (await refundAction.execute(topupId, Number(refundAmount), refundReason)) {
                  setShowRefund(false); setRefundAmount(""); setRefundReason(""); detail.refetch(); onChanged();
                }
              }}>Confirm Refund</Btn>
            <Btn variant="ghost" onClick={() => setShowRefund(false)}>Cancel</Btn>
          </div>
          {refundAction.error && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: 0 }}>{refundAction.error}</p>}
        </div>
      )}
      {retryAction.error && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: 0 }}>{retryAction.error}</p>}
    </div>
  );
}

// ── Credit Ledger (immutable) ────────────────────────────────────────────────

const LEDGER_EVENT_TYPES = [
  "completed_job_deduction", "customer_platform_charge_recovery", "manual_credit_adjustment",
  "topup_credit_granted", "topup_credit_refunded",
];

function CreditLedgerView({ onSelect, tenantId, jobId }: {
  onSelect: (id: string) => void;
  tenantId?: string;
  jobId?: string;
}) {
  const [q, setQ] = useState("");
  const query = useDebouncedValue(q);
  const [eventType, setEventType] = useState<string | undefined>(undefined);
  const [direction, setDirection] = useState<string | undefined>(undefined);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const ledger = useApi(useCallback(() => homeServicesFinanceApi.listCreditLedger({
    tenantId, jobId, q: query || undefined, eventType, direction,
    dateFrom: dateFrom || undefined, dateTo: dateTo || undefined,
    page, pageSize,
  }), [tenantId, jobId, query, eventType, direction, dateFrom, dateTo, page, pageSize]),
    [tenantId, jobId, query, eventType, direction, dateFrom, dateTo, page, pageSize]);
  const hasFilters = Boolean(q || eventType || direction || dateFrom || dateTo);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="hs-finance-filterbar">
        <div style={{ minWidth: 260, flex: "1 1 300px" }}><Input label="Search" placeholder="Provider, entry, job or request reference..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
        <div style={{ minWidth: 220 }}><Select label="Entry type" value={eventType ?? ""} onChange={v => { setEventType(v || undefined); setPage(1); }} options={[
          { value: "", label: "All entry types" },
          ...LEDGER_EVENT_TYPES.map(value => ({ value, label: ledgerEventLabel(value) })),
        ]} /></div>
        <div style={{ minWidth: 140 }}><Select label="Direction" value={direction ?? ""} onChange={v => { setDirection(v || undefined); setPage(1); }} options={[
          { value: "", label: "All directions" }, { value: "credit", label: "Credit" }, { value: "debit", label: "Debit" },
        ]} /></div>
        <div style={{ minWidth: 155 }}><Input label="From" type="date" value={dateFrom} onChange={v => { setDateFrom(v); setPage(1); }} /></div>
        <div style={{ minWidth: 155 }}><Input label="To" type="date" value={dateTo} onChange={v => { setDateTo(v); setPage(1); }} /></div>
        <div style={{ minWidth: 125 }}><Select label="Rows" value={String(pageSize)} onChange={v => { setPageSize(Number(v)); setPage(1); }} options={[
          { value: "30", label: "30 rows" }, { value: "50", label: "50 rows" }, { value: "100", label: "100 rows" },
        ]} /></div>
        {hasFilters && <div style={{ alignSelf: "flex-end" }}><Btn variant="ghost" onClick={() => { setQ(""); setEventType(undefined); setDirection(undefined); setDateFrom(""); setDateTo(""); setPage(1); }}>Clear filters</Btn></div>}
      </div>
      {(tenantId || jobId) && (
        <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0 }}>
          Showing exact ledger activity{tenantId ? ` for provider ${tenantId}` : ""}{jobId ? ` and job ${jobId}` : ""}.
        </p>
      )}
      <QueryError message={ledger.error} onRetry={ledger.refetch} />
      <DataTable
        loading={ledger.loading}
        rows={(ledger.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No ledger entries found for this filter."
        onRowClick={row => onSelect(String((row as Record<string, unknown>).ledger_id))}
        columns={[
          { key: "created_at", label: "Timestamp", render: v => dt(v as string) },
          { key: "ledger_id", label: "Entry ID", render: v => <span style={{ fontFamily: "monospace", fontSize: 11 }}>{String(v).slice(0, 8)}</span> },
          { key: "event_type", label: "Entry Type", render: v => <span style={{ fontSize: 11 }}>{ledgerEventLabel(v)}</span> },
          { key: "tenant_name", label: "Provider" },
          { key: "direction", label: "Direction", render: v => <Badge variant={v === "credit" ? "success" : "default"}>{String(v)}</Badge> },
          { key: "credit_delta", label: "Credit Units", render: v => (Number(v) >= 0 ? "+" : "") + units(v) },
          { key: "balance_after", label: "Balance After", render: v => units(v) },
          { key: "deduction_source", label: "Source", render: (v, row) => v ? String(v) : String((row as Record<string, unknown>).source_type ?? "—") },
        ]}
      />
      <Pagination page={page} total={ledger.data?.total ?? 0} pageSize={pageSize} onPage={setPage} alwaysShow />
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        The ledger is append-only. No code path exists to edit or delete a posted entry.
      </p>
    </div>
  );
}
function LedgerEntryDetail({ entryId }: { entryId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getLedgerEntryDetail(entryId), [entryId]), [entryId]);
  if (detail.loading) return <Skeleton height={140} />;
  return <KeyValueGrid data={detail.data} />;
}

// ── Adjustments ───────────────────────────────────────────────────────────────

const ADJUSTMENT_REASONS = [
  "PAYMENT_RECONCILIATION", "DUPLICATE_DEDUCTION_REVERSAL", "SERVICE_CREDIT_CORRECTION",
  "MIGRATION_CORRECTION", "EXPIRED_CREDIT_CORRECTION", "APPROVED_GOODWILL_ADJUSTMENT", "OTHER_REQUIRES_REVIEW",
];

function AdjustmentsView({ onCreated }: { onCreated: () => void }) {
  const [tenantId, setTenantId] = useState("");
  const [providerSearch, setProviderSearch] = useState("");
  const providerQuery = useDebouncedValue(providerSearch);
  const [direction, setDirection] = useState<"credit" | "debit">("credit");
  const [creditUnits, setCreditUnits] = useState("");
  const [reasonCode, setReasonCode] = useState(ADJUSTMENT_REASONS[0]);
  const [detailedReason, setDetailedReason] = useState("");
  const [supportingReference, setSupportingReference] = useState("");
  const [ledgerPage, setLedgerPage] = useState(1);
  const action = useAction((body: Parameters<typeof homeServicesFinanceApi.createAdjustment>[0]) =>
    homeServicesFinanceApi.createAdjustment(body));
  const providerResults = useApi(useCallback(() => homeServicesFinanceApi.listCreditAccounts({
    q: providerQuery || undefined, page: 1, pageSize: 8,
  }), [providerQuery]), [providerQuery]);
  const ledger = useApi(useCallback(() => homeServicesFinanceApi.listCreditLedger({
    eventType: "manual_credit_adjustment", page: ledgerPage, pageSize: 25,
  }), [ledgerPage]), [ledgerPage]);

  async function submit() {
    if (!tenantId.trim() || !creditUnits.trim() || !detailedReason.trim()) return;
    const r = await action.execute({
      tenantId: tenantId.trim(), direction, creditUnits, reasonCode, detailedReason,
      supportingReference: supportingReference.trim() || undefined,
    });
    if (r) {
      setTenantId(""); setProviderSearch(""); setCreditUnits(""); setDetailedReason("");
      setSupportingReference(""); setLedgerPage(1); ledger.refetch(); onCreated();
    }
  }

  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <Card style={{ padding: 16, flex: "1 1 320px" }}>
        <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>New manual adjustment</p>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
          Requires elevated permission. Creates an immutable ledger entry -- the balance is never edited directly.
        </p>
        <div style={{ position: "relative" }}>
          <Input label="Provider" placeholder="Search provider name or account ID..." value={providerSearch}
            onChange={v => { setProviderSearch(v); setTenantId(""); }} />
          {!!providerSearch.trim() && !tenantId && (
            <div style={{ position: "absolute", zIndex: 5, top: "100%", left: 0, right: 0, marginTop: 4,
              maxHeight: 220, overflowY: "auto", border: "1px solid var(--border)", borderRadius: 8,
              background: "var(--surface)", boxShadow: "var(--shadow-md)" }}>
              {providerResults.loading && <div style={{ padding: 10, fontSize: 12 }}>Searching…</div>}
              {providerResults.error && <div style={{ padding: 10, fontSize: 12, color: "var(--danger-text)" }}>{providerResults.error}</div>}
              {!providerResults.loading && !providerResults.error && (providerResults.data?.items ?? []).map((provider: Record<string, unknown>) => (
                <button key={String(provider.tenant_id)} type="button"
                  onClick={() => { setTenantId(String(provider.tenant_id)); setProviderSearch(String(provider.tenant_name ?? provider.tenant_id)); }}
                  style={{ display: "flex", width: "100%", justifyContent: "space-between", gap: 10, padding: "9px 10px",
                    border: 0, borderBottom: "1px solid var(--border-subtle)", background: "transparent",
                    color: "var(--text-primary)", cursor: "pointer", textAlign: "left" }}>
                  <span>{String(provider.tenant_name ?? "Unnamed provider")}</span>
                  <span style={{ color: "var(--text-tertiary)", fontFamily: "monospace", fontSize: 11 }}>{String(provider.tenant_id).slice(0, 8)}</span>
                </button>
              ))}
              {!providerResults.loading && !providerResults.error && (providerResults.data?.items ?? []).length === 0 &&
                <div style={{ padding: 10, fontSize: 12, color: "var(--text-tertiary)" }}>No provider credit account found.</div>}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, margin: "8px 0" }}>
          <Btn variant={direction === "credit" ? "primary" : "ghost"} onClick={() => setDirection("credit")}>Credit</Btn>
          <Btn variant={direction === "debit" ? "primary" : "ghost"} onClick={() => setDirection("debit")}>Debit</Btn>
        </div>
        <Input placeholder="Credit units" value={creditUnits} onChange={setCreditUnits} />
        <select value={reasonCode} onChange={e => setReasonCode(e.target.value)}
          style={{ width: "100%", padding: "7px 9px", margin: "8px 0", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)" }}>
          {ADJUSTMENT_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <textarea placeholder="Detailed reason" value={detailedReason} onChange={e => setDetailedReason(e.target.value)} rows={3}
          style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box" }} />
        <Input placeholder="Supporting reference (optional)" value={supportingReference} onChange={setSupportingReference} />
        {action.error && <p style={{ fontSize: 11, color: "var(--danger-text)", marginTop: 6 }}>{action.error}</p>}
        <Btn variant="primary" onClick={submit}
          disabled={action.loading || !tenantId || !Number.isFinite(Number(creditUnits)) || Number(creditUnits) <= 0 || detailedReason.trim().length < 3}
          style={{ marginTop: 10 }}>
          {action.loading ? "Submitting…" : "Submit Adjustment"}
        </Btn>
      </Card>
      <div style={{ flex: "2 1 420px" }}>
        <h4 style={{ fontSize: 12, fontWeight: 700, margin: "0 0 8px", textTransform: "uppercase", color: "var(--text-tertiary)" }}>Recent adjustments</h4>
        <QueryError message={ledger.error} onRetry={ledger.refetch} />
        <DataTable
          loading={ledger.loading}
          rows={(ledger.data?.items ?? []) as unknown as Record<string, unknown>[]}
          emptyText="No manual adjustments recorded yet."
          columns={[
            { key: "created_at", label: "Time", render: v => dt(v as string) },
            { key: "tenant_name", label: "Provider" },
            { key: "credit_delta", label: "Units", render: v => (Number(v) >= 0 ? "+" : "") + units(v) },
            { key: "reason_code", label: "Reason" },
            { key: "reason", label: "Detail" },
          ]}
        />
        <Pagination page={ledgerPage} total={ledger.data?.total ?? 0} pageSize={25} onPage={setLedgerPage} alwaysShow />
      </div>
    </div>
  );
}

// The Security Deposits and Deposit Refund Requests consoles were removed
// with the deposit itself (migrations 317/318). Providers hold spendable
// credit and purchased technician seats — nothing is held, nothing is
// refundable, so there is no queue for an admin to work.

// ── Invoices ──────────────────────────────────────────────────────────────────

function InvoicesTab() {
  const [q, setQ] = useState("");
  const query = useDebouncedValue(q);
  const [status, setStatus] = useState("");
  const [paymentStatus, setPaymentStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useApi(useCallback(() => homeServicesFinanceApi.getInvoicesSummary(), []));
  const invoices = useApi(useCallback(
    () => homeServicesFinanceApi.listInvoices({
      q: query || undefined, status: status || undefined,
      payment_status: paymentStatus || undefined, page, pageSize: 20,
    }),
    [query, status, paymentStatus, page]), [query, status, paymentStatus, page]);
  const s = summary.data as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <SummaryCard label="Issued" value={(s?.issued as number) ?? 0} />
        <SummaryCard label="Payment Collected" value={(s?.collected as number) ?? 0} />
        <SummaryCard label="Payment Verified" value={(s?.verified as number) ?? 0} />
        <SummaryCard label="Payment Pending" value={(s?.pending as number) ?? 0} tone="warning" />
        <SummaryCard label="Payment Failed" value={(s?.failed as number) ?? 0} tone="danger" />
        <SummaryCard label="Cancelled" value={(s?.cancelled as number) ?? 0} />
        <SummaryCard label="Invoice Value" value={money((s?.total_value as string) ?? 0)} />
      </div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div style={{ flex: 1, maxWidth: 320 }}><Input placeholder="Search invoice or tenant..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
        <Select value={status} onChange={v => { setStatus(v); setPage(1); }} placeholder="All invoice states" options={[
          { value: "draft", label: "Draft" }, { value: "issued", label: "Issued" },
          { value: "payment_pending", label: "Payment pending" }, { value: "payment_collected", label: "Payment collected" },
          { value: "paid", label: "Paid" }, { value: "cancelled", label: "Cancelled" },
          { value: "failed", label: "Failed" },
        ]} />
        <Select value={paymentStatus} onChange={v => { setPaymentStatus(v); setPage(1); }} placeholder="All payment states" options={[
          { value: "pending", label: "Pending" }, { value: "collected", label: "Collected" },
          { value: "verified", label: "Verified" }, { value: "failed", label: "Failed" },
          { value: "disputed", label: "Disputed" }, { value: "not_required", label: "Not required" },
        ]} />
      </div>
      <QueryError message={invoices.error} onRetry={invoices.refetch} />
      <DataTable
        loading={invoices.loading}
        rows={(invoices.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No service invoices found."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).id))}
        columns={[
          { key: "invoice_number", label: "Invoice #" },
          { key: "tenant_name", label: "Tenant" },
          { key: "total_amount", label: "Total", render: v => money(v as string) },
          { key: "payment_status", label: "Payment", render: v => <Badge variant={v === "verified" ? "success" : v === "failed" || v === "disputed" ? "danger" : v === "pending" || v === "collected" ? "warning" : "default"}>{String(v)}</Badge> },
          { key: "status", label: "Status", render: v => <Badge>{String(v)}</Badge> },
          { key: "issued_at", label: "Issued", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={invoices.data?.total ?? 0} pageSize={20} onPage={setPage} alwaysShow />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Invoice Detail" size="lg">
        {selected && <InvoiceDetail invoiceId={selected} />}
      </Modal>
    </div>
  );
}
function InvoiceDetail({ invoiceId }: { invoiceId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getInvoiceDetail(invoiceId), [invoiceId]), [invoiceId]);
  if (detail.loading) return <Skeleton height={160} />;
  return <KeyValueGrid data={detail.data} />;
}

// ── Customer Refunds ─────────────────────────────────────────────────────────

function FinancialEventsTab() {
  const [q, setQ] = useState("");
  const query = useDebouncedValue(q);
  const [eventType, setEventType] = useState("");
  const [recordType, setRecordType] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useApi(useCallback(() => homeServicesFinanceApi.getFinancialEventsSummary(), []));
  const events = useApi(useCallback(
    () => homeServicesFinanceApi.listFinancialEvents({
      q: query || undefined, event_type: eventType || undefined,
      record_type: recordType || undefined, page, pageSize: 30,
    }),
    [query, eventType, recordType, page]), [query, eventType, recordType, page]);
  const s = summary.data as Record<string, unknown> | undefined;
  const eventTypeOptions = Object.keys((s?.by_event_type as Record<string, unknown> | undefined) ?? {})
    .sort().map(value => ({ value, label: ledgerEventLabel(value) }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <SummaryCard label="Events Today" value={(s?.events_today as number) ?? 0} />
        <SummaryCard label="Immutable" value={s?.immutable ? "Yes" : "—"} />
      </div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div style={{ flex: 1, maxWidth: 320 }}><Input placeholder="Search tenant or request ID..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
        <Select value={eventType} onChange={v => { setEventType(v); setPage(1); }} placeholder="All event types" options={eventTypeOptions} />
        <Select value={recordType} onChange={v => { setRecordType(v); setPage(1); }} placeholder="All entity types" options={[
          { value: "invoice", label: "Invoice" }, { value: "payment", label: "Payment" },
          { value: "commission", label: "Commission" }, { value: "wallet", label: "Legacy wallet event" },
          { value: "activation_payment", label: "Activation payment" },
          { value: "credit_topup_order", label: "Credit top-up order" },
        ]} />
      </div>
      <QueryError message={events.error} onRetry={events.refetch} />
      <DataTable
        loading={events.loading}
        rows={(events.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No financial events recorded yet."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).event_id))}
        columns={[
          { key: "event_type", label: "Event Type" },
          { key: "record_type", label: "Entity" },
          { key: "tenant_name", label: "Tenant" },
          { key: "actor_type", label: "Actor" },
          { key: "occurred_at", label: "Occurred", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={events.data?.total ?? 0} pageSize={30} onPage={setPage} alwaysShow />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Financial Event Detail" size="lg">
        {selected && <FinancialEventDetail eventId={selected} />}
      </Modal>
    </div>
  );
}
function FinancialEventDetail({ eventId }: { eventId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getFinancialEventDetail(eventId), [eventId]), [eventId]);
  if (detail.loading) return <Skeleton height={160} />;
  return (
    <div>
      <KeyValueGrid data={detail.data} />
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 12 }}>
        Financial events are append-only. No code path exists to edit or delete this record.
      </p>
    </div>
  );
}

// ── Audit ────────────────────────────────────────────────────────────────────

function AuditPanel() {
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const audit = useApi(useCallback(() => homeServicesFinanceApi.listAudit(page, pageSize), [page]), [page]);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <QueryError message={audit.error} onRetry={audit.refetch} />
      <DataTable
        loading={audit.loading}
        rows={(audit.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No finance audit events recorded yet."
        columns={[
          { key: "operation", label: "Operation" },
          { key: "actor_role", label: "Actor" },
          { key: "after", label: "Details", render: v => <span style={{ fontFamily: "monospace", fontSize: 11 }}>{JSON.stringify(v)}</span> },
          { key: "created_at", label: "When", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={audit.data?.total ?? 0} pageSize={pageSize} onPage={setPage} alwaysShow />
    </div>
  );
}

// ── Shared: generic key/value detail grid for drawers ───────────────────────

function KeyValueGrid({ data }: { data: unknown }) {
  if (!data || typeof data !== "object") return null;
  const entries = Object.entries(data as Record<string, unknown>).filter(([k]) => !k.startsWith("_"));
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10, fontSize: 12 }}>
      {entries.map(([k, v]) => (
        <div key={k}>
          <div style={{ color: "var(--text-tertiary)", textTransform: "uppercase", fontSize: 10, marginBottom: 2 }}>{k.replace(/_/g, " ")}</div>
          <div style={{ fontWeight: 600, wordBreak: "break-word" }}>
            {v === null || v === undefined ? "—" :
              typeof v === "object" ? <pre style={{ fontSize: 11, whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(v, null, 2)}</pre> :
              String(v)}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Platform view of money that never touches the platform.
 *
 * Home-services customers pay the PROVIDER directly, so Fuvay only records
 * the declaration and the customer's confirmation of it. The tenant has had a
 * full console for this at /home-services/direct-payments. The admin view is
 * deliberately read-only: it supplies evidence, never customer interaction
 * or dispute adjudication.
 *
 * The admin list params are the admin router's own -- `q`, `pageSize`,
 * `confirmed` -- and deliberately NOT the tenant queue's `search`/`limit`/
 * `method`. Sending the tenant's names here silently returns unfiltered rows,
 * because FastAPI ignores query params it does not declare.
 */
function DirectPaymentsTab() {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [qDraft, setQDraft] = useState("");
  const [page, setPage] = useState(1);

  const summary = useApi(useCallback(
    () => homeServicesFinanceApi.getDirectPaymentsSummary(), []), []);
  const list = useApi(useCallback(
    () => homeServicesFinanceApi.listDirectPayments({
      status: status || undefined, q: q || undefined, page, pageSize: 20,
    }), [status, q, page]), [status, q, page]);

  const rows = (list.data?.items ?? []) as unknown as Record<string, unknown>[];
  const sum = (summary.data ?? {}) as Record<string, unknown>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Fuvay does not collect, hold, settle, or adjudicate this money. This is read-only
          operational evidence; the customer and provider handle confirmation and any dispute
          directly in their own apps.
        </p>
      </Card>

      {summary.data && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
          <SummaryCard label="Declarations" value={String(sum.total_attempts ?? 0)} />
          <SummaryCard label="Confirmed" value={String(sum.confirmed ?? 0)} />
          <SummaryCard label="Awaiting confirmation" value={String(sum.pending_confirmation ?? 0)} />
          <SummaryCard label="Disputed" value={String(sum.disputed ?? 0)} />
          <SummaryCard label="Provider collected" value={"₹" + String(sum.provider_collected_total ?? "0")} />
        </div>
      )}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
        <Select value={status} onChange={v => { setStatus(v); setPage(1); }} placeholder="All statuses" options={[
          { value: "awaiting_customer", label: "Awaiting customer" },
          { value: "confirmed", label: "Confirmed" },
          { value: "mismatched", label: "Mismatched" },
          { value: "disputed", label: "Disputed" },
          { value: "cancelled", label: "Cancelled" },
          { value: "reversed", label: "Reversed" },
        ]} />
        <Input
          value={qDraft}
          placeholder="Search job, provider or reference"
          onChange={v => setQDraft(v)}
        />
        <Btn variant="secondary" onClick={() => { setQ(qDraft); setPage(1); }}>Search</Btn>
        {(status || q) && (
          <Btn variant="ghost" onClick={() => { setStatus(""); setQ(""); setQDraft(""); setPage(1); }}>
            Clear
          </Btn>
        )}
      </div>

      {list.loading && <Skeleton height={220} />}
      {list.error && (
        <Card><p style={{ color: "var(--danger-text)", margin: 0 }}>{list.error}</p></Card>
      )}

      {list.data && (
        <>
          <DataTable
            rows={rows}
            emptyText="No direct payments match these filters."
            columns={[
              { key: "job_reference", label: "Job" },
              { key: "tenant_name", label: "Provider" },
              { key: "declared_amount", label: "Declared", render: v => v == null ? "—" : "₹" + String(v) },
              { key: "expected_amount", label: "Expected", render: v => v == null ? "—" : "₹" + String(v) },
              { key: "method", label: "Method" },
              {
                key: "status", label: "Status",
                render: v => {
                  const val = String(v ?? "");
                  const tone = val === "confirmed" ? "success"
                    : val === "disputed" || val === "mismatched" ? "danger"
                    : "warning";
                  return <Badge variant={tone}>{val.replace(/_/g, " ") || "—"}</Badge>;
                },
              },
              { key: "declared_at", label: "Declared at", render: v => v ? String(v).slice(0, 10) : "—" },
            ]}
          />
          <Pagination page={page} pageSize={20} total={Number(list.data.total ?? 0)} onPage={setPage} />
        </>
      )}

    </div>
  );
}
