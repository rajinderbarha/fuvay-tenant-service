import { useQuery } from "@tanstack/react-query";
import { diagnosticsApi } from "../api/diagnostics-api";
import {
  parseIssueTypeList,
  parseServiceOptionList,
  parseBrandList,
  parseServiceTypeList,
  type ValidatedIssueType,
  type ValidatedServiceOption,
  type ValidatedBrand,
  type ValidatedServiceType,
} from "../domain/diagnostic-catalog-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

/** Category-scoped only (see contract-matrix.md) — no service/customer dimension exists on these endpoints. */
export const assistantQueryKeys = {
  issueTypes: (categoryId: string, locale: string, tenantId: string | undefined) =>
    ["assistant", "issue-types", categoryId, locale, tenantId ?? "no-tenant"] as const,
  serviceOptions: (categoryId: string, locale: string, tenantId: string | undefined) =>
    ["assistant", "service-options", categoryId, locale, tenantId ?? "no-tenant"] as const,
  brands: (categoryId: string, locale: string, tenantId: string | undefined) => ["assistant", "brands", categoryId, locale, tenantId ?? "no-tenant"] as const,
  serviceTypes: (categoryId: string, locale: string, tenantId: string | undefined) =>
    ["assistant", "service-types", categoryId, locale, tenantId ?? "no-tenant"] as const,
};

function useDiagnosticCatalog<T>(
  key: readonly unknown[],
  fetcher: (signal: AbortSignal | undefined) => Promise<unknown>,
  parser: (payload: unknown) => { items: T[]; droppedCount: number } | null,
  eventName: string,
  enabled: boolean
) {
  return useQuery<T[]>({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const response = await fetcher(signal);
      const parsed = parser(response);
      if (!parsed) {
        logger.warn(`${eventName}_validation_failed`, {});
        throw new ApiError({ category: "validation_error", message: `${eventName} response did not match the expected shape.` });
      }
      if (parsed.droppedCount > 0) {
        logger.warn(`${eventName}_items_dropped`, { droppedCount: parsed.droppedCount });
      }
      return parsed.items;
    },
    enabled,
    staleTime: 5 * 60_000,
  });
}

export function useIssueTypes(categoryId: string, enabled: boolean) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();
  return useDiagnosticCatalog<ValidatedIssueType>(
    assistantQueryKeys.issueTypes(categoryId, locale, tenantId),
    (signal) => diagnosticsApi.listIssueTypes(categoryId, { signal }),
    parseIssueTypeList,
    "issue_types",
    enabled
  );
}

export function useServiceOptions(categoryId: string, enabled: boolean) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();
  return useDiagnosticCatalog<ValidatedServiceOption>(
    assistantQueryKeys.serviceOptions(categoryId, locale, tenantId),
    (signal) => diagnosticsApi.listServiceOptions(categoryId, { signal }),
    parseServiceOptionList,
    "service_options",
    enabled
  );
}

export function useBrands(categoryId: string, enabled: boolean) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();
  return useDiagnosticCatalog<ValidatedBrand>(
    assistantQueryKeys.brands(categoryId, locale, tenantId),
    (signal) => diagnosticsApi.listBrands(categoryId, { signal }),
    parseBrandList,
    "brands",
    enabled
  );
}

export function useServiceTypes(categoryId: string, enabled: boolean) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();
  return useDiagnosticCatalog<ValidatedServiceType>(
    assistantQueryKeys.serviceTypes(categoryId, locale, tenantId),
    (signal) => diagnosticsApi.listServiceTypes(categoryId, { signal }),
    parseServiceTypeList,
    "service_types",
    enabled
  );
}
