"use client";
import { PageShell, PageHeader, StatusBadge } from "@serviceos/design-system";
import { PipelineBadge } from "../../../../components/ux03/widgets/PipelineBadge";
import { SLAIndicator } from "../../../../components/ux04/SLAIndicator";
import { JobStatusTimeline } from "../../../../components/ux04/JobStatusTimeline";
import { QuoteSummary } from "../../../../components/ux04/QuoteSummary";
import { ChecklistProgress } from "../../../../components/ux04/ChecklistProgress";
import { PartsRequestSummary } from "../../../../components/ux04/PartsRequestSummary";
import { CreditCommissionSummary } from "../../../../components/ux04/CreditCommissionSummary";
import { CustomerCommunicationTimeline } from "../../../../components/ux04/CustomerCommunicationTimeline";
import { jobDetailFixture } from "../../../../lib/ux04/fixtures";

const SERVICE_JOB_STATUSES = ["quoted", "scheduled", "in_progress", "awaiting_parts", "completed"];

/** DESIGN PHASE UX-04 — Job Detail workspace (ServiceJob variant). Sticky
 * header + model-aware sections, no info repeated across sections. */
export default function JobDetailWorkspace() {
  const v = jobDetailFixture;
  return (
    <PageShell>
      <PageHeader
        title={`Job — ${v.job.customerName}`}
        description={v.job.serviceName}
        actions={<SLAIndicator sla={v.sla} />}
      />
      <div style={{ margin: "0.5rem 0" }}>
        <PipelineBadge pipeline={v.job.pipeline} canonicalId={v.job.canonicalId} />
      </div>
      <JobStatusTimeline statuses={SERVICE_JOB_STATUSES} current={v.job.status} />

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Status transition</h2>
        <p style={{ fontSize: "0.8125rem" }}>Current: <StatusBadge status={v.statusTransition.currentStatus} /></p>
        {v.statusTransition.allowedNext.map((opt) => (
          <div key={opt.toStatus} style={{ fontSize: "0.8125rem", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "0.5rem", marginTop: "0.5rem" }}>
            <p style={{ margin: 0, fontWeight: 600 }}>→ {opt.toStatus.replace(/_/g, " ")}</p>
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>Requires: {opt.requiredFieldsOrEvidence.join(", ")}</p>
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>Customer sees: {opt.customerVisibleEffect}</p>
          </div>
        ))}
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Quote</h2>
        {v.quote && <QuoteSummary quote={v.quote} />}
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Checklist</h2>
        {v.checklist && <ChecklistProgress checklist={v.checklist} mode="provider_review" />}
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Parts requests</h2>
        {v.partsRequests.map((pr) => <PartsRequestSummary key={pr.request.id} view={pr} />)}
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Credit &amp; commission</h2>
        <CreditCommissionSummary view={v.creditCommission} />
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Customer communication</h2>
        <CustomerCommunicationTimeline events={v.communication} />
      </section>
    </PageShell>
  );
}
