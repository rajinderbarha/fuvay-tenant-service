"use client";
import { useCallback } from "react";
import {
  providerStatusApi, tenantSetupApi, staffApi, providerServiceAreasApi, usageCreditsApi,
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
  { key: "package_active",          label: "Package Active",         desc: "Activate your subscription package",        href: "/finance/package",            icon: "Package" },
  { key: "credits_available",       label: "Usage Credits",          desc: "Ensure credits are available",              href: "/finance/usage-credit-ledger",icon: "CreditCard" },
  { key: "security_deposit_ok",     label: "Security Deposit",       desc: "₹5,000 deposit required",                  href: "/finance/security-deposit",   icon: "Shield" },
  { key: "service_areas_count",     label: "Service Areas",          desc: "Add at least one coverage area",            href: "/provider/service-areas",     icon: "ArrowRight" },
  { key: "active_services_count",   label: "Enable a Service",       desc: "Enable AC Repair or another service",       href: "/tenant/setup/services",      icon: "Zap" },
  { key: "coverage_configured",     label: "Service Coverage",       desc: "Set types, brands & issue types",           href: "/provider/service-coverage",  icon: "Shield" },
  { key: "staff_count",             label: "Add Technician",         desc: "Add at least one technician",               href: "/provider/staff",             icon: "Users2" },
  { key: "availability_configured", label: "Business Hours",          desc: "Set working hours",                         href: "/tenant/setup/availability",  icon: "CalendarCheck" },
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
  const pkgApi    = useApi(useCallback(() => tenantSetupApi.getPackage(), []), []);
  // FINAL-L5-03: Usage Credit Balance (usage_credit_ledger) is the real,
  // canonical source -- NOT tenantSetupApi.getWallet(), which reads the
  // dormant tenant_wallets table. See project memory.
  const creditApi = useApi(useCallback(() => usageCreditsApi.getBalance(), []), []);
  const staffApi2 = useApi(useCallback(() => staffApi.list(), []), []);
  const areasApi  = useApi(useCallback(() => providerServiceAreasApi.list(), []), []);

  const s        = statusApi.data;
  const blockers = [...(s?.visibility_blockers ?? []), ...(s?.bookability_blockers ?? [])];
  const pkg        = pkgApi.data as Record<string, unknown> | null;
  const staffCount = staffApi2.data?.users?.length ?? 0;
  const areasCount = areasApi.data?.total ?? areasApi.data?.areas?.length ?? 0;
  const creditBal  = creditApi.data?.usage_credit_balance ?? 0;
  const pkgStatus  = String(pkg?.status ?? "inactive");
  const depositSt  = String(pkg?.security_deposit_status ?? "pending");

  function isDone(key: string): boolean {
    switch (key) {
      case "profile_complete":        return !blockers.some(b => b.code?.includes("profile"));
      case "package_active":          return pkgStatus === "active";
      case "credits_available":       return creditBal > 0;
      case "security_deposit_ok":     return depositSt === "received" || depositSt === "waived";
      case "service_areas_count":     return areasCount > 0;
      case "active_services_count":   return !blockers.some(b => b.code?.includes("service") || b.code?.includes("offering"));
      case "coverage_configured":     return !blockers.some(b => b.code?.includes("coverage"));
      case "staff_count":             return staffCount > 0;
      case "availability_configured": return !blockers.some(b => b.code?.includes("availability") || b.code?.includes("slot"));
      case "documents_submitted":     return !blockers.some(b => b.code?.includes("document"));
      default:                        return false;
    }
  }

  const steps: SetupStep[] = SETUP_STEP_DEFS.map(st => ({ ...st, done: isDone(st.key) }));
  const doneCount = steps.filter(st => st.done).length;
  const total     = steps.length;
  const loading   = statusApi.loading || pkgApi.loading || creditApi.loading || staffApi2.loading || areasApi.loading;

  const refetch = useCallback(() => {
    statusApi.refetch(); pkgApi.refetch(); creditApi.refetch(); staffApi2.refetch(); areasApi.refetch();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    steps,
    doneCount,
    total,
    isComplete: doneCount === total,
    isBookable: s?.is_bookable ?? false,
    loading,
    error: statusApi.error,
    refetch,
  };
}
