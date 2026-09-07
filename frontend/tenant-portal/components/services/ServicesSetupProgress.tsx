"use client";
import React, { useEffect, useState } from "react";
import { homeServicesSetupOverviewApi, type HomeServicesSetupOverview } from "../../lib/api";
import { Card, Badge, Btn } from "../shared/ui";
import { StepProgressBar } from "../onboarding/StepProgressBar";
import { ProgressRing } from "../onboarding/ProgressRing";

export function ServicesSetupProgress({ revision, consultationFee }: { revision: unknown; consultationFee?: number | null }) {
  const [overview, setOverview] = useState<HomeServicesSetupOverview | null>(null);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    setOverview(null);
    homeServicesSetupOverviewApi.getOverview().then(data => {
      if (!cancelled) setOverview(data);
    }).catch(() => { if (!cancelled) { setOverview(null); setFailed(true); } });
    return () => { cancelled = true; };
  }, [revision, consultationFee, retry]);
  const section = overview?.sections.find(item => item.key === "SERVICES_PRICING");
  const complete = section?.status === "complete";
  const percentage = complete ? 100 : section?.percentage ?? 0;
  return <section aria-label="Services onboarding progress">
    <StepProgressBar step={3} total={8} />
    <Card style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 24 }}>
        {overview && section ? <ProgressRing pct={percentage}
          label="Service step completion"
          sublabel={`${section.configured_count ?? (complete ? 1 : 0)} of ${section.enabled_count ?? 1} enabled services configured`}
          tone={complete ? "success" : "brand"} />
          : <p role="status">{failed ? "Setup progress is temporarily unavailable." : "Loading setup progress…"}</p>}
        <div style={{ flex: "1 1 280px" }}>
          <h2 style={{ fontSize: 15, margin: "0 0 8px" }}>Services & pricing readiness</h2>
          {section && <Badge variant={complete ? "success" : "warning"}>{complete ? "100% complete" : "In progress"}</Badge>}
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 0 }}>
            {complete ? "Service setup is 100% complete. Save & continue to your technician seat plan." : "Configure every enabled service and save your changes. Coverage and business hours are completed later; publication happens at Review & Submit."}
          </p>
          {!!section?.blocking_reasons?.length && <ul>{section.blocking_reasons.map((reason, index) => <li key={`${reason.code}-${index}`}>{reason.message}</li>)}</ul>}
          {overview && <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>Overall onboarding: {overview.progress.percentage}% ({overview.progress.completed_required} of {overview.progress.total_required} required sections complete). This is separate from this service step.</p>}
          {failed && <Btn variant="secondary" onClick={() => setRetry(n => n + 1)}>Retry progress</Btn>}
        </div>
      </div>
    </Card>
  </section>;
}
