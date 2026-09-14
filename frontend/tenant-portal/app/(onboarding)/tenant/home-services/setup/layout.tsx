"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RequireSession } from "../../../../../components/shared/RequireSession";
import { homeServicesSetupOverviewApi } from "../../../../../lib/api";

const EDITABLE_DESTINATIONS = new Set([
  "HOME_SERVICES_SETUP_OVERVIEW",
  "HOME_SERVICES_CHANGES_REQUESTED",
]);

function SetupLifecycleGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<"checking" | "editable" | "unavailable">("checking");
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    setState("checking");
    setAttempt(value => value + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    homeServicesSetupOverviewApi.getRouting<{ next_destination: string }>()
      .then(({ next_destination }) => {
        if (cancelled) return;
        if (EDITABLE_DESTINATIONS.has(next_destination)) {
          setState("editable");
          return;
        }
        // Completed setup is not a second service editor. The operational
        // catalog is the only place to add/publish services after activation.
        const destination = next_destination === "HOME_SERVICES_UNDER_REVIEW"
          ? "/onboarding/application-status"
          : next_destination === "HOME_SERVICES_ACTIVATION"
            ? "/onboarding/activation-center"
            : "/dashboard";
        router.replace(destination);
      })
      .catch(() => { if (!cancelled) setState("unavailable"); });
    return () => { cancelled = true; };
  }, [attempt, router]);

  if (state === "editable") return <>{children}</>;
  if (state === "unavailable") return (
    <div role="alert" style={{ padding: 24, textAlign: "center" }}>
      <p>We couldn&apos;t verify your setup status. No setup pages are available until it can be checked.</p>
      <button type="button" onClick={retry}>Try again</button>
    </div>
  );
  return <div role="status" aria-busy="true" aria-label="Checking setup access" />;
}

export default function HomeServicesSetupLayout({ children }: { children: React.ReactNode }) {
  return <RequireSession><SetupLifecycleGate>{children}</SetupLifecycleGate></RequireSession>;
}
