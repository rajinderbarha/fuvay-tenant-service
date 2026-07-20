import { z } from "zod";

/**
 * The only schema version this build understands. Bump when the envelope
 * shape changes in a breaking way; a config with a different value is
 * rejected before field-level validation runs (see remote-config-client.ts).
 */
export const SUPPORTED_SCHEMA_VERSION = 1;

const semverPattern = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const routeIdPattern = /^[a-z][a-zA-Z0-9]*$/;
const moduleKeyPattern = /^[a-z][a-z0-9-]*$/;

const httpsUrl = z
  .string()
  .url()
  .refine((value) => value.startsWith("https://"), { message: "Only https:// URLs are permitted." });

const isoDateTime = z.string().datetime({ offset: true });

export const supportedLocaleSchema = z.enum(["en", "hi", "pa"]);

export const marketplaceConfigSchema = z.object({
  marketplaceId: z.string().min(1),
  tenantId: z.string().min(1).optional(),
  tenantSlug: z.string().min(1).optional(),
  displayName: z.string().min(1),
  active: z.boolean(),
  defaultLocale: supportedLocaleSchema,
  supportedLocales: z.array(supportedLocaleSchema).min(1),
  defaultCurrency: z.string().length(3),
  timezone: z.string().min(1),
  country: z.string().length(2),
  customerAppEnabled: z.boolean(),
});

export const applicationConfigSchema = z.object({
  customerAppEnabled: z.boolean(),
  developmentToolsEnabled: z.boolean(),
  analyticsEnabled: z.boolean(),
  crashReportingEnabled: z.boolean(),
  remoteImagesEnabled: z.boolean(),
  deepLinksEnabled: z.boolean(),
  notificationRoutingEnabled: z.boolean(),
  refreshIntervalSeconds: z.number().int().positive(),
  maxConfigAgeSeconds: z.number().int().positive(),
  cachedConfigFallbackAllowed: z.boolean(),
});

export const versionPolicySchema = z.object({
  minSupportedVersion: z.string().regex(semverPattern),
  latestRecommendedVersion: z.string().regex(semverPattern),
  mandatoryUpdate: z.boolean(),
  optionalUpdate: z.boolean(),
  updateTitle: z.string().min(1),
  updateMessage: z.string().min(1),
  storeUrlIOS: httpsUrl.optional(),
  storeUrlAndroid: httpsUrl.optional(),
  gracePeriodHours: z.number().int().nonnegative().default(0),
  blockedBuildNumbers: z.array(z.string().min(1)).default([]),
});

export const maintenanceConfigSchema = z
  .object({
    enabled: z.boolean(),
    type: z.enum(["none", "scheduled", "active-blocking", "active-read-only"]),
    title: z.string().optional(),
    message: z.string().optional(),
    startAt: isoDateTime.optional(),
    estimatedEndAt: isoDateTime.optional(),
    retryAllowed: z.boolean().default(true),
    retryIntervalSeconds: z.number().int().positive().optional(),
    statusPageUrl: httpsUrl.optional(),
    permittedRouteIds: z.array(z.string().regex(routeIdPattern)).default([]),
  })
  .superRefine((maintenance, ctx) => {
    if (maintenance.startAt && maintenance.estimatedEndAt) {
      if (new Date(maintenance.estimatedEndAt).getTime() <= new Date(maintenance.startAt).getTime()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "estimatedEndAt must be after startAt.", path: ["estimatedEndAt"] });
      }
    }
    if (maintenance.enabled && maintenance.type === "none") {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "enabled maintenance must not use type 'none'.", path: ["type"] });
    }
  });

export const moduleConfigSchema = z.object({
  key: z.string().regex(moduleKeyPattern),
  displayNameKey: z.string().min(1),
  enabled: z.boolean(),
  visible: z.boolean(),
  minAppVersion: z.string().regex(semverPattern).optional(),
  requiresAuth: z.boolean().default(false),
  supportedRegions: z.array(z.string().length(2)).optional(),
  dependsOn: z.array(z.string().regex(moduleKeyPattern)).default([]),
  routeId: z.string().regex(routeIdPattern).optional(),
  order: z.number().int().default(0),
  disableReasonKey: z.string().optional(),
});

export const navigationConfigSchema = z.object({
  initialRouteOverride: z.string().regex(routeIdPattern).optional(),
  allowedRouteIds: z.array(z.string().regex(routeIdPattern)).default([]),
  disabledRouteIds: z.array(z.string().regex(routeIdPattern)).default([]),
  deepLinkAllowlist: z.array(z.string().regex(routeIdPattern)).default([]),
  notificationRouteAllowlist: z.array(z.string().regex(routeIdPattern)).default([]),
  fallbackRouteId: z.string().regex(routeIdPattern),
});

export const remoteConfigEnvelopeSchema = z
  .object({
    schemaVersion: z.literal(SUPPORTED_SCHEMA_VERSION),
    configVersion: z.string().min(1),
    generatedAt: isoDateTime,
    expiresAt: isoDateTime.optional(),
    environment: z.enum(["development", "staging", "production"]),
    marketplace: marketplaceConfigSchema,
    application: applicationConfigSchema,
    versionPolicy: versionPolicySchema,
    maintenance: maintenanceConfigSchema,
    modules: z.array(moduleConfigSchema),
    navigation: navigationConfigSchema,
  })
  .superRefine((envelope, ctx) => {
    if (envelope.expiresAt && new Date(envelope.expiresAt).getTime() <= new Date(envelope.generatedAt).getTime()) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "expiresAt must be after generatedAt.", path: ["expiresAt"] });
    }

    const seenKeys = new Set<string>();
    for (const [index, module] of envelope.modules.entries()) {
      if (seenKeys.has(module.key)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: `Duplicate module key "${module.key}".`, path: ["modules", index, "key"] });
      }
      seenKeys.add(module.key);
    }

    for (const [index, module] of envelope.modules.entries()) {
      for (const dep of module.dependsOn) {
        if (!envelope.modules.some((candidate) => candidate.key === dep)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Module "${module.key}" depends on unknown module "${dep}".`,
            path: ["modules", index, "dependsOn"],
          });
        }
      }
    }

    if (hasCyclicModuleDependency(envelope.modules)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Module dependency graph contains a cycle.", path: ["modules"] });
    }

    if (!envelope.navigation.allowedRouteIds.includes(envelope.navigation.fallbackRouteId) && envelope.navigation.allowedRouteIds.length > 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "fallbackRouteId must be included in allowedRouteIds when allowedRouteIds is non-empty.",
        path: ["navigation", "fallbackRouteId"],
      });
    }

    if (
      envelope.navigation.initialRouteOverride &&
      envelope.navigation.allowedRouteIds.length > 0 &&
      !envelope.navigation.allowedRouteIds.includes(envelope.navigation.initialRouteOverride)
    ) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "initialRouteOverride must be an allowed route.", path: ["navigation", "initialRouteOverride"] });
    }

    for (const [index, module] of envelope.modules.entries()) {
      if (module.routeId && envelope.navigation.disabledRouteIds.includes(module.routeId) && module.enabled) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Module "${module.key}" is enabled but its route is in disabledRouteIds.`,
          path: ["modules", index, "enabled"],
        });
      }
    }
  });

function hasCyclicModuleDependency(modules: { key: string; dependsOn: string[] }[]): boolean {
  const graph = new Map(modules.map((module) => [module.key, module.dependsOn]));
  const visiting = new Set<string>();
  const visited = new Set<string>();

  function visit(key: string): boolean {
    if (visited.has(key)) return false;
    if (visiting.has(key)) return true;
    visiting.add(key);
    for (const dep of graph.get(key) ?? []) {
      if (visit(dep)) return true;
    }
    visiting.delete(key);
    visited.add(key);
    return false;
  }

  return [...graph.keys()].some((key) => visit(key));
}

export type MarketplaceConfig = z.infer<typeof marketplaceConfigSchema>;
export type ApplicationConfig = z.infer<typeof applicationConfigSchema>;
export type VersionPolicyConfig = z.infer<typeof versionPolicySchema>;
export type MaintenanceConfig = z.infer<typeof maintenanceConfigSchema>;
export type ModuleConfig = z.infer<typeof moduleConfigSchema>;
export type NavigationConfig = z.infer<typeof navigationConfigSchema>;
export type RemoteConfigEnvelope = z.infer<typeof remoteConfigEnvelopeSchema>;
