"use client";
import { PageShell, StatusBadge } from "@serviceos/design-system";
import { TenantDetailPage } from "../../../../components/ux03/patterns/TenantDetailPage";
import { PipelineBadge } from "../../../../components/ux03/widgets/PipelineBadge";
import { FIXTURE_SERVICE_JOBS, FIXTURE_PARTS_REQUESTS, FIXTURE_PACKAGE_CREDIT } from "../../../../lib/ux03/fixtures";

export default function JobDetail() {
  const job = FIXTURE_SERVICE_JOBS[0];
  const parts = FIXTURE_PARTS_REQUESTS.filter((p) => p.serviceJobId === job.id);
  return (
    <PageShell>
      <TenantDetailPage
        title={`Job — ${job.customerName}`}
        description={job.serviceName}
        headerBadges={<PipelineBadge pipeline={job.pipeline} canonicalId={job.canonicalId} />}
        sections={[
          { id: "overview", label: "Overview", render: () => <p>Status: <StatusBadge status={job.status} /> · Scheduled {new Date(job.scheduledAt).toLocaleString()}</p> },
          { id: "customer", label: "Customer & Address", render: () => <p>{job.customerName} — {job.address}</p> },
          { id: "assignment", label: "Assignment", render: () => <p>Assigned technician: {job.assignedTechnicianId ?? "Unassigned"}</p> },
          { id: "quote", label: "Quote", render: () => <p>Quote: {job.quoteId ?? "None yet"}</p> },
          { id: "parts", label: "Parts", render: () => (
            <div>
              {parts.length === 0 && <p>No parts requested.</p>}
              {parts.map((p) => (
                <div key={p.id}>
                  <p><StatusBadge status={p.status} /> — requested by {p.requestedByTechnicianId}</p>
                  <ul>{p.items.map((it) => <li key={it.id}>{it.name} x{it.qty} (₹{it.unitCost})</li>)}</ul>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    Approve/reject/install authority belongs to provider-side staff only — technicians request/view only.
                  </p>
                </div>
              ))}
            </div>
          ) },
          { id: "finance", label: "Commission & Credit", render: () => <p>Commission rate: {(job.commissionBps / 100).toFixed(1)}% of package credit ({FIXTURE_PACKAGE_CREDIT.planName} plan) — separate from any on-site customer payment.</p> },
          { id: "activity", label: "Activity", render: () => <p>Job created, quote drafted, technician assigned.</p> },
        ]}
      />
    </PageShell>
  );
}
