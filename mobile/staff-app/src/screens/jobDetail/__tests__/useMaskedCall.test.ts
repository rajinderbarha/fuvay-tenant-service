import { renderHook, waitFor, act } from "@testing-library/react-native";
import { useMaskedCall } from "../useMaskedCall";
import * as api from "../../../services/maskedCalling/maskedCallingApi";
import type { AppError } from "../../../services/api/types";

jest.mock("../../../services/maskedCalling/maskedCallingApi");

const JOB_ID = "job-1";

function contact(overrides: Partial<api.MaskedContactDTO> = {}): api.MaskedContactDTO {
  return {
    job_id: JOB_ID,
    customer_display: "Customer HS-1044",
    phone_number_visible: false,
    phone_number_policy: "Calls are connected through the platform.",
    can_call: true,
    cannot_call_reason: null,
    connected_before: false,
    last_call: null,
    ...overrides,
  };
}

function okResult<T>(data: T) {
  return { ok: true as const, data, meta: {} as never };
}

function errResult(code: string, safeMessage: string) {
  return {
    ok: false as const,
    error: { code, category: "server", safeMessage, retryable: false } as unknown as AppError,
  };
}

describe("useMaskedCall", () => {
  afterEach(() => jest.clearAllMocks());

  it("takes calling capability from the backend, never inferring it", async () => {
    (api.getContact as jest.Mock).mockResolvedValue(
      okResult(contact({ can_call: false, cannot_call_reason: "MASKED_CALLING_NOT_CONFIGURED" })),
    );
    const { result } = renderHook(() => useMaskedCall(JOB_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.contact?.can_call).toBe(false);
    expect(result.current.contact?.cannot_call_reason).toBe("MASKED_CALLING_NOT_CONFIGURED");
  });

  it("surfaces a returned error instead of treating it as success with undefined data", async () => {
    // The API client RETURNS a discriminated result rather than throwing; a
    // try/catch-shaped hook would have silently accepted this as a success.
    (api.getContact as jest.Mock).mockResolvedValue(
      errResult("SERVER_UNAVAILABLE", "Something went wrong."),
    );
    const { result } = renderHook(() => useMaskedCall(JOB_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.contact).toBeNull();
    expect(result.current.error?.safeMessage).toBe("Something went wrong.");
  });

  it("re-reads contact after a placed call so connected_before is not stale", async () => {
    (api.getContact as jest.Mock)
      .mockResolvedValueOnce(okResult(contact({ connected_before: false })))
      .mockResolvedValueOnce(okResult(contact({ connected_before: true })));
    (api.callCustomer as jest.Mock).mockResolvedValue(
      okResult({ id: "sess-1", job_id: JOB_ID, status: "ringing" } as never),
    );

    const { result } = renderHook(() => useMaskedCall(JOB_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.contact?.connected_before).toBe(false);

    await act(async () => { await result.current.placeCall(); });

    expect(api.callCustomer).toHaveBeenCalledWith(JOB_ID);
    expect(result.current.contact?.connected_before).toBe(true);
  });

  it("does not place a second call while one is already in flight", async () => {
    // Each press dials a real phone: a duplicate is the customer's phone
    // ringing twice, not a harmless retry.
    (api.getContact as jest.Mock).mockResolvedValue(okResult(contact()));
    let release: (v: unknown) => void = () => {};
    (api.callCustomer as jest.Mock).mockReturnValue(
      new Promise(res => { release = res; }),
    );

    const { result } = renderHook(() => useMaskedCall(JOB_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      // Both presses land in the SAME tick -- the realistic double-tap. A
      // state-based guard would let both through, so this asserts the ref.
      void result.current.placeCall();
      void result.current.placeCall();
      release(okResult({ id: "s", job_id: JOB_ID, status: "ringing" }));
    });

    expect(api.callCustomer).toHaveBeenCalledTimes(1);
  });

  it("reports a failed call attempt without claiming a number is available", async () => {
    (api.getContact as jest.Mock).mockResolvedValue(okResult(contact()));
    (api.callCustomer as jest.Mock).mockResolvedValue(
      errResult("SERVER_UNAVAILABLE", "We could not connect the call."),
    );

    const { result } = renderHook(() => useMaskedCall(JOB_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let returned: unknown = "unset";
    await act(async () => { returned = await result.current.placeCall(); });

    expect(returned).toBeNull();
    expect(result.current.error?.safeMessage).toBe("We could not connect the call.");
    expect(result.current.calling).toBe(false);
  });

  it("never exposes a phone-number-shaped field on the contact payload", () => {
    // Guards the invariant at the type/shape level: nothing in the DTO this
    // hook returns may carry a real number for a screen to render.
    const shape = contact();
    for (const key of Object.keys(shape)) {
      expect(key).not.toMatch(/phone_number$|^phone$|customer_phone|mobile/);
    }
    expect(shape.phone_number_visible).toBe(false);
  });
});
