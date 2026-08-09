import { formatCampaignEnds } from "../campaignWindow";

const NOW = new Date("2026-11-03T10:00:00Z");

describe("formatCampaignEnds", () => {
  it("says nothing at all for an open-ended campaign", () => {
    // The rule this module exists for: no manufactured urgency. A campaign with
    // no end date gets no deadline line, not "ends soon".
    expect(formatCampaignEnds(null, NOW)).toBeNull();
  });

  it("names the real end date", () => {
    expect(formatCampaignEnds("2026-11-05T18:29:59Z", NOW)).toBe("Ends 5 Nov");
  });

  it("says today for a campaign ending later the same day", () => {
    // Compared by CALENDAR day in the device's own timezone -- which is what a
    // customer means by "today" -- so both timestamps here are chosen to fall on
    // the same local day wherever the suite runs.
    expect(formatCampaignEnds("2026-11-03T12:00:00Z", NOW)).toBe("Ends today");
  });

  it("says tomorrow for the next calendar day, however few hours away", () => {
    expect(formatCampaignEnds("2026-11-04T12:00:00Z", NOW)).toBe("Ends tomorrow");
  });

  it("says nothing for a campaign that has already ended", () => {
    // The backend filters expired campaigns out; if one slips through, a stale
    // "Ends 1 Nov" is worse than no line.
    expect(formatCampaignEnds("2026-11-01T00:00:00Z", NOW)).toBeNull();
  });

  it("says nothing for an unparseable date rather than guessing a deadline", () => {
    expect(formatCampaignEnds("next diwali", NOW)).toBeNull();
    expect(formatCampaignEnds("", NOW)).toBeNull();
  });
});
