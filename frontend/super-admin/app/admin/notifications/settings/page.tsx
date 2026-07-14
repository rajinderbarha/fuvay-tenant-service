"use client";
/**
 * MODULE-L5-11 — Admin Notification Settings.
 *
 * The admin side had no notification settings page at all — only providers could
 * manage which events/channels they receive. This lets the logged-in admin turn
 * each delivery channel on/off per notification event, backed by the same
 * per-(user, event, channel) preference model.
 *
 * Absence of a preference row means "enabled" (the platform default), so an
 * unset toggle shows ON.
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Spinner } from "../../../../components/shared/ui";
import { sprint27AdminApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { RequirePermission } from "../../../../components/shared/PermissionGate";

const CHANNELS = [
  { key: "in_app",   label: "In-app" },
  { key: "email",    label: "Email" },
  { key: "sms",      label: "SMS" },
  { key: "whatsapp", label: "WhatsApp" },
  { key: "push",     label: "Push" },
];

// Curated set of admin-relevant notification events. Toggling a channel writes a
// per-(event, channel) preference; the key matches what the backend fires.
const EVENT_GROUPS: { group: string; events: { key: string; label: string }[] }[] = [
  { group: "Complaints & Disputes", events: [
    { key: "complaint.filed",                 label: "New complaint filed" },
    { key: "complaint.sla.escalated",         label: "Complaint SLA escalated" },
    { key: "complaint.ai_settlement.escalated", label: "AI settlement escalated to admin" },
    { key: "complaint.settlement_proposed",   label: "Settlement proposed" },
  ]},
  { group: "Providers & Onboarding", events: [
    { key: "tenant.activated",     label: "Provider activated" },
    { key: "tenant.onboarding",    label: "New onboarding request" },
  ]},
  { group: "Finance", events: [
    { key: "wallet.low_balance",   label: "Provider wallet low balance" },
    { key: "deposit.refund",       label: "Security deposit refunded" },
    { key: "topup.credited",       label: "Credit top-up received" },
  ]},
  { group: "Jobs & Bookings", events: [
    { key: "booking.confirmed",    label: "Booking confirmed" },
    { key: "job.completed",        label: "Job completed" },
  ]},
];

export default function AdminNotificationSettingsPage() {
  const prefs = useApi(useCallback(() => sprint27AdminApi.getPreferences(), []), []);
  // local overlay of pending toggles so the UI reacts instantly
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rows = prefs.data ?? [];
  const prefMap: Record<string, boolean> = {};
  for (const p of rows) prefMap[`${p.event_key}::${p.channel}`] = p.is_enabled;

  const isOn = (event: string, channel: string) => {
    const k = `${event}::${channel}`;
    if (k in overrides) return overrides[k];
    if (k in prefMap) return prefMap[k];
    return true; // no preference row = default enabled
  };

  const toggle = async (event: string, channel: string) => {
    const k = `${event}::${channel}`;
    const next = !isOn(event, channel);
    setOverrides(o => ({ ...o, [k]: next }));
    setSavingKey(k); setError(null);
    try {
      await sprint27AdminApi.updatePreference(event, channel, next);
    } catch (e) {
      setOverrides(o => ({ ...o, [k]: !next })); // revert on failure
      setError(e instanceof Error ? e.message : "Could not save preference.");
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <AdminLayout activeNav="settings">
      <RequirePermission requiredPermission="" parentLabel="Settings">
        <SectionHeader
          title="Notification Settings"
          subtitle="Choose which channels you receive each notification on. An unset toggle uses the platform default (on)."
        />

        {prefs.loading ? <Spinner /> : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {error && <p style={{ color: "var(--danger)", fontSize: 13 }}>{error}</p>}
            {EVENT_GROUPS.map(g => (
              <Card key={g.group} padding={0}>
                <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)",
                  fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                  {g.group}
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ textAlign: "left" }}>
                        <th style={{ padding: "10px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>Event</th>
                        {CHANNELS.map(c => (
                          <th key={c.key} style={{ padding: "10px 12px", textAlign: "center",
                            color: "var(--text-tertiary)", fontWeight: 600 }}>{c.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {g.events.map(ev => (
                        <tr key={ev.key} style={{ borderTop: "1px solid var(--border)" }}>
                          <td style={{ padding: "11px 16px", color: "var(--text-primary)" }}>{ev.label}</td>
                          {CHANNELS.map(c => {
                            const on = isOn(ev.key, c.key);
                            const k = `${ev.key}::${c.key}`;
                            return (
                              <td key={c.key} style={{ padding: "8px 12px", textAlign: "center" }}>
                                <button
                                  role="switch" aria-checked={on}
                                  disabled={savingKey === k}
                                  onClick={() => toggle(ev.key, c.key)}
                                  title={on ? "On" : "Off"}
                                  style={{
                                    width: 38, height: 22, borderRadius: 999, border: "none",
                                    cursor: "pointer", position: "relative", verticalAlign: "middle",
                                    background: on ? "var(--accent)" : "var(--surface-sunken, #d0d0d0)",
                                    opacity: savingKey === k ? 0.5 : 1, transition: "background 0.15s",
                                  }}>
                                  <span style={{
                                    position: "absolute", top: 2, left: on ? 18 : 2, width: 18, height: 18,
                                    borderRadius: "50%", background: "#fff", transition: "left 0.15s",
                                    boxShadow: "0 1px 2px rgba(0,0,0,0.3)",
                                  }} />
                                </button>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ))}
            <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              Changes save automatically. <Badge variant="muted">in-app</Badge> notifications also appear in the bell.
            </p>
          </div>
        )}
      </RequirePermission>
    </AdminLayout>
  );
}
