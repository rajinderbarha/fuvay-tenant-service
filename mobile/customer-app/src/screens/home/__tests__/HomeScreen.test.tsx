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
    bookableCategories: [{ categoryId: asCategoryId("cat-1"), name: "AC & Cooling", slug: "ac-cooling", iconUrl: null, description: null, startingPrice: null }],
    quickIssues: [],
    activeBooking: null,
    activeBookings: [],
    activeBookingTotal: 0,
    unreadNotificationCount: 0,
    campaigns: [],
    sections: [],
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

  it("renders only backend-returned bookable categories, with no price row when none is provided", () => {
    // startingPrice null => the card omits the "Starting at" row entirely
    // rather than fabricating a figure or rendering a zero.
    mockHomeQuery({ data: baseHome() });
    const { getByText, queryByText } = renderHome();
    expect(getByText("AC & Cooling")).toBeTruthy();
    expect(queryByText("Starting at")).toBeNull();
    expect(queryByText(/₹/)).toBeNull();
  });

  it("renders a real 'Starting at' price when the backend provides one", () => {
    mockHomeQuery({
      data: baseHome({
        bookableCategories: [
          { categoryId: asCategoryId("cat-1"), name: "AC & Cooling", slug: "ac-cooling", iconUrl: null, description: "Service, repair & more", startingPrice: 800 },
          { categoryId: asCategoryId("cat-2"), name: "Plumbing", slug: "plumbing", iconUrl: null, description: null, startingPrice: null },
        ],
      }),
    });
    const { getByText, getAllByText, queryByText } = renderHome();
    expect(getByText("AC & Cooling")).toBeTruthy();
    expect(getByText("Plumbing")).toBeTruthy();
    expect(getByText("Service, repair & more")).toBeTruthy();
    // Only the priced category shows a price row; the unpriced one does not.
    expect(getAllByText("Starting at")).toHaveLength(1);
    expect(getByText(/₹\s?800/)).toBeTruthy();
    expect(queryByText(/₹0\b/)).toBeNull();
  });

  it("never renders ₹0 for any service", () => {
    // A zero price is "not configured", never a real free service -- see
    // classifyRawAmount, which the card routes every amount through.
    mockHomeQuery({
      data: baseHome({
        bookableCategories: [
          { categoryId: asCategoryId("cat-1"), name: "AC & Cooling", slug: "ac-cooling", iconUrl: null, description: null, startingPrice: 0 },
        ],
      }),
    });
    const { queryByText } = renderHome();
    expect(queryByText(/₹0\b/)).toBeNull();
    expect(queryByText("Starting at")).toBeNull();
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
          { campaignId: "c-1", eyebrow: "Sponsored", title: "Monsoon Home Care", description: "Get ready", artworkUrlLight: null, artworkUrlDark: null, ctaLabel: "Explore", ctaDeeplink: "app://offers", priority: 1,
            style: "hero" as const, placement: "campaign_top" as const, accentColor: null, badgeText: null, endsAt: null },
        ],
      }),
    });
    const { getByText } = renderHome();
    expect(getByText("Monsoon Home Care")).toBeTruthy();
    expect(getByText("Sponsored")).toBeTruthy();
  });

  it("does not render the My Booking section when there is no active booking", () => {
    mockHomeQuery({ data: baseHome({ activeBooking: null }) });
    const { queryByText } = renderHome();
    expect(queryByText("My Booking")).toBeNull();
  });

  it("renders My Booking from real returned fields, never a fabricated ETA or technician", () => {
    mockHomeQuery({
      data: baseHome({
        // Mirrored into both, exactly as the adapter does: `activeBooking` is
        // always `activeBookings[0]`.
        activeBookings: [{
          bookingId: asServiceBookingId("b-1"), bookingNumber: "SB-2026-01", status: "scheduled",
          createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"),
          assignmentStatus: null, issueSummary: null, serviceName: null,
          preferredDate: null, preferredTimeWindow: null, providerName: null, technician: null,
          scheduledDate: null, scheduledTimeWindow: null, provider: null,
        }],
        activeBooking: {
          bookingId: asServiceBookingId("b-1"), bookingNumber: "SB-2026-01", status: "scheduled",
          createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"),
          assignmentStatus: null, issueSummary: null, serviceName: null,
          preferredDate: null, preferredTimeWindow: null, providerName: null, technician: null,
          scheduledDate: null, scheduledTimeWindow: null, provider: null,
        },
        activeBookingTotal: 1,
      }),
    });
    const { getByText, queryByText } = renderHome();
    expect(getByText("My Booking")).toBeTruthy();
    // With no service name or issue summary, the title falls back to the
    // booking number rather than inventing one.
    expect(getByText("SB-2026-01")).toBeTruthy();
    // The reference design shows "Arriving in 15 MIN"; nothing computes an
    // ETA, so no such claim may appear.
    expect(queryByText(/min/i)).toBeNull();
    expect(queryByText(/arriving/i)).toBeNull();
    expect(queryByText(/Rakesh/i)).toBeNull();
  });

  it("names the provider with its verification, rating, badges and the committed slot", () => {
    mockHomeQuery({
      data: baseHome({
        // Mirrored into both, exactly as the adapter does: `activeBooking` is
        // always `activeBookings[0]`.
        activeBookings: [{
          bookingId: asServiceBookingId("b-2"), bookingNumber: "SB-2026-02", status: "on_the_way",
          createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"),
          assignmentStatus: "assigned", issueSummary: "AC Not Cooling", serviceName: "AC Repair",
          preferredDate: null, preferredTimeWindow: null, providerName: "Guramrit",
          scheduledDate: "2026-08-07", scheduledTimeWindow: "10:30-11:30",
          provider: {
            name: "Guramrit", verified: true, rating: 4.8, reviewCount: 12,
            badges: [{ name: "Verified Business", icon: null, color: null }],
          },
          technician: { name: "Rakesh Kumar", role: "Service technician", photoUrl: null, rating: 4.6, reviewCount: 12 },
        }],
        activeBooking: {
          bookingId: asServiceBookingId("b-2"), bookingNumber: "SB-2026-02", status: "on_the_way",
          createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"),
          assignmentStatus: "assigned", issueSummary: "AC Not Cooling", serviceName: "AC Repair",
          preferredDate: null, preferredTimeWindow: null, providerName: "Guramrit",
          scheduledDate: "2026-08-07", scheduledTimeWindow: "10:30-11:30",
          provider: {
            name: "Guramrit", verified: true, rating: 4.8, reviewCount: 12,
            badges: [{ name: "Verified Business", icon: null, color: null }],
          },
          technician: { name: "Rakesh Kumar", role: "Service technician", photoUrl: null, rating: 4.6, reviewCount: 12 },
        },
        activeBookingTotal: 1,
      }),
    });
    const { getByText, queryByText } = renderHome();
    expect(getByText("AC Repair")).toBeTruthy();
    expect(getByText("Guramrit")).toBeTruthy();
    // The provider's rating, not the technician's -- the card leads with who
    // the customer booked.
    expect(getByText("4.8")).toBeTruthy();
    expect(getByText("Verified Business")).toBeTruthy();
    expect(getByText("· Rakesh Kumar")).toBeTruthy();
    // The COMMITTED slot, not the requested one.
    expect(getByText("7 Aug 10:30-11:30")).toBeTruthy();
    expect(getByText("On the way")).toBeTruthy();
    // Still no invented ETA.
    expect(queryByText(/arriving/i)).toBeNull();
  });

  it("shows a requested window only as such, never as a committed slot", () => {
    // preferred_* is what the customer ASKED for. Rendering it identically to a
    // scheduled slot would present a request as the provider's promise.
    mockHomeQuery({
      data: baseHome({
        // Mirrored into both, exactly as the adapter does: `activeBooking` is
        // always `activeBookings[0]`.
        activeBookings: [{
          bookingId: asServiceBookingId("b-4"), bookingNumber: "SB-2026-04", status: "pending_assignment",
          createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"),
          assignmentStatus: "unassigned", issueSummary: null, serviceName: "AC Service",
          preferredDate: "2026-08-12", preferredTimeWindow: "14:00-15:00",
          scheduledDate: null, scheduledTimeWindow: null,
          provider: { name: "Guramrit", verified: false, rating: null, reviewCount: 0, badges: [] },
          providerName: "Guramrit", technician: null,
        }],
        activeBooking: {
          bookingId: asServiceBookingId("b-4"), bookingNumber: "SB-2026-04", status: "pending_assignment",
          createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"),
          assignmentStatus: "unassigned", issueSummary: null, serviceName: "AC Service",
          preferredDate: "2026-08-12", preferredTimeWindow: "14:00-15:00",
          scheduledDate: null, scheduledTimeWindow: null,
          provider: { name: "Guramrit", verified: false, rating: null, reviewCount: 0, badges: [] },
          providerName: "Guramrit", technician: null,
        },
        activeBookingTotal: 1,
      }),
    });
    const { getByText, queryByText } = renderHome();
    expect(getByText("Guramrit")).toBeTruthy();
    // No rating, no badges, no verified tick: none of them are earned here.
    expect(queryByText(/^\d\.\d$/)).toBeNull();
    // A fixed future date, not "today": the label collapses to "Today" for
    // the current date, which would make this assertion pass or fail
    // depending on the day the suite runs.
    expect(getByText("12 Aug 14:00-15:00")).toBeTruthy();
  });

  it("omits the star when the technician has not been reviewed yet", () => {
    // staff_rating_summaries returns null until real reviews exist; an
    // unearned rating is worse than none.
    mockHomeQuery({
      data: baseHome({
        // Mirrored into both, exactly as the adapter does: `activeBooking` is
        // always `activeBookings[0]`.
        activeBookings: [{
          bookingId: asServiceBookingId("b-3"), bookingNumber: "SB-2026-03", status: "assigned",
          createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"),
          assignmentStatus: "assigned", issueSummary: null, serviceName: "Pipe Repair",
          preferredDate: null, preferredTimeWindow: null, providerName: null,
          scheduledDate: null, scheduledTimeWindow: null, provider: null,
          technician: { name: "Dhiman", role: "Service technician", photoUrl: null, rating: null, reviewCount: 0 },
        }],
        activeBooking: {
          bookingId: asServiceBookingId("b-3"), bookingNumber: "SB-2026-03", status: "assigned",
          createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"),
          assignmentStatus: "assigned", issueSummary: null, serviceName: "Pipe Repair",
          preferredDate: null, preferredTimeWindow: null, providerName: null,
          scheduledDate: null, scheduledTimeWindow: null, provider: null,
          technician: { name: "Dhiman", role: "Service technician", photoUrl: null, rating: null, reviewCount: 0 },
        },
        activeBookingTotal: 1,
      }),
    });
    const { getByText, queryByText } = renderHome();
    expect(getByText("Dhiman")).toBeTruthy();
    expect(queryByText(/^\d\.\d$/)).toBeNull();
  });

  it("renders enabled verticals only (backend already filters disabled ones)", () => {
    // Needs TWO verticals to assert anything about the switcher: with a
    // single vertical it is intentionally hidden (a one-option switcher is
    // not a switcher -- it rendered as a full-width brand pill that looked
    // like a primary action but did nothing). Disabled verticals are still
    // absent because the backend never sends them.
    mockHomeQuery({
      data: baseHome({
        enabledVerticals: [
          { verticalId: asVerticalId("v-1"), key: "home_services", label: "Home Services", icon: "home-outline" },
          { verticalId: asVerticalId("v-2"), key: "beauty", label: "Beauty", icon: "sparkles-outline" },
        ],
      }),
    });
    const { getByText, queryByText } = renderHome();
    expect(getByText("Home Services")).toBeTruthy();
    expect(getByText("Beauty")).toBeTruthy();
    expect(queryByText("Real Estate")).toBeNull();
  });

  it("tapping a quick issue carries the issue id so the Assistant can skip its picker", () => {
    mockHomeQuery({ data: baseHome({
      quickIssues: [{
        issueId: "issue-1", label: "AC Not Cooling",
        categoryId: asCategoryId("cat-1"), categorySlug: "ac-cooling", categoryName: "AC & Cooling", iconUrl: null,
      }],
    }) });
    const { getByText } = renderHome();
    fireEvent.press(getByText("AC Not Cooling"));
    expect(lastAssistantParams).toEqual({
      source: "service_card",
      categoryId: "cat-1",
      categoryName: "AC & Cooling",
      categorySlug: "ac-cooling",
      zipcode: "141001",
      existingDraftId: null,
      preselectedIssueId: "issue-1",
    });
  });

  it("drops a quick issue whose category has no slug rather than rendering a dead chip", () => {
    // The Assistant is entered by category slug; a chip that cannot open
    // is worse than an absent one.
    mockHomeQuery({ data: baseHome({
      quickIssues: [{
        issueId: "issue-2", label: "Drain Blocked",
        categoryId: asCategoryId("cat-9"), categorySlug: null, iconUrl: null, categoryName: "Plumbing",
      }],
    }) });
    const { queryByText } = renderHome();
    expect(queryByText("Drain Blocked")).toBeNull();
  });

  it("renders the sections the backend enabled, in the backend's order", () => {
    // Re-ordering Home or hiding a section used to need an app release.
    mockHomeQuery({
      data: baseHome({
        sections: [
          { key: "trust_benefits", order: 10, title: null },
          { key: "service_grid", order: 20, title: null },
        ],
      }),
    });
    const { getByText, queryByText } = renderHome();
    expect(getByText("What you're promised")).toBeTruthy();
    expect(getByText("Services Nearby")).toBeTruthy();
    // Not listed by the backend, so not drawn -- even though this build can.
    expect(queryByText("Not sure what to book?")).toBeNull();
  });

  it("honours an admin's section heading override", () => {
    mockHomeQuery({
      data: baseHome({
        sections: [{ key: "service_grid", order: 10, title: "Services in Ludhiana" }],
      }),
    });
    const { getByText, queryByText } = renderHome();
    expect(getByText("Services in Ludhiana")).toBeTruthy();
    expect(queryByText("Services Nearby")).toBeNull();
  });

  it("falls back to its shipped layout when the backend sends no sections", () => {
    // An empty list is "no instruction" from an older backend -- never an
    // instruction to draw nothing.
    mockHomeQuery({ data: baseHome({ sections: [] }) });
    const { getByText, queryByText } = renderHome();
    expect(getByText("Services Nearby")).toBeTruthy();
    expect(getByText("Not sure what to book?")).toBeTruthy();
    // The shipped order matches what customers actually see: both of these are
    // switched off in the layout settings, so the fallback must not reintroduce
    // them. Their renderers stay wired for turning back on from admin.
    expect(queryByText("What you're promised")).toBeNull();
    expect(queryByText(/How it works/i)).toBeNull();
  });

  it("skips a section key this build has no renderer for", () => {
    mockHomeQuery({
      data: baseHome({
        sections: [
          { key: "loyalty_points_widget", order: 10, title: null },
          { key: "service_grid", order: 20, title: null },
        ],
      }),
    });
    const { getByText } = renderHome();
    // The unknown key is ignored rather than crashing the screen, so a newer
    // backend can add sections ahead of an app release.
    expect(getByText("Services Nearby")).toBeTruthy();
  });

  it("hides the vertical switcher entirely when only one vertical is enabled", () => {
    mockHomeQuery({ data: baseHome() }); // fixture has exactly one vertical
    const { queryByRole } = renderHome();
    expect(queryByRole("tablist")).toBeNull();
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
      preselectedIssueId: null,
    });
    expect(lastAssistantParams).not.toHaveProperty("customerId");
    expect(lastAssistantParams).not.toHaveProperty("serviceabilityChecked");
  });

  it("does not navigate when a category has no resolvable slug (cannot start a draft without one)", () => {
    mockHomeQuery({ data: baseHome({ bookableCategories: [{ categoryId: asCategoryId("cat-2"), name: "Unmapped Service", slug: null, iconUrl: null, description: null, startingPrice: null }] }) });
    const { getByText } = renderHome();
    fireEvent.press(getByText("Unmapped Service"));
    expect(lastAssistantParams).toBe("not-navigated");
  });

  it("tapping the assistant card navigates to Assistant with no category pre-selected", () => {
    mockHomeQuery({ data: baseHome() });
    const { getByLabelText } = renderHome();
    fireEvent.press(getByLabelText(
      "Not sure what to book? Describe the problem and Fuvay Assistant takes it from there.",
    ));
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
