"use client";
/**
 * Provider complaint detail -- redirects into the Complaints & Resolution
 * Center with the case open. See ../page.tsx for why the separate provider
 * complaint pages were retired: notifications for new complaints, customer
 * replies and accepted resolutions all linked here, so the provider landed on
 * a copy with no deadlines and remedies the server now refuses.
 */
import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function ProviderComplaintDetailRedirect() {
  const router = useRouter();
  const params = useParams<{ complaint_id: string }>();
  const id = params?.complaint_id;

  useEffect(() => {
    router.replace(id ? `/home-services/complaints/${id}` : "/home-services/complaints");
  }, [id, router]);

  return null;
}
