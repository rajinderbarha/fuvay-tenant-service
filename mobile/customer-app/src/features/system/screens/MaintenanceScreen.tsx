import React, { useEffect, useRef } from "react";
import { View, findNodeHandle, AccessibilityInfo, Linking } from "react-native";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useStartup } from "../../../app/startup/use-startup";
import { formatDate, formatTime } from "../../../localization/formatters";
import type { SupportedLocale } from "../../../config/app-config";

export function MaintenanceScreen() {
  const { theme } = useAppTheme();
  const { t, i18n } = useTranslation("startup");
  const { snapshot, retry } = useStartup();
  const headingRef = useRef<View>(null);
  const maintenance = snapshot.resolvedConfig?.config.maintenance;
  const locale = i18n.language as SupportedLocale;

  useEffect(() => {
    const handle = headingRef.current && findNodeHandle(headingRef.current);
    if (handle) AccessibilityInfo.setAccessibilityFocus(handle);
  }, []);

  return (
    <ScreenContainer scrollable={false}>
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: theme.spacing[5], paddingHorizontal: theme.spacing[7] }}>
        <AppIcon name="information-circle" size="xl" color="iconWarning" />
        <View ref={headingRef} accessible accessibilityRole="header">
          <AppText variant="headingLarge" align="center">
            {maintenance?.title || t("maintenanceTitle")}
          </AppText>
        </View>
        <AppText variant="bodyMedium" color="textSecondary" align="center">
          {maintenance?.message || t("maintenanceMessage")}
        </AppText>
        {maintenance?.estimatedEndAt ? (
          <AppText variant="labelMedium" color="textTertiary" align="center">
            {formatDate(new Date(maintenance.estimatedEndAt), locale)} · {formatTime(new Date(maintenance.estimatedEndAt), locale)}
          </AppText>
        ) : null}
        <AppText variant="caption" color="textTertiary" align="center">
          {t("maintenanceRetryHint")}
        </AppText>
        {maintenance?.retryAllowed !== false ? <AppButton label={t("retry")} onPress={retry} variant="primary" size="medium" /> : null}
        {maintenance?.statusPageUrl ? (
          <AppButton label={t("support")} onPress={() => void Linking.openURL(maintenance.statusPageUrl!)} variant="text" size="medium" />
        ) : null}
      </View>
    </ScreenContainer>
  );
}
