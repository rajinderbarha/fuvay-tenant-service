import { distinctBadges, standingBadge } from "../providerBadges";

describe("distinctBadges", () => {
  it("collapses badges that share a display name", () => {
    // The live case: Guramrit held five separately-keyed definitions all named
    // "L5 Cfg Badge", so the booking card printed the label five times and React
    // errored on two children with the same key.
    const badges = [
      { name: "L5 Cfg Badge" }, { name: "L5 Cfg Badge" }, { name: "L5 Cfg Badge" },
      { name: "L5 Cfg Badge" }, { name: "L5 Cfg Badge" },
      { name: "AC Specialist" }, { name: "Verified Business" },
    ];
    expect(distinctBadges(badges).map(b => b.name)).toEqual([
      "L5 Cfg Badge", "AC Specialist", "Verified Business",
    ]);
  });

  it("keeps the FIRST occurrence, so the newest badge's icon and colour survive", () => {
    const kept = distinctBadges([
      { name: "Verified", icon: "shield-check" },
      { name: "Verified", icon: "old-icon" },
    ]);
    expect(kept).toHaveLength(1);
    expect(kept[0].icon).toBe("shield-check");
  });

  it("preserves order rather than sorting", () => {
    // The backend sends these most-recently-earned first, which is the order
    // worth showing.
    const names = distinctBadges([{ name: "B" }, { name: "A" }, { name: "C" }]).map(b => b.name);
    expect(names).toEqual(["B", "A", "C"]);
  });

  it("drops an unnamed badge instead of rendering an empty pill", () => {
    expect(distinctBadges([{ name: "" }, { name: "   " }, { name: "Real" }]))
      .toEqual([{ name: "Real" }]);
  });

  it("treats names differing only by surrounding space as the same badge", () => {
    expect(distinctBadges([{ name: "Verified" }, { name: " Verified " }])).toHaveLength(1);
  });

  it("returns an empty list unchanged", () => {
    expect(distinctBadges([])).toEqual([]);
  });
});

describe("standingBadge", () => {
  it("finds the badge carrying a level, wherever it sits in the list", () => {
    // Identified by the level, not by position, so the card does not depend on the
    // backend's ordering.
    const badge = standingBadge([
      { name: "AC Specialist" },
      { name: "Bronze Partner", icon: "medal", level: 1 },
    ]);
    expect(badge?.name).toBe("Bronze Partner");
  });

  it("returns null when no level has been earned", () => {
    // The card then shows nothing rather than promoting an independent badge into a
    // standing it does not represent.
    expect(standingBadge([{ name: "AC Specialist" }, { name: "Verified Business" }])).toBeNull();
  });

  it("keeps the highest level if a payload carries more than one", () => {
    const badge = standingBadge([
      { name: "Bronze Partner", level: 1 },
      { name: "Gold Partner", level: 3 },
      { name: "Silver Partner", level: 2 },
    ]);
    expect(badge?.name).toBe("Gold Partner");
  });

  it("ignores a zero or null level", () => {
    expect(standingBadge([{ name: "Nothing", level: 0 }, { name: "Also", level: null }])).toBeNull();
  });

  it("returns null for an empty list", () => {
    expect(standingBadge([])).toBeNull();
  });
});
