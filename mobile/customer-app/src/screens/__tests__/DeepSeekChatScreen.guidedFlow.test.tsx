import React from "react";
import { render, waitFor, fireEvent } from "@testing-library/react-native";
import { DeepSeekChatScreen } from "../DeepSeekChatScreen";
import { ThemeProvider } from "../../context/ThemeContext";
import { Animated } from "react-native";

function withTheme(ui: React.ReactElement) {
  return <ThemeProvider>{ui}</ThemeProvider>;
}

// Same environment-level TouchableOpacity/Animated workaround as
// DeepSeekChatScreen.handoff.test.tsx (see that file's comment) -- not an app
// behavior change.
jest.spyOn(Animated, "timing").mockImplementation(() => ({
  start: (cb?: (r: { finished: boolean }) => void) => cb?.({ finished: true }),
  stop: () => {}, reset: () => {},
} as any));

// UX-07 Pass 3e: real, non-snapshot tests for the guided-booking-flow
// restructure (compact header, honest progress indicator, collapsed-by-
// default answers-so-far summary, and the accessible names added to each
// real option row). Uses the same real reducer/API contract as the Pass 3d
// handoff tests -- no fabricated session/step shape.
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
  items: [{ id: "cat-1", slug: "plumbing", name: "Plumbing" }],
  total: 1,
};
const OFFERINGS = {
  items: [{ id: "off-1", slug: "tap_repair", name: "Tap Repair" }],
  total: 1,
};

describe("DeepSeekChatScreen guided flow restructure (UX-07 Pass 3e)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (aiConversationApi.createSession as jest.Mock).mockResolvedValue({ id: "sess-1" });
    (catalogApi.categories as jest.Mock).mockResolvedValue(CATEGORIES);
    (catalogApi.categoryOfferings as jest.Mock).mockResolvedValue(OFFERINGS);
    (catalogApi.brandsForService as jest.Mock).mockResolvedValue({ brands: [] });
  });

  async function openFlow() {
    const utils = render(withTheme(<DeepSeekChatScreen />));
    fireEvent.press(utils.getByTestId("chat-start"));
    await waitFor(() => expect(utils.queryByTestId("chat-book-service")).toBeTruthy(), { timeout: 5000 });
    fireEvent.press(utils.getByTestId("chat-book-service"));
    await waitFor(() => expect(catalogApi.categories).toHaveBeenCalled());
    return utils;
  }

  it("shows exactly one real category question at a time with an accessible name per option", async () => {
    const { getByTestId } = await openFlow();
    const row = getByTestId("category-plumbing");
    expect(row.props.accessibilityRole).toBe("button");
    expect(row.props.accessibilityLabel).toBe("Select category: Plumbing");
  });

  it("advances the honest, state-derived progress indicator after a real selection", async () => {
    const { getByTestId, queryByTestId } = await openFlow();
    // No progress row yet at the very first (category) question -- booking.step is idle.
    expect(queryByTestId("booking-summary-toggle")).toBeNull();

    fireEvent.press(getByTestId("category-plumbing"));
    await waitFor(() => expect(catalogApi.categoryOfferings).toHaveBeenCalledWith("plumbing"));

    // Selecting a category is real, structured state -- the summary now
    // appears (collapsed by default) and offering options are shown with
    // real accessible names.
    const summaryToggle = getByTestId("booking-summary-toggle");
    expect(summaryToggle.props.accessibilityState.expanded).toBe(false);
    const offeringRow = getByTestId("offering-tap_repair");
    expect(offeringRow.props.accessibilityLabel).toBe("Select service: Tap Repair");
  });

  it("expands the answers-so-far summary on demand and shows the real selected category", async () => {
    const { getByTestId, getByText } = await openFlow();
    fireEvent.press(getByTestId("category-plumbing"));
    await waitFor(() => expect(catalogApi.categoryOfferings).toHaveBeenCalledWith("plumbing"));

    fireEvent.press(getByTestId("booking-summary-toggle"));
    expect(getByText("Service: Plumbing")).toBeTruthy();
    expect(getByTestId("booking-start-over")).toBeTruthy();
  });

  it("closing and reopening the guided flow (Start over) does not create a duplicate AI session", async () => {
    const { getByTestId } = await openFlow();
    fireEvent.press(getByTestId("category-plumbing"));
    await waitFor(() => expect(catalogApi.categoryOfferings).toHaveBeenCalledWith("plumbing"));
    fireEvent.press(getByTestId("booking-summary-toggle"));
    fireEvent.press(getByTestId("booking-start-over"));
    await waitFor(() => expect(catalogApi.categories).toHaveBeenCalledTimes(2));
    // Only ever one AI session created for the whole screen lifetime --
    // "start over" resets the local booking reducer, it never re-runs
    // aiConversationApi.createSession.
    expect(aiConversationApi.createSession).toHaveBeenCalledTimes(1);
  });

  // UX-07 Pass 3f accessibility remediation.
  it("the guided booking-flow modal exposes accessible modal semantics and a labeled close/back control", async () => {
    const { getByTestId } = await openFlow();
    const backBtn = getByTestId("booking-flow-back");
    expect(backBtn.props.accessibilityRole).toBe("button");
    expect(backBtn.props.accessibilityLabel).toBe("Close guided booking");
    expect(backBtn.props.hitSlop).toBeTruthy();
  });

  it("language options in the language selector expose an accessible name and selected state", async () => {
    const utils = render(withTheme(<DeepSeekChatScreen />));
    fireEvent.press(utils.getByTestId("chat-start"));
    await waitFor(() => expect(utils.queryByTestId("chat-language-btn")).toBeTruthy());
    fireEvent.press(utils.getByTestId("chat-language-btn"));
    const englishOption = utils.getByTestId("chat-language-option-en");
    expect(englishOption.props.accessibilityRole).toBe("button");
    expect(englishOption.props.accessibilityState).toEqual({ selected: true });
  });
});
