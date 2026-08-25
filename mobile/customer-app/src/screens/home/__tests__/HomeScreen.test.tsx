import React from "react";
import { cleanup, fireEvent, waitFor } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import { renderWithProviders } from "../../../testing/renderWithProviders";
import { HomeScreen } from "../HomeScreen";
import * as homeQueryModule from "../../../api/home/useCustomerHomeQuery";
import { DEFAULT_HOME_SECTIONS, type CustomerHome, type HomeCampaign, type HomeQuickIssue } from "../../../domain/customerHome";
import { asAddressId, asCategoryId, asServiceBookingId, asVerticalId } from "../../../domain/ids";
import { parseServerTimestamp } from "../../../domain/dates";
import { recordHomeCampaignEvent } from "../../../api/home/customerHomeCampaignApi";
import { useGlobalServicesQuery } from "../../../api/globalServices/useGlobalServicesQuery";

jest.mock("../../../api/home/customerHomeCampaignApi", () => ({
  recordHomeCampaignEvent: jest.fn().mockResolvedValue({ recorded: true }),
}));
jest.mock("../../../api/home/useCustomerHomeQuery", () => ({
  useCustomerHomeQuery: jest.fn(),
}));
jest.mock("../../../api/globalServices/useGlobalServicesQuery", () => ({
  useGlobalServicesQuery: jest.fn(),
}));

const Tab = createBottomTabNavigator();
let lastAssistantParams: unknown = "not-navigated";

function CapturingAssistantScreen(props: { route?: { params: unknown } }) {
  lastAssistantParams = props.route?.params;
  return null;
}

function EmptyScreen() {
  return null;
}

function renderHome() {
  lastAssistantParams = "not-navigated";
  return renderWithProviders(
    <NavigationContainer>
      <Tab.Navigator screenOptions={{ headerShown: false }}>
        <Tab.Screen name="Home" component={HomeScreen} />
        <Tab.Screen name="Assistant" component={CapturingAssistantScreen} />
        <Tab.Screen name="Bookings" component={EmptyScreen} />
      </Tab.Navigator>
    </NavigationContainer>,
  );
}

const heroCampaign: HomeCampaign = {
  campaignId: "campaign-hero",
  placement: "home_hero",
  variant: "cinematic",
  themeKey: "ink",
  sectionTitle: null,
  priority: 100,
  sponsored: true,
  badge: "Sponsored",
  title: "Monsoon Home Care",
  subtitle: "Keep your home fresh and worry-free this season.",
  offerText: "Save 20% today",
  imageUrl: "https://res.cloudinary.com/demo/image/upload/sample.jpg",
  actionLabel: "Book now",
  actionUrl: null,
  categorySlug: "home_services",
  serviceGroupSlug: null,
  startsAt: null,
  endsAt: "2026-08-31T18:29:59Z",
};

const trustCampaigns: HomeCampaign[] = [
  ["trust-verified", "Verified providers", "Business and identity checks completed", "Verified"],
  ["trust-estimates", "Clear estimates", "Approve the scope before paid work begins", "Estimate"],
  ["trust-warranty", "Warranty protection", "Provider-owned service warranty applies", "Warranty"],
  ["trust-tracking", "Live job tracking", "Follow assignment and visit progress", "Tracking"],
].map(([campaignId, title, subtitle, badge], index) => ({
  ...heroCampaign,
  campaignId,
  placement: "home_trust",
  variant: "promise",
  title,
  subtitle,
  badge,
  offerText: null,
  priority: 100 - index,
  sponsored: false,
  actionLabel: "Learn more",
  categorySlug: null,
  endsAt: null,
}));

function baseHome(overrides: Partial<CustomerHome> = {}): CustomerHome {
  return {
    responseVersion: 4,
    address: { addressId: asAddressId("addr-1"), city: "Ludhiana", zipcode: "141001", isDefault: true },
    serviceability: { zipcode: "141001", checked: true },
    enabledVerticals: [{ verticalId: asVerticalId("v-1"), key: "home_services", label: "Home Services", icon: "home-outline" }],
    bookableCategories: [{ categoryId: asCategoryId("cat-1"), name: "Home Services", slug: "home_services", iconUrl: null, description: null, startingPrice: null }],
    bookableServiceGroups: [
      { serviceGroupId: "group-ac", name: "AC & HVAC", slug: "ac-hvac", description: null, iconUrl: null, categoryId: asCategoryId("cat-1"), categorySlug: "home_services" },
      { serviceGroupId: "group-plumbing", name: "Plumbing", slug: "plumbing", description: null, iconUrl: null, categoryId: asCategoryId("cat-1"), categorySlug: "home_services" },
    ],
    bookableMasterServices: [],
    campaigns: [heroCampaign, ...trustCampaigns],
    sections: DEFAULT_HOME_SECTIONS,
    quickIssues: [],
    activeBooking: null,
    activeBookings: [],
    activeBookingTotal: 0,
    unreadNotificationCount: 3,
    season: "monsoon",
    seasonLabel: "Monsoon picks",
    capabilities: { bargainAvailable: true, photoAttachAvailable: true, chatbotLanguageSelectable: true },
    ...overrides,
  };
}

function issue(index: number, intent: HomeQuickIssue["intent"] = "repair"): HomeQuickIssue {
  return {
    issueId: `issue-${index}`,
    label: `Problem ${index}`,
    categoryId: asCategoryId("cat-1"),
    categorySlug: "home_services",
    categoryName: "Home Services",
    intent,
  };
}

function mockHomeQuery(partial: Partial<ReturnType<typeof homeQueryModule.useCustomerHomeQuery>>) {
  (homeQueryModule.useCustomerHomeQuery as jest.Mock).mockReturnValue({
    isPending: false,
    isError: false,
    isRefetching: false,
    data: undefined,
    refetch: jest.fn(),
    ...partial,
  } as ReturnType<typeof homeQueryModule.useCustomerHomeQuery>);
}

describe("HomeScreen selected editorial marketplace", () => {
  beforeEach(() => {
    (recordHomeCampaignEvent as jest.Mock).mockClear();
    (useGlobalServicesQuery as jest.Mock).mockReturnValue({
      isPending: false,
      isError: false,
      refetch: jest.fn(),
      data: [
        { id: "digital-web", name: "Web Development", tagline: "Modern web products", description: null, iconUrl: null },
        { id: "digital-app", name: "Mobile App Dev", tagline: "Native mobile products", description: null, iconUrl: null },
        { id: "digital-ai", name: "AI & ML", tagline: "Practical AI systems", description: null, iconUrl: null },
      ],
    });
  });

  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
  });

  it("keeps the missing-location state", () => {
    mockHomeQuery({ data: baseHome({ address: null, serviceability: null }) });
    const view = renderHome();
    expect(view.getByText("Where do you need service?")).toBeTruthy();
    expect(view.getByText("Set your location")).toBeTruthy();
    expect(view.getByText("Web & mobile development")).toBeTruthy();
  });

  it("keeps the unserviceable location state", () => {
    mockHomeQuery({ data: baseHome({ serviceability: { zipcode: "999999", checked: false } }) });
    const view = renderHome();
    expect(view.getByText(/Not available in your area yet/)).toBeTruthy();
    expect(view.getByText(/999999/)).toBeTruthy();
    expect(view.getByText("Web & mobile development")).toBeTruthy();
  });

  it("renders the selected branded viewport using only live aggregate fields", async () => {
    mockHomeQuery({ data: baseHome() });
    const view = renderHome();

    expect(view.queryByLabelText("Fuvay")).toBeNull();
    expect(view.getByLabelText(/Ludhiana, 141001/)).toBeTruthy();
    expect(view.getByLabelText("Notifications, 3 unread")).toBeTruthy();
    expect(view.getByText("Monsoon Home Care")).toBeTruthy();
    expect(view.getByText("Popular services")).toBeTruthy();
    expect(view.getByText("AC & HVAC")).toBeTruthy();
    expect(view.getByText("Plumbing")).toBeTruthy();
    expect(view.getByText("Verified providers")).toBeTruthy();
    expect(view.getByText("Clear estimates")).toBeTruthy();
    expect(view.queryByText("Ideas and offers")).toBeNull();
    expect(view.queryByText("Fuvay Digital Studio")).toBeNull();
    expect(view.getByText("View all")).toBeTruthy();

    await waitFor(() => expect(recordHomeCampaignEvent).toHaveBeenCalledWith({
      campaignId: "campaign-hero",
      eventType: "delivered",
      placement: "home_hero",
    }));
  });

  it("opens a service group through its real parent booking category", () => {
    mockHomeQuery({ data: baseHome() });
    const view = renderHome();
    fireEvent.press(view.getByText("AC & HVAC"));
    expect(lastAssistantParams).toEqual({
      source: "service_card",
      categoryId: "cat-1",
      categoryName: "AC & HVAC",
      categorySlug: "home_services",
      serviceGroupSlug: "ac-hvac",
      masterServiceId: null,
      zipcode: "141001",
      existingDraftId: null,
      preselectedIssueId: null,
    });
  });

  it("records campaign clicks and opens the mapped category", async () => {
    mockHomeQuery({ data: baseHome() });
    const view = renderHome();
    fireEvent.press(view.getByLabelText("Book now: Monsoon Home Care"));

    expect(lastAssistantParams).toMatchObject({ categoryId: "cat-1", categorySlug: "home_services" });
    await waitFor(() => expect(recordHomeCampaignEvent).toHaveBeenCalledWith({
      campaignId: "campaign-hero",
      eventType: "clicked",
      placement: "home_hero",
    }));
  });

  it("shows a compact active booking without inventing an ETA", () => {
    const booking = {
      bookingId: asServiceBookingId("booking-1"), bookingNumber: "SB-2026-01", status: "on_the_way",
      createdAt: parseServerTimestamp("2026-08-01T09:00:00Z", "createdAt"), assignmentStatus: "assigned",
      issueSummary: "AC not cooling", serviceName: "AC Repair", preferredDate: null, preferredTimeWindow: null,
      providerName: "Guramrit", scheduledDate: "2026-08-23", scheduledTimeWindow: "10:30-11:30",
      provider: { name: "Guramrit", verified: true, rating: 4.8, reviewCount: 12, badges: [] },
      technician: { name: "Rakesh Kumar", role: "Technician", photoUrl: null, rating: 4.7, reviewCount: 8 },
    };
    mockHomeQuery({ data: baseHome({ activeBooking: booking, activeBookings: [booking], activeBookingTotal: 1 }) });
    const view = renderHome();
    expect(view.getAllByText("AC Repair").length).toBeGreaterThan(0);
    expect(view.getAllByText("Rakesh Kumar").length).toBeGreaterThan(0);
    expect(view.getAllByLabelText(/track booking/).length).toBeGreaterThan(0);
    expect(view.queryByText(/arriving|\d+ min/i)).toBeNull();
  });

  it("shows eligible master services separately from the service-group rail", () => {
    mockHomeQuery({ data: baseHome({
      bookableMasterServices: [{
        masterServiceId: "service-ac-repair", name: "AC Repair", slug: "ac-repair",
        description: "Diagnosis and repair", iconUrl: null,
        serviceGroupId: "group-ac", serviceGroupName: "AC & HVAC", serviceGroupSlug: "ac-hvac",
        categoryId: asCategoryId("cat-1"), categorySlug: "home_services",
      }],
    }) });
    const view = renderHome();
    expect(view.getByText("Recommended for you")).toBeTruthy();
    expect(view.getAllByText("AC Repair").length).toBeGreaterThan(0);
    expect(view.getByText("AVAILABLE IN YOUR AREA")).toBeTruthy();
    expect(view.getByLabelText("Book AC & HVAC")).toBeTruthy();
    expect(view.getByLabelText("Book Plumbing")).toBeTruthy();
    fireEvent.press(view.getAllByLabelText("Book AC Repair")[0]);
    expect(lastAssistantParams).toMatchObject({
      serviceGroupSlug: "ac-hvac",
      masterServiceId: "service-ac-repair",
    });
  });

  it("partitions live problems without repeating them and opens the selected issue", () => {
    const quickIssues = [
      ...Array.from({ length: 8 }, (_, index) => issue(index + 1)),
      issue(9, "repair"),
      issue(10, "consult"),
      issue(11, null),
    ];
    const problemSectionKeys = new Set(["featured_problems", "repair_problems", "consultation_problems", "more_problems"]);
    mockHomeQuery({ data: baseHome({
      quickIssues,
      sections: DEFAULT_HOME_SECTIONS.map(section => problemSectionKeys.has(section.key) ? { ...section, enabled: true } : section),
    }) });
    const view = renderHome();

    expect(view.getByText("What needs fixing?")).toBeTruthy();
    expect(view.getByText("Repairs you can book now")).toBeTruthy();
    expect(view.getByText("Get an expert opinion")).toBeTruthy();
    expect(view.getByText("More ways we can help")).toBeTruthy();
    for (const item of quickIssues) expect(view.getAllByText(item.label)).toHaveLength(1);

    fireEvent.press(view.getByLabelText("Problem 10, Home Services"));
    expect(lastAssistantParams).toMatchObject({
      categoryId: "cat-1",
      categorySlug: "home_services",
      preselectedIssueId: "issue-10",
    });
  });
});
