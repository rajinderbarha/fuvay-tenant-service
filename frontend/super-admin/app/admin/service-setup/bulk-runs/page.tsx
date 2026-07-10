"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { bulkWizardApi, BulkRunItem } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Btn } from "../../../../components/shared/ui";

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string }> = {
    queued: { bg: "var(--surface-sunken)", color: "var(--text-tertiary)" },
    running: { bg: "var(--accent-muted)", color: "var(--accent)" },
    completed: { bg: "var(--success-bg)", color: "var(--success-text)" },
    failed: { bg: "var(--danger-bg)", color: "var(--danger-text)" },
    partially_completed: { bg: "var(--warning-bg)", color: "var(--warning-text)" },
    rolled_back: { bg: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  };
  const s = map[status] ?? map.queued;
  return (
    <span style={{
      background: s.bg, color: s.color,
      fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 999,
      textTransform: "uppercase", letterSpacing: 0.5,
    }}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export default function BulkRunsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);

  const { data: runsData, loading, refetch } = useApi(
    () => bulkWizardApi.listRuns({ page, page_size: 25 }),
    [page],
  );

  const rollbackAction = useAction(async ({ id, reason }: { id: string; reason: string }) => {
    await bulkWizardApi.rollbackRun(id, reason);
    refetch();
  });

  const runs = (runsData as { items: BulkRunItem[]; total: number } | null)?.items ?? [];
  const total = (runsData as { items: BulkRunItem[]; total: number } | null)?.total ?? 0;

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ marginBottom: 8, fontSize: 12, color: "var(--text-tertiary)" }}>
        Service Setup / Bulk Wizard / Runs
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
            Bulk Setup Runs
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: "0.25rem 0 0", fontSize: 13 }}>
            History of all bulk setup execution runs
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/service-setup/bulk-wizard")}>
            Back to Wizard
          </Btn>
          <Btn variant="ghost" size="sm" onClick={() => refetch()}>Refresh</Btn>
        </div>
      </div>

      {loading ? (
        <div style={{ color: "var(--text-secondary)", padding: 24 }}>Loading runs...</div>
      ) : runs.length === 0 ? (
        <div style={{
          textAlign: "center", padding: "4rem 2rem",
          background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12,
        }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
            No runs yet.
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: 13, marginBottom: 20 }}>
            Execute a bulk setup draft to see runs here.
          </div>
          <Btn variant="primary" onClick={() => router.push("/admin/service-setup/bulk-wizard")}>
            Go to Bulk Wizard
          </Btn>
        </div>
      ) : (
        <>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Run Code", "Vertical", "Status", "Total", "Created", "Skipped", "Failed", "Dry Run", "Started At", "Actions"].map(h => (
                    <th key={h} style={{ textAlign: "left", padding: "10px 14px", color: "var(--text-secondary)", fontWeight: 600, fontSize: 11 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {runs.map(r => (
                  <tr key={r.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 14px", fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)" }}>{r.run_code}</td>
                    <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>{r.vertical_key ?? "—"}</td>
                    <td style={{ padding: "10px 14px" }}><StatusBadge status={r.status} /></td>
                    <td style={{ padding: "10px 14px", color: "var(--text-primary)" }}>{r.total_items}</td>
                    <td style={{ padding: "10px 14px", color: "var(--success-text)" }}>{r.created_count}</td>
                    <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>{r.skipped_count}</td>
                    <td style={{ padding: "10px 14px", color: "var(--danger-text)" }}>{r.failed_count}</td>
                    <td style={{ padding: "10px 14px" }}>
                      {r.is_dry_run
                        ? <span style={{ color: "var(--accent)", fontSize: 11, fontWeight: 600 }}>DRY RUN</span>
                        : <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>LIVE</span>
                      }
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-tertiary)", fontSize: 11 }}>
                      {r.started_at ? new Date(r.started_at).toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <div style={{ display: "flex", gap: 6 }}>
                        <Btn size="xs" variant="ghost" onClick={() => router.push(`/admin/service-setup/bulk-runs/${r.id}`)}>
                          Details
                        </Btn>
                        {r.rollback_available && (
                          <Btn size="xs" variant="danger" onClick={() => rollbackAction.execute({ id: r.id, reason: "Manual rollback" })}>
                            Rollback
                          </Btn>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, fontSize: 12, color: "var(--text-tertiary)" }}>
            <span>{total} total runs</span>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn size="xs" variant="ghost" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</Btn>
              <span style={{ padding: "0 8px", lineHeight: "28px" }}>Page {page}</span>
              <Btn size="xs" variant="ghost" disabled={runs.length < 25} onClick={() => setPage(p => p + 1)}>Next</Btn>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
