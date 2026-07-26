"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Merged into the canonical Provider Matching page (MODULE-L5-58) as its
// "Diagnostics" tab -- Provider Matching and Matching Diagnostics are now one
// page with four tabs (Diagnostics / Live Decisions / Policy Reference /
// Audit) so matching config/monitoring never lives in two disconnected
// places. Redirecting so old links/bookmarks keep working.
export default function LegacyMatchingDiagnosticsRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/admin/home-services/provider-matching"); }, [router]);
  return null;
}
