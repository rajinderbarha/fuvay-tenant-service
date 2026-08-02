import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCompletionProof } from "../useCompletionProof";

jest.mock("../../../services/completionProof/completionProofApi");
jest.mock("../../../services/media/mediaApi");

import * as api from "../../../services/completionProof/completionProofApi";
import * as mediaApi from "../../../services/media/mediaApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useCompletionProof (spec sections 12, 13, 17)", () => {
  it("fetches the completion-proof projection", async () => {
    (api.getCompletionProofDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, proof: { status: "draft" } } });
    const { result } = renderHook(() => useCompletionProof("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getCompletionProofDetail).toHaveBeenCalledWith("j1", expect.anything());
  });

  it("submit refetches rather than fabricating submitted state locally (never optimistic)", async () => {
    (api.getCompletionProofDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, proof: { status: "draft" } } });
    (api.submitCompletionProof as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useCompletionProof("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.submit(); });

    expect(api.submitCompletionProof).toHaveBeenCalledWith("j1");
    expect((api.getCompletionProofDetail as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("evidence upload uploads the file first, then attaches it via the real add-evidence call", async () => {
    (api.getCompletionProofDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, proof: { status: "draft" } } });
    (mediaApi.uploadChecklistEvidence as jest.Mock).mockResolvedValue({ ok: true, data: { id: "media1" } });
    (api.addEvidence as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useCompletionProof("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.addEvidenceFromUpload("after", "file://x.jpg", "x.jpg", "image/jpeg"); });

    expect(mediaApi.uploadChecklistEvidence).toHaveBeenCalledWith("j1", "file://x.jpg", "x.jpg", "image/jpeg");
    expect(api.addEvidence).toHaveBeenCalledWith("j1", "after", "media1");
  });

  it("guards against a duplicate mutation while one is in flight", async () => {
    (api.getCompletionProofDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, proof: { status: "draft" } } });
    let resolveSubmit: (v: any) => void = () => {};
    (api.submitCompletionProof as jest.Mock).mockReturnValue(new Promise(res => { resolveSubmit = res; }));
    const { result } = renderHook(() => useCompletionProof("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => { result.current.submit(); });
    act(() => { result.current.submit(); });

    expect(api.submitCompletionProof).toHaveBeenCalledTimes(1);
    await act(async () => { resolveSubmit({ ok: true, data: {} }); });
  });

  it("surfaces a mutation error without throwing", async () => {
    (api.getCompletionProofDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, proof: { status: "draft" } } });
    (api.submitCompletionProof as jest.Mock).mockResolvedValue({ ok: false, error: { code: "COMPLETION_PROOF_NOT_READY", safeMessage: "Complete every required item first." } });
    const { result } = renderHook(() => useCompletionProof("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.submit(); });

    expect(result.current.mutationError).toEqual({ code: "COMPLETION_PROOF_NOT_READY", safeMessage: "Complete every required item first." });
  });
});
