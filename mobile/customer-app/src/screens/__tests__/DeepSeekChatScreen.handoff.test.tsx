import React from "react";
import { render, waitFor, fireEvent } from "@testing-library/react-native";
import { DeepSeekChatScreen } from "../DeepSeekChatScreen";
import { ThemeProvider } from "../../context/ThemeContext";
import { Animated } from "react-native";

function withTheme(ui: React.ReactElement) {
  return <ThemeProvider>{ui}</ThemeProvider>;
}

// See TabNavigator.test.tsx for why: TouchableOpacity's own internal
// Animated.timing() opacity effect hits a pre-existing, environment-level
// react/react-native-renderer version mismatch (real bug: react-native
// 0.85.0 peer-depends on react ^19.2.3, this repo pins react 19.2.0 -- see
// known-limitations.md) -- test-only workaround, not an app behavior change.
jest.spyOn(Animated, "timing").mockImplementation(() => ({
  start: (cb?: (r: { finished: boolean }) => void) => cb?.({ finished: true }),
  stop: () => {}, reset: () => {},
} as any));

// UX-07 Pass 3d: real, non-snapshot tests for the two SmartBot handoff
// guarantees this pass's brief requires: (1) arriving with category context
// from Home skips the "what service do you need" category list entirely,
// and (2) switching the conversation language mid-flow preserves the
// category/booking state already gathered (chatBookingState.ts's reducer is
// a component-local useReducer independent of the `language` useState, so
// this also guards against a future regression that resets it).
jest.mock("../../lib/api", () => ({
  aiConversationApi: { createSession: jest.fn(), sendMessage: jest.fn() },
  catalogApi: {
    categories: jest.fn(),
    categoryOfferings: jest.fn(),
    brandsForService: jest.fn(),
  },
  homeServiceDraftApi: {
    start: jest.fn(), updateFields: jest.fn(), serviceabilityCheck: jest.fn(),
    priceEstimate: jest.fn(), matchAndPrice: jest.fn(), confirmPriceChoice: jest.fn(),
    summary: jest.fn(),
  },
  bookingConfirmApi: { confirmHomeServiceBooking: jest.fn() },
}));
import { aiConversationApi, catalogApi } from "../../lib/api";

const CATEGORIES = {
  items: [
    { id: "cat-1", slug: "ac_repair", name: "AC & Cooling" },
    { id: "cat-2", slug: "plumbing", name: "Plumbing" },
  ],
  total: 2,
};

describe("DeepSeekChatScreen category handoff (UX-07 Pass 3d)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (aiConversationApi.createSession as jest.Mock).mockResolvedValue({ id: "sess-1" });
    (catalogApi.categories as jest.Mock).mockResolvedValue(CATEGORIES);
    (catalogApi.categoryOfferings as jest.Mock).mockResolvedValue({ items: [], total: 0 });
  });

  it("auto-selects the matching real category and never shows the category picker again", async () => {
    const { getByTestId, queryByText } = render(withTheme(
      <DeepSeekChatScreen route={{ params: { initialCategoryLabel: "AC & Cooling" } }} />
    ));
    // Should land directly past the category list -- the offerings fetch for
    // the matched category ran, proving pickCategory() was invoked
    // automatically instead of waiting for a tap on a category row.
    await waitFor(() => expect(catalogApi.categoryOfferings).toHaveBeenCalledWith("ac_repair"));
    expect(queryByText("What do you need help with?")).toBeNull();
    expect(getByTestId("booking-category-context")).toBeTruthy();
  });

  it("falls back honestly (no fake selection) when the label doesn't match any real category", async () => {
    const { findByTestId } = render(withTheme(
      <DeepSeekChatScreen route={{ params: { initialCategoryLabel: "Nonexistent Service Xyz" } }} />
    ));
    const notice = await findByTestId("booking-handoff-notice");
    expect(notice.props.children).toContain("Nonexistent Service Xyz");
    expect(catalogApi.categoryOfferings).not.toHaveBeenCalled();
  });

  it("preserves category/booking state already gathered when the conversation language is switched", async () => {
    const { getByTestId, queryByText } = render(withTheme(
      <DeepSeekChatScreen route={{ params: { initialCategoryLabel: "Plumbing" } }} />
    ));
    await waitFor(() => expect(catalogApi.categoryOfferings).toHaveBeenCalledWith("plumbing"));
    expect(getByTestId("booking-category-context")).toBeTruthy();

    fireEvent.press(getByTestId("chat-language-btn"));
    fireEvent.press(getByTestId("chat-language-option-hi"));

    // Category context (component-local booking reducer state) must still
    // be present after the language switch -- not reset back to the
    // category list.
    expect(getByTestId("booking-category-context")).toBeTruthy();
    expect(queryByText("What do you need help with?")).toBeNull();
  });
});
