import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEmploymentDetails } from "../useEmploymentDetails";

jest.mock("../../../services/employment/employmentApi");
import * as api from "../../../services/employment/employmentApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const BASE = {
  business: { tenant_id: "t1", name: "Acme", logo_url: null, vertical_code: "home_services", vertical_label: "Home Services" },
  employment: { staff_id: "s1", staff_reference: "TECH-0042", staff_type: "technician", designation: "Technician", status: "active", status_known: true, joined_at: "2025-03-12T00:00:00Z", reports_to: null },
  status_known: true,
  assignments: { service_groups: [], job_types: [], verified_skills: [] },
  scope: { service_area_summary: null, working_schedule_summary: null, effective_capability_count: 7 },
  permissions: { capability_count: 7, groups: [] },
  allowed_actions: { request_correction: true },
};

beforeEach(() => jest.clearAllMocks());

describe("useEmploymentDetails (Phase S)", () => {
  it("loads the employment projection and fetches correction requests when allowed", async () => {
    (api.getEmploymentDetails as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (api.listCorrectionRequests as jest.Mock).mockResolvedValue({ ok: true, data: { requests: [] } });
    const { result } = renderHook(() => useEmploymentDetails(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getEmploymentDetails).toHaveBeenCalled();
    await waitFor(() => expect(api.listCorrectionRequests).toHaveBeenCalled());
  });

  it("submitCorrection posts and invalidates the corrections list rather than mutating locally", async () => {
    (api.getEmploymentDetails as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (api.listCorrectionRequests as jest.Mock).mockResolvedValue({ ok: true, data: { requests: [] } });
    (api.submitCorrectionRequest as jest.Mock).mockResolvedValue({ ok: true, data: { id: "c1", status: "pending_review" } });
    const { result } = renderHook(() => useEmploymentDetails(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.submitCorrection("designation", "Senior Technician", "Promoted"); });

    expect(api.submitCorrectionRequest).toHaveBeenCalledWith({ fieldKey: "designation", requestedValue: "Senior Technician", reason: "Promoted" });
    expect(api.listCorrectionRequests).toHaveBeenCalledTimes(2);
  });

  it("surfaces a duplicate-pending error without throwing", async () => {
    (api.getEmploymentDetails as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (api.listCorrectionRequests as jest.Mock).mockResolvedValue({ ok: true, data: { requests: [] } });
    (api.submitCorrectionRequest as jest.Mock).mockResolvedValue({ ok: false, error: { code: "CONFLICT", category: "validation", safeMessage: "You already have a pending correction request for this field.", retryable: false } });
    const { result } = renderHook(() => useEmploymentDetails(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.submitCorrection("designation", "Lead", "test"); });

    expect(result.current.submitError?.safeMessage).toBe("You already have a pending correction request for this field.");
  });
});
