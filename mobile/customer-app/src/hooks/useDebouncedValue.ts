import { useEffect, useState } from "react";

/**
 * Delays propagating a rapidly-changing value (a search box's text) until
 * it has been still for `delayMs`.
 *
 * The pending timer is cleared on every change, so only the final value in
 * a burst of typing is ever published -- one request per pause, not one
 * per keystroke.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
