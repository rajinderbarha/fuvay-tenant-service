"use client";
import { useCallback, useState } from "react";
import { useApi, useAction } from "../../../../hooks/useApi";
import { providerComplaintApi, ReworkRecord } from "../../../../lib/api";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  requested:   { background: "var(--warning-bg)",      color: "var(--warning-text)" },
  approved:    { background: "var(--success-bg)",      color: "var(--success-text)" },
  assigned:    { background: "var(--info-bg)",         color: "var(--info-text)" },
  scheduled:   { background: "var(--info-bg)",         color: "var(--info-text)" },
  in_progress: { background: "var(--warning-bg)",      color: "var(--warning-text)" },
  completed:   { background: "var(--success-bg)",      color: "var(--success-text)" },
  rejected:    { background: "var(--danger-bg)",       color: "var(--danger-text)" },
  cancelled:   { background: "var(--surface-sunken)",  color: "var(--text-tertiary)" },
};

const selStyle: React.CSSProperties = {
  height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 8,
  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
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
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 800, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Rework Requests</h1>
        <select style={selStyle} value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">All</option>
          <option value="approved">Approved</option>
          <option value="assigned">Assigned</option>
          <option value="scheduled">Scheduled</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {loading && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p>}
      {error   && <p style={{ fontSize: 13, color: "var(--danger-text)" }}>{error}</p>}
      {reworks && reworks.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No rework requests.</p>}

      {reworks && reworks.map((rw: ReworkRecord) => (
        <div key={rw.id} style={{ border: "1px solid var(--border)", borderRadius: 12, padding: 20,
          background: "var(--surface)", display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
              Rework #{rw.id.slice(0, 8)}
            </p>
            <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
              textTransform: "capitalize", ...(STATUS_STYLE[rw.status] ?? { background: "var(--surface-sunken)", color: "var(--text-secondary)" }) }}>
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
              <button onClick={() => startAction.execute(rw.id).then(() => refetch())}
                disabled={startAction.loading}
                style={{ padding: "6px 14px", fontSize: 13, fontWeight: 600, borderRadius: 8,
                  border: "none", cursor: "pointer", fontFamily: "inherit",
                  background: "var(--warning)", color: "white", opacity: startAction.loading ? 0.5 : 1 }}>
                {startAction.loading ? "…" : "Mark In Progress"}
              </button>
            )}
            {rw.status === "in_progress" && (
              <button onClick={() => completeAction.execute(rw.id).then(() => refetch())}
                disabled={completeAction.loading}
                style={{ padding: "6px 14px", fontSize: 13, fontWeight: 600, borderRadius: 8,
                  border: "none", cursor: "pointer", fontFamily: "inherit",
                  background: "var(--success)", color: "white", opacity: completeAction.loading ? 0.5 : 1 }}>
                {completeAction.loading ? "…" : "Mark Completed"}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
