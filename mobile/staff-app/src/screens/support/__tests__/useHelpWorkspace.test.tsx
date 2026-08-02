import React from "react";
import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useHelpWorkspace } from "../useHelpWorkspace";

jest.mock("../../../services/support/supportApi");
jest.mock("../../../services/employment/employmentApi");
import * as api from "../../../services/support/supportApi";
import * as employmentApi from "../../../services/employment/employmentApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const WORKSPACE = {
  service_status: { state: "operational", message: "All good", last_checked_at: null, evidence_fresh: true, affected_components: [], active_incident_count: 0 },
  summary: { open: 1, awaiting_your_reply: 0, resolved: 2, total: 3 },
  requests: [], requests_total: 0,
  quick_help: [{ key: "bookings_jobs", label: "Bookings & jobs", icon: "wrench", description: "", article_count: 3, has_content: true }],
  recommended_articles: [], knowledge_total: 3,
  form_options: { categories: [], impacts: [] },
  permissions: { can_view: true, can_create: true, can_reply: true, can_reopen: false },
};

beforeEach(() => jest.clearAllMocks());

describe("useHelpWorkspace (Phase Y)", () => {
  it("loads the real workspace and manager contact", async () => {
    (api.getWorkspace as jest.Mock).mockResolvedValue({ ok: true, data: WORKSPACE });
    (employmentApi.getEmploymentDetails as jest.Mock).mockResolvedValue({
      ok: true, data: { employment: { reports_to: { display_name: "Rajiv Kumar", designation: "Service Manager" } } },
    });
    const { result } = renderHook(() => useHelpWorkspace(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.service_status.state).toBe("operational");
    await waitFor(() => expect(result.current.manager?.display_name).toBe("Rajiv Kumar"));
  });

  it("surfaces an error without throwing", async () => {
    (api.getWorkspace as jest.Mock).mockResolvedValue({ ok: false, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } });
    (employmentApi.getEmploymentDetails as jest.Mock).mockResolvedValue({ ok: true, data: { employment: null } });
    const { result } = renderHook(() => useHelpWorkspace(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.error?.safeMessage).toBe("Network error");
  });
});
