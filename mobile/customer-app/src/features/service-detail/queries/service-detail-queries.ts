import { useQuery } from "@tanstack/react-query";
import { serviceDetailApi } from "../api/service-detail-api";
import { parseOfferingDetail, type ValidatedOfferingDetail } from "../../category/domain/offering-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

export const serviceDetailQueryKeys = {
  detail: (categoryId: string, serviceId: string, locale: string, tenantId: string | undefined) =>
    ["service", "detail", categoryId, serviceId, locale, tenantId ?? "no-tenant"] as const,
};

export function useServiceDetail(categoryId: string, serviceId: string) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery<ValidatedOfferingDetail>({
    queryKey: serviceDetailQueryKeys.detail(categoryId, serviceId, locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await serviceDetailApi.getOfferingDetail(categoryId, serviceId, { signal });
      const parsed = parseOfferingDetail(response);
      if (!parsed) {
        logger.warn("service_detail_validation_failed", { categoryId, serviceId });
        throw new ApiError({ category: "validation_error", message: "Service detail response did not match the expected shape." });
      }
      return parsed;
    },
    enabled: categoryId.length > 0 && serviceId.length > 0,
    staleTime: 5 * 60_000,
  });
}
