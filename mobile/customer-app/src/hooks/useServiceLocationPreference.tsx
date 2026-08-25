import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  clearServiceLocationPreference,
  loadServiceLocationPreference,
  normalizeServiceZipcode,
  saveServiceLocationPreference,
} from "../storage/serviceLocationPreference";

interface ServiceLocationPreference {
  zipcode: string | null;
  isLoaded: boolean;
  setZipcode: (zipcode: string) => Promise<void>;
  clearZipcode: () => Promise<void>;
}

const ServiceLocationContext = createContext<ServiceLocationPreference | undefined>(undefined);

/**
 * One app-wide source of truth. Keeping this above the tab navigator is
 * essential: tab screens stay mounted, so isolated hook state would leave an
 * already-mounted Assistant unaware of a PIN selected later on Home.
 */
export function ServiceLocationProvider({ children }: { children: React.ReactNode }) {
  const [zipcode, setZipcodeState] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;
    loadServiceLocationPreference()
      .then(value => {
        if (mounted) setZipcodeState(value);
      })
      .catch(() => {
        if (mounted) setZipcodeState(null);
      })
      .finally(() => {
        if (mounted) setIsLoaded(true);
      });
    return () => { mounted = false; };
  }, []);

  const setZipcode = useCallback(async (nextZipcode: string) => {
    const normalized = normalizeServiceZipcode(nextZipcode);
    if (!normalized) throw new Error("Invalid service location");
    // Update immediately so tab navigation never waits for storage I/O.
    setZipcodeState(normalized);
    try {
      await saveServiceLocationPreference(normalized);
    } catch (error) {
      // Keep the in-memory selection useful for the current session while
      // still surfacing the persistence error to the caller if it cares.
      throw error;
    }
  }, []);

  const clearZipcode = useCallback(async () => {
    setZipcodeState(null);
    await clearServiceLocationPreference();
  }, []);

  const value = useMemo(
    () => ({ zipcode, isLoaded, setZipcode, clearZipcode }),
    [zipcode, isLoaded, setZipcode, clearZipcode],
  );

  return <ServiceLocationContext.Provider value={value}>{children}</ServiceLocationContext.Provider>;
}

/** Shared native service-location state for Home and the Booking Assistant. */
export function useServiceLocationPreference(): ServiceLocationPreference {
  const context = useContext(ServiceLocationContext);
  if (!context) throw new Error("useServiceLocationPreference must be used within ServiceLocationProvider");
  return context;
}
