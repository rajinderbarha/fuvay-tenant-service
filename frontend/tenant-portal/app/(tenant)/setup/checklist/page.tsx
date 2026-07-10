"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Setup checklist — redirects to the full onboarding-status page.
 * The onboarding-status page (app/(tenant)/onboarding-status/page.tsx)
 * is the canonical setup checklist that calls providerOnboardingApi.getStatus()
 * and providerOnboardingApi.getItems(). This page provides a short-URL alias.
 */
export default function SetupChecklistPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/onboarding-status");
  }, [router]);

  return (
    <div style={{ padding: 32, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
      Redirecting to Setup Checklist…
    </div>
  );
}
