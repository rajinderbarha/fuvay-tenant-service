"use client";
import { TableSurface } from "@serviceos/design-system";

import React, { Suspense, useCallback, useDeferredValue, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle, ArrowLeft, BriefcaseBusiness, CalendarClock, CheckCircle2,
  ChevronLeft, ChevronRight, CircleDot, Download, FilterX, Mail, MapPin,
  Pencil, Phone, Search, ShieldCheck, Star, UserPlus, Users, Wallet, Wrench,
} from "lucide-react";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import { AddTeamMemberWizard } from "../../../../../components/onboarding/AddTeamMemberWizard";
import { Alert, Avatar, Button, Card, PageHeader, PageShell, Skeleton, StatCard, StatusBadge } from "@serviceos/design-system";
import {
  activationPaymentApi, homeServicesTeamApi, providerTeamMembersApi,
  type ProviderTeamMember, type StaffOverview, type TeamDirectoryStaffRow,
} from "../../../../../lib/api";
import { useApi } from "../../../../../hooks/useApi";
import { topupApi } from "../../../../../lib/api-topup";

const TABS = [
  ["overview", "Overview"], ["capabilities", "Capabilities"], ["availability", "Availability"],
  ["jobs", "Jobs"], ["performance", "Performance"], ["documents", "Documents"],
  ["activity", "Activity & audit"],
] as const;
type TabKey = typeof TABS[number][0];

const titleCase = (value: string | null | undefined) =>
  (value || "Not set").replaceAll("_", " ").replace(/\b\w/g, char => char.toUpperCase());
const dateText = (value: string | null | undefined) => value
  ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: value.includes("T") ? "short" : undefined }).format(new Date(value))
  : "—";
const money = (value: number | null | undefined) => new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 0,
}).format(Number(value || 0));

export default function TeamPage() { return <Suspense fallback={null}><TeamPageContent /></Suspense>; }

function TeamPageContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedStaffId = (params.staffId as string[] | undefined)?.[0] ?? null;
  const requestedTab = searchParams.get("tab") as TabKey | null;
  const tab: TabKey = TABS.some(([key]) => key === requestedTab) ? requestedTab! : "overview";
  if (!selectedStaffId) return <TeamDirectory />;
  return <TenantLayout activeNav="provider-staff"><PageShell>
    <button className="team-back" onClick={() => router.push("/home-services/team")}><ArrowLeft size={15} /> Back to team directory</button>
    <StaffDetail staffId={selectedStaffId} tab={tab} onTabChange={key => router.replace(`/home-services/team/${selectedStaffId}?tab=${key}`)} />
  </PageShell><TeamStyles /></TenantLayout>;
}

function TeamDirectory() {
  const router = useRouter();
  const [searchInput, setSearchInput] = useState("");
  const search = useDeferredValue(searchInput.trim());
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [availability, setAvailability] = useState("");
  const [readiness, setReadiness] = useState("");
  const [cursor, setCursor] = useState(0);
  const [limit, setLimit] = useState(25);
  const [addOpen, setAddOpen] = useState(false);
  useEffect(() => setCursor(0), [search, role, status, availability, readiness, limit]);
  const loader = useCallback(() => homeServicesTeamApi.list({ search: search || undefined, role: role || undefined,
    status: status || undefined, availability: availability || undefined, readiness: readiness || undefined, cursor, limit,
  }), [search, role, status, availability, readiness, cursor, limit]);
  const directory = useApi(loader, [search, role, status, availability, readiness, cursor, limit]);
  const funding = useApi(useCallback(() => activationPaymentApi.getFundingQuote(), []), []);
  // Seats are bought, not granted, so the roster is gated on the plan. This is
  // the same call the header credit pill makes: balance, seats and buyable
  // plans in one response.
  const topup = useApi(useCallback(() => topupApi.status(), []), []);
  const seatsOwned = topup.data?.entitled_seats ?? null;
  const noPlan = seatsOwned === 0;
  const seatsFull = seatsOwned != null && (topup.data?.available_seats ?? 0) <= 0 && !noPlan;
  const creditOut = (topup.data?.credit_balance ?? 1) <= 0;
  const hasFilters = Boolean(searchInput || role || status || availability || readiness);
  const clearFilters = () => { setSearchInput(""); setRole(""); setStatus(""); setAvailability(""); setReadiness(""); };

  function exportPage() {
    const rows = directory.data?.staff ?? [];
    const csv = [["Name", "Role", "Status", "Availability", "Readiness", "Jobs today", "Capacity"],
      ...rows.map(row => [row.name, row.role, row.employment_status, row.availability_status, row.readiness,
        String(row.jobs_today), `${row.capacity_used}/${row.capacity_limit}`])]
      .map(row => row.map(cell => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url;
    anchor.download = `team-directory-${new Date().toISOString().slice(0, 10)}.csv`; anchor.click(); URL.revokeObjectURL(url);
  }

  const summary = directory.data?.summary;
  const fundingQuote = funding.data as any;
  return <TenantLayout activeNav="provider-staff"><PageShell>
    <PageHeader title="Staff & technicians"
      description="One operational roster for setup readiness, dispatch capacity, staff access and service delivery."
      actions={<><Button variant="secondary" leftIcon={<Download size={14} />} disabled={!directory.data?.staff.length} onClick={exportPage}>Export page</Button><Button variant="primary" leftIcon={<UserPlus size={14} />} disabled={noPlan || seatsFull} onClick={() => setAddOpen(true)}>Add team member</Button></>} />
    {directory.error && <Alert tone="danger">{directory.error}</Alert>}
    {/* The roster stays visible without a plan so the provider can see what a
        plan unlocks and reach the purchase -- it is locked, not hidden. */}
    {noPlan && <Alert tone="warning">
      <strong>Buy a top-up plan to add technicians.</strong>{" "}
      A plan grants the technician seats that decide how many jobs you can run in one slot.{" "}
      <Link href="/home-services/finance">Buy a plan</Link>
    </Alert>}
    {seatsFull && <Alert tone="warning">
      All {seatsOwned} purchased seat{seatsOwned === 1 ? "" : "s"} are in use.{" "}
      <Link href="/home-services/finance">Buy another plan</Link> to add more technicians.
    </Alert>}
    {creditOut && !noPlan && <Alert tone="danger">
      <strong>Your team is suspended — the workspace is out of credit.</strong>{" "}
      Technicians are set inactive and cannot be assigned work. They are restored
      automatically the moment you top up.{" "}
      <Link href="/home-services/finance">Add credit</Link>
    </Alert>}
    <section className="team-kpis" aria-label="Team summary">{directory.loading || !summary
      ? Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} height={104} />) : <>
        <StatCard icon={Users} label="Total team" value={summary.total_team} tone="brand" />
        <StatCard icon={CheckCircle2} label="Active" value={summary.active} tone="success" />
        <StatCard icon={Wrench} label="Technicians" value={summary.technicians} tone="info" />
        <StatCard icon={CircleDot} label="Available now" value={summary.available_now} tone="success" />
        <StatCard icon={AlertTriangle} label="Needs setup" value={summary.setup_incomplete} tone="warning" />
        <StatCard icon={CalendarClock} label="Schedule conflicts" value={summary.schedule_conflicts} tone="danger" />
      </>}</section>
    <div className="team-insight-grid"><Card><div className="team-insight"><span className="team-insight-icon"><ShieldCheck size={18} /></span><div><strong>Setup and dispatch use this same roster</strong><p>Services, admin-managed skills and staff schedules resolve from the records used by onboarding and job assignment.</p></div><Link href="/tenant/home-services/setup/staff">Review setup mapping</Link></div></Card><Card><div className="team-insight"><span className="team-insight-icon"><Wallet size={18} /></span><div><strong>Workforce funding impact</strong><p>{funding.loading ? "Checking finance policy…" : fundingQuote ? `${fundingQuote.qualifying_technician_count ?? 0} qualifying technicians · ${seatsOwned ?? 0} seat${seatsOwned === 1 ? "" : "s"} purchased` : "Finance policy is shown in the canonical Home Services finance workspace."}</p></div><Link href="/home-services/finance">Open finance</Link></div></Card></div>
    <Card padding="none"><div className="team-toolbar"><label className="team-search"><Search size={15} /><input aria-label="Search team" value={searchInput} onChange={e => setSearchInput(e.target.value)} placeholder="Search name, email, phone or designation" /></label><Filter label="Role" value={role} onChange={setRole} options={directory.data?.available_filters.role ?? ["technician", "staff", "manager"]} /><Filter label="Status" value={status} onChange={setStatus} options={directory.data?.available_filters.status ?? ["active", "inactive"]} /><Filter label="Availability" value={availability} onChange={setAvailability} options={directory.data?.available_filters.availability ?? ["available", "busy", "offline", "unavailable"]} /><Filter label="Readiness" value={readiness} onChange={setReadiness} options={directory.data?.available_filters.readiness ?? ["ready", "needs_setup", "invitation_pending", "access_disabled"]} />{hasFilters && <Button variant="ghost" size="sm" leftIcon={<FilterX size={14} />} onClick={clearFilters}>Clear</Button>}</div>
      <div className="team-result-line"><span>{directory.loading ? "Loading roster…" : `${directory.data?.pagination.total ?? 0} team member${directory.data?.pagination.total === 1 ? "" : "s"}`}</span><span>Live capacity · {directory.data?.generated_at ? dateText(directory.data.generated_at) : "—"}</span></div>
      {directory.loading ? <div className="team-loading"><Skeleton height={56} /><Skeleton height={56} /><Skeleton height={56} /></div> : !directory.data?.staff.length ? <EmptyTeam filtered={hasFilters} onClear={clearFilters} onAdd={() => setAddOpen(true)} /> : <div className="team-table-wrap"><TableSurface className="team-table"><thead><tr><th>Team member</th><th>Role</th><th>Live availability</th><th>Today</th><th>Readiness</th><th></th></tr></thead><tbody>{directory.data.staff.map(row => <TeamRow key={row.staff_id} row={row} onOpen={() => router.push(`/home-services/team/${row.staff_id}`)} />)}</tbody></TableSurface></div>}
      <div className="team-pagination"><label>Rows <select value={limit} onChange={e => setLimit(Number(e.target.value))}><option>25</option><option>50</option><option>100</option></select></label><span>{directory.data ? `${directory.data.pagination.total ? cursor + 1 : 0}–${Math.min(cursor + limit, directory.data.pagination.total)} of ${directory.data.pagination.total}` : "0–0 of 0"}</span><Button variant="secondary" size="sm" aria-label="Previous page" disabled={cursor === 0} onClick={() => setCursor(directory.data?.pagination.previous_cursor ?? 0)}><ChevronLeft size={15} /></Button><Button variant="secondary" size="sm" aria-label="Next page" disabled={directory.data?.pagination.next_cursor == null} onClick={() => setCursor(directory.data?.pagination.next_cursor ?? cursor)}><ChevronRight size={15} /></Button></div>
    </Card>
  </PageShell>{addOpen && <AddTeamMemberWizard existing={null} onClose={() => setAddOpen(false)} onSaved={() => { setAddOpen(false); directory.refetch(); funding.refetch(); }} />}<TeamStyles /></TenantLayout>;
}

function Filter({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return <select aria-label={label} value={value} onChange={event => onChange(event.target.value)}><option value="">All {label.toLowerCase()}</option>{options.map(option => <option key={option} value={option}>{titleCase(option)}</option>)}</select>;
}

function TeamRow({ row, onOpen }: { row: TeamDirectoryStaffRow; onOpen: () => void }) {
  return <tr tabIndex={0} onClick={onOpen} onKeyDown={event => { if (event.key === "Enter") onOpen(); }}><td><div className="team-person"><Avatar src={row.photo} name={row.name} size={38} /><div><strong>{row.name}</strong><span>{row.verification_status === "no_login_configured" ? "Profile only · no app login" : titleCase(row.verification_status)}</span></div></div></td><td><strong>{titleCase(row.role)}</strong><span className="team-cell-note">{titleCase(row.employment_status)}</span></td><td><StatusBadge status={row.on_leave ? "on_leave" : row.availability_status} size="sm" /><span className="team-cell-note">{row.on_leave ? "Approved time off" : row.conflict_count ? `${row.conflict_count} conflict(s)` : "Presence synced"}</span></td><td><strong>{row.jobs_today} job{row.jobs_today === 1 ? "" : "s"}</strong><span className="team-cell-note">{row.capacity_used}/{row.capacity_limit} concurrent capacity</span></td><td><StatusBadge status={row.readiness} size="sm" /><span className="team-cell-note">{row.readiness_missing.length ? row.readiness_missing.map(titleCase).join(", ") : "Ready for assignment"}</span></td><td><ChevronRight size={17} /></td></tr>;
}

function EmptyTeam({ filtered, onClear, onAdd }: { filtered: boolean; onClear: () => void; onAdd: () => void }) {
  return <div className="team-empty"><span><Users size={23} /></span><h3>{filtered ? "No matching team members" : "Build your service team"}</h3><p>{filtered ? "Try removing one or more filters." : "Add technicians and operations staff, then map their approved skills and services."}</p><Button variant="primary" onClick={filtered ? onClear : onAdd}>{filtered ? "Clear filters" : "Add first team member"}</Button></div>;
}

function StaffDetail({ staffId, tab, onTabChange }: { staffId: string; tab: TabKey; onTabChange: (tab: TabKey) => void }) {
  const overview = useApi(useCallback(() => homeServicesTeamApi.overview(staffId), [staffId]), [staffId]);
  const member = useApi(useCallback(() => providerTeamMembersApi.get(staffId), [staffId]), [staffId]);
  const [editOpen, setEditOpen] = useState(false);
  return <div className="team-detail"><Card>{overview.loading || !overview.data ? <Skeleton height={90} /> : overview.error ? <Alert tone="danger">{overview.error}</Alert> : <div className="team-profile-head"><Avatar src={overview.data.identity.photo} name={overview.data.identity.name} size={62} /><div className="team-profile-copy"><div className="team-profile-title"><h1>{overview.data.identity.name}</h1><StatusBadge status={overview.data.employment_status} size="sm" /></div><p>{overview.data.identity.designation || titleCase(overview.data.identity.role)}</p><div><StatusBadge status={overview.data.verification_status} size="sm" /><StatusBadge status={overview.data.availability_status} size="sm" /><StatusBadge status={overview.data.readiness.status} size="sm" /></div></div><Button variant="secondary" leftIcon={<Pencil size={14} />} onClick={() => setEditOpen(true)} disabled={!member.data}>Edit profile</Button></div>}</Card><nav className="team-tabs" aria-label="Team member sections">{TABS.map(([key, label]) => <button key={key} className={tab === key ? "active" : ""} onClick={() => onTabChange(key)}>{label}</button>)}</nav>
    {tab === "overview" && <OverviewTab overview={overview.data} loading={overview.loading} error={overview.error} />}{tab === "capabilities" && <CapabilitiesTab staffId={staffId} />}{tab === "availability" && <AvailabilityTab staffId={staffId} />}{tab === "jobs" && <JobsTab staffId={staffId} />}{tab === "performance" && <PerformanceTab staffId={staffId} />}{tab === "documents" && <DocumentsTab staffId={staffId} />}{tab === "activity" && <ActivityTab staffId={staffId} />}
    {editOpen && member.data && <AddTeamMemberWizard existing={member.data as ProviderTeamMember} onClose={() => setEditOpen(false)} onSaved={() => { setEditOpen(false); member.refetch(); overview.refetch(); }} />}</div>;
}

function OverviewTab({ overview, loading, error }: { overview: StaffOverview | null; loading: boolean; error: string | null }) {
  if (loading || !overview) return <Skeleton height={320} />; if (error) return <Alert tone="danger">{error}</Alert>;
  return <div className="team-detail-grid"><div className="team-stack"><Card title="Profile & contact"><InfoRow icon={<Phone size={14} />} label="Phone" value={overview.identity.phone || "Not added"} /><InfoRow icon={<Mail size={14} />} label="Email" value={overview.identity.email || "Not added"} /><InfoRow icon={<MapPin size={14} />} label="Joined" value={dateText(overview.joined_at)} /></Card><Card title="Today’s schedule">{overview.today.schedule.length ? overview.today.schedule.map((job: any) => <Link className="team-list-row" key={job.job_id} href={`/home-services/bookings-jobs?job_id=${job.job_id}`}><span><strong>{job.job_number}</strong><small>{job.time_window || "Time not set"}</small></span><StatusBadge status={job.status} size="sm" /></Link>) : <InlineEmpty text="No jobs scheduled today." />}</Card><Card title="Assigned services">{overview.supported_services.length ? <div className="team-chips">{overview.supported_services.map((service: any) => <span key={service.id}>{service.name}</span>)}</div> : <InlineEmpty text="No service capability configured." />}</Card></div><div className="team-stack"><Card title="Capacity today"><div className="team-capacity"><strong>{overview.today.capacity_used}/{overview.today.capacity_limit}</strong><span>concurrent jobs used</span><div><i style={{ width: `${Math.min(100, overview.today.capacity_percentage)}%` }} /></div></div></Card><Card title="Operational readiness">{Object.entries(overview.readiness.checklist).map(([key, ready]) => <div className="team-check" key={key}>{ready ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}<span>{titleCase(key)}</span></div>)}</Card>{overview.next_assignment && <Card title="Next assignment"><Link className="team-list-row" href={`/home-services/bookings-jobs?job_id=${overview.next_assignment.job_id}`}><span><strong>{overview.next_assignment.job_number}</strong><small>{dateText(overview.next_assignment.scheduled_date)} · {overview.next_assignment.time_window || "Time pending"}</small></span><ChevronRight size={16} /></Link></Card>}</div></div>;
}

function CapabilitiesTab({ staffId }: { staffId: string }) {
  const result = useApi(useCallback(() => homeServicesTeamApi.capabilities(staffId), [staffId]), [staffId]);
  if (result.loading || !result.data) return <Skeleton height={300} />; if (result.error) return <Alert tone="danger">{result.error}</Alert>;
  return <Card title="Admin-approved service capability"><p className="team-card-intro">Providers select only category skills and enabled services configured by the administrator. Dispatch uses this same mapping.</p>{result.data.services.length ? <div className="team-capability-list">{result.data.services.map((service: any) => <div key={service.offering_id} className="team-capability"><div><strong>{service.master_service}</strong><span>{[service.category, service.service_group].filter(Boolean).join(" · ")}</span></div>{service.requires_type && <Capability label="Types" items={service.types} />}{service.requires_brand && <Capability label="Brands" items={service.brands} />}</div>)}</div> : <InlineEmpty text="No service capability configured for this team member." />}</Card>;
}
function Capability({ label, items }: { label: string; items: any[] }) { return <div><small>{label}</small><div className="team-chips">{items.filter(item => item.supported).map(item => <span key={item.id}>{item.name}</span>)}</div></div>; }

function AvailabilityTab({ staffId }: { staffId: string }) {
  const result = useApi(useCallback(() => homeServicesTeamApi.availability(staffId), [staffId]), [staffId]);
  if (result.loading || !result.data) return <Skeleton height={320} />; if (result.error) return <Alert tone="danger">{result.error}</Alert>;
  const data = result.data;
  return <div className="team-detail-grid"><Card title="Weekly working pattern" actions={<Link href={`/home-services/availability?staff_id=${staffId}`}>Manage availability</Link>}>{data.weekly_rules.length ? data.weekly_rules.map((rule: any) => <div className="team-list-row" key={rule.id}><span><strong>{["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][rule.day_of_week] || `Day ${rule.day_of_week}`}</strong><small>{String(rule.start_time).slice(0, 5)}–{String(rule.end_time).slice(0, 5)} · {rule.timezone || "Workspace timezone"}</small></span><StatusBadge status={rule.is_active ? "active" : "inactive"} size="sm" /></div>) : <InlineEmpty text="No staff-level schedule. Add one before dispatching jobs." />}</Card><div className="team-stack"><Card title="Current presence"><div className="team-presence"><CircleDot size={18} /><div><strong>{titleCase(data.presence)}</strong><span>{data.can_receive_assignment ? "Eligible for new assignments" : "New assignments disabled"}</span></div></div></Card><Card title="Upcoming time off">{data.time_off.length ? data.time_off.map((item: any) => <div className="team-list-row" key={item.id}><span><strong>{dateText(item.start_date)}–{dateText(item.end_date)}</strong><small>{item.reason || "No reason added"}</small></span></div>) : <InlineEmpty text="No upcoming time off." />}</Card><Card title="Date overrides">{data.overrides.length ? data.overrides.map((item: any) => <div className="team-list-row" key={item.id}><span><strong>{dateText(item.override_date)}</strong><small>{item.full_day_closed ? "Closed" : `${String(item.start_time).slice(0, 5)}–${String(item.end_time).slice(0, 5)}`}</small></span></div>) : <InlineEmpty text="No upcoming overrides." />}</Card></div></div>;
}

function JobsTab({ staffId }: { staffId: string }) {
  const [status, setStatus] = useState(""); const [search, setSearch] = useState(""); const [cursor, setCursor] = useState(0); const query = useDeferredValue(search.trim());
  useEffect(() => setCursor(0), [status, query]);
  const result = useApi(useCallback(() => homeServicesTeamApi.jobs(staffId, { status: status || undefined, search: query || undefined, cursor, limit: 25 }), [staffId, status, query, cursor]), [staffId, status, query, cursor]);
  return <Card padding="none"><div className="team-toolbar"><label className="team-search"><Search size={15} /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search job or service" /></label><Filter label="Status" value={status} onChange={setStatus} options={result.data?.available_statuses ?? []} /></div>{result.loading ? <div className="team-loading"><Skeleton height={52} /><Skeleton height={52} /></div> : result.error ? <Alert tone="danger">{result.error}</Alert> : result.data?.items.length ? <div className="team-table-wrap"><TableSurface className="team-table"><thead><tr><th>Job</th><th>Service</th><th>Schedule</th><th>Status</th><th></th></tr></thead><tbody>{result.data.items.map((job: any) => <tr key={job.id} onClick={() => location.href = `/home-services/bookings-jobs?job_id=${job.id}`}><td><strong>{job.job_number}</strong><span className="team-cell-note">{job.city || "Location pending"}</span></td><td>{job.service_name}</td><td>{dateText(job.scheduled_date)}<span className="team-cell-note">{job.scheduled_time_window || "Time pending"}</span></td><td><StatusBadge status={job.status} size="sm" /></td><td><ChevronRight size={16} /></td></tr>)}</tbody></TableSurface></div> : <InlineEmpty text="No assigned jobs match this view." />}{result.data && <div className="team-pagination"><span>{result.data.pagination.total} jobs</span><Button variant="secondary" size="sm" disabled={!cursor} onClick={() => setCursor(result.data?.pagination.previous_cursor ?? 0)}><ChevronLeft size={15} /></Button><Button variant="secondary" size="sm" disabled={result.data.pagination.next_cursor == null} onClick={() => setCursor(result.data?.pagination.next_cursor ?? cursor)}><ChevronRight size={15} /></Button></div>}</Card>;
}

function PerformanceTab({ staffId }: { staffId: string }) {
  const result = useApi(useCallback(() => homeServicesTeamApi.performance(staffId), [staffId]), [staffId]);
  if (result.loading || !result.data) return <Skeleton height={300} />; if (result.error) return <Alert tone="danger">{result.error}</Alert>;
  const data = result.data; const ratings = data.ratings as any;
  return <><section className="team-kpis team-kpis-four"><StatCard icon={BriefcaseBusiness} label="Completed jobs" value={data.completed_jobs} tone="success" /><StatCard icon={CalendarClock} label="Last 30 days" value={data.completed_last_30_days} tone="brand" /><StatCard icon={CheckCircle2} label="Completion rate" value={`${data.completion_rate}%`} tone="info" /><StatCard icon={Star} label="Customer rating" value={Number(ratings.average_rating || 0).toFixed(1)} tone="warning" /></section><div className="team-detail-grid"><Card title="Customer rating dimensions"><Metric label="Communication" value={ratings.communication_average_rating} /><Metric label="Punctuality" value={ratings.punctuality_average_rating} /><Metric label="Quality" value={ratings.quality_average_rating} /><p className="team-card-note">Based on {ratings.total_reviews || 0} verified reviews.</p></Card><Card title="Delivery record"><InfoRow icon={<CheckCircle2 size={14} />} label="Completed" value={String(data.completed_jobs)} /><InfoRow icon={<AlertTriangle size={14} />} label="Cancelled" value={String(data.cancelled_jobs)} /><InfoRow icon={<CalendarClock size={14} />} label="Last completed" value={dateText(data.last_completed_at)} /></Card></div></>;
}

function DocumentsTab({ staffId }: { staffId: string }) {
  const [search, setSearch] = useState(""); const [status, setStatus] = useState(""); const [cursor, setCursor] = useState(0); const query = useDeferredValue(search.trim());
  useEffect(() => setCursor(0), [query, status]);
  const result = useApi(useCallback(() => homeServicesTeamApi.documents(staffId, { search: query || undefined, status: status || undefined, cursor, limit: 25 }), [staffId, query, status, cursor]), [staffId, query, status, cursor]);
  return <Card padding="none"><div className="team-section-head"><div><strong>Staff verification documents</strong><p>Staff-scoped records from the same repository reviewed by administrators. Business onboarding documents remain separate.</p></div></div><div className="team-toolbar"><label className="team-search"><Search size={15} /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search document" /></label><Filter label="Status" value={status} onChange={setStatus} options={["pending_review", "verified", "rejected", "expired"]} /></div>{result.loading || !result.data ? <div className="team-loading"><Skeleton height={52} /><Skeleton height={52} /></div> : result.error ? <Alert tone="danger">{result.error}</Alert> : result.data.items.length ? <div className="team-list-pad">{result.data.items.map((doc: any) => <div className="team-list-row" key={doc.id}><span><strong>{doc.label || titleCase(doc.doc_type)}</strong><small>{doc.expiry_date ? `Expires ${dateText(doc.expiry_date)}` : `Uploaded ${dateText(doc.created_at)}`}</small></span><div className="team-row-actions"><StatusBadge status={doc.status} size="sm" />{doc.file_url && <a href={doc.file_url} target="_blank" rel="noreferrer">View</a>}</div></div>)}</div> : <InlineEmpty text="No staff-specific documents match this view." />}{result.data && <div className="team-pagination"><span>{result.data.pagination.total ?? 0} documents</span><Button variant="secondary" size="sm" disabled={!cursor} onClick={() => setCursor(Math.max(0, cursor - 25))}><ChevronLeft size={15} /></Button><Button variant="secondary" size="sm" disabled={result.data.pagination.next_cursor == null} onClick={() => setCursor(result.data.pagination.next_cursor ?? cursor)}><ChevronRight size={15} /></Button></div>}</Card>;
}

function ActivityTab({ staffId }: { staffId: string }) {
  const [search, setSearch] = useState(""); const [cursor, setCursor] = useState(0); const query = useDeferredValue(search.trim());
  useEffect(() => setCursor(0), [query]);
  const result = useApi(useCallback(() => homeServicesTeamApi.activity(staffId, { search: query || undefined, cursor, limit: 25 }), [staffId, query, cursor]), [staffId, query, cursor]);
  return <Card padding="none"><div className="team-section-head"><div><strong>Activity & audit trail</strong><p>Tenant-scoped, append-only actions connected to this roster profile or linked app account.</p></div></div><div className="team-toolbar"><label className="team-search"><Search size={15} /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search action, engine or actor" /></label></div>{result.loading || !result.data ? <div className="team-loading"><Skeleton height={52} /><Skeleton height={52} /></div> : result.error ? <Alert tone="danger">{result.error}</Alert> : result.data.items.length ? <div className="team-list-pad">{result.data.items.map((item: any) => <div className="team-list-row" key={item.id}><span><strong>{titleCase(item.operation)}</strong><small>{titleCase(item.engine_id)} · {titleCase(item.actor_role)} · {dateText(item.created_at)}</small></span>{item.is_high_risk && <StatusBadge status="high_risk" size="sm" />}</div>)}</div> : <InlineEmpty text="No audited changes match this view." />}{result.data && <div className="team-pagination"><span>{result.data.pagination.total ?? 0} events</span><Button variant="secondary" size="sm" disabled={!cursor} onClick={() => setCursor(Math.max(0, cursor - 25))}><ChevronLeft size={15} /></Button><Button variant="secondary" size="sm" disabled={result.data.pagination.next_cursor == null} onClick={() => setCursor(result.data.pagination.next_cursor ?? cursor)}><ChevronRight size={15} /></Button></div>}</Card>;
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="team-info"><span>{icon}</span><small>{label}</small><strong>{value}</strong></div>; }
function InlineEmpty({ text }: { text: string }) { return <div className="team-inline-empty">{text}</div>; }
function Metric({ label, value }: { label: string; value: any }) { const numeric = Number(value || 0); return <div className="team-metric"><div><span>{label}</span><strong>{numeric.toFixed(1)}</strong></div><div><i style={{ width: `${Math.min(100, numeric / 5 * 100)}%` }} /></div></div>; }

function TeamStyles() { return <style jsx global>{`
  .team-back{display:inline-flex;align-items:center;gap:7px;border:0;background:none;color:var(--text-secondary);font:600 12px inherit;cursor:pointer;padding:2px 0 10px}.team-back:hover{color:var(--brand)}
  .team-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}.team-kpis-four{grid-template-columns:repeat(4,minmax(0,1fr))}.team-insight-grid,.team-detail-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(290px,.85fr);gap:14px}.team-insight{display:flex;align-items:center;gap:12px}.team-insight-icon{display:grid;place-items:center;width:38px;height:38px;border-radius:11px;color:var(--brand);background:color-mix(in srgb,var(--brand) 10%,transparent);border:1px solid color-mix(in srgb,var(--brand) 24%,transparent);flex:0 0 auto}.team-insight>div{flex:1;min-width:0}.team-insight strong{font-size:13px}.team-insight p{margin:3px 0 0;color:var(--text-tertiary);font-size:11.5px;line-height:1.45}.team-insight a,.team-row-actions a{font-size:12px;font-weight:700;color:var(--brand);text-decoration:none;white-space:nowrap}
  .team-toolbar{display:flex;gap:8px;align-items:center;padding:14px;border-bottom:1px solid var(--border);flex-wrap:wrap}.team-toolbar>select,.team-pagination select{height:36px;padding:0 28px 0 10px;border:1px solid var(--border);border-radius:9px;background:var(--surface-sunken);color:var(--text-primary);font:600 11.5px inherit}.team-search{height:36px;display:flex;align-items:center;gap:8px;min-width:240px;flex:1;padding:0 11px;border:1px solid var(--border);border-radius:9px;background:var(--surface-sunken);color:var(--text-tertiary)}.team-search:focus-within{border-color:var(--brand);box-shadow:0 0 0 3px color-mix(in srgb,var(--brand) 12%,transparent)}.team-search input{width:100%;border:0;outline:0;background:transparent;color:var(--text-primary);font:500 12.5px inherit}.team-result-line{display:flex;justify-content:space-between;gap:12px;padding:10px 14px;border-bottom:1px solid var(--border);color:var(--text-tertiary);font-size:11px}.team-loading{display:grid;gap:8px;padding:14px}
  .team-table-wrap{overflow:auto}.team-table{width:100%;border-collapse:collapse;min-width:880px}.team-table th{padding:10px 14px;text-align:left;color:var(--text-tertiary);font-size:10.5px;text-transform:uppercase;letter-spacing:.055em;background:var(--surface-sunken);border-bottom:1px solid var(--border)}.team-table td{padding:12px 14px;border-bottom:1px solid var(--border);font-size:12px;color:var(--text-secondary);vertical-align:middle}.team-table tbody tr{cursor:pointer;transition:background .15s ease}.team-table tbody tr:hover,.team-table tbody tr:focus{background:color-mix(in srgb,var(--brand) 5%,var(--surface));outline:0}.team-table td>strong{display:block;color:var(--text-primary);font-size:12.5px}.team-cell-note{display:block;margin-top:3px;color:var(--text-tertiary);font-size:10.5px;max-width:220px}.team-person{display:flex;align-items:center;gap:10px}.team-person>div:last-child{display:flex;flex-direction:column;gap:3px}.team-person strong{color:var(--text-primary);font-size:13px}.team-person span{color:var(--text-tertiary);font-size:10.5px}.team-pagination{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:11px 14px}.team-pagination>label,.team-pagination>span{color:var(--text-tertiary);font-size:11px}.team-pagination>label{margin-right:auto}.team-pagination select{height:30px;margin-left:5px}.team-empty{text-align:center;padding:54px 20px}.team-empty>span{display:grid;place-items:center;width:48px;height:48px;margin:0 auto 12px;border-radius:14px;background:var(--surface-sunken);color:var(--brand);border:1px solid var(--border)}.team-empty h3{margin:0;color:var(--text-primary);font-size:16px}.team-empty p{margin:6px auto 15px;max-width:430px;color:var(--text-tertiary);font-size:12px;line-height:1.55}
  .team-detail,.team-stack{display:flex;flex-direction:column;gap:14px}.team-profile-head{display:flex;align-items:center;gap:15px}.team-profile-copy{flex:1;min-width:0}.team-profile-title{display:flex;gap:8px;align-items:center}.team-profile-title h1{margin:0;color:var(--text-primary);font-size:21px;letter-spacing:-.025em}.team-profile-copy>p{margin:4px 0 7px;color:var(--text-secondary);font-size:12.5px}.team-profile-copy>div:last-child{display:flex;gap:6px;flex-wrap:wrap}.team-tabs{display:flex;gap:3px;overflow-x:auto;border-bottom:1px solid var(--border)}.team-tabs button{padding:10px 12px;border:0;border-bottom:2px solid transparent;background:none;color:var(--text-tertiary);font:650 11.5px inherit;white-space:nowrap;cursor:pointer}.team-tabs button:hover{color:var(--text-primary)}.team-tabs button.active{color:var(--brand);border-bottom-color:var(--brand)}
  .team-info{display:grid;grid-template-columns:18px minmax(80px,.45fr) 1fr;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border)}.team-info:last-child{border-bottom:0}.team-info>span{color:var(--text-tertiary)}.team-info small{color:var(--text-tertiary);font-size:11px}.team-info strong{color:var(--text-primary);font-size:12px;font-weight:650}.team-list-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid var(--border);color:var(--text-secondary);text-decoration:none}.team-list-row:last-child{border-bottom:0}.team-list-row>span{display:flex;flex-direction:column;gap:3px}.team-list-row strong{color:var(--text-primary);font-size:12px}.team-list-row small{color:var(--text-tertiary);font-size:10.5px}.team-list-row:hover strong{color:var(--brand)}.team-inline-empty{padding:22px 0;text-align:center;color:var(--text-tertiary);font-size:12px}.team-chips{display:flex;gap:6px;flex-wrap:wrap}.team-chips>span{padding:5px 9px;border-radius:999px;border:1px solid var(--border);background:var(--surface-sunken);color:var(--text-secondary);font-size:10.5px}.team-capacity{text-align:center}.team-capacity>strong{display:block;color:var(--text-primary);font-size:28px}.team-capacity>span{color:var(--text-tertiary);font-size:11px}.team-capacity>div,.team-metric>div:last-child{height:6px;margin-top:12px;border-radius:999px;background:var(--surface-sunken);overflow:hidden}.team-capacity i,.team-metric i{display:block;height:100%;border-radius:inherit;background:var(--brand)}.team-check{display:flex;align-items:center;gap:8px;padding:6px 0;color:var(--text-secondary);font-size:12px}.team-check svg{color:var(--success)}
  .team-card-intro,.team-card-note{margin:0 0 14px;color:var(--text-tertiary);font-size:11.5px;line-height:1.55}.team-section-head{padding:15px 16px;border-bottom:1px solid var(--border)}.team-section-head strong{font-size:13.5px;color:var(--text-primary)}.team-section-head p{margin:4px 0 0;color:var(--text-tertiary);font-size:11px}.team-list-pad{padding:0 16px}.team-capability-list{display:grid;gap:10px}.team-capability{display:grid;grid-template-columns:minmax(180px,.7fr) 1fr 1fr;gap:14px;padding:13px;border:1px solid var(--border);border-radius:11px;background:var(--surface-sunken)}.team-capability>div:first-child{display:flex;flex-direction:column;gap:3px}.team-capability strong{color:var(--text-primary);font-size:12.5px}.team-capability span,.team-capability small{color:var(--text-tertiary);font-size:10.5px}.team-presence{display:flex;align-items:center;gap:10px}.team-presence svg{color:var(--success)}.team-presence>div{display:flex;flex-direction:column;gap:3px}.team-presence strong{font-size:13px}.team-presence span{font-size:10.5px;color:var(--text-tertiary)}.team-metric{padding:7px 0}.team-metric>div:first-child{display:flex;justify-content:space-between;color:var(--text-secondary);font-size:11.5px}.team-metric>div:last-child{margin-top:6px}.team-row-actions{display:flex;align-items:center;gap:10px}
  @media(max-width:1180px){.team-kpis{grid-template-columns:repeat(3,1fr)}}@media(max-width:850px){.team-insight-grid,.team-detail-grid{grid-template-columns:1fr}.team-capability{grid-template-columns:1fr}.team-profile-head{align-items:flex-start;flex-wrap:wrap}.team-profile-head>button{width:100%}}@media(max-width:620px){.team-kpis,.team-kpis-four{grid-template-columns:repeat(2,1fr)}.team-toolbar{align-items:stretch}.team-toolbar>*{flex:1 1 145px}.team-search{min-width:100%}.team-result-line>span:last-child{display:none}.team-insight{align-items:flex-start;flex-wrap:wrap}.team-insight a{margin-left:50px}.team-pagination{flex-wrap:wrap}}
`}</style>; }
