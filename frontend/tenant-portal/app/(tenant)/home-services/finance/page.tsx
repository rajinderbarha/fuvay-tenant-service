"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Home Services Finance Hub — TENANT-HS-FINANCE-HUB-01.
 *
 * Category-scoped consolidation of: finance readiness, usage-credit wallet,
 * credit purchase/top-ups, completed-job deductions, credit reversals,
 * technician seats, published finance policy,
 * financial activity and the reconciliation queue.
 *
 * Renders ONLY server-computed projections from
 * /v1/tenant/home-services/finance/* (app/engines/finance_hub/
 * tenant_hs_finance_router.py). This page never derives a balance, never
 * sums separate ledgers into one figure, and
 * never turns a failed fetch into a fake zero — a failed projection shows a
 * real error state instead.
 *
 * Direct customer payments stay on their own route
 * (/home-services/direct-payments); only a summary + link appears here.
 * There is deliberately NO payouts/settlement surface anywhere on this page —
 * for Home Services the customer pays the provider directly and ServiceOS
 * never holds or settles job funds.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Wallet, Shield, Receipt, FileText, LayoutDashboard, AlertTriangle,
  CheckCircle2, RefreshCw, Download, Eye, CreditCard, TrendingDown,
  ArrowUpRight, Clock, XCircle, Info, ExternalLink, ListChecks, Ban,
} from "lucide-react";
import { Card, Badge, Btn, Skeleton, KpiGrid, SummaryCard, Pagination } from "../../../../components/shared/ui";
import {
  homeServicesFinanceApi, ServiceOSError,
  type HsFinanceOverview, type HsFinanceTxnRow, type HsFinanceTxnPage,
  type HsCreditPackage, type HsTopupOrder,
  type HsFinanceReadinessCheck, type HsLiabilityHold, type HsCommissionRates,
} from "../../../../lib/api";
import { useRazorpayCheckout } from "../../../../hooks/useRazorpayCheckout";

/* ── tabs ─────────────────────────────────────────────────────────────────── */

const TABS = [
  { key: "overview",         label: "Overview",              icon: LayoutDashboard },
  { key: "usage-credits",    label: "Usage Credits",         icon: Wallet },
  { key: "topups",           label: "Top-ups & Transactions",icon: Receipt },
  { key: "policy",           label: "Policy & Audit",        icon: FileText },
] as const;
type TabKey = typeof TABS[number]["key"];

const LEDGER_VARIANT: Record<string, "default" | "info" | "warning" | "muted"> = {
  usage_credits: "default",
  security_deposit: "info",
  cash_tax: "warning",
  adjustment: "muted",
};

/* ── formatting helpers (display only — never arithmetic) ─────────────────── */

/** Formats a server-sent decimal STRING. Returns the em dash for null so a
 * missing value can never be mistaken for zero. */
function money(v: string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function moneyCompact(v: string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
function dt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}
function statusVariant(s: string): "success" | "warning" | "danger" | "muted" | "info" {
  if (["posted", "credited", "refunded", "confirmed"].includes(s)) return "success";
  if (["failed", "rejected", "cancelled", "mismatch", "disputed"].includes(s)) return "danger";
  if (["pending", "initiated", "paid_pending_credit", "processing", "info_requested"].includes(s)) return "warning";
  if (["submitted", "eligibility_review", "liability_review", "admin_decision"].includes(s)) return "info";
  return "muted";
}
function humanStatus(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

/* ── small presentational primitives (same visual language as dispatch) ──── */

function KpiCard({ label, value, sub, icon, variant = "default" }: {
  label: string; value: React.ReactNode; sub?: string;
  icon: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "info";
}) {
  return <SummaryCard label={label} value={value} sub={sub} icon={icon}
    tone={variant === "default" ? undefined : variant} />;
}

function SectionTitle({ icon, title, subtitle, actions }: {
  icon?: React.ReactNode; title: string; subtitle?: string; actions?: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between",
      gap: 12, marginBottom: 14, flexWrap: "wrap" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9, minWidth: 0 }}>
        {icon && <span style={{ color: "var(--accent)", display: "flex" }}>{icon}</span>}
        <div>
          <h2 style={{ fontSize: 14.5, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{title}</h2>
          {subtitle && <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "3px 0 0" }}>{subtitle}</p>}
        </div>
      </div>
      {actions && <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{actions}</div>}
    </div>
  );
}

function Row({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between",
      gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>
        {label}
        {hint && <span style={{ color: "var(--text-tertiary)", fontSize: 11.5 }}> · {hint}</span>}
      </span>
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", textAlign: "right" }}>{value}</span>
    </div>
  );
}

function ErrorBanner({ code, message, resolution }: { code?: string; message: string; resolution?: string }) {
  const disabled = code === "VERTICAL_DISABLED" || code === "TENANT_VERTICAL_NOT_ACTIVE";
  return (
    <div role="alert" style={{ display: "flex", gap: 9, padding: "12px 14px", borderRadius: 12,
      background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
      color: "var(--danger-text)", fontSize: 13, marginTop: 16 }}>
      <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
      <div>
        <div style={{ fontWeight: 600 }}>
          {disabled
            ? "Home Services is not active for your account yet — the Finance Hub unlocks once your enrollment is approved."
            : message}
        </div>
        {!disabled && resolution && (
          <div style={{ marginTop: 4, opacity: 0.85, fontSize: 12.5 }}>{resolution}</div>
        )}
        {!disabled && code && (
          <div style={{ marginTop: 4, fontSize: 11, opacity: 0.7, fontFamily: "monospace" }}>{code}</div>
        )}
      </div>
    </div>
  );
}

function EmptyRow({ text }: { text: string }) {
  return (
    <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", textAlign: "center", padding: "28px 12px", margin: 0 }}>
      {text}
    </p>
  );
}

/* ── readiness checklist (spec section 13) ───────────────────────────────── */

function ReadinessIcon({ state }: { state: HsFinanceReadinessCheck["state"] }) {
  if (state === "complete") return <CheckCircle2 size={15} style={{ color: "var(--success-text)" }} />;
  if (state === "blocked") return <XCircle size={15} style={{ color: "var(--danger-text)" }} />;
  if (state === "action_required") return <AlertTriangle size={15} style={{ color: "var(--warning-text)" }} />;
  return <Ban size={15} style={{ color: "var(--text-tertiary)" }} />;
}

function ReadinessCard({ data }: { data: HsFinanceOverview["readiness"] }) {
  const variant = data.status === "ready" ? "success" : data.status === "blocked" ? "danger" : "warning";
  return (
    <Card>
      <SectionTitle
        icon={<ListChecks size={16} />}
        title="Finance readiness"
        subtitle={`Computed server-side · ${dt(data.computed_at)}`}
        actions={<Badge variant={variant} size="lg" dot>{data.status_label}</Badge>}
      />
      <div style={{ display: "grid", gap: 2 }}>
        {data.checks.map(c => (
          <div key={c.code} style={{ display: "flex", gap: 9, alignItems: "flex-start",
            padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
            <span style={{ display: "flex", marginTop: 1 }}><ReadinessIcon state={c.state} /></span>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{c.label}</div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>{c.detail}</div>
            </div>
          </div>
        ))}
      </div>
      {data.blockers.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <p style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase",
            color: "var(--danger-text)", margin: "0 0 6px" }}>Blockers</p>
          {data.blockers.map(b => (
            <div key={b.code} style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
              borderRadius: 10, padding: "9px 11px", marginBottom: 6 }}>
              <div style={{ fontSize: 12.5, color: "var(--danger-text)", fontWeight: 600 }}>{b.message}</div>
              <div style={{ fontSize: 11.5, color: "var(--danger-text)", opacity: 0.85, marginTop: 2 }}>{b.resolution}</div>
            </div>
          ))}
        </div>
      )}
      {data.warnings.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <p style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase",
            color: "var(--warning-text)", margin: "0 0 6px" }}>Warnings</p>
          {data.warnings.map(b => (
            <div key={b.code} style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)",
              borderRadius: 10, padding: "9px 11px", marginBottom: 6 }}>
              <div style={{ fontSize: 12.5, color: "var(--warning-text)", fontWeight: 600 }}>{b.message}</div>
              <div style={{ fontSize: 11.5, color: "var(--warning-text)", opacity: 0.85, marginTop: 2 }}>{b.resolution}</div>
            </div>
          ))}
        </div>
      )}
      {data.blockers.length === 0 && data.warnings.length === 0 && (
        <p style={{ fontSize: 12.5, color: "var(--success-text)", margin: "12px 0 0" }}>
          No blockers or warnings. All finance requirements for Home Services are satisfied.
        </p>
      )}
    </Card>
  );
}

/* ── financial activity table (spec section 14) ──────────────────────────── */

/**
 * The only receipt endpoint is `/top-ups/{id}`, and the composed activity rows
 * carry a prefixed `row_id`: `cto:<uuid>` (top-up), `cto-gst:<uuid>` (its GST
 * half), `ucl:<uuid>` (usage-credit ledger) and `dep:<uuid>` (deposit
 * transaction). Only the first two map to something a receipt can be fetched
 * for. Returns null when the row has no reachable receipt, so the button is
 * not rendered at all rather than rendered dead.
 */
function topupIdFromRow(r: HsFinanceTxnRow): string | null {
  const id = String((r as { row_id?: string }).row_id ?? "");
  const m = /^cto(?:-gst)?:(.+)$/.exec(id);
  return m ? m[1] : null;
}

function ActivityTable({ page, compact, onReceipt }: {
  page: HsFinanceTxnPage; compact?: boolean; onReceipt?: (row: HsFinanceTxnRow) => void;
}) {
  if (page.items.length === 0) {
    return <EmptyRow text="No financial activity recorded yet for this workspace." />;
  }
  const cols = compact
    ? ["Date / time", "Ledger", "Event", "Debit", "Credit", "Credit balance", "Status"]
    : ["Date / time", "Reference", "Ledger", "Event", "Description", "Debit", "Credit",
       "Usage-credit balance", "Status", "Related", "Actions"];
  return (
    <div style={{ overflowX: "auto" }}>
      <TableSurface style={{ width: "100%", borderCollapse: "collapse", minWidth: compact ? 720 : 1180 }}>
        <thead>
          <tr>
            {cols.map(c => (
              <th key={c} style={{ textAlign: c.includes("Debit") || c.includes("Credit") || c.includes("balance") ? "right" : "left",
                fontSize: 10.5, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase",
                color: "var(--text-tertiary)", padding: "8px 10px", borderBottom: "1px solid var(--border)",
                whiteSpace: "nowrap" }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {page.items.map(r => (
            <tr key={r.row_id}>
              <td style={td()}>{dt(r.occurred_at)}</td>
              {!compact && (
                <td style={{ ...td(), fontFamily: "monospace", fontSize: 11, maxWidth: 190,
                  overflow: "hidden", textOverflow: "ellipsis" }}>{r.reference ?? "—"}</td>
              )}
              <td style={td()}>
                <Badge variant={LEDGER_VARIANT[r.ledger] ?? "muted"} size="sm">{r.ledger_label}</Badge>
              </td>
              <td style={{ ...td(), fontWeight: 600 }}>{r.event_label}</td>
              {!compact && (
                <td style={{ ...td(), color: "var(--text-secondary)", maxWidth: 300,
                  overflow: "hidden", textOverflow: "ellipsis" }} title={r.description}>{r.description}</td>
              )}
              <td style={{ ...td(), textAlign: "right", color: r.debit ? "var(--danger-text)" : "var(--text-tertiary)" }}>
                {r.debit ? money(r.debit) : "—"}
              </td>
              <td style={{ ...td(), textAlign: "right", color: r.credit ? "var(--success-text)" : "var(--text-tertiary)" }}>
                {r.credit ? money(r.credit) : "—"}
              </td>
              {/* Deposit / GST rows deliberately render "—" here. Never a combined balance. */}
              <td style={{ ...td(), textAlign: "right", fontWeight: 600 }}>
                {r.usage_credit_balance_after !== null ? money(r.usage_credit_balance_after) : "—"}
              </td>
              <td style={td()}>
                <Badge variant={statusVariant(r.status)} size="sm">{humanStatus(r.status)}</Badge>
              </td>
              {!compact && (
                <td style={{ ...td(), fontFamily: "monospace", fontSize: 10.5 }}>
                  {r.related_job_id
                    ? <Link href={`/jobs/${r.related_job_id}`} style={{ color: "var(--accent)" }}>
                        {r.related_job_id.slice(0, 8)}
                      </Link>
                    : (r.related_transaction_ref ? r.related_transaction_ref.slice(0, 14) : "—")}
                </td>
              )}
              {!compact && (
                <td style={td()}>
                  {/* `onReceipt` was an optional prop NO caller ever passed, so
                      every one of these buttons rendered, looked clickable and
                      did nothing. It is now wired, and only shown for rows that
                      resolve to a real top-up receipt. */}
                  {r.receipt_available && onReceipt && topupIdFromRow(r)
                    ? <Btn size="xs" variant="ghost" icon={<Eye size={12} />}
                        onClick={() => onReceipt(r)}>Receipt</Btn>
                    : <span style={{ color: "var(--text-tertiary)", fontSize: 11.5 }}>—</span>}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </TableSurface>
    </div>
  );
}
function td(): React.CSSProperties {
  return { fontSize: 12.5, color: "var(--text-primary)", padding: "10px",
    borderBottom: "1px solid var(--border)", verticalAlign: "top", whiteSpace: "nowrap" };
}

/* ── liability holds ─────────────────────────────────────────────────────── */

function HoldsList({ holds }: { holds: HsLiabilityHold[] }) {
  if (holds.length === 0) {
    return <p style={{ fontSize: 12.5, color: "var(--success-text)", margin: 0 }}>
      No liability holds against your account.
    </p>;
  }
  return (
    <div style={{ display: "grid", gap: 6 }}>
      {holds.map(h => (
        <div key={h.code} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
          gap: 10, background: "var(--warning-bg)", border: "1px solid var(--warning-border)",
          borderRadius: 10, padding: "8px 11px" }}>
          <span style={{ fontSize: 12.5, color: "var(--warning-text)", fontWeight: 600 }}>{h.label}</span>
          <span style={{ fontSize: 12, color: "var(--warning-text)" }}>
            {h.count}{h.amount ? ` · ${money(h.amount)}` : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

/* The deposit refund-request card was removed with the deposit itself
   (migrations 317/318): a top-up is spent down as commission, never held
   and returned, so there is nothing to request back. */

/* ── page ─────────────────────────────────────────────────────────────────── */

export default function HomeServicesFinancePage() {
  const [tab, setTab] = useState<TabKey>("overview");
  const [data, setData] = useState<HsFinanceOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ code?: string; message: string; resolution?: string } | null>(null);

  // tab-scoped extras
  const [txns, setTxns] = useState<HsFinanceTxnPage | null>(null);
  const [txnLedger, setTxnLedger] = useState<string>("");
  const [txnStatus, setTxnStatus] = useState<string>("");
  // The endpoint accepts `from`, `to` and `type` as well as ledger/status, but
  // only two of the five filters had controls, so a tenant could not narrow
  // financial activity to a period -- the single most common thing to want
  // when reconciling a statement.
  const [txnFrom, setTxnFrom] = useState<string>("");
  const [txnTo, setTxnTo] = useState<string>("");
  const [txnType, setTxnType] = useState<string>("");
  /** Commission actually charged on completed jobs. The endpoint exists to
   *  close a transparency gap ("the tenant had NO way to see the commission
   *  rate being charged") but the Finance Hub never called it -- pricing was
   *  only visible on the dashboard, not on the page about money. */
  const [rates, setRates] = useState<HsCommissionRates | null>(null);
  const [ratesFailed, setRatesFailed] = useState(false);
  /**
   * Top-ups were loaded once as `{ page_size: 25 }` with no page and no
   * status, so only the newest 25 orders were ever reachable and the endpoint's
   * `status`/`page` parameters had no controls. `total` was discarded too, so
   * there was nothing to page against.
   */
  const [topupTotal, setTopupTotal] = useState(0);
  const [topupPage, setTopupPage] = useState(1);
  const [topupStatus, setTopupStatus] = useState("");
  /** GST receipt for a credited order. `getTopup` returns it, but nothing
   *  called that endpoint, so the receipt a tenant needs for their books was
   *  unreachable from the UI. */
  const [receipt, setReceipt] = useState<{ order: HsTopupOrder; loading: boolean } | null>(null);
  const [txnPage, setTxnPage] = useState(1);
  const [txnLoading, setTxnLoading] = useState(false);

  const [topups, setTopups] = useState<HsTopupOrder[] | null>(null);
  const [packages, setPackages] = useState<HsCreditPackage[] | null>(null);
  const [buyOpen, setBuyOpen] = useState(false);
  const [buyQty, setBuyQty] = useState(1);
  const [buyBusy, setBuyBusy] = useState(false);
  const [buyResult, setBuyResult] = useState<string | null>(null);


  const [policyOpen, setPolicyOpen] = useState(false);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const { open: openCheckout } = useRazorpayCheckout();

  /* URL <-> tab sync (?tab=&ledger=&status=&page=) */
  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const t = sp.get("tab") as TabKey | null;
    if (t && TABS.some(x => x.key === t)) setTab(t);
    if (sp.get("ledger")) setTxnLedger(sp.get("ledger") as string);
    if (sp.get("status")) setTxnStatus(sp.get("status") as string);
    if (sp.get("from")) setTxnFrom(sp.get("from") as string);
    if (sp.get("to")) setTxnTo(sp.get("to") as string);
    if (sp.get("type")) setTxnType(sp.get("type") as string);
    const p = Number(sp.get("page")); if (p > 0) setTxnPage(p);
  }, []);

  const pushUrl = useCallback((next: Partial<{
    tab: string; ledger: string; status: string; page: number;
    from: string; to: string; type: string;
  }>) => {
    const sp = new URLSearchParams(window.location.search);
    Object.entries(next).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "" || v === 0) sp.delete(k);
      else sp.set(k, String(v));
    });
    window.history.replaceState(null, "", `${window.location.pathname}?${sp.toString()}`);
  }, []);

  const goTab = useCallback((t: TabKey) => { setTab(t); pushUrl({ tab: t }); }, [pushUrl]);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    homeServicesFinanceApi.getOverview()
      .then(d => setData(d))
      .catch((e: unknown) => {
        // Never degrade a failed finance fetch into a zero balance.
        setData(null);
        if (e instanceof ServiceOSError) setError({ code: e.code, message: e.message, resolution: e.resolution });
        else setError({ message: "Finance data is temporarily unavailable. Please retry." });
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  useEffect(() => {
    homeServicesFinanceApi.getCommissionRates()
      .then(r => { setRates(r); setRatesFailed(false); })
      // Never render a fabricated rate; show the panel as unavailable instead.
      .catch(() => { setRates(null); setRatesFailed(true); });
  }, []);

  const loadTxns = useCallback(() => {
    setTxnLoading(true);
    homeServicesFinanceApi.getTransactions({
      ledger: txnLedger || undefined, status: txnStatus || undefined,
      // The endpoint aliases these as `from` / `to` / `type`.
      from: txnFrom || undefined, to: txnTo || undefined, type: txnType || undefined,
      page: txnPage, page_size: 25,
    }).then(setTxns).catch(() => setTxns(null)).finally(() => setTxnLoading(false));
  }, [txnLedger, txnStatus, txnFrom, txnTo, txnType, txnPage]);

  useEffect(() => { if (tab === "topups") loadTxns(); }, [tab, loadTxns]);
  useEffect(() => {
    if (tab !== "topups") return;
    homeServicesFinanceApi.listTopups({ status: topupStatus || undefined, page: topupPage, page_size: 25 })
      .then(r => { setTopups(r.items); setTopupTotal(Number(r.total ?? 0)); })
      .catch(() => setTopups(null));
  }, [tab, topupStatus, topupPage]);

  const openReceipt = useCallback(async (topupId: string) => {
    setReceipt({ order: {} as HsTopupOrder, loading: true });
    try {
      const full = await homeServicesFinanceApi.getTopup(topupId);
      setReceipt({ order: full, loading: false });
    } catch {
      setReceipt(null);
    }
  }, []);

  const openBuy = useCallback(() => {
    setBuyOpen(true); setBuyResult(null);
    if (!packages) {
      homeServicesFinanceApi.getCreditPackages().then(r => setPackages(r.packages)).catch(() => setPackages([]));
    }
  }, [packages]);

  /**
   * Real bug fixed here: this used to stop at `createTopup` (which only
   * ever creates a Razorpay gateway order and posts NO credit) and show a
   * static "will be posted after verification" message with no way for
   * the tenant to actually pay -- there was no admin-approval GATE, there
   * was just a missing checkout step, so credit could never be purchased
   * at all through this UI. Now opens the real Razorpay Checkout with the
   * order this call already creates, then calls the real, HMAC-signature-
   * verified `/top-ups/confirm` endpoint -- server-verified and instant,
   * never an admin review queue.
   */
  const submitBuy = useCallback(async () => {
    setBuyBusy(true); setBuyResult(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let order: any = null;
    try {
      order = await homeServicesFinanceApi.createTopup(buyQty);
      const result = await openCheckout({
        keyId: order.key, orderId: order.gateway_order_id, amountPaise: order.amount_paise,
        currency: order.currency ?? "INR", name: "ServiceOS — Home Services Usage Credit",
        description: `${buyQty} credit package${buyQty === 1 ? "" : "s"}`,
      });
      const confirmed = await homeServicesFinanceApi.confirmTopup({
        gateway_order_id: result.razorpay_order_id,
        gateway_payment_id: result.razorpay_payment_id,
        signature: result.razorpay_signature,
      });
      setBuyResult(`Payment confirmed — ${money(confirmed.usable_credits_on_success ?? order.usable_credits_on_success)} credited to your wallet.`);
    } catch (e: unknown) {
      // The order is already created (and visible in the table) the moment
      // checkout opens -- if the tenant dismisses the Razorpay popup or the
      // signature confirm fails, cancel that same order rather than leaving
      // it stuck at "initiated" (which the table badges the same warning
      // yellow as a real in-flight payment, reading as "awaiting approval").
      if (order?.topup_id) {
        await homeServicesFinanceApi.cancelTopup(order.topup_id).catch(() => {});
      }
      setBuyResult(e instanceof ServiceOSError ? e.message : (e instanceof Error ? e.message : "Could not complete the top-up."));
    } finally {
      setBuyBusy(false); load();
    }
  }, [buyQty, load, openCheckout]);

  const doExport = useCallback(() => {
    setExportMsg("Preparing…");
    // Export previously ignored every filter except ledger, so a filtered
    // view exported a different (wider) set of rows than it displayed.
    homeServicesFinanceApi.exportStatement({
      ledger: txnLedger || undefined, status: txnStatus || undefined,
      from: txnFrom || undefined, to: txnTo || undefined, type: txnType || undefined,
    })
      .then(r => {
        const blob = new Blob([r.csv], { type: "text/csv;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob); a.download = r.filename; a.click();
        URL.revokeObjectURL(a.href);
        setExportMsg(`Exported ${r.row_count} row(s) — your tenant, Home Services only.`);
      })
      .catch((e: unknown) => setExportMsg(e instanceof ServiceOSError ? e.message : "Export failed."));
  }, [txnLedger, txnStatus, txnFrom, txnTo, txnType]);

  const kpis = data?.kpis;
  const statusVar = useMemo<"success" | "warning" | "danger">(() => {
    if (!kpis) return "warning";
    return kpis.finance_status === "ready" ? "success" : kpis.finance_status === "blocked" ? "danger" : "warning";
  }, [kpis]);

  return (
    <div style={{ padding: 24, maxWidth: 1800, margin: "0 auto" }}>
      <style>{`
        .fh-kpis { display: grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: 12px; margin: 20px 0; }
        @media (max-width: 1500px) { .fh-kpis { grid-template-columns: repeat(3, minmax(0,1fr)); } }
        @media (max-width: 900px)  { .fh-kpis { grid-template-columns: repeat(2, minmax(0,1fr)); } }
        .fh-two { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }
        @media (max-width: 1100px) { .fh-two { grid-template-columns: 1fr; } }
        .fh-queue { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; }
        @media (max-width: 1300px) { .fh-queue { grid-template-columns: repeat(2, minmax(0,1fr)); } }
        .fh-tabs { display: flex; gap: 4; overflow-x: auto; }
        .fh-input { width: 100%; background: var(--surface-sunken); border: 1px solid var(--border);
          border-radius: 10px; padding: 9px 11px; font-size: 13px; color: var(--text-primary);
          font-family: inherit; }
      `}</style>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        flexWrap: "wrap", gap: 14 }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase",
            color: "var(--accent)", margin: "0 0 6px" }}>FINANCE</p>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>
            Home Services Finance
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, maxWidth: 720 }}>
            Manage usage credits, technician seats and finance readiness for this Home Services workspace.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Btn variant="secondary" icon={<Download size={14} />} onClick={doExport}>Export Statement</Btn>
          <Btn variant="secondary" icon={<FileText size={14} />} onClick={() => { setPolicyOpen(true); goTab("policy"); }}>
            View Policy
          </Btn>
          <Btn variant="primary" icon={<CreditCard size={14} />} onClick={openBuy}>Buy Usage Credits</Btn>
        </div>
      </div>

      {exportMsg && (
        <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "8px 0 0" }}>{exportMsg}</p>
      )}

      {error && <ErrorBanner code={error.code} message={error.message} resolution={error.resolution} />}

      {/* ── 6 KPI cards ────────────────────────────────────────────────── */}
      {loading ? (
        <KpiGrid className="fh-kpis">{[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} height={104} radius={20} />)}</KpiGrid>
      ) : kpis && (
        <KpiGrid className="fh-kpis">
          <KpiCard label="Usable credits" value={moneyCompact(kpis.usable_credits)}
            sub={data?.usage_credits.is_low_balance ? "Below low-balance threshold" : "Available to spend on jobs"}
            icon={<Wallet size={17} />} variant={data?.usage_credits.is_low_balance ? "warning" : "success"} />
          <KpiCard label="Credits used this month" value={moneyCompact(kpis.credits_used_this_month)}
            sub={`${data?.usage_credits.completed_job_deductions ?? 0} completed-job deduction(s) all-time`}
            icon={<TrendingDown size={17} />} variant="info" />
          {/* Seats replaced the security deposit: headcount is bought with a
              top-up plan rather than collateralised. */}
          <KpiCard label="Technician seats" value={kpis.entitled_seats ?? 0}
            sub="Bought with a top-up plan — also jobs bookable per slot"
            icon={<Shield size={17} />} variant="default" />
          <KpiCard label="Action items" value={kpis.action_items}
            sub="Open finance items needing you"
            icon={<ListChecks size={17} />} variant={kpis.action_items > 0 ? "warning" : "success"} />
          <KpiCard label="Finance status" value={kpis.finance_status_label}
            sub="Server-computed readiness"
            icon={statusVar === "success" ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}
            variant={statusVar} />
        </KpiGrid>
      )}

      {/* ── Tabs ───────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: 4, borderBottom: "1px solid var(--border)",
        margin: "4px 0 18px", overflowX: "auto" }}>
        {TABS.map(t => {
          const Icon = t.icon;
          const on = tab === t.key;
          return (
            <button key={t.key} onClick={() => goTab(t.key)} style={{
              display: "inline-flex", alignItems: "center", gap: 7, background: "none", border: "none",
              borderBottom: `2px solid ${on ? "var(--brand)" : "transparent"}`,
              color: on ? "var(--text-primary)" : "var(--text-secondary)",
              fontWeight: on ? 700 : 500, fontSize: 13, padding: "10px 14px", cursor: "pointer",
              whiteSpace: "nowrap", fontFamily: "inherit",
            }}>
              <Icon size={14} />{t.label}
            </button>
          );
        })}
        <div style={{ marginLeft: "auto", paddingBottom: 6 }}>
          <Btn size="sm" variant="ghost" icon={<RefreshCw size={13} />} onClick={load}>Refresh</Btn>
        </div>
      </div>

      {loading && (
        <div style={{ display: "grid", gap: 16 }}>
          <Skeleton height={240} radius={20} /><Skeleton height={260} radius={20} />
        </div>
      )}

      {/* ══ OVERVIEW ══════════════════════════════════════════════════════ */}
      {!loading && data && tab === "overview" && (
        <div style={{ display: "grid", gap: 16 }}>

          {/* 1. Finance readiness */}
          <ReadinessCard data={data.readiness} />

          {/* 2. Recent financial activity */}
          <Card padding={0}>
            <div style={{ padding: "18px 18px 0" }}>
              <SectionTitle icon={<Receipt size={16} />} title="Recent financial activity"
                subtitle={data.recent_activity.never_combined_note}
                actions={<Btn size="sm" variant="secondary" icon={<ArrowUpRight size={13} />}
                  onClick={() => goTab("topups")}>View all</Btn>} />
            </div>
            <ActivityTable page={data.recent_activity} compact />
          </Card>

          {/* 3 + 4. Wallet and seats */}
          <div className="fh-two">
            <Card>
              <SectionTitle icon={<Wallet size={16} />} title="Usage-credit wallet"
                subtitle="Internal platform credits — not money"
                actions={<Badge variant={data.usage_credits.is_low_balance ? "warning" : "success"} size="sm">
                  {humanStatus(data.usage_credits.wallet_status)}</Badge>} />
              <div style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", marginBottom: 12 }}>
                {money(data.usage_credits.available_credits)}
              </div>
              <Row label="Reserved credits"
                value={data.usage_credits.reserved_credits_tracked ? money(data.usage_credits.reserved_credits) : "Not tracked"}
                hint={data.usage_credits.reserved_credits_tracked ? undefined : "no reservation mechanism exists"} />
              <Row label="Pending (paid, not yet posted)" value={money(data.usage_credits.pending_credits)} />
              <Row label="Used this month" value={money(data.usage_credits.credits_used_this_month)} />
              <Row label="Deducted all-time" value={money(data.usage_credits.credits_deducted_total)}
                hint={`${data.usage_credits.completed_job_deductions} job(s)`} />
              <Row label="Reversals" value={`${data.usage_credits.reversals_count} · ${money(data.usage_credits.reversals_total)}`} />
              <Row label="Low-balance threshold" value={money(data.usage_credits.low_balance_threshold)} />
              <Row label="Estimated jobs remaining"
                value={data.usage_credits.estimated_jobs_remaining_calculable
                  ? data.usage_credits.estimated_jobs_remaining
                  : "Not calculable yet"}
                hint={data.usage_credits.average_deduction_per_job
                  ? `avg ${money(data.usage_credits.average_deduction_per_job)}/job`
                  : "no priced deduction history"} />
              <Row label="Last top-up"
                value={data.usage_credits.last_topup
                  ? `${data.usage_credits.last_topup.order_ref} · ${dt(data.usage_credits.last_topup.created_at)}`
                  : "None yet"} />
              <Row label="Deduction policy" value={data.usage_credits.deduction_policy ?? "—"}
                hint={data.usage_credits.policy_version ? `v${data.usage_credits.policy_version}` : undefined} />
              <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
                <Btn size="sm" variant="primary" icon={<CreditCard size={13} />} onClick={openBuy}>Buy credits</Btn>
                <Btn size="sm" variant="secondary" onClick={() => goTab("usage-credits")}>View transactions</Btn>
              </div>
            </Card>

            <Card>
              <SectionTitle icon={<Shield size={16} />} title="Technician seats"
                subtitle="Bought with a top-up plan — one seat is one technician, and one more job per slot" />
              <div style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", marginBottom: 12 }}>
                {data.kpis?.entitled_seats ?? 0}
              </div>
              <Row label="Seats purchased" value={data.kpis?.entitled_seats ?? 0} />
              <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6, marginTop: 10 }}>
                The security deposit was retired. Your credit balance is what covers a
                penalty or settlement, and bookings pause if it falls below the floor —
                so keeping it topped up is what keeps work coming in.
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
                <Btn size="sm" variant="primary" icon={<CreditCard size={13} />} onClick={openBuy}>Buy a top-up plan</Btn>
              </div>
            </Card>
          </div>

          {/* 5. Current finance policy (read-only) */}
          <Card>
            <SectionTitle icon={<FileText size={16} />} title="Current finance policy"
              subtitle="Published by ServiceOS Admin · read-only for your business"
              actions={data.policy.resolved
                ? <Badge variant="muted" size="sm">v{data.policy.version} · {humanStatus(data.policy.status ?? "")}</Badge>
                : <Badge variant="danger" size="sm">Unresolved</Badge>} />
            {!data.policy.resolved ? (
              <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
                borderRadius: 10, padding: "10px 12px", fontSize: 12.5, color: "var(--danger-text)" }}>
                {data.policy.message} <span style={{ fontFamily: "monospace", opacity: 0.7 }}>({data.policy.error_code})</span>
              </div>
            ) : (
              <div className="fh-two">
                <div>
                  <Row label="Vertical" value={data.policy.vertical_label ?? "—"} />
                  <Row label="Revenue model" value={data.policy.revenue_model ?? "—"} />
                  <Row label="Customer payment" value={data.policy.customer_payment_model ?? "—"} />
                  <Row label="Credit purchase rule" value={data.policy.credit_purchase_rule ?? "—"} />
                  <Row label="Completion deduction" value={data.policy.completion_deduction_rule ?? "—"} />
                </div>
                <div>
                  <Row label="Bookings pause below" value={money(data.policy.credit_booking_floor)} />
                  <Row label="GST / tax rule" value={data.policy.gst_tax_rule ?? "—"} />
                  <Row label="Low-balance policy" value={data.policy.low_balance_policy ?? "—"} />
                  <Row label="Effective from" value={dt(data.policy.effective_from)} />
                  <Row label="Published by" value={data.policy.published_by ?? "ServiceOS Admin"}
                    hint={data.policy.published_at ? dt(data.policy.published_at) : undefined} />
                </div>
              </div>
            )}
          </Card>

          {/* 6. Direct customer-payment summary */}
          <Card>
            <SectionTitle icon={<Info size={16} />} title="Direct customer-payment summary"
              subtitle={data.direct_payments.notice}
              actions={
                <Link href={data.direct_payments.link} style={{ textDecoration: "none" }}>
                  <Btn size="sm" variant="secondary" icon={<ExternalLink size={13} />}>Open Direct Payments</Btn>
                </Link>
              } />
            {data.direct_payments.projection_failed ? (
              <div style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)",
                borderRadius: 10, padding: "10px 12px", fontSize: 12.5, color: "var(--warning-text)" }}>
                Direct-payment counts are temporarily unavailable (partial projection failure). No figures are
                shown rather than reporting a misleading zero.
              </div>
            ) : (
              <div className="fh-queue">
                <Row label="Awaiting provider confirmation" value={data.direct_payments.awaiting_provider_confirmation ?? 0} />
                <Row label="Awaiting customer confirmation" value={data.direct_payments.awaiting_customer_confirmation ?? 0} />
                <Row label="Confirmed" value={data.direct_payments.confirmed ?? 0} />
                <Row label="Mismatch" value={data.direct_payments.mismatch ?? 0} />
                <Row label="Disputed" value={data.direct_payments.disputed ?? 0} />
                <Row label="Total records" value={data.direct_payments.total_attempts ?? 0} />
                <Row label="Provider collected (recorded)" value={money(data.direct_payments.provider_collected_total)} />
                <Row label="Held by ServiceOS" value={money(data.direct_payments.serviceos_held_amount)}
                  hint="never holds job funds" />
              </div>
            )}
          </Card>

          {/* 7. Action & reconciliation queue */}
          <Card>
            <SectionTitle icon={<ListChecks size={16} />} title="Action & reconciliation queue"
              subtitle="Real counts from your ledgers — each card opens its exact filtered workflow" />
            <div className="fh-queue">
              {data.action_queue.map(q => {
                const active = q.count > 0;
                const tone = !active ? "muted" : q.severity;
                return (
                  <button key={q.code} onClick={() => {
                    goTab(q.tab as TabKey);
                    if (q.filter && typeof q.filter.ledger === "string") {
                      setTxnLedger(q.filter.ledger); pushUrl({ ledger: q.filter.ledger });
                    }
                    if (q.filter && typeof q.filter.status === "string") {
                      // FAILED_TOPUPS / PENDING_TOPUPS carry a top-up PAYMENT
                      // status ("failed" / "initiated"). This applied it to the
                      // transactions filter, where those are not valid statuses
                      // at all (the ledger only has posted/cancelled) — so the
                      // click filtered the activity table to nothing while the
                      // top-up table below stayed unfiltered, i.e. it produced
                      // a misleading empty state instead of the rows it named.
                      if (q.code === "FAILED_TOPUPS" || q.code === "PENDING_TOPUPS") {
                        setTopupStatus(q.filter.status); setTopupPage(1);
                      } else {
                        setTxnStatus(q.filter.status); pushUrl({ status: q.filter.status });
                      }
                    }
                  }} style={{
                    textAlign: "left", cursor: "pointer", fontFamily: "inherit",
                    background: active
                      ? (q.severity === "danger" ? "var(--danger-bg)" : q.severity === "warning" ? "var(--warning-bg)" : "var(--info-bg)")
                      : "var(--surface-sunken)",
                    border: `1px solid ${active
                      ? (q.severity === "danger" ? "var(--danger-border)" : q.severity === "warning" ? "var(--warning-border)" : "var(--info-border)")
                      : "var(--border)"}`,
                    borderRadius: 12, padding: "12px 13px",
                  }}>
                    <div style={{ fontSize: 22, fontWeight: 800, lineHeight: 1,
                      color: active
                        ? (q.severity === "danger" ? "var(--danger-text)" : q.severity === "warning" ? "var(--warning-text)" : "var(--info-text)")
                        : "var(--text-tertiary)" }}>{q.count}</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginTop: 6 }}>{q.label}</div>
                    <div style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 3 }}>
                      {active ? "Open workflow →" : "Nothing to do"}
                    </div>
                    <span style={{ display: "none" }}>{tone}</span>
                  </button>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* ══ USAGE CREDITS ═════════════════════════════════════════════════ */}
      {!loading && data && tab === "usage-credits" && (
        <div style={{ display: "grid", gap: 16 }}>
          <div className="fh-two">
            <Card>
              <SectionTitle icon={<Wallet size={16} />} title="Wallet balance"
                subtitle="tenant_billing.credit_balance — the single canonical balance" />
              <div style={{ fontSize: 34, fontWeight: 800, color: "var(--text-primary)" }}>
                {money(data.usage_credits.available_credits)}
              </div>
              <Row label="Wallet status" value={<Badge variant={data.usage_credits.is_low_balance ? "warning" : "success"} size="sm">
                {humanStatus(data.usage_credits.wallet_status)}</Badge>} />
              <Row label="Pending (paid, not posted)" value={money(data.usage_credits.pending_credits)} />
              <Row label="Failed top-ups" value={data.usage_credits.failed_topups} />
              <Row label="Pending gateway confirmation" value={data.usage_credits.pending_topups} />
              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                <Btn size="sm" variant="primary" icon={<CreditCard size={13} />} onClick={openBuy}>Buy credits</Btn>
                <Btn size="sm" variant="secondary" onClick={() => goTab("topups")}>Top-ups & transactions</Btn>
              </div>
            </Card>
            <Card>
              <SectionTitle icon={<TrendingDown size={16} />} title="Completed-job deductions"
                subtitle="Server-calculated at completion, idempotent per job — read-only here" />
              <Row label="Deductions posted" value={data.usage_credits.completed_job_deductions} />
              <Row label="Total deducted" value={money(data.usage_credits.credits_deducted_total)} />
              <Row label="Used this month" value={money(data.usage_credits.credits_used_this_month)} />
              <Row label="Average per job" value={money(data.usage_credits.average_deduction_per_job)} />
              <Row label="Reversals" value={`${data.usage_credits.reversals_count} · ${money(data.usage_credits.reversals_total)}`} />
              <Row label="Estimated jobs remaining"
                value={data.usage_credits.estimated_jobs_remaining_calculable
                  ? data.usage_credits.estimated_jobs_remaining : "Not calculable yet"} />
              <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "12px 0 0" }}>
                Credit reversals are an Admin-controlled correction. Posted ledger entries are immutable —
                a correction always appears as a separate reversal entry, never an edit.
              </p>
            </Card>
          </div>
          <Card padding={0}>
            <div style={{ padding: "18px 18px 0" }}>
              <SectionTitle icon={<Receipt size={16} />} title="Usage-credit ledger"
                subtitle="Ledger A only — purchases, top-ups, completion deductions, reversals" />
            </div>
            {data.usage_credits.ledger
              ? <ActivityTable page={data.usage_credits.ledger} />
              : <EmptyRow text="No usage-credit entries yet." />}
          </Card>
        </div>
      )}

      {/* ══ TOP-UPS & TRANSACTIONS ════════════════════════════════════════ */}
      {!loading && data && tab === "topups" && (
        <div style={{ display: "grid", gap: 16 }}>
          <Card>
            <SectionTitle icon={<CreditCard size={16} />} title="Credit top-up orders"
              subtitle="A pending payment never credits the wallet; a duplicate gateway callback never double-credits"
              actions={
                <>
                  {/* `status` was a supported query parameter with no control. */}
                  <select className="fh-input" style={{ width: 180 }} value={topupStatus}
                    onChange={e => { setTopupStatus(e.target.value); setTopupPage(1); }}>
                    <option value="">All payment statuses</option>
                    <option value="initiated">Initiated</option>
                    <option value="paid">Paid</option>
                    <option value="credited">Credited</option>
                    <option value="failed">Failed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                  <Btn size="sm" variant="primary" icon={<CreditCard size={13} />} onClick={openBuy}>Buy usage credits</Btn>
                </>
              } />
            {topups === null ? <Skeleton height={120} /> : topups.length === 0
              ? <EmptyRow text="No credit top-up orders yet." />
              : (
                <div style={{ overflowX: "auto" }}>
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse", minWidth: 900 }}>
                    <thead><tr>
                      {["Created", "Order ref", "Base credits", "GST", "Total payable", "Payment", "Wallet", "Gateway payment", "Receipt"].map(c =>
                        <th key={c} style={{ textAlign: "left", fontSize: 10.5, fontWeight: 700, letterSpacing: "0.05em",
                          textTransform: "uppercase", color: "var(--text-tertiary)", padding: "8px 10px",
                          borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>{c}</th>)}
                    </tr></thead>
                    <tbody>
                      {topups.map(t => (
                        <tr key={t.topup_id}>
                          <td style={td()}>{dt(t.created_at)}</td>
                          <td style={{ ...td(), fontFamily: "monospace", fontSize: 11 }}>{t.order_ref}</td>
                          <td style={td()}>{money(t.base_credits ?? String(t.credits_purchased))}</td>
                          <td style={td()}>{money(t.gst_amount)}</td>
                          <td style={{ ...td(), fontWeight: 700 }}>{money(t.total_payable ?? String(t.amount_paid))}</td>
                          <td style={td()}><Badge variant={statusVariant(t.payment_status)} size="sm">{humanStatus(t.payment_status)}</Badge></td>
                          <td style={td()}><Badge variant={statusVariant(t.wallet_credit_status)} size="sm">{humanStatus(t.wallet_credit_status)}</Badge></td>
                          <td style={{ ...td(), fontFamily: "monospace", fontSize: 10.5 }}>{t.gateway_payment_id ?? "—"}</td>
                          <td style={td()}>
                            {t.payment_status === "credited"
                              ? <Btn size="xs" variant="secondary" icon={<Eye size={11} />}
                                  onClick={() => openReceipt(String(t.topup_id))}>Receipt</Btn>
                              : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </TableSurface>
                  <Pagination page={topupPage} pageSize={25} total={topupTotal} onPage={setTopupPage} itemLabel="top-up orders" />
                </div>
              )}
          </Card>

          <Card padding={0}>
            <div style={{ padding: "18px 18px 0" }}>
              <SectionTitle icon={<Receipt size={16} />} title="Financial activity"
                subtitle="All four ledgers, tagged and never merged"
                actions={
                  <>
                    <select className="fh-input" style={{ width: 200 }} value={txnLedger}
                      onChange={e => { setTxnLedger(e.target.value); setTxnPage(1); pushUrl({ ledger: e.target.value, page: 1 }); }}>
                      <option value="">All ledgers</option>
                      {(txns?.ledgers ?? data.recent_activity.ledgers).map(l =>
                        <option key={l.value} value={l.value}>{l.label}</option>)}
                    </select>
                    {/* Status and type were free-text boxes, so the caller had
                        to guess the exact stored value. Both are now driven by
                        facets the endpoint returns. */}
                    <select className="fh-input" style={{ width: 160 }} value={txnStatus}
                      onChange={e => { setTxnStatus(e.target.value); setTxnPage(1); pushUrl({ status: e.target.value, page: 1 }); }}>
                      <option value="">All statuses</option>
                      {(txns?.statuses ?? []).map(v => <option key={v} value={v}>{humanStatus(v)}</option>)}
                    </select>
                    <select className="fh-input" style={{ width: 180 }} value={txnType}
                      onChange={e => { setTxnType(e.target.value); setTxnPage(1); pushUrl({ type: e.target.value, page: 1 }); }}>
                      <option value="">All event types</option>
                      {(txns?.types ?? []).map(v => <option key={v} value={v}>{humanStatus(v)}</option>)}
                    </select>
                    <input className="fh-input" style={{ width: 145 }} type="date" aria-label="From date" value={txnFrom}
                      onChange={e => { setTxnFrom(e.target.value); setTxnPage(1); pushUrl({ from: e.target.value, page: 1 }); }} />
                    <input className="fh-input" style={{ width: 145 }} type="date" aria-label="To date" value={txnTo}
                      onChange={e => { setTxnTo(e.target.value); setTxnPage(1); pushUrl({ to: e.target.value, page: 1 }); }} />
                    {(txnLedger || txnStatus || txnType || txnFrom || txnTo) && (
                      <Btn size="sm" variant="secondary" onClick={() => {
                        setTxnLedger(""); setTxnStatus(""); setTxnType(""); setTxnFrom(""); setTxnTo(""); setTxnPage(1);
                        pushUrl({ ledger: "", status: "", type: "", from: "", to: "", page: 1 });
                      }}>Clear</Btn>
                    )}
                    <Btn size="sm" variant="secondary" icon={<Download size={13} />} onClick={doExport}>Export</Btn>
                  </>
                } />
            </div>
            {txnLoading ? <div style={{ padding: 18 }}><Skeleton height={160} /></div>
              : txns ? <>
                  <ActivityTable page={txns} onReceipt={r => {
                    const id = topupIdFromRow(r);
                    if (id) openReceipt(id);
                  }} />
                  <Pagination page={txns.page} pageSize={txns.page_size} total={txns.total}
                    onPage={p => { setTxnPage(p); pushUrl({ page: p }); }} itemLabel="transactions" />
                </>
              : <EmptyRow text="Transactions could not be loaded. Please retry — no figures are shown rather than a misleading zero." />}
          </Card>
        </div>
      )}

      {/* ══ POLICY & AUDIT ════════════════════════════════════════════════ */}
      {!loading && data && tab === "policy" && (
        <div style={{ display: "grid", gap: 16 }}>
          {/* Commission actually charged on completed jobs. `/commission-rates`
              exists specifically to close the transparency gap of a tenant
              having no way to see its own rate, but the Finance Hub never
              called it -- the rate was visible only on the dashboard, not on
              the page about money. */}
          <Card>
            <SectionTitle icon={<CreditCard size={16} />} title="Commission charged to you"
              subtitle="The rate resolved the same way job completion resolves it — not an estimate"
              actions={rates
                ? <Badge variant={rates.is_live ? "default" : "muted"} size="lg">
                    {rates.is_live ? "Live" : "Not charging"}
                  </Badge>
                : undefined} />
            {ratesFailed ? (
              <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
                borderRadius: 10, padding: "10px 12px", fontSize: 12.5, color: "var(--danger-text)" }}>
                Commission rates could not be loaded. No rate is shown rather than a misleading zero.
              </div>
            ) : !rates ? (
              <Skeleton height={90} />
            ) : (
              <>
                <div className="fh-two">
                  <div>
                    <Row label="Provider model" value={rates.provider_model ?? "—"} />
                    <Row label="Default rate" value={rates.default_rate_pct ? `${rates.default_rate_pct}%` : "—"} />
                  </div>
                  <div>
                    <Row label="Charged on" value={rates.basis || "—"} />
                    <Row label="Charged as" value={rates.charged_as || "—"} />
                  </div>
                </div>
                {!rates.is_live && rates.not_live_reason && (
                  <div style={{ marginTop: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)",
                    borderRadius: 10, padding: "9px 11px", fontSize: 12, color: "var(--text-secondary)" }}>
                    {rates.not_live_reason}
                  </div>
                )}
                {rates.categories.length > 0 && (
                  <div style={{ marginTop: 14 }}>
                    <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em",
                      color: "var(--text-tertiary)", margin: "0 0 8px" }}>
                      Rate per service category
                    </p>
                    {/* These categories are derived from the tenant's own
                        enabled `tenant_services` rows — i.e. exactly the
                        catalogue the Services & Pricing setup page manages. */}
                    <div style={{ display: "grid", gap: 6 }}>
                      {rates.categories.map(c => (
                        <div key={c.category_id} style={{ display: "flex", justifyContent: "space-between",
                          alignItems: "center", gap: 10, padding: "8px 11px", background: "var(--surface-sunken)",
                          border: "1px solid var(--border)", borderRadius: 9 }}>
                          <span style={{ fontSize: 12.5, color: "var(--text-primary)" }}>
                            {c.category_name || "Category"}
                          </span>
                          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            {c.using_default && (
                              <span style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>default</span>
                            )}
                            <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)" }}>
                              {c.effective_rate_pct != null ? `${c.effective_rate_pct}%` : "—"}
                            </span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </Card>

          <Card>
            <SectionTitle icon={<FileText size={16} />} title="Published finance policy"
              subtitle="Immutable, versioned, published by ServiceOS Admin — your business cannot edit it"
              actions={data.policy.resolved
                ? <Badge variant="muted" size="lg">Version {data.policy.version}</Badge>
                : <Badge variant="danger" size="lg">Unresolved</Badge>} />
            {!data.policy.resolved ? (
              <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
                borderRadius: 10, padding: "10px 12px", fontSize: 12.5, color: "var(--danger-text)" }}>
                {data.policy.message}
              </div>
            ) : (
              <div className="fh-two">
                <div>
                  <Row label="Vertical" value={data.policy.vertical_label ?? "—"} />
                  <Row label="Revenue model" value={data.policy.revenue_model ?? "—"} />
                  <Row label="Credit package base" value={money(data.policy.credit_package_base_amount)} />
                  <Row label="GST percent" value={`${data.policy.credit_package_gst_percent ?? "—"}%`} />
                  <Row label="GST amount" value={money(data.policy.credit_package_gst_amount)} />
                  <Row label="Total payable" value={money(data.policy.credit_package_total_payable)} />
                  <Row label="Posted to usable wallet" value={money(data.policy.credited_wallet_amount)}
                    hint="GST never enters the wallet" />
                  <Row label="Initial purchase required" value={data.policy.initial_credit_purchase_required ? "Yes" : "No"} />
                </div>
                <div>
                  {/* The deposit rows here were retired with the deposit. What
                      protects the platform now is the credit floor below. */}
                  <Row label="Low-balance warning at" value={money(data.policy.credit_warning_threshold)} />
                  <Row label="Bookings pause below" value={money(data.policy.credit_booking_floor)}
                    hint="new bookings stop; work in flight finishes" />
                  <Row label="Seat accrual" value={data.policy.seat_accrual_mode ?? "—"} />
                  <Row label="Completion deduction" value={data.policy.completion_deduction_rule ?? "—"} />
                  <Row label="Status" value={humanStatus(data.policy.status ?? "—")} />
                  <Row label="Published" value={dt(data.policy.published_at)}
                    hint={data.policy.published_by ?? undefined} />
                </div>
              </div>
            )}
            {policyOpen && (
              <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "12px 0 0" }}>
                Every transaction snapshots the policy version in force when it was posted. Published versions
                are immutable — a change always creates a new version.
              </p>
            )}
          </Card>

          <Card padding={0}>
            <div style={{ padding: "18px 18px 0" }}>
              <SectionTitle icon={<Clock size={16} />} title="Finance audit trail"
                subtitle="Every finance action recorded against your workspace" />
            </div>
            {(data.policy.audit?.items.length ?? 0) === 0
              ? <EmptyRow text="No finance audit events recorded yet." />
              : (
                <div style={{ overflowX: "auto" }}>
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
                    <thead><tr>
                      {["When", "Operation", "Entity", "Entity id", "Actor role"].map(c =>
                        <th key={c} style={{ textAlign: "left", fontSize: 10.5, fontWeight: 700,
                          letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--text-tertiary)",
                          padding: "8px 10px", borderBottom: "1px solid var(--border)" }}>{c}</th>)}
                    </tr></thead>
                    <tbody>
                      {data.policy.audit!.items.map(a => (
                        <tr key={a.audit_id}>
                          <td style={td()}>{dt(a.created_at)}</td>
                          <td style={{ ...td(), fontWeight: 600 }}>{a.operation}</td>
                          <td style={td()}>{a.entity_type ?? "—"}</td>
                          <td style={{ ...td(), fontFamily: "monospace", fontSize: 10.5 }}>
                            {a.entity_id ? a.entity_id.slice(0, 12) : "—"}</td>
                          <td style={td()}>{a.actor_role ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </TableSurface>
                </div>
              )}
          </Card>
        </div>
      )}

      {/* ══ Buy credits panel (spec section 18) ═══════════════════════════ */}
      {buyOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 90,
          display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}
          onClick={() => setBuyOpen(false)}>
          <div onClick={e => e.stopPropagation()} style={{ width: "100%", maxWidth: 560 }}>
            <Card>
              <SectionTitle icon={<CreditCard size={16} />} title="Buy usage credits"
                subtitle="Admin-approved packages only — amounts are re-derived server-side from the published policy"
                actions={<Btn size="xs" variant="ghost" onClick={() => setBuyOpen(false)}>Close</Btn>} />
              {packages === null ? <Skeleton height={140} /> : packages.length === 0 ? (
                <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
                  borderRadius: 10, padding: "10px 12px", fontSize: 12.5, color: "var(--danger-text)" }}>
                  No approved credit package is available — the finance policy could not be resolved.
                </div>
              ) : (
                <>
                  <div style={{ display: "grid", gap: 8 }}>
                    {packages.map(p => (
                      <button key={p.package_key} onClick={() => setBuyQty(p.quantity)} style={{
                        textAlign: "left", cursor: "pointer", fontFamily: "inherit",
                        background: buyQty === p.quantity ? "var(--accent-muted)" : "var(--surface-sunken)",
                        border: `1px solid ${buyQty === p.quantity ? "var(--accent)" : "var(--border)"}`,
                        borderRadius: 12, padding: "11px 13px",
                      }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                          <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)" }}>{p.label}</span>
                          <span style={{ fontSize: 13.5, fontWeight: 800, color: "var(--text-primary)" }}>
                            {money(p.total_payable)}
                          </span>
                        </div>
                        <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", marginTop: 4 }}>
                          Base {money(p.base_credits)} + GST {p.gst_percent}% ({money(p.gst_amount)})
                          {" · "}usable credit posted: {money(p.base_credits)}
                        </div>
                      </button>
                    ))}
                  </div>
                  <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "12px 0 0" }}>
                    GST is platform tax and is never added to your usable credits. Credits are posted only
                    after ServiceOS verifies the payment signature server-side — a pending payment credits nothing.
                  </p>
                  {buyResult && (
                    <div style={{ marginTop: 12, background: "var(--info-bg)", border: "1px solid var(--info-border)",
                      borderRadius: 10, padding: "10px 12px", fontSize: 12.5, color: "var(--info-text)" }}>
                      {buyResult}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                    <Btn size="sm" variant="primary" loading={buyBusy} onClick={submitBuy}>Create order &amp; pay</Btn>
                    <Btn size="sm" variant="ghost" onClick={() => setBuyOpen(false)}>Cancel</Btn>
                  </div>
                </>
              )}
            </Card>
          </div>
        </div>
      )}
      {/* GST receipt for a credited top-up. `/top-ups/{id}` returns a real
          receipt object (number, base/GST split, transaction reference,
          policy version) but had no caller, so the document a tenant needs
          for their own books was unreachable from the product. */}
      {receipt && (
        <div role="dialog" aria-modal="true" onClick={e => { if (e.target === e.currentTarget) setReceipt(null); }}
          style={{ position: "fixed", inset: 0, zIndex: 900, display: "grid", placeItems: "center",
            background: "rgba(0,0,0,.5)", padding: 20 }}>
          <Card style={{ width: "min(520px, 100%)", maxHeight: "88vh", overflowY: "auto" }}>
            <SectionTitle icon={<Receipt size={16} />} title="Usage credit receipt"
              subtitle="Issued by ServiceOS for this credit purchase"
              actions={<Btn size="sm" variant="ghost" onClick={() => setReceipt(null)}>Close</Btn>} />
            {receipt.loading ? <Skeleton height={200} /> : !receipt.order.receipt ? (
              <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)",
                borderRadius: 10, padding: "10px 12px", fontSize: 12.5, color: "var(--text-secondary)" }}>
                A receipt is issued once the payment is credited to your wallet.
              </div>
            ) : (
              <>
                <Row label="Receipt number" value={receipt.order.receipt.receipt_number} />
                <Row label="Issued" value={dt(receipt.order.receipt.issued_at)} />
                <Row label="Order reference" value={receipt.order.order_ref ?? "—"} />
                <Row label="Base credit value" value={money(receipt.order.receipt.base_credit_value)} />
                <Row label="GST" value={money(receipt.order.receipt.gst_amount)} />
                <Row label="Total paid" value={money(receipt.order.receipt.total_paid)} />
                <Row label="Posted to usable wallet" value={money(receipt.order.receipt.usable_credit_posted)}
                  hint="GST never enters the wallet" />
                <Row label="Transaction reference" value={receipt.order.receipt.transaction_reference ?? "—"} />
                <Row label="Policy version" value={receipt.order.receipt.policy_version ?? "—"} />
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}

function lbl(): React.CSSProperties {
  return { display: "block", fontSize: 11.5, fontWeight: 600, color: "var(--text-secondary)",
    margin: "10px 0 5px" };
}
