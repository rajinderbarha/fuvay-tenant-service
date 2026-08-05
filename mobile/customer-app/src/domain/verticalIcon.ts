import { IconProps } from "../components/Icon";

/**
 * `vertical.icon` from the backend (`verticals.icon` column) is an
 * admin-authored, free-text Lucide/web icon component name (e.g. "Wrench",
 * "Home") -- valid on the web admin dashboard, but not a real Ionicons
 * glyph name, so `VerticalSwitcher` casting it straight through rendered
 * the "?" missing-glyph fallback for every vertical. This maps the exact
 * set of values currently stored in the `verticals` table (confirmed via
 * direct DB read) to real Ionicons names; an unrecognized future value
 * still fails safe to the existing generic fallback rather than crashing.
 */
const VERTICAL_ICON_MAP: Record<string, IconProps["name"]> = {
  Wrench: "construct-outline",
  Home: "home-outline",
  Sparkles: "sparkles-outline",
  ShoppingBag: "bag-outline",
  UtensilsCrossed: "restaurant-outline",
  GraduationCap: "school-outline",
  Briefcase: "briefcase-outline",
};

export function resolveVerticalIcon(rawIcon: string | null | undefined, fallback: IconProps["name"]): IconProps["name"] {
  if (rawIcon && rawIcon in VERTICAL_ICON_MAP) return VERTICAL_ICON_MAP[rawIcon];
  return fallback;
}
