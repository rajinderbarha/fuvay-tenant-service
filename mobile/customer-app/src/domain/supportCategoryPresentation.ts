import { IconProps } from "../components/Icon";
import { CustomerAppStackParamList } from "../navigation/routeTypes";

export type SupportCategoryCode = "booking_service" | "account_security" | "pricing_question" | "something_else";

export interface SupportCategoryPresentation {
  code: SupportCategoryCode;
  label: string;
  helperText: string;
  icon: IconProps["name"];
  /** Whether "Link a booking" is offered for this topic. */
  bookingApplicable: boolean;
  /** When set, selecting this topic leaves the support wizard entirely
   * for a real, already-built canonical screen instead of continuing to
   * Step 2 -- e.g. account access issues are not a real
   * `record_type`/`complaint_type` the complaints engine models at all
   * (confirmed during audit: `VALID_RECORD_TYPES` has no "account"
   * concept), so this topic must never silently become a generic support
   * request (spec section 6). */
  reroute?: { screen: keyof CustomerAppStackParamList; params?: object };
  /** The real `complaint_type` sent at submission (spec section 6's
   * payload allowlist) -- Step 1's coarse topic never asks the customer
   * to pick a specific reason, so this is the most honest single real
   * value for each topic bucket, never a code the backend doesn't
   * recognize. Absent for topics that reroute instead of submitting. */
  submissionComplaintType?: string;
}

/** Only real, confirmed-supported topics (spec section 5) -- no dynamic
 * category-discovery endpoint exists in the audited backend
 * (`COMPLAINT_TYPES` is a static Python constant, never exposed via any
 * route), so this is a typed frontend registry, not a fabricated list.
 * Each code maps to a real `complaint_type` handled in Step 2, except
 * `account_security` which reroutes instead of ever reaching the
 * complaints engine. */
const REGISTRY: Record<SupportCategoryCode, SupportCategoryPresentation> = {
  booking_service: {
    code: "booking_service", label: "Booking & service", helperText: "A current or past service",
    icon: "build-outline", bookingApplicable: true, submissionComplaintType: "other",
  },
  account_security: {
    code: "account_security", label: "Account & security", helperText: "Sign-in or account access",
    icon: "lock-closed-outline", bookingApplicable: false,
    reroute: { screen: "Security" },
  },
  pricing_question: {
    code: "pricing_question", label: "Pricing question", helperText: "Service price or visit fee",
    icon: "pricetag-outline", bookingApplicable: true, submissionComplaintType: "payment_issue",
  },
  something_else: {
    code: "something_else", label: "Something else", helperText: "Another support topic",
    icon: "help-circle-outline", bookingApplicable: true, submissionComplaintType: "other",
  },
};

export const SUPPORT_CATEGORIES: SupportCategoryPresentation[] = [
  REGISTRY.booking_service, REGISTRY.account_security, REGISTRY.pricing_question, REGISTRY.something_else,
];

export function resolveSupportCategoryPresentation(categoryCode: string): SupportCategoryPresentation | null {
  return (REGISTRY as Record<string, SupportCategoryPresentation>)[categoryCode] ?? null;
}
