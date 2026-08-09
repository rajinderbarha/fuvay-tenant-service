import { Ionicons } from "@expo/vector-icons";
import { resolveBadgeIcon, DEFAULT_BADGE_ICON } from "../badgeIcon";

describe("resolveBadgeIcon", () => {
  it("always returns a name Ionicons can actually draw", () => {
    // The bug this exists for: badge icons are free text an admin typed, and an
    // unknown name renders as NOTHING -- which is why the booking card showed no
    // badge icon at all.
    const stored = [
      "medal", "trophy", "crown", "shield-check", "star", "snow",
      "made-up-icon", "", null, undefined, "  MEDAL  ",
    ];
    for (const name of stored) {
      expect(Ionicons.glyphMap).toHaveProperty(resolveBadgeIcon(name));
    }
  });

  it("maps names Ionicons does not have onto ones it does", () => {
    expect(resolveBadgeIcon("shield-check")).toBe("shield-checkmark");
    expect(resolveBadgeIcon("crown")).not.toBe(DEFAULT_BADGE_ICON);
  });

  it("passes through a name that is already an Ionicons glyph", () => {
    expect(resolveBadgeIcon("water")).toBe("water");
  });

  it("falls back to a generic badge mark rather than nothing", () => {
    // A wrong-but-present icon beside the badge's own text beats a pill that looks
    // unfinished; the text carries the meaning either way.
    expect(resolveBadgeIcon("no-such-icon-anywhere")).toBe(DEFAULT_BADGE_ICON);
    expect(resolveBadgeIcon(null)).toBe(DEFAULT_BADGE_ICON);
  });

  it("is case and whitespace insensitive", () => {
    expect(resolveBadgeIcon("  Trophy ")).toBe("trophy");
  });
});
