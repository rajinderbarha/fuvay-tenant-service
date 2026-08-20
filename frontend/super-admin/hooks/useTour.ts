"use client";

import { useCallback, useEffect, useState } from "react";

export interface TourStep {
  id: string;
  targetId: string;
  title: string;
  description: string;
  position: "bottom" | "right" | "left" | "top";
}

// Targets are current AdminLayout IDs. Content intentionally describes the
// canonical native Home Services flow and does not revive retired wallets,
// health scores, package approvals, or commission configuration surfaces.
export const TOUR_STEPS: TourStep[] = [
  { id: "step-1", targetId: "nav-dashboard", title: "Command Center", description: "Your daily starting point for operational controls, provider readiness, finance exceptions, and platform risk.", position: "right" },
  { id: "step-2", targetId: "kpi-at-risk", title: "Provider attention", description: "Providers blocked by bookability, complaint SLA, credit, or deduction controls. Open the provider workspace to see the exact reason.", position: "bottom" },
  { id: "step-3", targetId: "nav-customers", title: "Customer operations", description: "Search customers, inspect service history, privacy controls, complaints, and native booking activity.", position: "right" },
  { id: "step-4", targetId: "nav-home-services", title: "Home Services operations", description: "Open providers, native bookings and jobs, finance, matching, service areas, and the current catalog workspace.", position: "right" },
  { id: "step-5", targetId: "nav-notifications", title: "Notification control", description: "Manage templates, channel configuration, delivery health, suppression, and auditable notification settings.", position: "right" },
  { id: "step-6", targetId: "nav-security", title: "Security & Threats", description: "Investigate threats, active sessions, IP controls, failed logins, and security policy state.", position: "right" },
  { id: "step-7", targetId: "nav-compliance", title: "Compliance", description: "Process privacy and data requests with their real status, due dates, evidence, and audit trail.", position: "right" },
];

const TOUR_KEY = "serviceos-admin-tour-done";

export function useTour() {
  const [active, setActive] = useState(false);
  const [step, setStep] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const disabledByEnv = process.env.NEXT_PUBLIC_DISABLE_TOUR_FOR_E2E === "true";
    const disabledByFlag = typeof window !== "undefined" && localStorage.getItem("serviceos_disable_tour_e2e") === "true";
    if (disabledByEnv || disabledByFlag) return;
    if (!localStorage.getItem(TOUR_KEY)) setActive(true);
  }, []);

  const complete = useCallback(() => {
    setActive(false);
    localStorage.setItem(TOUR_KEY, "true");
  }, []);

  const next = useCallback(() => {
    setStep(current => {
      if (current < TOUR_STEPS.length - 1) return current + 1;
      complete();
      return current;
    });
  }, [complete]);
  const prev = useCallback(() => setStep(current => Math.max(0, current - 1)), []);
  const restart = useCallback(() => {
    localStorage.removeItem(TOUR_KEY);
    setStep(0);
    setActive(true);
  }, []);

  return {
    active, step, mounted, currentStep: TOUR_STEPS[step], totalSteps: TOUR_STEPS.length,
    next, prev, skip: complete, complete, restart, isFirst: step === 0,
    isLast: step === TOUR_STEPS.length - 1,
  };
}
