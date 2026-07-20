"use client";
import React, { useCallback, useState } from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, Badge, Skeleton } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { staffMyWorkApi, MyWorkItem } from "../../../lib/api";

// Phase 2A — Technician My Work. An actionable queue derived from real
// ServiceJob + PartsRequest state (see
// docs/workflow-rearchitecture/phase-01a/my-work-contract.md), not a
// notification list. Scoped to the ServiceJob pipeline only; does not
// aggregate Booking or field_ops Job (see booking-job-canonical-decision.md).

const SECTION_ORDER = [
  "URGENT", "REQUIRES_MY_ACTION", "WAITING_FOR_OTHERS", "SCHEDULED", "FAILED",
] as const;

const SECTION_LABELS: Record<string, string> = {
  URGENT: "Urgent",
  REQUIRES_MY_ACTION: "Requires My Action",
  WAITING_FOR_OTHERS: "Waiting for Others",
  SCHEDULED: "Scheduled",
  FAILED: "Failed",
};

function categoryVariant(category: string): "danger" | "info" | "warning" | "muted" {
  if (category === "URGENT" || category === "FAILED") return "danger";
  if (category === "REQUIRES_MY_ACTION") return "warning";
  if (category === "SCHEDULED") return "info";
  return "muted";
}

export default function StaffMyWorkPage() {
  const [category, setCategory] = useState<string>("");
  const work = useApi(
    useCallback(() => staffMyWorkApi.list(category ? { category } : undefined), [category]),
    [category],
  );

  const items = work.data?.items ?? [];
  const grouped: Record<string, MyWorkItem[]> = {};
  for (const item of items) {
    // Items priority=urgent surface under URGENT regardless of category,
    // matching the approved contract's cross-cutting Urgent bucket.
    const bucket = item.priority === "urgent" ? "URGENT" : item.category;
    (grouped[bucket] ??= []).push(item);
  }

  return (
    <StaffLayout activeNav="my-work">
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>My Work</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
            Everything that needs your attention across assigned jobs and parts requests.
          </p>
        </div>
        <select value={category} onChange={e => setCategory(e.target.value)}
          style={{ padding: "8px 10px", fontSize: 13, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)" }}>
          <option value="">All categories</option>
          {SECTION_ORDER.map(c => <option key={c} value={c}>{SECTION_LABELS[c]}</option>)}
        </select>
      </div>

      {work.loading ? (
        <Skeleton height={240} />
      ) : work.error ? (
        <Card><p style={{ color: "var(--danger-text)", fontSize: 13 }}>{work.error}{work.requestId && ` — Request ID: ${work.requestId}`}</p></Card>
      ) : (
        <>
          {work.data?.sources_unavailable && work.data.sources_unavailable.length > 0 && (
            <Card style={{ marginBottom: 16, background: "var(--warning-bg)" }}>
              <p style={{ fontSize: 12, color: "var(--warning-text)", margin: 0 }}>
                Some data sources are temporarily unavailable ({work.data.sources_unavailable.join(", ")}) —
                the list below may be incomplete.
              </p>
            </Card>
          )}

          {items.length === 0 ? (
            <Card><p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>Nothing needs your attention right now.</p></Card>
          ) : (
            SECTION_ORDER.filter(section => grouped[section]?.length).map(section => (
              <div key={section} style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-tertiary)", margin: "0 0 8px" }}>
                  {SECTION_LABELS[section]} ({grouped[section].length})
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {grouped[section].map(item => (
                    <a key={item.id} href={item.destination_route} style={{ textDecoration: "none", color: "inherit" }}>
                      <Card hover>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 14, fontWeight: 700 }}>{item.user_facing_title}</div>
                            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{item.user_facing_status}</div>
                            <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 6 }}>{item.recommended_action}</div>
                            {item.blocking_reason && (
                              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>
                                Responsible: {item.responsible_role}
                              </div>
                            )}
                          </div>
                          <Badge variant={categoryVariant(item.category)} size="sm">{SECTION_LABELS[item.category] ?? item.category}</Badge>
                        </div>
                      </Card>
                    </a>
                  ))}
                </div>
              </div>
            ))
          )}
        </>
      )}
    </StaffLayout>
  );
}
