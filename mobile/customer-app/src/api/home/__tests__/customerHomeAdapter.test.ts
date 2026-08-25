import { parseCustomerHomeDto, adaptCustomerHome } from "../../adapters/customerHome";
import { ContractValidationError } from "../../../domain/errors";

function rawHome(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    response_version: 1,
    address: { address_id: "addr-1", city: "Ludhiana", zipcode: "141001", is_default: true },
    serviceability: { zipcode: "141001", checked: true },
    enabled_verticals: [{ vertical_id: "v-1", key: "home_services", label: "Home Services", icon: "home-outline" }],
    bookable_categories: [{ category_id: "cat-1", name: "AC & Cooling", code: "ac", icon_url: null }],
    active_booking: null,
    unread_notification_count: 2,
    capabilities: { bargain_available: true, photo_attach_available: true, chatbot_language_selectable: true },
    ...overrides,
  };
}

describe("quick issues", () => {
  it("adapts the shortcut list without inventing a price", () => {
    // The catalog does link each issue to a priced service, but the final
    // amount depends on answers the Assistant has not asked yet -- so the
    // payload carries no price and the domain object must not grow one.
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      quick_issues: [{
        issue_id: "i-1", label: "AC Not Cooling", slug: "ac-not-cooling",
        category_id: "cat-1", category_slug: "ac-cooling", category_name: "AC & Cooling",
      }],
    })));
    expect(home.quickIssues).toEqual([{
      issueId: "i-1", label: "AC Not Cooling",
      categoryId: "cat-1", categorySlug: "ac-cooling", categoryName: "AC & Cooling",
      // The backend sent no intent, so the problem belongs to neither intent
      // section -- the app must not guess one from the wording.
      intent: null,
    }]);
  });

  it("adapts eligible master services as a distinct home collection", () => {
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      bookable_master_services: [{
        master_service_id: "svc-1", name: "AC Repair", slug: "ac-repair",
        description: "Diagnosis and repair", icon_url: "https://cdn.example/ac.svg",
        service_group_id: "group-ac", service_group_name: "AC & HVAC",
        service_group_slug: "ac-hvac", category_id: "cat-1", category_slug: "home_services",
      }],
    })));
    expect(home.bookableMasterServices).toEqual([{
      masterServiceId: "svc-1", name: "AC Repair", slug: "ac-repair",
      description: "Diagnosis and repair", iconUrl: "https://cdn.example/ac.svg",
      serviceGroupId: "group-ac", serviceGroupName: "AC & HVAC",
      serviceGroupSlug: "ac-hvac", categoryId: "cat-1", categorySlug: "home_services",
    }]);
  });

  it("treats an older payload with no quick_issues as simply having none", () => {
    expect(adaptCustomerHome(parseCustomerHomeDto(rawHome())).quickIssues).toEqual([]);
  });
});

describe("customer home adapter", () => {
  it("parses a well-formed real-shaped payload", () => {
    const dto = parseCustomerHomeDto(rawHome());
    expect(dto.address?.city).toBe("Ludhiana");
  });

  it("rejects a malformed payload rather than guessing missing fields", () => {
    expect(() => parseCustomerHomeDto({ address: {} })).toThrow(ContractValidationError);
  });

  it("adapts a null address and null active_booking without throwing", () => {
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({ address: null, active_booking: null, serviceability: null })));
    expect(home.address).toBeNull();
    expect(home.activeBooking).toBeNull();
  });

  it("adapts categories with no price field at all (confirmed backend gap)", () => {
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome()));
    expect(home.bookableCategories[0]).not.toHaveProperty("price");
    expect(home.bookableCategories[0].name).toBe("AC & Cooling");
  });

  it("leaves the technician and service name null when the backend sends neither", () => {
    // `technician` / `service_name` became REAL backend fields when the
    // Home card was rebuilt as "My Booking" (customer_home service.py
    // resolves them from service_jobs.assigned_staff_id and the catalog),
    // so this no longer asserts they are impossible -- it asserts the
    // adapter never conjures them when they are absent.
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      active_booking: { booking_id: "b-1", booking_number: "SB-1", status: "scheduled", created_at: "2026-08-01T09:00:00Z" },
    })));
    expect(home.activeBooking).toEqual({
      bookingId: "b-1", bookingNumber: "SB-1", status: "scheduled", createdAt: "2026-08-01T09:00:00Z",
      assignmentStatus: null, issueSummary: null, preferredDate: null, preferredTimeWindow: null, providerName: null,
      serviceName: null, technician: null,
      // A committed slot and a provider block are absent here, so they must be
      // null rather than reconstructed from the requested date or the snapshot.
      scheduledDate: null, scheduledTimeWindow: null, provider: null,
    });
  });

  it("carries a real technician through verbatim, without defaulting an unearned rating", () => {
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      active_booking: {
        booking_id: "b-2", booking_number: "SB-2", status: "on_the_way", created_at: "2026-08-01T09:00:00Z",
        service_name: "AC Service",
        technician: { name: "Rakesh Kumar", role: "Service technician", photo_url: null, rating: null, review_count: 0 },
      },
    })));
    expect(home.activeBooking?.serviceName).toBe("AC Service");
    expect(home.activeBooking?.technician).toEqual({
      name: "Rakesh Kumar", role: "Service technician", photoUrl: null,
      // Null, not 0 and not a flattering default: a rating is earned or absent.
      rating: null, reviewCount: 0,
    });
  });

  it("carries the provider's earned facts and badges through as sent", () => {
    // Same two backend functions the booking-review card reads, so the app must
    // not re-derive or embellish any of it here.
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      active_booking: {
        booking_id: "b-5", booking_number: "SB-5", status: "on_the_way", created_at: "2026-08-01T09:00:00Z",
        scheduled_date: "2026-08-10", scheduled_time_window: "13:00-14:00",
        provider: {
          name: "Guramrit", verified: true, rating: 5, review_count: 1,
          badges: [
            // The STANDING badge carries a level; the independent ones do not, and
            // that is how the app tells them apart (see providerBadges.standingBadge).
            { name: "Bronze Partner", icon: "medal", color: "#b45309", level: 1 },
            { name: "AC Specialist", icon: "snow", color: "#0ea5e9" },
          ],
        },
      },
    })));
    expect(home.activeBooking?.scheduledDate).toBe("2026-08-10");
    expect(home.activeBooking?.scheduledTimeWindow).toBe("13:00-14:00");
    expect(home.activeBooking?.provider).toEqual({
      name: "Guramrit", verified: true, rating: 5, reviewCount: 1,
      badges: [
        { name: "Bronze Partner", icon: "medal", color: "#b45309", level: 1 },
        { name: "AC Specialist", icon: "snow", color: "#0ea5e9", level: null },
      ],
    });
  });

  it("reports an unverified, unrated provider as exactly that", () => {
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      active_booking: {
        booking_id: "b-6", booking_number: "SB-6", status: "pending_assignment", created_at: "2026-08-01T09:00:00Z",
        provider: { name: "New Provider", verified: false, rating: null, review_count: 0, badges: [] },
      },
    })));
    expect(home.activeBooking?.provider).toEqual({
      name: "New Provider", verified: false, rating: null, reviewCount: 0, badges: [],
    });
  });

  it("still has no field capable of expressing a live ETA", () => {
    // The reference design shows "Arriving in 15 MIN". Nothing in this
    // system computes an ETA, so the contract must offer nowhere to put
    // one -- that is what keeps a plausible-looking countdown from being
    // invented later.
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      active_booking: {
        booking_id: "b-3", booking_number: "SB-3", status: "on_the_way", created_at: "2026-08-01T09:00:00Z",
        eta_minutes: 15, arriving_in: "15 MIN",
      },
    })));
    const keys = Object.keys(home.activeBooking as object);
    expect(keys).not.toContain("etaMinutes");
    expect(keys).not.toContain("arrivingIn");
    expect(JSON.stringify(home.activeBooking)).not.toContain("15");
  });
});
