import { useCallback, useEffect, useState } from "react";
import { addRecentSearch, getRecentSearches, removeRecentSearch, clearRecentSearches } from "../state/recent-search-storage";

/** Customer-scoped recent searches — see recent-search-storage.ts for the isolation/privacy rationale. */
export function useRecentSearches(customerId: string | undefined) {
  const [items, setItems] = useState<string[]>([]);

  useEffect(() => {
    if (!customerId) {
      setItems([]);
      return;
    }
    let cancelled = false;
    void getRecentSearches(customerId).then((loaded) => {
      if (!cancelled) setItems(loaded);
    });
    return () => {
      cancelled = true;
    };
  }, [customerId]);

  const add = useCallback(
    async (query: string) => {
      if (!customerId) return;
      setItems(await addRecentSearch(customerId, query));
    },
    [customerId]
  );

  const remove = useCallback(
    async (query: string) => {
      if (!customerId) return;
      setItems(await removeRecentSearch(customerId, query));
    },
    [customerId]
  );

  const clear = useCallback(async () => {
    if (!customerId) return;
    await clearRecentSearches(customerId);
    setItems([]);
  }, [customerId]);

  return { items, add, remove, clear };
}
