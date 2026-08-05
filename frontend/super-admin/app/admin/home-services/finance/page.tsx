"use client";
/**
 * Home Services Finance — single consolidated workspace.
 *
 * One canonical route (/admin/home-services/finance?tab=...). Home Services
 * customers pay the PROVIDER directly (cash/UPI/card/bank transfer) --
 * ServiceOS never collects the job payment itself, holds provider earnings,
 * or pays out providers. "Direct Customer Payments" (ServicePaymentRecord,
 * invoice_payment.payment_service.record_onsite_payment) is the provider's
 * on-record of what the customer paid; a separate customer-confirmation
 * step and a separate provider completion charge (commission) exist as
 * distinct, never-merged records. No Payouts tab: confirmed structurally
 * absent for Home Services (vertical_catalog's own rules comment). A
 * provider deposit return lives entirely under Security Deposits and is
 * never a payout. The Monetization tab configures the Home-Services-only
 * platform charge policy (customer platform charge + provider completion
 * charge) via /v1/admin/home-services/finance/monetization/* -- it reuses
 * the same VerticalMonetizationPolicyService as the generic Platform >
 * Finance > Vertical Monetization page, hardcoded server-side to
 * "home_services", never a second monetization engine.
 */
import { useCallback, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, FileText, GitCompare, Sparkles, CheckCircle2, Circle, ShieldCheck, Wallet, RefreshCw, PlusCircle, Plus, Trash2 } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Input, DataTable, Skeleton, Modal, Pagination, Toaster, type ToastItem, SummaryCard,} from "../../../../components/shared/ui";
import { homeServicesFinanceApi, homeServicesFinanceMonetizationApi, homeServicesTopupPlanApi, adminWalletApi, commerceApi, type MonetizationPolicy, type TopupPlan, type WalletRecord, type CreditPackage } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

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
  | "overview" | "monetization" | "provider-charges" | "credits" | "security-deposits"
  | "invoices" | "customer-refunds" | "warranty-claims" | "financial-events" | "wallets";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "monetization", label: "Monetization" },
  // "Direct Customer Payments" removed 2026-08-05 at explicit user request --
  // this business does not use the customer-pays-provider-directly (cash/
  // UPI on-site declaration) model in Home Services. DirectPaymentsTab and
  // its backend (finance_hub/admin_hs_finance_router.py's /payments/*
  // routes, HomeServicesFinanceService.list_direct_payments et al.) stay in
  // the codebase, unlinked, in case that changes.
  { key: "provider-charges", label: "Provider Charges" },
  { key: "credits", label: "Credits & Top-ups" },
  { key: "security-deposits", label: "Security Deposits" },
  { key: "invoices", label: "Invoices" },
  { key: "customer-refunds", label: "Customer Refunds" },
  { key: "warranty-claims", label: "Warranty Claims" },
  { key: "financial-events", label: "Financial Events" },
  // Same /admin/provider-wallets data (adminWalletApi, real + already live) --
  // surfaced here too so this one page covers every Home Services money
  // surface; the standalone /admin/provider-wallets route stays live,
  // unlinked from nav, per this session's "don't delete before parity is
  // proven" rule.
  { key: "wallets", label: "Wallets" },
];

function money(v?: string | number | null) {
  const n = Number(v ?? 0);
  return `₹${n.toLocaleString("en-IN")}`;
}
function dt(v?: string | null) {
  return v ? new Date(v).toLocaleString("en-IN") : "—";
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
  const tab = (params.get("tab") as TabKey) || "overview";
  const [auditOpen, setAuditOpen] = useState(false);

  function setTab(t: TabKey) {
    router.replace(`/admin/home-services/finance?tab=${t}`);
  }

  return (
    <AdminLayout activeNav="hs-finance">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>Home Services Finance</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
            Direct customer payments, provider charges and financial operations for Home Services.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="ghost" icon={<FileText size={14} />} onClick={() => setAuditOpen(true)}>View Audit</Btn>
          <ExportButton tab={tab} />
        </div>
      </div>

      <StatusStrip />

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", margin: "16px 0", overflowX: "auto" }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{
              padding: "10px 14px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === t.key ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === t.key ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer",
              whiteSpace: "nowrap",
            }}>{t.label}</button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab onNavigate={setTab} />}
      {tab === "monetization" && <MonetizationTab />}
      {tab === "provider-charges" && <ProviderChargesTab />}
      {tab === "credits" && <CreditsTab />}
      {tab === "security-deposits" && <SecurityDepositsTab />}
      {tab === "invoices" && <InvoicesTab />}
      {tab === "customer-refunds" && <CustomerRefundsTab />}
      {tab === "warranty-claims" && <WarrantyClaimsTab />}
      {tab === "financial-events" && <FinancialEventsTab />}
      {tab === "wallets" && <WalletsTab />}

      <Modal open={auditOpen} onClose={() => setAuditOpen(false)} title="Audit Trail" size="lg">
        <AuditPanel />
      </Modal>
    </AdminLayout>
  );
}

function ExportButton({ tab }: { tab: TabKey }) {
  async function doExport() {
    let rows: Record<string, unknown>[] = [];
    if (tab === "provider-charges") rows = (await homeServicesFinanceApi.listProviderCharges({ pageSize: 5000 })).items;
    else if (tab === "credits") rows = (await homeServicesFinanceApi.listTopups({ pageSize: 5000 })).items;
    else if (tab === "security-deposits") rows = (await homeServicesFinanceApi.listDeposits({ pageSize: 5000 })).items;
    else if (tab === "invoices") rows = (await homeServicesFinanceApi.listInvoices({ pageSize: 5000 })).items;
    else if (tab === "customer-refunds") rows = (await homeServicesFinanceApi.listRefunds({ pageSize: 5000 })).items;
    else if (tab === "warranty-claims") rows = (await homeServicesFinanceApi.listWarrantyClaims({ pageSize: 5000 })).items;
    else if (tab === "financial-events") rows = (await homeServicesFinanceApi.listFinancialEvents({ pageSize: 5000 })).items;
    else if (tab === "wallets") rows = (await adminWalletApi.list()) as unknown as Record<string, unknown>[];
    else { const ov = await homeServicesFinanceApi.getOverview(); rows = [ov as Record<string, unknown>]; }

    if (rows.length === 0) { alert("Nothing to export for this tab yet."); return; }
    const headers = Object.keys(rows[0]);
    const csv = [headers.join(","), ...rows.map(r => headers.map(h => JSON.stringify(r[h] ?? "")).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `home-services-finance-${tab}.csv`; a.click();
    URL.revokeObjectURL(url);
  }
  return <Btn variant="ghost" icon={<Download size={14} />} onClick={doExport}>Export</Btn>;
}

function StatusStrip() {
  const ledger = useApi(useCallback(() => homeServicesFinanceApi.getLedgerHealth(), []));
  const h = ledger.data;
  return (
    <Card padding={16} style={{ display: "flex", flexWrap: "wrap", gap: 24 }}>
      <StatusDot ok label="Home Services vertical" value="Active" />
      <StatusDot ok label="Provider charging" value="Operational" />
      <StatusDot ok={h?.idempotency_protected ?? true} label="Credit ledger" value={h?.idempotency_protected ? "Healthy" : "Checking"} />
      <StatusDot ok={h?.append_only ?? true} label="Deposit ledger" value={h?.append_only ? "Healthy" : "Checking"} />
      <StatusDot ok label="Reconciliation" value={h?.last_reconciliation ? dt(h.last_reconciliation) : "Not yet run"} />
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
    provider_completion_charges: { posted: number; total_amount: string };
    active_usage_credit_balance: string; security_deposits_held: string;
  };
  secondary: {
    low_credit_providers: number; failed_charge_recoveries: number; deposit_return_requests: number;
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
  const b = o.group_b_serviceos_financial_position;
  const sec = o.secondary;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h3 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>
          ServiceOS financial position
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
          <NotTrackedCard label="Platform Charges Recovered" tracked={b.platform_charge_recovery_tracked} value={b.platform_charges_recovered} />
          <SummaryCard label="Provider Completion Charges" value={money(b.provider_completion_charges.total_amount)} onClick={() => onNavigate("provider-charges")} />
          <SummaryCard label="Available Usage Credits" value={money(b.active_usage_credit_balance)} onClick={() => onNavigate("credits")} />
          <SummaryCard label="Security Deposits Held" value={money(b.security_deposits_held)} onClick={() => onNavigate("security-deposits")} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <SummaryCard label="Low-Credit Providers" value={sec.low_credit_providers} tone={sec.low_credit_providers > 0 ? "warning" : undefined} onClick={() => onNavigate("credits")} />
        <SummaryCard label="Failed Charge Recoveries" value={sec.failed_charge_recoveries} tone={sec.failed_charge_recoveries > 0 ? "danger" : undefined} onClick={() => onNavigate("provider-charges")} />
        <SummaryCard label="Deposit Return Requests" value={sec.deposit_return_requests} tone={sec.deposit_return_requests > 0 ? "warning" : undefined} onClick={() => onNavigate("security-deposits")} />
        <SummaryCard label="Warranty Financial Exposure" value={money(sec.warranty_financial_exposure)} onClick={() => onNavigate("warranty-claims")} />
        <SummaryCard label="Finance Exceptions" value={sec.finance_exceptions} tone={sec.finance_exceptions > 0 ? "danger" : undefined} />
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
          ServiceOS does not hold or pay out provider service earnings.
        </p>
      </Card>

      <Card padding={16} style={{ borderColor: "var(--warning-text, #b45309)" }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 6px" }}>Audit note</h3>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>{o.audit_note}</p>
      </Card>
    </div>
  );
}

function NotTrackedCard({ label, tracked, value }: { label: string; tracked: boolean; value: string | null }) {
  return (
    <Card padding={16}>
      <div style={{ fontSize: 22, fontWeight: 800, color: tracked ? "var(--text-primary)" : "var(--text-tertiary)" }}>
        {tracked ? money(value) : "Not tracked"}
      </div>
      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>{label}</div>
    </Card>
  );
}

// ── Monetization ─────────────────────────────────────────────────────────────
// Home-Services-only policy workspace: reuses the same monetization engine as
// Platform > Finance > Vertical Monetization, hardcoded server-side to
// "home_services" so it can never read or mutate another vertical's policy.

// All 5 are real enum values on the shared cross-vertical
// VerticalMonetizationPolicy model. Only COMPLETION_CREDITS is currently
// wired to actual job-completion charging for Home Services (execution/
// usage_credit_deduction.py::deduct_for_completed_job always reads the flat
// per-service credit amount from the Provider Completion Charge Config
// table, never provider_model/provider_percentage) -- the others are kept
// selectable (per explicit request) and clearly labeled as not-yet-enforced
// below, rather than removed.
const PROVIDER_MODELS = ["NONE", "COMPLETION_CREDITS", "PERCENTAGE_COMMISSION", "FIXED_COMPLETION_CHARGE", "SUBSCRIPTION", "LEAD_FEE"];
const CUSTOMER_FEE_MODELS = ["NONE", "PERCENTAGE", "FIXED", "PERCENTAGE_WITH_MIN_MAX"];

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

  const currentApi = useApi(useCallback(() => homeServicesFinanceMonetizationApi.getCurrent(), []));
  const draftApi = useApi(useCallback(() => homeServicesFinanceMonetizationApi.getDraft(), []));
  const historyApi = useApi(useCallback(() => homeServicesFinanceMonetizationApi.getHistory(), []), [showCompare], { enabled: showCompare });

  const saveDraftAction = useAction((p: Partial<MonetizationPolicy>) => homeServicesFinanceMonetizationApi.saveDraft(p));
  const publishAction = useAction((r: string) => homeServicesFinanceMonetizationApi.publish(r));
  const discardDraftAction = useAction(() => homeServicesFinanceMonetizationApi.discardDraft());

  const current = currentApi.data as MonetizationPolicy | null;
  const draft = draftApi.data as MonetizationPolicy | null;

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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Toaster toasts={toasts} onRemove={remove} />
      <Card padding={16} style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "center" }}>
        <StatusDot ok label="Active Policy" value={current ? `v${current.version_number}` : "None"} />
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
                Provider-side charge <Badge variant="success">Active</Badge>
              </p>
              <Btn variant="ghost" onClick={startDraft}>Edit in Draft</Btn>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 14, fontSize: 12 }}>
              <KV label="Revenue model" value={fmt(current?.provider_model)} />
              <KV label="Trigger" value="Eligible job completion" />
              <KV label="Actual charge" value="Set per-service — see Provider Charges tab" />
              <KV label="Recovery source" value="Provider usage credits" />
            </div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
              The real per-job amount is configured per service/job-type in the Provider Charges tab's
              &quot;Provider Completion Charge Config&quot;, not here — this card just records the vertical's charging model.
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)", flexWrap: "wrap" }}>
              <CheckCircle2 size={13} /> Eligible completion → <CheckCircle2 size={13} /> Idempotency check → <CheckCircle2 size={13} /> Credits deducted → <CheckCircle2 size={13} /> Ledger posted
            </div>
          </Card>

          <Card padding={16}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <p style={{ fontSize: 14, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                Customer platform charge <Badge variant="success">Active</Badge>
              </p>
              <Btn variant="ghost" onClick={startDraft}>Edit in Draft</Btn>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 12, fontSize: 12 }}>
              <KV label="Fee model" value={fmt(current?.customer_fee_model)} />
              <KV label="Rate" value={current?.customer_fee_percentage ? `${current.customer_fee_percentage}%` : "—"} />
              <KV label="Minimum" value={current?.customer_fee_min_minor != null ? money(current.customer_fee_min_minor / 100) : "—"} />
              <KV label="Maximum" value={current?.customer_fee_max_minor != null ? money(current.customer_fee_max_minor / 100) : "—"} />
              <KV label="Collection" value="Provider collects directly" />
              <KV label="Recovery" value="Deducted from usage credits" />
            </div>
            <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>
              ServiceOS does not collect the customer&apos;s job payment.
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
                <PreviewRow label="Provider completion charge" value="Varies by service — see Provider Charges tab" />
                <PreviewRow label="ServiceOS holds provider earnings" value="₹0" />
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>Preview only — does not change tenant pricing.</p>
              </div>
            )}
          </Card>

          <Card padding={16}>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px" }}>Policy lifecycle</p>
            {["Draft configuration", "Validate rules", "Preview impact", "Finance review", "Publish version"].map((step, i) => (
              <div key={step} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, fontSize: 12, color: i < 3 ? "var(--success-text)" : "var(--text-tertiary)" }}>
                {i < 3 ? <CheckCircle2 size={13} /> : <Circle size={13} />} {step}
              </div>
            ))}
            <Badge variant="success">v{fmt(current?.version_number)} Active</Badge>
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
            {PROVIDER_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          {form.provider_model === "COMPLETION_CREDITS" ? (
            <>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px" }}>
                This value is a record of intent only — it does not drive actual charging. The real amount deducted
                per completed job is set per-service in <strong>Provider Charges &gt; Provider Completion Charge
                Config</strong> (a service with no rule there is charged 0 credits regardless of what's set here).
              </p>
              <Input placeholder="Credit units (reference only, not enforced)" value={String(form.provider_credit_units ?? "")}
                onChange={v => setForm({ ...form, provider_credit_units: Number(v) })} />
            </>
          ) : form.provider_model !== "NONE" && (
            <p style={{ fontSize: 11, color: "var(--warning-text, #b45309)", margin: "0 0 8px" }}>
              Not yet enforced for Home Services — job completion always charges the flat per-service credit amount
              (Provider Charges tab), regardless of this setting. Saved here for record-keeping only.
            </p>
          )}
          {form.provider_model === "PERCENTAGE_COMMISSION" && (
            <Input placeholder="Provider commission % of invoice (e.g. 10)" value={String(form.provider_percentage ?? "")}
              onChange={v => setForm({ ...form, provider_percentage: v })} />
          )}
          {form.provider_model === "FIXED_COMPLETION_CHARGE" && (
            <Input placeholder="Fixed charge per job (₹)" value={form.provider_fixed_amount_minor != null ? String(form.provider_fixed_amount_minor / 100) : ""}
              onChange={v => setForm({ ...form, provider_fixed_amount_minor: Math.round(Number(v) * 100) })} />
          )}
          {form.provider_model === "SUBSCRIPTION" && (
            <Input placeholder="Subscription plan ID" value={String(form.provider_subscription_plan_id ?? "")}
              onChange={v => setForm({ ...form, provider_subscription_plan_id: v })} />
          )}

          <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.03em", marginTop: 16, display: "block" }}>
            Customer-side charge — added to what the customer pays
          </label>
          <select value={form.customer_fee_model ?? "NONE"} onChange={e => setForm({ ...form, customer_fee_model: e.target.value })}
            style={{ width: "100%", padding: "7px 9px", margin: "4px 0 10px" }}>
            {CUSTOMER_FEE_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          {(form.customer_fee_model === "PERCENTAGE" || form.customer_fee_model === "PERCENTAGE_WITH_MIN_MAX") && (
            <Input placeholder="Customer platform fee %" value={String(form.customer_fee_percentage ?? "")}
              onChange={v => setForm({ ...form, customer_fee_percentage: v })} />
          )}
          {form.customer_fee_model === "FIXED" && (
            <Input placeholder="Fixed fee (₹)" value={form.customer_fee_fixed_amount_minor != null ? String(form.customer_fee_fixed_amount_minor / 100) : ""}
              onChange={v => setForm({ ...form, customer_fee_fixed_amount_minor: Math.round(Number(v) * 100) })} />
          )}
          {form.customer_fee_model === "PERCENTAGE_WITH_MIN_MAX" && (
            <div style={{ display: "flex", gap: 8 }}>
              <Input placeholder="Min fee (₹)" value={form.customer_fee_min_minor != null ? String(form.customer_fee_min_minor / 100) : ""}
                onChange={v => setForm({ ...form, customer_fee_min_minor: Math.round(Number(v) * 100) })} />
              <Input placeholder="Max fee (₹)" value={form.customer_fee_max_minor != null ? String(form.customer_fee_max_minor / 100) : ""}
                onChange={v => setForm({ ...form, customer_fee_max_minor: Math.round(Number(v) * 100) })} />
            </div>
          )}
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

// ── Provider Activation Requirement + Top-up Plans ──────────────────────────
// Lives under Credits & Top-ups > "Top-up Plans" sub-tab. Two genuinely
// separate things, both on HomeServicesActivationFinancePolicy (NOT
// VerticalMonetizationPolicy): (1) the ONE-TIME deposit + optional starter
// credit purchase a tenant must clear to activate as a provider (read by
// vertical_catalog/activation.py, activation_payment_service.py,
// tenant_finance_readiness_router.py -- genuinely load-bearing, cannot be
// removed), and (2) the REPEATABLE top-up plans a tenant can buy any time,
// any number of times (backed by CreditPackage, platform_commerce engine).
// Deliberately called "Plans" in the UI, not "Packages" -- per explicit user
// preference, matches how they think about tenant-facing pricing tiers.

function TopupPackagesPanel() {
  const { toasts, push, remove } = useToasts();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Toaster toasts={toasts} onRemove={remove} />
      <TopupPlanSection onToast={push} />
      <TopupPackagesSection onToast={push} />
    </div>
  );
}

function TopupPlanSection({ onToast }: { onToast: (msg: string, variant?: ToastItem["variant"]) => void }) {
  const [showDrawer, setShowDrawer] = useState(false);
  const [form, setForm] = useState<Partial<TopupPlan>>({});
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<string[]>([]);

  const currentApi = useApi(useCallback(() => homeServicesTopupPlanApi.getCurrent(), []));
  const draftApi = useApi(useCallback(() => homeServicesTopupPlanApi.getDraft(), []));
  const saveDraftAction = useAction((p: Partial<TopupPlan>) => homeServicesTopupPlanApi.saveDraft(p));
  const publishAction = useAction((r: string) => homeServicesTopupPlanApi.publish(r));
  const discardDraftAction = useAction(() => homeServicesTopupPlanApi.discardDraft());

  const current = currentApi.data as TopupPlan | null;
  const draft = draftApi.data as TopupPlan | null;

  function startDraft() {
    setForm(draft ?? current ?? {
      credit_package_base_amount: 1000, credit_package_gst_percent: 18,
      credited_wallet_amount: 1000, deposit_amount_per_technician: 2000, currency: "INR",
    });
    setErrors([]);
    setShowDrawer(true);
  }

  async function validateNow(): Promise<boolean> {
    const v = await homeServicesTopupPlanApi.validate(form);
    setErrors(v.errors);
    if (v.errors.length > 0) onToast("Fix validation errors first.", "warning");
    return v.errors.length === 0;
  }

  async function saveDraft() {
    if (!(await validateNow())) return;
    const r = await saveDraftAction.execute(form);
    if (r) { draftApi.refetch(); onToast("Top-up plan draft saved."); }
    else onToast(saveDraftAction.error ?? "Failed to save draft.", "danger");
  }

  async function confirmPublish() {
    if (!reason.trim()) return;
    if (!(await validateNow())) return;
    // Publish only takes a reason -- it publishes whatever draft is already
    // saved server-side, so on-screen edits that were never sent via
    // "Save Draft" were silently lost (or publish 404'd with no draft to
    // publish at all). Always sync the form first, then publish it.
    const saved = await saveDraftAction.execute(form);
    if (!saved) {
      onToast(saveDraftAction.error ?? "Failed to save your changes before publishing.", "danger");
      return;
    }
    const r = await publishAction.execute(reason.trim());
    if (r) {
      setShowDrawer(false); setReason(""); currentApi.refetch(); draftApi.refetch();
      onToast("Top-up plan published — now live.");
    } else {
      onToast(publishAction.error ?? "Failed to publish.", "danger");
    }
  }

  async function discardDraft() {
    const r = await discardDraftAction.execute();
    if (r) { setShowDrawer(false); draftApi.refetch(); onToast("Draft discarded."); }
    else onToast(discardDraftAction.error ?? "Failed to discard draft.", "danger");
  }

  const gstAmount = current ? Math.round((current.credit_package_base_amount * current.credit_package_gst_percent) / 100) : 0;
  const nothingRequired = current && !current.deposit_required && !current.initial_credit_purchase_required;

  return (
    <Card padding={16}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
          Provider Activation Requirement
          {draft && <Badge variant="warning">Draft v{draft.version_number} pending</Badge>}
        </p>
        <div style={{ display: "flex", gap: 6 }}>
          {draft && (
            <Btn variant="ghost" size="sm" icon={<Trash2 size={14} />} onClick={discardDraft} disabled={discardDraftAction.loading}
              style={{ color: "var(--danger-text)" }}>
              {discardDraftAction.loading ? "Deleting…" : "Delete Draft"}
            </Btn>
          )}
          <Btn variant="ghost" size="sm" icon={<Sparkles size={14} />} onClick={startDraft}>{draft ? "Edit Draft" : "Edit"}</Btn>
        </div>
      </div>

      {nothingRequired ? (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          No deposit or starter purchase required — providers can activate immediately. Ongoing credit purchases
          are the Top-up Plans below.
        </p>
      ) : (
        <>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
            One-time requirement to activate as a provider — separate from the repeatable Top-up Plans below.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, fontSize: 12 }}>
            <KV label="Security deposit / technician" value={current?.deposit_required ? money(current.deposit_amount_per_technician) : "Not required"} />
            {current?.initial_credit_purchase_required && (
              <>
                <KV label="Starter purchase amount" value={money(current.credit_package_base_amount)} />
                <KV label="GST" value={`${current.credit_package_gst_percent}% (${money(gstAmount)})`} />
                <KV label="Credits granted" value={units(current.credited_wallet_amount)} />
              </>
            )}
          </div>
        </>
      )}

      {showDrawer && (
        <Modal open onClose={() => setShowDrawer(false)} title="Edit Activation Requirement" size="md">
          <label style={{ fontSize: 12, fontWeight: 600 }}>Security deposit</label>
          <div style={{ display: "flex", gap: 8, margin: "4px 0 10px" }}>
            <Btn variant={form.deposit_required !== false ? "primary" : "ghost"}
              onClick={() => setForm({ ...form, deposit_required: true })}>Required</Btn>
            <Btn variant={form.deposit_required === false ? "primary" : "ghost"}
              onClick={() => setForm({ ...form, deposit_required: false })}>Not required</Btn>
          </div>
          {form.deposit_required !== false && (
            <>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Deposit per technician (₹)</label>
              <Input value={String(form.deposit_amount_per_technician ?? "")}
                onChange={v => setForm({ ...form, deposit_amount_per_technician: Number(v) })} />
            </>
          )}

          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginTop: 16 }}>Starter credit purchase</label>
          <div style={{ display: "flex", gap: 8, margin: "4px 0 10px" }}>
            <Btn variant={form.initial_credit_purchase_required !== false ? "primary" : "ghost"}
              onClick={() => setForm({ ...form, initial_credit_purchase_required: true })}>Required</Btn>
            <Btn variant={form.initial_credit_purchase_required === false ? "primary" : "ghost"}
              onClick={() => setForm({ ...form, initial_credit_purchase_required: false })}>Not required</Btn>
          </div>
          {form.initial_credit_purchase_required !== false && (
            <>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Starter purchase amount (₹)</label>
              <Input value={String(form.credit_package_base_amount ?? "")}
                onChange={v => setForm({ ...form, credit_package_base_amount: Number(v), credited_wallet_amount: Number(v) })} />
              <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginTop: 10 }}>GST %</label>
              <Input value={String(form.credit_package_gst_percent ?? "")}
                onChange={v => setForm({ ...form, credit_package_gst_percent: Number(v) })} />
            </>
          )}
          {errors.length > 0 && errors.map(e => <p key={e} style={{ fontSize: 11, color: "var(--danger-text)", margin: "4px 0 0" }}>{e}</p>)}
          <div style={{ display: "flex", gap: 8, margin: "14px 0" }}>
            <Btn variant="secondary" onClick={validateNow}>Validate</Btn>
            <Btn variant="secondary" onClick={saveDraft} disabled={saveDraftAction.loading}>
              {saveDraftAction.loading ? "Saving…" : "Save Draft"}
            </Btn>
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
            <Btn variant="ghost" onClick={() => setShowDrawer(false)}>Cancel</Btn>
            <Btn variant="primary" disabled={!reason.trim() || errors.length > 0} onClick={confirmPublish}>
              {publishAction.loading ? "Publishing…" : "Review & Publish"}
            </Btn>
          </div>
        </Modal>
      )}
    </Card>
  );
}

// ── Top-up Plans (multiple named, purchasable price tiers) ─────────────────
// What a tenant actually buys credits with, any time, any number of times.
// Reuses the real, already-live CreditPackage admin CRUD (platform_commerce
// engine, /v1/commerce/packages) rather than inventing a new table -- wired
// into the real Home Services top-up flow via CreditTopupOrder.
// credit_package_id (tenant_hs_finance_service.create_topup accepts
// credit_package_id and credits the same TenantBilling/UsageCreditLedger
// pipeline as everything else).
const EMPTY_PKG_FORM = { name: "", description: "", credits_amount: "1000", price_inr: "1000", bonus_pct: "0" };

function TopupPackagesSection({ onToast }: { onToast: (msg: string, variant?: ToastItem["variant"]) => void }) {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_PKG_FORM);

  const pkgsApi = useApi(useCallback(() => commerceApi.listPackages(), []), []);
  const createAction = useAction((body: Record<string, unknown>) => commerceApi.createPackage(body as Parameters<typeof commerceApi.createPackage>[0]));
  const updateAction = useAction((id: string, body: Record<string, unknown>) => commerceApi.updatePackage(id, body));
  const archiveAction = useAction((id: string) => commerceApi.deletePackage(id));
  const deleteAction = useAction((id: string) => commerceApi.deletePackagePermanently(id));

  const packages = pkgsApi.data?.packages ?? [];

  function startCreate() {
    setEditingId(null);
    setForm(EMPTY_PKG_FORM);
    setShowForm(true);
  }
  function startEdit(pkg: CreditPackage) {
    setEditingId(pkg.package_id);
    setForm({
      name: pkg.name, description: pkg.description ?? "",
      credits_amount: String(pkg.credits_amount), price_inr: String(pkg.price_inr), bonus_pct: String(pkg.bonus_pct),
    });
    setShowForm(true);
  }

  async function submit() {
    if (!form.name.trim() || !form.credits_amount.trim() || !form.price_inr.trim()) return;
    const body = {
      name: form.name.trim(), description: form.description.trim() || undefined,
      credits_amount: Number(form.credits_amount), price_inr: Number(form.price_inr),
      bonus_pct: Number(form.bonus_pct) || 0,
    };
    const result = editingId ? await updateAction.execute(editingId, body) : await createAction.execute(body);
    if (result) {
      setShowForm(false); setEditingId(null); pkgsApi.refetch();
      onToast(editingId ? "Plan updated." : "Plan created.");
    } else {
      onToast((editingId ? updateAction.error : createAction.error) ?? "Failed to save plan.", "danger");
    }
  }

  async function archive(pkg: CreditPackage) {
    if (!confirm(`Archive plan "${pkg.name}"? Tenants will no longer be able to buy it.`)) return;
    const result = await archiveAction.execute(pkg.package_id);
    if (result === null) onToast(archiveAction.error ?? "Failed to archive plan.", "danger");
    else { pkgsApi.refetch(); onToast("Plan archived."); }
  }

  async function deletePermanently(pkg: CreditPackage) {
    if (!confirm(`Permanently delete plan "${pkg.name}"? This cannot be undone.`)) return;
    const result = await deleteAction.execute(pkg.package_id);
    if (result === null) onToast(deleteAction.error ?? "Failed to delete plan.", "danger");
    else { pkgsApi.refetch(); onToast("Plan deleted."); }
  }

  const activePkgs = packages.filter(p => p.is_active);
  const archivedPkgs = packages.filter(p => !p.is_active);

  return (
    <Card padding={16}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Top-up Plans</p>
        <Btn variant="primary" icon={<Plus size={14} />} onClick={startCreate}>Create Plan</Btn>
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 14px" }}>
        This is what tenants actually buy — create as many plans as you want, at any price from low to high.
        A tenant picks one and can buy it again any time (unlike the one-time activation requirement above).
      </p>

      {pkgsApi.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
          {[0, 1, 2].map(i => <Skeleton key={i} height={130} />)}
        </div>
      ) : packages.length === 0 ? (
        <div style={{ padding: "28px 0", textAlign: "center" }}>
          <Wallet size={28} style={{ color: "var(--text-tertiary)", margin: "0 auto 10px", display: "block" }} />
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 4px" }}>No top-up plans created yet.</p>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Click &quot;Create Plan&quot; to add your first one — tenants can&apos;t buy credits until at least one plan exists.</p>
        </div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
            {activePkgs.map(pkg => (
              <div key={pkg.package_id} style={{
                display: "flex", flexDirection: "column", gap: 8, padding: 16, borderRadius: 12,
                border: "1px solid var(--border)", background: "var(--surface-elevated, var(--surface))",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{pkg.name}</span>
                  {pkg.bonus_pct > 0 && <Badge variant="success">+{pkg.bonus_pct}% bonus</Badge>}
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--brand)" }}>{money(pkg.price_inr)}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {units(pkg.total_credits)} credited
                  {pkg.bonus_pct > 0 && <span style={{ color: "var(--text-tertiary)" }}> ({units(pkg.credits_amount)} base)</span>}
                </div>
                {pkg.description && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{pkg.description}</p>}
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: "auto" }}>
                  {pkg.purchase_count > 0 ? `Bought ${pkg.purchase_count}×` : "Never purchased"}
                </div>
                <div style={{ display: "flex", gap: 6, marginTop: 4, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
                  <Btn variant="ghost" size="sm" onClick={() => startEdit(pkg)} style={{ flex: 1, justifyContent: "center" }}>Edit</Btn>
                  {pkg.purchase_count === 0 ? (
                    <Btn variant="ghost" size="sm" onClick={() => deletePermanently(pkg)} style={{ flex: 1, justifyContent: "center", color: "var(--danger-text)" }}>Delete</Btn>
                  ) : (
                    <Btn variant="ghost" size="sm" onClick={() => archive(pkg)} style={{ flex: 1, justifyContent: "center", color: "var(--danger-text)" }}>Archive</Btn>
                  )}
                </div>
              </div>
            ))}
          </div>

          {archivedPkgs.length > 0 && (
            <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
              <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.03em", color: "var(--text-tertiary)", margin: "0 0 8px" }}>
                Archived
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {archivedPkgs.map(pkg => (
                  <div key={pkg.package_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "8px 12px", borderRadius: 8, background: "var(--surface-sunken)", opacity: 0.7 }}>
                    <span style={{ fontSize: 12 }}>{pkg.name} — {money(pkg.price_inr)} for {units(pkg.total_credits)}</span>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <Badge>Archived</Badge>
                      {pkg.purchase_count === 0 && (
                        <Btn variant="ghost" size="sm" onClick={() => deletePermanently(pkg)} style={{ color: "var(--danger-text)" }}>Delete</Btn>
                      )}
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
        <Input value={form.name} onChange={v => setForm({ ...form, name: v })} placeholder="e.g. Starter, Pro, Bulk" />
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginTop: 10 }}>Description (optional)</label>
        <Input value={form.description} onChange={v => setForm({ ...form, description: v })} />
        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Credits</label>
            <Input value={form.credits_amount} onChange={v => setForm({ ...form, credits_amount: v })} disabled={!!editingId} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Price (₹)</label>
            <Input value={form.price_inr} onChange={v => setForm({ ...form, price_inr: v })} />
          </div>
        </div>
        {editingId && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>Credits can&apos;t change once this plan has ever been purchased.</p>}
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginTop: 10 }}>Bonus %</label>
        <Input value={form.bonus_pct} onChange={v => setForm({ ...form, bonus_pct: v })} placeholder="0" />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
          <Btn variant="ghost" onClick={() => setShowForm(false)}>Cancel</Btn>
          <Btn variant="primary" loading={createAction.loading || updateAction.loading}
            disabled={!form.name.trim() || !form.credits_amount.trim() || !form.price_inr.trim()}
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

// ── Direct Customer Payments ─────────────────────────────────────────────────

function DirectPaymentsTab() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useApi(useCallback(() => homeServicesFinanceApi.getDirectPaymentsSummary(), []));
  const payments = useApi(useCallback(
    () => homeServicesFinanceApi.listDirectPayments({ q: q || undefined, page, pageSize: 20 }),
    [q, page]));
  const s = summary.data as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <SummaryCard label="Total Attempts" value={(s?.total_attempts as number) ?? 0} />
        <SummaryCard label="Confirmed" value={(s?.confirmed as number) ?? 0} />
        <SummaryCard label="Pending Confirmation" value={(s?.pending_confirmation as number) ?? 0} tone="warning" />
        <SummaryCard label="Disputed" value={(s?.disputed as number) ?? 0} tone="danger" />
        <SummaryCard label="Provider-Collected Total" value={money((s?.provider_collected_total as string) ?? 0)} />
        <SummaryCard label="Customer Platform Charges Recorded" value={money((s?.customer_platform_charges_recorded as string) ?? 0)} />
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        The customer pays the provider directly. ServiceOS never collects this payment or holds provider earnings.
      </p>
      <div style={{ maxWidth: 320 }}><Input placeholder="Search invoice or provider..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
      <DataTable
        loading={payments.loading}
        rows={(payments.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No direct customer payments recorded yet."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).id))}
        columns={[
          { key: "invoice_number", label: "Invoice #" },
          { key: "tenant_name", label: "Provider" },
          { key: "provider_collected_amount", label: "Provider-Collected", render: v => money(v as string) },
          { key: "customer_platform_charge", label: "Platform Charge", render: v => money(v as string) },
          { key: "payment_mode", label: "Method" },
          { key: "payment_status", label: "Status", render: v => <Badge variant={v === "verified" || v === "collected" ? "success" : v === "disputed" || v === "failed" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "customer_confirmed", label: "Confirmed", render: v => v ? <Badge variant="success">Yes</Badge> : <Badge variant="warning">Pending</Badge> },
          { key: "created_at", label: "Recorded", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={payments.data?.total ?? 0} pageSize={20} onPage={setPage} />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Direct Customer Payment Detail" size="lg">
        {selected && <DirectPaymentDetail paymentId={selected} />}
      </Modal>
    </div>
  );
}
function DirectPaymentDetail({ paymentId }: { paymentId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getDirectPaymentDetail(paymentId), [paymentId]));
  if (detail.loading) return <Skeleton height={160} />;
  const d = detail.data as Record<string, unknown> | undefined;
  const recovery = d?.customer_platform_charge_recovery as { status: string; credits: string | null; posted_at: string | null } | undefined;
  const completion = d?.provider_completion_charge as { status: string; credits: string | null; posted_at: string | null } | undefined;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <KeyValueGrid data={detail.data} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <ChargeLedgerCard title="CUSTOMER_PLATFORM_CHARGE_RECOVERY" entry={recovery} />
        <ChargeLedgerCard title="PROVIDER_COMPLETION_CHARGE" entry={completion} />
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
        Two independent ledger entries, never merged into one commission record. ServiceOS collected
        ₹0 from the customer directly — this payment was recorded by the provider.
      </p>
    </div>
  );
}
function ChargeLedgerCard({ title, entry }: { title: string; entry?: { status: string; credits: string | null; posted_at: string | null } }) {
  const posted = entry?.status === "posted" || entry?.status === "recovered";
  return (
    <Card padding={14}>
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.03em", color: "var(--text-tertiary)", marginBottom: 8 }}>{title}</div>
      <Badge variant={posted ? "success" : "default"}>{entry?.status ?? "not_calculated"}</Badge>
      {entry?.credits && <div style={{ fontSize: 18, fontWeight: 800, marginTop: 8 }}>{entry.credits} credits</div>}
      {entry?.posted_at && <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>Posted {dt(entry.posted_at)}</div>}
    </Card>
  );
}

// ── Provider Charges ─────────────────────────────────────────────────────────

function ProviderChargesTab() {
  const [q, setQ] = useState("");
  const [chargeModel, setChargeModel] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const charges = useApi(useCallback(
    () => homeServicesFinanceApi.listProviderCharges({ chargeModel, page, pageSize: 20 }),
    [chargeModel, page]));
  const filtered = (charges.data?.items ?? []).filter(r =>
    !q || JSON.stringify(r).toLowerCase().includes(q.toLowerCase()));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", gap: 10 }}>
        <div style={{ flex: 1, maxWidth: 320 }}><Input placeholder="Search tenant or job..." value={q} onChange={setQ} /></div>
        <Btn variant={chargeModel === undefined ? "primary" : "ghost"} onClick={() => setChargeModel(undefined)}>All</Btn>
        <Btn variant={chargeModel === "usage_credit" ? "primary" : "ghost"} onClick={() => setChargeModel("usage_credit")}>Usage Credit</Btn>
        <Btn variant={chargeModel === "commission" ? "primary" : "ghost"} onClick={() => setChargeModel("commission")}>Commission</Btn>
      </div>
      <DataTable
        loading={charges.loading}
        rows={filtered as unknown as Record<string, unknown>[]}
        emptyText="No provider charges found for this filter."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).charge_ref))}
        columns={[
          { key: "charge_ref", label: "Charge Ref", render: v => <span style={{ fontFamily: "monospace", fontSize: 12 }}>{String(v).split(":")[1]?.slice(0, 8)}</span> },
          { key: "charge_model", label: "Model", render: v => <Badge variant={v === "commission" ? "info" : "default"}>{String(v)}</Badge> },
          { key: "tenant_name", label: "Tenant" },
          { key: "job_id", label: "Job", render: v => v ? String(v).slice(0, 8) : "—" },
          { key: "amount", label: "Amount", render: v => money(v as string) },
          { key: "status", label: "Status", render: v => <Badge variant={v === "posted" || v === "deducted" ? "success" : v === "failed" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "triggered_at", label: "Triggered", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={charges.data?.total ?? 0} pageSize={20} onPage={setPage} />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Provider Charge Detail" size="lg">
        {selected && <ProviderChargeDetail chargeRef={selected} />}
      </Modal>

      <ChargeConfigSection />
    </div>
  );
}

function ChargeConfigSection() {
  const config = useApi(useCallback(() => homeServicesFinanceApi.listChargeConfig({ pageSize: 100 }), []));
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);

  async function save(ruleId: string) {
    const raw = editing[ruleId];
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0) { alert("Credits must be a non-negative number."); return; }
    setSaving(ruleId);
    try {
      await homeServicesFinanceApi.updateChargeConfig(ruleId, Math.round(value));
      config.refetch();
      setEditing(e => { const n = { ...e }; delete n[ruleId]; return n; });
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to update charge config.");
    } finally {
      setSaving(null);
    }
  }

  return (
    <Card padding={16}>
      <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px" }}>Provider Completion Charge Config</h3>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
        Credits deducted from a provider&apos;s balance per completed job, by service/job type. This amount
        varies by service — edit and save per row. Changes apply to jobs completed after the change; already-posted
        charges are never retroactively edited.
      </p>
      <DataTable
        loading={config.loading}
        rows={(config.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No pricing rules found."
        columns={[
          { key: "master_service_name", label: "Service", render: v => v ? String(v) : "—" },
          { key: "job_type", label: "Job Type" },
          { key: "rule_name", label: "Rule", render: v => v ? String(v) : "—" },
          { key: "is_active", label: "Active", render: v => v ? <Badge variant="success">Active</Badge> : <Badge>Inactive</Badge> },
          {
            key: "completed_job_deduction_credits", label: "Completion Charge (credits)",
            render: (v, row) => {
              const ruleId = String((row as Record<string, unknown>).rule_id);
              const current = editing[ruleId] ?? String(v);
              const dirty = editing[ruleId] !== undefined && editing[ruleId] !== String(v);
              return (
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <input
                    type="number" min={0} value={current}
                    onChange={e => setEditing(prev => ({ ...prev, [ruleId]: e.target.value }))}
                    style={{ width: 80, padding: "4px 6px", fontSize: 12, background: "var(--bg-secondary)",
                             border: "1px solid var(--border)", borderRadius: 4, color: "var(--text-primary)" }}
                  />
                  {dirty && (
                    <Btn variant="primary" onClick={() => save(ruleId)} disabled={saving === ruleId}>
                      {saving === ruleId ? "Saving…" : "Save"}
                    </Btn>
                  )}
                </div>
              );
            },
          },
        ]}
      />
    </Card>
  );
}
function ProviderChargeDetail({ chargeRef }: { chargeRef: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getProviderChargeDetail(chargeRef), [chargeRef]));
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
// ServiceOS to purchase credits) use money().

function units(v: unknown): string {
  const n = Number(v ?? 0);
  return `${n.toLocaleString("en-IN")} credits`;
}

const CREDIT_SUBTABS = ["accounts", "topups", "packages", "ledger", "adjustments"] as const;
type CreditSubTab = typeof CREDIT_SUBTABS[number];

function CreditsTab() {
  const [subTab, setSubTab] = useState<CreditSubTab>("accounts");
  const [selectedTopup, setSelectedTopup] = useState<string | null>(null);
  const [selectedLedgerEntry, setSelectedLedgerEntry] = useState<string | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<Record<string, unknown> | null>(null);

  const accountsSummary = useApi(useCallback(
    () => homeServicesFinanceApi.listCreditAccounts({ pageSize: 1000 }), []));
  const topupsAll = useApi(useCallback(() => homeServicesFinanceApi.listTopups({ pageSize: 1000 }), []));

  const accts = (accountsSummary.data?.items ?? []) as unknown as Record<string, unknown>[];
  const lowBalanceCount = accts.filter(a => a.low_balance).length;
  const tops = (topupsAll.data?.items ?? []) as unknown as Record<string, unknown>[];
  const pendingTopups = tops.filter(t => !["credited", "failed", "cancelled", "refunded"].includes(String(t.payment_status))).length;
  const failedTopups = tops.filter(t => t.payment_status === "failed").length;
  const creditsPurchased = tops.reduce((s, t) => s + Number(t.credits_purchased ?? 0), 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Credit units are not a cash wallet.</p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <SummaryCard label="Providers" value={accts.length} />
        <SummaryCard label="Low-Balance Providers" value={lowBalanceCount} tone={lowBalanceCount > 0 ? "warning" : undefined} onClick={() => setSubTab("accounts")} />
        <SummaryCard label="Credits Purchased" value={units(creditsPurchased)} onClick={() => setSubTab("topups")} />
        <SummaryCard label="Pending Top-ups" value={pendingTopups} tone={pendingTopups > 0 ? "warning" : undefined} onClick={() => setSubTab("topups")} />
        <SummaryCard label="Failed Top-ups" value={failedTopups} tone={failedTopups > 0 ? "danger" : undefined} onClick={() => setSubTab("topups")} />
      </div>

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)" }}>
        {([
          ["accounts", "Credit Accounts"], ["topups", "Top-up Orders"], ["packages", "Top-up Plans"],
          ["ledger", "Credit Ledger"], ["adjustments", "Adjustments"],
        ] as [CreditSubTab, string][]).map(([key, label]) => (
          <button key={key} onClick={() => setSubTab(key)}
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
      {subTab === "ledger" && <CreditLedgerView onSelect={setSelectedLedgerEntry} />}
      {subTab === "adjustments" && <AdjustmentsView onCreated={() => accountsSummary.refetch()} />}

      <Modal open={!!selectedTopup} onClose={() => setSelectedTopup(null)} title="Top-up Order Detail" size="lg">
        {selectedTopup && <TopupDetail topupId={selectedTopup} onChanged={() => topupsAll.refetch()} />}
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
  const [lowOnly, setLowOnly] = useState(false);
  const accounts = useApi(useCallback(
    () => homeServicesFinanceApi.listCreditAccounts({ q: q || undefined, lowBalanceOnly: lowOnly, pageSize: 100 }),
    [q, lowOnly]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 10 }}>
        <div style={{ flex: 1, maxWidth: 320 }}><Input placeholder="Search provider or account ID..." value={q} onChange={setQ} /></div>
        <Btn variant={lowOnly ? "primary" : "ghost"} onClick={() => setLowOnly(v => !v)}>Low balance only</Btn>
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Scoped to Home Services. Business Vertical is fixed and cannot be changed here.</p>
      <DataTable
        loading={accounts.loading}
        rows={(accounts.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No Home Services credit accounts found."
        onRowClick={row => onSelect(row as Record<string, unknown>)}
        columns={[
          { key: "tenant_name", label: "Provider" },
          { key: "credit_balance", label: "Available Credits", render: v => units(v) },
          { key: "reserved_credits", label: "Reserved Credits", render: () => units(0) },
          { key: "pending_recoveries", label: "Pending Recoveries", render: () => "—" },
          { key: "low_balance_threshold", label: "Low-Balance Threshold", render: v => units(v) },
          { key: "low_balance", label: "Credit Status", render: (_v, row) => {
            const s = creditAccountStatus(row as Record<string, unknown>);
            return <Badge variant={s.variant}>{s.label}</Badge>;
          } },
        ]}
      />
    </div>
  );
}

function CreditAccountDetail({ account }: { account: Record<string, unknown> }) {
  const ledger = useApi(useCallback(
    () => homeServicesFinanceApi.listCreditLedger({ tenantId: String(account.tenant_id), pageSize: 20 }),
    [account.tenant_id]));
  const s = creditAccountStatus(account);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <SummaryCard label="Available Credits" value={units(account.credit_balance)} />
        <SummaryCard label="Reserved Credits" value={units(0)} />
        <SummaryCard label="Low-Balance Threshold" value={units(account.low_balance_threshold)} />
        <SummaryCard label="Credit Status" value={s.label} tone={s.variant === "danger" || s.variant === "warning" ? s.variant : undefined} />
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        Reservations are not part of the canonical Home Services deduction flow today -- charges post directly
        (idempotent per job/event), so no Reserved-credit workflow applies here yet.
      </p>
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
  const topups = useApi(useCallback(() => homeServicesFinanceApi.listTopups({ paymentStatus: status, pageSize: 100 }), [status]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {[undefined, "initiated", "paid_pending_credit", "credited", "failed", "refunded"].map(s => (
          <Btn key={s ?? "all"} variant={status === s ? "primary" : "ghost"} onClick={() => setStatus(s)}>{s ?? "All"}</Btn>
        ))}
      </div>
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
    </div>
  );
}
function TopupDetail({ topupId, onChanged }: { topupId: string; onChanged: () => void }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getTopupDetail(topupId), [topupId]));
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [showRefund, setShowRefund] = useState(false);
  const retryAction = useAction((id: string) => homeServicesFinanceApi.retryTopupCredit(id));
  const refundAction = useAction((id: string, amount: number, reason: string) => homeServicesFinanceApi.refundTopup(id, amount, reason));

  if (detail.loading) return <Skeleton height={120} />;
  const d = detail.data as Record<string, unknown> | undefined;
  const status = d?.payment_status as string | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <KeyValueGrid data={detail.data} />
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        A top-up is a provider payment to ServiceOS to purchase platform Usage Credits -- distinct from a customer
        paying the provider for a service job.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {(status === "paid_pending_credit" || status === "failed") && (
          <Btn variant="secondary" loading={retryAction.loading}
            onClick={async () => { if (await retryAction.execute(topupId)) { detail.refetch(); onChanged(); } }}>
            Retry Credit Posting
          </Btn>
        )}
        {status === "credited" && (
          <Btn variant="ghost" onClick={() => setShowRefund(v => !v)}>Refund</Btn>
        )}
      </div>
      {showRefund && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, background: "var(--surface-sunken)", borderRadius: 8 }}>
          <Input placeholder="Amount" value={refundAmount} onChange={setRefundAmount} />
          <Input placeholder="Reason" value={refundReason} onChange={setRefundReason} />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="primary" loading={refundAction.loading} disabled={!refundAmount.trim()}
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
];

function CreditLedgerView({ onSelect }: { onSelect: (id: string) => void }) {
  const [eventType, setEventType] = useState<string | undefined>(undefined);
  const ledger = useApi(useCallback(() => homeServicesFinanceApi.listCreditLedger({ eventType, pageSize: 100 }), [eventType]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Btn variant={!eventType ? "primary" : "ghost"} onClick={() => setEventType(undefined)}>All</Btn>
        {LEDGER_EVENT_TYPES.map(e => (
          <Btn key={e} variant={eventType === e ? "primary" : "ghost"} onClick={() => setEventType(e)}>{e.toUpperCase()}</Btn>
        ))}
      </div>
      <DataTable
        loading={ledger.loading}
        rows={(ledger.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No ledger entries found for this filter."
        onRowClick={row => onSelect(String((row as Record<string, unknown>).id))}
        columns={[
          { key: "created_at", label: "Timestamp", render: v => dt(v as string) },
          { key: "id", label: "Entry ID", render: v => <span style={{ fontFamily: "monospace", fontSize: 11 }}>{String(v).slice(0, 8)}</span> },
          { key: "event_type", label: "Entry Type", render: v => <span style={{ fontFamily: "monospace", fontSize: 11 }}>{String(v).toUpperCase()}</span> },
          { key: "tenant_name", label: "Provider" },
          { key: "direction", label: "Direction", render: v => <Badge variant={v === "credit" ? "success" : "default"}>{String(v)}</Badge> },
          { key: "credit_delta", label: "Credit Units", render: v => (Number(v) >= 0 ? "+" : "") + units(v) },
          { key: "balance_after", label: "Balance After", render: v => units(v) },
          { key: "source_type", label: "Source", render: v => v ? String(v) : "—" },
        ]}
      />
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        The ledger is append-only. No code path exists to edit or delete a posted entry.
      </p>
    </div>
  );
}
function LedgerEntryDetail({ entryId }: { entryId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getLedgerEntryDetail(entryId), [entryId]));
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
  const [direction, setDirection] = useState<"credit" | "debit">("credit");
  const [creditUnits, setCreditUnits] = useState("");
  const [reasonCode, setReasonCode] = useState(ADJUSTMENT_REASONS[0]);
  const [detailedReason, setDetailedReason] = useState("");
  const action = useAction((body: Parameters<typeof homeServicesFinanceApi.createAdjustment>[0]) =>
    homeServicesFinanceApi.createAdjustment(body));
  const ledger = useApi(useCallback(() => homeServicesFinanceApi.listCreditLedger({ eventType: "manual_credit_adjustment", pageSize: 50 }), []));

  async function submit() {
    if (!tenantId.trim() || !creditUnits.trim() || !detailedReason.trim()) return;
    const r = await action.execute({ tenantId: tenantId.trim(), direction, creditUnits, reasonCode, detailedReason });
    if (r) { setTenantId(""); setCreditUnits(""); setDetailedReason(""); ledger.refetch(); onCreated(); }
  }

  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <Card style={{ padding: 16, flex: "1 1 320px" }}>
        <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>New manual adjustment</p>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
          Requires elevated permission. Creates an immutable ledger entry -- the balance is never edited directly.
        </p>
        <Input placeholder="Provider (tenant ID)" value={tenantId} onChange={setTenantId} />
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
        {action.error && <p style={{ fontSize: 11, color: "var(--danger-text)", marginTop: 6 }}>{action.error}</p>}
        <Btn variant="primary" onClick={submit} disabled={action.loading} style={{ marginTop: 10 }}>
          {action.loading ? "Submitting…" : "Submit Adjustment"}
        </Btn>
      </Card>
      <div style={{ flex: "2 1 420px" }}>
        <h4 style={{ fontSize: 12, fontWeight: 700, margin: "0 0 8px", textTransform: "uppercase", color: "var(--text-tertiary)" }}>Recent adjustments</h4>
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
      </div>
    </div>
  );
}

// ── Security Deposits ────────────────────────────────────────────────────────

function SecurityDepositsTab() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useApi(useCallback(() => homeServicesFinanceApi.getDepositsSummary(), []));
  const deposits = useApi(useCallback(
    () => homeServicesFinanceApi.listDeposits({ q: q || undefined, page, pageSize: 20 }),
    [q, page]));
  const s = summary.data as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <SummaryCard label="Total Held" value={money((s?.total_held as string) ?? 0)} />
        <SummaryCard label="Active" value={(s?.active_held_deposits as number) ?? 0} />
        <SummaryCard label="Pending" value={(s?.pending_deposits as number) ?? 0} />
        <SummaryCard label="Return Requests" value={(s?.refund_pending as number) ?? 0} tone="warning" />
        <SummaryCard label="Refunded" value={(s?.refunded as number) ?? 0} />
        <SummaryCard label="Risk Cases" value={(s?.deposit_risk_cases as number) ?? 0} tone={(s?.deposit_risk_cases as number) > 0 ? "danger" : undefined} />
      </div>
      <div style={{ maxWidth: 320 }}><Input placeholder="Search tenant..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
      <DataTable
        loading={deposits.loading}
        rows={(deposits.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No security deposits found for Home Services."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).deposit_id))}
        columns={[
          { key: "tenant_name", label: "Provider" },
          { key: "required_amount", label: "Required", render: v => money(v as number) },
          { key: "current_balance", label: "Current Balance", render: v => money(v as number) },
          { key: "status", label: "Status", render: v => <Badge variant={v === "paid" ? "success" : v === "refund_requested" ? "warning" : "default"}>{String(v)}</Badge> },
          { key: "created_at", label: "Collected", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={deposits.data?.pagination?.total ?? 0} pageSize={20} onPage={setPage} />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Security Deposit Detail" size="lg">
        {selected && <DepositDetail depositId={selected} onChanged={() => { deposits.refetch(); summary.refetch(); }} />}
      </Modal>
    </div>
  );
}
type DepositActionKind = "approve" | "reject" | "record-offline" | "refund" | "adjust";

function DepositDetail({ depositId, onChanged }: { depositId: string; onChanged: () => void }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getDepositDetail(depositId), [depositId]));
  const [openAction, setOpenAction] = useState<DepositActionKind | null>(null);
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [reason, setReason] = useState("");

  const approveAction = useAction((id: string, notes?: string) => homeServicesFinanceApi.approveDeposit(id, notes));
  const rejectAction = useAction((id: string, r: string) => homeServicesFinanceApi.rejectDeposit(id, r));
  const recordOfflineAction = useAction((id: string, amt: number, ref?: string, notes?: string) =>
    homeServicesFinanceApi.recordOfflineDeposit(id, amt, ref, notes));
  const refundAction = useAction((id: string, amt: number, r: string) => homeServicesFinanceApi.refundDeposit(id, amt, r));
  const adjustAction = useAction((id: string, amt: number, r: string) => homeServicesFinanceApi.adjustDeposit(id, amt, r));

  const busy = approveAction.loading || rejectAction.loading || recordOfflineAction.loading || refundAction.loading || adjustAction.loading;
  const error = approveAction.error || rejectAction.error || recordOfflineAction.error || refundAction.error || adjustAction.error;

  function reset() { setOpenAction(null); setAmount(""); setReference(""); setReason(""); }
  function afterSuccess() { reset(); detail.refetch(); onChanged(); }

  if (detail.loading) return <Skeleton height={160} />;
  const d = detail.data as Record<string, unknown> | undefined;
  const status = d?.status as string | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <KeyValueGrid data={detail.data} />
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        A deposit return is recorded here as a SECURITY_DEPOSIT_RETURN ledger entry — never a provider payout.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {status === "pending" && (
          <>
            <Btn variant="primary" loading={approveAction.loading}
              onClick={async () => { if (await approveAction.execute(depositId, undefined)) afterSuccess(); }}>Approve</Btn>
            <Btn variant="ghost" onClick={() => setOpenAction("reject")}>Reject</Btn>
          </>
        )}
        {(status === "unpaid" || status === "pending") && (
          <Btn variant="secondary" onClick={() => setOpenAction("record-offline")}>Record Offline Payment</Btn>
        )}
        {(status === "paid" || status === "refund_requested") && (
          <Btn variant="ghost" onClick={() => setOpenAction("refund")}>Refund</Btn>
        )}
        <Btn variant="ghost" onClick={() => setOpenAction("adjust")}>Adjust / Forfeit</Btn>
      </div>

      {openAction === "reject" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, background: "var(--surface-sunken)", borderRadius: 8 }}>
          <Input placeholder="Rejection reason" value={reason} onChange={setReason} />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="primary" loading={rejectAction.loading} disabled={!reason.trim()}
              onClick={async () => { if (await rejectAction.execute(depositId, reason.trim())) afterSuccess(); }}>Confirm Reject</Btn>
            <Btn variant="ghost" onClick={reset}>Cancel</Btn>
          </div>
        </div>
      )}
      {openAction === "record-offline" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, background: "var(--surface-sunken)", borderRadius: 8 }}>
          <Input placeholder="Amount received" value={amount} onChange={setAmount} />
          <Input placeholder="Reference (e.g. bank transfer ref)" value={reference} onChange={setReference} />
          <Input placeholder="Notes (optional)" value={reason} onChange={setReason} />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="primary" loading={recordOfflineAction.loading} disabled={!amount.trim()}
              onClick={async () => { if (await recordOfflineAction.execute(depositId, Number(amount), reference, reason)) afterSuccess(); }}>
              Confirm Payment
            </Btn>
            <Btn variant="ghost" onClick={reset}>Cancel</Btn>
          </div>
        </div>
      )}
      {openAction === "refund" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, background: "var(--surface-sunken)", borderRadius: 8 }}>
          <Input placeholder="Refund amount" value={amount} onChange={setAmount} />
          <Input placeholder="Reason" value={reason} onChange={setReason} />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="primary" loading={refundAction.loading} disabled={!amount.trim() || !reason.trim()}
              onClick={async () => { if (await refundAction.execute(depositId, Number(amount), reason.trim())) afterSuccess(); }}>
              Confirm Refund
            </Btn>
            <Btn variant="ghost" onClick={reset}>Cancel</Btn>
          </div>
        </div>
      )}
      {openAction === "adjust" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, background: "var(--surface-sunken)", borderRadius: 8 }}>
          <Input placeholder="Adjustment amount" value={amount} onChange={setAmount} />
          <Input placeholder="Reason" value={reason} onChange={setReason} />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="primary" loading={adjustAction.loading} disabled={!amount.trim() || !reason.trim()}
              onClick={async () => { if (await adjustAction.execute(depositId, Number(amount), reason.trim())) afterSuccess(); }}>
              Confirm Adjustment
            </Btn>
            <Btn variant="ghost" onClick={reset}>Cancel</Btn>
          </div>
        </div>
      )}
      {error && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: 0 }}>{error}</p>}
    </div>
  );
}

// ── Invoices ──────────────────────────────────────────────────────────────────

function InvoicesTab() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useApi(useCallback(() => homeServicesFinanceApi.getInvoicesSummary(), []));
  const invoices = useApi(useCallback(
    () => homeServicesFinanceApi.listInvoices({ q: q || undefined, page, pageSize: 20 }),
    [q, page]));
  const s = summary.data as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <SummaryCard label="Issued" value={(s?.issued as number) ?? 0} />
        <SummaryCard label="Paid" value={(s?.paid as number) ?? 0} />
        <SummaryCard label="Outstanding" value={(s?.outstanding as number) ?? 0} tone="warning" />
        <SummaryCard label="Overdue" value={(s?.overdue as number) ?? 0} tone="danger" />
        <SummaryCard label="Cancelled" value={(s?.cancelled as number) ?? 0} />
      </div>
      <div style={{ maxWidth: 320 }}><Input placeholder="Search invoice #..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
      <DataTable
        loading={invoices.loading}
        rows={(invoices.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No service invoices found."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).id))}
        columns={[
          { key: "invoice_number", label: "Invoice #" },
          { key: "tenant_name", label: "Tenant" },
          { key: "total_amount", label: "Total", render: v => money(v as string) },
          { key: "payment_status", label: "Payment", render: v => <Badge variant={v === "paid" ? "success" : v === "overdue" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "status", label: "Status", render: v => <Badge>{String(v)}</Badge> },
          { key: "issued_at", label: "Issued", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={invoices.data?.total ?? 0} pageSize={20} onPage={setPage} />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Invoice Detail" size="lg">
        {selected && <InvoiceDetail invoiceId={selected} />}
      </Modal>
    </div>
  );
}
function InvoiceDetail({ invoiceId }: { invoiceId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getInvoiceDetail(invoiceId), [invoiceId]));
  if (detail.loading) return <Skeleton height={160} />;
  return <KeyValueGrid data={detail.data} />;
}

// ── Customer Refunds ─────────────────────────────────────────────────────────

function CustomerRefundsTab() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useApi(useCallback(() => homeServicesFinanceApi.getRefundsSummary(), []));
  const refunds = useApi(useCallback(
    () => homeServicesFinanceApi.listRefunds({ q: q || undefined, page, pageSize: 20 }),
    [q, page]));
  const s = summary.data as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <SummaryCard label="Requested" value={(s?.requested as number) ?? 0} />
        <SummaryCard label="Under Review" value={(s?.under_review as number) ?? 0} tone="warning" />
        <SummaryCard label="Approved" value={(s?.approved as number) ?? 0} />
        <SummaryCard label="Recorded by Provider" value={(s?.recorded as number) ?? 0} />
        <SummaryCard label="Verified" value={(s?.verified as number) ?? 0} />
        <SummaryCard label="Rejected" value={(s?.rejected as number) ?? 0} tone="danger" />
      </div>
      <div style={{ maxWidth: 320 }}><Input placeholder="Search refund #..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
      <DataTable
        loading={refunds.loading}
        rows={(refunds.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No customer refunds found for Home Services."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).id))}
        columns={[
          { key: "refund_number", label: "Refund #" },
          { key: "tenant_name", label: "Provider" },
          { key: "requested_amount", label: "Requested", render: v => money(v as string) },
          { key: "approved_amount", label: "Approved", render: v => v ? money(v as string) : "—" },
          { key: "status", label: "Status", render: v => <Badge variant={v === "verified" ? "success" : v === "rejected" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "created_at", label: "Requested At", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={refunds.data?.total ?? 0} pageSize={20} onPage={setPage} />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Customer Refund Detail" size="lg">
        {selected && <RefundDetail refundId={selected} />}
      </Modal>
    </div>
  );
}
function RefundDetail({ refundId }: { refundId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getRefundDetail(refundId), [refundId]));
  const [busy, setBusy] = useState<string | null>(null);

  async function run(action: string, fn: () => Promise<unknown>) {
    setBusy(action);
    try { await fn(); detail.refetch(); }
    catch (e) { alert(e instanceof Error ? e.message : `Failed to ${action}.`); }
    finally { setBusy(null); }
  }

  if (detail.loading) return <Skeleton height={160} />;
  const status = (detail.data as Record<string, unknown> | undefined)?.status as string | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <KeyValueGrid data={detail.data} />
      <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
        The provider collected this payment directly, so the provider returns the money — admin only
        records, reviews and confirms the evidence. This is never a ServiceOS cash refund.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {status === "requested" && (
          <>
            <Btn variant="primary" disabled={busy === "approve"}
              onClick={() => run("approve", () => homeServicesFinanceApi.approveRefund(refundId))}>
              {busy === "approve" ? "Approving…" : "Approve"}
            </Btn>
            <Btn variant="ghost" disabled={busy === "reject"}
              onClick={() => { const reason = prompt("Rejection reason:"); if (reason) run("reject", () => homeServicesFinanceApi.rejectRefund(refundId, reason)); }}>
              {busy === "reject" ? "Rejecting…" : "Reject"}
            </Btn>
          </>
        )}
        {status === "approved" && (
          <Btn variant="primary" disabled={busy === "record"}
            onClick={() => {
              const amount = prompt("Amount the provider actually refunded:");
              if (amount) run("record", () => homeServicesFinanceApi.recordRefund(refundId, amount));
            }}>
            {busy === "record" ? "Recording…" : "Record Provider Refund"}
          </Btn>
        )}
        {status === "recorded" && (
          <Btn variant="primary" disabled={busy === "verify"}
            onClick={() => run("verify", () => homeServicesFinanceApi.verifyProviderRefund(refundId))}>
            {busy === "verify" ? "Verifying…" : "Verify with Customer Confirmation"}
          </Btn>
        )}
      </div>
    </div>
  );
}

// ── Warranty Claims ──────────────────────────────────────────────────────────

function WarrantyClaimsTab() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useApi(useCallback(() => homeServicesFinanceApi.getWarrantyClaimsSummary(), []));
  const claims = useApi(useCallback(
    () => homeServicesFinanceApi.listWarrantyClaims({ q: q || undefined, page, pageSize: 20 }),
    [q, page]));
  const s = summary.data as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <SummaryCard label="Pending Review" value={(s?.pending_review as number) ?? 0} tone="warning" />
        <SummaryCard label="Investigating" value={(s?.investigation_ongoing as number) ?? 0} />
        <SummaryCard label="Approved" value={(s?.approved_claims as number) ?? 0} />
        <SummaryCard label="Rejected" value={(s?.rejected_claims as number) ?? 0} />
        <SummaryCard label="Settled Value" value={money((s?.settled_value as string) ?? 0)} />
      </div>
      <div style={{ maxWidth: 320 }}><Input placeholder="Search job or provider..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
      <DataTable
        loading={claims.loading}
        rows={(claims.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No warranty claims found for Home Services."
        onRowClick={row => setSelected(String((row as Record<string, unknown>).claim_id))}
        columns={[
          { key: "tenant_name", label: "Provider" },
          { key: "job_id", label: "Job", render: v => v ? String(v).slice(0, 8) : "—" },
          { key: "claim_type", label: "Type" },
          { key: "amount_requested", label: "Exposure", render: v => money(v as number) },
          { key: "status", label: "Status", render: v => <Badge variant={v === "approved" ? "success" : v === "rejected" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "created_at", label: "Created", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={claims.data?.total ?? 0} pageSize={20} onPage={setPage} />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Warranty Claim Detail" size="lg">
        {selected && <WarrantyClaimDetail claimId={selected} />}
      </Modal>
    </div>
  );
}
function WarrantyClaimDetail({ claimId }: { claimId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getWarrantyClaimDetail(claimId), [claimId]));
  if (detail.loading) return <Skeleton height={160} />;
  return <KeyValueGrid data={detail.data} />;
}

// ── Financial Events ─────────────────────────────────────────────────────────

function FinancialEventsTab() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useApi(useCallback(() => homeServicesFinanceApi.getFinancialEventsSummary(), []));
  const events = useApi(useCallback(
    () => homeServicesFinanceApi.listFinancialEvents({ q: q || undefined, page, pageSize: 30 }),
    [q, page]));
  const s = summary.data as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <SummaryCard label="Events Today" value={(s?.events_today as number) ?? 0} />
        <SummaryCard label="Immutable" value={s?.immutable ? "Yes" : "—"} />
      </div>
      <div style={{ maxWidth: 320 }}><Input placeholder="Search tenant or request ID..." value={q} onChange={v => { setQ(v); setPage(1); }} /></div>
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
      <Pagination page={page} total={events.data?.total ?? 0} pageSize={30} onPage={setPage} />
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Financial Event Detail" size="lg">
        {selected && <FinancialEventDetail eventId={selected} />}
      </Modal>
    </div>
  );
}
function FinancialEventDetail({ eventId }: { eventId: string }) {
  const detail = useApi(useCallback(() => homeServicesFinanceApi.getFinancialEventDetail(eventId), [eventId]));
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
  const audit = useApi(useCallback(() => homeServicesFinanceApi.listAudit(1, 50), []));
  return (
    <DataTable
      loading={audit.loading}
      rows={(audit.data?.items ?? []) as unknown as Record<string, unknown>[]}
      emptyText="No audit events recorded yet — run a reconciliation or export to generate one."
      columns={[
        { key: "operation", label: "Operation" },
        { key: "actor_role", label: "Actor" },
        { key: "after", label: "Details", render: v => <span style={{ fontFamily: "monospace", fontSize: 11 }}>{JSON.stringify(v)}</span> },
        { key: "created_at", label: "When", render: v => dt(v as string) },
      ]}
    />
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

// ── Provider Wallets (ported from the standalone /admin/provider-wallets
// page so this workspace covers every Home Services money surface) ─────────

function WalletsTab() {
  const [creditTarget, setCreditTarget] = useState<string | null>(null);
  const [creditAmount, setCreditAmount] = useState("");
  const [creditReason, setCreditReason] = useState("");

  const { data, loading, refetch } = useApi(useCallback(() => adminWalletApi.list(), []));
  const wallets: WalletRecord[] = (Array.isArray(data) ? data : []) as WalletRecord[];

  const creditAction = useAction(useCallback(
    (tenantId: string, amount: number, reason: string) => adminWalletApi.credit(tenantId, { amount, reason }),
    []));

  const handleCredit = async () => {
    if (!creditTarget) return;
    const result = await creditAction.execute(creditTarget, Number(creditAmount), creditReason || "Admin credit");
    if (result) {
      setCreditTarget(null); setCreditAmount(""); setCreditReason("");
      refetch();
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Credit balances for all provider tenants.</p>
        <Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[0, 1, 2].map(i => <Skeleton key={i} height={80} />)}
        </div>
      ) : wallets.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <Wallet size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No provider wallets found.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {wallets.map((w: WalletRecord) => (
            <Card key={w.tenant_id} padding={16}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)", margin: 0 }}>
                    Tenant: {w.tenant_id?.slice(0, 12)}
                  </p>
                  <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 12, flexWrap: "wrap" }}>
                    <span><strong>Balance:</strong> {w.current_balance}</span>
                    <span><strong>Reserved:</strong> {w.reserved_balance}</span>
                    <span><strong>In:</strong> {w.total_purchased}</span>
                    <span><strong>Out:</strong> {w.total_deducted}</span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <Badge variant={w.is_active ? "success" : "danger"}>{w.is_active ? "Active" : "Inactive"}</Badge>
                  <Btn size="sm" onClick={() => setCreditTarget(w.tenant_id)}>
                    <PlusCircle size={12} /> Add Credit
                  </Btn>
                </div>
              </div>

              {creditTarget === w.tenant_id && (
                <div style={{ marginTop: 12, padding: 12, background: "var(--surface-sunken)",
                  borderRadius: "var(--radius-md)", display: "flex", flexDirection: "column", gap: 8 }}>
                  <Input placeholder="Amount" value={creditAmount} onChange={setCreditAmount} />
                  <Input placeholder="Reason (optional)" value={creditReason} onChange={setCreditReason} />
                  <div style={{ display: "flex", gap: 8 }}>
                    <Btn size="sm" onClick={handleCredit} loading={creditAction.loading}>Confirm Credit</Btn>
                    <Btn size="sm" variant="ghost" onClick={() => setCreditTarget(null)}>Cancel</Btn>
                  </div>
                  {creditAction.error && <p style={{ color: "var(--danger-text)", fontSize: 11, margin: 0 }}>{creditAction.error}</p>}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
