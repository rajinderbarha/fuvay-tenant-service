import { parseBookingDetail } from "../booking-detail-schema";

const validDetail = {
  booking_id: "b-1",
  booking_number: "BK-20260713-000001",
  status: "assigned",
  assignment_status: "assigned",
  assignment_message: "Technician assigned.",
  preferred_date: null,
  preferred_time_window: "Morning",
  city: "Pune",
  address: {
    address_line_1: "12 MG Road",
    address_line_2: null,
    landmark: null,
    city: "Pune",
    state: "MH",
    zipcode: "411001",
    country: "IN",
    name: "Asha",
    phone: "9999999999",
  },
  issue_summary: "Not cooling",
  selected_provider: { provider_name: "Acme Repairs", rating: 4.2, public_badges: ["Verified"] },
  selected_price_option: "mid",
  selected_price_amount: 690,
  payment_mode: "customer_pays_provider_directly",
};

describe("parseBookingDetail", () => {
  it("parses a real, found booking without a job", () => {
    const result = parseBookingDetail(validDetail);
    expect(result.kind).toBe("found");
    if (result.kind === "found") expect(result.booking.job_status).toBeUndefined();
  });

  it("parses a real, found booking with a job", () => {
    const result = parseBookingDetail({ ...validDetail, job_status: "assigned", scheduled_date: "2026-07-15", scheduled_time_window: "Morning" });
    expect(result.kind).toBe("found");
    if (result.kind === "found") expect(result.booking.job_status).toBe("assigned");
  });

  it("parses the real {success:false, error:{code,message}} not-found shape (distinct from CUSTOMER-L5-11's other endpoint's {error:string} shape)", () => {
    const result = parseBookingDetail({ success: false, error: { code: "BOOKING_NOT_FOUND", message: "Booking not found." } });
    expect(result).toEqual({ kind: "error", code: "BOOKING_NOT_FOUND" });
  });

  it("fails closed on a malformed payload without throwing", () => {
    expect(parseBookingDetail(null)).toEqual({ kind: "invalid" });
    expect(parseBookingDetail({})).toEqual({ kind: "invalid" });
  });
});
