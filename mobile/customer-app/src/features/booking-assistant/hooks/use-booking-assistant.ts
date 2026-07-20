import { useEffect, useState } from "react";
import { useIssueTypes, useServiceOptions, useBrands, useServiceTypes } from "../queries/assistant-queries";
import { createAssistantSession, type AssistantSessionState } from "../domain/assistant-session";
import type { StepGates } from "../domain/assistant-steps";

export interface RequiredFieldGates {
  requiresBrand: boolean;
  requiresType: boolean;
  requiresCustomerNotes: boolean;
  requiresPhotoUpload: boolean;
}

/**
 * Orchestrates the four category-scoped catalog queries and, once every
 * *needed* one has settled, creates the in-memory assistant session exactly
 * once. Brands/service-types are only fetched when the offering actually
 * requires them (CUSTOMER-L5-05 §59's request-budget concern) — issue types
 * and service options are always fetched since no offering-level flag
 * gates their presence (see contract-matrix.md).
 */
export function useBookingAssistant(serviceId: string, categoryId: string, requiredFields: RequiredFieldGates) {
  const issueTypes = useIssueTypes(categoryId, true);
  const serviceOptions = useServiceOptions(categoryId, true);
  const brands = useBrands(categoryId, requiredFields.requiresBrand);
  const serviceTypes = useServiceTypes(categoryId, requiredFields.requiresType);

  const catalogsLoading =
    issueTypes.isLoading ||
    serviceOptions.isLoading ||
    (requiredFields.requiresBrand && brands.isLoading) ||
    (requiredFields.requiresType && serviceTypes.isLoading);
  const catalogsError =
    issueTypes.isError || serviceOptions.isError || (requiredFields.requiresBrand && brands.isError) || (requiredFields.requiresType && serviceTypes.isError);

  const [session, setSession] = useState<AssistantSessionState | null>(null);

  useEffect(() => {
    if (catalogsLoading || catalogsError || session) return;

    const gates: StepGates = {
      hasIssueTypes: (issueTypes.data?.length ?? 0) > 0,
      hasServiceOptions: (serviceOptions.data?.length ?? 0) > 0,
      hasBrands: (brands.data?.length ?? 0) > 0,
      hasServiceTypes: (serviceTypes.data?.length ?? 0) > 0,
      requiresBrand: requiredFields.requiresBrand,
      requiresType: requiredFields.requiresType,
      requiresCustomerNotes: requiredFields.requiresCustomerNotes,
      requiresPhotoUpload: requiredFields.requiresPhotoUpload,
    };
    setSession(createAssistantSession(serviceId, categoryId, gates));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once catalogs settle; session creation itself must not re-run on later data refetches.
  }, [catalogsLoading, catalogsError, session]);

  function retry() {
    void issueTypes.refetch();
    void serviceOptions.refetch();
    if (requiredFields.requiresBrand) void brands.refetch();
    if (requiredFields.requiresType) void serviceTypes.refetch();
  }

  return { session, setSession, catalogsLoading, catalogsError, issueTypes, serviceOptions, brands, serviceTypes, retry };
}
