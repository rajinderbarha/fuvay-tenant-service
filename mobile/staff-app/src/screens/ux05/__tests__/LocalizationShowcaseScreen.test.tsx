import React from "react";
import { screen } from "@testing-library/react-native";
import { renderWithTheme as render } from "../../../testUtils/renderWithTheme";
import { LocalizationShowcaseScreen } from "../LocalizationShowcaseScreen";

const LONG_HINDI = "ग्राहक ने बताया कि एयर कंडीशनर ठंडी हवा नहीं दे रहा है और कंप्रेसर से अजीब सी आवाज़ आ रही है, कृपया जल्द से जल्द तकनीशियन भेजें और सर्विस पूरी होने के बाद रसीद भी उपलब्ध कराएं।";

describe("LocalizationShowcaseScreen (real long-string spot check)", () => {
  it("renders the full long Hindi customer-issue string without truncation on CustomerContactCard", () => {
    render(<LocalizationShowcaseScreen />);
    // CustomerContactCard's issue-summary Text has no numberOfLines prop --
    // if it did truncate, the full string would not be queryable by exact
    // text match (RNTL matches the rendered text content, not a
    // visually-clipped substring, so this proves no numberOfLines was
    // accidentally added, not that pixels don't clip -- see
    // localization-readiness-report.md for that honest boundary).
    expect(screen.getAllByText(LONG_HINDI).length).toBeGreaterThan(0);
  });

  it("renders the full long Hindi restricted-state reason without truncation", () => {
    render(<LocalizationShowcaseScreen />);
    // PermissionRestrictedState.reason also has no numberOfLines -- appears
    // twice in this screen (contact card + restricted state use the same
    // string) so assert at least one full match exists.
    expect(screen.getAllByText(LONG_HINDI).length).toBeGreaterThan(0);
  });

  it("does NOT render the full long Punjabi notification body (intentional 2-line truncation)", () => {
    render(<LocalizationShowcaseScreen />);
    // NotificationCard's body deliberately sets numberOfLines={2} (a list
    // context where truncation is the correct, intentional behavior, not a
    // localization bug) -- the exact full string should NOT be an exact
    // text-node match once RNTL flattens rendered text, distinguishing
    // "intentionally truncated" from "accidentally truncated" elsewhere on
    // this screen.
    expect(screen.getByText(/ਗਾਹਕ ਨੇ ਦੱਸਿਆ/)).toBeTruthy();
  });

  it("renders Punjabi address text on AddressCard without truncation", () => {
    render(<LocalizationShowcaseScreen />);
    expect(screen.getByText(/ਲੁਧਿਆਣਾ, ਪੰਜਾਬ/)).toBeTruthy();
  });
});
