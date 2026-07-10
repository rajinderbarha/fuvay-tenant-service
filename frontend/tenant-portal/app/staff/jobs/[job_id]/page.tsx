"use client";
import React, { useCallback } from "react";
import { useParams } from "next/navigation";
import { StaffLayout } from "../../../../components/layout/StaffLayout";
import { Card, Badge, Skeleton } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import { staffSelfApi } from "../../../../lib/api";

const DISABLED_ACTIONS = [
  "Start Job", "On The Way", "In Progress", "Complete Job",
  "Collect Payment", "Confirm Payment", "Deduct Credits",
];

export default function StaffJobDetailPage() {
  const params = useParams<{ job_id: string }>();
  const jobId = params.job_id;
  const job = useApi(useCallback(() => staffSelfApi.getJobDetail(jobId), [jobId]), [jobId]);

  return (
    <StaffLayout activeNav="jobs">
      {job.loading ? <Skeleton height={300}/> : job.error ? (
        <Card><p style={{ color: "var(--danger-text)", fontSize: 13 }}>{job.error}{job.requestId && ` — Request ID: ${job.requestId}`}</p></Card>
      ) : job.data ? (
        <>
          <div style={{ marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{job.data.job_number || `Job ${job.data.job_id.slice(0, 8)}`}</h1>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>{job.data.service_category || job.data.job_type}</p>
            </div>
            <Badge variant="info" size="sm">{job.data.status}</Badge>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 16 }}>
            <Card>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Job Details</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
                <Row label="Customer" value={job.data.customer_name}/>
                <Row label="Phone" value={job.data.customer_phone}/>
                <Row label="Address" value={job.data.customer_address}/>
                <Row label="City / Zip" value={[job.data.city, job.data.zipcode].filter(Boolean).join(" / ") || undefined}/>
                <Row label="Scheduled" value={job.data.scheduled_at ? new Date(job.data.scheduled_at).toLocaleString() : undefined}/>
                <Row label="Notes" value={job.data.notes}/>
              </div>

              {job.data.checklist && job.data.checklist.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 8px" }}>Checklist</h4>
                  {job.data.checklist.map((c, i) => (
                    <div key={i} style={{ fontSize: 13, padding: "4px 0" }}>
                      {c.completed ? "☑" : "☐"} {c.step}
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Job Actions</h3>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 12 }}>
                Job execution actions are not certified in this phase.
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {DISABLED_ACTIONS.map(a => (
                  <button key={a} disabled title="Not certified in this phase"
                    style={{
                      padding: "8px 12px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                      border: "1px solid var(--border)", background: "var(--card-bg)",
                      color: "var(--text-tertiary)", cursor: "not-allowed", textAlign: "left",
                    }}>
                    {a} <span style={{ fontStyle: "italic", fontWeight: 400 }}>— Not certified in this phase</span>
                  </button>
                ))}
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </StaffLayout>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
      <div>{value || "—"}</div>
    </div>
  );
}
