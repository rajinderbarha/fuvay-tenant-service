"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * The Trust & Quality audit trail.
 *
 * Every rule activation, manual award, revocation and queued sweep already
 * wrote a `trust_quality_audit_logs` row, and the endpoint to read them already
 * existed — but nothing in the console ever called it, so the record existed
 * purely for a DBA. Badges and health bands decide commission and customer-facing
 * trust, which makes "who changed this and why" a compliance question, not a
 * nicety.
 */
import React, { useCallback, useState } from "react";
import { ScrollText } from "lucide-react";
import { Card, Btn, Badge, Spinner, Select, Pagination, EmptyState } from "../../../components/shared/ui";
import { trustQualityApi, TrustQualityAuditRow, TQ_ENUMS } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";

const PAGE_SIZE = 25;

/** Colour by what the action did, not by which engine it belongs to. */
function actionTone(action: string): "success" | "danger" | "warning" | "info" | "muted" {
  if (action.includes("awarded") || action.includes("activated")) return "success";
  if (action.includes("revoked") || action.includes("failed")) return "danger";
  if (action.includes("deactivated") || action.includes("expired") || action.includes("cancelled")) return "warning";
  if (action.includes("queued") || action.includes("calculated")) return "info";
  return "muted";
}

export function AuditTab() {
  const [page, setPage] = useState(1);
  const [actionType, setActionType] = useState("");
  const [targetType, setTargetType] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const logs = useApi(
    useCallback(() => trustQualityApi.listAuditLogs({
      action_type: actionType || undefined,
      target_type: targetType || undefined,
      limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE,
    }), [actionType, targetType, page]),
    [actionType, targetType, page],
  );

  const rows = logs.data?.items ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ minWidth: 240 }}>
            <Select label="Action" value={actionType}
              onChange={v => { setActionType(v); setPage(1); }}
              options={[{ value: "", label: "All actions" },
                ...["badge_rule.activated", "badge_rule.deactivated",
                    "badge_assignment.awarded", "badge_assignment.revoked",
                    "badge_assignment.expired", "health_formula.activated",
                    "health_formula.deactivated", "health_score.calculated",
                    "recalculation_job.queued", "recalculation_job.cancelled",
                   ].map(v => ({ value: v, label: v }))]} />
          </div>
          <div style={{ minWidth: 200 }}>
            <Select label="Target type" value={targetType}
              onChange={v => { setTargetType(v); setPage(1); }}
              options={[
                { value: "", label: "All targets" },
                ...TQ_ENUMS.badgeTargets.map(v => ({ value: v, label: v.replace(/_/g, " ") })),
                { value: "health_formula", label: "health formula" },
                { value: "badge_rule", label: "badge rule" },
                { value: "recalculation_job", label: "recalculation job" },
              ]} />
          </div>
          <Btn size="sm" variant="ghost" onClick={() => logs.refetch()}>Refresh</Btn>
        </div>
      </Card>

      <Card padding={0}>
        {logs.loading ? <Spinner /> : rows.length === 0 ? (
          <EmptyState icon={<ScrollText />} title="No audit entries"
            description="Rule changes, badge awards and recalculations appear here as they happen." />
        ) : (
          <>
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "10px 16px" }}>When</th>
                  <th style={{ padding: "10px 16px" }}>Action</th>
                  <th style={{ padding: "10px 16px" }}>Target</th>
                  <th style={{ padding: "10px 16px" }}>Actor</th>
                  <th style={{ padding: "10px 16px" }}>Reason</th>
                  <th style={{ padding: "10px 16px" }}></th>
                </tr></thead>
                <tbody>
                  {rows.map(l => (
                    <React.Fragment key={l.id}>
                      <tr style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "10px 16px", color: "var(--text-tertiary)", fontSize: 12, whiteSpace: "nowrap" }}>
                          {String(l.created_at ?? "").replace("T", " ").slice(0, 19)}
                        </td>
                        <td style={{ padding: "10px 16px" }}>
                          <Badge variant={actionTone(l.action_type)}>{l.action_type}</Badge>
                        </td>
                        <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                          {l.target_type ? `${l.target_type.replace(/_/g, " ")}` : "—"}
                          {l.target_id && <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{l.target_id.slice(0, 8)}</div>}
                        </td>
                        <td style={{ padding: "10px 16px", fontSize: 12 }}>{l.actor_role ?? "system"}</td>
                        <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)", maxWidth: 280 }}>
                          {l.reason || "—"}
                        </td>
                        <td style={{ padding: "10px 16px" }}>
                          <Btn size="sm" variant="ghost"
                            onClick={() => setExpanded(expanded === l.id ? null : l.id)}>
                            {expanded === l.id ? "Hide" : "Detail"}
                          </Btn>
                        </td>
                      </tr>
                      {expanded === l.id && (
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                          <td colSpan={6} style={{ padding: 0, background: "var(--surface-sunken)" }}>
                            <ValueDiff row={l} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </TableSurface>
            </div>
            <Pagination page={page} total={logs.data?.total ?? 0}
              pageSize={PAGE_SIZE} onPage={setPage} alwaysShow />
          </>
        )}
      </Card>
    </div>
  );
}

function ValueDiff({ row }: { row: TrustQualityAuditRow }) {
  const pane = (title: string, value: Record<string, unknown> | null) => (
    <div style={{ flex: 1, minWidth: 240 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
        letterSpacing: "0.05em", color: "var(--text-tertiary)", marginBottom: 6 }}>{title}</div>
      <pre style={{ margin: 0, fontSize: 11, lineHeight: 1.5, whiteSpace: "pre-wrap",
        wordBreak: "break-word", color: "var(--text-secondary)", fontFamily: "monospace" }}>
        {value ? JSON.stringify(value, null, 2) : "—"}
      </pre>
    </div>
  );
  return (
    <div style={{ padding: "14px 16px", display: "flex", gap: 24, flexWrap: "wrap" }}>
      {pane("Before", row.old_value)}
      {pane("After", row.new_value)}
    </div>
  );
}
