"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { serviceJobAssignmentApi, type DashboardAlert } from "../lib/api";

/** Polling keeps the queue current without making the alert surface feel unstable. */
const POLL_MS = 30_000;
const REMINDER_SNOOZE_MS = 15 * 60_000;
const MAX_REMINDER_AGE_MS = 24 * 60 * 60_000;

/** Dismissals survive route changes and reloads, but expire so unresolved work
 * can be escalated again. A different alert phase always receives a new key. */
const SNOOZE_KEY = "fuvay.provider.job-alerts.snoozed.v2";

function readSnoozes(): Map<string, number> {
  if (typeof window === "undefined") return new Map();
  try {
    const raw = window.localStorage.getItem(SNOOZE_KEY);
    const parsed = raw ? JSON.parse(raw) as Record<string, number> : {};
    const now = Date.now();
    return new Map(Object.entries(parsed).filter(([, until]) =>
      Number.isFinite(until) && until > now && until <= now + MAX_REMINDER_AGE_MS,
    ));
  } catch {
    return new Map();
  }
}

function writeSnoozes(snoozes: Map<string, number>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(SNOOZE_KEY, JSON.stringify(Object.fromEntries(snoozes)));
  } catch {
    /* Storage failure must never block the provider workspace. */
  }
}

/** Stable within one operational phase. Poll-generated wording and minute counts
 * must not create a brand-new modal every refresh. Meaningful escalations do. */
export function alertKey(alert: DashboardAlert): string {
  const kind = alert.alert_kind
    ?? (alert.assignment_required ? "assignment" : alert.departure_required ? "departure" : "delayed");
  if (kind === "assignment") return `${alert.job_id}:assignment:${alert.assignment_overdue ? "overdue" : "new"}`;
  if (kind === "departure") return `${alert.job_id}:departure:${alert.scheduled_date ?? "date"}:${alert.scheduled_time_window ?? "slot"}`;
  const late = Math.max(0, alert.minutes_late ?? 0);
  const milestone = late < 60 ? "under-1h" : late < 240 ? "1h" : late < 1440 ? "4h" : `${Math.floor(late / 1440)}d`;
  return `${alert.job_id}:delayed:${milestone}`;
}

export interface JobAlertsState {
  /** Alerts due to interrupt now. Empty means no popup. */
  pending: DashboardAlert[];
  newTotal: number;
  departureTotal: number;
  delayedTotal: number;
  /** Snoozes the current alert phases without hiding their queue counts. */
  dismiss: () => void;
}

/**
 * Feeds the provider-wide interrupting popup.
 *
 * It deliberately does not ask the server to raise notifications on a background poll
 *    (`notify: false`). The GET raises `job.delayed` as a side effect, and a page left
 *    open overnight should not be what decides when a provider is notified. The first
 *    authenticated portal load does raise them, because that is a person actually arriving.
 */
export function useJobAlerts(): JobAlertsState {
  const [pending, setPending] = useState<DashboardAlert[]>([]);
  const [newTotal, setNewTotal] = useState(0);
  const [departureTotal, setDepartureTotal] = useState(0);
  const [delayedTotal, setDelayedTotal] = useState(0);
  const snoozesRef = useRef<Map<string, number>>(new Map());
  const sinceRef = useRef<string | null>(null);
  const firstLoadRef = useRef(true);
  const requestInFlightRef = useRef(false);

  useEffect(() => {
    snoozesRef.current = readSnoozes();
  }, []);

  const load = useCallback(async () => {
    if (requestInFlightRef.current || (typeof document !== "undefined" && document.visibilityState !== "visible")) return;
    requestInFlightRef.current = true;
    try {
      const res = await serviceJobAssignmentApi.dashboardAlerts({
        since: sinceRef.current,
        notify: firstLoadRef.current,
      });
      firstLoadRef.current = false;
      sinceRef.current = res.as_of ?? null;

      setNewTotal(res.new_job_total ?? 0);
      setDepartureTotal(res.departure_total ?? 0);
      setDelayedTotal(res.delayed_total ?? 0);

      const all = [
        ...(res.departure_jobs ?? []),
        ...(res.delayed_jobs ?? []),
        ...(res.new_jobs ?? []),
      ];
      const now = Date.now();
      const currentKeys = new Set(all.map(alertKey));
      for (const [key, until] of snoozesRef.current) {
        if (until <= now || !currentKeys.has(key)) snoozesRef.current.delete(key);
      }
      writeSnoozes(snoozesRef.current);
      const next = all.filter(alert => (snoozesRef.current.get(alertKey(alert)) ?? 0) <= now);
      setPending(current => {
        const currentSignature = current.map(alertKey).join("|");
        const nextSignature = next.map(alertKey).join("|");
        return currentSignature === nextSignature ? current : next;
      });
    } catch {
      // Silent: alerts are an addition to the dashboard, and a failed poll must not
      // replace a working page with an error. The counts simply stay as they were.
    } finally {
      requestInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => { void load(); }, POLL_MS);
    const resume = () => { if (document.visibilityState === "visible") void load(); };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("online", resume);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("online", resume);
    };
  }, [load]);

  const dismiss = useCallback(() => {
    setPending(current => {
      const until = Date.now() + REMINDER_SNOOZE_MS;
      for (const alert of current) {
        snoozesRef.current.set(alertKey(alert), until);
      }
      writeSnoozes(snoozesRef.current);
      return [];
    });
  }, []);

  return { pending, newTotal, departureTotal, delayedTotal, dismiss };
}
