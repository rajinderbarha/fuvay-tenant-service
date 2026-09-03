import { Platform } from "react-native";
import { ENV } from "../../config/environment";

export interface CustomerPublicAppConfig {
  minimumSupportedVersion: string;
  storeUrl: string | null;
  maintenance: boolean;
  enabledVerticals: string[];
}

let latestStoreUrl: string | null = null;

export function getCustomerStoreUrl(): string | null { return latestStoreUrl; }

export async function loadCustomerPublicAppConfig(): Promise<CustomerPublicAppConfig> {
  const response = await fetch(`${ENV.apiBaseUrl}/v1/public/app-config/customer`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`App configuration failed (${response.status})`);
  const body = await response.json() as { data?: Record<string, unknown> };
  const data = body.data ?? {};
  const storeUrl = Platform.OS === "ios"
    ? (typeof data.ios_store_url === "string" ? data.ios_store_url : null)
    : (typeof data.android_store_url === "string" ? data.android_store_url : null);
  latestStoreUrl = storeUrl;
  return {
    minimumSupportedVersion: typeof data.minimum_supported_version === "string" ? data.minimum_supported_version : "1.0.0",
    storeUrl,
    maintenance: data.maintenance === true,
    enabledVerticals: Array.isArray(data.enabled_verticals) ? data.enabled_verticals.filter((v): v is string => typeof v === "string") : ["home_services"],
  };
}

export function isVersionBelow(current: string, minimum: string): boolean {
  const parts = (value: string) => value.split(".").map(x => Number.parseInt(x, 10) || 0);
  const a = parts(current); const b = parts(minimum);
  for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
    if ((a[i] ?? 0) < (b[i] ?? 0)) return true;
    if ((a[i] ?? 0) > (b[i] ?? 0)) return false;
  }
  return false;
}
