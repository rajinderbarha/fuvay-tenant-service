"use client";
/**
 * Canonical Home Services "Bookings & Jobs" workspace.
 *
 * TENANT-OPS-01 Phase 2 — extends the real backend projection GET
 * /v1/tenant/home-services/bookings-jobs (app/engines/final_records/
 * tenant_bookings_jobs_router.py). Backend computes stage, available
 * actions, SLA, complaint indicator and catalog names — this page only
 * renders what the API returned, never infers status from client state.
 *
 * Scope proven this pass: KPI strip (backend-authoritative, not a client
 * undercount), filter toolbar (search/date/service/assignment/SLA), stage
 * tabs, dense table, right-side preview panel with lifecycle + next-action +
 * quote/visit-fee + direct-payment context, and two real mutations (confirm
 * payment, navigate to Dispatch Board / full job). NOT built this pass:
 * Board view + drag-drop, export, inline execution-transition mutations
 * (start inspection / create estimate / mark work done etc. — those route
 * to the real "Open full job" page instead of being faked here), "More
 * filters" (type/brand/technician/pincode/complaint state).
 */
import React, { Suspense, useCallback, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  RefreshCw, Download, Truck, Search, X, MoreVertical, ExternalLink,
  Users, UserX, Activity, Clock3, ShieldAlert, CheckCircle2,
} from "lucide-react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import {
  PageShell, PageHeader, Card, StatCard, StatusBadge, Skeleton, Alert, Button,
  Modal, Input, Select,
} from "@serviceos/design-system";
import { bookingsJobsApi, type BJItem, type BJDetail } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

const STAGE_TABS: { id: string; label: string }[] = [
  { id: "",                  label: "All" },
  { id: "new",                label: "New" },
  { id: "assignment",         label: "Assignment" },
  { id: "scheduled",          label: "Scheduled" },
  { id: "on_the_way",         label: "On the way" },
  { id: "inspection",         label: "Inspection" },
  { id: "estimate_approval",  label: "Estimate approval" },
  { id: "in_progress",        label: "In progress" },
  { id: "payment",            label: "Payment" },
  { id: "completed",          label: "Completed" },
];

const LIFECYCLE_STAGES = [
  "new", "assignment", "scheduled", "on_the_way", "inspection",
  "estimate_approval", "in_progress", "payment", "completed",
];

function todayISO(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

function dateRangeFor(preset: string): { date_from?: string; date_to?: string } {
  if (preset === "today") return { date_from: todayISO(0), date_to: todayISO(0) };
  if (preset === "tomorrow") return { date_from: todayISO(1), date_to: todayISO(1) };
  if (preset === "week") return { date_from: todayISO(0), date_to: todayISO(6) };
  return {};
}

// Honest, stage-derived label -- the list projection doesn't join the
// invoice per row (would be N+1); the preview panel shows the REAL
// invoice.payment_status once a row is selected. This column is a coarse
// signal only, documented as such rather than fabricating precision.
function directPaymentLabel(stage: string): string {
  if (stage === "payment") return "Awaiting provider confirmation";
  if (stage === "completed") return "Confirmed";
  if (stage === "in_progress") return "Not required yet";
  return "Not required yet";
}

export default function BookingsJobsPage() {
  return (
    <Suspense fallback={null}>
      <BookingsJobsPageContent />
    </Suspense>
  );
}

function BookingsJobsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const stage = searchParams.get("stage") ?? "";
  const datePreset = searchParams.get("date") ?? "";
  const offeringId = searchParams.get("service") ?? "";
  const assignment = searchParams.get("assignment") ?? "";
  const sla = searchParams.get("sla") ?? "";
  const selectedJobId = searchParams.get("job_id");
  const [search, setSearch] = useState(searchParams.get("search") ?? "");

  const setParam = useCallback((key: string, value: string) => {
    const qs = new URLSearchParams(searchParams.toString());
    if (value) qs.set(key, value); else qs.delete(key);
    router.push(`/home-services/bookings-jobs?${qs}`);
  }, [router, searchParams]);

  const selectJob = useCallback((jobId: string | null) => {
    const qs = new URLSearchParams(searchParams.toString());
    if (jobId) qs.set("job_id", jobId); else qs.delete("job_id");
    router.push(`/home-services/bookings-jobs?${qs}`);
  }, [router, searchParams]);

  const { date_from, date_to } = dateRangeFor(datePreset);

  // Real bug fixed here: `useApi(fetcher, deps)` needs deps passed to the
  // OUTER call too (it memoizes its own `run` callback on that array) --
  // both calls here only ever passed the inner useCallback's deps to that
  // inner useCallback, leaving useApi's own `deps` at its default `[]`.
  // That froze `run`'s closure at mount forever: changing any filter/stage
  // tab updated the URL and highlighted the tab, but the table underneath
  // never actually refetched, and the job detail drawer never loaded past
  // its initial `Promise.resolve(null)` for any job ever clicked.
  const listDeps = [search, stage, assignment, sla, offeringId, date_from, date_to];
  const list = useApi(useCallback(() => bookingsJobsApi.list({
    search: search || undefined, stage: stage || undefined,
    assignment_status: assignment || undefined, sla: sla || undefined,
    offering_id: offeringId || undefined, date_from, date_to, limit: 50,
  }), listDeps), listDeps);

  const detail = useApi(useCallback(
    () => selectedJobId ? bookingsJobsApi.detail(selectedJobId) : Promise.resolve(null),
    [selectedJobId],
  ), [selectedJobId]);

  const items = list.data?.items ?? [];
  const summary = list.data?.summary;

  return (
    <TenantLayout activeNav="jobs">
      <PageShell>
        <PageHeader
          title="Bookings & jobs"
          description="Track every customer request from booking to completion."
          actions={
            <>
              <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={14} />} onClick={list.refetch}>
                Refresh
              </Button>
              <Button variant="secondary" size="sm" leftIcon={<Download size={14} />}>Export</Button>
              <Button variant="primary" size="sm" leftIcon={<Truck size={14} />}
                onClick={() => router.push("/home-services/dispatch")}>
                Dispatch board
              </Button>
            </>
          }
        />

        {list.error && <Alert tone="danger">{list.error}</Alert>}

        {list.loading || !summary ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={80} />)}
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
            <StatCard icon={Activity} label="Total active" value={summary.total_active} tone="brand" />
            <StatCard icon={UserX} label="Unassigned" value={summary.unassigned} tone="warning" />
            <StatCard icon={Clock3} label="In progress" value={summary.in_progress} tone="info" />
            <StatCard icon={Users} label="Awaiting approval" value={summary.awaiting_approval} tone="warning" />
            <StatCard icon={ShieldAlert} label="At risk" value={summary.at_risk} tone="danger" />
            <StatCard icon={CheckCircle2} label="Completed today" value={summary.completed_today} tone="success" />
          </div>
        )}

        <Card padding="sm">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: "6px 4px" }}>
            <div style={{ position: "relative", flex: "1 1 220px" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: 10, color: "var(--text-tertiary)" }} />
              <input
                value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search job #, booking #, customer, technician..."
                style={{ width: "100%", padding: "8px 10px 8px 30px", borderRadius: 8, fontSize: 13,
                  border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }}
              />
            </div>
            <select value={datePreset} onChange={e => setParam("date", e.target.value)}
              style={selectStyle}>
              <option value="">All dates</option>
              <option value="today">Today</option>
              <option value="tomorrow">Tomorrow</option>
              <option value="week">This week</option>
            </select>
            <select value={offeringId} onChange={e => setParam("service", e.target.value)} style={selectStyle}>
              <option value="">All services</option>
              {(list.data?.available_filters?.services ?? []).map(s => (
                <option key={s.offering_id} value={s.offering_id}>{s.name}</option>
              ))}
            </select>
            <select value={assignment} onChange={e => setParam("assignment", e.target.value)} style={selectStyle}>
              <option value="">All assignment</option>
              <option value="assigned">Assigned</option>
              <option value="unassigned">Unassigned</option>
            </select>
            <select value={sla} onChange={e => setParam("sla", e.target.value)} style={selectStyle}>
              <option value="">All SLA</option>
              <option value="ON_TRACK">On track</option>
              <option value="AT_RISK">At risk</option>
              <option value="BREACHED">Breached</option>
            </select>
          </div>

          <div style={{ display: "flex", gap: 2, padding: "4px", background: "var(--surface-sunken)",
            borderRadius: 10, border: "1px solid var(--border)", margin: "8px 4px", overflowX: "auto" }}>
            {STAGE_TABS.map(t => (
              <button key={t.id} onClick={() => setParam("stage", t.id)} style={{
                padding: "6px 12px", borderRadius: 8, border: "none", whiteSpace: "nowrap",
                background: stage === t.id ? "var(--surface)" : "transparent",
                color: stage === t.id ? "var(--text-primary)" : "var(--text-secondary)",
                fontWeight: stage === t.id ? 600 : 400, fontSize: 12, cursor: "pointer", fontFamily: "inherit",
              }}>{t.label}</button>
            ))}
          </div>

          {list.loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 8 }}>
              {[...Array(4)].map((_, i) => <Skeleton key={i} height={48} />)}
            </div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
              No bookings or jobs match this view.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
                <thead>
                  <tr style={{ textAlign: "left" }}>
                    {["Job", "Customer", "Service", "Schedule", "Technician", "Stage", "SLA", "Direct payment", ""].map(h => (
                      <th key={h} style={{ padding: "8px 10px", fontWeight: 600, color: "var(--text-tertiary)",
                        borderBottom: "1px solid var(--border)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map(row => (
                    <JobRow key={row.service_job_id} row={row} selected={row.service_job_id === selectedJobId}
                      onClick={() => selectJob(row.service_job_id)} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </PageShell>

      {selectedJobId && (
        <JobPreviewPanel jobId={selectedJobId} detail={detail.data} loading={detail.loading}
          error={detail.error} onClose={() => selectJob(null)} onChanged={() => { detail.refetch(); list.refetch(); }} />
      )}
    </TenantLayout>
  );
}

const selectStyle: React.CSSProperties = {
  padding: "8px 8px", borderRadius: 8, fontSize: 12, border: "1px solid var(--border)",
  background: "var(--surface-sunken)", color: "var(--text-primary)",
};

function JobRow({ row, selected, onClick }: { row: BJItem; selected: boolean; onClick: () => void }) {
  const slaStatus = row.sla?.sla_status ?? "NOT_APPLICABLE";
  return (
    <tr onClick={onClick} style={{
      cursor: "pointer", background: selected ? "var(--accent-muted)" : "transparent",
      borderLeft: selected ? "3px solid var(--brand)" : "3px solid transparent",
      borderBottom: "1px solid var(--border)",
    }}>
      <td style={{ padding: "10px" }}>
        <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.job_number}</div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{row.booking_number}</div>
      </td>
      <td style={{ padding: "10px" }}>
        <div>{row.customer_alias ?? "—"}</div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{row.locality ?? "—"}</div>
      </td>
      <td style={{ padding: "10px" }}>
        <div>{row.service_name ?? "—"}</div>
        {row.job_type_label && <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{row.job_type_label}</div>}
      </td>
      <td style={{ padding: "10px" }}>
        {row.scheduled_date ? `${row.scheduled_date} · ${row.scheduled_time_window ?? ""}` : "Not scheduled"}
      </td>
      <td style={{ padding: "10px" }}>
        {row.assigned_staff_id ? "Assigned" : <span style={{ color: "var(--warning-text)" }}>Unassigned</span>}
        {row.open_complaint_count > 0 && (
          <div style={{ fontSize: 10, color: "var(--danger-text)" }}>{row.open_complaint_count} complaint(s)</div>
        )}
      </td>
      <td style={{ padding: "10px" }}><StatusBadge status={row.stage} size="sm" /></td>
      <td style={{ padding: "10px" }}>
        {slaStatus === "NOT_APPLICABLE" ? "—" : (
          <span style={{
            fontSize: 11, fontWeight: 700,
            color: slaStatus === "BREACHED" ? "var(--danger-text)" : slaStatus === "AT_RISK" ? "var(--warning-text)" : "var(--success-text)",
          }}>
            {slaStatus === "BREACHED" ? `${row.sla?.minutes_overdue}m overdue`
              : slaStatus === "AT_RISK" ? `${row.sla?.minutes_remaining}m left` : "On track"}
          </span>
        )}
      </td>
      <td style={{ padding: "10px", fontSize: 11.5 }}>{directPaymentLabel(row.stage)}</td>
      <td style={{ padding: "10px" }}>
        <button onClick={e => { e.stopPropagation(); onClick(); }} aria-label="Open"
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
          <MoreVertical size={14} />
        </button>
      </td>
    </tr>
  );
}

function JobPreviewPanel({ jobId, detail, loading, error, onClose, onChanged }: {
  jobId: string; detail: BJDetail | null; loading: boolean; error: string | null;
  onClose: () => void; onChanged: () => void;
}) {
  const router = useRouter();
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <div style={{
      position: "fixed", top: 0, right: 0, width: 380, height: "100vh",
      background: "var(--surface)", borderLeft: "1px solid var(--border)",
      zIndex: 900, overflowY: "auto", padding: 20, boxShadow: "-8px 0 24px rgba(0,0,0,0.2)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", fontWeight: 700 }}>
            {detail ? String(detail.job.job_number) : "Job"}
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
            {detail?.service_name ?? "Loading…"}
          </div>
        </div>
        <button onClick={onClose} aria-label="Close" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
          <X size={18} />
        </button>
      </div>

      {loading || !detail ? (
        error ? <Alert tone="danger">{error}</Alert> : <Skeleton height={300} />
      ) : (
        <>
          <div style={{ marginBottom: 12 }}>
            <StatusBadge status={detail.stage.stage} />
          </div>

          <Card padding="sm" style={{ marginBottom: 12 }}>
            <Field label="Customer" value={String(detail.booking.customer_alias ?? "—")} />
            <Field label="Locality" value={String(detail.booking.locality ?? "—")} />
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>
              Message through ServiceOS — raw contact is never shown here.
            </div>
          </Card>

          <Card padding="sm" style={{ marginBottom: 12 }}>
            <Field label="Job type" value={detail.job_type_label ?? "—"} />
            <Field label="Schedule" value={
              detail.job.scheduled_date ? `${detail.job.scheduled_date} · ${detail.job.scheduled_time_window ?? ""}` : "Not scheduled"
            } />
            <Field label="Visit fee" value={detail.visit_fee ? `₹${detail.visit_fee}` : "—"} />
            <Field label="Estimate" value={
              detail.quote ? `₹${detail.quote.customer_payable_amount} (${detail.quote.status})` : "No estimate yet"
            } />
          </Card>

          <Card padding="sm" style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", marginBottom: 8 }}>LIFECYCLE</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {LIFECYCLE_STAGES.map(s => {
                const idx = LIFECYCLE_STAGES.indexOf(detail.stage.stage);
                const thisIdx = LIFECYCLE_STAGES.indexOf(s);
                const done = thisIdx < idx;
                const current = s === detail.stage.stage;
                return (
                  <span key={s} style={{
                    fontSize: 10, padding: "3px 7px", borderRadius: 999,
                    background: current ? "var(--brand)" : done ? "var(--success-bg)" : "var(--surface-sunken)",
                    color: current ? "#151617" : done ? "var(--success-text)" : "var(--text-tertiary)",
                    fontWeight: current ? 700 : 400,
                  }}>{s.replace(/_/g, " ")}</span>
                );
              })}
            </div>
          </Card>

          <Card padding="sm" style={{ marginBottom: 12, background: "var(--accent-muted)" }}>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Next required action</div>
            <div style={{ fontWeight: 700, marginBottom: 10 }}>
              {detail.stage.next_action ? detail.stage.next_action.label : "None — terminal"}
            </div>
            {detail.stage.next_action?.action_key === "assign_technician" && (
              <Button variant="primary" size="sm" onClick={() => router.push("/home-services/dispatch")}>
                Assign in Dispatch Board
              </Button>
            )}
            {detail.stage.next_action?.action_key === "confirm_payment" && (
              <Button variant="primary" size="sm" onClick={() => setConfirmOpen(true)}>
                Confirm direct payment
              </Button>
            )}
            {detail.stage.next_action && !["assign_technician", "confirm_payment"].includes(detail.stage.next_action.action_key) && (
              <Button variant="primary" size="sm" rightIcon={<ExternalLink size={12} />}
                onClick={() => router.push(`/service-jobs/${detail.job.id}`)}>
                Continue in full job
              </Button>
            )}
          </Card>

          {detail.open_complaint_count > 0 && (
            <Alert tone="danger">{detail.open_complaint_count} open complaint(s) on this job.</Alert>
          )}

          <div style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "10px 0", lineHeight: 1.5 }}>
            {detail.direct_payment_notice}
          </div>

          <Button variant="secondary" size="sm" style={{ width: "100%" }}
            onClick={() => router.push(`/service-jobs/${detail.job.id}`)}>
            Open full job
          </Button>

          {confirmOpen && (
            <ConfirmPaymentModal jobId={jobId} invoiceAmount={detail.invoice?.customer_payable_amount as number | undefined}
              onClose={() => setConfirmOpen(false)}
              onSaved={() => { setConfirmOpen(false); onChanged(); }} />
          )}
        </>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontSize: 12.5 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", textAlign: "right" }}>{value}</span>
    </div>
  );
}

function ConfirmPaymentModal({ jobId, invoiceAmount, onClose, onSaved }: {
  jobId: string; invoiceAmount?: number; onClose: () => void; onSaved: () => void;
}) {
  const [paymentMode, setPaymentMode] = useState("onsite_cash");
  const [amount, setAmount] = useState(invoiceAmount ? String(invoiceAmount) : "");

  const { execute: save, loading, error } = useAction(
    (body: { payment_mode: string; collected_amount: number }) => bookingsJobsApi.confirmPayment(jobId, body),
    { onSuccess: onSaved },
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const parsed = Number(amount);
    if (!parsed || parsed <= 0) return;
    await save({ payment_mode: paymentMode, collected_amount: parsed });
  }

  return (
    <Modal open onClose={onClose} title="Confirm direct payment">
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
          Customer pays the provider directly. This records your confirmation only — ServiceOS never collects or settles this payment.
        </div>
        {error && <Alert tone="danger">{error}</Alert>}
        <Select label="Payment mode" value={paymentMode} onChange={e => setPaymentMode(e.target.value)} options={[
          { value: "onsite_cash", label: "Cash" },
          { value: "onsite_upi", label: "UPI" },
          { value: "onsite_card", label: "Card at service location" },
          { value: "bank_transfer", label: "Bank transfer" },
        ]} />
        <Input label="Amount collected" type="number" min={0} value={amount} onChange={e => setAmount(e.target.value)} required />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button type="submit" variant="primary" loading={loading}>Confirm payment</Button>
        </div>
      </form>
    </Modal>
  );
}
