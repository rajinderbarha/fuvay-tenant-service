import { useCallback, useEffect, useRef, useState } from "react";
import * as placesApi from "../api/places/placesApi";
import { PlaceAddressDto, PlaceSuggestionDto } from "../api/contracts/places";
import { useDebouncedValue } from "./useDebouncedValue";

export interface ResolvedAddress {
  formattedAddress: string | null;
  line1: string | null;
  city: string | null;
  state: string | null;
  zipcode: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface AddressAutocompleteState {
  suggestions: PlaceSuggestionDto[];
  /** Whether this deployment has address lookup at all. False hides the whole
   * affordance rather than showing one that can never return anything. */
  available: boolean;
  searching: boolean;
  resolving: boolean;
  /** Feeds the query. Debounced internally -- Places bills per request. */
  setQuery: (value: string) => void;
  clear: () => void;
  /** Resolves a suggestion into the fields the address form stores. */
  select: (placeId: string) => Promise<ResolvedAddress | null>;
}

/** One address entry is one billable Google SESSION, provided the same token goes on
 * every keystroke and on the final details call. A fresh token per entry, and a new
 * one after each successful resolve, is what keeps that true. */
function newSessionToken(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Address autocomplete, shared by every place a customer enters an address.
 *
 * Lives in a hook rather than a component because the two surfaces that need it --
 * the booking chat's address turn and the saved-addresses form -- look nothing alike
 * but need identical behaviour: same debounce, same session-token discipline, same
 * "no key means no affordance" rule.
 *
 * Failure is silent by design. If a lookup fails, suggestions are simply empty and
 * the customer types the address as they always could; an error banner over an
 * optional convenience would be worse than the convenience being absent.
 */
export function useAddressAutocomplete(): AddressAutocompleteState {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<PlaceSuggestionDto[]>([]);
  const [available, setAvailable] = useState(true);
  const [searching, setSearching] = useState(false);
  const [resolving, setResolving] = useState(false);
  const sessionToken = useRef(newSessionToken());
  // Guards against a slow earlier keystroke landing after a faster later one and
  // replacing the current suggestions with stale ones.
  const generation = useRef(0);

  const debounced = useDebouncedValue(query, 350);

  useEffect(() => {
    const term = debounced.trim();
    if (term.length < 3) {
      setSuggestions([]);
      setSearching(false);
      return;
    }
    const mine = ++generation.current;
    setSearching(true);
    placesApi.suggestAddresses(term, sessionToken.current)
      .then(res => {
        if (mine !== generation.current) return;
        setAvailable(res.data.configured);
        setSuggestions(res.data.suggestions);
      })
      .catch(() => {
        if (mine !== generation.current) return;
        // Silent: the typed form still works, which is the whole fallback.
        setSuggestions([]);
      })
      .finally(() => {
        if (mine === generation.current) setSearching(false);
      });
  }, [debounced]);

  const clear = useCallback(() => {
    generation.current += 1;
    setQuery("");
    setSuggestions([]);
    setSearching(false);
  }, []);

  const select = useCallback(async (placeId: string): Promise<ResolvedAddress | null> => {
    setResolving(true);
    try {
      const res = await placesApi.resolveAddress(placeId, sessionToken.current);
      // A new session starts after a completed lookup, so the next address entry is
      // billed as its own session rather than extending this one.
      sessionToken.current = newSessionToken();
      const address: PlaceAddressDto | null = res.data.address;
      if (!res.data.resolved || !address) return null;
      setSuggestions([]);
      return {
        formattedAddress: address.formatted_address,
        line1: address.line1,
        city: address.city,
        state: address.state,
        zipcode: address.zipcode,
        latitude: address.latitude,
        longitude: address.longitude,
      };
    } catch {
      return null;
    } finally {
      setResolving(false);
    }
  }, []);

  return { suggestions, available, searching, resolving, setQuery, clear, select };
}
