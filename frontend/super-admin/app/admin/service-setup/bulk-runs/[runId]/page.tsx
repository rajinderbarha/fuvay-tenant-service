"use client";
import { TableSurface } from "@serviceos/design-system";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { bulkSetupApi, BulkSetupRun, BulkSetupRunItem } from "../../../../../lib/api";
import { PageHeader } from "@serviceos/design-system";
import { Btn, KpiGrid, SummaryCard } from "../../../../../components/shared/ui";

const ACTION_COLORS: Record<string, string> = {
  created: "var(--success-bg)",
  reused:  "var(--info-bg)",
  mapped:  "var(--accent-muted)",
  skipped: "var(--surface-sunken)",
  failed:  "var(--danger-bg)",
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

  if (loading) return <div style={{ padding: "var(--space-8)", color: "var(--text-secondary)" }}>Loading...</div>;
  if (!run) return <div style={{ padding: "var(--space-8)", color: "var(--text-secondary)" }}>Run not found.</div>;

  const items = run.items ?? [];
  const byAction: Record<string, BulkSetupRunItem[]> = {};
  for (const item of items) {
    byAction[item.action] = [...(byAction[item.action] ?? []), item];
  }

  return (
    <div style={{ maxWidth: 1000, display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <PageHeader
        title="Bulk Setup Run"
        description={`Run ID: ${run.id}`}
        eyebrow="Service Setup"
        actions={<Link href="/admin/service-setup/bulk-runs"><Btn variant="secondary" size="sm">Back to Runs</Btn></Link>}
      />

      {/* Summary cards */}
      <KpiGrid>
        {Object.entries(run.summary_json ?? {}).map(([k, v]) => (
          <SummaryCard key={k} label={k.replace(/_/g, " ")} value={v} />
        ))}
        <SummaryCard label="Status" value={run.status} tone={run.status === "completed" ? "success" : "danger"} />
      </KpiGrid>

      {run.error_json && (
        <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)" }}>
          <div style={{ fontWeight: 700, color: "var(--danger-text)", marginBottom: "var(--space-1)" }}>Error</div>
          <pre style={{ fontSize: "0.75rem", margin: 0 }}>{JSON.stringify(run.error_json, null, 2)}</pre>
        </div>
      )}

      {/* Items by action */}
      {items.length === 0 ? (
        <p style={{ color: "var(--text-tertiary)" }}>No item records for this run.</p>
      ) : (
        <div>
          {Object.entries(byAction).map(([action, actionItems]) => (
            <div key={action} style={{ marginBottom: "1.25rem" }}>
              <h3 style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: "var(--space-2)", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
                {action} ({actionItems.length})
              </h3>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Entity Type", "Code / ID", "Message"].map(h => (
                      <th key={h} scope="col" style={{ textAlign: "left", padding: "0.4rem 0.75rem", fontSize: "0.7rem", color: "var(--text-tertiary)", fontWeight: 600, borderBottom: "1px solid var(--border)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {actionItems.map(item => (
                    <tr key={item.id} style={{ borderBottom: "1px solid var(--border)", background: ACTION_COLORS[item.action] ?? "transparent" }}>
                      <td style={{ padding: "0.4rem 0.75rem", fontSize: "0.78rem", fontFamily: "monospace" }}>{item.entity_type}</td>
                      <td style={{ padding: "0.4rem 0.75rem", fontSize: "0.75rem", color: "var(--text-tertiary)", fontFamily: "monospace" }}>
                        {item.entity_code ?? item.entity_id?.slice(0, 8) ?? "—"}
                      </td>
                      <td style={{ padding: "0.4rem 0.75rem", fontSize: "0.78rem", color: "var(--text-secondary)" }}>{item.message ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </TableSurface>
            </div>
          ))}
        </div>
      )}

      <div style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
        Draft: {run.draft_id} | Applied by: {run.applied_by_user_id ?? "—"} | Completed: {run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}
      </div>
    </div>
  );
}
