"use client";
import { useCallback } from "react";
import {
  providerStatusApi,
  homeServicesSetupOverviewApi,
  type HomeServicesSetupSection,
} from "../lib/api";
import { useApi } from "./useApi";

// ── Setup wizard step definitions ───────────────────────────────────────────
// Relocated verbatim from components/layout/TenantLayout.tsx (SETUP_STEPS +
// isDone()) so the same real completion logic can be computed once and
// reused by TenantLayout (nav filtering), the Dashboard page (first-time
// banner) and the Profile page (setup-access section) without triplicating
// the 5 underlying API calls. `icon` is a lucide-react icon *name* (not a
// JSX element) so this file stays a plain .ts hook — each consumer maps the
// name to its own <Icon/> the way lib/nav-config.ts already does.
export const SETUP_STEP_DEFS = [
  { key: "profile_complete",        label: "Business Profile",       desc: "Add business name, GST, address",           href: "/profile",                   icon: "Zap" },
  { key: "credits_available",       label: "Usage Credits",          desc: "Maintain credits for completed-job charges", href: "/home-services/finance?tab=usage-credits", icon: "CreditCard" },
  { key: "technician_seats_ok",     label: "Technician Seats",       desc: "Buy a top-up plan covering your technicians", href: "/home-services/finance", icon: "Shield" },
  { key: "service_areas_count",     label: "Coverage Pincodes",      desc: "Add at least one coverage pincode",         href: "/business/coverage-hours",     icon: "ArrowRight" },
  { key: "active_services_count",   label: "Enable a Service",       desc: "Enable and price a service",                href: "/home-services/services",     icon: "Zap" },
  { key: "coverage_configured",     label: "Service Coverage",       desc: "Set types, brands & job types",             href: "/home-services/services",     icon: "Shield" },
  { key: "staff_count",             label: "Add Technician",         desc: "Add at least one technician",               href: "/home-services/team",         icon: "Users2" },
  { key: "availability_configured", label: "Business Hours",          desc: "Set working hours",                         href: "/tenant/home-services/setup/coverage-availability",  icon: "CalendarCheck" },
  { key: "documents_submitted",     label: "Documents",              desc: "Submit required business documents",        href: "/documents",                  icon: "FileText" },
] as const;

export type SetupStepKey = typeof SETUP_STEP_DEFS[number]["key"];
export type SetupStep = typeof SETUP_STEP_DEFS[number] & { done: boolean };

export interface SetupStatus {
  steps: SetupStep[];
  doneCount: number;
  total: number;
  isComplete: boolean;
  isBookable: boolean;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useSetupStatus(): SetupStatus {
  const statusApi = useApi(useCallback(() => providerStatusApi.get(), []), []);
  const overviewApi = useApi(
    useCallback(() => homeServicesSetupOverviewApi.getOverview(), []),
    [],
  );

  const s        = statusApi.data;
  const blockers = [...(s?.visibility_blockers ?? []), ...(s?.bookability_blockers ?? [])];
  const sections = overviewApi.data?.sections ?? [];
  const section = (key: string): HomeServicesSetupSection | undefined =>
    sections.find(item => item.key === key);
  const isSectionComplete = (key: string): boolean => section(key)?.status === "complete";
  const metric = (key: string, field: string): number => {
    const raw = section(key)?.[field];
    return typeof raw === "number" && Number.isFinite(raw) ? raw : 0;
  };
  const hasBlocker = (...codes: string[]) => blockers.some(blocker => {
    const normalized = String(blocker.code ?? "").trim().toUpperCase();
    return codes.includes(normalized);
  });

  function isDone(key: string): boolean {
    switch (key) {
      case "profile_complete":        return isSectionComplete("BUSINESS_PROFILE");
      case "credits_available":       return Boolean(s) && !hasBlocker("USAGE_CREDITS_INSUFFICIENT", "USAGE_CREDITS_MISSING");
      case "technician_seats_ok":     return Boolean(s) && !hasBlocker("TECHNICIAN_SEAT_LIMIT_REACHED", "PURCHASE_TOPUP_PLAN");
      case "service_areas_count":     return metric("COVERAGE_AVAILABILITY", "active_areas") > 0;
      case "active_services_count":   return metric("SERVICES_PRICING", "published_count") > 0;
      case "coverage_configured":     return isSectionComplete("SERVICES_PRICING");
      case "staff_count":             return metric("STAFF_TECHNICIANS", "active_staff") > 0;
      case "availability_configured": return metric("COVERAGE_AVAILABILITY", "availability_rules") > 0;
      case "documents_submitted":     return isSectionComplete("DOCUMENTS");
      default:                        return false;
    }
  }

  const steps: SetupStep[] = SETUP_STEP_DEFS.map(st => ({ ...st, done: isDone(st.key) }));
  const doneCount = steps.filter(st => st.done).length;
  const total     = steps.length;
  const loading   = statusApi.loading || overviewApi.loading;

  const refetch = useCallback(() => {
    statusApi.refetch(); overviewApi.refetch();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    steps,
    doneCount,
    total,
    isComplete: doneCount === total,
    isBookable: s?.is_bookable ?? false,
    loading,
    error: statusApi.error ?? overviewApi.error,
    refetch,
  };
}
