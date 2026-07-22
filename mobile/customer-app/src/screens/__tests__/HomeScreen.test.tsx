import React from "react";
import { render, waitFor, fireEvent } from "@testing-library/react-native";
import HomeScreen from "../HomeScreen";
import { ThemeProvider } from "../../context/ThemeContext";

function withTheme(ui: React.ReactElement) {
  return <ThemeProvider>{ui}</ThemeProvider>;
}

// UX-07 Pass 3d: real, behavior-level (non-snapshot) tests for the
// redesigned Home screen. Mocks the api.ts surface HomeScreen actually calls
// (bookingsApi.list/fieldOpsJobsApi.list) rather than the network layer, per
// this codebase's existing test convention (see AuthContext.test.tsx).
const mockUser: { full_name?: string } = {};
jest.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ user: mockUser.full_name ? { full_name: mockUser.full_name } : null }),
}));

jest.mock("../../lib/api", () => ({
  bookingsApi: { list: jest.fn() },
  fieldOpsJobsApi: { list: jest.fn() },
}));
import { bookingsApi, fieldOpsJobsApi } from "../../lib/api";

// Skeleton is a leaf loading-indicator component unrelated to what these
// tests verify; stubbing it avoids a pre-existing, environment-level
// react/react-native-renderer version-mismatch warning (react-native 0.85.0
// peer-depends on react ^19.2.3, this repo pins react 19.2.0 -- a real,
// pre-existing inconsistency, not something this pass's presentation-only
// scope should be fixing by bumping dependency versions) that only
// surfaces when Animated.timing().start() actually runs inside a test.
// See known-limitations.md for the full writeup.
jest.mock("../../components/Skeleton", () => {
  const { View } = require("react-native");
  return { Skeleton: (props: any) => <View testID="skeleton-mock" style={{ height: props.height }} /> };
});

function navProps() {
  return { navigation: { navigate: jest.fn() } } as any;
}

describe("HomeScreen (UX-07 Pass 3d redesign)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUser.full_name = undefined;
    (bookingsApi.list as jest.Mock).mockResolvedValue({ items: [], total: 0 });
    (fieldOpsJobsApi.list as jest.Mock).mockResolvedValue({ jobs: [], has_next: false });
  });

  it("greets with the real first name when AuthContext has one", async () => {
    mockUser.full_name = "Priya Sharma";
    const { getByTestId } = render(withTheme(<HomeScreen {...navProps()} />));
    await waitFor(() => {
      const text = getByTestId("home-greeting").props.children;
      const joined = Array.isArray(text) ? text.join("") : String(text);
      expect(joined).toContain("Priya");
    });
  });

  it("falls back to an honest time-of-day greeting with no fake name when no user is loaded", async () => {
    mockUser.full_name = undefined;
    const { getByTestId } = render(withTheme(<HomeScreen {...navProps()} />));
    await waitFor(() => {
      const text = getByTestId("home-greeting").props.children;
      const joined = Array.isArray(text) ? text.join("") : String(text);
      expect(joined).not.toContain("Customer");
      expect(joined).toMatch(/Good (morning|afternoon|evening)/);
    });
  });

  it("shows the real active-booking card when a real active job exists", async () => {
    (fieldOpsJobsApi.list as jest.Mock).mockResolvedValue({
      jobs: [{ job_id: "job-1", status: "in_progress" }], has_next: false,
    });
    const { getByTestId, queryByTestId } = render(withTheme(<HomeScreen {...navProps()} />));
    await waitFor(() => expect(getByTestId("home-active-booking")).toBeTruthy());
    expect(queryByTestId("home-no-active-booking")).toBeNull();
  });

  it("shows a light empty state, not a dominant banner, when there is no active job", async () => {
    const { getByTestId, queryByTestId } = render(withTheme(<HomeScreen {...navProps()} />));
    await waitFor(() => expect(getByTestId("home-no-active-booking")).toBeTruthy());
    expect(queryByTestId("home-active-booking")).toBeNull();
  });

  it("routes the SmartBot CTA to the AIAssistant tab with no category params", async () => {
    const nav = navProps();
    const { getByTestId } = render(withTheme(<HomeScreen {...nav} />));
    await waitFor(() => getByTestId("home-smartbot-cta"));
    fireEvent.press(getByTestId("home-smartbot-cta"));
    expect(nav.navigation.navigate).toHaveBeenCalledWith("Tabs", { screen: "AIAssistant", params: undefined });
  });

  it("routes a popular-service tile tap to SmartBot carrying that service's label as context", async () => {
    const nav = navProps();
    const { getByTestId } = render(withTheme(<HomeScreen {...nav} />));
    await waitFor(() => getByTestId("home-service-tile-ac"));
    fireEvent.press(getByTestId("home-service-tile-ac"));
    expect(nav.navigation.navigate).toHaveBeenCalledWith("Tabs", {
      screen: "AIAssistant", params: { initialCategoryLabel: "AC Repair" },
    });
  });
});
