"use client";
import { useApi } from "../../../hooks/useApi";
import { useAction } from "../../../hooks/useApi";
import { adminReworkApi, ReworkRecord } from "../../../lib/api";
import { useState, useCallback } from "react";

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
  height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
};

export default function AdminReworkRequestsPage() {
  const [status, setStatus] = useState("");
  const { data: reworks, loading, error, refetch } = useApi(
    () => adminReworkApi.list(undefined, status || undefined),
    [status]
  );
  const approveAction = useAction(
    useCallback(async (id: string) => { await adminReworkApi.approve(id); refetch(); }, [refetch])
  );
  const rejectAction  = useAction(
    useCallback(async (id: string, reason: string) => { await adminReworkApi.reject(id, reason); refetch(); }, [refetch])
  );
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 900, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Rework Requests (Admin)</h1>
        <select style={selStyle} value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">All</option>
          {["requested","approved","assigned","scheduled","in_progress","completed","rejected","cancelled"].map(s => (
            <option key={s} value={s}>{s.replace(/_/g," ")}</option>
          ))}
        </select>
      </div>

      {loading && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p>}
      {error   && <p style={{ fontSize: 13, color: "var(--danger-text)" }}>{error}</p>}
      {reworks && reworks.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No rework requests found.</p>}

      {reworks && reworks.map((rw: ReworkRecord) => (
        <div key={rw.id} style={{ border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20,
          background: "var(--surface)", display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>
                Rework #{rw.id.slice(0, 8)}
              </p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                Complaint: {rw.complaint_id.slice(0, 8)}
              </p>
            </div>
            <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600, textTransform: "capitalize",
              ...(STATUS_STYLE[rw.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
              {rw.status.replace(/_/g," ")}
            </span>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>{rw.rework_reason}</p>
          {rw.scheduled_date && (
            <p style={{ fontSize: 11, color: "var(--accent)", margin: 0 }}>Scheduled: {rw.scheduled_date}</p>
          )}
          {rw.status === "requested" && (
            <div style={{ display: "flex", gap: 8, paddingTop: 4 }}>
              <button onClick={() => approveAction.execute(rw.id)} disabled={approveAction.loading}
                style={{ padding: "6px 14px", fontSize: 13, fontWeight: 600, borderRadius:"var(--radius-md)", border: "none",
                  cursor: "pointer", fontFamily: "inherit", background: "var(--success)", color: "white",
                  opacity: approveAction.loading ? 0.5 : 1 }}>
                {approveAction.loading ? "…" : "Approve"}
              </button>
              <button onClick={() => setRejectId(rw.id)}
                style={{ padding: "6px 14px", fontSize: 13, fontWeight: 600, borderRadius:"var(--radius-md)", border: "none",
                  cursor: "pointer", fontFamily: "inherit", background: "var(--danger)", color: "white" }}>
                Reject
              </button>
            </div>
          )}
        </div>
      ))}

      {rejectId && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex",
          alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "var(--surface)", borderRadius:"var(--radius-lg)", padding: 24, width: "100%",
            maxWidth: 400, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>Reject Rework Request</h2>
            <textarea
              style={{ width: "100%", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", padding: "8px 12px",
                fontSize: 13, background: "var(--bg)", color: "var(--text-primary)", fontFamily: "inherit",
                resize: "vertical", boxSizing: "border-box" }}
              rows={3}
              placeholder="Reason for rejection…"
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => { rejectAction.execute(rejectId, rejectReason); setRejectId(null); setRejectReason(""); }}
                disabled={rejectAction.loading || !rejectReason}
                style={{ padding: "8px 16px", fontSize: 13, fontWeight: 600, borderRadius:"var(--radius-md)", border: "none",
                  cursor: "pointer", fontFamily: "inherit", background: "var(--danger)", color: "white",
                  opacity: rejectAction.loading || !rejectReason ? 0.5 : 1 }}>
                {rejectAction.loading ? "…" : "Confirm Reject"}
              </button>
              <button onClick={() => setRejectId(null)}
                style={{ padding: "8px 16px", fontSize: 13, color: "var(--text-secondary)", background: "none",
                  border: "none", cursor: "pointer", fontFamily: "inherit" }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
