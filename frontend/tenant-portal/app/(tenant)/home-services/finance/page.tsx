"use client";
/**
 * Home Services Finance Hub — TENANT-HS-FINANCE-HUB-01.
 *
 * Category-scoped consolidation of: finance readiness, usage-credit wallet,
 * credit purchase/top-ups, completed-job deductions, credit reversals,
 * security deposit, deposit refund requests, published finance policy,
 * financial activity and the reconciliation queue.
 *
 * Renders ONLY server-computed projections from
 * /v1/tenant/home-services/finance/* (app/engines/finance_hub/
 * tenant_hs_finance_router.py). This page never derives a balance, never
 * sums the usage-credit and security-deposit ledgers into one figure, and
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
import { Card, Badge, Btn, Skeleton } from "../../../../components/shared/ui";
import {
  homeServicesFinanceApi, ServiceOSError,
  type HsFinanceOverview, type HsFinanceTxnRow, type HsFinanceTxnPage,
  type HsCreditPackage, type HsTopupOrder, type HsRefundRequest,
  type HsFinanceReadinessCheck, type HsLiabilityHold,
} from "../../../../lib/api";
import { useRazorpayCheckout } from "../../../../hooks/useRazorpayCheckout";

/* ── tabs ─────────────────────────────────────────────────────────────────── */

const TABS = [
  { key: "overview",         label: "Overview",              icon: LayoutDashboard },
  { key: "usage-credits",    label: "Usage Credits",         icon: Wallet },
  { key: "security-deposit", label: "Security Deposit",      icon: Shield },
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
  const tone: Record<string, { bg: string; fg: string }> = {
    default: { bg: "var(--accent-muted)",  fg: "var(--accent)"        },
    success: { bg: "var(--success-bg)",    fg: "var(--success-text)"  },
    warning: { bg: "var(--warning-bg)",    fg: "var(--warning-text)"  },
    danger:  { bg: "var(--danger-bg)",     fg: "var(--danger-text)"   },
    info:    { bg: "var(--info-bg)",       fg: "var(--info-text)"     },
  };
  const t = tone[variant];
  return (
    <Card padding={16}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
            color: "var(--text-tertiary)", margin: "0 0 8px" }}>{label}</p>
          <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.1,
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{value}</div>
          {sub && <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "6px 0 0" }}>{sub}</p>}
        </div>
        <div style={{ width: 34, height: 34, borderRadius: 10, background: t.bg, color: t.fg,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          border: "1px solid var(--border)" }}>{icon}</div>
      </div>
    </Card>
  );
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
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: compact ? 720 : 1180 }}>
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
                  {r.receipt_available
                    ? <Btn size="xs" variant="ghost" icon={<Eye size={12} />}
                        onClick={() => onReceipt?.(r)}>Receipt</Btn>
                    : <span style={{ color: "var(--text-tertiary)", fontSize: 11.5 }}>—</span>}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
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
      No liability holds against your deposit.
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

/* ── refund request card ─────────────────────────────────────────────────── */

function RefundRequestCard({ rr }: { rr: HsRefundRequest }) {
  const idx = rr.workflow_stages.indexOf(rr.status);
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, padding: 14, marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace" }}>
          {rr.request_ref}
        </span>
        <Badge variant={statusVariant(rr.status)} size="md" dot>{rr.status_label}</Badge>
      </div>
      {/* workflow tracker — the real state machine, not decorative */}
      <div style={{ display: "flex", gap: 4, marginTop: 12, flexWrap: "wrap" }}>
        {rr.workflow_stages.map((s, i) => (
          <span key={s} style={{
            fontSize: 10, fontWeight: 700, letterSpacing: "0.03em", padding: "3px 8px", borderRadius: 999,
            background: idx >= 0 && i <= idx ? "var(--accent-muted)" : "var(--surface-sunken)",
            color: idx >= 0 && i <= idx ? "var(--accent)" : "var(--text-tertiary)",
            border: "1px solid var(--border)",
          }}>{humanStatus(s)}</span>
        ))}
      </div>
      <div style={{ marginTop: 12 }}>
        <Row label="Requested" value={money(rr.requested_amount)} />
        <Row label="Approved" value={rr.approved_amount ? money(rr.approved_amount) : "—"} />
        <Row label="Eligible at submission" value={money(rr.eligible_amount_snapshot)} />
        <Row label="Held / required at submission"
          value={`${money(rr.deposit_held_snapshot)} / ${money(rr.deposit_required_snapshot)}`} />
        <Row label="Qualifying technicians" value={rr.qualifying_technicians_snapshot} />
        <Row label="Policy version" value={rr.policy_version ?? "—"} />
        <Row label="Bank account" value={rr.bank_account_number_masked ?? "—"}
          hint={rr.bank_ifsc ?? undefined} />
        <Row label="Submitted" value={dt(rr.submitted_at)} />
        {rr.payout_reference && <Row label="Payout reference" value={rr.payout_reference} />}
      </div>
      {rr.reason && (
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "10px 0 0" }}>
          <strong style={{ color: "var(--text-primary)" }}>Reason: </strong>{rr.reason}
        </p>
      )}
      {rr.info_requested_note && (
        <div style={{ marginTop: 10, background: "var(--warning-bg)", border: "1px solid var(--warning-border)",
          borderRadius: 10, padding: "9px 11px", fontSize: 12, color: "var(--warning-text)" }}>
          <strong>Admin requested information: </strong>{rr.info_requested_note}
        </div>
      )}
      {rr.blockers.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em",
            color: "var(--text-tertiary)", margin: "0 0 6px" }}>
            Liabilities recorded at submission (reviewed by Admin before approval)
          </p>
          <HoldsList holds={rr.blockers} />
        </div>
      )}
    </div>
  );
}

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
  const [txnPage, setTxnPage] = useState(1);
  const [txnLoading, setTxnLoading] = useState(false);

  const [topups, setTopups] = useState<HsTopupOrder[] | null>(null);
  const [packages, setPackages] = useState<HsCreditPackage[] | null>(null);
  const [buyOpen, setBuyOpen] = useState(false);
  const [buyQty, setBuyQty] = useState(1);
  const [buyBusy, setBuyBusy] = useState(false);
  const [buyResult, setBuyResult] = useState<string | null>(null);

  const [refundOpen, setRefundOpen] = useState(false);
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [refundBank, setRefundBank] = useState("");
  const [refundAcct, setRefundAcct] = useState("");
  const [refundIfsc, setRefundIfsc] = useState("");
  const [refundBusy, setRefundBusy] = useState(false);
  const [refundMsg, setRefundMsg] = useState<{ ok: boolean; text: string } | null>(null);

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
    const p = Number(sp.get("page")); if (p > 0) setTxnPage(p);
  }, []);

  const pushUrl = useCallback((next: Partial<{ tab: string; ledger: string; status: string; page: number }>) => {
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

  const loadTxns = useCallback(() => {
    setTxnLoading(true);
    homeServicesFinanceApi.getTransactions({
      ledger: txnLedger || undefined, status: txnStatus || undefined,
      page: txnPage, page_size: 25,
    }).then(setTxns).catch(() => setTxns(null)).finally(() => setTxnLoading(false));
  }, [txnLedger, txnStatus, txnPage]);

  useEffect(() => { if (tab === "topups") loadTxns(); }, [tab, loadTxns]);
  useEffect(() => {
    if (tab !== "topups") return;
    homeServicesFinanceApi.listTopups({ page_size: 25 }).then(r => setTopups(r.items)).catch(() => setTopups(null));
  }, [tab]);

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

  const submitRefund = useCallback(() => {
    setRefundBusy(true); setRefundMsg(null);
    homeServicesFinanceApi.createRefundRequest({
      requested_amount: refundAmount, reason: refundReason,
      bank_account_name: refundBank || undefined,
      bank_account_number: refundAcct || undefined,
      bank_ifsc: refundIfsc || undefined,
    })
      .then(rr => { setRefundMsg({ ok: true, text: `Refund request ${rr.request_ref} submitted for Admin review.` }); setRefundOpen(false); load(); })
      .catch((e: unknown) => setRefundMsg({ ok: false, text: e instanceof ServiceOSError ? e.message : "Could not submit the refund request." }))
      .finally(() => setRefundBusy(false));
  }, [refundAmount, refundReason, refundBank, refundAcct, refundIfsc, load]);

  const doExport = useCallback(() => {
    setExportMsg("Preparing…");
    homeServicesFinanceApi.exportStatement({ ledger: txnLedger || undefined })
      .then(r => {
        const blob = new Blob([r.csv], { type: "text/csv;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob); a.download = r.filename; a.click();
        URL.revokeObjectURL(a.href);
        setExportMsg(`Exported ${r.row_count} row(s) — your tenant, Home Services only.`);
      })
      .catch((e: unknown) => setExportMsg(e instanceof ServiceOSError ? e.message : "Export failed."));
  }, [txnLedger]);

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
            Manage usage credits, security deposit and finance readiness for this Home Services workspace.
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
        <div className="fh-kpis">{[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} height={104} radius={20} />)}</div>
      ) : kpis && (
        <div className="fh-kpis">
          <KpiCard label="Usable credits" value={moneyCompact(kpis.usable_credits)}
            sub={data?.usage_credits.is_low_balance ? "Below low-balance threshold" : "Available to spend on jobs"}
            icon={<Wallet size={17} />} variant={data?.usage_credits.is_low_balance ? "warning" : "success"} />
          <KpiCard label="Credits used this month" value={moneyCompact(kpis.credits_used_this_month)}
            sub={`${data?.usage_credits.completed_job_deductions ?? 0} completed-job deduction(s) all-time`}
            icon={<TrendingDown size={17} />} variant="info" />
          <KpiCard label="Deposit held" value={moneyCompact(kpis.deposit_held)}
            sub="Held separately from usage credits"
            icon={<Shield size={17} />} variant="default" />
          <KpiCard label="Deposit required" value={moneyCompact(kpis.deposit_required)}
            sub={`${data?.security_deposit.qualifying_technician_count ?? 0} qualifying technician(s)`}
            icon={<Shield size={17} />}
            variant={Number(data?.security_deposit.top_up_due ?? 0) > 0 ? "danger" : "default"} />
          <KpiCard label="Action items" value={kpis.action_items}
            sub="Open finance items needing you"
            icon={<ListChecks size={17} />} variant={kpis.action_items > 0 ? "warning" : "success"} />
          <KpiCard label="Finance status" value={kpis.finance_status_label}
            sub="Server-computed readiness"
            icon={statusVar === "success" ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}
            variant={statusVar} />
        </div>
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

          {/* 3 + 4. Wallet and deposit — visually SEPARATE cards, never summed */}
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
              <SectionTitle icon={<Shield size={16} />} title="Security deposit"
                subtitle="Held separately — never combined with usage credits"
                actions={<Badge variant={data.security_deposit.status === "fully_funded" ? "success"
                  : data.security_deposit.status === "top_up_due" || data.security_deposit.status === "not_paid" ? "danger" : "info"}
                  size="sm">{humanStatus(data.security_deposit.status)}</Badge>} />
              <div style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", marginBottom: 12 }}>
                {money(data.security_deposit.deposit_held)}
              </div>
              <Row label="Qualifying technicians" value={data.security_deposit.qualifying_technician_count}
                hint={data.security_deposit.technician_count_policy ?? undefined} />
              <Row label="Amount per technician" value={money(data.security_deposit.amount_per_technician)} />
              <Row label="Minimum deposit" value={money(data.security_deposit.minimum_deposit)} />
              <Row label="Required" value={money(data.security_deposit.deposit_required)} />
              <Row label="Pending payment" value={money(data.security_deposit.deposit_pending)} />
              <Row label="Top-up due" value={money(data.security_deposit.top_up_due)} />
              <Row label="Potentially refundable excess" value={money(data.security_deposit.refundable_excess)} />
              <Row label="Eligible to request now" value={money(data.security_deposit.eligible_refund_amount)} />
              <Row label="Policy version" value={data.security_deposit.policy_version ?? "—"} />
              <div style={{ marginTop: 12 }}>
                <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em",
                  color: "var(--text-tertiary)", margin: "0 0 6px" }}>Liability holds</p>
                <HoldsList holds={data.security_deposit.liability_holds} />
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
                <Btn size="sm" variant="secondary" onClick={() => goTab("security-deposit")}>Manage deposit</Btn>
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
                  <Row label="Deposit rule" value={data.policy.deposit_rule ?? "—"} />
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
                    if (q.filter && typeof q.filter.ledger === "string") { setTxnLedger(q.filter.ledger); pushUrl({ ledger: q.filter.ledger }); }
                    if (q.filter && typeof q.filter.status === "string") { setTxnStatus(q.filter.status); pushUrl({ status: q.filter.status }); }
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

      {/* ══ SECURITY DEPOSIT ══════════════════════════════════════════════ */}
      {!loading && data && tab === "security-deposit" && (
        <div style={{ display: "grid", gap: 16 }}>
          <div className="fh-two">
            <Card>
              <SectionTitle icon={<Shield size={16} />} title="Deposit position"
                subtitle="Independent of the usage-credit wallet" />
              <div style={{ fontSize: 34, fontWeight: 800, color: "var(--text-primary)" }}>
                {money(data.security_deposit.deposit_held)}
              </div>
              <Row label="Gross paid to date" value={money(data.security_deposit.deposit_held_gross)} />
              <Row label="Refunded to date" value={money(data.security_deposit.deposit_refunded_total)} />
              <Row label="Required" value={money(data.security_deposit.deposit_required)}
                hint={`${data.security_deposit.qualifying_technician_count} qualifying technician(s)`} />
              <Row label="Per technician" value={money(data.security_deposit.amount_per_technician)} />
              <Row label="Top-up due" value={money(data.security_deposit.top_up_due)} />
              <Row label="Potentially refundable excess" value={money(data.security_deposit.refundable_excess)} />
              <Row label="Eligible to request now" value={money(data.security_deposit.eligible_refund_amount)} />
              <Row label="Last deposit transaction"
                value={data.security_deposit.last_transaction
                  ? String((data.security_deposit.last_transaction as Record<string, unknown>).gateway_order_id ?? "—")
                  : "None"} />
              {Number(data.security_deposit.top_up_due) > 0 && (
                <div style={{ marginTop: 12, background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
                  borderRadius: 10, padding: "10px 12px", fontSize: 12.5, color: "var(--danger-text)" }}>
                  Your technician headcount requires {money(data.security_deposit.deposit_required)}.
                  A top-up of {money(data.security_deposit.top_up_due)} is outstanding — your held balance was
                  not changed silently, and existing jobs are unaffected.
                </div>
              )}
            </Card>
            <Card>
              <SectionTitle icon={<AlertTriangle size={16} />} title="Liability & hold review"
                subtitle="Checked by Admin before any refund is approved" />
              <HoldsList holds={data.security_deposit.liability_holds} />
              <Row label="Holds with a quantified amount" value={money(data.security_deposit.liability_holds_total)} />
              <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "12px 0 0" }}>
                Reducing your technician count never triggers an automatic refund and never rewrites the
                historical held ledger — it only makes an excess potentially refundable, which you must
                request below.
              </p>
              <div style={{ marginTop: 14 }}>
                <Btn size="sm" variant="primary" disabled={Number(data.security_deposit.eligible_refund_amount) <= 0}
                  onClick={() => { setRefundOpen(true); setRefundAmount(data.security_deposit.eligible_refund_amount); setRefundMsg(null); }}>
                  Request deposit refund
                </Btn>
                {Number(data.security_deposit.eligible_refund_amount) <= 0 && (
                  <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
                    Nothing is refundable right now — your held deposit does not exceed the required amount.
                  </p>
                )}
              </div>
            </Card>
          </div>

          {refundMsg && (
            <div style={{ background: refundMsg.ok ? "var(--success-bg)" : "var(--danger-bg)",
              border: `1px solid ${refundMsg.ok ? "var(--success-border)" : "var(--danger-border)"}`,
              color: refundMsg.ok ? "var(--success-text)" : "var(--danger-text)",
              borderRadius: 12, padding: "11px 13px", fontSize: 13 }}>{refundMsg.text}</div>
          )}

          {refundOpen && (
            <Card>
              <SectionTitle icon={<Shield size={16} />} title="New deposit refund request"
                subtitle="Your business cannot approve or process its own refund — ServiceOS Admin decides" />
              <div className="fh-two" style={{ gap: 12 }}>
                <div>
                  <label style={lbl()}>Amount to request (max {money(data.security_deposit.eligible_refund_amount)})</label>
                  <input className="fh-input" value={refundAmount} onChange={e => setRefundAmount(e.target.value)} />
                  <label style={lbl()}>Reason</label>
                  <textarea className="fh-input" rows={3} value={refundReason}
                    onChange={e => setRefundReason(e.target.value)}
                    placeholder="Why is this deposit no longer required?" />
                </div>
                <div>
                  <label style={lbl()}>Bank account name</label>
                  <input className="fh-input" value={refundBank} onChange={e => setRefundBank(e.target.value)} />
                  <label style={lbl()}>Account number</label>
                  <input className="fh-input" value={refundAcct} onChange={e => setRefundAcct(e.target.value)} />
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                    Only the last 4 digits are stored.
                  </p>
                  <label style={lbl()}>IFSC</label>
                  <input className="fh-input" value={refundIfsc} onChange={e => setRefundIfsc(e.target.value)} />
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                <Btn size="sm" variant="primary" loading={refundBusy}
                  disabled={!refundAmount || refundReason.trim().length < 5} onClick={submitRefund}>
                  Submit request
                </Btn>
                <Btn size="sm" variant="ghost" onClick={() => setRefundOpen(false)}>Cancel</Btn>
              </div>
            </Card>
          )}

          <Card>
            <SectionTitle icon={<ListChecks size={16} />} title="Refund requests"
              subtitle={data.security_deposit.refund_requests?.approval_note
                ?? "Approval is an Admin-only action."} />
            {(data.security_deposit.refund_requests?.items.length ?? 0) === 0
              ? <EmptyRow text="You have not submitted any deposit refund requests." />
              : data.security_deposit.refund_requests!.items.map(rr =>
                  <RefundRequestCard key={rr.refund_request_id} rr={rr} />)}
          </Card>

          <Card padding={0}>
            <div style={{ padding: "18px 18px 0" }}>
              <SectionTitle icon={<Receipt size={16} />} title="Security-deposit ledger"
                subtitle="Ledger B only — usage-credit balance intentionally shows — on every row" />
            </div>
            {data.security_deposit.ledger
              ? <ActivityTable page={data.security_deposit.ledger} />
              : <EmptyRow text="No deposit activity yet." />}
          </Card>
        </div>
      )}

      {/* ══ TOP-UPS & TRANSACTIONS ════════════════════════════════════════ */}
      {!loading && data && tab === "topups" && (
        <div style={{ display: "grid", gap: 16 }}>
          <Card>
            <SectionTitle icon={<CreditCard size={16} />} title="Credit top-up orders"
              subtitle="A pending payment never credits the wallet; a duplicate gateway callback never double-credits"
              actions={<Btn size="sm" variant="primary" icon={<CreditCard size={13} />} onClick={openBuy}>Buy usage credits</Btn>} />
            {topups === null ? <Skeleton height={120} /> : topups.length === 0
              ? <EmptyRow text="No credit top-up orders yet." />
              : (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 900 }}>
                    <thead><tr>
                      {["Created", "Order ref", "Base credits", "GST", "Total payable", "Payment", "Wallet", "Gateway payment"].map(c =>
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
                        </tr>
                      ))}
                    </tbody>
                  </table>
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
                    <input className="fh-input" style={{ width: 150 }} placeholder="Status…" value={txnStatus}
                      onChange={e => { setTxnStatus(e.target.value); setTxnPage(1); pushUrl({ status: e.target.value, page: 1 }); }} />
                    <Btn size="sm" variant="secondary" icon={<Download size={13} />} onClick={doExport}>Export</Btn>
                  </>
                } />
            </div>
            {txnLoading ? <div style={{ padding: 18 }}><Skeleton height={160} /></div>
              : txns ? <>
                  <ActivityTable page={txns} />
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    gap: 12, padding: "12px 18px", borderTop: "1px solid var(--border)", flexWrap: "wrap" }}>
                    <span style={{ fontSize: 11.5, color: "var(--text-tertiary)" }}>
                      {txns.total} row(s) · page {txns.page}
                      {" · "}
                      {Object.entries(txns.ledger_totals as Record<string, { rows: number }>).map(([k, v]) => `${k}: ${v.rows}`).join("  ·  ")}
                    </span>
                    <div style={{ display: "flex", gap: 6 }}>
                      <Btn size="xs" variant="secondary" disabled={txns.page <= 1}
                        onClick={() => { const p = txns.page - 1; setTxnPage(p); pushUrl({ page: p }); }}>Previous</Btn>
                      <Btn size="xs" variant="secondary" disabled={txns.page * txns.page_size >= txns.total}
                        onClick={() => { const p = txns.page + 1; setTxnPage(p); pushUrl({ page: p }); }}>Next</Btn>
                    </div>
                  </div>
                </>
              : <EmptyRow text="Transactions could not be loaded. Please retry — no figures are shown rather than a misleading zero." />}
          </Card>
        </div>
      )}

      {/* ══ POLICY & AUDIT ════════════════════════════════════════════════ */}
      {!loading && data && tab === "policy" && (
        <div style={{ display: "grid", gap: 16 }}>
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
                  <Row label="Deposit required" value={data.policy.deposit_required ? "Yes" : "No"} />
                  <Row label="Deposit calculation" value={data.policy.deposit_calculation_mode ?? "—"} />
                  <Row label="Per technician" value={money(data.policy.deposit_amount_per_technician)} />
                  <Row label="Minimum deposit" value={money(data.policy.minimum_deposit)} />
                  <Row label="Technician count policy" value={data.policy.technician_count_policy ?? "—"} />
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
                  <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
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
                  </table>
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
    </div>
  );
}

function lbl(): React.CSSProperties {
  return { display: "block", fontSize: 11.5, fontWeight: 600, color: "var(--text-secondary)",
    margin: "10px 0 5px" };
}
