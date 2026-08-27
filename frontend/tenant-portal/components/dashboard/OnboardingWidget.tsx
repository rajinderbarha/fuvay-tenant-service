"use client";
import React, { useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, Btn, Skeleton } from "../shared/ui";
import { providerOnboardingApi } from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";
import { CheckCircle2, AlertCircle, ChevronRight, RefreshCw, ClipboardList } from "lucide-react";

export function OnboardingWidget() {
  const router = useRouter();
  const status = useApi(useCallback(() => providerOnboardingApi.getStatus(), []));
  const refreshAction = useAction(useCallback(async () => {
    await providerOnboardingApi.refresh();
    status.refetch();
  }, [status]));

  const s = status.data;

  if (status.loading) {
    return (
      <Card>
        <Skeleton height={90}/>
      </Card>
    );
  }

  if (status.error) {
    return (
      <Card>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
          gap: 12, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <AlertCircle size={16} style={{ color: "var(--danger)" }}/>
            <span style={{ fontSize: 13, color: "var(--danger)" }}>Onboarding status unavailable</span>
          </div>
          <Btn size="xs" variant="ghost" onClick={status.refetch}>Retry</Btn>
        </div>
      </Card>
    );
  }

  if (!s) return null;

  if (s.onboarding_ready) {
    return (
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
          justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <CheckCircle2 size={22} style={{ color: "var(--success)", flexShrink: 0 }}/>
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--success)", margin: 0 }}>
                Onboarding complete
              </p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "1px 0 0" }}>
                Your business is ready to accept bookings
              </p>
            </div>
          </div>
          <Btn size="xs" variant="ghost" onClick={() => router.push("/tenant/home-services/setup")}>
            View Checklist <ChevronRight size={11}/>
          </Btn>
        </div>
      </Card>
    );
  }

  const mainBlocker = s.blockers[0];
  const pct = s.progress_percentage;

  return (
    <Card>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {/* Header row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <ClipboardList size={15} style={{ color: "var(--accent)" }}/>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              Onboarding — {pct}%
            </span>
          </div>
          <Btn size="xs" variant="ghost" loading={refreshAction.loading}
            onClick={() => refreshAction.execute()}>
            <RefreshCw size={11}/>
          </Btn>
        </div>

        {/* Progress bar */}
        <div style={{ height: 6, background: "var(--surface-sunken)", borderRadius: 99,
          overflow: "hidden", border: "1px solid var(--border)" }}>
          <div style={{ height: "100%", borderRadius: 99,
            width: `${Math.max(0, Math.min(100, pct))}%`,
            background: pct >= 60 ? "var(--warning)" : "#2563eb",
            transition: "width 0.4s" }}/>
        </div>

        {/* Main blocker */}
        {mainBlocker && (
          <p style={{ fontSize: 11, color: "var(--danger)", margin: 0 }}>
            <AlertCircle size={11} style={{ display: "inline", marginRight: 4 }}/>
            {mainBlocker.message}
          </p>
        )}

        {/* Next action */}
        {s.next_action && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
            gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
              Next: {s.next_action.title}
            </span>
            <Btn size="xs" variant="primary" onClick={() => router.push(s.next_action!.route)}>
              {s.next_action.action_label} <ChevronRight size={11}/>
            </Btn>
          </div>
        )}

        {/* Footer */}
        <div style={{ display: "flex", gap: 8, paddingTop: 2 }}>
          <Btn size="xs" variant="ghost" onClick={() => router.push("/tenant/home-services/setup")}>
            View Full Checklist
          </Btn>
        </div>
      </div>
    </Card>
  );
}
