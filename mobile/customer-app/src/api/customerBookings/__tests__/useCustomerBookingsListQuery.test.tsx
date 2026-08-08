import React from "react";
import { renderHook, waitFor, act } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCustomerBookingsListQuery } from "../useCustomerBookingsListQuery";
import * as customerBookingsApi from "../customerBookingsApi";

jest.mock("../customerBookingsApi");

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <NavigationContainer>{children}</NavigationContainer>
    </QueryClientProvider>
  );
}

function bookingDto(id: string) {
  return {
    id, booking_number: `SB-${id}`, draft_id: "d-1", customer_id: "c-1", tenant_id: "t-1",
    category_id: "cat-1", offering_id: "off-1", job_type_id: "jt-1",
    customer_name: null, customer_phone: null, city: "Ludhiana", zipcode: "141002",
    address_snapshot: null, preferred_date: null, preferred_time_window: null,
    price_snapshot: null, issue_summary: null, issue_details: null, answer_snapshot: null,
    status: "pending_assignment", assignment_status: "unassigned", failure_reason: null,
    created_at: "2026-08-01T09:41:00Z", updated_at: "2026-08-01T09:41:00Z",
  };
}

function page(items: ReturnType<typeof bookingDto>[], total: number, offset: number, counts = { active: total, completed: 0, all: total }) {
  return { data: { items, total, counts, limit: 20, offset } };
}

describe("useCustomerBookingsListQuery", () => {
  afterEach(() => jest.resetAllMocks());

  it("requests the selected bucket and exposes the backend's authoritative counts", async () => {
    (customerBookingsApi.listMyBookings as jest.Mock).mockResolvedValue(page([bookingDto("b-1")], 1, 0, { active: 1, completed: 4, all: 5 }));
    const { result } = renderHook(() => useCustomerBookingsListQuery("active"), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    // `undefined` search: an empty box must send no `q` at all, not an
    // empty term the backend would have to special-case.
    expect(customerBookingsApi.listMyBookings).toHaveBeenCalledWith("active", 20, 0, undefined, undefined);
    expect(result.current.counts).toEqual({ active: 1, completed: 4, all: 5 });
  });

  it("passes a search term to the backend rather than filtering the loaded pages", async () => {
    // Client-side filtering would only ever search pages already fetched,
    // silently missing older bookings -- so the term must reach the API.
    (customerBookingsApi.listMyBookings as jest.Mock).mockResolvedValue(page([bookingDto("b-1")], 1, 0));
    const { result } = renderHook(() => useCustomerBookingsListQuery("all", "  cooling  "), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    // Trimmed, so " cooling " and "cooling" hit one cache entry.
    expect(customerBookingsApi.listMyBookings).toHaveBeenCalledWith("all", 20, 0, "cooling", undefined);
  });

  it("treats a whitespace-only search as no search at all", async () => {
    (customerBookingsApi.listMyBookings as jest.Mock).mockResolvedValue(page([bookingDto("b-1")], 1, 0));
    const { result } = renderHook(() => useCustomerBookingsListQuery("all", "   "), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(customerBookingsApi.listMyBookings).toHaveBeenCalledWith("all", 20, 0, undefined, undefined);
  });

  it("sends the status filter alongside the bucket rather than instead of it", async () => {
    // `status` narrows WITHIN the bucket server-side; dropping the bucket
    // would widen the list the moment a filter was applied.
    (customerBookingsApi.listMyBookings as jest.Mock).mockResolvedValue(page([bookingDto("b-1")], 1, 0));
    const { result } = renderHook(() => useCustomerBookingsListQuery("all", "", "completed"), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(customerBookingsApi.listMyBookings).toHaveBeenCalledWith("all", 20, 0, undefined, "completed");
  });

  it("sends no status at all when the filter is cleared", async () => {
    (customerBookingsApi.listMyBookings as jest.Mock).mockResolvedValue(page([bookingDto("b-1")], 1, 0));
    const { result } = renderHook(() => useCustomerBookingsListQuery("all", "", null), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(customerBookingsApi.listMyBookings).toHaveBeenCalledWith("all", 20, 0, undefined, undefined);
  });

  it("loads a further page via fetchNextPage without duplicating rows", async () => {
    (customerBookingsApi.listMyBookings as jest.Mock).mockImplementation((_bucket: string, _limit: number, offset: number) => {
      if (offset === 0) return Promise.resolve(page([bookingDto("b-1")], 2, 0));
      return Promise.resolve(page([bookingDto("b-2")], 2, offset));
    });
    const { result } = renderHook(() => useCustomerBookingsListQuery("active"), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(result.current.hasNextPage).toBe(true);

    await act(async () => { await result.current.fetchNextPage(); });

    await waitFor(() => expect(result.current.items).toHaveLength(2));
    expect(new Set(result.current.items.map(i => i.bookingId)).size).toBe(2);
    expect(result.current.hasNextPage).toBe(false);
  });

  it("keeps the previous results on screen while a new search term loads", async () => {
    // The blink this fixes: a new term is a new query key, a new key has no
    // cached data, so the query returned to `isPending` on every keystroke and
    // the screen replaced the whole list -- search box included -- with a
    // loading state, then put it back.
    (customerBookingsApi.listMyBookings as jest.Mock).mockResolvedValue(page([bookingDto("b-1")], 1, 0));
    const { result, rerender } = renderHook(
      ({ term }: { term: string }) => useCustomerBookingsListQuery("all", term),
      { wrapper, initialProps: { term: "co" } },
    );
    await waitFor(() => expect(result.current.items).toHaveLength(1));

    let resolveNext: (value: unknown) => void = () => {};
    (customerBookingsApi.listMyBookings as jest.Mock).mockReturnValue(
      new Promise(resolve => { resolveNext = resolve; }),
    );
    rerender({ term: "cool" });

    // Mid-flight: still one row, never a pending/empty screen.
    expect(result.current.isPending).toBe(false);
    expect(result.current.items).toHaveLength(1);
    expect(result.current.isStale).toBe(true);

    await act(async () => { resolveNext(page([bookingDto("b-2")], 1, 0)); });
    await waitFor(() => expect(result.current.isStale).toBe(false));
    expect(result.current.items.map(i => i.bookingId)).toEqual(["b-2"]);
  });

  it("does not fire a second request for a term the query key already fetched", async () => {
    // The focus effect listed [bucket, q], so its callback identity changed with
    // every debounced term and useFocusEffect re-ran it -- one wasted request
    // per search on top of the one the key change already made.
    (customerBookingsApi.listMyBookings as jest.Mock).mockResolvedValue(page([bookingDto("b-1")], 1, 0));
    const { result, rerender } = renderHook(
      ({ term }: { term: string }) => useCustomerBookingsListQuery("all", term),
      { wrapper, initialProps: { term: "co" } },
    );
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    const afterFirstTerm = (customerBookingsApi.listMyBookings as jest.Mock).mock.calls.length;

    rerender({ term: "cool" });
    await waitFor(() =>
      expect((customerBookingsApi.listMyBookings as jest.Mock).mock.calls
        .some(c => c[3] === "cool")).toBe(true));

    // Exactly one more call: the new key's fetch.
    expect((customerBookingsApi.listMyBookings as jest.Mock).mock.calls.length)
      .toBe(afterFirstTerm + 1);
  });

  it("stops pagination on an empty page even if total disagrees (defensive termination)", async () => {
    (customerBookingsApi.listMyBookings as jest.Mock).mockResolvedValue(page([], 999, 0));
    const { result } = renderHook(() => useCustomerBookingsListQuery("all"), { wrapper });
    await waitFor(() => expect(result.current.items).toEqual([]));
    expect(result.current.hasNextPage).toBe(false);
  });
});

