import { IconProps } from "../components/Icon";

/**
 * Per-slug icon for a service category.
 *
 * Source of truth stays the backend: `category.iconUrl` (uploaded from the
 * super-admin IconPicker) always wins when present, so icons remain
 * changeable without a release. This map only decides what to draw when
 * that field is null -- which today is EVERY category, since no icons have
 * been uploaded yet. Before this existed the fallback was a single generic
 * `construct-outline` wrench for every category, so Air Conditioning,
 * Plumbing, Electrical and the rest were visually identical and the grid
 * read as unfinished.
 *
 * Keys are the category `slug` (stable, used by the booking-draft API),
 * not the display name, so renaming a category in admin cannot silently
 * break its icon. An unknown/new slug still falls back to the generic
 * glyph rather than rendering a missing-glyph "?".
 */
const CATEGORY_ICON_MAP: Record<string, IconProps["name"]> = {
  "air-conditioning": "snow-outline",
  "ac": "snow-outline",
  "hvac": "thermometer-outline",
  "plumbing": "water-outline",
  "electrical": "flash-outline",
  "painting": "color-palette-outline",
  "pest-control": "bug-outline",
  "home-cleaning": "sparkles-outline",
  "cleaning": "sparkles-outline",
  "appliance-repair": "hardware-chip-outline",
  "carpentry": "hammer-outline",
  "furniture": "bed-outline",
  "security": "shield-checkmark-outline",
  "gardening": "leaf-outline",
  "moving": "cube-outline",
};

export const CATEGORY_ICON_FALLBACK: IconProps["name"] = "construct-outline";

export function resolveCategoryIcon(
  slug: string | null | undefined,
  fallback: IconProps["name"] = CATEGORY_ICON_FALLBACK,
): IconProps["name"] {
  if (slug && slug in CATEGORY_ICON_MAP) return CATEGORY_ICON_MAP[slug];
  return fallback;
}
