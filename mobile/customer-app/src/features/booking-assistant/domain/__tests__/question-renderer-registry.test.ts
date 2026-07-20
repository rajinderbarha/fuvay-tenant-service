import { resolveQuestionRenderer } from "../question-renderer-registry";

describe("resolveQuestionRenderer", () => {
  it("recognizes every supported question type", () => {
    for (const type of ["SINGLE_SELECT", "MULTI_SELECT", "SHORT_TEXT", "INFORMATION"]) {
      expect(resolveQuestionRenderer(type)).toEqual({ recognized: true, questionType: type });
    }
  });

  it("fails closed for an unknown type without throwing", () => {
    const result = resolveQuestionRenderer("BOOLEAN");
    expect(result.recognized).toBe(false);
  });

  it("fails closed for an empty string", () => {
    expect(resolveQuestionRenderer("").recognized).toBe(false);
  });
});
