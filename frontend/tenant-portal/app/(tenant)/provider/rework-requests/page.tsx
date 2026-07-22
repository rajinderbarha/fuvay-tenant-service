"use client";
import { useCallback, useState } from "react";
import { useApi, useAction } from "../../../../hooks/useApi";
import { providerComplaintApi, ReworkRecord } from "../../../../lib/api";
import { PageHeader, Card, Select, Button, Spinner } from "@serviceos/design-system";

type BV = "default" | "success" | "warning" | "danger" | "info" | "muted";

const STATUS_VARIANT: Record<string, BV> = {
  requested:   "warning",
  approved:    "success",
  assigned:    "info",
  scheduled:   "info",
  in_progress: "warning",
  completed:   "success",
  rejected:    "danger",
  cancelled:   "muted",
};

const STATUS_STYLE: Record<BV, React.CSSProperties> = {
  default: { background: "var(--bg-muted)",   color: "var(--text-secondary)" },
  success: { background: "var(--success-bg)", color: "var(--success-text)" },
  warning: { background: "var(--warning-bg)", color: "var(--warning-text)" },
  danger:  { background: "var(--danger-bg)",  color: "var(--danger-text)" },
  info:    { background: "var(--info-bg)",    color: "var(--info-text)" },
  muted:   { background: "var(--bg-muted)",   color: "var(--text-tertiary)" },
};

export default function ProviderReworkRequestsPage() {
  const [status, setStatus] = useState("");
  const { data: reworks, loading, error, refetch } = useApi(
    () => providerComplaintApi.listReworks(status || undefined),
    [status]
  );
  const startAction = useAction(
    useCallback(async (id: string) => { await providerComplaintApi.startRework(id); }, [])
  );
  const completeAction = useAction(
    useCallback(async (id: string) => { await providerComplaintApi.completeRework(id); }, [])
  );

  return (
    <>
      <PageHeader
        title="Rework Requests"
        actions={
          <Select value={status} onChange={e => setStatus(e.target.value)}
            placeholder="All"
            options={[
              { value: "approved",    label: "Approved" },
              { value: "assigned",    label: "Assigned" },
              { value: "scheduled",   label: "Scheduled" },
              { value: "in_progress", label: "In Progress" },
              { value: "completed",   label: "Completed" },
            ]}
            style={{ minWidth: 180 }}
          />
        }
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 16, maxWidth: 800 }}>
        {loading && <Spinner />}
        {error   && <p style={{ fontSize: 13, color: "var(--danger-text)" }}>{error}</p>}
        {reworks && reworks.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No rework requests.</p>}

        {reworks && reworks.map((rw: ReworkRecord) => (
          <Card key={rw.id}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                  Rework #{rw.id.slice(0, 8)}
                </p>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                  textTransform: "capitalize", ...(STATUS_STYLE[STATUS_VARIANT[rw.status] ?? "muted"]) }}>
                  {rw.status.replace(/_/g, " ")}
                </span>
              </div>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>{rw.rework_reason}</p>
              {rw.scheduled_date && (
                <p style={{ fontSize: 11, color: "var(--accent)", margin: 0 }}>Scheduled: {rw.scheduled_date}</p>
              )}
              {rw.customer_visible_notes && (
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{rw.customer_visible_notes}</p>
              )}
              <div style={{ display: "flex", gap: 8, paddingTop: 4 }}>
                {(rw.status === "assigned" || rw.status === "scheduled") && (
                  <Button variant="secondary" size="sm" loading={startAction.loading}
                    onClick={() => startAction.execute(rw.id).then(() => refetch())}>
                    Mark In Progress
                  </Button>
                )}
                {rw.status === "in_progress" && (
                  <Button variant="primary" size="sm" loading={completeAction.loading}
                    onClick={() => completeAction.execute(rw.id).then(() => refetch())}>
                    Mark Completed
                  </Button>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
