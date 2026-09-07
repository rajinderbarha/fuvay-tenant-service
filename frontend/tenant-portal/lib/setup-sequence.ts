import type { HomeServicesSetupOverview } from "./api";

export const SETUP_STEPS = [
  ["BUSINESS_PROFILE", "business-profile", "Business Profile"],
  ["DOCUMENTS", "documents", "Documents"],
  ["SERVICES_PRICING", "services-pricing", "Services & Pricing"],
  ["TECHNICIAN_PLAN", "plan", "Technician Seat Plan"],
  ["STAFF_TECHNICIANS", "staff", "Staff & Technicians"],
  ["COVERAGE_AVAILABILITY", "coverage-availability", "Coverage & Availability"],
  ["FINANCE_READINESS", "finance", "Finance Readiness"],
  ["REVIEW_SUBMIT", "review", "Review & Submit"],
] as const;

export function setupPrerequisite(overview: HomeServicesSetupOverview | null, slug: string) {
  const index = SETUP_STEPS.findIndex(step => step[1] === slug);
  if (index <= 0 || overview?.vertical?.status === "active") return null;
  for (const [key, route, label] of SETUP_STEPS.slice(0, index)) {
    if (overview?.sections.find(section => section.key === key)?.status !== "complete") {
      return { key, label, route: `/tenant/home-services/setup/${route}` };
    }
  }
  return null;
}
