import { Ionicons } from "@expo/vector-icons";

type IoniconName = keyof typeof Ionicons.glyphMap;

/**
 * The icon for a provider badge.
 *
 * Badge icons are stored as free text an admin typed (or a ladder default like
 * "medal"), and the app draws Ionicons. The two vocabularies only partly overlap:
 * "shield-check" and "crown" are real, sensible names that Ionicons does not have,
 * and an unknown name renders as NOTHING -- which is why the booking card showed no
 * badge icon at all.
 *
 * So names are mapped, and anything unrecognised falls back to a generic badge mark
 * rather than disappearing. A wrong-but-present icon beside the badge's own text is
 * better than a pill that looks unfinished; the text carries the meaning either way.
 */
const ALIASES: Record<string, IoniconName> = {
  // Standing ladder defaults.
  medal: "medal",
  trophy: "trophy",
  crown: "diamond",          // no crown in Ionicons; a gem reads as "top tier"
  // Common admin-configured names.
  "shield-check": "shield-checkmark",
  "shield-checkmark": "shield-checkmark",
  shield: "shield",
  star: "star",
  "check-circle": "checkmark-circle",
  checkmark: "checkmark-circle",
  verified: "checkmark-circle",
  snow: "snow",
  flash: "flash",
  water: "water",
  leaf: "leaf",
  heart: "heart",
  ribbon: "ribbon",
  time: "time",
  rocket: "rocket",
  thumbsup: "thumbs-up",
  "thumbs-up": "thumbs-up",
};

/** Shown when the stored name matches nothing -- never an empty space. */
export const DEFAULT_BADGE_ICON: IoniconName = "ribbon";

export function resolveBadgeIcon(icon: string | null | undefined): IoniconName {
  const key = (icon ?? "").trim().toLowerCase();
  if (!key) return DEFAULT_BADGE_ICON;
  const mapped = ALIASES[key];
  if (mapped) return mapped;
  // An exact Ionicons name that simply is not in the alias table above.
  if (key in Ionicons.glyphMap) return key as IoniconName;
  // "medal-outline" for "medal", etc: try the outline variant before giving up.
  if (`${key}-outline` in Ionicons.glyphMap) return `${key}-outline` as IoniconName;
  return DEFAULT_BADGE_ICON;
}
