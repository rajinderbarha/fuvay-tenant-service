"use client";
/**
 * DESIGN PHASE UX-04B — field_ops.Job detail. Distinct from the ServiceJob
 * Job Detail Workspace: deliberately has NO quote/checklist/parts/invoice/
 * credit sections, because field_ops.Job has no such concept
 * (booking-job-pipeline-separation.md). Renders only what
 * `FieldOpsJobDetailView` actually carries.
 */
import React from "react";
import { PageHeader, StatusBadge } from "@serviceos/design-system";
import { PipelineBadge } from "../ux03/widgets/PipelineBadge";
import { SLAIndicator } from "./SLAIndicator";
import type { FieldOpsJobDetailView } from "../../lib/ux04/types";

export function FieldOpsJobDetail({ view }: { view: FieldOpsJobDetailView }) {
  return (
    <div>
      <PageHeader
        title={`field_ops.Job — ${view.job.customerName}`}
        description={view.job.serviceName}
        actions={<SLAIndicator sla={view.sla} />}
      />
      <div style={{ margin: "0.5rem 0" }}>
        <PipelineBadge pipeline={view.job.pipeline} canonicalId={view.job.canonicalId} />
      </div>
      <p style={{ fontSize: "0.8125rem" }}>
        Source Booking: {view.job.id} · Status: <StatusBadge status={view.job.status} /> · Scheduled{" "}
        {new Date(view.job.scheduledAt).toLocaleString()}
      </p>
      <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{view.job.address}</p>
      <p style={{ fontSize: "0.8125rem" }}>Assigned staff: {view.job.assignedStaffId ?? "Unassigned"}</p>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Notes</h2>
        {view.notes.length === 0 ? (
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>No notes.</p>
        ) : (
          <ul style={{ fontSize: "0.8125rem" }}>
            {view.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Timeline</h2>
        <ul style={{ listStyle: "none", padding: 0, fontSize: "0.8125rem" }}>
          {view.timeline.map((e) => (
            <li key={e.id}>
              {e.at} · {e.actorName} ({e.actorRole}): {e.action}
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "0.9375rem" }}>Activity / Audit</h2>
        <ul style={{ listStyle: "none", padding: 0, fontSize: "0.8125rem" }}>
          {view.activity.map((e) => (
            <li key={e.id}>
              {e.at} · {e.actorName}: {e.action} — {e.result}
            </li>
          ))}
        </ul>
      </section>

      <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", fontStyle: "italic", marginTop: "1rem" }}>
        This page intentionally has no quote, checklist, parts, invoice, or credit/commission section —
        field_ops.Job has no such concept. See the Job Detail Workspace for the ServiceJob-pipeline equivalent.
      </p>
    </div>
  );
}
