import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addressApi, type AddressPayload } from "../api/address-api";
import { parseAddress, parseAddressList, parseDeleteAddressResponse, type ValidatedAddress } from "../domain/address-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

/** Customer isolation comes from the backend (ownership-enforced on every endpoint) — the key still scopes by locale/tenant defensively, matching every previous sprint's pattern. */
export const addressQueryKeys = {
  list: (locale: string, tenantId: string | undefined) => ["address", "list", locale, tenantId ?? "no-tenant"] as const,
};

export function useAddresses() {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery<ValidatedAddress[]>({
    queryKey: addressQueryKeys.list(locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await addressApi.listAddresses({ signal });
      const parsed = parseAddressList(response);
      if (!parsed) {
        logger.warn("address_list_validation_failed", {});
        throw new ApiError({ category: "validation_error", message: "Address list response did not match the expected shape." });
      }
      if (parsed.droppedCount > 0) logger.warn("address_list_items_dropped", { droppedCount: parsed.droppedCount });
      return parsed.addresses;
    },
    staleTime: 30_000,
  });
}

function invalidateAddressList(queryClient: ReturnType<typeof useQueryClient>) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();
  void queryClient.invalidateQueries({ queryKey: addressQueryKeys.list(locale, tenantId) });
}

export function useCreateAddress() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AddressPayload) => {
      const response = await addressApi.createAddress(payload);
      const parsed = parseAddress(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Address creation response did not match the expected shape." });
      logger.info("address_created", {});
      return parsed;
    },
    onSuccess: () => invalidateAddressList(queryClient),
  });
}

export function useUpdateAddress() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { addressId: string; payload: Partial<AddressPayload> }) => {
      const response = await addressApi.updateAddress(params.addressId, params.payload);
      const parsed = parseAddress(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Address update response did not match the expected shape." });
      logger.info("address_updated", {});
      return parsed;
    },
    onSuccess: () => invalidateAddressList(queryClient),
  });
}

export function useDeleteAddress() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (addressId: string) => {
      const response = await addressApi.deleteAddress(addressId);
      const parsed = parseDeleteAddressResponse(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Delete response did not match the expected shape." });
      logger.info("address_deleted", {});
      return parsed;
    },
    onSuccess: () => invalidateAddressList(queryClient),
  });
}

export function useSetDefaultAddress() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (addressId: string) => {
      const response = await addressApi.setDefaultAddress(addressId);
      const parsed = parseAddress(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Set-default response did not match the expected shape." });
      return parsed;
    },
    onSuccess: () => invalidateAddressList(queryClient),
  });
}
