import { sizes } from "../design-system/tokens/sizes";

export type SupportedLocale = "en" | "hi" | "pa";

export interface LocaleDefinition {
  code: SupportedLocale;
  label: string;
  isRTL: boolean;
}

export const SUPPORTED_LOCALES: LocaleDefinition[] = [
  { code: "en", label: "English", isRTL: false },
  { code: "hi", label: "हिंदी", isRTL: false },
  { code: "pa", label: "ਪੰਜਾਬੀ", isRTL: false },
];

export interface SupportContactConfig {
  helpCenterRouteId: string;
  supportTicketRouteId: string;
}

export interface LegalRouteIds {
  termsOfService: string;
  privacyPolicy: string;
}

export interface AppConfig {
  appName: string;
  defaultLocale: SupportedLocale;
  supportedLocales: LocaleDefinition[];
  defaultThemePreference: "light" | "dark" | "system";
  requestTimeoutDefaultMs: number;
  pagination: { defaultPageSize: number; maxPageSize: number };
  media: { maxImageSizeBytes: number; supportedImageMimeTypes: string[] };
  supportContact: SupportContactConfig;
  legalRoutes: LegalRouteIds;
  remoteConfigDefaults: Record<string, boolean>;
  featureModuleDefaults: Record<string, boolean>;
  minTouchTargetSize: number;
  maxReadableContentWidth: number;
  devToolsEnabledByDefault: boolean;
}

export const appConfig: AppConfig = {
  appName: "ServiceOS",
  defaultLocale: "en",
  supportedLocales: SUPPORTED_LOCALES,
  defaultThemePreference: "system",
  requestTimeoutDefaultMs: 15000,
  pagination: { defaultPageSize: 20, maxPageSize: 100 },
  media: {
    maxImageSizeBytes: 10 * 1024 * 1024,
    supportedImageMimeTypes: ["image/jpeg", "image/png", "image/webp"],
  },
  // Route identifiers only — actual URLs/phone numbers are backend-config-driven
  // (feature-config endpoint, later sprint) and must not be hardcoded here.
  supportContact: {
    helpCenterRouteId: "support.helpCenter",
    supportTicketRouteId: "support.newTicket",
  },
  legalRoutes: {
    termsOfService: "legal.termsOfService",
    privacyPolicy: "legal.privacyPolicy",
  },
  remoteConfigDefaults: {},
  featureModuleDefaults: {
    bookingAssistant: false,
    bargain: false,
    rewards: false,
  },
  minTouchTargetSize: sizes.touchTargetMin,
  maxReadableContentWidth: sizes.maxContentWidth,
  devToolsEnabledByDefault: __DEV__,
};
