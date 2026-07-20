import { useEffect, useState } from "react";

/** Generic debounce — used by the search input so every keystroke does not trigger a request (CUSTOMER-L5-04 §18). */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);

  return debounced;
}
