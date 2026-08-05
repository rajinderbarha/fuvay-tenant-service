"use client";
/**
 * MODULE-L5-11 — Customer Notifications.
 *
 * The customer app had no notification surface at all. This lists the customer's
 * notifications (booking updates, complaint responses, settlement offers, credit
 * alerts) with mark-read, and a settings section to turn delivery channels on/off
 * per event. Reached from Profile → Notifications.
 */
import { useEffect, useState, useCallback } from "react";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import {
  listNotifications, markRead, markAllRead, getPreferences, updatePreference,
  CustomerNotification, NotificationPref,
} from "../../../lib/api/customer-notifications";

const CHANNELS = [
  { key: "in_app", label: "In-app" },
  { key: "email",  label: "Email" },
  { key: "sms",    label: "SMS" },
  { key: "push",   label: "Push" },
];

const EVENTS = [
  { key: "booking.confirmed",           label: "Booking updates" },
  { key: "job.completed",               label: "Job completed" },
  { key: "complaint.resolution_offered", label: "Complaint responses" },
  { key: "complaint.settlement_proposed", label: "Settlement offers" },
  { key: "complaint.settlement_paid",   label: "Credit / refund alerts" },
];

const STATUS_COLOR = (s: string) =>
  s === "critical" || s === "danger" ? "#c0392b" : s === "warning" ? "#b45309" : "#3B6FED";

export default function CustomerNotificationsPage() {
  const [tab, setTab] = useState<"list" | "settings">("list");
  const [notifs, setNotifs] = useState<CustomerNotification[] | null>(null);
  const [prefs, setPrefs] = useState<NotificationPref[]>([]);
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    listNotifications(undefined, 40).then(r => setNotifs(r.items ?? [])).catch(setError);
    getPreferences().then(setPrefs).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const prefMap: Record<string, boolean> = {};
  for (const p of prefs) prefMap[`${p.event_key}::${p.channel}`] = p.is_enabled;
  const isOn = (e: string, c: string) => {
    const k = `${e}::${c}`;
    if (k in overrides) return overrides[k];
    if (k in prefMap) return prefMap[k];
    return true;
  };
  const toggle = async (e: string, c: string) => {
    const k = `${e}::${c}`; const next = !isOn(e, c);
    setOverrides(o => ({ ...o, [k]: next })); setBusy(true); setError(null);
    try { await updatePreference(e, c, next); }
    catch (err) { setOverrides(o => ({ ...o, [k]: !next })); setError(err); }
    finally { setBusy(false); }
  };

  const open = async (n: CustomerNotification) => {
    if (n.read_status !== "read") { try { await markRead(n.id); } catch { /* ignore */ } }
    if (n.action_url) window.location.href = n.action_url; else load();
  };

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 0" }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Notifications</h1>
        {tab === "list" && (notifs?.some(n => n.read_status !== "read")) && (
          <button className="co-btn co-btn-secondary" style={{ padding: "6px 12px", fontSize: 13 }}
            onClick={() => markAllRead().then(load).catch(setError)}>
            Mark all read
          </button>
        )}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <button className={`co-btn ${tab === "list" ? "" : "co-btn-secondary"}`}
          style={{ padding: "6px 14px", fontSize: 13 }} onClick={() => setTab("list")}>Inbox</button>
        <button className={`co-btn ${tab === "settings" ? "" : "co-btn-secondary"}`}
          style={{ padding: "6px 14px", fontSize: 13 }} onClick={() => setTab("settings")}>Settings</button>
      </div>

      <ErrorBanner error={error} />

      {tab === "list" && (
        <>
          {!notifs && <div className="co-skeleton" style={{ height: 160 }} />}
          {notifs && notifs.length === 0 && (
            <div className="co-card" style={{ textAlign: "center", padding: 24, color: "#666" }}>
              No notifications yet.
            </div>
          )}
          {notifs?.map(n => {
            const unread = n.read_status !== "read";
            return (
              <div key={n.id} className="co-card" onClick={() => open(n)}
                style={{ marginBottom: 10, cursor: "pointer", display: "flex", gap: 10,
                  background: unread ? "#FFF9F0" : undefined }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", marginTop: 6, flexShrink: 0,
                  background: unread ? STATUS_COLOR(n.severity) : "transparent" }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: unread ? 700 : 600, fontSize: 14, marginBottom: 2 }}>{n.title}</div>
                  <div style={{ fontSize: 13, color: "#444", marginBottom: 3 }}>{n.body}</div>
                  <div style={{ fontSize: 11, color: "#888" }}>{new Date(n.created_at).toLocaleString()}</div>
                </div>
              </div>
            );
          })}
        </>
      )}

      {tab === "settings" && (
        <div className="co-card" style={{ padding: 0 }}>
          <div style={{ padding: "12px 14px", borderBottom: "1px solid #eee", fontSize: 13, color: "#666" }}>
            Choose how you want to be notified. An unset toggle is on by default.
          </div>
          {EVENTS.map(ev => (
            <div key={ev.key} style={{ padding: "12px 14px", borderBottom: "1px solid #f0f0f0" }}>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>{ev.label}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 14 }}>
                {CHANNELS.map(c => {
                  const on = isOn(ev.key, c.key);
                  return (
                    <label key={c.key} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                      <input type="checkbox" checked={on} disabled={busy}
                        onChange={() => toggle(ev.key, c.key)} style={{ width: 16, height: 16 }} />
                      {c.label}
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      <BottomNav />
    </div>
  );
}
