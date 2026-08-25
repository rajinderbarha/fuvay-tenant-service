import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { HomeScreen } from "../HomeScreen";
import * as homeQueryModule from "../../../api/home/useCustomerHomeQuery";
import { CustomerHome, DEFAULT_HOME_SECTIONS } from "../../../domain/customerHome";
import { asCategoryId, asVerticalId, asServiceBookingId, asAddressId } from "../../../domain/ids";

const Tab = createBottomTabNavigator();

/**
 * Home renders many lists from one payload, and a repeated React key there is not a
 * cosmetic warning: React reuses the wrong node, so a tile can show one problem's
 * label with another's icon, or lose a tap. This asserts the whole screen renders a
 * realistic payload -- every section on, the full problem list -- without one.
 */
function fullHome(): CustomerHome {
  const issues = Array.from({ length: 24 }, (_, i) => ({
    issueId: `issue-${i}`,
    label: `Problem ${i}`,
    categoryId: asCategoryId(`cat-${i % 4}`),
    categorySlug: `cat-${i % 4}`,
    categoryName: `Category ${i % 4}`,
    intent: i % 2 === 0 ? ("repair" as const) : ("consult" as const),
  }));
  return {
    responseVersion: 1,
    address: { addressId: asAddressId("addr-1"), city: "Ludhiana", zipcode: "141001", isDefault: true },
    serviceability: { zipcode: "141001", checked: true },
    enabledVerticals: [
      { verticalId: asVerticalId("v-1"), key: "home_services", label: "Home Services", icon: "home-outline" },
      { verticalId: asVerticalId("v-2"), key: "coaching", label: "Coaching", icon: "school-outline" },
    ],
    bookableCategories: Array.from({ length: 7 }, (_, i) => ({
      categoryId: asCategoryId(`cat-${i}`), name: `Category ${i}`, slug: `cat-${i}`,
      iconUrl: null, description: null, startingPrice: null,
    })),
    bookableServiceGroups: Array.from({ length: 5 }, (_, i) => ({
      serviceGroupId: `group-${i}`,
      name: `Service group ${i}`,
      slug: `service-group-${i}`,
      description: null,
      iconUrl: null,
      categoryId: asCategoryId(`cat-${i}`),
      categorySlug: `cat-${i}`,
    })),
    bookableMasterServices: Array.from({ length: 8 }, (_, i) => ({
      masterServiceId: `master-${i}`,
      name: `Master service ${i}`,
      slug: `master-service-${i}`,
      description: null,
      iconUrl: null,
      serviceGroupId: `group-${i % 5}`,
      serviceGroupName: `Service group ${i % 5}`,
      serviceGroupSlug: `service-group-${i % 5}`,
      categoryId: asCategoryId(`cat-${i % 5}`),
      categorySlug: `cat-${i % 5}`,
    })),
    campaigns: [],
    sections: DEFAULT_HOME_SECTIONS,
    quickIssues: issues,
    activeBooking: null,
    activeBookings: Array.from({ length: 3 }, (_, i) => ({
      bookingId: asServiceBookingId(`bk-${i}`),
      status: "confirmed",
      statusLabel: "Request confirmed",
      serviceName: `Service ${i}`,
      scheduledDate: null,
      scheduledTimeWindow: null,
      provider: null,
    })) as unknown as CustomerHome["activeBookings"],
    activeBookingTotal: 37,
    unreadNotificationCount: 0,
    season: "monsoon",
    seasonLabel: "Monsoon picks",
    capabilities: { bargainAvailable: true, photoAttachAvailable: true, chatbotLanguageSelectable: true },
  };
}

describe("Home list keys", () => {
  afterEach(() => jest.restoreAllMocks());

  it("renders every section of a full payload without a duplicate React key", () => {
    jest.spyOn(homeQueryModule, "useCustomerHomeQuery").mockReturnValue({
      isPending: false, isError: false, isRefetching: false, data: fullHome(), refetch: jest.fn(),
    } as unknown as ReturnType<typeof homeQueryModule.useCustomerHomeQuery>);
    const errors: string[] = [];
    const spy = jest.spyOn(console, "error").mockImplementation((...args) => {
      errors.push(args.map(String).join(" "));
    });

    renderWithProviders(
      <NavigationContainer>
        <Tab.Navigator>
          <Tab.Screen name="Home" component={HomeScreen} />
          <Tab.Screen name="Assistant" component={() => null} />
          <Tab.Screen name="Bookings" component={() => null} />
        </Tab.Navigator>
      </NavigationContainer>,
    );

    spy.mockRestore();
    const keyWarnings = errors.filter(e => /same key|unique "key"/i.test(e));
    expect(keyWarnings).toEqual([]);
  });
});
