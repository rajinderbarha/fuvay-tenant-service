"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { PipelineAwareBookingDetail } from "../../../../components/ux04/PipelineAwareBookingDetail";
import { bookingListFixture, jobListFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — Booking Detail, both pipelines side by side.
 * Pipeline identity always visible via PipelineBadge; no field is
 * converted from one fixture shape to the other. */
export default function BookingDetail() {
  const booking = bookingListFixture[0];
  const serviceBooking = jobListFixture[0];
  return (
    <PageShell>
      <PageHeader title="Booking Detail" description="Booking pipeline (left) vs ServiceBooking pipeline (right) — never merged." />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <PipelineAwareBookingDetail booking={booking.booking} sla={booking.sla} />
        <PipelineAwareBookingDetail booking={serviceBooking.job} sla={serviceBooking.sla} />
      </div>
    </PageShell>
  );
}
