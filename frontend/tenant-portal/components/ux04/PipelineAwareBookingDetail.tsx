"use client";
/**
 * DESIGN PHASE UX-04A — pipeline-aware Booking Detail. Renders the SAME
 * section shell for both pipelines but NEVER converts fields across them:
 * the Booking pipeline (`booking_field_ops`) shows only `BookingFixture`
 * fields; the ServiceBooking pipeline (`service_booking_service_job`) shows
 * only the pre-job-workspace subset of `ServiceJobFixture` fields (no
 * quote/checklist/parts/invoice section here — those live in the Job
 * Detail Workspace once transitioned). See
 * docs/design/ux-04a-tenant-operations-completion/booking-detail-pipeline-evidence.md
 * for why UX-03's fixture layer has no separate "ServiceBooking" type.
 */
import React from "react";
import type { BookingFixture, ServiceJobFixture } from "../../lib/ux03/types";
import { PipelineBadge } from "../ux03/widgets/PipelineBadge";
import { SLAIndicator } from "./SLAIndicator";
import type { SLAStateView } from "../../lib/ux04/types";

export function PipelineAwareBookingDetail({
  booking,
  sla,
}: {
  booking: BookingFixture | ServiceJobFixture;
  sla: SLAStateView;
}) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <PipelineBadge pipeline={booking.pipeline} canonicalId={booking.canonicalId} />
        <SLAIndicator sla={sla} />
      </div>
      <p style={{ fontWeight: 600, margin: "0.5rem 0 0" }}>{booking.customerName} — {booking.serviceName}</p>
      <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{booking.address}</p>
      <p style={{ fontSize: "0.8125rem" }}>Scheduled {new Date(booking.scheduledAt).toLocaleString()} · status {booking.status}</p>
      <p style={{ fontSize: "0.75rem", color: "var(--warning-text)" }}>
        Cancel/reschedule: {booking.cancelSupported.replace(/_/g, " ")} — no working action rendered.
      </p>
      {booking.pipeline === "booking_field_ops" ? (
        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Assigned staff: {booking.assignedStaffId ?? "Unassigned"}</p>
      ) : (
        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
          Assigned technician: {booking.assignedTechnicianId ?? "Unassigned"} — job-specific sections
          (quote/checklist/parts/invoice/credit) intentionally omitted from this Booking Detail view; see the
          Job Detail Workspace once the job exists.
        </p>
      )}
    </div>
  );
}
