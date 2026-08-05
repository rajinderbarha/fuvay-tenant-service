import React from "react";
import { renderHook, waitFor } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCustomerBookingDetailsQuery } from "../useCustomerBookingDetailsQuery";
import * as customerBookingsApi from "../customerBookingsApi";
import { DomainError } from "../../../domain/errors";

jest.mock("../customerBookingsApi");

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <NavigationContainer>{children}</NavigationContainer>
    </QueryClientProvider>
  );
}

function baseDto(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "b-1", booking_number: "SB-2026-01", draft_id: "d-1", customer_id: "c-1", tenant_id: "t-1",
    category_id: "cat-1", offering_id: "off-1", job_type_id: "jt-1",
    customer_name: null, customer_phone: null, city: "Ludhiana", zipcode: "141002",
    address_snapshot: null, preferred_date: null, preferred_time_window: null,
    price_snapshot: null, issue_summary: null, issue_details: null,
    status: "pending_assignment", assignment_status: "unassigned", failure_reason: null,
    created_at: "2026-08-01T09:41:00Z", updated_at: "2026-08-01T09:41:00Z",
    ...overrides,
  };
}

function notFoundError() {
  return new DomainError({ category: "UNKNOWN", diagnostic: "Booking not found", httpStatus: 404, telemetryMeta: { backendCode: "BOOKING_NOT_FOUND" } });
}

describe("useCustomerBookingDetailsQuery", () => {
  afterEach(() => jest.clearAllMocks());

  it("fetches strictly by booking ID and ignores any navigation-supplied display data", async () => {
    (customerBookingsApi.getMyBooking as jest.Mock).mockResolvedValue({ data: baseDto() });
    const { result } = renderHook(() => useCustomerBookingDetailsQuery("b-1"), { wrapper });
    await waitFor(() => expect(result.current.data?.kind).toBe("found"));
    expect(customerBookingsApi.getMyBooking).toHaveBeenCalledWith("b-1");
  });

  it("maps both a genuinely missing booking and a cross-customer one to the SAME not_found kind", async () => {
    (customerBookingsApi.getMyBooking as jest.Mock).mockRejectedValueOnce(notFoundError());
    const { result, unmount } = renderHook(() => useCustomerBookingDetailsQuery("missing"), { wrapper });
    await waitFor(() => expect(result.current.data?.kind).toBe("not_found"));
    unmount();

    (customerBookingsApi.getMyBooking as jest.Mock).mockRejectedValueOnce(notFoundError());
    const { result: result2 } = renderHook(() => useCustomerBookingDetailsQuery("someone-elses"), { wrapper });
    await waitFor(() => expect(result2.current.data?.kind).toBe("not_found"));
  });
});
