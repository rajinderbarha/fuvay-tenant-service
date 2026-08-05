import { MUTATION_SAFETY, offlinePolicyFor, requiresLiveConfirmation } from "../offline";

describe("offline operation classification", () => {
  it("classifies every irreversible workflow mutation named in the spec as requiring live confirmation", () => {
    const mustBeLive: (keyof typeof MUTATION_SAFETY)[] = [
      "bookingDraft.confirm", "booking.cancel", "booking.reschedule",
      "quote.reject", "review.submit",
    ];
    for (const key of mustBeLive) {
      expect(requiresLiveConfirmation(offlinePolicyFor(key))).toBe(true);
    }
  });

  it("classifies quote.approve as IDEMPOTENT (has a verified Idempotency-Key mechanism)", () => {
    expect(offlinePolicyFor("quote.approve")).toBe("IDEMPOTENT_MUTATION");
  });

  it("classifies draft edits as LOCAL_DRAFT and photo attachment as MEDIA_UPLOAD", () => {
    expect(offlinePolicyFor("bookingDraft.update")).toBe("LOCAL_DRAFT");
    expect(offlinePolicyFor("bookingDraft.attachPhoto")).toBe("MEDIA_UPLOAD");
  });

  it("has an explicit classification for every declared mutation key (no silent gaps)", () => {
    for (const key of Object.keys(MUTATION_SAFETY)) {
      expect(MUTATION_SAFETY[key as keyof typeof MUTATION_SAFETY]).toBeTruthy();
    }
  });
});
