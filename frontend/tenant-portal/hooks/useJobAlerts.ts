"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { serviceJobAssignmentApi, type DashboardAlert } from "../lib/api";

/** How often the dashboard asks. A new job should surface while the provider is still
 * looking at the screen, not on their next visit. */
const POLL_MS = 10_000;
const OFFER_SNOOZE_MS = 30_000;

/** Delayed-job alerts are remembered for this session; unassigned offers are
 * only snoozed for 30 seconds and must reappear until action is taken. */
const SEEN_KEY = "fuvay.dashboard.alerts.seen";

function readSeen(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.sessionStorage.getItem(SEEN_KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    // A corrupt or unavailable store must not stop the dashboard loading. Worst case
    // the provider sees an alert twice, which is better than the page failing.
    return new Set();
  }
}

function writeSeen(seen: Set<string>): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(SEEN_KEY, JSON.stringify([...seen]));
  } catch {
    /* Ignored for the same reason as above. */
  }
}

/** One alert is one job in one state, so a job going from late to later re-alerts, but a
 * refresh with nothing changed does not. */
function alertKey(alert: DashboardAlert): string {
  return `${alert.job_id}:${alert.tone}:${alert.lateness_label ?? "new"}`;
}

export interface JobAlertsState {
  /** Alerts due to interrupt now. Empty means no popup. */
  pending: DashboardAlert[];
  newTotal: number;
  delayedTotal: number;
  /** Snoozes offers briefly and marks delayed alerts seen this session. */
  dismiss: () => void;
}

/**
 * Feeds the dashboard's interrupting popup.
 *
 * It deliberately does not ask the server to raise notifications on a background poll
 *    (`notify: false`). The GET raises `job.delayed` as a side effect, and a page left
 *    open overnight should not be what decides when a provider is notified. The first
 *    load of the dashboard does raise them, because that is a person actually arriving.
 */
export function useJobAlerts(): JobAlertsState {
  const [pending, setPending] = useState<DashboardAlert[]>([]);
  const [newTotal, setNewTotal] = useState(0);
  const [delayedTotal, setDelayedTotal] = useState(0);
  const seenRef = useRef<Set<string>>(new Set());
  const snoozedOffersRef = useRef<Map<string, number>>(new Map());
  const sinceRef = useRef<string | null>(null);
  const firstLoadRef = useRef(true);

  useEffect(() => {
    seenRef.current = readSeen();
  }, []);

  const load = useCallback(async () => {
    try {
      const res = await serviceJobAssignmentApi.dashboardAlerts({
        since: sinceRef.current,
        notify: firstLoadRef.current,
      });
      firstLoadRef.current = false;
      sinceRef.current = res.as_of ?? null;

      setNewTotal(res.new_job_total ?? 0);
      setDelayedTotal(res.delayed_total ?? 0);

      const all = [...(res.delayed_jobs ?? []), ...(res.new_jobs ?? [])];
      setPending(all.filter(alert => alert.tone === "success"
        ? (snoozedOffersRef.current.get(alert.job_id) ?? 0) <= Date.now()
        : !seenRef.current.has(alertKey(alert))));
    } catch {
      // Silent: alerts are an addition to the dashboard, and a failed poll must not
      // replace a working page with an error. The counts simply stay as they were.
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => { void load(); }, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  const dismiss = useCallback(() => {
    setPending(current => {
      const seen = new Set(seenRef.current);
      for (const alert of current) {
        if (alert.tone === "success") {
          snoozedOffersRef.current.set(alert.job_id, Date.now() + OFFER_SNOOZE_MS);
        } else {
          seen.add(alertKey(alert));
        }
      }
      seenRef.current = seen;
      writeSeen(seen);
      return [];
    });
  }, []);

  return { pending, newTotal, delayedTotal, dismiss };
}
