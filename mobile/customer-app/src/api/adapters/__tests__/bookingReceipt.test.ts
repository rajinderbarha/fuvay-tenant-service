import { adaptBookingReceipt } from "../bookingReceipt";
import { ServiceBookingDto } from "../../contracts/customerBookings";

function baseDto(overrides: Partial<ServiceBookingDto> = {}): ServiceBookingDto {
  return {
    id: "b-1", booking_number: "SB-2026-01", draft_id: "d-1", customer_id: "c-1", tenant_id: "t-1",
    category_id: "cat-1", offering_id: "off-1", job_type_id: "jt-1",
    customer_name: null, customer_phone: null, city: "Ludhiana", zipcode: "141002",
    address_snapshot: { line1: "Model Town" }, preferred_date: null, preferred_time_window: null,
    price_snapshot: null, provider_snapshot: { provider_name: "CoolFix", tenant_id: "t-1" },
    issue_summary: "Not cooling", issue_details: null, status: "pending_assignment", assignment_status: "unassigned",
    failure_reason: null, created_at: null, updated_at: null,
    offering_name: "AC Repair", category_name: "AC & Cooling", job_type_label: "Repair",
    ...overrides,
  } as ServiceBookingDto;
}

describe("adaptBookingReceipt", () => {
  it("adapts a real finalized booking into a truthful receipt", () => {
    const receipt = adaptBookingReceipt(baseDto());
    expect(receipt.bookingId).toBe("b-1");
    expect(receipt.bookingNumber).toBe("SB-2026-01");
    expect(receipt.currentStage).toBe("provider_assignment");
    expect(receipt.service.name).toBe("AC Repair");
    expect(receipt.service.jobType).toBe("Repair");
    expect(receipt.address.formatted).toContain("141002");
  });

  it("never surfaces provider_snapshot contents anywhere on the receipt (staff-dependent safety boundary)", () => {
    const receipt = adaptBookingReceipt(baseDto());
    const serialized = JSON.stringify(receipt);
    expect(serialized).not.toContain("CoolFix");
  });

  it("classifies a real inspection visit fee from the finalized price_snapshot", () => {
    const receipt = adaptBookingReceipt(baseDto({
      price_snapshot: { requires_inspection_estimate: true, visit_fee: 299 },
    }));
    expect(receipt.pricing.state).toEqual({ kind: "inspection_based" });
    expect(receipt.pricing.inspection?.visitFee).toEqual({ minorUnits: 29900, currency: "INR" });
  });

  it("never renders a zero/missing price as valid or free", () => {
    const receipt = adaptBookingReceipt(baseDto({ price_snapshot: { standard_price: 0 } }));
    expect(receipt.pricing.state).toEqual({ kind: "unavailable" });
  });

  it("resolves notification capability as unavailable (no push transport exists)", () => {
    const receipt = adaptBookingReceipt(baseDto());
    expect(receipt.notificationCapability).toEqual({ kind: "unavailable" });
  });
});
