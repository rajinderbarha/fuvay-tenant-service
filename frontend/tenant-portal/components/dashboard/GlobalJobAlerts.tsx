"use client";

import { useRouter } from "next/navigation";
import { useJobAlerts } from "../../hooks/useJobAlerts";
import { JobAlertPopup } from "./JobAlertPopup";

/** Authenticated provider-wide host for assignment and visit urgency alerts. */
export function GlobalJobAlerts() {
  const router = useRouter();
  const alerts = useJobAlerts();
  const closeAndOpen = (path: string) => {
    alerts.dismiss();
    router.push(path);
  };

  return <JobAlertPopup
    alerts={alerts.pending}
    newTotal={alerts.newTotal}
    departureTotal={alerts.departureTotal}
    delayedTotal={alerts.delayedTotal}
    onDismiss={alerts.dismiss}
    onOpenJob={(jobId) => closeAndOpen(`/home-services/bookings-jobs?job_id=${jobId}`)}
    onSeeAllDelayed={() => closeAndOpen("/home-services/bookings-jobs?sla=ATTENTION")}
    onOpenBoard={() => closeAndOpen("/home-services/bookings-jobs")}
  />;
}
