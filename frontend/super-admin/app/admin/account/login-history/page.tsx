"use client";
import React, { useState, useEffect } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Spinner } from "../../../../components/shared/ui";
import { authApi, type LoginHistoryEvent } from "../../../../lib/api";

function fmt(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}
function eventVariant(t: string): "success" | "danger" | "muted" | "warning" {
  if (t === "login_success") return "success";
  if (t === "login_failed")  return "danger";
  if (t === "logout")        return "muted";
  return "warning";
}

export default function SelfLoginHistoryPage() {
  const [events, setEvents] = useState<LoginHistoryEvent[]>([]);
  const [total, setTotal]   = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true); setError("");
      try {
        const res = await authApi.getSelfLoginHistory(100);
        setEvents(res.events ?? []);
        setTotal(res.total ?? 0);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load login history.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <AdminLayout activeNav="account">
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 900 }}>
        <SectionHeader
          title="Login History"
          subtitle={`${total} event(s) recorded for your account`}
        />

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: 48 }}><Spinner /></div>
        ) : error ? (
          <div style={{ padding: 24, color: "var(--danger-text)", fontSize: 13 }}>{error}</div>
        ) : events.length === 0 ? (
          <Card padding={24}>
            <p style={{ margin: 0, color: "var(--text-tertiary)", fontSize: 13 }}>
              No login events recorded yet.
            </p>
          </Card>
        ) : (
          <Card padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Time", "Event", "IP Address", "Device", "Failure Reason"].map(h => (
                      <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600,
                        fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase",
                        letterSpacing: "0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {events.map(ev => (
                    <tr key={ev.event_id} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px", color: "var(--text-secondary)", fontSize: 12 }}>
                        {fmt(ev.created_at)}
                      </td>
                      <td style={{ padding: "10px 16px" }}>
                        <Badge variant={eventVariant(ev.event_type)} size="sm">
                          {ev.event_type.replace(/_/g, " ")}
                        </Badge>
                      </td>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12,
                        color: "var(--text-secondary)" }}>{ev.ip_address ?? "—"}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                        {ev.device_id ?? "—"}
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--danger-text)" }}>
                        {ev.failure_reason ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </AdminLayout>
  );
}
