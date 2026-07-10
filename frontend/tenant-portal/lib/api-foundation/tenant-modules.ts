/**
 * FRONTEND-CONNECT-01 — Tenant API module stubs (tenant-portal).
 *
 * Thin named wrappers requested by the spec, wired to REAL existing
 * endpoints/methods already in ../api.ts (myStatusApi, providerStatusApi,
 * providerServiceAreasApi, homeServicesSetupApi, providerAvailabilityApi,
 * usageCreditsApi, jobsApi — verified against actual signatures below).
 * All go through apiFetch/getTenantId() internally — tenant context is
 * already injected by those existing functions.
 */
import {
  myStatusApi, providerServiceAreasApi, homeServicesSetupApi,
  providerAvailabilityApi, usageCreditsApi, jobsApi,
  type ProviderAvailabilityPayload,
} from "../api";
import { requireTenantContext } from "./tenant-context";

export const getTenantSetupChecklist = () => myStatusApi.getStatus();

export const getTenantBusinessProfile = () => myStatusApi.getStatus();

export const getTenantServiceAreas = () => {
  requireTenantContext();
  return providerServiceAreasApi.list();
};

export const getTenantServicesSetup = () => {
  requireTenantContext();
  return homeServicesSetupApi.listEnabled();
};

export const getTenantServiceCoverage = (tenantServiceId: string) =>
  homeServicesSetupApi.getTypes(tenantServiceId);

export const getTenantAvailability = () => {
  requireTenantContext();
  return providerAvailabilityApi.list();
};

export const getTenantJobs = (params?: Partial<{ status: string; limit: string; cursor: string; date: string }>) => {
  requireTenantContext();
  return jobsApi.list(params);
};

export const getTenantJobDetail = (jobId: string) => jobsApi.get(jobId);

export const getTenantUsageCreditBalance = () => usageCreditsApi.getBalance();

export const getTenantUsageCreditLedger = () => usageCreditsApi.getLedger();

// ── Mutation stubs ────────────────────────────────────────────────────────
export const saveTenantServiceSetup = (tenantServiceId: string) =>
  homeServicesSetupApi.saveDraft(tenantServiceId);

export const publishTenantServices = (tenantServiceId: string) =>
  homeServicesSetupApi.publish(tenantServiceId);

export const saveTenantServiceCoverage = (tenantServiceId: string, typeIds: string[]) =>
  homeServicesSetupApi.setTypes(tenantServiceId, typeIds);

export const publishTenantServiceCoverage = (tenantServiceId: string) =>
  homeServicesSetupApi.publish(tenantServiceId);

export const saveTenantAvailability = (payload: ProviderAvailabilityPayload) => {
  requireTenantContext();
  return providerAvailabilityApi.create(payload);
};

export const assignTechnician = (jobId: string, staffId: string) => {
  requireTenantContext();
  return jobsApi.assignStaff(jobId, staffId);
};
