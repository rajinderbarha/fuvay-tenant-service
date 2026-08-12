"use client";
/**
 * Home Services Customer 360° — single-customer detail page.
 *
 * Overview, Services Used, Providers Used, Jobs and Complaints tabs are
 * backed by real data (ServiceJob/ServiceInvoice/CustomerComplaint queries
 * scoped to this customer_id). Payments (confirmation-level detail),
 * Reviews, Addresses and Activity & Audit tabs need canonical read
 * services this page doesn't reach into yet -- not fabricated as
 * empty/zero, shown as an explicit not-available note instead.
 */
import { useCallback, useState, Suspense } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Breadcrumbs } from "../../../../../components/layout/Breadcrumbs";
import { Card, Badge, Btn, Skeleton, DataTable } from "../../../../../components/shared/ui";
import { hsCustomerDirectoryApi } from "../../../../../lib/api";
import { useApi } from "../../../../../hooks/useApi";

function dt(v?: string | null) {
  return v ? new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}
function money(v?: string | number | null) {
  return `₹${Number(v ?? 0).toLocaleString("en-IN")}`;
}

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "services", label: "Services Used" },
  { key: "jobs", label: "Jobs" },
  { key: "providers", label: "Providers Used" },
  { key: "payments", label: "Payments" },
  { key: "reviews", label: "Reviews" },
  { key: "complaints", label: "Complaints" },
  { key: "addresses", label: "Service Addresses Used" },
  { key: "activity", label: "Activity & Audit" },
] as const;
type TabKey = typeof TABS[number]["key"];

export default function CustomerDetailPage() {
  return (
    <Suspense fallback={<Skeleton height={400} />}>
      <CustomerDetailWorkspace />
    </Suspense>
  );
}

function CustomerDetailWorkspace() {
  const params = useParams();
  const router = useRouter();
  const search = useSearchParams();
  const customerId = String(params.customer_id);
  const tab = (search.get("tab") as TabKey) || "overview";
  const detail = useApi(useCallback(() => hsCustomerDirectoryApi.getDetail(customerId), [customerId]));

  function back() { router.back(); }
  function setTab(t: TabKey) { router.replace(`/admin/home-services/customers/${customerId}?tab=${t}`); }

  if (detail.loading) return <AdminLayout activeNav="home_services-customers"><Skeleton height={400} /></AdminLayout>;
  if (detail.error) {
    return (
      <AdminLayout activeNav="home_services-customers">
        <Card padding={24}>
          <p style={{ color: "var(--danger-text)" }}>
            {detail.error.toLowerCase().includes("not found")
              ? "This customer was not found, or has no Home Services activity."
              : `Failed to load customer: ${detail.error}`}
          </p>
          <Btn variant="ghost" icon={<ArrowLeft size={14} />} onClick={back}>Back to Customers</Btn>
        </Card>
      </AdminLayout>
    );
  }
  const d = detail.data as Record<string, unknown> | undefined;
  if (!d) return null;

  return (
    <AdminLayout activeNav="home_services-customers">
      <Breadcrumbs crumbs={[
        { label: "Operations", href: "/admin/operations" },
        { label: "Home Services", href: "/admin/home-services" },
        { label: "Customers", href: "/admin/home-services/customers" },
        { label: String(d.name ?? customerId.slice(0, 8)) },
      ]} />
      <button onClick={back}
        style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", color: "var(--text-tertiary)", fontSize: 12, cursor: "pointer", padding: 0, marginBottom: 12 }}>
        <ArrowLeft size={13} /> Back to Customers
      </button>

      <Card padding={20} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{String(d.name ?? "Unnamed customer")}</h1>
            <Badge variant="info">Home Services</Badge>
            <Badge variant={d.is_active ? "success" : "default"}>{d.is_active ? "Active" : "Inactive"}</Badge>
            <Badge variant={d.repeat_status === "repeat" ? "success" : "default"}>{String(d.repeat_status).replace(/_/g, " ")}</Badge>
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 12, color: "var(--text-tertiary)", flexWrap: "wrap" }}>
            <span>Customer ID: {customerId.slice(0, 8)}</span>
            <span>{String(d.email ?? "—")}</span>
            <span>{String(d.phone ?? "—")}</span>
            <span>First booking {dt(d.first_booking_at as string)}</span>
          </div>
        </div>
      </Card>

      <Card padding={12} style={{ marginTop: 12, background: "var(--surface-sunken)" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          Actions on this page affect only Home Services. Payment reliability is based on customer and
          provider confirmations. ServiceOS does not collect the job payment.
        </p>
      </Card>

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", margin: "16px 0", overflowX: "auto" }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{ padding: "10px 14px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === t.key ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === t.key ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer", whiteSpace: "nowrap" }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab d={d} />}
      {tab === "services" && <ServicesTab d={d} />}
      {tab === "providers" && <ProvidersTab d={d} />}
      {tab === "jobs" && <JobsTab customerId={customerId} />}
      {tab === "complaints" && <ComplaintsTab customerId={customerId} />}
      {tab === "payments" && <PaymentsTab customerId={customerId} />}
      {tab === "reviews" && <ReviewsTab customerId={customerId} />}
      {tab === "addresses" && <AddressesTab customerId={customerId} />}
      {tab === "activity" && <ActivityTab customerId={customerId} />}
    </AdminLayout>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card padding={14}>
      <div style={{ fontSize: 18, fontWeight: 800 }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{label}{sub ? ` · ${sub}` : ""}</div>
    </Card>
  );
}

function OverviewTab({ d }: { d: Record<string, unknown> }) {
  const reliability = String(d.payment_reliability ?? "insufficient_data");
  const reliabilityLabel = reliability === "reliable"
    ? "Reliable"
    : reliability === "needs_review" ? "Needs Review" : "Insufficient Data";
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
      <StatCard label="Completed Jobs" value={String(d.completed_jobs ?? 0)} />
      <StatCard label="Cancelled Jobs" value={String(d.cancelled_jobs ?? 0)} />
      <StatCard label="Confirmed Job Value" value={money(d.confirmed_job_value as string)} sub="Not platform collection" />
      <StatCard label="Open Complaints" value={String(d.open_complaints ?? 0)} />
      <StatCard label="Payment Reliability" value={reliabilityLabel}
        sub={`${Number(d.payment_decisions ?? 0)} customer decisions`} />
    </div>
  );
}

function ServicesTab({ d }: { d: Record<string, unknown> }) {
  const services = (d.services_used_by_master_service ?? []) as Record<string, unknown>[];
  return (
    <DataTable
      rows={services}
      emptyText="No completed services recorded for this customer yet."
      columns={[
        { key: "master_service_name", label: "Master Service", render: (v, row) => v ? String(v) : String((row as Record<string, unknown>).offering_id).slice(0, 8) },
        { key: "completed_jobs", label: "Completed Jobs" },
      ]}
    />
  );
}

function ProvidersTab({ d }: { d: Record<string, unknown> }) {
  const providers = (d.providers_used ?? []) as Record<string, unknown>[];
  return (
    <DataTable
      rows={providers}
      emptyText="No providers used by this customer yet."
      columns={[
        { key: "provider_name", label: "Provider", render: (v, row) => (
          <a href={`/admin/home-services/providers/${(row as Record<string, unknown>).tenant_id}`} style={{ color: "var(--brand)" }}>
            {v ? String(v) : String((row as Record<string, unknown>).tenant_id).slice(0, 8)}
          </a>
        ) },
        { key: "completed_jobs", label: "Completed Jobs" },
      ]}
    />
  );
}

function JobsTab({ customerId }: { customerId: string }) {
  const jobs = useApi(useCallback(() => hsCustomerDirectoryApi.getJobs(customerId), [customerId]));
  if (jobs.loading) return <Skeleton height={200} />;
  if (jobs.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Jobs unavailable: {jobs.error}</p></Card>;
  return (
    <DataTable
      rows={(jobs.data?.items ?? []) as unknown as Record<string, unknown>[]}
      emptyText="No Home Services jobs recorded for this customer."
      columns={[
        { key: "job_number", label: "Job #" },
        { key: "master_service_name", label: "Service", render: v => v ? String(v) : "—" },
        { key: "provider_name", label: "Provider", render: (v, row) => (
          <a href={`/admin/home-services/providers/${(row as Record<string, unknown>).tenant_id}`} style={{ color: "var(--brand)" }}>
            {v ? String(v) : String((row as Record<string, unknown>).tenant_id ?? "").slice(0, 8)}
          </a>
        ) },
        { key: "status", label: "Status", render: v => <Badge variant={v === "completed" ? "success" : v === "cancelled" ? "danger" : "default"}>{String(v)}</Badge> },
        { key: "updated_at", label: "Last Update", render: v => dt(v as string) },
      ]}
    />
  );
}

function ComplaintsTab({ customerId }: { customerId: string }) {
  const complaints = useApi(useCallback(() => hsCustomerDirectoryApi.getComplaints(customerId), [customerId]));
  if (complaints.loading) return <Skeleton height={200} />;
  if (complaints.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Complaints unavailable: {complaints.error}</p></Card>;
  return (
    <DataTable
      rows={(complaints.data?.items ?? []) as unknown as Record<string, unknown>[]}
      emptyText="No complaints recorded for this customer."
      columns={[
        { key: "complaint_number", label: "Complaint #" },
        { key: "title", label: "Title", render: v => v ? String(v) : "—" },
        { key: "severity", label: "Severity", render: v => <Badge variant={v === "high" || v === "critical" ? "danger" : v === "medium" ? "warning" : "default"}>{String(v ?? "—")}</Badge> },
        { key: "status", label: "Status", render: v => <Badge variant={v === "resolved" || v === "closed" ? "success" : "default"}>{String(v)}</Badge> },
        { key: "created_at", label: "Created", render: v => dt(v as string) },
      ]}
    />
  );
}

function PaymentsTab({ customerId }: { customerId: string }) {
  const payments = useApi(useCallback(() => hsCustomerDirectoryApi.getPayments(customerId), [customerId]));
  if (payments.loading) return <Skeleton height={200} />;
  if (payments.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Payments unavailable: {payments.error}</p></Card>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Card padding={12} style={{ background: "var(--surface-sunken)" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{payments.data?.note}</p>
      </Card>
      <DataTable
        rows={(payments.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No direct customer payments recorded."
        columns={[
          { key: "collected_amount", label: "Amount", render: v => money(v as string) },
          { key: "payment_mode", label: "Method" },
          { key: "payment_status", label: "Status", render: v => <Badge variant={v === "verified" || v === "collected" ? "success" : v === "disputed" || v === "failed" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "customer_confirmed", label: "Confirmed", render: v => v ? <Badge variant="success">Yes</Badge> : <Badge variant="warning">Pending</Badge> },
          { key: "created_at", label: "Date", render: v => dt(v as string) },
        ]}
      />
    </div>
  );
}

function ReviewsTab({ customerId }: { customerId: string }) {
  const reviews = useApi(useCallback(() => hsCustomerDirectoryApi.getReviews(customerId), [customerId]));
  if (reviews.loading) return <Skeleton height={200} />;
  if (reviews.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Reviews unavailable: {reviews.error}</p></Card>;
  return (
    <DataTable
      rows={(reviews.data?.items ?? []) as unknown as Record<string, unknown>[]}
      emptyText="No reviews submitted by this customer."
      columns={[
        { key: "review_number", label: "Review #" },
        { key: "overall_rating", label: "Rating", render: v => `${v ?? "—"} ★` },
        { key: "provider_rating", label: "Provider Rating", render: v => v ? `${v} ★` : "—" },
        { key: "status", label: "Status", render: v => <Badge>{String(v)}</Badge> },
        { key: "created_at", label: "Date", render: v => dt(v as string) },
      ]}
    />
  );
}

function AddressesTab({ customerId }: { customerId: string }) {
  const addresses = useApi(useCallback(() => hsCustomerDirectoryApi.getAddresses(customerId), [customerId]));
  if (addresses.loading) return <Skeleton height={200} />;
  if (addresses.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Addresses unavailable: {addresses.error}</p></Card>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        Distinct booking-address snapshots actually used — not a full address book (no dedicated address
        model is wired into this path yet).
      </p>
      <DataTable
        rows={(addresses.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No booking addresses recorded for this customer."
        columns={[
          { key: "city", label: "City", render: v => v ? String(v) : "—" },
          { key: "zipcode", label: "Zipcode", render: v => v ? String(v) : "—" },
          { key: "last_used_at", label: "Last Used", render: v => dt(v as string) },
        ]}
      />
    </div>
  );
}

function ActivityTab({ customerId }: { customerId: string }) {
  const activity = useApi(useCallback(() => hsCustomerDirectoryApi.getActivity(customerId), [customerId]));
  if (activity.loading) return <Skeleton height={200} />;
  if (activity.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Activity unavailable: {activity.error}</p></Card>;
  const notAvailable = (activity.data as Record<string, unknown> | undefined)?.sources_not_available as string[] | undefined;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        Composed read-only timeline from bookings, jobs, payments, financial events, reviews and complaints —
        each entry links back to its own source record, nothing is duplicated.
        {notAvailable && notAvailable.length > 0 && ` Not yet available: ${notAvailable.join(", ").replace(/_/g, " ")}.`}
      </p>
      <DataTable
        rows={(activity.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No activity recorded for this customer."
        columns={[
          { key: "description", label: "Event" },
          { key: "source_system", label: "Source", render: v => <Badge>{String(v).replace(/_/g, " ")}</Badge> },
          { key: "actor", label: "Actor", render: v => v ? String(v) : "—" },
          { key: "timestamp", label: "When", render: v => dt(v as string) },
        ]}
      />
    </div>
  );
}
