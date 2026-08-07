import { resolveAnswerFieldIcon, ANSWER_FIELD_ICON_FALLBACK } from "../answerFieldIcon";

describe("resolveAnswerFieldIcon", () => {
  it("matches on the answer before the question", () => {
    // "Split AC" is the meaningful token here; the question label
    // ("Unit type") would also match a rule, so this proves precedence.
    expect(resolveAnswerFieldIcon("Split AC", "Unit type")).toBe("sunny-outline");
  });

  it("falls back to the question label when the answer matches nothing", () => {
    // A brand name is arbitrary text -- "LG" can never be pattern-matched,
    // so the question is what carries the meaning.
    expect(resolveAnswerFieldIcon("LG", "Brand")).toBe("pricetag-outline");
  });

  it("returns the neutral glyph rather than guessing when neither matches", () => {
    expect(resolveAnswerFieldIcon("Zeta 9000", "Something else")).toBe(ANSWER_FIELD_ICON_FALLBACK);
  });

  it("handles a missing answer and a missing question without throwing", () => {
    expect(resolveAnswerFieldIcon(null)).toBe(ANSWER_FIELD_ICON_FALLBACK);
    expect(resolveAnswerFieldIcon(undefined, null)).toBe(ANSWER_FIELD_ICON_FALLBACK);
  });
});
