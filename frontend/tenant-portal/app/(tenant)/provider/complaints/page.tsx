"use client";
/**
 * Complaints -- folded into the Complaints & Resolution Center.
 *
 * This older queue had drifted from the workspace in the sidebar
 * (/home-services/complaints): it showed no resolution deadlines, and its
 * detail page offered remedies the engine cannot carry out ("reassign
 * provider") and money-based settlements that paid the customer nothing.
 * Every provider notification also linked here, so providers acted on the
 * stale copy. Redirecting keeps old links working without a second surface.
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ProviderComplaintsPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/home-services/complaints"); }, [router]);
  return null;
}
