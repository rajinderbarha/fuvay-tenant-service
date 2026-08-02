import React from "react";
import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useTechnicianJobs } from "../useTechnicianJobs";

jest.mock("../../../services/jobs/jobsApi");
jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ accessContext: { tenantId: "t1", technicianId: "tech1" } }),
}));

import * as jobsApi from "../../../services/jobs/jobsApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function job(id: string) {
  return {
    job_id: id, job_reference: `HS-${id}`, offering_id: null, service_label: "AC Repair",
    job_type_id: null, job_type_label: null, workflow_status: "assigned", scheduled_date: null,
    scheduled_time_window: null, safe_locality: null, customer_alias: "Customer",
    next_required_action: { key: null, label: null, allowed: false }, allowed_actions: [],
    blocker: null, payment_confirmation_state: null, entity_version: null, workflow_version: null, updated_at: null,
  };
}

beforeEach(() => jest.clearAllMocks());

describe("useTechnicianJobs — pagination and dedup (spec section 12)", () => {
  it("fetches the first page and exposes counts_by_view", async () => {
    (jobsApi.getMobileJobs as jest.Mock).mockResolvedValue({
      ok: true, meta: {},
      data: { results: [job("1")], next_cursor: null, has_more: false, counts_by_view: { today: 1, active: 0, upcoming: 0, completed: 0, archive: 0 }, applied_filters: {}, server_timestamp: "" },
    });
    const { result } = renderHook(() => useTechnicianJobs({ view: "today", search: "" }), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(result.current.countsByView?.today).toBe(1);
    expect(result.current.hasNextPage).toBe(false);
  });

  it("deduplicates by job_id across pages, never showing a duplicate row", async () => {
    (jobsApi.getMobileJobs as jest.Mock)
      .mockResolvedValueOnce({
        ok: true, meta: {},
        data: { results: [job("1"), job("2")], next_cursor: "cursor-1", has_more: true, counts_by_view: { today: 3, active: 0, upcoming: 0, completed: 0, archive: 0 }, applied_filters: {}, server_timestamp: "" },
      })
      .mockResolvedValueOnce({
        ok: true, meta: {},
        // Job "2" appears again (e.g. a boundary re-fetch) -- must not duplicate.
        data: { results: [job("2"), job("3")], next_cursor: null, has_more: false, counts_by_view: { today: 3, active: 0, upcoming: 0, completed: 0, archive: 0 }, applied_filters: {}, server_timestamp: "" },
      });
    const { result } = renderHook(() => useTechnicianJobs({ view: "today", search: "" }), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(2));
    await result.current.fetchNextPage();
    await waitFor(() => expect(result.current.items).toHaveLength(3));
    const ids = result.current.items.map(i => i.job_id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("surfaces a safe error and stops paging on failure", async () => {
    (jobsApi.getMobileJobs as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "SERVER_UNAVAILABLE", category: "server", safeMessage: "Something went wrong on our end.", retryable: true },
    });
    const { result } = renderHook(() => useTechnicianJobs({ view: "today", search: "" }), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.safeMessage).toBe("Something went wrong on our end.");
  });
});
