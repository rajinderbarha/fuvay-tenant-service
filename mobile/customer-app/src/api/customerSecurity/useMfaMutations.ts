import { useMutation, useQueryClient } from "@tanstack/react-query";
import { setupMfa, confirmMfa, disableMfa } from "./customerSecurityApi";
import { queryKeys } from "../queryKeys";

/** Returns the temporary enrollment secret + backup codes -- caller must
 * never cache/persist this response beyond the enrollment screen's local
 * state (spec section 8/14). */
export function useSetupMfaMutation() {
  return useMutation({ mutationFn: () => setupMfa() });
}

export function useConfirmMfaMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => confirmMfa(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.customerProfile() });
    },
  });
}

export function useDisableMfaMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ password, code }: { password: string; code: string }) => disableMfa(password, code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.customerProfile() });
    },
  });
}
