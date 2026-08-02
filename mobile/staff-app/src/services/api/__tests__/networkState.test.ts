import NetInfo from "@react-native-community/netinfo";
import {
  startNetworkMonitoring, stopNetworkMonitoring, getNetworkState, isOffline,
  subscribeNetworkState, onReconnect, __resetNetworkStateForTests,
} from "../networkState";
import { getRetryDecision } from "../retryPolicy";
import { AppError } from "../types";

function fireNetInfoEvent(state: Partial<{ isConnected: boolean; isInternetReachable: boolean }>) {
  const listener = (NetInfo.addEventListener as jest.Mock).mock.calls.at(-1)?.[0];
  listener?.(state);
}

beforeEach(() => {
  __resetNetworkStateForTests();
  stopNetworkMonitoring();
  jest.clearAllMocks();
});

describe("network state classification", () => {
  it("classifies isConnected:false as offline", () => {
    startNetworkMonitoring();
    fireNetInfoEvent({ isConnected: false });
    expect(getNetworkState()).toBe("offline");
    expect(isOffline()).toBe(true);
  });

  it("classifies isInternetReachable:false (connected but no internet) distinctly", () => {
    startNetworkMonitoring();
    fireNetInfoEvent({ isConnected: true, isInternetReachable: false });
    expect(getNetworkState()).toBe("internet_reachable_false");
    expect(isOffline()).toBe(true);
  });

  it("classifies a fully healthy connection as online", () => {
    startNetworkMonitoring();
    fireNetInfoEvent({ isConnected: true, isInternetReachable: true });
    expect(getNetworkState()).toBe("online");
    expect(isOffline()).toBe(false);
  });
});

describe("reconnect detection", () => {
  it("fires onReconnect exactly once when transitioning from offline to online", () => {
    startNetworkMonitoring();
    fireNetInfoEvent({ isConnected: false });
    const handler = jest.fn();
    onReconnect(handler);
    fireNetInfoEvent({ isConnected: true, isInternetReachable: true });
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("does not fire onReconnect for an online->online transition", () => {
    startNetworkMonitoring();
    fireNetInfoEvent({ isConnected: true, isInternetReachable: true });
    const handler = jest.fn();
    onReconnect(handler);
    fireNetInfoEvent({ isConnected: true, isInternetReachable: true });
    expect(handler).not.toHaveBeenCalled();
  });

  it("notifies subscribeNetworkState listeners on every real transition", () => {
    startNetworkMonitoring();
    const listener = jest.fn();
    subscribeNetworkState(listener);
    fireNetInfoEvent({ isConnected: false });
    expect(listener).toHaveBeenCalledWith("offline");
  });
});

describe("retry policy pauses while offline (spec section 15)", () => {
  it("suppresses an otherwise-retryable error while offline", () => {
    startNetworkMonitoring();
    fireNetInfoEvent({ isConnected: false });
    const error: AppError = { code: "SERVER_UNAVAILABLE", category: "server", safeMessage: "x", retryable: true };
    expect(getRetryDecision(error, 1, false).shouldRetry).toBe(false);
  });
});
