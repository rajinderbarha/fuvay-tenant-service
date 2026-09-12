"use client";

import React, {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  ExternalLink,
  Filter,
  MapPin,
  RefreshCw,
  Search,
  ShieldAlert,
  Truck,
  UserCheck,
  UserPlus,
  UserX,
  Users,
  Wrench,
  X,
} from "lucide-react";
import { DefaultAvatar } from "../../../../components/shared/ProfilePhotoUploader";
import {
  DispatchDateNavigator,
  TenantDispatchBoard,
} from "../../../../components/dispatch/TenantDispatchBoard";
import {
  Alert,
  Button,
  Card,
  Drawer,
  Input,
  KpiGrid,
  Modal,
  PageHeader,
  PageShell,
  Pagination,
  Select,
  Skeleton,
  StatusBadge,
  SummaryCard,
  Textarea,
} from "@serviceos/design-system";
import {
  homeServicesDispatchApi,
  serviceJobAssignmentApi,
  ServiceOSError,
  type HsAssignmentOptions,
  type HsAssignmentOptionTechnician,
  type HsDispatchJobSummary,
  type HsDispatchProjection,
  type ProviderSlot,
} from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const PAGE_PATH = "/home-services/dispatch";
const PAGE_SIZES = [25, 50, 100];
const DAY_START = 8;
const DAY_END = 20;
const EXCLUSION_LABELS: Record<string, string> = {
  STAFF_INACTIVE: "Inactive or assignment disabled",
  STAFF_NOT_VERIFIED: "Verification incomplete",
  JOB_TYPE_UNSUPPORTED: "Required service skill is missing",
  SERVICE_NOT_CONFIGURED: "Provider service is not configured",
  TYPE_UNSUPPORTED: "Equipment type unsupported",
  BRAND_UNSUPPORTED: "Brand unsupported",
  OUTSIDE_AVAILABILITY: "Working hours are not configured",
  SCHEDULE_CONFLICT: "Overlapping assignment",
  ACTIVE_JOB_IN_PROGRESS: "Technician already has an open job",
  CAPACITY_EXCEEDED: "Capacity reached",
  OUTSIDE_COVERAGE: "Outside coverage",
  TENANT_MISMATCH: "Different business",
};

function localToday() {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}
function shiftDate(value: string, days: number) {
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}
function formatDate(value: string, weekday = true) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", {
    ...(weekday ? { weekday: "short" } : {}),
    day: "2-digit",
    month: "short",
  });
}
function parsePage(value: string | null) {
  const parsed = Number(value ?? 1);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}
function parsePageSize(value: string | null) {
  const parsed = Number(value ?? 25);
  return PAGE_SIZES.includes(parsed) ? parsed : 25;
}
function parseTimePart(value: string, meridiem?: string) {
  const [hourText, minuteText] = value.split(":");
  let hour = Number(hourText);
  const minute = Number(minuteText || 0);
  if (meridiem) {
    hour %= 12;
    if (meridiem.toUpperCase() === "PM") hour += 12;
  }
  return Number.isFinite(hour) && Number.isFinite(minute)
    ? hour + minute / 60
    : null;
}
function parseWindow(
  value?: string | null,
): { start: number; end: number } | null {
  if (!value) return null;
  const match = value
    .trim()
    .match(
      /^(\d{1,2}(?::\d{2})?)\s*(AM|PM)?\s*-\s*(\d{1,2}(?::\d{2})?)\s*(AM|PM)?$/i,
    );
  if (!match) return null;
  const start = parseTimePart(match[1], match[2]);
  const end = parseTimePart(match[3], match[4] || match[2]);
  return start == null || end == null || end <= start ? null : { start, end };
}
function dueLabel(job: HsDispatchJobSummary) {
  const minutes = job.minutes_until_due;
  if (minutes == null) return null;
  const absolute = Math.abs(minutes);
  const readable =
    absolute >= 60
      ? `${Math.floor(absolute / 60)}h ${absolute % 60}m`
      : `${absolute}m`;
  return minutes < 0 ? `${readable} overdue` : `${readable} left`;
}

function compactJobNumber(value: string) {
  if (value.length <= 12) return value;
  return `JOB-${value.slice(-6)}`;
}

function ServiceJobIcon({ job, size = 44 }: { job: HsDispatchJobSummary; size?: number }) {
  return (
    <span
      aria-hidden="true"
      style={{
        position: "relative",
        width: size,
        height: size,
        flex: `0 0 ${size}px`,
        display: "grid",
        placeItems: "center",
        overflow: "hidden",
        borderRadius: 10,
        color: "var(--brand)",
        background: "var(--accent-muted)",
        border: "1px solid var(--border)",
      }}
    >
      <Wrench size={Math.round(size * 0.45)} strokeWidth={1.8} />
      {job.service_icon_url ? (
        <img
          src={job.service_icon_url}
          alt=""
          loading="lazy"
          onError={(event) => {
            event.currentTarget.style.display = "none";
          }}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "contain",
            padding: 6,
            background: "var(--surface-raised)",
          }}
        />
      ) : null}
    </span>
  );
}

export default function DispatchPage() {
  return (
    <Suspense fallback={<DispatchSkeleton />}>
      <DispatchWorkspace />
    </Suspense>
  );
}
function DispatchSkeleton() {
  return (
    <PageShell>
      <Skeleton height={700} />
    </PageShell>
  );
}

function DispatchWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const date = params.get("date") || localToday();
  const view = params.get("view") === "week" ? "week" : "day";
  const search = params.get("search") || "";
  const serviceId = params.get("service") || "";
  const technicianId = params.get("technician") || "";
  const focus = params.get("focus") || "all";
  const selectedJobId = params.get("job_id");
  const page = parsePage(params.get("page"));
  const pageSize = parsePageSize(params.get("page_size"));
  const [searchDraft, setSearchDraft] = useState(search);
  const [showFilters, setShowFilters] = useState(false);
  const [showCapacity, setShowCapacity] = useState(true);
  const [options, setOptions] = useState<HsAssignmentOptions | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);
  const [pendingAction, setPendingAction] = useState<{
    type: "assign" | "reassign" | "unassign";
    technician?: HsAssignmentOptionTechnician;
  } | null>(null);
  const [reason, setReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [availableSlots, setAvailableSlots] = useState<ProviderSlot[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [scheduleReason, setScheduleReason] = useState("");
  useEffect(() => setSearchDraft(search), [search]);

  const updateParams = useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(params.toString());
      Object.entries(updates).forEach(([key, value]) =>
        value ? next.set(key, value) : next.delete(key),
      );
      router.push(next.size ? `${PAGE_PATH}?${next}` : PAGE_PATH);
    },
    [params, router],
  );
  const dependencies = [
    date,
    view,
    search,
    serviceId,
    technicianId,
    page,
    pageSize,
  ];
  const board = useApi<HsDispatchProjection>(
    useCallback(
      () =>
        homeServicesDispatchApi.getDispatchBoard({
          date,
          view,
          search: search || undefined,
          offering_id: serviceId || undefined,
          technician_id: technicianId || undefined,
          limit: pageSize,
          offset: (page - 1) * pageSize,
        }),
      dependencies,
    ),
    dependencies,
  );
  const loadOptions = useCallback(async (jobId: string) => {
    setOptionsLoading(true);
    setOptionsError(null);
    setOptions(null);
    setShowExcluded(false);
    try {
      setOptions(await homeServicesDispatchApi.getAssignmentOptions(jobId));
    } catch (error) {
      setOptionsError(
        error instanceof ServiceOSError
          ? error.message
          : "Could not load assignment options.",
      );
    } finally {
      setOptionsLoading(false);
    }
  }, []);
  useEffect(() => {
    if (selectedJobId) loadOptions(selectedJobId);
    else {
      setOptions(null);
      setOptionsError(null);
    }
  }, [loadOptions, selectedJobId]);
  useEffect(() => {
    const total = board.data?.pagination.total;
    if (total == null || page === 1) return;
    const last = Math.max(1, Math.ceil(total / pageSize));
    if (page > last) updateParams({ page: String(last), job_id: null });
  }, [board.data?.pagination.total, page, pageSize, updateParams]);

  const scheduledJobs = useMemo(() => {
    const jobs = board.data?.scheduled_jobs ?? [];
    return focus === "conflicts"
      ? jobs.filter((job) => job.has_conflict)
      : jobs;
  }, [board.data?.scheduled_jobs, focus]);
  const selectJob = (jobId: string) => updateParams({ job_id: jobId });
  const clearFilters = () =>
    updateParams({
      search: null,
      service: null,
      technician: null,
      focus: null,
      page: null,
      job_id: null,
    });
  const stepDate = view === "week" ? 7 : 1;
  const hasFilters = Boolean(
    search || serviceId || technicianId || focus !== "all",
  );
  function submitSearch(event: React.FormEvent) {
    event.preventDefault();
    updateParams({
      search: searchDraft.trim() || null,
      page: null,
      job_id: null,
    });
  }

  async function executeAssignment() {
    if (!selectedJobId || !pendingAction) return;
    if (
      (pendingAction.type === "reassign" ||
        pendingAction.type === "unassign") &&
      !reason.trim()
    )
      return;
    setActionLoading(true);
    setOptionsError(null);
    try {
      if (pendingAction.type === "unassign")
        await homeServicesDispatchApi.unassign(selectedJobId, reason.trim());
      else if (pendingAction.type === "reassign" && pendingAction.technician)
        await homeServicesDispatchApi.reassign(
          selectedJobId,
          pendingAction.technician.staff_member_id,
          reason.trim(),
        );
      else if (pendingAction.technician)
        await homeServicesDispatchApi.assign(
          selectedJobId,
          pendingAction.technician.staff_member_id,
        );
      setPendingAction(null);
      setReason("");
      await Promise.all([board.refetch(), loadOptions(selectedJobId)]);
    } catch (error) {
      setOptionsError(
        error instanceof ServiceOSError
          ? error.message
          : "The assignment could not be saved.",
      );
      setPendingAction(null);
    } finally {
      setActionLoading(false);
    }
  }
  async function openSchedule() {
    if (!selectedJobId) return;
    setScheduleOpen(true);
    setSelectedSlot("");
    setScheduleReason("");
    setSlotsLoading(true);
    setOptionsError(null);
    try {
      const result = await serviceJobAssignmentApi.availableSlots(
        selectedJobId,
        Boolean(options?.job_context.is_emergency),
      );
      setAvailableSlots(result.slots ?? []);
    } catch (error) {
      setOptionsError(
        error instanceof ServiceOSError
          ? error.message
          : "Available slots could not be loaded.",
      );
    } finally {
      setSlotsLoading(false);
    }
  }
  async function saveSchedule() {
    if (!selectedJobId || !selectedSlot) return;
    const slot = availableSlots.find(
      (item) => `${item.date}|${item.time_window}` === selectedSlot,
    );
    if (!slot) return;
    const changingExisting = Boolean(options?.job_context.scheduled_date);
    if (changingExisting && !scheduleReason.trim()) return;
    setActionLoading(true);
    try {
      const result = await serviceJobAssignmentApi.schedule(selectedJobId, {
        scheduled_date: slot.date,
        scheduled_time_window: slot.time_window,
        reason: scheduleReason.trim() || undefined,
      });
      if (!result.success)
        throw new ServiceOSError(
          result.error_code || "SCHEDULE_FAILED",
          result.message || "The schedule could not be saved.",
        );
      setScheduleOpen(false);
      await Promise.all([board.refetch(), loadOptions(selectedJobId)]);
    } catch (error) {
      setOptionsError(
        error instanceof ServiceOSError
          ? error.message
          : "The schedule could not be saved.",
      );
      setScheduleOpen(false);
    } finally {
      setActionLoading(false);
    }
  }

  const summary = board.data?.summary;
  const unassignedVisible = focus === "all" || focus === "unassigned";
  const scheduleVisible =
    focus === "all" || focus === "scheduled" || focus === "conflicts";
  return (
    <>
      <PageShell>
        <PageHeader
          eyebrow=""
          title="Dispatch"
          description="Match unassigned jobs to a free, qualified technician for the customer's booked slot."
          actions={<DispatchDateNavigator
            dateLabel={`${date === localToday() ? "Today · " : ""}${formatDate(date)}`}
            onPrevious={() => updateParams({ date: shiftDate(date, -1), page: null, job_id: null })}
            onNext={() => updateParams({ date: shiftDate(date, 1), page: null, job_id: null })}
          />}
        />
        {board.error && <Alert tone="danger">{board.error}</Alert>}
        {board.data?.schedule_truncated && <Alert tone="warning">This day contains more than 5,000 scheduled visits. Choose another date or narrow the work from Bookings &amp; jobs.</Alert>}
        {board.loading && !board.data
          ? <div style={{ display: "grid", gap: 18 }}><div className="tenant-dispatch-kpis">{Array.from({ length: 3 }, (_, index) => <Skeleton key={index} height={109} />)}</div><Skeleton height={190} /><Skeleton height={390} /></div>
          : board.data && <TenantDispatchBoard board={board.data} date={date} selectedJobId={selectedJobId} onSelectJob={selectJob} />}
        {false && <div>
        <style>{`.dispatch-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.dispatch-period-bar{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:8px 10px;border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface)}.dispatch-kpis{display:grid;grid-template-columns:repeat(5,minmax(140px,1fr));gap:10px}.dispatch-filters{display:grid;grid-template-columns:minmax(240px,1.6fr) repeat(2,minmax(160px,.7fr)) auto;gap:10px;align-items:end}.dispatch-grid{display:grid;grid-template-columns:minmax(330px,34%) minmax(0,1fr);gap:12px;align-items:stretch}.dispatch-grid>*{min-width:0}.dispatch-grid.schedule-only{grid-template-columns:minmax(0,1fr)}.dispatch-grid.queue-only{grid-template-columns:minmax(330px,520px)}.dispatch-panel-card{height:clamp(460px,calc(100vh - 390px),660px);display:flex!important;flex-direction:column;overflow:hidden}.dispatch-panel-card>.dispatch-board-scroll{flex:1;min-height:0;max-height:none!important}.dispatch-board-scroll{max-height:clamp(420px,calc(100vh - 390px),660px)!important}.dispatch-selection-hint{display:flex;justify-content:flex-end;align-items:center;gap:7px;color:var(--text-tertiary);font-size:11.5px;padding:0 4px}.week-grid{display:grid;grid-template-columns:160px repeat(7,minmax(130px,1fr));min-width:1080px}.week-cell{min-height:88px;padding:8px;border-right:1px solid var(--border);border-bottom:1px solid var(--border)}.dispatch-switch{width:36px;height:20px;padding:2px;border:0;border-radius:999px;background:var(--surface-sunken);box-shadow:inset 0 0 0 1px var(--border);cursor:pointer;display:inline-flex;align-items:center;transition:.18s}.dispatch-switch[data-on=true]{background:var(--brand)}.dispatch-switch>span{width:16px;height:16px;border-radius:50%;background:white;box-shadow:0 1px 3px rgba(0,0,0,.28);transform:translateX(0);transition:.18s}.dispatch-switch[data-on=true]>span{transform:translateX(16px)}@media(max-width:1180px){.dispatch-filters{grid-template-columns:minmax(220px,1fr) repeat(2,minmax(150px,.7fr))}.dispatch-filters>.dispatch-actions{grid-column:1/-1}}@media(max-width:1050px){.dispatch-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.dispatch-filters{grid-template-columns:1fr 1fr}.dispatch-grid,.dispatch-grid.schedule-only,.dispatch-grid.queue-only{grid-template-columns:1fr}.dispatch-panel-card{height:auto;min-height:420px}.dispatch-board-scroll{max-height:560px!important}.dispatch-selection-hint{justify-content:flex-start}}@media(max-width:720px){.dispatch-period-bar{align-items:flex-start;flex-direction:column}.dispatch-period-bar>.dispatch-actions{width:100%}.dispatch-filters{grid-template-columns:1fr}.dispatch-filters>.dispatch-actions{grid-column:auto}.dispatch-kpis{grid-template-columns:1fr}}`}</style>
        <PageHeader
          eyebrow=""
          title="Dispatch"
          description="Match unassigned jobs to a free, qualified technician for the customer's booked slot."
          actions={
            <div className="dispatch-actions">
              <Button
                variant="secondary"
                onClick={() => router.push("/home-services/bookings-jobs")}
              >
                All jobs <ExternalLink size={14} />
              </Button>
              <Button
                variant="secondary"
                onClick={board.refetch}
                loading={board.loading}
              >
                <RefreshCw size={14} /> Refresh
              </Button>
            </div>
          }
        />
        <div className="dispatch-period-bar">
          <div className="dispatch-actions">
            <Button
              variant="secondary"
              size="sm"
              aria-label="Previous period"
              onClick={() =>
                updateParams({
                  date: shiftDate(date, -stepDate),
                  page: null,
                  job_id: null,
                })
              }
            >
              <ChevronLeft size={15} />
            </Button>
            <Button
              variant={date === localToday() ? "primary" : "secondary"}
              size="sm"
              onClick={() =>
                updateParams({ date: localToday(), page: null, job_id: null })
              }
            >
              Today
            </Button>
            <strong style={{ color: "var(--text-primary)", fontSize: 14 }}>
              {view === "week"
                ? `${formatDate(date)} – ${formatDate(shiftDate(date, 6))}`
                : formatDate(date)}
            </strong>
            <Button
              variant="secondary"
              size="sm"
              aria-label="Next period"
              onClick={() =>
                updateParams({
                  date: shiftDate(date, stepDate),
                  page: null,
                  job_id: null,
                })
              }
            >
              <ChevronRight size={15} />
            </Button>
          </div>
          <div className="dispatch-actions">
            <Button
              variant={view === "day" ? "primary" : "secondary"}
              size="sm"
              onClick={() =>
                updateParams({ view: "day", page: null, job_id: null })
              }
            >
              Day
            </Button>
            <Button
              variant={view === "week" ? "primary" : "secondary"}
              size="sm"
              onClick={() =>
                updateParams({ view: "week", page: null, job_id: null })
              }
            >
              Week
            </Button>
            {board.data && (
              <span style={{ color: "var(--text-tertiary)", fontSize: 11.5 }}>
                Updated{" "}
                {new Date(board.data.generated_at).toLocaleTimeString("en-IN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>
        </div>
        {board.error && <Alert tone="danger">{board.error}</Alert>}
        {board.data?.schedule_truncated && (
          <Alert tone="warning">
            This period contains more than 5,000 scheduled visits. Narrow the
            service or technician filter to work safely.
          </Alert>
        )}
        {board.loading && !board.data ? (
          <KpiGrid minCardWidth={160}>
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton key={index} height={108} />
            ))}
          </KpiGrid>
        ) : (
          summary && (
            <div className="dispatch-kpis">
              <SummaryCard
                label="Unassigned"
                value={summary.unassigned_count}
                sub="Needs an owner"
                icon={<UserX />}
                tone={summary.unassigned_count ? "warning" : undefined}
                active={focus === "unassigned"}
                onClick={() =>
                  updateParams({
                    focus: focus === "unassigned" ? null : "unassigned",
                    page: null,
                    job_id: null,
                  })
                }
              />
              <SummaryCard
                label="Scheduled"
                value={summary.scheduled_count}
                sub={view === "week" ? "This week" : "Selected day"}
                icon={<CalendarDays />}
                tone="info"
                active={focus === "scheduled"}
                onClick={() =>
                  updateParams({
                    focus: focus === "scheduled" ? null : "scheduled",
                    page: null,
                    job_id: null,
                  })
                }
              />
              <SummaryCard
                label="On the way"
                value={summary.on_the_way_count}
                sub="Travel in progress"
                icon={<Truck />}
                tone="success"
              />
              <SummaryCard
                label="Capacity"
                value={`${summary.capacity_used}/${summary.capacity_total}`}
                sub="Roster utilization"
                icon={<Users />}
              />
              <SummaryCard
                label="Conflicting jobs"
                value={summary.conflict_count}
                sub="Overlapping visits"
                icon={<ShieldAlert />}
                tone={summary.conflict_count ? "danger" : undefined}
                active={focus === "conflicts"}
                onClick={() =>
                  updateParams({
                    focus: focus === "conflicts" ? null : "conflicts",
                    page: null,
                    job_id: null,
                  })
                }
              />
            </div>
          )
        )}
        <Card padding="none">
          <div style={{ padding: 14 }} className="dispatch-filters">
            <form onSubmit={submitSearch} style={{ display: "flex", gap: 8 }}>
              <Input
                aria-label="Search dispatch"
                placeholder="Search job, booking, service, issue or city"
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
              />
              <Button type="submit" variant="secondary">
                <Search size={15} />
              </Button>
            </form>
            <Select
              label="Service"
              value={serviceId}
              onChange={(event) =>
                updateParams({
                  service: event.target.value || null,
                  page: null,
                  job_id: null,
                })
              }
              options={[
                { value: "", label: "All services" },
                ...(board.data?.filters.services ?? []).map((item) => ({
                  value: item.id,
                  label: item.name,
                })),
              ]}
            />
            <Select
              label="Technician"
              value={technicianId}
              onChange={(event) =>
                updateParams({
                  technician: event.target.value || null,
                  page: null,
                  job_id: null,
                })
              }
              options={[
                { value: "", label: "All technicians" },
                ...(board.data?.filters.technicians ?? []).map((item) => ({
                  value: item.staff_member_id,
                  label: item.name,
                })),
              ]}
            />
            <div className="dispatch-actions">
              <Button
                variant={showFilters ? "primary" : "secondary"}
                onClick={() => setShowFilters((value) => !value)}
              >
                <Filter size={14} /> Focus
              </Button>
              {hasFilters && (
                <Button variant="ghost" onClick={clearFilters}>
                  <X size={14} /> Clear
                </Button>
              )}
            </div>
          </div>
          {showFilters && (
            <div
              style={{
                padding: "0 14px 14px",
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
              }}
            >
              {[
                ["all", "All work"],
                ["unassigned", "Unassigned"],
                ["scheduled", "Scheduled"],
                ["conflicts", "Conflicts"],
              ].map(([value, label]) => (
                <Button
                  key={value}
                  size="sm"
                  variant={focus === value ? "primary" : "secondary"}
                  onClick={() =>
                    updateParams({
                      focus: value === "all" ? null : value,
                      page: null,
                      job_id: null,
                    })
                  }
                >
                  {label}
                </Button>
              ))}
            </div>
          )}
        </Card>
        {board.loading && !board.data ? (
          <div className="dispatch-grid">
            <Skeleton height={560} />
            <Skeleton height={560} />
            <Skeleton height={560} />
          </div>
        ) : (
          board.data && (
            <div
              className={`dispatch-grid ${
                unassignedVisible && scheduleVisible
                  ? ""
                  : scheduleVisible
                    ? "schedule-only"
                    : "queue-only"
              }`}
            >
              {unassignedVisible && (
                <UnassignedQueue
                  jobs={board.data.unassigned_jobs}
                  selectedJobId={selectedJobId}
                  total={board.data.pagination.total}
                  page={page}
                  pageSize={pageSize}
                  onSelect={selectJob}
                  onPage={(next) =>
                    updateParams({ page: String(next), job_id: null })
                  }
                  onPageSize={(size) =>
                    updateParams({
                      page_size: String(size),
                      page: null,
                      job_id: null,
                    })
                  }
                />
              )}
              {scheduleVisible && (
                <Card padding="none" className="dispatch-panel-card">
                  <div
                    style={{
                      padding: "14px 16px",
                      borderBottom: "1px solid var(--border)",
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                    }}
                  >
                    <div>
                      <h2 style={sectionTitle}>Technician schedule</h2>
                      <p style={sectionSub}>
                        {view === "week"
                          ? "Seven-day workload and conflicts"
                          : "Committed visits by technician and time"}
                      </p>
                    </div>
                    <div className="dispatch-actions" style={{ flexWrap: "nowrap" }}>
                      <span style={{ color: "var(--text-secondary)", fontSize: 11.5, whiteSpace: "nowrap" }}>
                        View capacity
                      </span>
                      <button
                        type="button"
                        role="switch"
                        aria-checked={showCapacity}
                        aria-label="Show technician capacity"
                        className="dispatch-switch"
                        data-on={showCapacity}
                        onClick={() => setShowCapacity((value) => !value)}
                      >
                        <span />
                      </button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => router.push("/home-services/team")}
                      >
                        Manage team <ExternalLink size={13} />
                      </Button>
                    </div>
                  </div>
                  {view === "day" ? (
                    <DaySchedule
                      targetDate={date}
                      technicians={board.data.technician_schedule}
                      jobs={scheduledJobs}
                      showCapacity={showCapacity}
                      selectedJobId={selectedJobId}
                      onSelect={selectJob}
                    />
                  ) : (
                    <WeekSchedule
                      start={date}
                      technicians={board.data.technician_schedule}
                      jobs={scheduledJobs}
                      showCapacity={showCapacity}
                      selectedJobId={selectedJobId}
                      onSelect={selectJob}
                    />
                  )}
                </Card>
              )}
            </div>
          )
        )}
        {board.data && !selectedJobId && (
          <div className="dispatch-selection-hint">
            <UserCheck size={14} /> Select a job to assign or reschedule
          </div>
        )}
        </div>}
        <Drawer
          open={Boolean(selectedJobId)}
          onClose={() => updateParams({ job_id: null })}
          title="Job assignment"
        >
          <AssignmentPanel
            jobId={selectedJobId}
            options={options}
            loading={optionsLoading}
            error={optionsError}
            actionLoading={actionLoading}
            showExcluded={showExcluded}
            onShowExcluded={() => setShowExcluded((value) => !value)}
            onOpenJob={() =>
              selectedJobId && router.push(`/home-services/bookings-jobs?job_id=${selectedJobId}`)
            }
            onSchedule={openSchedule}
            onAssign={(technician) =>
              setPendingAction({
                type: options?.current_assignment ? "reassign" : "assign",
                technician,
              })
            }
            onUnassign={() => setPendingAction({ type: "unassign" })}
          />
        </Drawer>
        <Modal
          open={Boolean(pendingAction)}
          onClose={() => !actionLoading && setPendingAction(null)}
          title={
            pendingAction?.type === "unassign"
              ? "Remove assignment"
              : pendingAction?.type === "reassign"
                ? "Confirm reassignment"
                : "Confirm assignment"
          }
        >
          <div style={{ display: "grid", gap: 14 }}>
            <p style={bodyText}>
              {pendingAction?.type === "unassign"
                ? "The job returns to the unassigned queue. The technician will no longer own this visit."
                : `${pendingAction?.technician?.name ?? "This technician"} will become responsible for this visit.`}
            </p>
            {pendingAction?.type !== "assign" && (
              <Textarea
                label="Reason"
                required
                rows={3}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Record the operational reason for the audit trail"
              />
            )}
            <div
              className="dispatch-actions"
              style={{ justifyContent: "flex-end" }}
            >
              <Button
                variant="secondary"
                onClick={() => setPendingAction(null)}
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                variant={
                  pendingAction?.type === "unassign" ? "destructive" : "primary"
                }
                loading={actionLoading}
                disabled={pendingAction?.type !== "assign" && !reason.trim()}
                onClick={executeAssignment}
              >
                Confirm
              </Button>
            </div>
          </div>
        </Modal>
        <Modal
          open={scheduleOpen}
          onClose={() => !actionLoading && setScheduleOpen(false)}
          title={
            options?.job_context.scheduled_date
              ? "Reschedule visit"
              : "Schedule visit"
          }
        >
          <div style={{ display: "grid", gap: 14 }}>
            {slotsLoading ? (
              <Skeleton height={90} />
            ) : availableSlots.length ? (
              <Select
                label="Available slot"
                required
                value={selectedSlot}
                onChange={(event) => setSelectedSlot(event.target.value)}
                placeholder="Choose a capacity-checked slot"
                options={availableSlots.map((slot) => ({
                  value: `${slot.date}|${slot.time_window}`,
                  label: `${formatDate(slot.date)} · ${slot.time_window}${slot.capacity != null ? ` · ${Math.max(0, slot.capacity - (slot.already_booked ?? 0))} open` : ""}`,
                }))}
              />
            ) : (
              <Alert tone="warning">
                No bookable slots are available. Check team working hours and
                capacity before scheduling.
              </Alert>
            )}
            {options?.job_context.scheduled_date && (
              <Textarea
                label="Reason for change"
                required
                rows={3}
                value={scheduleReason}
                onChange={(event) => setScheduleReason(event.target.value)}
                placeholder="Why is this committed visit moving?"
              />
            )}
            <div
              className="dispatch-actions"
              style={{ justifyContent: "space-between" }}
            >
              <Button
                variant="ghost"
                onClick={() => router.push("/business/coverage-hours")}
              >
                Manage availability <ExternalLink size={13} />
              </Button>
              <div className="dispatch-actions">
                <Button
                  variant="secondary"
                  onClick={() => setScheduleOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  loading={actionLoading}
                  disabled={
                    !selectedSlot ||
                    Boolean(
                      options?.job_context.scheduled_date &&
                      !scheduleReason.trim(),
                    )
                  }
                  onClick={saveSchedule}
                >
                  Save schedule
                </Button>
              </div>
            </div>
          </div>
        </Modal>
      </PageShell>
    </>
  );
}

const sectionTitle: React.CSSProperties = {
  margin: 0,
  color: "var(--text-primary)",
  fontSize: 15,
  fontWeight: 750,
};
const sectionSub: React.CSSProperties = {
  margin: "3px 0 0",
  color: "var(--text-tertiary)",
  fontSize: 11.5,
};
const bodyText: React.CSSProperties = {
  margin: 0,
  color: "var(--text-secondary)",
  fontSize: 13,
  lineHeight: 1.55,
};

function UnassignedQueue({
  jobs,
  selectedJobId,
  total,
  page,
  pageSize,
  onSelect,
  onPage,
  onPageSize,
}: {
  jobs: HsDispatchJobSummary[];
  selectedJobId: string | null;
  total: number;
  page: number;
  pageSize: number;
  onSelect: (id: string) => void;
  onPage: (page: number) => void;
  onPageSize: (size: number) => void;
}) {
  const [sort, setSort] = useState<"oldest" | "due">("oldest");
  const sorted = [...jobs].sort((first, second) => {
    if (sort === "due") {
      return (
        (first.minutes_until_due ?? Number.MAX_SAFE_INTEGER) -
        (second.minutes_until_due ?? Number.MAX_SAFE_INTEGER)
      );
    }
    return new Date(first.requested_at || 0).getTime() - new Date(second.requested_at || 0).getTime();
  });
  return (
    <Card padding="none" className="dispatch-panel-card">
      <div
        style={{
          padding: "12px 14px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <h2 style={sectionTitle}>Unassigned queue</h2>
          <span
            style={{
              minWidth: 24,
              height: 24,
              padding: "0 7px",
              display: "inline-grid",
              placeItems: "center",
              borderRadius: 999,
              color: "var(--text-secondary)",
              background: "var(--surface-sunken)",
              border: "1px solid var(--border)",
              fontSize: 11,
              fontWeight: 750,
            }}
          >
            {total}
          </span>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className="ds-text-caption" style={{ color: "var(--text-tertiary)" }}>Sort</span>
          <select
            aria-label="Sort unassigned jobs"
            value={sort}
            onChange={(event) => setSort(event.target.value as "oldest" | "due")}
            style={{
              border: 0,
              outline: 0,
              background: "transparent",
              color: "var(--text-secondary)",
              fontSize: 11.5,
              cursor: "pointer",
            }}
          >
            <option value="oldest">Oldest first</option>
            <option value="due">Due first</option>
          </select>
        </label>
      </div>
      <div className="dispatch-board-scroll" style={{ overflowY: "auto" }}>
        {sorted.length ? (
          sorted.map((job) => (
            <JobQueueCard
              key={job.job_id}
              job={job}
              selected={job.job_id === selectedJobId}
              onClick={() => onSelect(job.job_id)}
            />
          ))
        ) : (
          <EmptyPanel
            icon={<CheckCircle2 size={22} />}
            title="Queue is clear"
            message="No unassigned jobs match this period and filter."
          />
        )}
      </div>
      {total > 0 && (
        <div style={{ padding: "8px 10px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
          <label
            style={{
              display: "flex",
              gap: 7,
              alignItems: "center",
              color: "var(--text-tertiary)",
              fontSize: 11.5,
              marginBottom: 0,
            }}
          >
            Rows
            <select
              value={pageSize}
              onChange={(event) => onPageSize(Number(event.target.value))}
              style={{
                background: "var(--surface)",
                color: "var(--text-primary)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: 4,
              }}
            >
              {PAGE_SIZES.map((size) => (
                <option key={size}>{size}</option>
              ))}
            </select>
          </label>
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            alwaysShow
            onPage={onPage}
          />
        </div>
      )}
    </Card>
  );
}
function JobQueueCard({
  job,
  selected,
  onClick,
}: {
  job: HsDispatchJobSummary;
  selected: boolean;
  onClick: () => void;
}) {
  const due = dueLabel(job);
  const displayTime = job.scheduled_time_window || job.requested_time_window;
  return (
    <button
      onClick={onClick}
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        border: 0,
        borderBottom: "1px solid var(--border)",
        borderLeft: `3px solid ${job.is_emergency ? "var(--warning-text)" : selected ? "var(--brand)" : "transparent"}`,
        padding: "10px 12px",
        background: selected ? "var(--accent-muted)" : "transparent",
        cursor: "pointer",
      }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <ServiceJobIcon job={job} size={42} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <strong
              style={{
                color: "var(--text-primary)",
                fontSize: 12.5,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {job.job_number}
            </strong>
            <span style={{ flexShrink: 0, color: "var(--text-secondary)", fontSize: 11 }}>
              {displayTime || "Time slot pending"}
            </span>
          </div>
          <div style={{ marginTop: 2, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <span style={{ color: "var(--text-secondary)", fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {job.master_service_name || "Service visit"}
            </span>
            <span style={{ color: job.is_emergency ? "var(--warning-text)" : "var(--text-link)", fontSize: 10.5 }}>
              {job.is_emergency ? "Emergency" : due || "Standard"}
            </span>
          </div>
          <span style={{ marginTop: 4, display: "flex", gap: 5, alignItems: "center", color: "var(--text-tertiary)", fontSize: 10.5, minWidth: 0 }}>
            <MapPin size={11} style={{ flexShrink: 0 }} />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {job.customer_address || job.locality || "Service address unavailable"}
            </span>
          </span>
        </div>
      </div>
    </button>
  );
}

function DaySchedule({
  targetDate,
  technicians,
  jobs,
  showCapacity,
  selectedJobId,
  onSelect,
}: {
  targetDate: string;
  technicians: HsDispatchProjection["technician_schedule"];
  jobs: HsDispatchJobSummary[];
  showCapacity: boolean;
  selectedJobId: string | null;
  onSelect: (id: string) => void;
}) {
  const allowed = new Set(jobs.map((job) => job.job_id));
  const now = new Date();
  const nowHour = now.getHours() + now.getMinutes() / 60;
  const currentPosition =
    localToday() === targetDate &&
    nowHour >= DAY_START &&
    nowHour <= DAY_END
      ? ((nowHour - DAY_START) / (DAY_END - DAY_START)) * 100
      : null;
  return (
    <div className="dispatch-board-scroll" style={{ overflow: "auto", minHeight: 0 }}>
      {technicians.length ? (
        <div style={{ minWidth: 920, minHeight: "100%" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "160px 1fr",
              borderBottom: "1px solid var(--border)",
              minHeight: 36,
            }}
          >
            <span />
            <div style={{ position: "relative", display: "grid", gridTemplateColumns: `repeat(${DAY_END - DAY_START},1fr)` }}>
              {Array.from({ length: DAY_END - DAY_START }, (_, index) => (
                <span
                  key={index}
                  style={{
                    padding: "9px 4px 7px",
                    textAlign: "center",
                    color: "var(--text-tertiary)",
                    fontSize: 10,
                  }}
                >
                  {String(((DAY_START + index - 1) % 12) + 1)}{" "}
                  {DAY_START + index >= 12 ? "PM" : "AM"}
                </span>
              ))}
              {currentPosition != null ? (
                <span
                  style={{
                    position: "absolute",
                    left: `${currentPosition}%`,
                    top: 3,
                    transform: "translateX(-50%)",
                    zIndex: 5,
                    padding: "3px 6px",
                    borderRadius: 5,
                    background: "var(--brand)",
                    color: "white",
                    fontSize: 9.5,
                    fontWeight: 750,
                    whiteSpace: "nowrap",
                  }}
                >
                  {now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                </span>
              ) : null}
            </div>
          </div>
          {technicians.map((technician, technicianIndex) => {
            const techJobs = (
              technician.jobs_in_range ||
              technician.jobs_today ||
              []
            ).filter((job) => allowed.has(job.job_id));
            return (
              <div
                key={technician.staff_member_id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "160px 1fr",
                  minHeight: 82,
                  borderBottom: "1px solid var(--border)",
                }}
              >
                <div style={{ padding: "14px 10px", borderRight: "1px solid var(--border)" }}>
                  <TechnicianLabel technician={technician} showCapacity={showCapacity} />
                </div>
                <div style={{ position: "relative", minHeight: 81, overflow: "hidden" }}>
                  {Array.from({ length: DAY_END - DAY_START }, (_, index) => (
                    <span
                      key={index}
                      aria-hidden="true"
                      style={{
                        position: "absolute",
                        insetBlock: 0,
                        left: `${(index / (DAY_END - DAY_START)) * 100}%`,
                        borderLeft: "1px dashed var(--border)",
                        opacity: 0.7,
                      }}
                    />
                  ))}
                  {currentPosition != null ? (
                    <span
                      aria-hidden="true"
                      style={{
                        position: "absolute",
                        insetBlock: 0,
                        left: `${currentPosition}%`,
                        borderLeft: "1px solid var(--brand)",
                        zIndex: 3,
                        pointerEvents: "none",
                      }}
                    />
                  ) : null}
                  {techJobs.length ? (
                    techJobs.map((job) => {
                      const window = parseWindow(job.scheduled_time_window);
                      if (!window)
                        return (
                          <JobChip
                            key={job.job_id}
                            job={job}
                            selected={job.job_id === selectedJobId}
                            onClick={() => onSelect(job.job_id)}
                          />
                        );
                      const left = Math.max(
                        0,
                        ((window.start - DAY_START) / (DAY_END - DAY_START)) *
                          100,
                      );
                      const width = Math.min(
                        100 - left,
                        ((window.end - window.start) / (DAY_END - DAY_START)) *
                          100,
                      );
                      return (
                        <button
                          key={job.job_id}
                          onClick={() => onSelect(job.job_id)}
                          title={`${job.job_number} · ${job.scheduled_time_window}`}
                          style={{
                            position: "absolute",
                            left: `${left}%`,
                            width: `${Math.max(width, 8)}%`,
                            top: 10,
                            minHeight: 58,
                            overflow: "hidden",
                            padding: "8px 9px",
                            textAlign: "left",
                            cursor: "pointer",
                            borderRadius: 6,
                            border: `1px solid ${job.has_conflict ? "var(--danger-border)" : job.job_id === selectedJobId ? "var(--brand)" : "var(--info-border)"}`,
                            background: job.has_conflict
                              ? "var(--danger-bg)"
                              : job.job_id === selectedJobId
                                ? "var(--accent-muted)"
                                : ["var(--success-bg)", "var(--info-bg)", "var(--warning-bg)"][technicianIndex % 3],
                            zIndex: 2,
                          }}
                        >
                          <strong
                            style={{
                              display: "block",
                              color: job.has_conflict
                                ? "var(--danger-text)"
                                : "var(--text-primary)",
                              fontSize: 10.5,
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {compactJobNumber(job.job_number)}
                          </strong>
                          <span
                            style={{
                              color: "var(--text-tertiary)",
                              fontSize: 9.5,
                            }}
                          >
                            {job.scheduled_time_window}
                          </span>
                        </button>
                      );
                    })
                  ) : (
                    <span
                      style={{
                        display: "inline-flex",
                        margin: "29px 0 0 12px",
                        color:
                          technician.status === "active"
                            ? "var(--success-text)"
                            : "var(--text-tertiary)",
                        fontSize: 11.5,
                      }}
                    >
                      {technician.status === "active"
                        ? "Available"
                        : technician.status}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyPanel
          icon={<UserPlus size={22} />}
          title="No technicians configured"
          message="Add active technicians and working hours before dispatching jobs."
        />
      )}
    </div>
  );
}
function WeekSchedule({
  start,
  technicians,
  jobs,
  showCapacity,
  selectedJobId,
  onSelect,
}: {
  start: string;
  technicians: HsDispatchProjection["technician_schedule"];
  jobs: HsDispatchJobSummary[];
  showCapacity: boolean;
  selectedJobId: string | null;
  onSelect: (id: string) => void;
}) {
  const days = Array.from({ length: 7 }, (_, index) => shiftDate(start, index));
  const allowed = new Set(jobs.map((job) => job.job_id));
  return (
    <div className="dispatch-board-scroll" style={{ overflow: "auto", maxHeight: 660 }}>
      <div className="week-grid">
        <div className="week-cell" />
        {days.map((day) => (
          <div
            key={day}
            className="week-cell"
            style={{
              minHeight: 48,
              textAlign: "center",
              color:
                day === localToday()
                  ? "var(--text-link)"
                  : "var(--text-secondary)",
              fontWeight: 700,
              fontSize: 11.5,
            }}
          >
            {formatDate(day)}
          </div>
        ))}
        {technicians.map((technician) => (
          <React.Fragment key={technician.staff_member_id}>
            <div className="week-cell">
              <TechnicianLabel technician={technician} showCapacity={showCapacity} />
            </div>
            {days.map((day) => {
              const dayJobs = (technician.jobs_in_range || []).filter(
                (job) => allowed.has(job.job_id) && job.scheduled_date === day,
              );
              return (
                <div key={day} className="week-cell">
                  {dayJobs.map((job) => (
                    <JobChip
                      key={job.job_id}
                      job={job}
                      selected={job.job_id === selectedJobId}
                      onClick={() => onSelect(job.job_id)}
                    />
                  ))}
                  {!dayJobs.length && technician.status === "active" && (
                    <span
                      style={{ color: "var(--success-text)", fontSize: 10.5 }}
                    >
                      Available
                    </span>
                  )}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
function TechnicianLabel({
  technician,
  showCapacity = true,
}: {
  technician: HsDispatchProjection["technician_schedule"][number];
  showCapacity?: boolean;
}) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", minWidth: 0 }}>
      <DefaultAvatar
        name={technician.name}
        src={technician.profile_photo_url}
        size={30}
      />
      <div style={{ minWidth: 0 }}>
        <strong
          style={{
            display: "block",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            color: "var(--text-primary)",
            fontSize: 11.5,
          }}
        >
          {technician.name}
        </strong>
        {showCapacity ? (
          <span style={{ display: "flex", alignItems: "center", gap: 5, color: "var(--text-secondary)", fontSize: 10 }}>
            <span
              aria-hidden="true"
              style={{ width: 6, height: 6, borderRadius: "50%", background: technician.status === "active" ? "var(--success-text)" : "var(--text-tertiary)" }}
            />
            {technician.capacity_used ?? technician.jobs_in_range?.length ?? 0}/{technician.capacity_limit ?? 1}
          </span>
        ) : (
          <span style={{ color: "var(--text-tertiary)", fontSize: 10 }}>
            {technician.status}
          </span>
        )}
      </div>
    </div>
  );
}
function JobChip({
  job,
  selected,
  onClick,
}: {
  job: HsDispatchJobSummary;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "block",
        width: "100%",
        marginBottom: 5,
        padding: "6px 7px",
        textAlign: "left",
        cursor: "pointer",
        borderRadius: 7,
        border: `1px solid ${job.has_conflict ? "var(--danger-border)" : selected ? "var(--brand)" : "var(--border)"}`,
        background: job.has_conflict
          ? "var(--danger-bg)"
          : selected
            ? "var(--accent-muted)"
            : "var(--surface-sunken)",
      }}
    >
      <strong
        style={{
          display: "block",
          color: job.has_conflict
            ? "var(--danger-text)"
            : "var(--text-primary)",
          fontSize: 9.5,
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {job.job_number}
      </strong>
      <span style={{ color: "var(--text-tertiary)", fontSize: 9 }}>
        {job.scheduled_time_window || job.requested_time_window || "Time pending"}
      </span>
    </button>
  );
}

function AssignmentPanel({
  jobId,
  options,
  loading,
  error,
  actionLoading,
  showExcluded,
  onShowExcluded,
  onOpenJob,
  onSchedule,
  onAssign,
  onUnassign,
}: {
  jobId: string | null;
  options: HsAssignmentOptions | null;
  loading: boolean;
  error: string | null;
  actionLoading: boolean;
  showExcluded: boolean;
  onShowExcluded: () => void;
  onOpenJob: () => void;
  onSchedule: () => void;
  onAssign: (technician: HsAssignmentOptionTechnician) => void;
  onUnassign: () => void;
}) {
  if (!jobId)
    return (
      <Card>
        <EmptyPanel
          icon={<UserCheck size={24} />}
          title="Select a job"
          message="Choose a queue item or scheduled visit to inspect eligibility and assignment ownership."
        />
      </Card>
    );
  return (
    <Card padding="none">
      <div
        style={{
          padding: "14px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          gap: 10,
        }}
      >
        <div>
          <h2 style={sectionTitle}>Assignment decision</h2>
          <p style={sectionSub}>
            Only backend-qualified technicians are actionable
          </p>
        </div>
      </div>
      <div style={{ padding: 15, display: "grid", gap: 14 }}>
        {loading && <Skeleton height={360} />}
        {error && <Alert tone="danger">{error}</Alert>}
        {options && (
          <>
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 8,
                  alignItems: "center",
                }}
              >
                <strong style={{ color: "var(--text-link)", fontSize: 12 }}>
                  {options.job_context.job_number}
                </strong>
                <StatusBadge status={options.job_context.status} />
              </div>
              <h3
                style={{
                  margin: "6px 0 2px",
                  color: "var(--text-primary)",
                  fontSize: 17,
                }}
              >
                {options.job_context.master_service_name || "Service visit"}
              </h3>
              <p style={bodyText}>
                {options.job_context.customer_alias || "Customer"} ·{" "}
                {options.job_context.locality || "Locality unavailable"}
              </p>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
              }}
            >
              <Detail
                label="Schedule"
                value={
                  options.job_context.scheduled_date
                    ? `${formatDate(options.job_context.scheduled_date)} · ${options.job_context.scheduled_time_window || "Time pending"}`
                    : "Not scheduled"
                }
              />
              <Detail
                label="Issue"
                value={options.job_context.issue_summary || "Not supplied"}
              />
              {options.job_context.customer_health && <Detail
                label="Customer health"
                value={`${Math.round(options.job_context.customer_health.score)}/100 · ${options.job_context.customer_health.band.replace(/_/g, " ")}`}
              />}
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Button size="sm" variant="secondary" onClick={onOpenJob}>
                Booking details <ChevronRight size={12} />
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={onSchedule}
                disabled={!options.current_assignment}
              >
                <Clock3 size={12} />{" "}
                {options.job_context.scheduled_date ? "Reschedule" : "Schedule"}
              </Button>
            </div>
            {options.current_assignment && (
              <div
                style={{
                  padding: 11,
                  borderRadius: 9,
                  border: "1px solid var(--info-border)",
                  background: "var(--info-bg)",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 10,
                  alignItems: "center",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 9, minWidth: 0 }}>
                  <DefaultAvatar
                    name={options.current_assignment.staff_name || "Assigned technician"}
                    src={options.current_assignment.profile_photo_url}
                    size={34}
                  />
                  <div style={{ minWidth: 0 }}>
                    <span
                      style={{ color: "var(--text-tertiary)", fontSize: 10.5 }}
                    >
                      Current owner
                    </span>
                    <strong
                      style={{
                        display: "block",
                        color: "var(--text-primary)",
                        fontSize: 13,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {options.current_assignment.staff_name ||
                        "Assigned technician"}
                    </strong>
                  </div>
                </div>
                {options.available_actions.includes("unassign") && (
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={onUnassign}
                    disabled={actionLoading}
                  >
                    Unassign
                  </Button>
                )}
              </div>
            )}
            <div>
              <h4 style={{ ...sectionTitle, fontSize: 12.5, marginBottom: 8 }}>
                Eligible technicians ({options.eligible_technicians.length})
              </h4>
              <div style={{ display: "grid", gap: 8 }}>
                {options.eligible_technicians.map((technician) => {
                  const current =
                    options.current_assignment?.assigned_staff_member_id ===
                    technician.staff_member_id;
                  return (
                    <div
                      key={technician.staff_member_id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 10,
                        alignItems: "center",
                        padding: 10,
                        borderRadius: 9,
                        border: "1px solid var(--success-border)",
                        background: "var(--success-bg)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 9, minWidth: 0 }}>
                        <DefaultAvatar
                          name={technician.name}
                          src={technician.profile_photo_url}
                          size={34}
                        />
                        <div style={{ minWidth: 0 }}>
                          <strong
                            style={{
                              display: "block",
                              color: "var(--text-primary)",
                              fontSize: 12.5,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {technician.name}
                          </strong>
                          <span
                            style={{
                              color: "var(--success-text)",
                              fontSize: 10.5,
                            }}
                          >
                            {current
                              ? "Current assignment"
                              : technician.warnings?.length
                                ? `Available · ${technician.warnings.map((warning) => EXCLUSION_LABELS[warning.toUpperCase()] || warning.replace(/_/g, " ")).join(" · ")}`
                                : "Skill and availability verified"}
                          </span>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant={current ? "secondary" : "primary"}
                        disabled={current || actionLoading}
                        onClick={() => onAssign(technician)}
                      >
                        {current
                          ? "Current"
                          : options.current_assignment
                            ? "Reassign"
                            : "Assign"}
                      </Button>
                    </div>
                  );
                })}
                {!options.eligible_technicians.length && (
                  <Alert tone="warning">
                    No technician is available for this visit. Open Show
                    excluded to see the exact reason.
                  </Alert>
                )}
              </div>
            </div>
            <div>
              <Button variant="ghost" size="sm" onClick={onShowExcluded}>
                <AlertTriangle size={13} /> {showExcluded ? "Hide" : "Show"}{" "}
                excluded ({options.excluded_technicians.length})
              </Button>
              {showExcluded && (
                <div style={{ display: "grid", gap: 7, marginTop: 8 }}>
                  {options.excluded_technicians.map((technician) => (
                    <div
                      key={technician.staff_member_id}
                      style={{
                        padding: 9,
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        display: "flex",
                        alignItems: "center",
                        gap: 9,
                      }}
                    >
                      <DefaultAvatar
                        name={technician.name}
                        src={technician.profile_photo_url}
                        size={30}
                      />
                      <div>
                      <strong
                        style={{ color: "var(--text-primary)", fontSize: 11.5 }}
                      >
                        {technician.name}
                      </strong>
                      <p
                        style={{
                          margin: "3px 0 0",
                          color: "var(--danger-text)",
                          fontSize: 10.5,
                        }}
                      >
                        {(technician.exclusion_reason_codes || [])
                          .map(
                            (code) =>
                              EXCLUSION_LABELS[code] || code.replace(/_/g, " "),
                          )
                          .join(" · ") || "Not eligible"}
                      </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span style={{ color: "var(--text-tertiary)", fontSize: 10.5 }}>
        {label}
      </span>
      <p
        style={{
          margin: "3px 0 0",
          color: "var(--text-primary)",
          fontSize: 11.5,
          lineHeight: 1.4,
        }}
      >
        {value}
      </p>
    </div>
  );
}
function EmptyPanel({
  icon,
  title,
  message,
}: {
  icon: React.ReactNode;
  title: string;
  message: string;
}) {
  return (
    <div
      style={{
        minHeight: 150,
        padding: 24,
        display: "grid",
        placeItems: "center",
        textAlign: "center",
      }}
    >
      <div>
        <span style={{ color: "var(--text-tertiary)" }}>{icon}</span>
        <h3
          style={{
            margin: "8px 0 4px",
            color: "var(--text-primary)",
            fontSize: 13.5,
          }}
        >
          {title}
        </h3>
        <p style={{ ...bodyText, maxWidth: 260 }}>{message}</p>
      </div>
    </div>
  );
}
