"use client";

import React from "react";
import {
  AlertTriangle, BriefcaseBusiness, CalendarDays, ChevronRight, Clock3,
  IndianRupee, MapPin, ShieldCheck, UserRound, X,
} from "lucide-react";
import { Alert, Button, Card, Skeleton, StatusBadge } from "@serviceos/design-system";
import type { BJDetail } from "../../lib/api";

interface AvailabilityJobDrawerProps {
  jobId: string;
  technicianName: string | null;
  detail: BJDetail | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onOpenDetails: () => void;
  onOpenDispatch: () => void;
}

function humanize(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  const text = String(value).replace(/_/g, " ").trim().toLowerCase();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : fallback;
}

function money(value: unknown): string {
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount)
    : "—";
}

function scheduleLabel(date: unknown, window: unknown): string {
  if (!date) return "Not scheduled";
  const formatted = new Date(`${String(date)}T00:00:00`).toLocaleDateString("en-IN", {
    weekday: "short", day: "2-digit", month: "short", year: "numeric",
  });
  return `${formatted} · ${window || "Time pending"}`;
}

function textValue(value: unknown, fallback = "—"): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ marginBottom: 3, color: "var(--text-tertiary)", fontSize: 10.5, fontWeight: 650, letterSpacing: ".04em", textTransform: "uppercase" }}>{label}</div>
      <div style={{ color: "var(--text-primary)", fontSize: 12.5, fontWeight: 600, lineHeight: 1.45, overflowWrap: "anywhere" }}>{value}</div>
    </div>
  );
}

function PanelTitle({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 12, color: "var(--text-primary)", fontSize: 12.5, fontWeight: 750 }}>
      <span style={{ color: "var(--brand)", display: "grid", placeItems: "center" }}>{icon}</span>{children}
    </div>
  );
}

export function AvailabilityJobDrawer({
  jobId, technicianName, detail, loading, error, onClose, onOpenDetails, onOpenDispatch,
}: AvailabilityJobDrawerProps) {
  const booking = (detail?.booking ?? {}) as BJDetail["booking"];
  const job = (detail?.job ?? {}) as BJDetail["job"];
  const invoice = detail?.invoice;
  const quote = detail?.quote;
  const priceSnapshot = (booking.price_snapshot ?? {}) as Record<string, unknown>;
  const completion = (job.completion_data ?? null) as Record<string, unknown> | null;
  const customerTotal = invoice?.customer_payable_amount
    ?? quote?.customer_payable_amount
    ?? priceSnapshot.customer_total
    ?? priceSnapshot.display_price
    ?? priceSnapshot.selected_price_amount;
  const serviceAmount = invoice?.total_amount ?? quote?.total_amount;
  const photoCount = Array.isArray(booking.customer_photo_urls) ? booking.customer_photo_urls.length : 0;
  const resolvedTechnician = detail?.technician?.full_name ?? technicianName ?? "Unassigned";

  return (
    <>
      <button type="button" aria-label="Close allocated job details" onClick={onClose} style={{
        position: "fixed", inset: 0, zIndex: 1190, border: 0, background: "rgba(0,0,0,.5)", backdropFilter: "blur(2px)",
      }} />
      <aside aria-label="Allocated job details" style={{
        position: "fixed", top: 0, right: 0, bottom: 0, zIndex: 1200,
        width: "min(540px, 100vw)", overflowY: "auto", background: "var(--surface)",
        borderLeft: "1px solid var(--border)", boxShadow: "-18px 0 55px rgba(0,0,0,.3)",
        animation: "slideInAvailabilityJob .2s cubic-bezier(.4,0,.2,1)",
      }}>
        <style>{`@keyframes slideInAvailabilityJob{from{transform:translateX(100%)}to{transform:translateX(0)}}`}</style>
        <header style={{ position: "sticky", top: 0, zIndex: 2, display: "flex", justifyContent: "space-between", gap: 12, padding: "18px 20px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
          <div style={{ display: "flex", gap: 11, minWidth: 0 }}>
            <span style={{ display: "grid", placeItems: "center", width: 40, height: 40, flex: "0 0 40px", borderRadius: 12, color: "var(--brand)", background: "var(--accent-muted)" }}><BriefcaseBusiness size={18} /></span>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: "var(--text-tertiary)", fontSize: 10.5, fontWeight: 700, letterSpacing: ".06em", textTransform: "uppercase" }}>{detail?.job.job_number ?? jobId}</div>
              <h2 style={{ margin: "3px 0 0", color: "var(--text-primary)", fontSize: 19, lineHeight: 1.25 }}>{detail?.service_name ?? "Allocated job"}</h2>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close job details" style={{ display: "grid", placeItems: "center", width: 34, height: 34, flex: "0 0 34px", border: "1px solid var(--border)", borderRadius: 10, background: "var(--surface)", color: "var(--text-tertiary)", cursor: "pointer" }}><X size={16} /></button>
        </header>

        <div style={{ display: "grid", gap: 13, padding: 20 }}>
          {loading || !detail ? (
            error ? <Alert tone="danger">{error}</Alert> : <><Skeleton height={74} /><Skeleton height={170} /><Skeleton height={160} /></>
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <StatusBadge status={detail.stage.stage} />
                <span style={{ color: detail.sla?.sla_status === "BREACHED" ? "var(--danger-text)" : "var(--text-tertiary)", fontSize: 11.5, fontWeight: 650 }}>
                  SLA {humanize(detail.sla?.sla_status, "Not applicable")}
                </span>
              </div>

              <Card padding="sm">
                <PanelTitle icon={<CalendarDays size={14} />}>Visit and assignment</PanelTitle>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: "13px 16px" }}>
                  <Field label="Schedule" value={scheduleLabel(job.scheduled_date, job.scheduled_time_window)} />
                  <Field label="Technician" value={resolvedTechnician} />
                  <Field label="Job type" value={detail.job_type_label ?? "Not specified"} />
                  <Field label="Assignment" value={humanize(job.assignment_status)} />
                  <Field label="Booking" value={textValue(booking.booking_number)} />
                  <Field label="Job status" value={humanize(job.status)} />
                </div>
              </Card>

              <Card padding="sm">
                <PanelTitle icon={<UserRound size={14} />}>Customer request</PanelTitle>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: "13px 16px" }}>
                  <Field label="Customer" value={textValue(booking.customer_alias, "Private customer")} />
                  <Field label="Area" value={<span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><MapPin size={12} />{textValue(booking.locality, "Location unavailable")}</span>} />
                  <Field label="Reported problem" value={detail.problem_name ?? "Not specified"} />
                  <Field label="Priority" value={booking.is_emergency ? <span style={{ color: "var(--danger-text)" }}>Emergency</span> : "Standard"} />
                </div>
                {(booking.issue_summary || booking.customer_note) && (
                  <div style={{ marginTop: 13, padding: "11px 12px", borderRadius: 10, background: "var(--surface-sunken)", color: "var(--text-secondary)", fontSize: 12.5, lineHeight: 1.55 }}>
                    {textValue(booking.issue_summary || booking.customer_note)}
                  </div>
                )}
                {photoCount > 0 && <div style={{ marginTop: 8, color: "var(--text-tertiary)", fontSize: 11.5 }}>{photoCount} customer photo{photoCount === 1 ? "" : "s"} attached</div>}
              </Card>

              <Card padding="sm">
                <PanelTitle icon={<IndianRupee size={14} />}>Price and payment</PanelTitle>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: "13px 16px" }}>
                  <Field label="Customer total" value={money(customerTotal)} />
                  <Field label="Service amount" value={money(serviceAmount)} />
                  <Field label="Visit fee" value={money(detail.visit_fee)} />
                  <Field label="Payment" value={invoice ? humanize(invoice.payment_status, "Pending") : quote ? `Estimate ${humanize(quote.status)}` : "Not due"} />
                </div>
              </Card>

              {completion && (
                <Card padding="sm">
                  <PanelTitle icon={<ShieldCheck size={14} />}>Completion and warranty</PanelTitle>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: "13px 16px" }}>
                    <Field label="Work summary" value={textValue(completion.work_summary)} />
                    <Field label="Collected" value={money(completion.collected_amount)} />
                    <Field label="Payment mode" value={humanize(completion.payment_mode)} />
                    <Field label="Warranty" value={job.warranty_days ? `${job.warranty_days} days` : "Not provided"} />
                  </div>
                </Card>
              )}

              <Card padding="sm" style={{ background: "var(--accent-muted)" }}>
                <PanelTitle icon={<Clock3 size={14} />}>Current workflow</PanelTitle>
                <Field label="Current stage" value={detail.stage.stage_label ?? humanize(detail.stage.stage)} />
                <Field label="Next action" value={detail.stage.next_action?.label ?? "Workflow complete"} />
                {detail.open_complaint_count > 0 && (
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 9, color: "var(--danger-text)", fontSize: 12, fontWeight: 650 }}>
                    <AlertTriangle size={13} />{detail.open_complaint_count} open complaint{detail.open_complaint_count === 1 ? "" : "s"}
                  </div>
                )}
              </Card>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 9 }}>
                <Button variant="secondary" size="sm" onClick={onOpenDetails} rightIcon={<ChevronRight size={14} />}>Full job details</Button>
                <Button variant="primary" size="sm" onClick={onOpenDispatch} rightIcon={<ChevronRight size={14} />}>Manage in dispatch</Button>
              </div>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
