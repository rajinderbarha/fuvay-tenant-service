"use client";
/**
 * Submitted Setup — real distinct page (was previously a hash fragment,
 * #submitted-setup, on /onboarding/application-status, which is exactly why
 * clicking "Submitted Setup" in the restricted sidebar rendered Application
 * Status content: it WAS Application Status content, same route, no
 * separate page ever existed).
 *
 * Reuses the real `snapshot` field already returned by
 * tenantApplicationStatusApi.get() (GET .../application-status) — no new
 * backend endpoint invented; this is the same immutable submitted-version
 * data the Application Status page already fetches and partially renders,
 * just given its own dedicated, deep-linkable, refresh-safe route.
 */
import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, RefreshCw, Lock } from "lucide-react";
import { OnboardingShell } from "../../../components/onboarding/OnboardingShell";
import { Card, Badge, Btn, Skeleton } from "../../../components/shared/ui";
import { tenantApplicationStatusApi, ServiceOSError, type ApplicationStatus } from "../../../lib/api";

export default function SubmittedSetupPage() {
  const router = useRouter();
  const [data, setData] = useState<ApplicationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    tenantApplicationStatusApi.get()
      .then(d => {
        setData(d);
        // Same lifecycle guard as Application Status: a tenant that hasn't
        // submitted yet has no submitted snapshot to show.
        if (d.status === "draft_setup" || d.status === "draft") {
          router.replace("/tenant/home-services/setup/overview");
        }
      })
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your submitted setup."))
      .finally(() => setLoading(false));
  }, [router]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <OnboardingShell activeNav="submitted-setup" restricted>
        <Skeleton height={64} style={{ marginBottom: 20 }} />
        <Skeleton height={320} />
      </OnboardingShell>
    );
  }

  if (error || !data) {
    return (
      <OnboardingShell activeNav="submitted-setup" restricted>
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your submitted setup.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14} />} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </OnboardingShell>
    );
  }

  return (
    <OnboardingShell activeNav="submitted-setup" restricted>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "var(--brand)", margin: "0 0 6px" }}>TENANT ONBOARDING</p>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Submitted setup</h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
            The exact version submitted for review — Version {data.submission_details.version}, submission {data.submission_details.submission_id}.
          </p>
        </div>
        {data.is_locked && <Badge variant="muted" size="lg" dot><Lock size={12} style={{ marginRight: 4 }} />Locked</Badge>}
      </div>

      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <FileText size={16} style={{ color: "var(--text-tertiary)" }} />
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Submitted sections</h3>
        </div>
        <div style={{ border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
          {data.snapshot.map((s, i) => (
            <div key={s.key} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 14px", gap: 10,
              borderBottom: i < data.snapshot.length - 1 ? "1px solid var(--border)" : "none", flexWrap: "wrap",
            }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{s.label}</span>
              <Badge variant={s.status === "complete" ? "success" : "muted"} size="sm">
                {s.status === "complete" ? "Complete" : s.status === "optional" ? "Optional" : "Incomplete"}
              </Badge>
            </div>
          ))}
        </div>
      </Card>

      <div style={{ marginTop: 20 }}>
        <Btn variant="secondary" onClick={() => router.push("/onboarding/application-status")}>
          Back to application status
        </Btn>
      </div>
    </OnboardingShell>
  );
}
