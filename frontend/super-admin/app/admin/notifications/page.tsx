"use client";
import React, { useState, useCallback } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, SectionHeader, Skeleton, EmptyState, Select, Input, Spinner,
} from "../../../components/shared/ui";
import { sprint27AdminApi } from "../../../lib/api";
import type { InAppNotification } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Bell, CheckCheck, RefreshCw, Eye, Settings } from "lucide-react";
import { RequirePermission } from "../../../components/shared/PermissionGate";
import { NotificationTemplatesContent } from "./templates/page";
import { EventPoliciesPanel } from "./EventPoliciesPanel";
import { DeliveryProvidersPanel } from "./DeliveryProvidersPanel";
import { LogsFailuresPanel } from "./LogsFailuresPanel";

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

// ── Settings tab (was a separate /admin/notifications/settings page +
// nav item, folded in here 2026-08-05 at explicit user request). ──────────
function NotificationSettingsPanel() {
  const prefs = useApi(useCallback(() => sprint27AdminApi.getPreferences(), []), []);
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
    <RequirePermission requiredPermission="" parentLabel="Settings">
      {prefs.loading ? <Spinner /> : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
            Choose which channels you receive each notification on. An unset toggle uses the platform default (on).
          </p>
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
  );
}

const SEVERITY_VARIANT: Record<string, "danger" | "warning" | "success" | "muted"> = {
  critical: "danger", high: "danger", medium: "warning", low: "muted", info: "muted",
};

export default function NotificationCenterPage() {
  const [tab, setTab] = useState<"feed" | "templates" | "policies" | "providers" | "logs" | "settings">("feed");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<InAppNotification | null>(null);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const feed = useApi(useCallback(() =>
    sprint27AdminApi.listNotifications({
      read_status: statusFilter || undefined,
      limit: 100,
    }), [statusFilter]));

  const unreadCountApi = useApi(useCallback(() =>
    sprint27AdminApi.getUnreadCount(), []));

  const markReadAction = useAction(useCallback((id: string) =>
    sprint27AdminApi.markRead(id), []));

  const markAllReadAction = useAction(useCallback(() =>
    sprint27AdminApi.markAllRead(), []));

  async function handleMarkRead(id: string) {
    const res = await markReadAction.execute(id);
    if (res) { feed.refetch(); unreadCountApi.refetch(); notify("Notification marked as read."); }
  }

  async function handleMarkAllRead() {
    const res = await markAllReadAction.execute();
    if (res) { feed.refetch(); unreadCountApi.refetch(); notify(`Marked ${res.marked_read} notifications as read.`); }
  }

  const items: InAppNotification[] = (feed.data?.items ?? []).filter(n => {
    if (typeFilter && !n.notification_type.includes(typeFilter)) return false;
    if (search) {
      const q = search.toLowerCase();
      return n.title.toLowerCase().includes(q) || n.body.toLowerCase().includes(q);
    }
    return true;
  });

  const total = feed.data?.total ?? 0;
  const unread = unreadCountApi.data?.unread_count ?? 0;
  const failed = items.filter(n => n.severity === "critical" || n.severity === "high").length;
  const delivered = items.filter(n => n.read_status === "read").length;

  return (
    <AdminLayout activeNav="notifications">
      <style>{`
        .nc-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
        .nc-kpi-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px; }
        .nc-kpi-card.accent { border-top: 3px solid var(--brand); }
        .nc-kpi-card.danger { border-top: 3px solid var(--danger); }
        .nc-kpi-value { font-size: 28px; font-weight: 800; color: var(--text-primary); }
        .nc-kpi-value.danger { color: var(--danger-text); }
        .nc-kpi-label { font-size: 11px; color: var(--text-tertiary); margin-top: 4px; text-transform: uppercase; letter-spacing: .05em; }
        .nc-toolbar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
        .nc-toolbar-search { flex: 1 1 220px; }
        .nc-list { display: flex; flex-direction: column; gap: 0; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
        .nc-row { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr auto; gap: 12px; align-items: center;
          padding: 14px 18px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background .15s; }
        .nc-row:last-child { border-bottom: none; }
        .nc-row:hover { background: var(--surface-hover, var(--surface-sunken)); }
        .nc-row.unread { background: var(--brand-bg, rgba(0,80,255,.04)); font-weight: 600; }
        .nc-col-header { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr auto; gap: 12px;
          padding: 10px 18px; background: var(--surface-sunken); border-bottom: 1px solid var(--border);
          font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: .05em; }
        .nc-detail-field { margin-bottom: 12px; }
        .nc-detail-label { font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
        .nc-detail-value { font-size: 13px; color: var(--text-primary); }
        @media (max-width: 768px) {
          .nc-kpi-grid { grid-template-columns: repeat(2,1fr); }
          .nc-row, .nc-col-header { grid-template-columns: 1fr auto; }
          .nc-row > *:nth-child(2), .nc-row > *:nth-child(3), .nc-row > *:nth-child(4),
          .nc-col-header > *:nth-child(2), .nc-col-header > *:nth-child(3), .nc-col-header > *:nth-child(4) { display: none; }
        }
      `}</style>

      <SectionHeader
        title="Notification Center"
        subtitle="Real-time feed of platform, tenant, and system notifications."
        actions={tab === "feed" ? (
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="secondary" onClick={handleMarkAllRead} loading={markAllReadAction.loading}>
              <CheckCheck size={14} style={{ marginRight: 4 }}/> Mark All Read
            </Btn>
            <Btn variant="ghost" size="sm" onClick={() => { feed.refetch(); unreadCountApi.refetch(); }}>
              <RefreshCw size={14}/>
            </Btn>
          </div>
        ) : undefined}
      />

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 20, overflowX: "auto" }}>
        {([
          ["feed", "Feed"], ["templates", "Templates"], ["policies", "Event Policies"],
          ["providers", "Delivery Providers"], ["logs", "Logs & Failures"], ["settings", "Settings"],
        ] as const).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            style={{ padding: "10px 16px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === key ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === key ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer",
              display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}>
            {key === "settings" && <Settings size={13} />} {label}
          </button>
        ))}
      </div>

      {tab === "templates" && <NotificationTemplatesContent />}
      {tab === "policies" && <EventPoliciesPanel />}
      {tab === "providers" && <DeliveryProvidersPanel />}
      {tab === "logs" && <LogsFailuresPanel />}
      {tab === "settings" && <NotificationSettingsPanel />}

      {tab === "feed" && <>
      {toast && (
        <div style={{ padding: "10px 16px", marginBottom: 16, borderRadius: 10,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13 }}>
          {toast.msg}
        </div>
      )}

      {/* KPI cards */}
      <div className="nc-kpi-grid">
        {feed.loading ? [...Array(4)].map((_, i) => <Skeleton key={i} height={90} style={{ borderRadius: 14 }}/>) : <>
          <div className="nc-kpi-card">
            <div className="nc-kpi-value">{total}</div>
            <div className="nc-kpi-label">Total</div>
          </div>
          <div className={`nc-kpi-card${unread > 0 ? " accent" : ""}`}>
            <div className="nc-kpi-value">{unread}</div>
            <div className="nc-kpi-label">Unread</div>
          </div>
          <div className={`nc-kpi-card${failed > 0 ? " danger" : ""}`}>
            <div className={`nc-kpi-value${failed > 0 ? " danger" : ""}`}>{failed}</div>
            <div className="nc-kpi-label">High/Critical</div>
          </div>
          <div className="nc-kpi-card">
            <div className="nc-kpi-value">{delivered}</div>
            <div className="nc-kpi-label">Read</div>
          </div>
        </>}
      </div>

      {/* Toolbar */}
      <div className="nc-toolbar">
        <div className="nc-toolbar-search">
          <Input placeholder="Search notifications…" value={search} onChange={setSearch}/>
        </div>
        <Select
          value={statusFilter}
          onChange={setStatusFilter}
          placeholder="Status"
          options={[
            { value: "", label: "All Status" },
            { value: "unread", label: "Unread" },
            { value: "read", label: "Read" },
          ]}
        />
        <Select
          value={typeFilter}
          onChange={setTypeFilter}
          placeholder="Type"
          options={[
            { value: "", label: "All Types" },
            { value: "booking", label: "Booking" },
            { value: "payment", label: "Payment" },
            { value: "complaint", label: "Complaint" },
            { value: "tenant", label: "Tenant" },
            { value: "security", label: "Security" },
            { value: "system", label: "System" },
          ]}
        />
      </div>

      {/* Notification list */}
      {feed.loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[...Array(6)].map((_, i) => <Skeleton key={i} height={56}/>)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="No notifications yet"
          description="No notifications yet. System and tenant alerts will appear here."
          icon={<Bell size={40} style={{ color: "var(--text-tertiary)" }}/>}
        />
      ) : (
        <div className="nc-list">
          <div className="nc-col-header">
            <span>Notification</span>
            <span>Type</span>
            <span>Severity</span>
            <span>Created</span>
            <span>Actions</span>
          </div>
          {items.map(n => (
            <div
              key={n.id}
              className={`nc-row${n.read_status === "unread" ? " unread" : ""}`}
              onClick={() => setSelected(n)}
            >
              <div>
                <div style={{ fontSize: 13, fontWeight: n.read_status === "unread" ? 700 : 500, color: "var(--text-primary)", marginBottom: 2 }}>
                  {n.title}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 360 }}>
                  {n.body}
                </div>
              </div>
              <div>
                <Badge variant="muted">{n.notification_type.replace(/_/g, " ")}</Badge>
              </div>
              <div>
                <Badge variant={SEVERITY_VARIANT[n.severity] ?? "muted"}>{n.severity}</Badge>
              </div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                {new Date(n.created_at).toLocaleString()}
              </div>
              <div style={{ display: "flex", gap: 6 }} onClick={e => e.stopPropagation()}>
                <Btn size="xs" variant="ghost" onClick={() => setSelected(n)}><Eye size={12}/></Btn>
                {n.read_status === "unread" && (
                  <Btn size="xs" variant="secondary" loading={markReadAction.loading}
                    onClick={() => handleMarkRead(n.id)}>Read</Btn>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail modal */}
      {selected && (
        <Modal open onClose={() => setSelected(null)} title={selected.title} size="md">
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Badge variant={SEVERITY_VARIANT[selected.severity] ?? "muted"}>{selected.severity}</Badge>
              <Badge variant={selected.read_status === "unread" ? "warning" : "success"}>{selected.read_status}</Badge>
              <Badge variant="muted">{selected.notification_type.replace(/_/g, " ")}</Badge>
            </div>

            <div className="nc-detail-field">
              <div className="nc-detail-label">Message</div>
              <div className="nc-detail-value" style={{ padding: "12px 14px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", whiteSpace: "pre-wrap" }}>
                {selected.body}
              </div>
            </div>

            {selected.action_url && (
              <div className="nc-detail-field">
                <div className="nc-detail-label">Action</div>
                <Link href={selected.action_url} style={{ color: "var(--brand)", fontSize: 13 }}>
                  {selected.action_label ?? selected.action_url}
                </Link>
              </div>
            )}

            {selected.source_record_type && (
              <div className="nc-detail-field">
                <div className="nc-detail-label">Related Record</div>
                <div className="nc-detail-value">{selected.source_record_type} — {selected.source_record_id}</div>
              </div>
            )}

            <div className="nc-detail-field">
              <div className="nc-detail-label">Created</div>
              <div className="nc-detail-value">{new Date(selected.created_at).toLocaleString()}</div>
            </div>

            {selected.read_at && (
              <div className="nc-detail-field">
                <div className="nc-detail-label">Read At</div>
                <div className="nc-detail-value">{new Date(selected.read_at).toLocaleString()}</div>
              </div>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", borderTop: "1px solid var(--border)", paddingTop: 14 }}>
              {selected.read_status === "unread" && (
                <Btn size="sm" variant="secondary" loading={markReadAction.loading}
                  onClick={() => { handleMarkRead(selected.id); setSelected(null); }}>
                  Mark as Read
                </Btn>
              )}
              <Btn size="sm" variant="ghost" onClick={() => setSelected(null)}>Close</Btn>
            </div>
          </div>
        </Modal>
      )}
      </>}
    </AdminLayout>
  );
}
