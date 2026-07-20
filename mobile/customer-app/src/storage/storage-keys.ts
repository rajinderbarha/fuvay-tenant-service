/**
 * Versioned, typed storage keys. Bump the version suffix when the shape of a
 * stored value changes in a way that requires migration/reset.
 */
export const PREFERENCE_STORAGE_KEYS = {
  themePreference: "serviceos.pref.themePreference.v1",
  localePreference: "serviceos.pref.localePreference.v1",
  onboardingComplete: "serviceos.pref.onboardingComplete.v1",
  devToolsEnabled: "serviceos.pref.devToolsEnabled.v1",
  remoteConfigCache: "serviceos.pref.remoteConfigCache.v1",
  optionalUpdateDismissedVersion: "serviceos.pref.optionalUpdateDismissedVersion.v1",
} as const;

export const SECURE_STORAGE_KEYS = {
  accessToken: "serviceos.secure.accessToken.v1",
  refreshToken: "serviceos.secure.refreshToken.v1",
  deviceBindingId: "serviceos.secure.deviceBindingId.v1",
} as const;

export type PreferenceStorageKey = (typeof PREFERENCE_STORAGE_KEYS)[keyof typeof PREFERENCE_STORAGE_KEYS];
export type SecureStorageKey = (typeof SECURE_STORAGE_KEYS)[keyof typeof SECURE_STORAGE_KEYS];
