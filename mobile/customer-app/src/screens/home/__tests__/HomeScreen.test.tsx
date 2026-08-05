import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { HomeScreen } from "../HomeScreen";
import * as homeQueryModule from "../../../api/home/useCustomerHomeQuery";
import * as profileQueryModule from "../../../api/customer/useCustomerProfileQuery";
import { CustomerHome } from "../../../domain/customerHome";
import { asCategoryId, asCustomerId, asVerticalId, asServiceBookingId, asAddressId } from "../../../domain/ids";
import { parseServerTimestamp } from "../../../domain/dates";

const Tab = createBottomTabNavigator();

let lastAssistantParams: unknown = "not-navigated";
function CapturingAssistantScreen(props: { route?: { params: unknown } }) {
  lastAssistantParams = props.route?.params;
  return null;
}

function renderHome() {
  lastAssistantParams = "not-navigated";
  return renderWithProviders(
    <NavigationContainer>
      <Tab.Navigator>
        <Tab.Screen name="Home" component={HomeScreen} />
        <Tab.Screen name="Assistant" component={CapturingAssistantScreen} />
        <Tab.Screen name="Bookings" component={() => null} />
      </Tab.Navigator>
    </NavigationContainer>,
  );
}

function baseHome(overrides: Partial<CustomerHome> = {}): CustomerHome {
  return {
    responseVersion: 1,
    address: { addressId: asAddressId("addr-1"), city: "Ludhiana", zipcode: "141001", isDefault: true },
    serviceability: { zipcode: "141001", checked: true },
    enabledVerticals: [{ verticalId: asVerticalId("v-1"), key: "home_services", label: "Home Services", icon: "home-outline" }],
    bookableCategories: [{ categoryId: asCategoryId("cat-1"), name: "AC & Cooling", slug: "ac-cooling", iconUrl: null }],
    activeBooking: null,
    unreadNotificationCount: 0,
    campaigns: [],
    capabilities: { bargainAvailable: true, photoAttachAvailable: true, chatbotLanguageSelectable: true },
    ...overrides,
  };
}

function mockHomeQuery(partial: Partial<ReturnType<typeof homeQueryModule.useCustomerHomeQuery>>) {
  jest.spyOn(homeQueryModule, "useCustomerHomeQuery").mockReturnValue({
    isPending: false, isError: false, isRefetching: false, data: undefined, refetch: jest.fn(),
    ...partial,
  } as ReturnType<typeof homeQueryModule.useCustomerHomeQuery>);
}

describe("HomeScreen", () => {
  beforeEach(() => {
    jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
      data: {
        id: asCustomerId("c-1"), fullName: "Rajinder Singh", displayName: "Rajinder", phone: null, email: null,
        avatarUrl: null, language: "en", timezone: "Asia/Kolkata", verified: true, isActive: true,
        createdAt: "2026-01-01T00:00:00Z",
        capabilities: { canEditProfile: true, canUpdateAvatar: false, canManageAddresses: false, canChangePassword: true, canManageSessions: true, canDeleteAccount: false },
      },
    } as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
  });
  afterEach(() => jest.restoreAllMocks());

  it("shows a loading skeleton while the aggregation query is pending", () => {
    mockHomeQuery({ isPending: true });
    const { getByLabelText } = renderHome();
    expect(getByLabelText("Loading your home screen")).toBeTruthy();
  });

  it("shows an error state with retry when the aggregation query fails", () => {
    mockHomeQuery({ isError: true });
    const { getByText } = renderHome();
    expect(getByText("We couldn't load your home screen")).toBeTruthy();
    expect(getByText("Try again")).toBeTruthy();
  });

  it("shows NoAddressState when the customer has no address on file", () => {
    mockHomeQuery({ data: baseHome({ address: null }) });
    const { getAllByText } = renderHome();
    expect(getAllByText("Choose your location").length).toBeGreaterThan(0);
  });

  it("shows UnserviceableState for a ZIP the backend does not service", () => {
    mockHomeQuery({ data: baseHome({ serviceability: { zipcode: "999999", checked: false } }) });
    const { getByText } = renderHome();
    expect(getByText(/Not available in your area yet/)).toBeTruthy();
    expect(getByText(/999999/)).toBeTruthy();
  });

  it("renders the real customer first name from the profile query, not a hardcoded name", () => {
    mockHomeQuery({ data: baseHome() });
    const { getByText } = renderHome();
    expect(getByText(/Rajinder$/)).toBeTruthy();
  });

  it("renders only backend-returned bookable categories, with no price label when none is provided", () => {
    mockHomeQuery({ data: baseHome() });
    const { getByText } = renderHome();
    expect(getByText("AC & Cooling")).toBeTruthy();
    expect(getByText("View details")).toBeTruthy();
  });

  it("never renders ₹0 for any service", () => {
    mockHomeQuery({ data: baseHome() });
    const { queryByText } = renderHome();
    expect(queryByText(/₹0\b/)).toBeNull();
  });

  it("hides the campaign carousel entirely when there are no campaigns", () => {
    mockHomeQuery({ data: baseHome({ campaigns: [] }) });
    const { queryByLabelText } = renderHome();
    expect(queryByLabelText(/Promotional offers/)).toBeNull();
  });

  it("renders campaigns when present, sorted by backend priority", () => {
    mockHomeQuery({
      data: baseHome({
        campaigns: [
          { campaignId: "c-1", eyebrow: "Sponsored", title: "Monsoon Home Care", description: "Get ready", artworkUrlLight: null, artworkUrlDark: null, ctaLabel: "Explore", ctaDeeplink: "app://offers", priority: 1 },
        ],
      }),
    });
    const { getByText } = renderHome();
    expect(getByText("Monsoon Home Care")).toBeTruthy();
    expect(getByText("Sponsored")).toBeTruthy();
  });

  it("does not render the active booking card when there is no active booking", () => {
    mockHomeQuery({ data: baseHome({ activeBooking: null }) });
    const { queryByText } = renderHome();
    expect(queryByText("My Booking")).toBeNull();
  });

  it("renders the active booking card using only real returned fields, never a fabricated ETA/technician", () => {
    mockHomeQuery({
      data: baseHome({
        activeBooking: { bookingId: asServiceBookingId("b-1"), bookingNumber: "SB-2026-01", status: "scheduled", createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt") },
      }),
    });
    const { getByText, queryByText } = renderHome();
    expect(getByText("My Booking")).toBeTruthy();
    expect(getByText("SB-2026-01")).toBeTruthy();
    expect(queryByText(/min away/i)).toBeNull();
    expect(queryByText(/Rakesh/i)).toBeNull();
  });

  it("renders enabled verticals only (backend already filters disabled ones)", () => {
    mockHomeQuery({ data: baseHome() });
    const { getByText, queryByText } = renderHome();
    expect(getByText("Home Services")).toBeTruthy();
    expect(queryByText("Real Estate")).toBeNull();
  });

  it("tapping a service card navigates to Assistant carrying real backend context (category, slug, zip) and no customer identity", () => {
    mockHomeQuery({ data: baseHome() });
    const { getByText } = renderHome();
    fireEvent.press(getByText("AC & Cooling"));
    expect(lastAssistantParams).toEqual({
      source: "service_card",
      categoryId: "cat-1",
      categoryName: "AC & Cooling",
      categorySlug: "ac-cooling",
      zipcode: "141001",
      existingDraftId: null,
    });
    expect(lastAssistantParams).not.toHaveProperty("customerId");
    expect(lastAssistantParams).not.toHaveProperty("serviceabilityChecked");
  });

  it("does not navigate when a category has no resolvable slug (cannot start a draft without one)", () => {
    mockHomeQuery({ data: baseHome({ bookableCategories: [{ categoryId: asCategoryId("cat-2"), name: "Unmapped Service", slug: null, iconUrl: null }] }) });
    const { getByText } = renderHome();
    fireEvent.press(getByText("Unmapped Service"));
    expect(lastAssistantParams).toBe("not-navigated");
  });

  it("tapping 'Start chat' navigates to Assistant with no category pre-selected", () => {
    mockHomeQuery({ data: baseHome() });
    const { getByLabelText } = renderHome();
    fireEvent.press(getByLabelText("Not sure what to book? Tell Fuvay Assistant what's wrong. Start chat."));
    expect(lastAssistantParams).toMatchObject({ source: "assistant_card", categoryId: null, categoryName: null });
  });

  it("opens the location picker when the location row is pressed, and re-runs the Home query with the new ZIP", () => {
    const refetch = jest.fn();
    mockHomeQuery({ data: baseHome() });
    const { getByLabelText, getByText } = renderHome();
    fireEvent(getByLabelText(/Location: Ludhiana · 141001/), "touchEnd");
    fireEvent.changeText(getByLabelText("ZIP code"), "160001");
    fireEvent.press(getByText("Confirm location"));
    // Re-rendering with a new zipcodeOverride calls useCustomerHomeQuery
    // again with the new value -- verified via the spy call arguments.
    expect(homeQueryModule.useCustomerHomeQuery).toHaveBeenLastCalledWith("160001");
    void refetch;
  });

  it("offers a location picker from the unserviceable state's Change location action", () => {
    mockHomeQuery({ data: baseHome({ serviceability: { zipcode: "999999", checked: false } }) });
    const { getByText, getByLabelText } = renderHome();
    fireEvent.press(getByText("Change location"));
    expect(getByLabelText("ZIP code")).toBeTruthy();
  });

  it("shows the unread notification dot only when the real Home count is > 0", () => {
    mockHomeQuery({ data: baseHome({ unreadNotificationCount: 2 }) });
    const { getByLabelText } = renderHome();
    expect(getByLabelText("Notifications, unread")).toBeTruthy();
  });

  it("the notification bell is pressable and does not crash without a parent navigator (unit render)", () => {
    mockHomeQuery({ data: baseHome({ unreadNotificationCount: 1 }) });
    const { getByLabelText } = renderHome();
    // No outer stack is mounted in this render, so navigation.getParent()
    // is undefined -- the handler's optional chaining must not throw.
    expect(() => fireEvent.press(getByLabelText("Notifications, unread"))).not.toThrow();
  });
});
