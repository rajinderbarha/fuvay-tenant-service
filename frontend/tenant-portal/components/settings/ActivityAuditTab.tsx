"use client";
import React, { useCallback } from "react";
import { Card, Skeleton } from "../shared/ui";
import { workspaceSettingsApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

function opLabel(op: string): string {
  return op.replace(/[._]/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

export function ActivityAuditTab() {
  const activity = useApi(useCallback(() => workspaceSettingsApi.getActivity(30), []));
  if (activity.loading) return <Skeleton height={300}/>;
  if (!activity.data) return <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>{activity.error ?? "Could not load activity."}</p>;
  const items = activity.data.items;

  return (
    <Card style={{ maxWidth: 780 }}>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Workspace setting changes</p>
      {items.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No workspace setting changes recorded yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {items.map(item => (
            <div key={item.id} style={{ padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{opLabel(item.operation)}</p>
                  <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
                    {item.actor_name}{item.actor_role ? ` · ${item.actor_role}` : ""}
                  </p>
                </div>
                <span style={{ fontSize: 11, color: "var(--text-tertiary)", flexShrink: 0 }}>
                  {item.created_at ? new Date(item.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—"}
                </span>
              </div>
              {item.after && Object.keys(item.after).length > 0 && (
                <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "6px 0 0", fontFamily: "monospace" }}>
                  {JSON.stringify(item.after)}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
