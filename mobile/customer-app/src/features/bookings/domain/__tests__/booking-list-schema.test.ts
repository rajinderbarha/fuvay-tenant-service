import { parseBookingListPage } from "../booking-list-schema";

const validItem = {
  booking_id: "b-1",
  booking_number: "BK-20260713-000001",
  status: "pending_assignment",
  issue_summary: "Not cooling",
  city: "Pune",
  preferred_date: null,
  selected_provider: { provider_name: "Acme Repairs", rating: 4.2, public_badges: ["Verified"] },
  selected_price_option: "mid",
  selected_price_amount: 690,
};

describe("parseBookingListPage", () => {
  it("accepts a real page of bookings", () => {
    const result = parseBookingListPage({ items: [validItem], page: 1, page_size: 20 });
    expect(result?.items).toHaveLength(1);
    expect(result?.droppedCount).toBe(0);
  });

  it("drops individually-invalid items rather than failing the whole page", () => {
    const result = parseBookingListPage({ items: [validItem, { booking_id: "b-2" }], page: 1, page_size: 20 });
    expect(result?.items).toHaveLength(1);
    expect(result?.droppedCount).toBe(1);
  });

  it("infers mayHaveMore honestly from a full page, never from a fabricated total", () => {
    const full = parseBookingListPage({ items: new Array(20).fill(validItem), page: 1, page_size: 20 });
    expect(full?.mayHaveMore).toBe(true);
    const partial = parseBookingListPage({ items: [validItem], page: 1, page_size: 20 });
    expect(partial?.mayHaveMore).toBe(false);
  });

  it("accepts a null selected_provider (a real possible shape)", () => {
    const result = parseBookingListPage({ items: [{ ...validItem, selected_provider: null }], page: 1, page_size: 20 });
    expect(result?.items[0]?.selected_provider).toBeNull();
  });

  it("rejects a malformed envelope without throwing", () => {
    expect(parseBookingListPage(null)).toBeNull();
    expect(parseBookingListPage({})).toBeNull();
  });
});
