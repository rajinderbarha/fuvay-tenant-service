"use client";
import React, { useEffect, useState } from "react";
import { homeServicesSetupOverviewApi, type HomeServicesSetupOverview } from "../../lib/api";
import { Card, Badge, Btn } from "../shared/ui";
import { StepProgressBar } from "../onboarding/StepProgressBar";
import { ProgressRing } from "../onboarding/ProgressRing";

export function ServicesSetupProgress({ revision }: { revision: unknown }) {
  const [overview, setOverview] = useState<HomeServicesSetupOverview | null>(null);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    homeServicesSetupOverviewApi.getOverview().then(data => {
      if (!cancelled) setOverview(data);
    }).catch(() => { if (!cancelled) { setOverview(null); setFailed(true); } });
    return () => { cancelled = true; };
  }, [revision, retry]);
  const section = overview?.sections.find(item => item.key === "SERVICES_PRICING");
  const complete = section?.status === "complete";
  return <section aria-label="Services onboarding progress">
    <StepProgressBar step={3} total={8} />
    <Card style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 24 }}>
        {overview ? <ProgressRing pct={overview.progress.percentage}
          label="Overall setup completion"
          sublabel={`${overview.progress.completed_required} of ${overview.progress.total_required} required sections complete`}
          tone={overview.progress.percentage === 100 ? "success" : "brand"} />
          : <p role="status">{failed ? "Setup progress is temporarily unavailable." : "Loading setup progress…"}</p>}
        <div style={{ flex: "1 1 280px" }}>
          <h2 style={{ fontSize: 15, margin: "0 0 8px" }}>Services & pricing readiness</h2>
          {section && <Badge variant={complete ? "success" : "warning"}>{complete ? "100% complete" : "In progress"}</Badge>}
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 0 }}>
            {complete ? "Your service setup meets the current readiness checks." : "Choose your services and save pricing here. Final validation and publication happen at Review & Submit after coverage is configured."}
          </p>
          {failed && <Btn variant="secondary" onClick={() => setRetry(n => n + 1)}>Retry progress</Btn>}
        </div>
      </div>
    </Card>
  </section>;
}
