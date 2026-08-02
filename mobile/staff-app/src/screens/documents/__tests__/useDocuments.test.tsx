import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useDocuments } from "../useDocuments";

jest.mock("../../../services/documents/documentsApi");
jest.mock("../../../services/media/mediaApi");
jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ accessContext: { userId: "user-1" } }),
}));
import * as api from "../../../services/documents/documentsApi";
import * as mediaApi from "../../../services/media/mediaApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const BASE = { readiness: { percentage: 0, complete: 0, required: 2, action_needed: 2, pending: 0, verified: 0 }, requirements: [] };

beforeEach(() => jest.clearAllMocks());

describe("useDocuments (Phase T)", () => {
  it("loads the documents projection", async () => {
    (api.getDocuments as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    const { result } = renderHook(() => useDocuments(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getDocuments).toHaveBeenCalled();
  });

  it("submit uploads then submits the document, then refetches rather than mutating locally", async () => {
    (api.getDocuments as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (mediaApi.uploadStaffDocument as jest.Mock).mockResolvedValue({ ok: true, data: { id: "media-1" } });
    (api.submitDocument as jest.Mock).mockResolvedValue({ ok: true, data: { id: "doc-1", status: "pending_review" } });
    const { result } = renderHook(() => useDocuments(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.submit("technician_identity_proof", "file://a.jpg", "a.jpg", "image/jpeg"); });

    expect(mediaApi.uploadStaffDocument).toHaveBeenCalledWith("file://a.jpg", "a.jpg", "image/jpeg", "user-1");
    expect(api.submitDocument).toHaveBeenCalledWith({ docType: "technician_identity_proof", mediaAssetId: "media-1" });
    expect(api.getDocuments).toHaveBeenCalledTimes(2);
  });

  it("surfaces an upload error without calling submitDocument", async () => {
    (api.getDocuments as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (mediaApi.uploadStaffDocument as jest.Mock).mockResolvedValue({ ok: false, error: { code: "VALIDATION_ERROR", category: "validation", safeMessage: "Couldn't upload.", retryable: false } });
    const { result } = renderHook(() => useDocuments(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.submit("technician_identity_proof", "file://a.jpg", "a.jpg", "image/jpeg"); });

    expect(api.submitDocument).not.toHaveBeenCalled();
    expect(result.current.uploadError?.safeMessage).toBe("Couldn't upload.");
  });
});
