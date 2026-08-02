import React from "react";
import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSecurity } from "../useSecurity";

jest.mock("../../../services/auth/securityApi");
import * as api from "../../../services/auth/securityApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useSecurity (Phase V)", () => {
  it("loads the real backend security summary", async () => {
    (api.getSecuritySummary as jest.Mock).mockResolvedValue({
      ok: true,
      data: { security_status: { level: "protected", label: "Your account is protected", reasons: [] } },
    });
    const { result } = renderHook(() => useSecurity(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getSecuritySummary).toHaveBeenCalled();
    expect(result.current.data?.security_status.level).toBe("protected");
  });

  it("surfaces an error without throwing", async () => {
    (api.getSecuritySummary as jest.Mock).mockResolvedValue({ ok: false, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } });
    const { result } = renderHook(() => useSecurity(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.error?.safeMessage).toBe("Network error");
  });
});
