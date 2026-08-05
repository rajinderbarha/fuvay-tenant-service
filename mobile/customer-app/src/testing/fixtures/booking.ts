import { ServiceBookingDto } from "../../api/contracts/bookings";

export function makeServiceBookingDto(overrides: Partial<ServiceBookingDto> = {}): ServiceBookingDto {
  return {
    id: "booking-22222222-2222-2222-2222-222222222222",
    booking_number: "SB-2026-000045",
    draft_id: "draft-99999999-9999-9999-9999-999999999999",
    customer_id: "customer-33333333-3333-3333-3333-333333333333",
    tenant_id: "tenant-44444444-4444-4444-4444-444444444444",
    category_id: "category-55555555-5555-5555-5555-555555555555",
    offering_id: "offering-66666666-6666-6666-6666-666666666666",
    job_type_id: "jobtype-77777777-7777-7777-7777-777777777777",
    customer_name: "Asha Rao",
    city: "Bengaluru",
    zipcode: "560001",
    preferred_date: "2026-08-05",
    preferred_time_window: "10:00-12:00",
    price_snapshot: { agreed_price: "899.00" },
    provider_snapshot: { provider_name: "QuickFix Services", rating: 4.6, public_badges: ["verified"] },
    status: "scheduled",
    assignment_status: "accepted",
    failure_reason: null,
    created_at: "2026-08-01T09:00:00Z",
    updated_at: "2026-08-01T09:30:00Z",
    ...overrides,
  };
}
