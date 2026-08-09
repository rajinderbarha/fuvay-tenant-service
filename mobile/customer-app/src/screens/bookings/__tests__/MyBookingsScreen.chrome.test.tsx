import React from "react";
import { render, screen } from "@testing-library/react-native";
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

  it("keeps the search box and filters pinned while the title can fold away", () => {
    // A title restating the tab is worth reclaiming on scroll; a CONTROL that
    // scrolls out of reach is worse than the title that does.
    renderScreen();
    expect(screen.getByLabelText("Search bookings")).toBeTruthy();
    expect(screen.getByLabelText("Filter bookings")).toBeTruthy();
    expect(screen.getByText("My Bookings")).toBeTruthy();
  });
});
