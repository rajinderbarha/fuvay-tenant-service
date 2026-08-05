import { adaptBookingListItem, adaptBookingListPage } from "../bookingList";
import { ServiceBookingDto, BookingListResponseDto } from "../../contracts/customerBookings";

function bookingDto(overrides: Partial<ServiceBookingDto> = {}): ServiceBookingDto {
  return {
    id: "b-1", booking_number: "SB-2026-01", draft_id: "d-1", customer_id: "c-1", tenant_id: "t-1",
    category_id: "cat-1", offering_id: "off-1", job_type_id: "jt-1",
    customer_name: null, customer_phone: null, city: "Ludhiana", zipcode: "141002",
    address_snapshot: { line1: "Model Town" }, preferred_date: null, preferred_time_window: null,
    price_snapshot: { requires_inspection_estimate: true, visit_fee: 299 },
    issue_summary: "Not cooling", issue_details: null,
    answer_snapshot: {
      schema_version: 1,
      answers: [
        { question_id: "q-1", question_key: "brand", question_label: "Brand", question_type: "single_select", answer_code: "LG", answer_label: "LG", sequence: 1 },
      ],
    },
    status: "pending_assignment", assignment_status: "unassigned",
    failure_reason: null, created_at: "2026-08-01T09:41:00Z", updated_at: "2026-08-01T09:41:00Z",
    offering_name: "AC Repair", category_name: "AC & Cooling", job_type_label: "Repair",
    ...overrides,
  } as ServiceBookingDto;
}

describe("adaptBookingListItem", () => {
  it("adapts a real booking into a list item using the shared status/pricing adapters", () => {
    const item = adaptBookingListItem(bookingDto());
    expect(item.serviceName).toBe("AC Repair");
    expect(item.stage).toBe("provider_assignment");
    expect(item.pricing.inspection?.visitFee).toEqual({ minorUnits: 29900, currency: "INR" });
    expect(item.summaryFields).toEqual([{ key: "q-1", label: "Brand", value: "LG" }]);
  });

  it("adapts to a different category's fields without any AC-specific assumption", () => {
    const item = adaptBookingListItem(bookingDto({
      offering_name: "Geyser Repair", category_name: "Water Heating",
      answer_snapshot: { schema_version: 1, answers: [{ question_id: "q-9", question_key: "capacity", question_label: "Tank capacity", question_type: "single_select", answer_code: "15L", answer_label: "15 Litres", sequence: 1 }] },
    }));
    expect(item.serviceName).toBe("Geyser Repair");
    expect(item.summaryFields[0].value).toBe("15 Litres");
  });

  it("never renders a zero finalized price as valid", () => {
    const item = adaptBookingListItem(bookingDto({ price_snapshot: { standard_price: 0 } }));
    expect(item.pricing.state).toEqual({ kind: "unavailable" });
  });
});

describe("adaptBookingListPage", () => {
  it("adapts every item and preserves the authoritative server total", () => {
    const dto: BookingListResponseDto = {
      items: [bookingDto(), bookingDto({ id: "b-2" })], total: 7,
      counts: { active: 7, completed: 0, all: 7 }, limit: 20, offset: 0,
    };
    const page = adaptBookingListPage(dto);
    expect(page.items).toHaveLength(2);
    expect(page.total).toBe(7);
    expect(page.counts).toEqual({ active: 7, completed: 0, all: 7 });
  });
});
