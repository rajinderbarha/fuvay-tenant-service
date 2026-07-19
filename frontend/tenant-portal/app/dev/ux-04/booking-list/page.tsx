"use client";
import { PageShell, PageHeader, StatusBadge } from "@serviceos/design-system";
import { PipelineBadge } from "../../../../components/ux03/widgets/PipelineBadge";
import { SLAIndicator } from "../../../../components/ux04/SLAIndicator";
import { bookingListFixture, jobListFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04 — pipeline-aware combined list showcase (Booking rows
 * and ServiceJob rows both render, each keeping its own PipelineBadge and
 * status vocabulary — never merged into one generic row shape). */
export default function BookingList() {
  return (
    <PageShell>
      <PageHeader title="Bookings & Jobs" description="Today / Unassigned / Upcoming / Needs quote / SLA risk / Completed presets (fixture-backed)." />
      <table style={{ width: "100%", marginTop: "1rem", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
            <th>Pipeline</th><th>Customer</th><th>Service</th><th>Status</th><th>SLA</th><th>Next action</th>
          </tr>
        </thead>
        <tbody>
          {bookingListFixture.map((b) => (
            <tr key={b.booking.id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td><PipelineBadge pipeline={b.booking.pipeline} canonicalId={b.booking.canonicalId} /></td>
              <td>{b.booking.customerName}</td>
              <td>{b.booking.serviceName}</td>
              <td><StatusBadge status={b.booking.status} /></td>
              <td><SLAIndicator sla={b.sla} /></td>
              <td>{b.nextAction ?? "—"}</td>
            </tr>
          ))}
          {jobListFixture.map((j) => (
            <tr key={j.job.id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td><PipelineBadge pipeline={j.job.pipeline} canonicalId={j.job.canonicalId} /></td>
              <td>{j.job.customerName}</td>
              <td>{j.job.serviceName}</td>
              <td><StatusBadge status={j.job.status} /></td>
              <td><SLAIndicator sla={j.sla} /></td>
              <td>{j.nextAction ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PageShell>
  );
}
