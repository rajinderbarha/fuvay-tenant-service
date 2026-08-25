import { adaptCustomerBookingDetails } from "../customerBookingDetails";
import { ServiceBookingDto } from "../../contracts/customerBookings";

function baseDto(overrides: Partial<ServiceBookingDto> = {}): ServiceBookingDto {
  return {
    id: "b-1", booking_number: "SB-2026-01", draft_id: "d-1", customer_id: "c-1", tenant_id: "t-1",
    category_id: "cat-1", offering_id: "off-1", job_type_id: "jt-1",
    customer_name: null, customer_phone: null, city: "Ludhiana", zipcode: "141002",
    address_snapshot: { line1: "Model Town" }, preferred_date: null, preferred_time_window: null,
    price_snapshot: { requires_inspection_estimate: true, visit_fee: 299 },
    provider_snapshot: { provider_name: "CoolFix", tenant_id: "t-1" },
    issue_summary: "Not cooling",
    // NOT the answers source (see adapter comment) -- populated here only
    // to prove it is never read for the answers list.
    issue_details: { legacy: "unrelated inspection-report shape" },
    answer_snapshot: {
      schema_version: 1,
      answers: [
        { question_id: "q-2", question_key: "ac_type", question_label: "AC type", question_type: "single_select", answer_code: "split_ac", answer_label: "Split AC", sequence: 2 },
        { question_id: "q-1", question_key: "brand", question_label: "What is your AC brand?", question_type: "single_select", answer_code: "LG", answer_label: "LG", sequence: 1 },
      ],
    },
    status: "pending_assignment", assignment_status: "unassigned",
    failure_reason: null, created_at: "2026-08-01T09:41:00Z", updated_at: "2026-08-01T09:41:00Z",
    offering_name: "AC Repair", category_name: "AC & Cooling", job_type_label: "Repair",
    ...overrides,
  } as ServiceBookingDto;
}

describe("adaptCustomerBookingDetails", () => {
  it("adapts the real versioned answer_snapshot into label/value pairs, sorted by sequence", () => {
    const details = adaptCustomerBookingDetails(baseDto());
    expect(details.service.answers.map(a => a.label)).toEqual(["What is your AC brand?", "AC type"]);
    expect(details.service.answers[0].value).toBe("LG");
    expect(details.service.answers[1].value).toBe("Split AC");
  });

  it("never reads issue_details for answers -- that column is a different consumer's inspection-report shape", () => {
    const details = adaptCustomerBookingDetails(baseDto());
    const serialized = JSON.stringify(details.service.answers);
    expect(serialized).not.toContain("unrelated inspection-report shape");
  });

  it("produces no answers when the booking has no answer_snapshot", () => {
    const details = adaptCustomerBookingDetails(baseDto({ answer_snapshot: null }));
    expect(details.service.answers).toEqual([]);
  });

  it("never surfaces provider_snapshot contents anywhere on the details model", () => {
    const details = adaptCustomerBookingDetails(baseDto());
    expect(JSON.stringify(details)).not.toContain("CoolFix");
  });

  it("derives exactly one real activity event from created_at", () => {
    const details = adaptCustomerBookingDetails(baseDto());
    expect(details.activity).toHaveLength(1);
  });

  it("resolves the pending-assignment stage and truthful copy for a freshly confirmed booking", () => {
    const details = adaptCustomerBookingDetails(baseDto());
    expect(details.stage).toBe("provider_assignment");
    expect(details.activityText).toBe("Assigning an eligible professional");
  });

  it("renders the real in-progress booking stage instead of regressing the timeline", () => {
    const details = adaptCustomerBookingDetails(baseDto({ status: "in_progress" }));
    expect(details.stage).toBe("scheduled");
    expect(details.statusLabel).toBe("Service in progress");
  });

  it("never renders a zero/missing finalized price as valid or free", () => {
    const details = adaptCustomerBookingDetails(baseDto({ price_snapshot: { standard_price: 0 } }));
    expect(details.pricing.state).toEqual({ kind: "unavailable" });
  });

  it("adapts finalized customer photos and note without mixing provider evidence", () => {
    const details = adaptCustomerBookingDetails(baseDto({
      customer_photo_urls: ["https://res.cloudinary.com/demo/image/upload/photo.jpg"],
      customer_note: "Water is dripping near the wall.",
    }));
    expect(details.attachments).toEqual([{ id: "b-1:customer-photo:0", url: "https://res.cloudinary.com/demo/image/upload/photo.jpg" }]);
    expect(details.note).toBe("Water is dripping near the wall.");
  });
});
