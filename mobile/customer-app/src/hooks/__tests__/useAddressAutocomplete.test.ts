import { act, renderHook, waitFor } from "@testing-library/react-native";
import { useAddressAutocomplete } from "../useAddressAutocomplete";
import * as placesApi from "../../api/places/placesApi";

jest.mock("../../api/places/placesApi");

const suggest = placesApi.suggestAddresses as jest.Mock;
const resolve = placesApi.resolveAddress as jest.Mock;

function suggestionsResponse(configured: boolean, descriptions: string[]) {
  return {
    data: {
      configured,
      suggestions: descriptions.map((description, i) => ({ place_id: `p-${i}`, description })),
    },
  };
}

describe("useAddressAutocomplete", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    suggest.mockResolvedValue(suggestionsResponse(true, ["Bassi Pathana, Punjab, India"]));
  });

  it("never queries for a term shorter than three characters", async () => {
    const { result } = renderHook(() => useAddressAutocomplete());
    act(() => result.current.setQuery("Ba"));
    await waitFor(() => expect(result.current.searching).toBe(false));
    expect(suggest).not.toHaveBeenCalled();
    expect(result.current.suggestions).toEqual([]);
  });

  it("queries once a real term is typed and exposes the suggestions", async () => {
    const { result } = renderHook(() => useAddressAutocomplete());
    act(() => result.current.setQuery("Bassi"));
    await waitFor(() => expect(result.current.suggestions).toHaveLength(1));
    expect(suggest).toHaveBeenCalledWith("Bassi", expect.any(String));
  });

  it("sends the SAME session token for every keystroke of one address entry", async () => {
    // Google bills an autocomplete session, not a request. A fresh token per
    // keystroke would turn one address entry into a dozen billable sessions.
    const { result } = renderHook(() => useAddressAutocomplete());
    act(() => result.current.setQuery("Bass"));
    await waitFor(() => expect(suggest).toHaveBeenCalledTimes(1));
    act(() => result.current.setQuery("Bassi P"));
    await waitFor(() => expect(suggest).toHaveBeenCalledTimes(2));

    expect(suggest.mock.calls[0][1]).toBe(suggest.mock.calls[1][1]);
  });

  it("reports unavailable when the deployment has no Places key configured", async () => {
    suggest.mockResolvedValue(suggestionsResponse(false, []));
    const { result } = renderHook(() => useAddressAutocomplete());
    act(() => result.current.setQuery("Bassi"));
    await waitFor(() => expect(result.current.available).toBe(false));
  });

  it("stays available and simply shows nothing when a lookup fails", async () => {
    // The typed form is the fallback; an error banner over an optional
    // convenience would be worse than the convenience being absent.
    suggest.mockRejectedValue(new Error("network"));
    const { result } = renderHook(() => useAddressAutocomplete());
    act(() => result.current.setQuery("Bassi"));
    await waitFor(() => expect(result.current.searching).toBe(false));
    expect(result.current.suggestions).toEqual([]);
  });

  it("returns the resolved fields, keeping absent ones null rather than invented", async () => {
    resolve.mockResolvedValue({
      data: {
        resolved: true,
        address: {
          formatted_address: "Bassi Pathana, Punjab, India", line1: "Bassi Pathana",
          city: "Bassi Pathana", state: "Punjab",
          zipcode: null, latitude: 30.6861187, longitude: 76.4042404,
        },
      },
    });
    const { result } = renderHook(() => useAddressAutocomplete());

    let resolved: Awaited<ReturnType<typeof result.current.select>> = null;
    await act(async () => { resolved = await result.current.select("p-0"); });

    expect(resolved).toEqual({
      formattedAddress: "Bassi Pathana, Punjab, India", line1: "Bassi Pathana",
      city: "Bassi Pathana", state: "Punjab",
      zipcode: null, latitude: 30.6861187, longitude: 76.4042404,
    });
  });

  it("returns null when the place could not be resolved", async () => {
    resolve.mockResolvedValue({ data: { resolved: false, address: null } });
    const { result } = renderHook(() => useAddressAutocomplete());
    let resolved: unknown = "unset";
    await act(async () => { resolved = await result.current.select("p-0"); });
    expect(resolved).toBeNull();
  });

  it("starts a new billable session after a completed resolve", async () => {
    resolve.mockResolvedValue({ data: { resolved: false, address: null } });
    const { result } = renderHook(() => useAddressAutocomplete());

    act(() => result.current.setQuery("Bassi"));
    await waitFor(() => expect(suggest).toHaveBeenCalledTimes(1));
    const firstToken = suggest.mock.calls[0][1];

    await act(async () => { await result.current.select("p-0"); });

    act(() => result.current.setQuery("Morinda"));
    await waitFor(() => expect(suggest).toHaveBeenCalledTimes(2));
    expect(suggest.mock.calls[1][1]).not.toBe(firstToken);
  });
});
