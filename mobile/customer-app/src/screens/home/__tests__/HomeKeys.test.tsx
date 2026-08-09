import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { HomeScreen } from "../HomeScreen";
import * as homeQueryModule from "../../../api/home/useCustomerHomeQuery";
import * as globalServicesModule from "../../../api/globalServices/useGlobalServicesQuery";
import { CustomerHome } from "../../../domain/customerHome";
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
    iconUrl: null,
    intent: i % 2 === 0 ? ("repair" as const) : ("consult" as const),
  }));
  return {
    responseVersion: 1,
    address: { addressId: asAddressId("addr-1"), city: "Ludhiana", zipcode: "141001", isDefault: true },
    serviceability: { zipcode: "141001", checked: true },
    enabledVerticals: [
      { verticalId: asVerticalId("v-1"), key: "home_services", label: "Home Services", icon: "home-outline" },
      { verticalId: asVerticalId("v-2"), key: "global_services", label: "Global", icon: "globe-outline" },
    ],
    bookableCategories: Array.from({ length: 7 }, (_, i) => ({
      categoryId: asCategoryId(`cat-${i}`), name: `Category ${i}`, slug: `cat-${i}`,
      iconUrl: null, description: null, startingPrice: null,
    })),
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
    campaigns: Array.from({ length: 6 }, (_, i) => ({
      campaignId: `camp-${i}`,
      title: `Campaign ${i}`,
      subtitle: null,
      imageUrl: null,
      ctaLabel: null,
      categoryId: null,
      displayStyle: "strip",
      placement: "campaign_top",
      accentColor: null,
      badgeText: null,
      startsAt: null,
      endsAt: null,
    })) as unknown as CustomerHome["campaigns"],
    // Every section the backend can order, so no node escapes the check.
    sections: [
      "active_booking", "quick_problems", "campaign_top", "service_grid",
      "campaign_after_services", "assistant_entry", "campaign_mid", "problem_circles",
      "campaign_after_circles", "global_services", "campaign_bottom",
      "repair_intent", "consult_intent", "trust_benefits", "how_it_works", "verticals",
    ].map((key, i) => ({ key, order: i * 10, title: null })),
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
    jest.spyOn(globalServicesModule, "useGlobalServicesQuery").mockReturnValue({
      isPending: false, isError: false,
      data: Array.from({ length: 6 }, (_, i) => ({
        id: `gs-${i}`, name: `Global ${i}`, tagline: null, description: null, iconUrl: null,
      })),
    } as unknown as ReturnType<typeof globalServicesModule.useGlobalServicesQuery>);

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
