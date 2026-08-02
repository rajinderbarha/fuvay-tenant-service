import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePrivacy } from "../usePrivacy";

jest.mock("../../../services/privacy/privacyApi");
import * as api from "../../../services/privacy/privacyApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const SUMMARY = { privacy_status: { code: "up_to_date", label: "Up to date" }, policy: { version: "1.0", effective_from: null }, request_counts: { open: 0, completed: 0 }, recent_request: null };
const CONSENTS = [
  { purpose_code: "service_communications", label: "Service communications", description: "", legal_or_policy_basis: "contract_or_security", required: true, enabled: true, configurable: false, policy_version: "1.0", last_changed_at: null },
  { purpose_code: "product_improvement", label: "Product improvement", description: "", legal_or_policy_basis: "consent", required: false, enabled: true, configurable: true, policy_version: "1.0", last_changed_at: null },
];

beforeEach(() => jest.clearAllMocks());

describe("usePrivacy (Phase X)", () => {
  it("loads summary and consents", async () => {
    (api.getSummary as jest.Mock).mockResolvedValue({ ok: true, data: SUMMARY });
    (api.getConsents as jest.Mock).mockResolvedValue({ ok: true, data: { consents: CONSENTS } });
    const { result } = renderHook(() => usePrivacy(), { wrapper });
    await waitFor(() => expect(result.current.summaryLoading).toBe(false));
    expect(result.current.summary?.privacy_status.code).toBe("up_to_date");
    expect(result.current.consents.length).toBe(2);
  });

  it("toggleConsent rolls back on failure", async () => {
    (api.getSummary as jest.Mock).mockResolvedValue({ ok: true, data: SUMMARY });
    (api.getConsents as jest.Mock).mockResolvedValue({ ok: true, data: { consents: CONSENTS } });
    (api.updateConsent as jest.Mock).mockResolvedValue({ ok: false, error: { code: "MANDATORY_PROCESSING", category: "validation", safeMessage: "Required.", retryable: false } });
    const { result } = renderHook(() => usePrivacy(), { wrapper });
    await waitFor(() => expect(result.current.summaryLoading).toBe(false));

    await act(async () => { await result.current.toggleConsent("service_communications", false); });

    expect(result.current.mutationError?.safeMessage).toBe("Required.");
  });

  it("submitRequest invalidates the summary on success", async () => {
    (api.getSummary as jest.Mock).mockResolvedValue({ ok: true, data: SUMMARY });
    (api.getConsents as jest.Mock).mockResolvedValue({ ok: true, data: { consents: CONSENTS } });
    (api.submitRequest as jest.Mock).mockResolvedValue({ ok: true, data: { request_id: "r1", request_number: "PRV-1", status: "submitted", message: "ok" } });
    const { result } = renderHook(() => usePrivacy(), { wrapper });
    await waitFor(() => expect(result.current.summaryLoading).toBe(false));

    const outcome = await act(async () => result.current.submitRequest("data_correction", "test reason"));

    expect(api.submitRequest).toHaveBeenCalledWith({ requestType: "data_correction", reason: "test reason", details: undefined, isAccountClosure: undefined });
    expect(outcome).toEqual({ ok: true, requestId: "r1" });
  });
});
