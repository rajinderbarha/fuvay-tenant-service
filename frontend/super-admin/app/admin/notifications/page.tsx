"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, SectionHeader, Skeleton, EmptyState, Select, Input,
} from "../../../components/shared/ui";
import { sprint27AdminApi } from "../../../lib/api";
import type { InAppNotification } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Bell, CheckCheck, RefreshCw, Eye } from "lucide-react";

const SEVERITY_VARIANT: Record<string, "danger" | "warning" | "success" | "muted"> = {
  critical: "danger", high: "danger", medium: "warning", low: "muted", info: "muted",
};

export default function NotificationCenterPage() {
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
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="secondary" onClick={handleMarkAllRead} loading={markAllReadAction.loading}>
              <CheckCheck size={14} style={{ marginRight: 4 }}/> Mark All Read
            </Btn>
            <Btn variant="ghost" size="sm" onClick={() => { feed.refetch(); unreadCountApi.refetch(); }}>
              <RefreshCw size={14}/>
            </Btn>
          </div>
        }
      />

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
                <a href={selected.action_url} style={{ color: "var(--brand)", fontSize: 13 }}>
                  {selected.action_label ?? selected.action_url}
                </a>
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
    </AdminLayout>
  );
}
