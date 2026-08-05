import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listJobPartsRequests, approvePartsRequest, declinePartsRequest } from "./customerPartsApi";
import { adaptCustomerPartsRequestList } from "../adapters/customerParts";

const partsKey = (jobId: string) => ["customer-parts", "job", jobId] as const;

export function usePartsRequestsQuery(jobId: string, enabled: boolean) {
  return useQuery({
    queryKey: partsKey(jobId),
    queryFn: async () => adaptCustomerPartsRequestList((await listJobPartsRequests(jobId)).data),
    enabled,
  });
}

export function useApprovePartsRequestMutation(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (partsRequestId: string) => (await approvePartsRequest(partsRequestId)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: partsKey(jobId) }),
  });
}

export function useDeclinePartsRequestMutation(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ partsRequestId, reason }: { partsRequestId: string; reason: string }) =>
      (await declinePartsRequest(partsRequestId, reason)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: partsKey(jobId) }),
  });
}
