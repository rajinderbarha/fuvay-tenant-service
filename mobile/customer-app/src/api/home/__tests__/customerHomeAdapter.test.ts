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

  it("never carries a technician/ETA/rating field on active_booking (structurally impossible)", () => {
    const home = adaptCustomerHome(parseCustomerHomeDto(rawHome({
      active_booking: { booking_id: "b-1", booking_number: "SB-1", status: "scheduled", created_at: "2026-08-01T09:00:00Z" },
    })));
    expect(home.activeBooking).toEqual({
      bookingId: "b-1", bookingNumber: "SB-1", status: "scheduled", createdAt: "2026-08-01T09:00:00Z",
    });
    expect(Object.keys(home.activeBooking as object)).toEqual(["bookingId", "bookingNumber", "status", "createdAt"]);
  });
});
