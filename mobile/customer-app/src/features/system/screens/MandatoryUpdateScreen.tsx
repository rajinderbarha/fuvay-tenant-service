import React, { useEffect } from "react";
import { View, BackHandler, Linking, Platform } from "react-native";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useStartup } from "../../../app/startup/use-startup";
import { toastService } from "../../../components/feedback/toast-service";
import { environment } from "../../../config/environment";

/**
 * Blocks app access: the hardware back button is swallowed (never exits the
 * screen), and there is intentionally no dismiss button — reaching this
 * screen already means the version policy evaluated to "mandatory". App
 * resume/retry re-runs startup (see StartupProvider), which re-evaluates the
 * policy — the screen is never marked "handled" just because the store opened.
 */
export function MandatoryUpdateScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("startup");
  const { snapshot, retry } = useStartup();
  const versionPolicy = snapshot.resolvedConfig?.config.versionPolicy;
  const storeUrl = Platform.OS === "ios" ? versionPolicy?.storeUrlIOS : versionPolicy?.storeUrlAndroid;

  useEffect(() => {
    const subscription = BackHandler.addEventListener("hardwareBackPress", () => true);
    return () => subscription.remove();
  }, []);

  async function handleUpdatePress() {
    if (!storeUrl) {
      toastService.error(t("storeUnavailable"));
      return;
    }
    try {
      await Linking.openURL(storeUrl);
    } catch {
      toastService.error(t("storeUnavailable"));
    }
  }

  return (
    <ScreenContainer scrollable={false}>
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: theme.spacing[5], paddingHorizontal: theme.spacing[7] }}>
        <AppIcon name="alert-circle" size="xl" color="iconWarning" />
        <AppText variant="headingLarge" align="center" accessibilityRole="header">
          {versionPolicy?.updateTitle || t("updateRequiredTitle")}
        </AppText>
        <AppText variant="bodyMedium" color="textSecondary" align="center">
          {versionPolicy?.updateMessage || t("updateRequiredMessage")}
        </AppText>
        <AppText variant="caption" color="textTertiary" align="center">
          {t("currentVersion")}: {environment.buildVersion}
          {versionPolicy?.minSupportedVersion ? `  ·  ${t("requiredVersion")}: ${versionPolicy.minSupportedVersion}` : ""}
        </AppText>
        <AppButton label={t("updateNow")} onPress={handleUpdatePress} variant="primary" size="large" />
        <AppButton label={t("configurationRetry")} onPress={retry} variant="text" size="medium" />
      </View>
    </ScreenContainer>
  );
}
