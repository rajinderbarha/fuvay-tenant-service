import { useInfiniteQuery } from "@tanstack/react-query";
import { getMyLoginActivity } from "./customerSecurityApi";
import { adaptLoginActivityEvent } from "../adapters/customerSecurity";
import { LoginActivityFilter } from "../../domain/customerSecurity";

export const LOGIN_ACTIVITY_QUERY_KEY = (filter: LoginActivityFilter) =>
  ["customer", "security", "loginActivity", filter] as const;

/** Real cursor pagination (spec section 17) -- `next_cursor` comes
 * straight from the backend's own keyset cursor, never a client-computed
 * offset. */
export function useLoginActivityQuery(filter: LoginActivityFilter) {
  return useInfiniteQuery({
    queryKey: LOGIN_ACTIVITY_QUERY_KEY(filter),
    queryFn: async ({ pageParam }: { pageParam: string | undefined }) => {
      const res = await getMyLoginActivity(filter, pageParam);
      return {
        events: res.data.events.map(adaptLoginActivityEvent),
        nextCursor: res.data.next_cursor,
      };
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: last => last.nextCursor ?? undefined,
  });
}
