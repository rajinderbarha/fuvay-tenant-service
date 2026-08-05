import { useMutation, useQueryClient } from "@tanstack/react-query";
import { changePassword } from "./customerSecurityApi";
import { ChangePasswordRequest } from "../contracts/customerSecurity";
import { queryKeys } from "../queryKeys";

export function useChangePasswordMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ChangePasswordRequest) => changePassword(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.customerProfile() });
    },
  });
}
