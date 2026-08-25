"use client";
/**
 * Rework requests — folded into the Customer Remedies workspace.
 *
 * This page was an orphan: nothing in the sidebar, the dashboard or any other
 * page linked to `/provider/rework-requests`, so the only way to reach it was
 * to type the URL. It also offered only "start" and "complete" — never
 * `schedule`, even though `POST /v1/provider/rework-requests/{id}/schedule`
 * exists and is the step that tells the customer when you are coming.
 *
 * Rework is the third leg of the same complaint-remedy flow as refunds and
 * warranty claims (accepting a rework resolution spawns a
 * ServiceReworkRequest), so it now lives beside them under the
 * "Refunds & Warranty" sidebar item. Redirecting keeps any existing bookmark
 * working instead of leaving a second, diverging copy of the surface.
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ProviderReworkRequestsPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/provider/refund-requests"); }, [router]);
  return null;
}
