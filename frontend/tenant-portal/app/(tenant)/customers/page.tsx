"use client";
import { TableSurface } from "@serviceos/design-system";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Alert, Button, Card, EmptyState, Input, PageHeader, PageShell,
  Pagination, Select, Skeleton, StatCard,
} from "@serviceos/design-system";
import {
  AlertTriangle, BadgeIndianRupee, ChevronRight, RefreshCw, RotateCcw,
  Search, ShieldCheck, UserCheck, UserPlus, Users2,
} from "lucide-react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Badge } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import {
  hsCustomersApi, type HsCustomerListItem, type HsCustomerListParams,
} from "../../../lib/api";

const PAGE_SIZES = [20, 50, 100];

function positiveInt(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function fmtDate(value: string | null): string {
  if (!value) return "No activity yet";
  return new Date(value).toLocaleDateString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
  });
}

function fmtMoney(value: string | number | null | undefined): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 0,
  }).format(Number(value ?? 0));
}

function customerType(status: HsCustomerListItem["repeat_status"]) {
  if (status === "repeat") return { label: "Repeat", variant: "success" as const };
  if (status === "one_time") return { label: "One-time", variant: "info" as const };
  return { label: "New", variant: "muted" as const };
}

function paymentState(status: HsCustomerListItem["payment_reliability"]) {
  if (status === "reliable") return { label: "Reliable", variant: "success" as const };
  if (status === "needs_review") return { label: "Needs review", variant: "danger" as const };
  return { label: "Building history", variant: "muted" as const };
}

export default function CustomersPage() {
  return <Suspense fallback={<CustomersPageSkeleton />}><CustomersWorkspace /></Suspense>;
}

function CustomersPageSkeleton() {
  return (
    <TenantLayout activeNav="customers"><PageShell>
      <Skeleton height={64} /><Skeleton height={132} /><Skeleton height={420} />
    </PageShell></TenantLayout>
  );
}

function CustomersWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const activity = params.get("activity") ?? "";
  const repeatStatus = params.get("repeat_status") ?? "";
  const paymentReliability = params.get("payment_reliability") ?? "";
  const complaintState = params.get("complaint_state") ?? "";
  const sort = params.get("sort") ?? "last_activity_desc";
  const page = positiveInt(params.get("page"), 1);
  const requestedPageSize = positiveInt(params.get("page_size"), 20);
  const pageSize = PAGE_SIZES.includes(requestedPageSize) ? requestedPageSize : 20;
  const [searchDraft, setSearchDraft] = useState(q);

  useEffect(() => setSearchDraft(q), [q]);

  const setListState = useCallback((changes: Record<string, string | number | null>) => {
    const next = new URLSearchParams(params.toString());
    Object.entries(changes).forEach(([key, value]) => {
      if (value === null || value === "") next.delete(key);
      else next.set(key, String(value));
    });
    router.replace(`/customers${next.size ? `?${next.toString()}` : ""}`);
  }, [params, router]);

  const listParams: HsCustomerListParams = {
    q: q || undefined,
    activity: (activity || undefined) as HsCustomerListParams["activity"],
    repeat_status: (repeatStatus || undefined) as HsCustomerListParams["repeat_status"],
    payment_reliability: (paymentReliability || undefined) as HsCustomerListParams["payment_reliability"],
    complaint_state: (complaintState || undefined) as HsCustomerListParams["complaint_state"],
    sort: sort as HsCustomerListParams["sort"],
    page, page_size: pageSize,
  };

  const summary = useApi(useCallback(() => hsCustomersApi.summary(), []), []);
  const customers = useApi(
    useCallback(() => hsCustomersApi.list(listParams), [
      q, activity, repeatStatus, paymentReliability, complaintState, sort, page, pageSize,
    ]),
    [q, activity, repeatStatus, paymentReliability, complaintState, sort, page, pageSize],
  );

  const rows = customers.data?.items ?? [];
  const total = customers.data?.total ?? 0;
  const s = summary.data;
  const hasFilters = Boolean(q || activity || repeatStatus || paymentReliability || complaintState);

  function submitSearch(event: React.FormEvent) {
    event.preventDefault();
    setListState({ q: searchDraft.trim(), page: 1 });
  }

  function clearFilters() {
    setSearchDraft("");
    setListState({
      q: null, activity: null, repeat_status: null,
      payment_reliability: null, complaint_state: null, page: 1,
    });
  }

  return (
    <TenantLayout activeNav="customers">
      <PageShell>
        <PageHeader
          eyebrow="Business"
          context="Customers"
          title="Customers"
          description="A privacy-safe relationship view across bookings, jobs, payments, reviews and support cases."
          actions={<Button variant="secondary" leftIcon={<RefreshCw size={15} />} onClick={() => { summary.refetch(); customers.refetch(); }} disabled={summary.loading || customers.loading}>Refresh</Button>}
        />

        <div className="customer-kpis">
          <StatCard icon={Users2} label="Total relationships" value={summary.loading ? "—" : (s?.total_customers ?? 0)} />
          <StatCard icon={UserCheck} label={`Active · ${s?.active_window_days ?? 90} days`} value={summary.loading ? "—" : (s?.active_customers ?? 0)} tone="success" />
          <StatCard icon={RotateCcw} label="Repeat customers" value={summary.loading ? "—" : (s?.repeat_customers ?? 0)} tone="info" />
          <StatCard icon={UserPlus} label={`New · ${s?.new_customer_window_days ?? 30} days`} value={summary.loading ? "—" : (s?.new_customers ?? 0)} tone="brand" />
          <StatCard icon={AlertTriangle} label="Open complaints" value={summary.loading ? "—" : (s?.open_complaints ?? 0)} tone={(s?.open_complaints ?? 0) > 0 ? "danger" : "success"} />
          <StatCard icon={BadgeIndianRupee} label="Confirmed job value" value={summary.loading ? "—" : fmtMoney(s?.confirmed_job_value)} tone="info" />
        </div>

        {summary.error && <Alert tone="warning" title="Some relationship metrics are unavailable">{summary.error} Use Refresh to try again.</Alert>}

        <Card padding="none" className="customer-directory-card">
          <div className="customer-toolbar">
            <div><h2>Customer directory</h2><p>{total.toLocaleString("en-IN")} relationships match this view</p></div>
            <div className="customer-privacy-note"><ShieldCheck size={15} /><span>Identity and contact details stay protected outside active job access.</span></div>
          </div>

          <form className="customer-filters" onSubmit={submitSearch}>
            <div className="customer-search"><Search size={15} /><Input aria-label="Search by customer alias" value={searchDraft} maxLength={100} onChange={event => setSearchDraft(event.target.value)} placeholder="Search customer alias, for example HS-8F42" /></div>
            <Button type="submit" variant="secondary">Search</Button>
            <Select aria-label="Activity filter" value={activity} onChange={event => setListState({ activity: event.target.value, page: 1 })} options={[{ value: "", label: "All activity" }, { value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
            <Select aria-label="Customer type filter" value={repeatStatus} onChange={event => setListState({ repeat_status: event.target.value, page: 1 })} options={[{ value: "", label: "All customer types" }, { value: "repeat", label: "Repeat customers" }, { value: "one_time", label: "One-time customers" }, { value: "none", label: "No completed jobs" }]} />
            <Select aria-label="Payment history filter" value={paymentReliability} onChange={event => setListState({ payment_reliability: event.target.value, page: 1 })} options={[{ value: "", label: "All payment history" }, { value: "reliable", label: "Reliable" }, { value: "needs_review", label: "Needs review" }, { value: "insufficient_data", label: "Building history" }]} />
            <Select aria-label="Complaint filter" value={complaintState} onChange={event => setListState({ complaint_state: event.target.value, page: 1 })} options={[{ value: "", label: "All complaint states" }, { value: "open", label: "Has open complaints" }, { value: "clear", label: "No open complaints" }]} />
            <Select aria-label="Sort customers" value={sort} onChange={event => setListState({ sort: event.target.value, page: 1 })} options={[{ value: "last_activity_desc", label: "Recently active" }, { value: "last_activity_asc", label: "Least recently active" }, { value: "completed_desc", label: "Most completed jobs" }, { value: "complaints_desc", label: "Open complaints first" }, { value: "first_booking_desc", label: "Newest relationships" }]} />
            {hasFilters && <Button type="button" variant="ghost" onClick={clearFilters}>Clear filters</Button>}
          </form>

          {customers.error ? (
            <div className="customer-state"><Alert tone="danger" title="Customer directory could not be loaded">{customers.error}{customers.requestId ? ` · Request ${customers.requestId}` : ""}</Alert><Button variant="secondary" onClick={customers.refetch}>Try again</Button></div>
          ) : customers.loading ? (
            <div className="customer-loading">{Array.from({ length: 7 }, (_, index) => <Skeleton key={index} height={54} />)}</div>
          ) : rows.length === 0 ? (
            <div className="customer-state"><EmptyState title={hasFilters ? "No customers match these filters" : "No customer relationships yet"} description={hasFilters ? "Clear or broaden the filters to return to the full directory." : "Customers appear automatically after a confirmed booking from the native customer app."} />{hasFilters && <Button variant="secondary" onClick={clearFilters}>Clear filters</Button>}</div>
          ) : <CustomerTable rows={rows} onOpen={id => router.push(`/customers/${id}`)} />}

          <div className="customer-pagination-row">
            <Select aria-label="Rows per page" value={String(pageSize)} onChange={event => setListState({ page_size: event.target.value, page: 1 })} options={PAGE_SIZES.map(size => ({ value: String(size), label: `${size} per page` }))} />
            <div className="customer-pagination"><Pagination page={page} total={total} pageSize={pageSize} alwaysShow onPage={nextPage => setListState({ page: nextPage })} /></div>
          </div>
        </Card>
      </PageShell>

      <style jsx global>{`
        .customer-kpis { display: grid; grid-template-columns: repeat(6, minmax(150px, 1fr)); gap: 12px; }
        .customer-directory-card { overflow: hidden; }
        .customer-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 18px 20px; border-bottom: 1px solid var(--border); }
        .customer-toolbar h2 { margin: 0; color: var(--text-primary); font-size: 16px; }
        .customer-toolbar p { margin: 3px 0 0; color: var(--text-tertiary); font-size: 12px; }
        .customer-privacy-note { display: flex; align-items: center; gap: 7px; max-width: 430px; color: var(--text-secondary); font-size: 12px; }
        .customer-privacy-note svg { color: var(--success-text); flex: 0 0 auto; }
        .customer-filters { display: grid; grid-template-columns: minmax(260px, 1.5fr) auto repeat(5, minmax(140px, .7fr)); gap: 8px; align-items: center; padding: 12px 16px; background: var(--surface-sunken); border-bottom: 1px solid var(--border); }
        .customer-search { position: relative; }
        .customer-search > svg { position: absolute; z-index: 1; left: 11px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary); }
        .customer-search input { padding-left: 34px !important; }
        .customer-table-wrap { overflow-x: auto; }
        .customer-table { width: 100%; border-collapse: collapse; min-width: 940px; }
        .customer-table th { padding: 10px 16px; text-align: left; color: var(--text-tertiary); font-size: 10px; font-weight: 700; letter-spacing: .055em; text-transform: uppercase; white-space: nowrap; background: var(--surface); border-bottom: 1px solid var(--border); }
        .customer-table td { padding: 13px 16px; color: var(--text-secondary); font-size: 12.5px; border-bottom: 1px solid var(--border); }
        .customer-table tbody tr { cursor: pointer; transition: background .15s ease; }
        .customer-table tbody tr:hover { background: var(--surface-sunken); }
        .customer-table tbody tr:focus-visible { outline: 2px solid var(--brand); outline-offset: -2px; }
        .customer-identity { display: flex; align-items: center; gap: 10px; }
        .customer-avatar { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; background: var(--accent-muted); color: var(--brand); font-weight: 800; font-size: 11px; }
        .customer-alias { color: var(--text-primary); font-weight: 700; }
        .customer-subtext { color: var(--text-tertiary); font-size: 10.5px; margin-top: 2px; }
        .customer-count { color: var(--text-primary); font-weight: 700; }
        .customer-open { display: inline-flex; align-items: center; gap: 4px; color: var(--brand); font-weight: 700; }
        .customer-state { min-height: 280px; padding: 34px; display: grid; place-items: center; gap: 12px; }
        .customer-loading { padding: 16px; display: grid; gap: 8px; }
        .customer-pagination-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 16px; }
        .customer-pagination { flex: 1; }
        .customer-pagination > div { border-top: 0 !important; padding-right: 0 !important; }
        @media (max-width: 1240px) { .customer-kpis { grid-template-columns: repeat(3, minmax(160px, 1fr)); } .customer-filters { grid-template-columns: minmax(260px, 1fr) auto repeat(3, minmax(150px, 1fr)); } }
        @media (max-width: 760px) { .customer-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } .customer-toolbar { align-items: flex-start; flex-direction: column; } .customer-filters { grid-template-columns: 1fr 1fr; } .customer-search { grid-column: 1 / -1; } .customer-pagination-row { align-items: stretch; flex-direction: column; padding-top: 12px; } }
      `}</style>
    </TenantLayout>
  );
}

function CustomerTable({ rows, onOpen }: { rows: HsCustomerListItem[]; onOpen: (id: string) => void }) {
  return <div className="customer-table-wrap"><TableSurface className="customer-table"><thead><tr><th>Customer</th><th>Activity</th><th>Completed</th><th>Services</th><th>Relationship</th><th>Payment history</th><th>Complaints</th><th aria-label="Actions" /></tr></thead><tbody>
    {rows.map(row => {
      const type = customerType(row.repeat_status);
      const payment = paymentState(row.payment_reliability);
      const initials = row.alias.replace("Customer ", "").slice(-4, -2) || "HS";
      return <tr key={row.customer_id} tabIndex={0} onClick={() => onOpen(row.customer_id)} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") onOpen(row.customer_id); }}>
        <td><div className="customer-identity"><div className="customer-avatar">{initials}</div><div><div className="customer-alias">{row.alias}</div><div className="customer-subtext">Relationship since {fmtDate(row.first_booking_at)}</div></div></div></td>
        <td><Badge variant={row.is_active ? "success" : "muted"} size="sm">{row.is_active ? "Active" : "Inactive"}</Badge><div className="customer-subtext">{fmtDate(row.last_activity_at)}</div></td>
        <td><span className="customer-count">{row.completed_jobs}</span></td>
        <td><span className="customer-count">{row.services_used_count}</span></td>
        <td><Badge variant={type.variant} size="sm">{type.label}</Badge></td>
        <td><Badge variant={payment.variant} size="sm">{payment.label}</Badge></td>
        <td>{row.open_complaints > 0 ? <Badge variant="danger" size="sm">{row.open_complaints} open</Badge> : <Badge variant="success" size="sm">Clear</Badge>}</td>
        <td><span className="customer-open">Open <ChevronRight size={13} /></span></td>
      </tr>;
    })}
  </tbody></TableSurface></div>;
}
