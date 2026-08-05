import React from "react";
import { renderWithProviders } from "../../testing/renderWithProviders";
import { OfflineBanner } from "../OfflineBanner";
import * as networkState from "../../api/networkState";

describe("OfflineBanner", () => {
  afterEach(() => {
    networkState.__resetNetworkStateForTests();
    jest.restoreAllMocks();
  });

  it("renders nothing when the network state is online", () => {
    jest.spyOn(networkState, "getNetworkState").mockReturnValue("online");
    const { queryByText } = renderWithProviders(<OfflineBanner />);
    expect(queryByText(/You're offline/)).toBeNull();
  });

  it("renders the offline message when the network state is offline", () => {
    jest.spyOn(networkState, "getNetworkState").mockReturnValue("offline");
    const { getByText } = renderWithProviders(<OfflineBanner />);
    expect(getByText(/You're offline/)).toBeTruthy();
  });
});
