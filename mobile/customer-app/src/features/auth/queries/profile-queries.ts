import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "../api/auth-api";
import { toCustomerSession } from "../domain/session";
import { getSessionState, updateSessionProfile } from "../state/session-store";
import { queryKeys } from "../../../state/query-client";

export const profileQueryKeys = {
  root: () => queryKeys.all("customer-profile"),
};

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (patch: { full_name?: string; phone?: string }) => authApi.updateProfile(patch),
    onSuccess: (profile) => {
      const current = getSessionState().session;
      if (current) {
        const next = toCustomerSession({ accessToken: current.accessToken, refreshToken: current.refreshToken }, profile);
        updateSessionProfile(next);
      }
      void queryClient.invalidateQueries({ queryKey: profileQueryKeys.root() });
    },
  });
}
