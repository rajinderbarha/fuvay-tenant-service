import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useProfile } from "../useProfile";

jest.mock("../../../services/profile/profileApi");
jest.mock("../../../services/media/mediaApi");
jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ accessContext: { userId: "user-1" } }),
}));
import * as api from "../../../services/profile/profileApi";
import * as mediaApi from "../../../services/media/mediaApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useProfile (Phase R)", () => {
  it("loads the profile projection", async () => {
    (api.getProfile as jest.Mock).mockResolvedValue({ ok: true, data: { identity: {}, employment: {}, readiness: { missing: [] }, documents: [], required_document_types: [], security: {} } });
    const { result } = renderHook(() => useProfile(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getProfile).toHaveBeenCalled();
  });

  it("submitDocument uploads then adds the document, then refetches rather than mutating locally", async () => {
    (api.getProfile as jest.Mock).mockResolvedValue({ ok: true, data: { identity: {}, employment: {}, readiness: { missing: [] }, documents: [], required_document_types: [], security: {} } });
    (mediaApi.uploadStaffDocument as jest.Mock).mockResolvedValue({ ok: true, data: { id: "media-1" } });
    (api.addDocument as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useProfile(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.submitDocument("identity_document", "file://a.jpg", "a.jpg", "image/jpeg"); });

    expect(mediaApi.uploadStaffDocument).toHaveBeenCalledWith("file://a.jpg", "a.jpg", "image/jpeg", "user-1");
    expect(api.addDocument).toHaveBeenCalledWith("identity_document", "media-1");
    expect(api.getProfile).toHaveBeenCalledTimes(2);
  });

  it("surfaces an upload error without calling addDocument", async () => {
    (api.getProfile as jest.Mock).mockResolvedValue({ ok: true, data: { identity: {}, employment: {}, readiness: { missing: [] }, documents: [], required_document_types: [], security: {} } });
    (mediaApi.uploadStaffDocument as jest.Mock).mockResolvedValue({ ok: false, error: { code: "UPLOAD_FAILED", safeMessage: "Couldn't upload." } });
    const { result } = renderHook(() => useProfile(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.submitDocument("identity_document", "file://a.jpg", "a.jpg", "image/jpeg"); });

    expect(api.addDocument).not.toHaveBeenCalled();
    expect(result.current.mutationError).toEqual({ code: "UPLOAD_FAILED", safeMessage: "Couldn't upload." });
  });
});
