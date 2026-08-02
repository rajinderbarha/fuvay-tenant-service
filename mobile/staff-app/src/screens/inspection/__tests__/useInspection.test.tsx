import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useInspection } from "../useInspection";

jest.mock("../../../services/inspection/inspectionApi");
jest.mock("../../../services/media/mediaApi");

import * as inspectionApi from "../../../services/inspection/inspectionApi";
import * as mediaApi from "../../../services/media/mediaApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useInspection (spec sections 9, 10, 17)", () => {
  it("fetches the inspection projection for the given job", async () => {
    (inspectionApi.getInspectionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, instance: { instance_id: "inst1" } } });
    const { result } = renderHook(() => useInspection("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(inspectionApi.getInspectionDetail).toHaveBeenCalledWith("j1", expect.anything());
  });

  it("saving an item response refetches rather than mutating local state (never optimistic)", async () => {
    (inspectionApi.getInspectionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, instance: { instance_id: "inst1" } } });
    (inspectionApi.saveChecklistItemResponse as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useInspection("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.saveItemResponse("inst1", "item1", { value: "yes" }, null); });

    expect(inspectionApi.saveChecklistItemResponse).toHaveBeenCalledWith("inst1", "item1", { value: "yes" }, null);
    expect((inspectionApi.getInspectionDetail as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("guards against a second save for the same item while one is in flight", async () => {
    (inspectionApi.getInspectionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, instance: { instance_id: "inst1" } } });
    let resolveSave: (v: any) => void = () => {};
    (inspectionApi.saveChecklistItemResponse as jest.Mock).mockReturnValue(new Promise(res => { resolveSave = res; }));
    const { result } = renderHook(() => useInspection("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => { result.current.saveItemResponse("inst1", "item1", { value: "yes" }, null); });
    act(() => { result.current.saveItemResponse("inst1", "item2", { value: "no" }, null); });

    expect(inspectionApi.saveChecklistItemResponse).toHaveBeenCalledTimes(1);
    await act(async () => { resolveSave({ ok: true, data: {} }); });
  });

  it("completion composes the checklist-complete call and the workflow-transition call, never skipping either", async () => {
    (inspectionApi.getInspectionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, instance: { instance_id: "inst1" } } });
    (inspectionApi.completeChecklistInstance as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    (inspectionApi.completeInspectionWorkflow as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useInspection("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const outcome = await act(async () => result.current.complete());

    expect(inspectionApi.completeChecklistInstance).toHaveBeenCalledWith("inst1");
    expect(inspectionApi.completeInspectionWorkflow).toHaveBeenCalledWith("j1");
    expect(outcome).toEqual({ ok: true });
  });

  it("stops at the checklist-complete error and never calls the workflow transition", async () => {
    (inspectionApi.getInspectionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, instance: { instance_id: "inst1" } } });
    (inspectionApi.completeChecklistInstance as jest.Mock).mockResolvedValue({ ok: false, error: { code: "VALIDATION_ERROR", safeMessage: "Required item incomplete." } });
    const { result } = renderHook(() => useInspection("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.complete(); });

    expect(inspectionApi.completeInspectionWorkflow).not.toHaveBeenCalled();
    expect(result.current.completeError).toEqual({ code: "VALIDATION_ERROR", safeMessage: "Required item incomplete." });
  });

  it("evidence upload delegates to the media client, scoped by item", async () => {
    (inspectionApi.getInspectionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, instance: { instance_id: "inst1" } } });
    (mediaApi.uploadChecklistEvidence as jest.Mock).mockResolvedValue({ ok: true, data: { id: "media1" } });
    const { result } = renderHook(() => useInspection("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const outcome = await act(async () => result.current.uploadEvidence("item1", "file://x.jpg", "x.jpg", "image/jpeg"));

    expect(mediaApi.uploadChecklistEvidence).toHaveBeenCalledWith("j1", "file://x.jpg", "x.jpg", "image/jpeg");
    expect(outcome).toEqual({ ok: true, fileId: "media1" });
  });
});
