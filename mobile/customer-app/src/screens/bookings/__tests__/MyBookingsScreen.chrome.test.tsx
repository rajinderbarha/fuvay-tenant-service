import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { AppProviders } from "../../../providers/AppProviders";
import { MyBookingsScreen } from "../MyBookingsScreen";
import * as listQueryModule from "../../../api/customerBookings/useCustomerBookingsListQuery";
import * as homeQueryModule from "../../../api/home/useCustomerHomeQuery";

jest.mock("../../../api/customerBookings/useCustomerBookingsListQuery");
jest.mock("../../../api/home/useCustomerHomeQuery");

function mockList(overrides: Record<string, unknown> = {}) {
  (listQueryModule.useCustomerBookingsListQuery as jest.Mock).mockReturnValue({
    items: [], counts: { active: 0, completed: 0, all: 0 },
    isPending: false, isStale: false, isError: false, isRefetching: false,
    isFetchingNextPage: false, hasNextPage: false,
    fetchNextPage: jest.fn(), refetch: jest.fn(), dataUpdatedAt: Date.now(),
    ...overrides,
  });
}

describe("MyBookingsScreen chrome", () => {
  beforeEach(() => {
    (homeQueryModule.useCustomerHomeQuery as jest.Mock).mockReturnValue({ data: undefined });
    mockList();
  });
  afterEach(() => jest.clearAllMocks());

  function renderScreen() {
    return render(
      <AppProviders>
        <NavigationContainer>
          <MyBookingsScreen />
        </NavigationContainer>
      </AppProviders>,
    );
  }

  it("does not ask for the bottom safe-area inset the tab bar already applies", () => {
    // The bug: `edges={["top","bottom"]}` added a bottom inset on a screen that
    // sits inside a tab navigator, leaving a blank strip of background between
    // the last card and the tab bar.
    renderScreen();
    const safeArea = screen.UNSAFE_getByType(
      require("react-native-safe-area-context").SafeAreaView,
    );
    expect(safeArea.props.edges).toEqual(["top"]);
  });

  it("keeps search off screen until asked for, and the tabs always reachable", () => {
    // Search and filtering used to hold a permanent row above the tabs. Most visits
    // are here to look at the list, so the controls are now opened from the tab row
    // -- but the affordance itself stays pinned, because a CONTROL that scrolls out
    // of reach is worse than the title that does.
    renderScreen();
    expect(screen.queryByLabelText("Search bookings")).toBeNull();
    expect(screen.queryByLabelText("Filter bookings")).toBeNull();
    expect(screen.getByLabelText("Search and filter bookings")).toBeTruthy();
    expect(screen.getByText("My bookings")).toBeTruthy();
  });

  it("opens the search box and the filter control together on demand", () => {
    // Filtering lives inside the search row, so revealing one has to reveal both --
    // otherwise the filter becomes unreachable.
    renderScreen();
    fireEvent.press(screen.getByLabelText("Search and filter bookings"));
    expect(screen.getByLabelText("Search bookings")).toBeTruthy();
    expect(screen.getByLabelText("Filter bookings")).toBeTruthy();
  });

  it("refuses to hide the search row while a term is applied", () => {
    // A narrowed list whose controls are hidden reads as missing bookings.
    renderScreen();
    fireEvent.press(screen.getByLabelText("Search and filter bookings"));
    fireEvent.changeText(screen.getByLabelText("Search bookings"), "geyser");
    expect(screen.queryByLabelText("Close search")).toBeNull();
    expect(screen.getByLabelText("Search bookings")).toBeTruthy();
  });

  it("closes an empty search row when the customer dismisses it", () => {
    renderScreen();
    fireEvent.press(screen.getByLabelText("Search and filter bookings"));
    fireEvent.press(screen.getByLabelText("Close search"));
    expect(screen.queryByLabelText("Search bookings")).toBeNull();
    expect(screen.getByLabelText("Search and filter bookings")).toBeTruthy();
  });
});

describe("MyBookingsScreen: finding what is late", () => {
  afterEach(() => jest.restoreAllMocks());

  function withItems(items: unknown[]) {
    (homeQueryModule.useCustomerHomeQuery as jest.Mock).mockReturnValue({ data: undefined });
    mockList({ items, counts: { active: items.length, completed: 0, all: items.length } });
    return render(
      <AppProviders>
        <NavigationContainer>
          <MyBookingsScreen />
        </NavigationContainer>
      </AppProviders>,
    );
  }

  function item(id: string, urgency: string | null) {
    return {
      bookingId: id, bookingNumber: id, rawStatus: "confirmed",
      stage: "active", statusLabel: "Request confirmed",
      activityText: null, supportingText: null, createdAt: null,
      serviceName: `Service ${id}`, jobType: null, summaryFields: [],
      address: { label: null, formatted: "Ludhiana", zipcode: null },
      pricing: { state: { kind: "unavailable" }, inspection: null },
      urgency, scheduledDate: null, scheduledTimeWindow: null, latenessLabel: null,
    };
  }

  it("heads each group and counts it, today before the backlog", () => {
    // The whole complaint: with one newest-first list, a six-day-overdue visit sat below
    // something scheduled for next week and could only be found by reading every card.
    withItems([item("a", "upcoming"), item("b", "late"), item("c", "today")]);

    expect(screen.getByText("Past their slot (1)")).toBeTruthy();
    expect(screen.getByText("Today (1)")).toBeTruthy();
    expect(screen.getByText("Upcoming (1)")).toBeTruthy();
  });

  it("says how many are late before any scrolling", () => {
    withItems([item("b", "late"), item("c", "late")]);
    expect(screen.getByText("2 bookings are past their scheduled slot")).toBeTruthy();
  });

  it("uses the singular for exactly one", () => {
    withItems([item("b", "late")]);
    expect(screen.getByText("1 booking is past its scheduled slot")).toBeTruthy();
  });

  it("shows no late summary and no headings when nothing is grouped", () => {
    // Finished bookings carry no urgency, so the Completed tab stays a plain list.
    withItems([item("d", null)]);
    expect(screen.queryByText(/past its scheduled slot|past their scheduled slot/)).toBeNull();
    expect(screen.queryByText(/Past their slot/)).toBeNull();
  });
});
