import React from "react";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { MyBookingsStrip } from "../MyBookingsStrip";
import { HomeActiveBooking } from "../../../domain/customerHome";
import { asServiceBookingId } from "../../../domain/ids";

function booking(n: number, overrides: Partial<HomeActiveBooking> = {}): HomeActiveBooking {
  return {
    bookingId: asServiceBookingId(`b-${n}`),
    bookingNumber: `BK-0000${n}`,
    status: "accepted",
    createdAt: null,
    assignmentStatus: "assigned",
    issueSummary: null,
    serviceName: `Service ${n}`,
    preferredDate: null,
    preferredTimeWindow: null,
    providerName: "Guramrit",
    scheduledDate: "2026-08-12",
    scheduledTimeWindow: "14:00-15:00",
    provider: { name: "Guramrit", verified: true, rating: 4.8, reviewCount: 12, badges: [] },
    technician: null,
    ...overrides,
  } as HomeActiveBooking;
}

const noop = { onPressBooking: () => {}, onViewAll: () => {}, categories: [] };

describe("MyBookingsStrip", () => {
  it("shows every booking it was given, not just the newest", () => {
    // The single card this replaces showed only the newest, with no sign that
    // two more were live.
    renderWithProviders(
      <MyBookingsStrip bookings={[booking(1), booking(2), booking(3)]} total={3} {...noop} />,
    );
    for (const n of [1, 2, 3]) expect(screen.getByText(`Service ${n}`)).toBeTruthy();
    expect(screen.getByLabelText("Your bookings, 3 shown of 3")).toBeTruthy();
  });

  it("offers View all only when there are more than it is showing", () => {
    // A link to a list containing exactly what is already on screen is noise.
    renderWithProviders(
      <MyBookingsStrip bookings={[booking(1), booking(2), booking(3)]} total={7} {...noop} />,
    );
    expect(screen.getByLabelText("View all 7 bookings")).toBeTruthy();
    expect(screen.getByText("3 of 7")).toBeTruthy();
  });

  it("hides View all when the strip already shows everything", () => {
    renderWithProviders(
      <MyBookingsStrip bookings={[booking(1), booking(2)]} total={2} {...noop} />,
    );
    expect(screen.queryByText("View all")).toBeNull();
    expect(screen.getByText("2 active")).toBeTruthy();
  });

  it("does not page or dot a single booking", () => {
    // A one-page carousel with one dot implies a second page.
    renderWithProviders(<MyBookingsStrip bookings={[booking(1)]} total={1} {...noop} />);
    expect(screen.queryByLabelText(/Your bookings,/)).toBeNull();
    expect(screen.getByText("Service 1")).toBeTruthy();
    expect(screen.getByText("My Booking")).toBeTruthy();
  });

  it("pluralises the heading off the real total", () => {
    renderWithProviders(<MyBookingsStrip bookings={[booking(1)]} total={4} {...noop} />);
    expect(screen.getByText("My Bookings")).toBeTruthy();
  });

  it("reports which booking was tapped", () => {
    const onPressBooking = jest.fn();
    const items = [booking(1), booking(2)];
    renderWithProviders(
      <MyBookingsStrip bookings={items} total={2} categories={[]} onViewAll={() => {}} onPressBooking={onPressBooking} />,
    );
    fireEvent.press(screen.getByText("Service 2"));
    expect(onPressBooking).toHaveBeenCalledWith(items[1]);
  });

  it("renders nothing at all with no live bookings", () => {
    // No heading either: a "My Bookings" title over nothing reads as a section
    // that failed to load. (Asserted on content rather than a null tree --
    // renderWithProviders wraps the subject in providers, so the tree is never
    // literally null.)
    const { queryByText } = renderWithProviders(
      <MyBookingsStrip bookings={[]} total={0} {...noop} />,
    );
    expect(queryByText(/My Booking/)).toBeNull();
    expect(queryByText("View all")).toBeNull();
  });

  it("uses the admin heading when the layout settings set one", () => {
    renderWithProviders(
      <MyBookingsStrip bookings={[booking(1)]} total={1} title="Your job today" {...noop} />,
    );
    expect(screen.getByText("Your job today")).toBeTruthy();
    expect(screen.queryByText("My Booking")).toBeNull();
  });

  it("shows only the provider's standing badge, not a row of pills", () => {
    // Live case: a provider held five separately-keyed badge definitions all named
    // "L5 Cfg Badge" plus two others. A card this size cannot carry that, and a
    // customer reads several pills as several endorsements when they may be one fact
    // counted several times. Independent badges live on the fuller provider surfaces.
    const errors: string[] = [];
    const spy = jest.spyOn(console, "error").mockImplementation((...args) => {
      errors.push(args.map(String).join(" "));
    });

    renderWithProviders(
      <MyBookingsStrip
        bookings={[booking(1, {
          provider: {
            name: "Guramrit", verified: true, rating: 5, reviewCount: 3,
            badges: [
              { name: "Bronze Partner", icon: "medal", color: "#b45309", level: 1 },
              { name: "L5 Cfg Badge" }, { name: "L5 Cfg Badge" },
              { name: "AC Specialist", icon: "snow" },
            ],
          },
        } as Partial<HomeActiveBooking>)]}
        total={1}
        {...noop}
      />,
    );

    spy.mockRestore();
    expect(errors.filter(e => /same key|unique "key"/i.test(e))).toEqual([]);
    expect(screen.getAllByText("Bronze Partner")).toHaveLength(1);
    expect(screen.queryByText("L5 Cfg Badge")).toBeNull();
    expect(screen.queryByText("AC Specialist")).toBeNull();
  });

  it("shows no badge at all for a provider who has earned no level", () => {
    // Silence, not a starter badge: one nobody earned devalues the ones that were.
    renderWithProviders(
      <MyBookingsStrip
        bookings={[booking(1, {
          provider: {
            name: "Guramrit", verified: true, rating: null, reviewCount: 0,
            badges: [{ name: "AC Specialist", icon: "snow" }],
          },
        } as Partial<HomeActiveBooking>)]}
        total={1}
        {...noop}
      />,
    );
    expect(screen.queryByText("AC Specialist")).toBeNull();
  });

  it("keeps the highest level when a payload somehow carries two", () => {
    // The ladder supersedes; it never accumulates.
    renderWithProviders(
      <MyBookingsStrip
        bookings={[booking(1, {
          provider: {
            name: "Guramrit", verified: true, rating: 5, reviewCount: 40,
            badges: [
              { name: "Bronze Partner", icon: "medal", level: 1 },
              { name: "Gold Partner", icon: "trophy", level: 3 },
            ],
          },
        } as Partial<HomeActiveBooking>)]}
        total={1}
        {...noop}
      />,
    );
    expect(screen.getByText("Gold Partner")).toBeTruthy();
    expect(screen.queryByText("Bronze Partner")).toBeNull();
  });
});
