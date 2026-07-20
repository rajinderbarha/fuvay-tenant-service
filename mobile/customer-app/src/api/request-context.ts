import { appConfig } from "../config/app-config";
import { environment } from "../config/environment";

let currentLocale: string = appConfig.defaultLocale;
let currentTenantId: string | undefined;
let authTokenProvider: (() => Promise<string | null>) | null = null;
let unauthorizedHandler: (() => Promise<boolean>) | null = null;

export function setRequestLocale(locale: string): void {
  currentLocale = locale;
}

export function getRequestLocale(): string {
  return currentLocale;
}

export function setRequestTenantId(tenantId: string | undefined): void {
  currentTenantId = tenantId;
}

export function getRequestTenantId(): string | undefined {
  return currentTenantId;
}

/** Registered by the (future) auth feature; keeps the API client decoupled from auth storage. */
export function setAuthTokenProvider(provider: (() => Promise<string | null>) | null): void {
  authTokenProvider = provider;
}

function newRequestId(): string {
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

export async function buildRequestHeaders(extra?: Record<string, string>): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Request-Id": newRequestId(),
    "X-Request-Source": "customer-mobile-app",
    "X-App-Version": environment.buildVersion,
    "X-Platform": "react-native",
    "Accept-Language": currentLocale,
    ...extra,
  };
  if (currentTenantId) headers["X-Tenant-Id"] = currentTenantId;
  return headers;
}

export async function resolveAuthToken(): Promise<string | null> {
  if (!authTokenProvider) return null;
  return authTokenProvider();
}

/**
 * Registered by the auth feature's refresh coordinator. Called by
 * api-client.ts exactly once per failing request when a response comes
 * back `unauthorized` — must resolve `true` only if a fresh access token
 * is now available and the caller should retry, `false` otherwise. Kept
 * decoupled from api-client.ts's own internals so there is still only one
 * HTTP client and one place that knows how to refresh a session.
 */
export function setUnauthorizedHandler(handler: (() => Promise<boolean>) | null): void {
  unauthorizedHandler = handler;
}

export async function handleUnauthorized(): Promise<boolean> {
  if (!unauthorizedHandler) return false;
  return unauthorizedHandler();
}
