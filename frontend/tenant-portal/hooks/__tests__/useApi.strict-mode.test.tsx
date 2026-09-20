import React, { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useAction, useApi } from "../useApi";

describe("useApi Strict Mode loading", () => {
  it("starts only one automatic request", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ready: true });
    const wrapper = ({ children }: { children: React.ReactNode }) => <StrictMode>{children}</StrictMode>;

    const { result } = renderHook(() => useApi(fetcher), { wrapper });

    await waitFor(() => expect(result.current.data).toEqual({ ready: true }));
    expect(fetcher).toHaveBeenCalledOnce();
    expect(result.current.error).toBeNull();
  });

  it("recovers once from a transient browser-level read failure", async () => {
    const fetcher = vi.fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce({ ready: true });

    const { result } = renderHook(() => useApi(fetcher));

    await waitFor(() => expect(result.current.data).toEqual({ ready: true }));
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(result.current.error).toBeNull();
  });
});

describe("useAction validation errors", () => {
  it("shows the actionable local validation message", async () => {
    const { result } = renderHook(() => useAction(async () => {
      throw new Error("Enter an exact price for Tap change.");
    }));

    await act(async () => { await result.current.execute(); });

    expect(result.current.error).toBe("Enter an exact price for Tap change.");
  });
});
