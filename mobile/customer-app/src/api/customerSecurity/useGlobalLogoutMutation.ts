import { useMutation, useQueryClient } from "@tanstack/react-query";
import { logoutAllSessions } from "./customerSecurityApi";
import { logout } from "../session/sessionManager";

/** `POST /v1/auth/logout-all` revokes every session including the current
 * one (confirmed in `AuthService.logout_all`) -- only AFTER an
 * authoritative server success do we clear local credentials/cache via
 * the shared `sessionManager.logout()` (spec section 10: never clear only
 * the local session while claiming all devices were signed out). */
export function useGlobalLogoutMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => logoutAllSessions(),
    onSuccess: async () => {
      await logout();
      queryClient.clear();
    },
  });
}
