import { useEffect, useRef } from "react";
import * as Location from "expo-location";
import { geoApi } from "../lib/api";

/**
 * Tracks staff GPS location and syncs to the Geo engine every 30s.
 * Call startTracking() when on an active job, stopTracking() otherwise.
 */
export function useLocation() {
  const interval = useRef<ReturnType<typeof setInterval> | null>(null);

  async function startTracking() {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") return;

    async function sync() {
      try {
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
        await geoApi.updateLocation(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy ?? undefined);
      } catch { /* fail silently */ }
    }

    await sync();
    interval.current = setInterval(sync, 30_000);
  }

  function stopTracking() {
    if (interval.current) { clearInterval(interval.current); interval.current = null; }
  }

  useEffect(() => () => { stopTracking(); }, []);

  return { startTracking, stopTracking };
}
