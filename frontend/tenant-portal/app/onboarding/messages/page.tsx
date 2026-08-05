"use client";
/**
 * Messages & Requests — real distinct page (was previously a hash fragment,
 * #messages, on /onboarding/application-status — same root cause as the
 * Submitted Setup bug: no separate page ever existed, so it always rendered
 * Application Status content).
 *
 * HONEST GAP: there is no dedicated two-way admin<->tenant messaging/thread
 * backend in this codebase (checked app.engines.vertical_catalog.service.py
 * and .models.py — no Message/Thread model, no admin-notes-to-tenant
 * endpoint beyond the fields already on the enrollment record itself). This
 * page does NOT invent fake message data. It surfaces the real one-way
 * admin-communication fields that DO exist and are already fetched by
 * tenantApplicationStatusApi.get(): `changes_requested_note`,
 * `rejection_reason`, and the `review_activity` event log. If a real
 * two-way thread endpoint is built later, this page should be repointed to
 * it instead of this reused data.
 */
import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, XCircle, CheckCircle2, RefreshCw, MessageSquare } from "lucide-react";
import { OnboardingShell } from "../../../components/onboarding/OnboardingShell";
import { Card, Btn, Skeleton } from "../../../components/shared/ui";
import { tenantApplicationStatusApi, ServiceOSError, type ApplicationStatus } from "../../../lib/api";

const ACTIVITY_LABEL: Record<string, string> = {
  "enrollment.submitted": "Setup submitted",
  "enrollment.under_review": "Review started",
  "enrollment.changes_requested": "Changes requested",
  "enrollment.approved": "Approved",
  "enrollment.active": "Activated",
  "enrollment.rejected": "Rejected",
  "enrollment.suspended": "Suspended",
};

function fmt(ts: string | null): string {
  if (!ts) return "";
  return new Date(ts).toLocaleString(undefined, { month: "short", day: "2-digit", year: "numeric", hour: "numeric", minute: "2-digit" });
}

export default function MessagesPage() {
  const [data, setData] = useState<ApplicationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    tenantApplicationStatusApi.get()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your messages."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <OnboardingShell activeNav="messages" restricted>
        <Skeleton height={64} style={{ marginBottom: 20 }} />
        <Skeleton height={240} />
      </OnboardingShell>
    );
  }

  if (error || !data) {
    return (
      <OnboardingShell activeNav="messages" restricted>
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your messages.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14} />} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </OnboardingShell>
    );
  }

  const hasNote = Boolean(data.changes_requested_note || data.rejection_reason);

  return (
    <OnboardingShell activeNav="messages" restricted>
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "var(--brand)", margin: "0 0 6px" }}>TENANT ONBOARDING</p>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Messages &amp; requests</h1>
        <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
          Communication from our review team about your application.
        </p>
      </div>

      {data.changes_requested_note && (
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 12, padding: 12, borderRadius: 12, background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
            <AlertTriangle size={18} style={{ color: "var(--warning-text)", flexShrink: 0 }} />
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--warning-text)", margin: "0 0 4px" }}>Changes requested</p>
              <p style={{ fontSize: 13, color: "var(--warning-text)", margin: 0 }}>{data.changes_requested_note}</p>
            </div>
          </div>
        </Card>
      )}

      {data.rejection_reason && (
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 12, padding: 12, borderRadius: 12, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
            <XCircle size={18} style={{ color: "var(--danger-text)", flexShrink: 0 }} />
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--danger-text)", margin: "0 0 4px" }}>Application rejected</p>
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{data.rejection_reason}</p>
            </div>
          </div>
        </Card>
      )}

      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <MessageSquare size={16} style={{ color: "var(--text-tertiary)" }} />
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Review activity</h3>
        </div>
        {data.review_activity.length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No review activity yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {data.review_activity.map((ev, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
                  <CheckCircle2 size={14} style={{ color: "var(--success-text)" }} />
                  {ACTIVITY_LABEL[ev.action] ?? ev.action}
                </span>
                <span style={{ fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{fmt(ev.occurred_at)}</span>
              </div>
            ))}
          </div>
        )}
        {!hasNote && data.review_activity.length === 0 && (
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 12 }}>
            No messages from our team yet. You&apos;ll be notified here as soon as there&apos;s an update.
          </p>
        )}
      </Card>
    </OnboardingShell>
  );
}
