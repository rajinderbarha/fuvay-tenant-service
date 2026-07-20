import { environment } from "../config/environment";
import { appConfig } from "../config/app-config";
import { SUPPORTED_SCHEMA_VERSION, type RemoteConfigEnvelope } from "./remote-config-schema";

/**
 * Compiled, safe, system-only fallback. Used only when no valid cache and no
 * reachable remote config exist. Deliberately enables zero business modules
 * (fail-closed for feature enablement) — it exists purely so the app can
 * still boot to a system baseline screen rather than being permanently
 * unusable on first install with no network.
 */
export function buildCompiledDefaults(): RemoteConfigEnvelope {
  const now = new Date().toISOString();

  return {
    schemaVersion: SUPPORTED_SCHEMA_VERSION,
    configVersion: "compiled-default-0",
    generatedAt: now,
    environment: environment.name === "production" ? "production" : environment.name === "staging" ? "staging" : "development",
    marketplace: {
      marketplaceId: "default",
      displayName: appConfig.appName,
      active: true,
      defaultLocale: appConfig.defaultLocale,
      supportedLocales: appConfig.supportedLocales.map((locale) => locale.code),
      defaultCurrency: "INR",
      timezone: "Asia/Kolkata",
      country: "IN",
      customerAppEnabled: true,
    },
    application: {
      customerAppEnabled: true,
      developmentToolsEnabled: __DEV__,
      analyticsEnabled: false,
      crashReportingEnabled: false,
      remoteImagesEnabled: true,
      deepLinksEnabled: true,
      notificationRoutingEnabled: false,
      refreshIntervalSeconds: 900,
      maxConfigAgeSeconds: 86400,
      cachedConfigFallbackAllowed: true,
    },
    versionPolicy: {
      // Permissive on purpose: compiled defaults must never mandatorily block
      // the app when the real policy is unreachable. Must sort below any
      // prerelease-tagged dev build (e.g. "0.0.0-dev") under semver
      // precedence rules, or a dev build would compare as older than this
      // floor and get mandatorily blocked by its own fallback config.
      minSupportedVersion: "0.0.0-0",
      latestRecommendedVersion: environment.buildVersion,
      mandatoryUpdate: false,
      optionalUpdate: false,
      updateTitle: "Update available",
      updateMessage: "A newer version of the app is available.",
      gracePeriodHours: 0,
      blockedBuildNumbers: [],
    },
    maintenance: {
      enabled: false,
      type: "none",
      retryAllowed: true,
      permittedRouteIds: [],
    },
    modules: [],
    navigation: {
      allowedRouteIds: [],
      disabledRouteIds: [],
      deepLinkAllowlist: [],
      notificationRouteAllowlist: [],
      fallbackRouteId: "baselineLanding",
    },
  };
}
