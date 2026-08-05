import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { NotificationCenterScreen } from "../NotificationCenterScreen";
import * as queriesModule from "../../../api/notifications/useNotificationsQueries";
import { CustomerNotification } from "../../../domain/notification";
import { asNotificationId } from "../../../domain/ids";
import { ServerTimestamp } from "../../../domain/dates";
import { AppProviders } from "../../../providers/AppProviders";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
}));

jest.mock("../../../api/networkState", () => ({
  ...jest.requireActual("../../../api/networkState"),
  isOffline: jest.fn(() => false),
}));
import { isOffline } from "../../../api/networkState";

function notification(overrides: Partial<CustomerNotification> = {}): CustomerNotification {
  return {
    id: asNotificationId("n-1"),
    type: "booking.confirmed",
    title: "AC Repair booking confirmed",
    body: "Booking FUV-2841 has been created successfully.",
    createdAt: "2026-08-01T09:42:00Z" as ServerTimestamp,
    readAt: null,
    readStatus: "unread",
    destination: { kind: "booking", bookingId: "b-1" },
    ...overrides,
  };
}

function mockList(items: CustomerNotification[], opts: {
  isPending?: boolean; isError?: boolean; hasNextPage?: boolean; isRefetching?: boolean; isFetchingNextPage?: boolean;
} = {}) {
  jest.spyOn(queriesModule, "useNotificationsListQuery").mockReturnValue({
    items, total: items.length,
    isPending: !!opts.isPending, isError: !!opts.isError,
    isRefetching: !!opts.isRefetching, isFetchingNextPage: !!opts.isFetchingNextPage,
    hasNextPage: !!opts.hasNextPage, fetchNextPage: jest.fn(), refetch: jest.fn(),
  } as unknown as ReturnType<typeof queriesModule.useNotificationsListQuery>);
}

function mockUnreadCount(count: number | undefined) {
  jest.spyOn(queriesModule, "useUnreadNotificationCountQuery").mockReturnValue({
    data: count,
  } as unknown as ReturnType<typeof queriesModule.useUnreadNotificationCountQuery>);
}

function mockMarkRead() {
  jest.spyOn(queriesModule, "useMarkNotificationReadMutation").mockReturnValue({
    mutate: jest.fn(), isPending: false,
  } as unknown as ReturnType<typeof queriesModule.useMarkNotificationReadMutation>);
}

function mockMarkAllRead(overrides: { isPending?: boolean } = {}) {
  jest.spyOn(queriesModule, "useMarkAllNotificationsReadMutation").mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue(undefined), isPending: !!overrides.isPending,
  } as unknown as ReturnType<typeof queriesModule.useMarkAllNotificationsReadMutation>);
}

describe("NotificationCenterScreen", () => {
  beforeEach(() => { (isOffline as jest.Mock).mockReturnValue(false); });
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); mockGoBack.mockClear(); });

  it("shows the real authoritative unread count, never a hardcoded '3 unread'", () => {
    mockList([notification()]); mockUnreadCount(3); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("3 unread")).toBeTruthy();
  });

  it("uses singular grammar for exactly one unread", () => {
    mockList([notification()]); mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("1 unread")).toBeTruthy();
  });

  it("hides the unread badge at zero", () => {
    mockList([notification({ readStatus: "read" })]); mockUnreadCount(0); mockMarkRead(); mockMarkAllRead();
    const { queryByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(queryByText(/unread$/)).toBeNull();
  });

  it("shows Mark all read only when unread notifications exist", () => {
    mockList([notification()]); mockUnreadCount(2); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("Mark all read")).toBeTruthy();
  });

  it("hides Mark all read when there are no unread notifications", () => {
    mockList([notification({ readStatus: "read" })]); mockUnreadCount(0); mockMarkRead(); mockMarkAllRead();
    const { queryByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(queryByText("Mark all read")).toBeNull();
  });

  it("shows the empty state when there are no notifications at all", () => {
    mockList([]); mockUnreadCount(0); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("No notifications yet")).toBeTruthy();
    expect(getByText("Booking and support updates will appear here.")).toBeTruthy();
  });

  it("groups notifications under Today/Earlier headers using real timestamps", () => {
    mockList([
      notification({ id: asNotificationId("n-today"), createdAt: new Date().toISOString() as ServerTimestamp }),
      notification({ id: asNotificationId("n-earlier"), createdAt: "2020-01-01T00:00:00Z" as ServerTimestamp }),
    ]);
    mockUnreadCount(2); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("Today")).toBeTruthy();
    expect(getByText("Earlier")).toBeTruthy();
  });

  it("shows 'You're all caught up' only once the final page is reached with items loaded", () => {
    mockList([notification()], { hasNextPage: false });
    mockUnreadCount(0); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("You're all caught up")).toBeTruthy();
  });

  it("does not show 'You're all caught up' while more pages remain", () => {
    mockList([notification()], { hasNextPage: true });
    mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { queryByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(queryByText("You're all caught up")).toBeNull();
  });

  it("navigates to BookingDetails for a real service_bookings destination and marks it read", () => {
    const markRead = jest.fn();
    jest.spyOn(queriesModule, "useMarkNotificationReadMutation").mockReturnValue({
      mutate: markRead, isPending: false,
    } as unknown as ReturnType<typeof queriesModule.useMarkNotificationReadMutation>);
    mockList([notification({ destination: { kind: "booking", bookingId: "b-42" } })]);
    mockUnreadCount(1); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    fireEvent.press(getByText("AC Repair booking confirmed"));
    expect(markRead).toHaveBeenCalledWith("n-1");
    expect(mockNavigate).toHaveBeenCalledWith("BookingDetails", { bookingId: "b-42" });
  });

  it("navigates to SupportRequestDetails for a real customer_complaints destination", () => {
    mockList([notification({
      id: asNotificationId("n-2"), title: "Support request resolved",
      destination: { kind: "supportRequest", requestId: "req-9" },
    })]);
    mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    fireEvent.press(getByText("Support request resolved"));
    expect(mockNavigate).toHaveBeenCalledWith("SupportRequestDetails", { requestId: "req-9" });
  });

  it("renders a notification with no safe destination as non-interactive, never navigating", () => {
    mockList([notification({
      id: asNotificationId("n-3"), title: "New message from support", destination: null,
    })]);
    mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    fireEvent.press(getByText("New message from support"));
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("calls the real bulk mark-all-read mutation, not a loop over loaded rows", async () => {
    const mutateAsync = jest.fn().mockResolvedValue(undefined);
    jest.spyOn(queriesModule, "useMarkAllNotificationsReadMutation").mockReturnValue({
      mutateAsync, isPending: false,
    } as unknown as ReturnType<typeof queriesModule.useMarkAllNotificationsReadMutation>);
    mockList([notification(), notification({ id: asNotificationId("n-2") })]);
    mockUnreadCount(2); mockMarkRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    fireEvent.press(getByText("Mark all read"));
    expect(mutateAsync).toHaveBeenCalledTimes(1);
  });

  it("switches to the real backend-filtered Unread tab", () => {
    mockList([notification()]); mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    fireEvent.press(getByText("Unread"));
    expect(queriesModule.useNotificationsListQuery).toHaveBeenLastCalledWith("unread");
  });

  it("shows the empty-unread state distinct from the empty-all state", () => {
    mockList([]); mockUnreadCount(0); mockMarkRead(); mockMarkAllRead();
    const { getByText, rerender } = renderWithProviders(<NotificationCenterScreen />);
    fireEvent.press(getByText("Unread"));
    mockList([]);
    rerender(<AppProviders><NotificationCenterScreen /></AppProviders>);
    expect(getByText("You're all caught up")).toBeTruthy();
    expect(getByText("There are no unread notifications.")).toBeTruthy();
  });

  it("shows a compact offline banner and preserves cached notifications", () => {
    (isOffline as jest.Mock).mockReturnValue(true);
    mockList([notification()]); mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { getByText, queryByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("AC Repair booking confirmed")).toBeTruthy();
    expect(queryByText("Notifications can't be loaded")).toBeNull();
  });

  it("shows the uncached offline state when there is nothing cached yet", () => {
    (isOffline as jest.Mock).mockReturnValue(true);
    mockList([]); mockUnreadCount(undefined); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("Notifications can't be loaded")).toBeTruthy();
  });

  it("preserves the cached list on a refresh error instead of blanking the screen", () => {
    mockList([notification()], { isError: true }); mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("AC Repair booking confirmed")).toBeTruthy();
    expect(getByText(/couldn't refresh/i)).toBeTruthy();
  });

  it("shows the full-screen error state only when there is no cached data at all", () => {
    mockList([], { isError: true }); mockUnreadCount(undefined); mockMarkRead(); mockMarkAllRead();
    const { getByText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByText("Something went wrong")).toBeTruthy();
  });

  it("Go back navigates via the back chevron", () => {
    mockList([notification()]); mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { getByLabelText } = renderWithProviders(<NotificationCenterScreen />);
    fireEvent.press(getByLabelText("Go back"));
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("gives each row an accessible unread/read state label, never color alone", () => {
    mockList([notification({ readStatus: "unread" }), notification({ id: asNotificationId("n-2"), readStatus: "read", title: "Booking completed" })]);
    mockUnreadCount(1); mockMarkRead(); mockMarkAllRead();
    const { getByLabelText } = renderWithProviders(<NotificationCenterScreen />);
    expect(getByLabelText(/^Unread\./)).toBeTruthy();
    expect(getByLabelText(/^Read\./)).toBeTruthy();
  });
});
