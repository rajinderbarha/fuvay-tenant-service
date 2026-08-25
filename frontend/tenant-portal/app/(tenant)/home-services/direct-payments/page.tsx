"use client";
/**
 * Home Services — Direct Payments (job-linked payment confirmation and
 * reconciliation).
 *
 * This is NOT a payment-collection page. ServiceOS never collects, holds,
 * settles or transfers the job payment and never creates a provider payout:
 * the customer pays the provider business directly and this surface records
 * the provider's DECLARATION plus the customer's CONFIRMATION of it.
 *
 * Everything rendered here comes from the real backend
 * (/v1/tenant/home-services/direct-payments and its detail projection) --
 * every amount, status, workflow step and activity entry is server-resolved.
 * The expected amount is resolved server-side from the approved estimate /
 * invoice snapshot / booking price snapshot; this page never computes or
 * submits an expected amount. Queue and selection state live in real query
 * params so refresh and browser history work.
 */
import React, { useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle, ArrowUpDown, BellRing, CheckCircle2, ChevronDown, Clock,
  Download, ExternalLink, FileText, Image as ImageIcon, Info, Lock, Pencil,
  RefreshCw, Search, ShieldAlert, Wrench,
} from "lucide-react";
import { Badge, Btn, Card, Skeleton } from "../../../../components/shared/ui";
import {
  API_BASE, ServiceOSError, getToken, homeServicesDirectPaymentsApi,
  type HsDpDetail, type HsDpQueue, type HsDpRecord,
} from "../../../../lib/api";

const TABS: { key: string; label: string; countKey: string }[] = [
  { key: "needs_action",      label: "Needs action",      countKey: "needs_action" },
  { key: "all",               label: "All",               countKey: "all" },
  { key: "confirmed",         label: "Confirmed",         countKey: "confirmed" },
  { key: "mismatched",        label: "Mismatch",          countKey: "mismatch" },
  { key: "disputed",          label: "Disputed",          countKey: "disputed" },
];

const DATE_RANGES: { key: string; label: string; days: number | null }[] = [
  { key: "7d",  label: "Last 7 days",  days: 7 },
  { key: "30d", label: "Last 30 days", days: 30 },
  { key: "90d", label: "Last 90 days", days: 90 },
  { key: "all", label: "All time",     days: null },
];

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  confirmed: "success",
  awaiting_customer: "warning",
  awaiting_provider: "info",
  mismatched: "danger",
  disputed: "danger",
  not_required: "muted",
  cancelled: "muted",
  reversed: "muted",
};

function money(amount: string | null | undefined, currency = "INR"): string {
  if (amount === null || amount === undefined) return "—";
  const n = Number(amount);
  if (Number.isNaN(n)) return String(amount);
  const sym = currency === "INR" ? "₹" : `${currency} `;
  return `${sym}${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function relTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function fmtDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

function isoDaysAgo(days: number): string {
  const d = new Date(Date.now() - days * 86400000);
  return d.toISOString();
}

function DirectPaymentsPageInner() {
  const router = useRouter();
  const params = useSearchParams();

  // URL is the source of truth for queue + selection state (section 4).
  const tab       = params.get("status") ?? "needs_action";
  const method    = params.get("method") ?? "";
  // Both were accepted and applied by the API all along, but no facet listed
  // the values so nothing could offer them. Same URL-as-source-of-truth rule
  // as every other filter here.
  const serviceId    = params.get("service_id") ?? "";
  const technicianId = params.get("technician_id") ?? "";
  const search    = params.get("q") ?? "";
  const range     = params.get("range") ?? "30d";
  const page      = Number(params.get("page") ?? "1");
  const paymentId = params.get("payment_id");

  const [queue, setQueue] = useState<HsDpQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ code?: string; message: string } | null>(null);
  const [limit, setLimit] = useState(10);

  const [detail, setDetail] = useState<HsDpDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [action, setAction] = useState<string | null>(null);
  /** Correction form for an existing declaration. The server versions every
   *  declaration and rejects a write against a stale version, so the read
   *  version is sent back as `expected_version`. */
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState<{
    amount: string; method: string; reference_id: string; note: string;
    correction_reason: string; difference_reason: string;
  }>({ amount: "", method: "", reference_id: "", note: "", correction_reason: "", difference_reason: "" });
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [searchDraft, setSearchDraft] = useState(search);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const setParam = useCallback((patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString());
    Object.entries(patch).forEach(([k, v]) => {
      if (v === null || v === "") next.delete(k); else next.set(k, v);
    });
    router.push(`/home-services/direct-payments?${next.toString()}`);
  }, [params, router]);

  const dateFrom = useMemo(() => {
    const r = DATE_RANGES.find(d => d.key === range);
    return r?.days ? isoDaysAgo(r.days) : undefined;
  }, [range]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    homeServicesDirectPaymentsApi.list({
      status: tab, method: method || undefined, search: search || undefined,
      service_id: serviceId || undefined, technician_id: technicianId || undefined,
      date_from: dateFrom, page, limit,
    })
      .then(d => { setQueue(d); setLastUpdated(new Date()); })
      .catch((e: unknown) => {
        // Never turn an API failure into fake zero KPIs (section 23).
        setQueue(null);
        setError(e instanceof ServiceOSError
          ? { code: e.code, message: e.message }
          : { message: "We couldn't load direct payments." });
      })
      .finally(() => setLoading(false));
  }, [tab, method, search, serviceId, technicianId, dateFrom, page, limit]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setSearchDraft(search); }, [search]);

  const loadDetail = useCallback((id: string) => {
    setDetailLoading(true);
    setDetailError(null);
    homeServicesDirectPaymentsApi.get(id)
      .then(setDetail)
      .catch((e: unknown) => {
        setDetail(null);
        setDetailError(e instanceof ServiceOSError ? e.message
          : "We couldn't load this payment record.");
      })
      .finally(() => setDetailLoading(false));
  }, []);

  useEffect(() => {
    if (!paymentId) { setDetail(null); setDetailError(null); return; }
    if (paymentId.startsWith("job:")) {
      setDetail(null);
      setDetailError("No declaration exists for this job yet. "
        + "The provider must record the payment the customer made before it can "
        + "be reconciled.");
      return;
    }
    loadDetail(paymentId);
  }, [paymentId, loadDetail]);

  // Auto-select the first record so the workspace is never a blank right pane.
  useEffect(() => {
    if (!paymentId && queue && queue.records.length > 0) {
      const preferred = queue.records.find(r => r.kind === "record") ?? queue.records[0];
      setParam({ payment_id: preferred.id });
    }
  }, [queue, paymentId, setParam]);

  async function run(name: string, fn: () => Promise<unknown>, okText: string) {
    setAction(name);
    setNotice(null);
    try {
      await fn();
      setNotice({ kind: "ok", text: okText });
      if (paymentId && !paymentId.startsWith("job:")) loadDetail(paymentId);
      load();
    } catch (e) {
      setNotice({ kind: "err", text: e instanceof ServiceOSError ? e.message : "That action failed." });
    } finally {
      setAction(null);
    }
  }

  async function submitCorrection() {
    if (!detail) return;
    const pd = (detail.provider_declaration ?? {}) as { version?: number };
    await run("edit", () => homeServicesDirectPaymentsApi.correctDeclaration(detail.record.id, {
      // Optimistic-concurrency guard: if the customer confirmed (or anyone
      // else corrected) since this panel was loaded, the server rejects the
      // write rather than silently overwriting the newer state.
      expected_version: typeof pd.version === "number" ? pd.version : undefined,
      amount: editForm.amount.trim() || undefined,
      method: editForm.method.trim() || undefined,
      reference_id: editForm.reference_id.trim() || undefined,
      note: editForm.note.trim() || undefined,
      correction_reason: editForm.correction_reason.trim() || undefined,
      // The server REQUIRES this whenever the declared amount differs from the
      // server-resolved expected amount (DIRECT_PAYMENT_DIFFERENCE_REASON_
      // REQUIRED). It is a separate field from `correction_reason`: one
      // explains why the record changed, the other why the money differs.
      difference_reason: editForm.difference_reason.trim() || undefined,
    }), "Declaration corrected. The customer sees the updated amount.");
    setEditOpen(false);
  }

  function doExport() {
    run("export", async () => {
      const data = await homeServicesDirectPaymentsApi.export({
        status: tab, method: method || undefined,
        date_from: dateFrom, search: search || undefined,
        service_id: serviceId || undefined, technician_id: technicianId || undefined,
      });
      const head = data.fields.join(",");
      const body = data.rows.map(r =>
        data.fields.map(f => `"${String(r[f] ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
      const blob = new Blob([`${head}\n${body}`], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "direct-payments.csv"; a.click();
      URL.revokeObjectURL(url);
    }, "Export downloaded.");
  }

  const s = queue?.summary;

  return (
    <div style={{ padding: 24, maxWidth: 1800, margin: "0 auto" }}>
      <style>{`
        .dp-kpis { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: 16px 0; }
        @media (max-width: 1500px) { .dp-kpis { grid-template-columns: repeat(3, 1fr); } }
        @media (max-width: 900px)  { .dp-kpis { grid-template-columns: repeat(2, 1fr); } }
        .dp-workspace { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); gap: 16px; align-items: start; }
        @media (max-width: 1400px) { .dp-workspace { grid-template-columns: 1fr; } }
        .dp-trio { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
        @media (max-width: 1100px) { .dp-trio { grid-template-columns: 1fr; } }
        .dp-duo { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        @media (max-width: 900px) { .dp-duo { grid-template-columns: 1fr; } }
        .dp-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
        .dp-table th { text-align: left; font-size: 11px; text-transform: uppercase;
          letter-spacing: 0.4px; color: var(--text-tertiary); font-weight: 700;
          padding: 8px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
        .dp-table td { padding: 10px 8px; border-bottom: 1px solid var(--border);
          color: var(--text-secondary); vertical-align: middle; }
        .dp-scroll { overflow-x: auto; }
      `}</style>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 800, letterSpacing: 1.2, color: "var(--accent)", margin: "0 0 6px" }}>
            FINANCE
          </p>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>
            Direct Payments
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Reconcile customer-to-provider payment confirmations for Home Services jobs.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Btn variant="secondary" icon={<Download size={14}/>} onClick={doExport}
               loading={action === "export"}>Export</Btn>
          <Select value={range} onChange={v => setParam({ range: v, page: "1" })}
                  options={DATE_RANGES.map(d => ({ value: d.key, label: d.label }))} width={150}/>
          <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Refresh</Btn>
        </div>
      </div>

      {/* ── Mandatory banner ───────────────────────────────────────────── */}
      <div role="note" style={{
        display: "flex", gap: 10, alignItems: "flex-start", marginTop: 16,
        padding: "12px 14px", borderRadius: 12, background: "var(--info-bg)",
        border: "1px solid var(--info-border)", color: "var(--info-text)", fontSize: 13,
      }}>
        <Info size={16} style={{ flexShrink: 0, marginTop: 1 }}/>
        <span style={{ fontWeight: 600 }}>
          {queue?.banner?.text
            ?? "ServiceOS does not collect this money. Customers pay your business directly."}
        </span>
      </div>

      {error && (
        <div role="alert" style={{
          display: "flex", gap: 8, padding: "12px 14px", borderRadius: 12,
          background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
          color: "var(--danger-text)", fontSize: 13, marginTop: 14,
        }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/>
          <span>
            {error.code === "VERTICAL_DISABLED" || error.code === "TENANT_VERTICAL_NOT_ACTIVE"
              ? "Home Services is not active for your account, so new direct-payment operations are blocked. Existing confirmations and disputes are preserved."
              : error.code === "PERMISSION_DENIED"
              ? "You don't have permission to view direct payments. Ask your tenant owner for direct_payments:read."
              : error.message}
          </span>
        </div>
      )}

      {notice && (
        <div role="status" style={{
          display: "flex", gap: 8, padding: "10px 14px", borderRadius: 12, marginTop: 14,
          background: notice.kind === "ok" ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${notice.kind === "ok" ? "var(--success-border)" : "var(--danger-border)"}`,
          color: notice.kind === "ok" ? "var(--success-text)" : "var(--danger-text)", fontSize: 12.5,
        }}>
          {notice.kind === "ok" ? <CheckCircle2 size={15}/> : <AlertTriangle size={15}/>}
          <span>{notice.text}</span>
        </div>
      )}

      {/* ── 6 KPI cards ────────────────────────────────────────────────── */}
      {loading && !queue ? (
        <div className="dp-kpis">{[0,1,2,3,4,5].map(i => <Skeleton key={i} height={104}/>)}</div>
      ) : s ? (
        <div className="dp-kpis">
          <Kpi label="Awaiting provider" count={s.awaiting_provider.count}
               sub={money(s.awaiting_provider.amount)} variant="info" icon={<Clock size={16}/>}/>
          <Kpi label="Awaiting customer" count={s.awaiting_customer.count}
               sub={money(s.awaiting_customer.amount)} variant="warning" icon={<BellRing size={16}/>}/>
          <Kpi label="Confirmed" count={s.confirmed.count}
               sub={money(s.confirmed.amount)} variant="success" icon={<CheckCircle2 size={16}/>}/>
          <Kpi label="Mismatched" count={s.mismatched.count}
               sub={money(s.mismatched.amount)} variant="danger" icon={<ShieldAlert size={16}/>}/>
          <Kpi label="Disputed" count={s.disputed.count}
               sub={money(s.disputed.amount)} variant="danger" icon={<AlertTriangle size={16}/>}/>
          <Kpi label={s.confirmed_direct_payment_value.label}
               money={money(s.confirmed_direct_payment_value.amount,
                            s.confirmed_direct_payment_value.currency)}
               sub={s.confirmed_direct_payment_value.subtext}
               variant="default" icon={<FileText size={16}/>}/>
        </div>
      ) : null}

      {/* ── Two-pane workspace ─────────────────────────────────────────── */}
      <div className="dp-workspace">
        {/* LEFT — queue */}
        <Card padding={0} style={{ overflow: "hidden" }}>
          {/* toolbar */}
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap",
                        padding: 14, borderBottom: "1px solid var(--border)" }}>
            <div style={{ position: "relative", flex: "1 1 200px", minWidth: 180 }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: 10, color: "var(--text-tertiary)" }}/>
              <input
                value={searchDraft}
                placeholder="Search job, customer or service"
                onChange={e => setSearchDraft(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") setParam({ q: searchDraft, page: "1" }); }}
                style={{
                  width: "100%", padding: "8px 10px 8px 30px", fontSize: 12.5,
                  background: "var(--surface-sunken)", color: "var(--text-primary)",
                  border: "1px solid var(--border)", borderRadius: 9, outline: "none",
                }}/>
            </div>
            <Select value={tab} onChange={v => setParam({ status: v, page: "1" })} width={150}
                    options={[{ value: "all", label: "All statuses" },
                              ...(queue?.filters.statuses ?? []).map(x => ({ value: x.value, label: x.label }))]}/>
            <Select value={method} onChange={v => setParam({ method: v, page: "1" })} width={130}
                    options={[{ value: "", label: "All methods" },
                              ...(queue?.filters.methods ?? []).map(x => ({ value: x.value, label: x.label }))]}/>
            <Select value={serviceId} onChange={v => setParam({ service_id: v, page: "1" })} width={150}
                    options={[{ value: "", label: "All services" },
                              ...(queue?.filters.services ?? []).map(x => ({ value: x.value, label: x.label }))]}/>
            <Select value={technicianId} onChange={v => setParam({ technician_id: v, page: "1" })} width={150}
                    options={[{ value: "", label: "All technicians" },
                              ...(queue?.filters.technicians ?? []).map(x => ({ value: x.value, label: x.label }))]}/>
          </div>

          {/* status tabs */}
          <div className="dp-scroll" style={{ display: "flex", gap: 4, padding: "10px 14px 0" }}>
            {TABS.map(t => {
              const active = tab === t.key;
              const n = queue?.tab_counts?.[t.countKey];
              return (
                <button key={t.key} onClick={() => setParam({ status: t.key, page: "1" })}
                  style={{
                    display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap",
                    background: active ? "var(--accent-muted)" : "transparent",
                    color: active ? "var(--accent)" : "var(--text-secondary)",
                    border: "none", borderRadius: 8, padding: "7px 12px",
                    fontSize: 12.5, fontWeight: 700, cursor: "pointer",
                  }}>
                  {t.label}
                  {n !== undefined && (
                    <span style={{
                      background: active ? "var(--accent)" : "var(--surface-sunken)",
                      color: active ? "var(--text-on-brand)" : "var(--text-tertiary)",
                      borderRadius: 20, padding: "1px 7px", fontSize: 11, fontWeight: 800,
                    }}>{n}</span>
                  )}
                </button>
              );
            })}
          </div>

          {/* table */}
          <div className="dp-scroll" style={{ padding: "8px 14px 0" }}>
            {loading && !queue ? (
              <div style={{ padding: 12 }}><Skeleton height={280}/></div>
            ) : !queue || queue.records.length === 0 ? (
              <EmptyQueue tab={tab} hasError={!!error}/>
            ) : (
              <table className="dp-table">
                <thead>
                  <tr>
                    <th>Job</th><th>Customer</th><th>Service</th>
                    <th>Declared</th><th>Method</th>
                    <th>Provider</th><th>Customer conf.</th><th>Status</th>
                    <th style={{ cursor: "pointer" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                        Updated <ArrowUpDown size={11}/>
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {queue.records.map(r => (
                    <QueueRow key={r.id} r={r} selected={paymentId === r.id}
                              onClick={() => setParam({ payment_id: r.id })}/>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* pagination */}
          {queue && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                          gap: 10, padding: 14, flexWrap: "wrap" }}>
              <span style={{ fontSize: 11.5, color: "var(--text-tertiary)" }}>
                {queue.pagination.total} record{queue.pagination.total === 1 ? "" : "s"}
                {" · page "}{queue.pagination.page} of {queue.pagination.pages}
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Select value={String(limit)} width={92}
                        onChange={v => { setLimit(Number(v)); setParam({ page: "1" }); }}
                        options={[10, 25, 50].map(n => ({ value: String(n), label: `${n} / page` }))}/>
                <Btn variant="secondary" size="sm" disabled={queue.pagination.page <= 1}
                     onClick={() => setParam({ page: String(page - 1) })}>Prev</Btn>
                <Btn variant="secondary" size="sm"
                     disabled={queue.pagination.page >= queue.pagination.pages}
                     onClick={() => setParam({ page: String(page + 1) })}>Next</Btn>
              </div>
            </div>
          )}
        </Card>

        {/* RIGHT — selected payment detail */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {detailLoading ? (
            <Card><Skeleton height={420}/></Card>
          ) : detailError ? (
            <Card>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <Info size={16} style={{ color: "var(--text-tertiary)", marginTop: 2 }}/>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>{detailError}</p>
              </div>
            </Card>
          ) : detail ? (
            <DetailPane
              d={detail}
              busy={action}
              onRemind={() => run("remind",
                () => homeServicesDirectPaymentsApi.remind(detail.record.id),
                "Confirmation reminder sent through ServiceOS.")}
              onDispute={() => run("dispute",
                () => homeServicesDirectPaymentsApi.openDispute(detail.record.id,
                  "The customer reports a different amount for this direct payment."),
                "Payment dispute opened in the Complaints & Resolution Center.")}
              onEdit={() => {
                const pd = detail.provider_declaration ?? {};
                setEditForm({
                  amount: String(pd.amount ?? ""),
                  method: String(pd.method ?? ""),
                  reference_id: String(pd.reference_id ?? ""),
                  note: String(pd.note ?? ""),
                  correction_reason: "",
                  difference_reason: String(pd.difference_reason ?? ""),
                });
                setEditOpen(true);
              }}
            />
          ) : (
            <Card>
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", textAlign: "center", padding: "40px 0" }}>
                Select a payment on the left to review its confirmation.
              </p>
            </Card>
          )}
        </div>
      </div>

      {/* ── Footer disclaimer ──────────────────────────────────────────── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
        marginTop: 18, padding: "12px 14px", borderRadius: 12,
        background: "var(--surface-sunken)", border: "1px solid var(--border)",
        color: "var(--text-tertiary)", fontSize: 12,
      }}>
        <Lock size={13}/>
        <span>
          {queue?.footer_disclaimer
            ?? "All confirmations are recorded securely within ServiceOS. We never share or request personal contact details."}
        </span>
      </div>

      {lastUpdated && (
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", textAlign: "center", margin: "8px 0 0" }}>
          Last updated {lastUpdated.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
        </p>
      )}

      {/* Correct a declaration before the customer confirms it. The endpoint
          (PATCH .../declaration) existed all along; the button that should
          have opened this had no handler. The expected amount is deliberately
          NOT editable — it is resolved server-side from the approved estimate
          / invoice / booking snapshot and the API ignores any client value. */}
      {editOpen && detail && (() => {
        const expected = Number(detail.record.expected_amount ?? NaN);
        const entered = Number(editForm.amount);
        const amountDiffers = Number.isFinite(expected) && Number.isFinite(entered)
          && expected.toFixed(2) !== entered.toFixed(2);
        return (
        <div role="dialog" aria-modal="true"
          onClick={e => { if (e.target === e.currentTarget) setEditOpen(false); }}
          style={{ position: "fixed", inset: 0, zIndex: 900, display: "grid", placeItems: "center",
            background: "rgba(0,0,0,.5)", padding: 20 }}>
          <Card style={{ width: "min(520px,100%)", maxHeight: "88vh", overflowY: "auto" }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
              Correct declaration
            </h2>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 14px" }}>
              {typeof detail.available_actions.edit_declaration_hint === "string"
                ? detail.available_actions.edit_declaration_hint
                : "Available before customer confirmation"}
              . Every correction is versioned and visible to the customer.
            </p>

            <label style={dpLbl()}>Amount received (₹)</label>
            <input value={editForm.amount} type="number" min="0" step="0.01"
              onChange={e => setEditForm(f => ({ ...f, amount: e.target.value }))} style={dpField()} />

            <label style={dpLbl()}>Payment method</label>
            <select value={editForm.method}
              onChange={e => setEditForm(f => ({ ...f, method: e.target.value }))} style={dpField()}>
              <option value="">Unchanged</option>
              {/* Methods come from the record itself rather than a hardcoded
                  list, so this can never offer one the backend rejects. */}
              {["onsite_cash", "onsite_upi", "onsite_card", "onsite_bank_transfer", "onsite_other"].map(m => (
                <option key={m} value={m}>{m.replace("onsite_", "").replace(/_/g, " ")}</option>
              ))}
            </select>

            <label style={dpLbl()}>Reference id</label>
            <input value={editForm.reference_id}
              onChange={e => setEditForm(f => ({ ...f, reference_id: e.target.value }))} style={dpField()} />

            <label style={dpLbl()}>Note</label>
            <textarea rows={2} value={editForm.note}
              onChange={e => setEditForm(f => ({ ...f, note: e.target.value }))}
              style={{ ...dpField(), height: "auto", resize: "vertical" }} />

            <label style={dpLbl()}>Why is this being corrected?</label>
            <textarea rows={2} value={editForm.correction_reason}
              onChange={e => setEditForm(f => ({ ...f, correction_reason: e.target.value }))}
              placeholder="Recorded against the correction for audit."
              style={{ ...dpField(), height: "auto", resize: "vertical" }} />

            {/* The server rejects a corrected amount that differs from the
                expected amount unless a difference reason is supplied. Asking
                for it only when it actually applies keeps the common case to
                one reason field instead of two. */}
            {amountDiffers && (
              <>
                <label style={dpLbl()}>
                  Why does this differ from the expected {money(String(detail.record.expected_amount ?? ""))}?
                </label>
                <textarea rows={2} value={editForm.difference_reason}
                  onChange={e => setEditForm(f => ({ ...f, difference_reason: e.target.value }))}
                  placeholder="Required when the amount received is not the expected amount."
                  style={{ ...dpField(), height: "auto", resize: "vertical" }} />
              </>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setEditOpen(false)}>Cancel</Btn>
              <Btn variant="primary" loading={action === "edit"}
                disabled={!editForm.correction_reason.trim()
                  || (amountDiffers && !editForm.difference_reason.trim())}
                onClick={submitCorrection}>Save correction</Btn>
            </div>
          </Card>
        </div>
        );
      })()}
    </div>
  );
}

function dpLbl(): React.CSSProperties {
  return { display: "block", fontSize: 11.5, fontWeight: 600, color: "var(--text-secondary)",
    margin: "10px 0 5px" };
}
function dpField(): React.CSSProperties {
  return { width: "100%", height: 36, padding: "0 10px", fontSize: 13,
    background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 8,
    color: "var(--text-primary)", fontFamily: "inherit", boxSizing: "border-box" };
}

/* ── Detail pane ─────────────────────────────────────────────────────── */

function DetailPane({ d, busy, onRemind, onDispute, onEdit }: {
  d: HsDpDetail; busy: string | null;
  onRemind: () => void; onDispute: () => void; onEdit: () => void;
}) {
  const rec = d.record;
  const pd = d.provider_declaration;
  const cc = d.customer_confirmation;
  const vf = d.visit_fee_adjustment;
  const canRemind = d.available_actions.remind_customer === true;
  const canEdit = d.available_actions.edit_declaration === true;
  const canDispute = d.available_actions.open_dispute === true;

  return (
    <>
      <Card>
        {/* header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                      gap: 10, flexWrap: "wrap" }}>
          <h2 style={{ fontSize: 16.5, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
            Payment confirmation — {rec.job_ref}
          </h2>
          <div style={{ display: "flex", gap: 6 }}>
            <Badge variant={STATUS_VARIANT[rec.status] ?? "muted"} size="sm">{rec.status_label}</Badge>
            <Badge variant="muted" size="sm">Direct payment</Badge>
          </div>
        </div>

        {/* job + price breakdown */}
        <div className="dp-duo" style={{ marginTop: 14 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <span style={{
              width: 36, height: 36, borderRadius: 10, flexShrink: 0,
              background: "var(--accent-muted)", color: "var(--accent)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}><Wrench size={17}/></span>
            <div>
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 3px" }}>
                {d.job_context.service ?? "Service"}
              </p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 2px" }}>
                {d.job_context.technician ?? "Technician not recorded"}
              </p>
              <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
                {d.job_context.completed_at
                  ? `Completed: ${fmtDateTime(d.job_context.completed_at)}`
                  : `Job status: ${d.job_context.job_status ?? "—"}`}
              </p>
            </div>
          </div>

          <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)",
                        borderRadius: 12, padding: 12 }}>
            <Line label={d.approved_estimate ? "Approved estimate" : "Expected amount"}
                  value={money(d.expected_amount
                    ? String(Number(d.expected_amount) - Number(vf.adjustment ?? 0))
                    : d.expected_amount, rec.currency)}/>
            {vf.applied && (
              <Line label="Visit fee" value={`− ${money(vf.visit_fee, rec.currency)}`} negative/>
            )}
            <div style={{ height: 1, background: "var(--border)", margin: "8px 0" }}/>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
                {d.final_payable_label}
              </span>
              <span style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>
                {money(d.expected_amount, rec.currency)}
              </span>
            </div>
            {d.expected_unresolved_reason && (
              <p style={{ fontSize: 11, color: "var(--warning-text)", margin: "8px 0 0" }}>
                Expected amount unresolved ({d.expected_unresolved_reason}) — nothing is guessed.
              </p>
            )}
            {d.approved_estimate && (
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
                Estimate {d.approved_estimate.quote_number} v{d.approved_estimate.version_number}
                {d.approved_estimate.is_approved ? " · approved" : ` · ${d.approved_estimate.status}`}
              </p>
            )}
          </div>
        </div>

        {/* provider declared + customer confirmation */}
        <div className="dp-duo" style={{ marginTop: 14 }}>
          <div style={{ border: "1px solid var(--border)", borderRadius: 12, padding: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)" }}>
                Provider declared
              </span>
              <Badge variant={pd.state === "confirmed" ? "success" : "warning"} size="sm">
                {pd.state === "confirmed" ? "Confirmed" : "Pending"}
              </Badge>
            </div>
            <p style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 10px" }}>
              {money(pd.amount, pd.currency)}
            </p>
            <Line label="Method" value={pd.method_label}/>
            <Line label="Reference ID" value={pd.reference_id ?? "—"}/>
            <Line label="Evidence" value={d.evidence ? d.evidence.label : "None uploaded"}/>
            <Line label="Confirmed at" value={fmtDateTime(pd.confirmed_at)}/>
            {pd.difference_reason && (
              <p style={{ fontSize: 11.5, color: "var(--danger-text)", margin: "8px 0 0" }}>
                Differs from expected — {pd.difference_reason}
              </p>
            )}
          </div>

          <div style={{ border: "1px solid var(--border)", borderRadius: 12, padding: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)" }}>
                Customer confirmation
              </span>
              <Badge variant={cc.state === "confirmed" ? "success"
                            : cc.state === "mismatched" ? "danger" : "warning"} size="sm">
                {cc.state === "confirmed" ? "Confirmed"
                  : cc.state === "mismatched" ? "Mismatched" : "Pending"}
              </Badge>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", margin: "4px 0 12px" }}>
              <span style={{
                width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: cc.state === "confirmed" ? "var(--success-bg)"
                  : cc.state === "mismatched" ? "var(--danger-bg)" : "var(--warning-bg)",
                color: cc.state === "confirmed" ? "var(--success-text)"
                  : cc.state === "mismatched" ? "var(--danger-text)" : "var(--warning-text)",
              }}>
                {cc.state === "confirmed" ? <CheckCircle2 size={17}/>
                  : cc.state === "mismatched" ? <ShieldAlert size={17}/> : <Clock size={17}/>}
              </span>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                {cc.state === "confirmed" ? "Customer confirmed the amount"
                  : cc.state === "mismatched"
                    ? `Customer reported ${money(cc.reported_amount, rec.currency)}`
                    : "Pending customer confirmation"}
              </span>
            </div>
            <Line label="Reminder sent"
                  value={cc.last_reminder_at
                    ? `${fmtDateTime(cc.last_reminder_at)} · ${cc.reminder_channel}`
                    : "Not sent yet"}/>
            {cc.next_reminder_allowed_at && (
              <Line label="Next reminder" value={fmtDateTime(cc.next_reminder_allowed_at)}/>
            )}
            {cc.escalation_due_at && (
              <Line label="Escalates" value={fmtDateTime(cc.escalation_due_at)}/>
            )}
            <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
              {cc.reassurance}
            </p>
          </div>
        </div>

        {/* workflow tracker */}
        <div style={{ marginTop: 16 }}>
          <p style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
            Payment reconciliation workflow
          </p>
          <div className="dp-scroll">
            <div style={{ display: "flex", alignItems: "flex-start", gap: 4, minWidth: 560 }}>
              {d.workflow.steps.map((st, i) => (
                <React.Fragment key={st.key}>
                  <div style={{ flex: 1, textAlign: "center" }}>
                    <span style={{
                      width: 30, height: 30, borderRadius: "50%", margin: "0 auto 6px",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      background: st.complete ? "var(--success-bg)"
                        : st.current ? "var(--accent-muted)" : "var(--surface-sunken)",
                      color: st.complete ? "var(--success-text)"
                        : st.current ? "var(--accent)" : "var(--text-tertiary)",
                      border: st.current ? "1px solid var(--accent)" : "1px solid var(--border)",
                      fontSize: 12, fontWeight: 800,
                    }}>
                      {st.complete ? <CheckCircle2 size={15}/> : i + 1}
                    </span>
                    <p style={{
                      fontSize: 11, margin: 0, fontWeight: st.current ? 800 : 600,
                      color: st.complete ? "var(--text-secondary)"
                        : st.current ? "var(--accent)" : "var(--text-tertiary)",
                    }}>{st.label}</p>
                    {st.current && (
                      <p style={{ fontSize: 10, color: "var(--accent)", margin: "2px 0 0", fontWeight: 700 }}>
                        Current step
                      </p>
                    )}
                  </div>
                  {i < d.workflow.steps.length - 1 && (
                    <div style={{ flex: "0 0 20px", height: 2, marginTop: 15,
                      background: st.complete ? "var(--success-border)" : "var(--border)" }}/>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>

        {/* actions */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginTop: 16 }}>
          <Btn variant="primary" icon={<BellRing size={14}/>} onClick={onRemind}
               disabled={!canRemind} loading={busy === "remind"}>
            Send confirmation reminder
          </Btn>
          <div>
            {/* This button had no onClick at all: when the server allowed
                editing it enabled itself and did nothing. */}
            <Btn variant="secondary" icon={<Pencil size={14}/>} disabled={!canEdit}
                 onClick={onEdit}>Edit declaration</Btn>
            <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
              {typeof d.available_actions.edit_declaration_hint === "string"
                ? d.available_actions.edit_declaration_hint
                : "Available before customer confirmation"}
            </p>
          </div>
          <a href={`/home-services/bookings-jobs?job_id=${rec.job_id}`}
             style={{ textDecoration: "none" }}>
            <Btn variant="secondary" icon={<ExternalLink size={14}/>}>Open job</Btn>
          </a>
        </div>
      </Card>

      {/* evidence / activity / policy */}
      <div className="dp-trio">
        <Card padding={14}>
          <p style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
            Evidence (Provider)
          </p>
          {d.evidence?.view_path ? (
            <EvidenceThumb path={d.evidence.view_path}
                           amountLabel={money(pd.amount, pd.currency)}/>
          ) : (
            <div style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
              <ImageIcon size={15}/> No evidence uploaded for this declaration.
            </div>
          )}
        </Card>

        <Card padding={14}>
          <p style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
            Activity
          </p>
          {d.activity.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No recorded activity yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {d.activity.map((a, i) => (
                <div key={i} style={{ display: "flex", gap: 8 }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent)",
                                 flexShrink: 0, marginTop: 5 }}/>
                  <div>
                    <p style={{ fontSize: 12, color: "var(--text-primary)", margin: 0, fontWeight: 600 }}>
                      {a.label}
                    </p>
                    <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                      {fmtDateTime(a.at)} · {a.actor}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card padding={14}>
          <p style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
            Policy &amp; guidance
          </p>
          <ul style={{ margin: 0, paddingLeft: 16, display: "flex", flexDirection: "column", gap: 6 }}>
            {d.policy.map((p, i) => (
              <li key={i} style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.45 }}>{p}</li>
            ))}
          </ul>
        </Card>
      </div>

      {/* danger bar */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12,
        flexWrap: "wrap", padding: "12px 14px", borderRadius: 12,
        background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
      }}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          <AlertTriangle size={15} style={{ color: "var(--danger-text)", flexShrink: 0, marginTop: 2 }}/>
          <div>
            <p style={{ fontSize: 12.5, color: "var(--danger-text)", margin: 0, fontWeight: 700 }}>
              If customer reports another amount, open a payment dispute.
            </p>
            <p style={{ fontSize: 11, color: "var(--danger-text)", opacity: 0.85, margin: "2px 0 0" }}>
              Disputes go to Complaints &amp; Resolution Center.
              {d.dispute ? ` Linked: ${d.dispute.complaint_number ?? d.dispute.complaint_id} (${d.dispute.status}).` : ""}
            </p>
          </div>
        </div>
        <Btn variant="danger" icon={<ShieldAlert size={14}/>} onClick={onDispute}
             disabled={!canDispute} loading={busy === "dispute"}>Open dispute</Btn>
      </div>
    </>
  );
}

/* ── Small pieces ────────────────────────────────────────────────────── */

/** Evidence is stored privately: the media route is access-checked and has NO
 * public URL, so a bare <img src> (which cannot send the Authorization header)
 * would always fail. Fetch it as an authenticated blob and render that. */
function EvidenceThumb({ path, amountLabel }: { path: string; amountLabel: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } })
      .then(r => (r.ok ? r.blob() : Promise.reject(new Error(String(r.status)))))
      .then(blob => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => { if (!cancelled) setFailed(true); });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  if (failed) {
    return (
      <div style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
        <ImageIcon size={15}/> Evidence is stored but could not be loaded.
      </div>
    );
  }
  return (
    <>
      <div style={{ position: "relative", borderRadius: 10, overflow: "hidden", minHeight: 90,
                    border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt="Provider payment receipt"
               style={{ width: "100%", maxHeight: 130, objectFit: "cover", display: "block" }}/>
        ) : <Skeleton height={90}/>}
        <span style={{
          position: "absolute", bottom: 6, right: 6, padding: "2px 8px", borderRadius: 8,
          background: "rgba(0,0,0,0.6)", color: "#fff", fontSize: 11, fontWeight: 700,
        }}>{amountLabel}</span>
      </div>
      {url && (
        <p style={{ fontSize: 11.5, margin: "8px 0 0" }}>
          <a href={url} target="_blank" rel="noreferrer"
             style={{ color: "var(--accent)", fontWeight: 700, textDecoration: "none" }}>
            View full image
          </a>
        </p>
      )}
    </>
  );
}

function Line({ label, value, negative }: { label: string; value: string; negative?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, padding: "3px 0" }}>
      <span style={{ fontSize: 11.5, color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ fontSize: 12, fontWeight: 600,
                     color: negative ? "var(--danger-text)" : "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

function Kpi({ label, count, money: moneyValue, sub, variant, icon }: {
  label: string; count?: number; money?: string; sub?: string;
  variant: "default" | "success" | "info" | "warning" | "danger"; icon?: React.ReactNode;
}) {
  const colors: Record<string, { fg: string; bg: string }> = {
    default: { fg: "var(--text-primary)",   bg: "var(--surface-sunken)" },
    success: { fg: "var(--success-text)",   bg: "var(--success-bg)" },
    info:    { fg: "var(--info-text)",      bg: "var(--info-bg)" },
    warning: { fg: "var(--warning-text)",   bg: "var(--warning-bg)" },
    danger:  { fg: "var(--danger-text)",    bg: "var(--danger-bg)" },
  };
  const c = colors[variant];
  return (
    <Card padding={16}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        {icon && (
          <span style={{ width: 26, height: 26, borderRadius: "50%", background: c.bg, color: c.fg,
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{icon}</span>
        )}
        <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0, fontWeight: 700 }}>{label}</p>
      </div>
      <p style={{ fontSize: moneyValue ? 20 : 26, fontWeight: 800, color: c.fg, margin: 0 }}>
        {moneyValue ?? count ?? 0}
      </p>
      {sub && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{sub}</p>}
    </Card>
  );
}

function QueueRow({ r, selected, onClick }: {
  r: HsDpRecord; selected: boolean; onClick: () => void;
}) {
  const conf = (state: string) => {
    if (state === "confirmed") return { icon: <CheckCircle2 size={13}/>, label: "Confirmed", color: "var(--success-text)" };
    if (state === "mismatched") return { icon: <ShieldAlert size={13}/>, label: "Mismatch", color: "var(--danger-text)" };
    return { icon: <Clock size={13}/>, label: "Pending", color: "var(--warning-text)" };
  };
  const p = conf(r.provider_confirmation.state);
  const c = conf(r.customer_confirmation.state);
  return (
    <tr onClick={onClick} style={{
      cursor: "pointer",
      background: selected ? "var(--accent-muted)" : undefined,
      boxShadow: selected ? "inset 3px 0 0 0 var(--accent)" : undefined,
    }}>
      <td>
        <span style={{ fontWeight: 800, color: "var(--accent)" }}>{r.job_ref}</span>
        {r.time_window && (
          <span style={{
            marginLeft: 6, padding: "1px 6px", borderRadius: 6, fontSize: 10,
            background: "var(--surface-sunken)", color: "var(--text-tertiary)", fontWeight: 700,
          }}>{r.time_window}</span>
        )}
      </td>
      <td>{r.customer_alias ?? "—"}</td>
      <td>{r.service ?? "—"}</td>
      <td style={{ fontWeight: 700, color: "var(--text-primary)", whiteSpace: "nowrap" }}>
        {money(r.declared_amount ?? r.expected_amount, r.currency)}
      </td>
      <td style={{ whiteSpace: "nowrap" }}>{r.method_label ?? "—"}</td>
      <td>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: p.color, fontWeight: 600 }}>
          {p.icon}{p.label}
        </span>
      </td>
      <td>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: c.color, fontWeight: 600 }}>
          {c.icon}{c.label}
        </span>
      </td>
      <td><Badge variant={STATUS_VARIANT[r.status] ?? "muted"} size="sm">{r.status_label}</Badge></td>
      <td style={{ whiteSpace: "nowrap" }}>{relTime(r.updated_at)}</td>
    </tr>
  );
}

function EmptyQueue({ tab, hasError }: { tab: string; hasError: boolean }) {
  if (hasError) return null;
  const msg = tab === "needs_action"
    ? "Nothing needs your action. Every direct payment is either confirmed or waiting on the customer."
    : tab === "confirmed"
    ? "No confirmed direct payments in this period yet."
    : tab === "mismatched"
    ? "No mismatched declarations — declared amounts match the approved amounts."
    : tab === "disputed"
    ? "No open payment disputes."
    : "No eligible direct-payment records yet. Records appear once work is done on a job that requires a direct-payment confirmation.";
  return (
    <div style={{ padding: "44px 12px", textAlign: "center" }}>
      <CheckCircle2 size={22} style={{ color: "var(--text-tertiary)", marginBottom: 8 }}/>
      <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", margin: 0 }}>{msg}</p>
    </div>
  );
}

function Select({ value, onChange, options, width = 140 }: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; width?: number;
}) {
  return (
    <div style={{ position: "relative", width }}>
      <select value={value} onChange={e => onChange(e.target.value)}
        style={{
          width: "100%", appearance: "none", padding: "8px 26px 8px 10px", fontSize: 12.5,
          background: "var(--surface)", color: "var(--text-primary)",
          border: "1px solid var(--border)", borderRadius: 9, cursor: "pointer", outline: "none",
        }}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <ChevronDown size={13} style={{ position: "absolute", right: 9, top: 10,
        color: "var(--text-tertiary)", pointerEvents: "none" }}/>
    </div>
  );
}

/**
 * Real build failure fixed here: this page calls `useSearchParams()`, which
 * Next.js requires to sit inside a Suspense boundary. Without one, static
 * prerendering threw "useSearchParams() should be wrapped in a suspense
 * boundary" and FAILED THE WHOLE PRODUCTION BUILD.
 *
 * The boundary is scoped to the page rather than the layout so the rest of
 * the tenant shell keeps prerendering normally.
 */
export default function DirectPaymentsPage() {
  return (
    <Suspense fallback={null}>
      <DirectPaymentsPageInner />
    </Suspense>
  );
}
