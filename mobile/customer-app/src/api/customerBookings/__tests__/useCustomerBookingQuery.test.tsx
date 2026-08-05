import React from "react";
import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCustomerBookingQuery } from "../useCustomerBookingQuery";
import * as customerBookingsApi from "../customerBookingsApi";
import { DomainError } from "../../../domain/errors";

jest.mock("../customerBookingsApi");

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function baseDto(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "b-1", booking_number: "SB-2026-01", draft_id: "d-1", customer_id: "c-1", tenant_id: "t-1",
    category_id: "cat-1", offering_id: "off-1", job_type_id: "jt-1",
    customer_name: null, customer_phone: null, city: "Ludhiana", zipcode: "141002",
    address_snapshot: null, preferred_date: null, preferred_time_window: null,
    price_snapshot: null, issue_summary: null, issue_details: null,
    status: "pending_assignment", assignment_status: "unassigned", failure_reason: null,
    created_at: null, updated_at: null,
    ...overrides,
  };
}

describe("useCustomerBookingQuery", () => {
  afterEach(() => jest.clearAllMocks());

  it("returns a found receipt for a real booking DTO", async () => {
    (customerBookingsApi.getMyBooking as jest.Mock).mockResolvedValue({ data: baseDto() });
    const { result } = renderHook(() => useCustomerBookingQuery("b-1"), { wrapper });
    await waitFor(() => expect(result.current.data?.kind).toBe("found"));
    expect(result.current.data?.kind === "found" && result.current.data.receipt.bookingNumber).toBe("SB-2026-01");
  });

  it("maps a real 404 to kind: not_found, never rendering a fake receipt", async () => {
    (customerBookingsApi.getMyBooking as jest.Mock).mockRejectedValue(
      new DomainError({ category: "UNKNOWN", diagnostic: "Booking not found", httpStatus: 404, telemetryMeta: { backendCode: "BOOKING_NOT_FOUND" } }),
    );
    const { result } = renderHook(() => useCustomerBookingQuery("missing"), { wrapper });
    await waitFor(() => expect(result.current.data?.kind).toBe("not_found"));
  });

  it("maps a cross-customer 404 to the SAME kind as a genuinely missing booking (indistinguishable by design)", async () => {
    (customerBookingsApi.getMyBooking as jest.Mock).mockRejectedValue(
      new DomainError({ category: "UNKNOWN", diagnostic: "Booking not found", httpStatus: 404, telemetryMeta: { backendCode: "BOOKING_NOT_FOUND" } }),
    );
    const { result } = renderHook(() => useCustomerBookingQuery("someone-elses"), { wrapper });
    await waitFor(() => expect(result.current.data?.kind).toBe("not_found"));
  });

  it("re-throws a non-404 error rather than silently treating it as not_found", async () => {
    (customerBookingsApi.getMyBooking as jest.Mock).mockRejectedValue(
      new DomainError({ category: "BACKEND_UNAVAILABLE", diagnostic: "server error", httpStatus: 500 }),
    );
    const { result } = renderHook(() => useCustomerBookingQuery("b-1"), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
