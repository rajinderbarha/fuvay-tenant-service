import { CategoryId } from "./ids";

/** Home Services is the only vertical launching first; Coaching, Food and
 * Real Estate must remain capability-driven, never hardcoded as available
 * (Phase A-C spec section 11, reaffirmed Phase D section 8). This union
 * only names verticals actually observed in the backend route surface
 * this phase (customer/coaching/*, customer/real-estate/*); "food" has no
 * confirmed customer route yet and is deliberately absent until it does. */
export type VerticalKey = "home_services" | "coaching" | "real_estate";

export interface Category {
  id: CategoryId;
  slug: string;
  name: string;
  vertical: VerticalKey | null;
  isActive: boolean;
}
