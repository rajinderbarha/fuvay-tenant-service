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
    campaigns: [
      { campaign_id: "c-2", title: "Second", priority: 20 },
      { campaign_id: "c-1", title: "First", priority: 10 },
    ],
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

  it("sorts campaigns by backend priority ascending", () => {
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome()));
    expect(home.campaigns.map(c => c.campaignId)).toEqual(["c-1", "c-2"]);
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

  it("never carries a technician identity, live ETA, or rating on active_booking (structurally impossible)", () => {
    // issue_summary/provider_name/preferred_date/preferred_time_window/
    // assignment_status were added to the real backend payload (customer_home
    // service.py) so the Home card could show something more than a bare
    // status slug -- this is still a closed, known field set, just a wider
    // one than before. What must never appear here is anything the backend
    // doesn't send: a technician's name/photo, a live ETA countdown, or a
    // rating -- none of those are in this DTO's schema at all.
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      active_booking: { booking_id: "b-1", booking_number: "SB-1", status: "scheduled", created_at: "2026-08-01T09:00:00Z" },
    })));
    expect(home.activeBooking).toEqual({
      bookingId: "b-1", bookingNumber: "SB-1", status: "scheduled", createdAt: "2026-08-01T09:00:00Z",
      assignmentStatus: null, issueSummary: null, preferredDate: null, preferredTimeWindow: null, providerName: null,
    });
    expect(Object.keys(home.activeBooking as object).sort()).toEqual(
      ["assignmentStatus", "bookingId", "bookingNumber", "createdAt", "issueSummary", "preferredDate", "preferredTimeWindow", "providerName", "status"],
    );
  });
});
