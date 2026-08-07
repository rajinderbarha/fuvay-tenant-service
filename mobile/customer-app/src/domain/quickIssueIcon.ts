import { IconProps } from "../components/Icon";

/**
 * Icon + tint for a quick-issue chip.
 *
 * Issues are free-text catalog rows (master_issue_types.name) with no icon
 * column, so the glyph is derived from the wording -- exactly the approach
 * already used for Global Services (see globalServiceIcon.ts), keeping one
 * icon system in the app rather than introducing a second.
 *
 * Matching is on the ISSUE first, then the category, so "Gas Refill Needed"
 * gets a refill glyph rather than the generic AC one. Anything unmatched
 * falls back to a neutral wrench: a wrong-but-confident icon reads worse
 * than an honestly generic one.
 */
export interface QuickIssueIcon {
  name: IconProps["name"];
  /** Circle fill behind the glyph. */
  tint: string;
  /** Glyph colour on that fill. */
  onTint: string;
}

const TINTS = {
  blue: "#2563EB",
  teal: "#0D9488",
  amber: "#D97706",
  violet: "#7C3AED",
  green: "#059669",
  rose: "#E11D48",
} as const;

type Tint = (typeof TINTS)[keyof typeof TINTS];

const RULES: ReadonlyArray<[RegExp, IconProps["name"], Tint]> = [
  [/not\s*cool|cooling\s*low|low\s*cool/i, "snow-outline", TINTS.blue],
  [/gas\s*refill|refill/i, "color-fill-outline", TINTS.teal],
  [/not\s*start|won'?t\s*start|no\s*power|power/i, "flash-outline", TINTS.amber],
  [/smell|odou?r/i, "alert-circle-outline", TINTS.rose],
  [/nois|sound/i, "volume-high-outline", TINTS.violet],
  [/leak|drip/i, "water-outline", TINTS.blue],
  [/block|clog|drain/i, "git-merge-outline", TINTS.teal],
  [/install/i, "hammer-outline", TINTS.violet],
  [/deep\s*clean/i, "sparkles-outline", TINTS.green],
  [/clean|wash/i, "sparkles-outline", TINTS.teal],
  [/service|maintenanc|amc/i, "construct-outline", TINTS.blue],
  [/tap|faucet|pipe|plumb/i, "water-outline", TINTS.blue],
  [/switch|socket|wiring|electric|light|fan/i, "flash-outline", TINTS.amber],
  [/paint/i, "brush-outline", TINTS.rose],
  [/pest|termite|cockroach/i, "bug-outline", TINTS.green],
];

const FALLBACK: QuickIssueIcon = {
  name: "construct-outline",
  tint: TINTS.blue,
  onTint: "#FFFFFF",
};

export function resolveQuickIssueIcon(
  label: string | null | undefined,
  categoryName?: string | null,
): QuickIssueIcon {
  for (const source of [label, categoryName]) {
    if (!source) continue;
    const hit = RULES.find(([re]) => re.test(source));
    if (hit) return { name: hit[1], tint: hit[2], onTint: "#FFFFFF" };
  }
  return FALLBACK;
}
