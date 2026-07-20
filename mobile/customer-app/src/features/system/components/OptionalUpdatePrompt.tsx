import React, { useEffect, useState } from "react";
import { View, Linking, Platform } from "react-native";
import { useTranslation } from "react-i18next";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { preferenceStorage } from "../../../storage/preference-storage";
import { PREFERENCE_STORAGE_KEYS } from "../../../storage/storage-keys";
import { evaluateVersionPolicy, type VersionPolicyResult } from "../../../remote-config/version-policy";
import type { VersionPolicyConfig } from "../../../remote-config/remote-config-schema";
import { environment } from "../../../config/environment";

export interface OptionalUpdatePromptProps {
  policy: VersionPolicyConfig;
}

/**
 * Non-blocking banner. Dismissal is persisted keyed by the *recommended*
 * version string, so it reappears automatically once the policy recommends
 * a newer version (a config revision), without needing an extra "revision"
 * concept of its own.
 */
export function OptionalUpdatePrompt({ policy }: OptionalUpdatePromptProps) {
  const { theme } = useAppTheme();
  const { t } = useTranslation("startup");
  const [dismissedVersion, setDismissedVersion] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    preferenceStorage.getItem<string>(PREFERENCE_STORAGE_KEYS.optionalUpdateDismissedVersion).then((value) => {
      if (cancelled) return;
      setDismissedVersion(value);
      setHydrated(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!hydrated) return null;

  const result: VersionPolicyResult = evaluateVersionPolicy({
    currentVersion: environment.buildVersion,
    currentBuildNumber: environment.buildNumber,
    platform: Platform.OS === "ios" ? "ios" : "android",
    policy,
  });

  const shouldShow =
    (result.outcome === "supported-update-available" || result.outcome === "supported-update-recommended") &&
    dismissedVersion !== policy.latestRecommendedVersion;

  if (!shouldShow) return null;

  async function handleUpdate() {
    if (!result.storeUrl) return;
    try {
      await Linking.openURL(result.storeUrl);
    } catch {
      // Store-open failure is non-fatal for an optional prompt — silently ignored, user can dismiss.
    }
  }

  function handleLater() {
    void preferenceStorage.setItem(PREFERENCE_STORAGE_KEYS.optionalUpdateDismissedVersion, policy.latestRecommendedVersion);
    setDismissedVersion(policy.latestRecommendedVersion);
  }

  return (
    <View
      accessibilityRole="alert"
      style={{
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        gap: theme.spacing[4],
        backgroundColor: theme.colors.statusInfoBackground,
        paddingHorizontal: theme.spacing[6],
        paddingVertical: theme.spacing[4],
      }}
    >
      <AppText variant="labelMedium" style={{ color: theme.colors.statusInfoForeground, flex: 1 }}>
        {policy.updateMessage || t("updateAvailableMessage")}
      </AppText>
      <AppButton label={t("updateNow")} onPress={handleUpdate} variant="text" size="small" />
      <AppButton label={t("later")} onPress={handleLater} variant="text" size="small" />
    </View>
  );
}
