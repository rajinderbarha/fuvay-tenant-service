import { IconProps } from "../components/Icon";

/**
 * Fallback icon for a Global Service card.
 *
 * Global Services are free-text, admin-authored rows (`name` is the only
 * guaranteed field -- there is no slug or type column, see
 * app/engines/global_services/models.py), so unlike categories there is no
 * stable key to map on. Matching on keywords in the name is therefore the
 * only option that varies the icon at all; anything unrecognised keeps the
 * previous generic phone glyph, which is still the honest default for a
 * "we call you back" card.
 *
 * `iconUrl` from admin always takes priority over this -- see the caller.
 */
const KEYWORD_ICONS: ReadonlyArray<[RegExp, IconProps["name"]]> = [
  [/inspect|survey|audit|check/i, "search-outline"],
  [/annual|plan|subscription|membership|amc/i, "calendar-outline"],
  [/clean/i, "sparkles-outline"],
  [/repair|fix|maintenance/i, "construct-outline"],
  [/install/i, "build-outline"],
  [/protect|secure|safety|shield|warranty/i, "shield-checkmark-outline"],
  [/consult|advice|expert/i, "chatbubbles-outline"],
];

export const GLOBAL_SERVICE_ICON_FALLBACK: IconProps["name"] = "call-outline";

export function resolveGlobalServiceIcon(name: string | null | undefined): IconProps["name"] {
  if (!name) return GLOBAL_SERVICE_ICON_FALLBACK;
  for (const [pattern, icon] of KEYWORD_ICONS) {
    if (pattern.test(name)) return icon;
  }
  return GLOBAL_SERVICE_ICON_FALLBACK;
}
