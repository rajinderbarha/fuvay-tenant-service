import { useCallback } from "react";
import * as Location from "expo-location";
import { logger } from "../../../observability/logger";

export interface CurrentLocationPrefill {
  latitude: number;
  longitude: number;
  city: string;
  district: string;
  state: string;
  zipcode: string;
  country: string;
  addressLine1: string;
}

export type CurrentLocationOutcome = { outcome: "resolved"; prefill: CurrentLocationPrefill } | { outcome: "permission_denied" } | { outcome: "unavailable" };

/**
 * No backend geocoding exists (confirmed absent — see contract-matrix.md),
 * so this uses `expo-location`'s own OS-level reverse geocoder (no
 * third-party API key, no network call to any geocoding provider this app
 * controls). The result is always presented to the customer as an
 * *editable prefill*, never auto-submitted — CUSTOMER-L5-07 §17's "do not
 * submit raw coordinates as the full address without confirmation."
 * Permission is requested at point of use, never at startup.
 */
export function useCurrentLocation() {
  const resolveCurrentLocation = useCallback(async (): Promise<CurrentLocationOutcome> => {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (!permission.granted) {
      logger.info("current_location_requested", { result: "permission_denied" });
      return { outcome: "permission_denied" };
    }

    try {
      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const [address] = await Location.reverseGeocodeAsync({ latitude: position.coords.latitude, longitude: position.coords.longitude });
      if (!address) {
        logger.info("current_location_requested", { result: "unavailable" });
        return { outcome: "unavailable" };
      }

      const addressLine1 = [address.streetNumber, address.street].filter(Boolean).join(" ") || address.name || "";

      logger.info("current_location_resolved", {});
      return {
        outcome: "resolved",
        prefill: {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          city: address.city ?? "",
          district: address.subregion ?? "",
          state: address.region ?? "",
          zipcode: address.postalCode ?? "",
          country: address.country ?? "India",
          addressLine1,
        },
      };
    } catch {
      logger.info("current_location_requested", { result: "unavailable" });
      return { outcome: "unavailable" };
    }
  }, []);

  return { resolveCurrentLocation };
}
