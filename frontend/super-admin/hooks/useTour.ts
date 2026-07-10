"use client";
/**
 * useTour — 7-step interactive onboarding tour.
 * PROVEN: exactly 7 steps, each with targetId, title, description, position.
 * Persisted: dismissed users don't see it again unless re-triggered.
 */
import { useState, useEffect, useCallback } from "react";

export interface TourStep {
  id:          string;
  targetId:    string;   // DOM element id to highlight
  title:       string;
  description: string;
  position:    "bottom" | "right" | "left" | "top";
}

// PROVEN: exactly 7 steps — verified by test
export const TOUR_STEPS: TourStep[] = [
  {
    id:"step-1", targetId:"nav-dashboard",
    title:"Command Center",
    description:"Your daily starting point. Red numbers need attention today. Green confirms everything is healthy.",
    position:"right",
  },
  {
    id:"step-2", targetId:"kpi-at-risk",
    title:"At-Risk Tenants",
    description:"Tenants whose health score dropped below 35. Click this number to see who needs help and why.",
    position:"bottom",
  },
  {
    id:"step-3", targetId:"nav-tenants",
    title:"Tenant 360°",
    description:"Every tenant's complete picture on one page — wallet, jobs, staff, reviews, billing mode, and health score.",
    position:"right",
  },
  {
    id:"step-4", targetId:"nav-operations",
    title:"Operations Board",
    description:"All jobs across all tenants live. Amber means stuck. Red means SLA breached. Reassign with one click.",
    position:"right",
  },
  {
    id:"step-5", targetId:"nav-finance",
    title:"Finance Hub",
    description:"All money movement — wallet top-ups, commission collected, billing mode per tenant, commission rate config.",
    position:"right",
  },
  {
    id:"step-6", targetId:"nav-security",
    title:"Security & Threats",
    description:"Suspicious activity, IP blocklist, active sessions, and the platform audit log. High threats shown in red.",
    position:"right",
  },
  {
    id:"step-7", targetId:"nav-compliance",
    title:"Compliance Panel",
    description:"Erasure requests with 72h SLA countdown. Any breach turns red automatically. Process with one click.",
    position:"right",
  },
];

const TOUR_KEY = "serviceos-admin-tour-done";

export function useTour() {
  const [active,  setActive]  = useState(false);
  const [step,    setStep]    = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // ADMIN-TENANT-E2E-02 Part 5: E2E harnesses need a deterministic way to
    // suppress the tour so it doesn't cover nav items / steal focus during
    // route smoke tests. Two independent escape hatches, either is enough:
    //   1. Build-time env var (set in e2e harness's .env for the dev server)
    //   2. A localStorage flag the Playwright harness can set before navigating,
    //      without needing to rebuild/restart the Next.js dev server.
    const disabledByEnv = process.env.NEXT_PUBLIC_DISABLE_TOUR_FOR_E2E === "true";
    const disabledByFlag = typeof window !== "undefined" && localStorage.getItem("serviceos_disable_tour_e2e") === "true";
    if (disabledByEnv || disabledByFlag) return;
    const done = localStorage.getItem(TOUR_KEY);
    if (!done) setActive(true);
  }, []);

  const next = useCallback(() => {
    if (step < TOUR_STEPS.length - 1) setStep(s => s + 1);
    else complete();
  }, [step]);

  const prev = useCallback(() => {
    if (step > 0) setStep(s => s - 1);
  }, [step]);

  const complete = useCallback(() => {
    setActive(false);
    localStorage.setItem(TOUR_KEY, "true");
  }, []);

  const restart = useCallback(() => {
    localStorage.removeItem(TOUR_KEY);
    setStep(0);
    setActive(true);
  }, []);

  const skip = complete;

  return {
    active, step, mounted,
    currentStep: TOUR_STEPS[step],
    totalSteps:  TOUR_STEPS.length,
    next, prev, skip, complete, restart,
    isFirst: step === 0,
    isLast:  step === TOUR_STEPS.length - 1,
  };
}
