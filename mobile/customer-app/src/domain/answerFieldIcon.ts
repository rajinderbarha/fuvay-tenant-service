import { IconProps } from "../components/Icon";

/**
 * Glyph for one answer cell in the booking card's detail grid.
 *
 * The design (node 5944-302) shows a small outline icon beside each
 * answer -- a unit type, a brand, a symptom. Answers are free-text
 * catalog values with no icon column, so the glyph is derived from the
 * wording, the same approach already used for quick issues and global
 * services rather than inventing a second icon system.
 *
 * Matching is on the ANSWER first, then the question label, so "LG"
 * under a "Brand" question still resolves via the question when the
 * brand name itself matches nothing. An unmatched pair gets a neutral
 * dot -- a confidently wrong icon reads worse than a plain one.
 */
const ANSWER_RULES: ReadonlyArray<[RegExp, IconProps["name"]]> = [
  [/split|window|cassette|tower|inverter/i, "sunny-outline"],
  [/not\s*cool|cooling|temperature|heat/i, "thermometer-outline"],
  [/leak|water|drip/i, "water-outline"],
  [/nois|sound/i, "volume-high-outline"],
  [/smell|odou?r/i, "alert-circle-outline"],
  [/power|electric|spark|start/i, "flash-outline"],
  [/gas|refill/i, "color-fill-outline"],
  [/install/i, "hammer-outline"],
  [/clean|wash/i, "sparkles-outline"],
];

const QUESTION_RULES: ReadonlyArray<[RegExp, IconProps["name"]]> = [
  [/brand|make|manufactur/i, "pricetag-outline"],
  [/type|model|unit|capacity|size/i, "cube-outline"],
  [/issue|problem|symptom|fault/i, "alert-circle-outline"],
  [/quantity|how\s*many|count/i, "layers-outline"],
  [/when|date|time/i, "time-outline"],
];

export const ANSWER_FIELD_ICON_FALLBACK: IconProps["name"] = "ellipse-outline";

export function resolveAnswerFieldIcon(
  answer: string | null | undefined,
  questionLabel?: string | null,
): IconProps["name"] {
  if (answer) {
    const hit = ANSWER_RULES.find(([re]) => re.test(answer));
    if (hit) return hit[1];
  }
  if (questionLabel) {
    const hit = QUESTION_RULES.find(([re]) => re.test(questionLabel));
    if (hit) return hit[1];
  }
  return ANSWER_FIELD_ICON_FALLBACK;
}
