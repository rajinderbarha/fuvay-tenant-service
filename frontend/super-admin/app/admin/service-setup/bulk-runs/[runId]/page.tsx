"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { bulkSetupApi, BulkSetupRun, BulkSetupRunItem } from "../../../../../lib/api";

const ACTION_COLORS: Record<string, string> = {
  created: "#dcfce7",
  reused:  "#dbeafe",
  mapped:  "#ede9fe",
  skipped: "#f3f4f6",
  failed:  "#fef2f2",
};

export default function BulkRunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<BulkSetupRun | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    bulkSetupApi.getRun(runId)
      .then(setRun)
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) return <div style={{ padding: "2rem" }}>Loading...</div>;
  if (!run) return <div style={{ padding: "2rem" }}>Run not found.</div>;

  const items = run.items ?? [];
  const byAction: Record<string, BulkSetupRunItem[]> = {};
  for (const item of items) {
    byAction[item.action] = [...(byAction[item.action] ?? []), item];
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "900px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link href="/admin/service-setup/bulk-runs" style={{ color: "#6b7280", fontSize: "0.85rem", textDecoration: "none" }}>
          ← Back to Runs
        </Link>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700, margin: "0.5rem 0 0" }}>Bulk Setup Run</h1>
        <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>{run.id}</div>
      </div>

      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.75rem", marginBottom: "1.5rem" }}>
        {Object.entries(run.summary_json ?? {}).map(([k, v]) => (
          <div key={k} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", padding: "0.85rem", textAlign: "center" }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#1e3a5f" }}>{v}</div>
            <div style={{ fontSize: "0.75rem", color: "#6b7280" }}>{k}</div>
          </div>
        ))}
        <div style={{ background: run.status === "completed" ? "#f0fdf4" : "#fef2f2", border: `1px solid ${run.status === "completed" ? "#bbf7d0" : "#fecaca"}`, borderRadius: "0.5rem", padding: "0.85rem", textAlign: "center" }}>
          <div style={{ fontSize: "0.9rem", fontWeight: 700, color: run.status === "completed" ? "var(--success)" : "var(--danger)" }}>{run.status}</div>
          <div style={{ fontSize: "0.7rem", color: "#6b7280" }}>status</div>
        </div>
      </div>

      {run.error_json && (
        <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "0.5rem", padding: "1rem", marginBottom: "1.25rem" }}>
          <div style={{ fontWeight: 700, color: "var(--danger)", marginBottom: "0.25rem" }}>Error</div>
          <pre style={{ fontSize: "0.75rem", margin: 0 }}>{JSON.stringify(run.error_json, null, 2)}</pre>
        </div>
      )}

      {/* Items by action */}
      {items.length === 0 ? (
        <p style={{ color: "#9ca3af" }}>No item records for this run.</p>
      ) : (
        <div>
          {Object.entries(byAction).map(([action, actionItems]) => (
            <div key={action} style={{ marginBottom: "1.25rem" }}>
              <h3 style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "#4b5563" }}>
                {action} ({actionItems.length})
              </h3>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#f9fafb" }}>
                    {["Entity Type", "Code / ID", "Message"].map(h => (
                      <th key={h} style={{ textAlign: "left", padding: "0.4rem 0.75rem", fontSize: "0.7rem", color: "#6b7280", fontWeight: 600, borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {actionItems.map(item => (
                    <tr key={item.id} style={{ borderBottom: "1px solid #f3f4f6", background: ACTION_COLORS[item.action] ?? "transparent" }}>
                      <td style={{ padding: "0.4rem 0.75rem", fontSize: "0.78rem", fontFamily: "monospace" }}>{item.entity_type}</td>
                      <td style={{ padding: "0.4rem 0.75rem", fontSize: "0.75rem", color: "#6b7280", fontFamily: "monospace" }}>
                        {item.entity_code ?? item.entity_id?.slice(0, 8) ?? "—"}
                      </td>
                      <td style={{ padding: "0.4rem 0.75rem", fontSize: "0.78rem", color: "#4b5563" }}>{item.message ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: "1.5rem", fontSize: "0.75rem", color: "#9ca3af" }}>
        Draft: {run.draft_id} | Applied by: {run.applied_by_user_id ?? "—"} | Completed: {run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}
      </div>
    </div>
  );
}
