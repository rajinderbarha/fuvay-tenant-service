import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { MyBookingsScreen } from "../MyBookingsScreen";
import * as listQueryModule from "../../../api/customerBookings/useCustomerBookingsListQuery";
import * as homeQueryModule from "../../../api/home/useCustomerHomeQuery";

const Tab = createBottomTabNavigator();

function renderBookings(initialParams?: { initialSearch?: string; openFilter?: boolean }) {
  return renderWithProviders(
    <NavigationContainer>
      <Tab.Navigator>
        <Tab.Screen name="Bookings" component={MyBookingsScreen} initialParams={initialParams} />
        <Tab.Screen name="Assistant" component={() => null} />
      </Tab.Navigator>
    </NavigationContainer>,
  );
}

function mockListQuery(overrides: Partial<ReturnType<typeof listQueryModule.useCustomerBookingsListQuery>> = {}) {
  jest.spyOn(listQueryModule, "useCustomerBookingsListQuery").mockReturnValue({
    items: [], counts: { active: 0, completed: 0, all: 0 },
    isPending: false, isError: false, isRefetching: false, isFetchingNextPage: false,
    hasNextPage: false, fetchNextPage: jest.fn(), refetch: jest.fn(), dataUpdatedAt: Date.now(),
    ...overrides,
  } as ReturnType<typeof listQueryModule.useCustomerBookingsListQuery>);
}

describe("MyBookingsScreen entry state from Booking Details' search launcher", () => {
  beforeEach(() => {
    mockListQuery();
    jest.spyOn(homeQueryModule, "useCustomerHomeQuery").mockReturnValue({
      data: undefined,
    } as ReturnType<typeof homeQueryModule.useCustomerHomeQuery>);
  });
  afterEach(() => jest.restoreAllMocks());

  it("pre-fills the search box from initialSearch", () => {
    const { getByDisplayValue } = renderBookings({ initialSearch: "AC Service" });
    expect(getByDisplayValue("AC Service")).toBeTruthy();
  });

  it("auto-opens the filter sheet when openFilter is set", () => {
    const { getByText } = renderBookings({ openFilter: true });
    expect(getByText("Filter bookings")).toBeTruthy();
  });

  it("does not force the filter sheet open on an ordinary tab tap", () => {
    const { queryByText } = renderBookings(undefined);
    expect(queryByText("Filter bookings")).toBeNull();
  });
});
