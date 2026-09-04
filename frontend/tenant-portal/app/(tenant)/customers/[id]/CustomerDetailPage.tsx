"use client";

import React, { Suspense, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Alert, Button, Card, EmptyState, PageHeader, PageShell, Pagination,
  Skeleton, StatCard,
} from "@serviceos/design-system";
import {
  ArrowLeft, BadgeIndianRupee, BriefcaseBusiness, CalendarDays,
  CheckCircle2, Clock3, LockKeyhole, MessageSquareWarning, RotateCcw,
  ShieldCheck, Star, Wrench, XCircle,
} from "lucide-react";
import { Badge } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import {
  hsCustomersApi, type HsCustomerDetail, type HsCustomerFeed,
} from "../../../../lib/api";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "services", label: "Services used" },
  { key: "jobs", label: "Jobs" },
  { key: "payments", label: "Payments" },
  { key: "complaints", label: "Complaints" },
  { key: "reviews", label: "Reviews" },
  { key: "activity", label: "Activity & audit" },
] as const;
type TabKey = typeof TABS[number]["key"];
type Row = Record<string, unknown>;

function fmtDate(value: unknown, withTime = false): string {
  if (!value) return "—";
  return new Date(String(value)).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

function fmtMoney(value: unknown): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 0,
  }).format(Number(value ?? 0));
}

function typeBadge(status: HsCustomerDetail["repeat_status"]) {
  if (status === "repeat") return <Badge variant="success">Repeat customer</Badge>;
  if (status === "one_time") return <Badge variant="info">One-time customer</Badge>;
  return <Badge variant="muted">New relationship</Badge>;
}

function paymentBadge(status: HsCustomerDetail["payment_reliability"]) {
  if (status === "reliable") return <Badge variant="success">Reliable payment history</Badge>;
  if (status === "needs_review") return <Badge variant="danger">Payment review needed</Badge>;
  return <Badge variant="muted">Payment history building</Badge>;
}

export default function CustomerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <CustomerDetailWorkspace customerId={id} />
    </Suspense>
  );
}

function DetailSkeleton() {
  return <PageShell><Skeleton height={82} /><Skeleton height={132} /><Skeleton height={360} /></PageShell>;
}

function CustomerDetailWorkspace({ customerId }: { customerId: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const requestedTab = params.get("tab") as TabKey | null;
  const tab: TabKey = TABS.some(item => item.key === requestedTab) ? requestedTab! : "overview";
  const page = Math.max(1, Number(params.get("page") ?? 1) || 1);
  const detail = useApi(useCallback(() => hsCustomersApi.detail(customerId), [customerId]), [customerId]);
  const customer = detail.data;

  function setTab(nextTab: TabKey) {
    router.replace(`/customers/${customerId}?tab=${nextTab}`);
  }

  function setPage(nextPage: number) {
    const next = new URLSearchParams(params.toString());
    next.set("tab", tab);
    next.set("page", String(nextPage));
    router.replace(`/customers/${customerId}?${next.toString()}`);
  }

  return (
    <>
      <PageShell>
        <PageHeader
          eyebrow=""
          title={customer?.alias ?? "Customer relationship"}
          description="Tenant-scoped service history with privacy controls applied at the API boundary."
          actions={<Button variant="secondary" leftIcon={<ArrowLeft size={15} />} onClick={() => router.push("/customers")}>Back to customers</Button>}
        />

        {detail.error ? (
          <Card><Alert tone="danger" title="Customer relationship could not be loaded">{detail.error}{detail.requestId ? ` · Request ${detail.requestId}` : ""}</Alert><Button variant="secondary" onClick={detail.refetch} style={{ marginTop: 12 }}>Try again</Button></Card>
        ) : detail.loading || !customer ? (
          <><Skeleton height={120} /><Skeleton height={340} /></>
        ) : (
          <>
            <RelationshipHeader customer={customer} />
            <div className="customer-detail-tabs" role="tablist" aria-label="Customer relationship sections">
              {TABS.map(item => <button key={item.key} type="button" role="tab" aria-selected={tab === item.key} onClick={() => setTab(item.key)}>{item.label}</button>)}
            </div>
            {tab === "overview" && <OverviewTab customer={customer} customerId={customerId} />}
            {tab === "services" && <ServicesTab customer={customer} />}
            {tab !== "overview" && tab !== "services" && <FeedTab key={`${tab}-${page}`} customerId={customerId} tab={tab} page={page} onPage={setPage} />}
          </>
        )}
      </PageShell>

      <style jsx global>{`
        .relationship-hero { display: flex; justify-content: space-between; align-items: center; gap: 14px; padding: 16px; }
        .relationship-person { display: flex; align-items: center; gap: 14px; min-width: 0; }
        .relationship-avatar { width: 46px; height: 46px; border-radius: 50%; display: grid; place-items: center; color: var(--brand); background: var(--accent-muted); font-size: 15px; font-weight: 600; }
        .relationship-person h2 { margin: 0; color: var(--text-primary); font-size: 17px; font-weight:600; }
        .relationship-meta { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 7px; }
        .relationship-dates { display: grid; grid-template-columns: repeat(2, minmax(150px, 1fr)); gap: 8px; }
        .relationship-date { padding: 10px 14px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface-sunken); }
        .relationship-date span { display: block; color: var(--text-tertiary); font:500 10px/1 "IBM Plex Mono",var(--font-family-mono); text-transform: uppercase; letter-spacing: .06em; }
        .relationship-date strong { display: block; color: var(--text-primary); font-size: 13px; margin-top: 4px; }
        .customer-detail-tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--border); overflow-x: auto; }
        .customer-detail-tabs button { border: 0; border-bottom: 2px solid transparent; padding: 11px 4px; background: transparent; color: var(--text-tertiary); font:500 13px/1 inherit; cursor: pointer; white-space: nowrap; }
        .customer-detail-tabs button[aria-selected="true"] { color: var(--text-primary); border-bottom-color: var(--brand); font-weight:600; }
        .customer-overview-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(min(160px,100%),1fr)); gap: 10px; }
        .customer-overview-grid .ds-summary-card { border-radius:14px!important; }
        .customer-overview-panels { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr); gap: 16px; }
        .customer-panel-title { display: flex; align-items: center; gap: 9px; margin: 0 0 4px; padding-bottom:10px; border-bottom:1px solid var(--border); color: var(--text-primary); font-size: 15px; font-weight:600; }
        .customer-privacy-card { background:var(--accent-muted)!important;border-color:color-mix(in srgb,var(--brand) 12%,var(--border))!important; }
        .customer-policy-list { display: grid; gap: 10px; }
        .customer-policy-row { display: flex; gap: 9px; color: var(--text-secondary); font-size: 12px; line-height: 1.5; }
        .customer-policy-row svg { color: var(--brand); flex: 0 0 auto; margin-top: 2px; }
        .customer-timeline { display: grid; gap: 2px; }
        .customer-event { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; gap: 9px; align-items: start; padding: 10px 0; border-bottom: 1px solid var(--border); }
        .customer-event-icon { width: 25px; height: 25px; border-radius: 8px; display: grid; place-items: center; background: var(--accent-muted); color: var(--brand); }
        .customer-event strong { color: var(--text-primary); display: block; font-size: 12.5px; }
        .customer-event small { color: var(--text-tertiary); font-size: 10.5px; }
        .customer-services-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }
        .customer-service-card { display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 16px; }
        .customer-service-card h3 { color: var(--text-primary); margin: 0; font-size: 14px; }
        .customer-service-card p { color: var(--text-tertiary); margin: 4px 0 0; font-size: 11px; }
        .customer-feed { overflow: hidden; }
        .customer-feed-row { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(140px, .7fr) minmax(130px, .6fr) auto; gap: 14px; align-items: center; padding: 13px 18px; border-bottom: 1px solid var(--border); }
        .customer-feed-row strong { color: var(--text-primary); font-size: 12.5px; }
        .customer-feed-row p { color: var(--text-tertiary); font-size: 10.5px; margin: 3px 0 0; }
        .customer-feed-secondary { color: var(--text-secondary); font-size: 12px; }
        .customer-feed-link { color: var(--brand); font-size: 12px; font-weight: 700; text-decoration: none; }
        @media (max-width: 1080px) { .customer-overview-grid { grid-template-columns: repeat(3, minmax(150px, 1fr)); } .customer-overview-panels { grid-template-columns: 1fr; } }
        @media (max-width: 720px) { .relationship-hero { align-items: flex-start; flex-direction: column; } .relationship-dates { width: 100%; } .customer-overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .customer-feed-row { grid-template-columns: 1fr auto; } .customer-feed-secondary { display: none; } }
      `}</style>
    </>
  );
}

function RelationshipHeader({ customer }: { customer: HsCustomerDetail }) {
  return <Card padding="none"><div className="relationship-hero">
    <div className="relationship-person"><div className="relationship-avatar">{customer.alias.slice(-4, -2)}</div><div><h2>{customer.alias}</h2><div className="relationship-meta"><Badge variant={customer.is_active ? "success" : "muted"}>{customer.is_active ? "Active" : "Inactive"}</Badge>{typeBadge(customer.repeat_status)}{paymentBadge(customer.payment_reliability)}</div></div></div>
    <div className="relationship-dates"><div className="relationship-date"><span>Relationship since</span><strong>{fmtDate(customer.first_booking_at)}</strong></div><div className="relationship-date"><span>Last activity</span><strong>{fmtDate(customer.last_activity_at)}</strong></div></div>
  </div></Card>;
}

function OverviewTab({ customer, customerId }: { customer: HsCustomerDetail; customerId: string }) {
  const activity = useApi(useCallback(() => hsCustomersApi.activity(customerId, { page: 1, page_size: 6 }), [customerId]), [customerId]);
  const items = activity.data?.items ?? [];
  return <>
    <div className="customer-overview-grid">
      <StatCard icon={CheckCircle2} label="Completed jobs" value={customer.completed_jobs} tone="success" />
      <StatCard icon={XCircle} label="Cancelled jobs" value={customer.cancelled_jobs} tone="danger" />
      <StatCard icon={Wrench} label="Services used" value={customer.services_used_by_master_service.length} tone="info" />
      <StatCard icon={BadgeIndianRupee} label="Confirmed job value" value={fmtMoney(customer.confirmed_job_value)} tone="brand" />
      <StatCard icon={MessageSquareWarning} label="Open complaints" value={customer.open_complaints} tone={customer.open_complaints > 0 ? "danger" : "success"} />
    </div>
    <div className="customer-overview-panels">
      <Card><h3 className="customer-panel-title"><Clock3 size={16} /> Recent relationship activity</h3>{activity.error ? <Alert tone="warning">{activity.error}</Alert> : activity.loading ? <Skeleton height={130} /> : items.length === 0 ? <EmptyState title="No activity recorded" description="Booking and job events will appear here automatically." /> : <div className="customer-timeline">{items.map((item, index) => <div className="customer-event" key={`${String(item.source_system)}-${String(item.source_record_id)}-${index}`}><div className="customer-event-icon"><CalendarDays size={13} /></div><div><strong>{String(item.description ?? item.event_type ?? "Relationship event")}</strong><small>{String(item.source_system ?? "system").replace(/_/g, " ")} · {String(item.actor ?? "system")}</small></div><small>{fmtDate(item.timestamp, true)}</small></div>)}</div>}</Card>
      <Card className="customer-privacy-card"><h3 className="customer-panel-title"><ShieldCheck size={16} /> Privacy and operating policy</h3><div className="customer-policy-list"><div className="customer-policy-row"><LockKeyhole size={15} /><span>Customer name, phone, email and reusable addresses are not exposed in this directory.</span></div><div className="customer-policy-row"><BriefcaseBusiness size={15} /><span>Exact service address and relay contact are available only during an authorized active job.</span></div><div className="customer-policy-row"><RotateCcw size={15} /><span>All service, pricing and payment values come from finalized booking, invoice and direct-payment records.</span></div></div></Card>
    </div>
  </>;
}

function ServicesTab({ customer }: { customer: HsCustomerDetail }) {
  const services = customer.services_used_by_master_service;
  if (services.length === 0) return <Card><EmptyState title="No completed services yet" description="A service appears here after its first completed job." /></Card>;
  return <div className="customer-services-grid">{services.map(service => <Card key={service.offering_id} padding="none"><div className="customer-service-card"><div><h3>{service.master_service_name ?? "Catalog service"}</h3><p>Mapped from the admin master service used by the completed job.</p></div><Badge variant="success">{service.completed_jobs} completed</Badge></div></Card>)}</div>;
}

function FeedTab({ customerId, tab, page, onPage }: { customerId: string; tab: Exclude<TabKey, "overview" | "services">; page: number; onPage: (page: number) => void }) {
  const pageSize = 20;
  const fetcher = useCallback((): Promise<HsCustomerFeed> => {
    const query = { page, page_size: pageSize };
    if (tab === "jobs") return hsCustomersApi.jobs(customerId, query);
    if (tab === "payments") return hsCustomersApi.payments(customerId, query);
    if (tab === "complaints") return hsCustomersApi.complaints(customerId, query);
    if (tab === "reviews") return hsCustomersApi.reviews(customerId, query);
    return hsCustomersApi.activity(customerId, query);
  }, [customerId, page, tab]);
  const feed = useApi(fetcher, [customerId, page, tab]);
  const items = feed.data?.items ?? [];
  return <Card padding="none" className="customer-feed">
    {feed.data?.note && <Alert tone="info">{feed.data.note}</Alert>}
    {feed.error ? <div style={{ padding: 18 }}><Alert tone="danger" title={`Could not load ${tab}`}>{feed.error}{feed.requestId ? ` · Request ${feed.requestId}` : ""}</Alert><Button variant="secondary" onClick={feed.refetch} style={{ marginTop: 10 }}>Try again</Button></div> : feed.loading ? <div style={{ padding: 16, display: "grid", gap: 8 }}>{Array.from({ length: 6 }, (_, index) => <Skeleton key={index} height={52} />)}</div> : items.length === 0 ? <div style={{ padding: 30 }}><EmptyState title={`No ${tab} recorded`} description="This view is sourced from finalized operational records and does not create placeholder data." /></div> : items.map((item, index) => <FeedRow key={String(item.job_id ?? item.payment_id ?? item.complaint_id ?? item.review_id ?? item.source_record_id ?? index)} tab={tab} item={item} />)}
    <Pagination page={page} total={feed.data?.total ?? 0} pageSize={pageSize} onPage={onPage} />
  </Card>;
}

function FeedRow({ tab, item }: { tab: Exclude<TabKey, "overview" | "services">; item: Row }) {
  if (tab === "jobs") return <div className="customer-feed-row"><div><strong>{String(item.job_number ?? "Job")} · {String(item.master_service_name ?? "Catalog service")}</strong><p>{fmtDate(item.scheduled_date)} · {String(item.assignment_status ?? "assignment pending").replace(/_/g, " ")}</p></div><div className="customer-feed-secondary">{String(item.status ?? "unknown").replace(/_/g, " ")}</div><Badge variant={item.status === "completed" ? "success" : item.status === "cancelled" ? "danger" : "info"}>{String(item.status ?? "unknown").replace(/_/g, " ")}</Badge><Link className="customer-feed-link" href={`/home-services/bookings-jobs?job_id=${item.job_id}`}>Open job</Link></div>;
  if (tab === "payments") return <div className="customer-feed-row"><div><strong>{fmtMoney(item.collected_amount)}</strong><p>{String(item.payment_mode ?? "Payment method unavailable").replace(/_/g, " ")} · {fmtDate(item.created_at, true)}</p></div><div className="customer-feed-secondary">{String(item.payment_status ?? "pending").replace(/_/g, " ")}</div><Badge variant={item.customer_confirmed ? "success" : "warning"}>{item.customer_confirmed ? "Customer confirmed" : "Awaiting confirmation"}</Badge><span /></div>;
  if (tab === "complaints") return <div className="customer-feed-row"><div><strong>{String(item.complaint_number ?? "Complaint")} · {String(item.title ?? "Support case")}</strong><p>Created {fmtDate(item.created_at, true)} · SLA {String(item.sla_status ?? "not set").replace(/_/g, " ")}</p></div><div className="customer-feed-secondary">{String(item.severity ?? "normal")} severity</div><Badge variant={item.status === "resolved" || item.status === "closed" ? "success" : "warning"}>{String(item.status ?? "open").replace(/_/g, " ")}</Badge><Link className="customer-feed-link" href={`/home-services/complaints/${item.complaint_id}`}>Open case</Link></div>;
  if (tab === "reviews") return <div className="customer-feed-row"><div><strong><Star size={13} style={{ verticalAlign: -2, marginRight: 5 }} />{String(item.overall_rating ?? "—")} / 5</strong><p>{String(item.review_number ?? "Review")} · {fmtDate(item.created_at)}</p></div><div className="customer-feed-secondary">Provider rating {String(item.provider_rating ?? "—")}</div><Badge variant="info">{String(item.status ?? "submitted").replace(/_/g, " ")}</Badge><span /></div>;
  return <div className="customer-feed-row"><div><strong>{String(item.description ?? item.event_type ?? "Activity")}</strong><p>{String(item.source_system ?? "system").replace(/_/g, " ")} · {String(item.actor ?? "system")}</p></div><div className="customer-feed-secondary">{fmtDate(item.timestamp, true)}</div><Badge variant="muted">Audit event</Badge><span /></div>;
}
