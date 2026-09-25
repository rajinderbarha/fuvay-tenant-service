"use client";

import { usePathname, useRouter } from "next/navigation";
import { useJobAlerts } from "../../hooks/useJobAlerts";
import { JobAlertPopup } from "./JobAlertPopup";

/** Authenticated provider-wide host for assignment and visit urgency alerts. */
export function GlobalJobAlerts() {
  const router = useRouter();
  const pathname = usePathname();
  const alerts = useJobAlerts();
  const closeAndOpen = (path: string) => {
    alerts.dismiss();
    router.push(path);
  };

  // The bookings and dispatch workspaces already keep their queues live. A
  // blocking global dialog on top of those action surfaces interrupts the task
  // the alert is asking the provider to perform.
  const providerIsManagingJobs = pathname.startsWith("/home-services/bookings-jobs")
    || pathname.startsWith("/home-services/dispatch");
  if (providerIsManagingJobs) return null;

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
