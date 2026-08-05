import { useCallback } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listMySupportRequests, createMySupportRequest, getMySupportRequest,
  cancelMySupportRequest, listMySupportRequestMessages, addMySupportRequestMessage,
} from "./supportRequestsApi";
import { adaptSupportRequest, adaptSupportRequestMessage } from "../adapters/supportRequests";
import { CreateSupportRequestBody } from "../contracts/supportRequests";
import { SupportRequest } from "../../domain/supportRequests";
import { DomainError } from "../../domain/errors";

export type SupportRequestDetailResult =
  | { kind: "found"; request: SupportRequest }
  | { kind: "unavailable" };

export const supportRequestQueryKeys = {
  list: () => ["customer", "supportRequests", "list"] as const,
  detail: (requestId: string) => ["customer", "supportRequests", "detail", requestId] as const,
  messages: (requestId: string) => ["customer", "supportRequests", "messages", requestId] as const,
};

export function useSupportRequestsListQuery() {
  return useQuery({
    queryKey: supportRequestQueryKeys.list(),
    queryFn: async () => {
      const res = await listMySupportRequests();
      return res.data.map(adaptSupportRequest);
    },
  });
}

/** Missing and foreign IDs both collapse to `unavailable` -- the backend's
 * `get_customer_complaint` raises a distinct `COMPLAINT_ACCESS_DENIED`
 * (403) for a foreign request vs `COMPLAINT_NOT_FOUND` (404) for a
 * missing one (a real, pre-existing, deliberately-tested asymmetry in
 * `app/engines/complaints/complaint_service.py` -- see the final report's
 * disclosed gap). This hook does not distinguish the two toward the UI
 * either way, so the screen itself never learns which case occurred. */
export function useSupportRequestDetailQuery(requestId: string) {
  const query = useQuery({
    queryKey: supportRequestQueryKeys.detail(requestId),
    queryFn: async (): Promise<SupportRequestDetailResult> => {
      try {
        const res = await getMySupportRequest(requestId);
        return { kind: "found", request: adaptSupportRequest(res.data) };
      } catch (err) {
        if (err instanceof DomainError && (err.httpStatus === 404 || err.httpStatus === 403)) {
          return { kind: "unavailable" };
        }
        throw err;
      }
    },
  });

  useFocusEffect(
    useCallback(() => {
      query.refetch();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [requestId]),
  );

  return query;
}

export function useCreateSupportRequestMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateSupportRequestBody) => createMySupportRequest(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supportRequestQueryKeys.list() });
    },
  });
}

export function useCancelSupportRequestMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ requestId, reason }: { requestId: string; reason: string }) =>
      cancelMySupportRequest(requestId, reason),
    onSuccess: (_data, { requestId }) => {
      queryClient.invalidateQueries({ queryKey: supportRequestQueryKeys.list() });
      queryClient.invalidateQueries({ queryKey: supportRequestQueryKeys.detail(requestId) });
    },
  });
}

export function useSupportRequestMessagesQuery(requestId: string) {
  return useQuery({
    queryKey: supportRequestQueryKeys.messages(requestId),
    queryFn: async () => {
      const res = await listMySupportRequestMessages(requestId);
      return res.data.map(adaptSupportRequestMessage);
    },
  });
}

export function useAddSupportRequestMessageMutation(requestId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (messageText: string) => addMySupportRequestMessage(requestId, messageText),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supportRequestQueryKeys.messages(requestId) });
    },
  });
}
