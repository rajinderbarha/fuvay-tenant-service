import React, { StrictMode } from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useApi } from "../useApi";

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
