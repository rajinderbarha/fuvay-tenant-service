import {
  normalizeSingleSelectAnswer,
  normalizeMultiSelectAnswer,
  normalizeShortTextAnswer,
  normalizeInformationAcknowledgement,
} from "../answer-normalization";

describe("normalizeSingleSelectAnswer", () => {
  it("submits the stable option ID as the canonical answer, not the label", () => {
    const record = normalizeSingleSelectAnswer("brand", "brand-id-123", "LG (translated label)");
    expect(record.canonicalAnswer).toBe("brand-id-123");
    expect(record.displaySummary).toBe("LG (translated label)");
    expect(record.questionType).toBe("SINGLE_SELECT");
  });
});

describe("normalizeMultiSelectAnswer", () => {
  it("preserves option order and joins labels for the summary", () => {
    const record = normalizeMultiSelectAnswer("service_option", ["a", "b"], ["Gas refill", "Deep clean"]);
    expect(record.canonicalAnswer).toEqual(["a", "b"]);
    expect(record.displaySummary).toBe("Gas refill, Deep clean");
  });

  it("summarizes an empty selection honestly rather than blank", () => {
    const record = normalizeMultiSelectAnswer("service_option", [], []);
    expect(record.displaySummary).toBe("None selected");
  });
});

describe("normalizeShortTextAnswer", () => {
  it("trims and collapses whitespace", () => {
    expect(normalizeShortTextAnswer("customer_note", "  hello   world  ").canonicalAnswer).toBe("hello world");
  });

  it("strips control characters", () => {
    expect(normalizeShortTextAnswer("customer_note", "hi\x00there\x1F").canonicalAnswer).toBe("hithere");
  });

  it("caps length at 500 characters", () => {
    const long = "a".repeat(600);
    expect((normalizeShortTextAnswer("customer_note", long).canonicalAnswer as string).length).toBe(500);
  });

  it("preserves Hindi and Punjabi text untouched", () => {
    expect(normalizeShortTextAnswer("customer_note", "पंखा काम नहीं कर रहा").canonicalAnswer).toBe("पंखा काम नहीं कर रहा");
  });
});

describe("normalizeInformationAcknowledgement", () => {
  it("records a canonical acknowledgement, never a customer-authored value", () => {
    const record = normalizeInformationAcknowledgement("photo_boundary");
    expect(record.canonicalAnswer).toBe("acknowledged");
    expect(record.questionType).toBe("INFORMATION");
  });
});
