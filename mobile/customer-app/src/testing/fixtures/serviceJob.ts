import { ServiceJobDto } from "../../api/contracts/serviceJobs";

/** Realistic fixture for unit/contract/adapter tests only -- never used as
 * a production fallback response (see Phase D section 21). */
export function makeServiceJobDto(overrides: Partial<ServiceJobDto> = {}): ServiceJobDto {
  return {
    id: "job-11111111-1111-1111-1111-111111111111",
    job_number: "SJ-2026-000123",
    booking_id: "booking-22222222-2222-2222-2222-222222222222",
    customer_id: "customer-33333333-3333-3333-3333-333333333333",
    tenant_id: "tenant-44444444-4444-4444-4444-444444444444",
    category_id: "category-55555555-5555-5555-5555-555555555555",
    offering_id: "offering-66666666-6666-6666-6666-666666666666",
    job_type_id: "jobtype-77777777-7777-7777-7777-777777777777",
    assigned_staff_id: "staff-88888888-8888-8888-8888-888888888888",
    scheduled_date: "2026-08-05",
    scheduled_time_window: "10:00-12:00",
    city: "Bengaluru",
    zipcode: "560001",
    status: "on_the_way",
    assignment_status: "accepted",
    failure_reason: null,
    created_at: "2026-08-01T09:30:00Z",
    updated_at: "2026-08-01T10:00:00Z",
    ...overrides,
  };
}
