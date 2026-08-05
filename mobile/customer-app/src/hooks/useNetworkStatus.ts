import { useEffect, useState } from "react";
import { getNetworkState, subscribeNetworkState, NetworkState } from "../api/networkState";

/** Publishes the current network state to a component without coupling it
 * to NetInfo directly. */
export function useNetworkStatus(): NetworkState {
  const [status, setStatus] = useState<NetworkState>(getNetworkState());
  useEffect(() => subscribeNetworkState(setStatus), []);
  return status;
}
