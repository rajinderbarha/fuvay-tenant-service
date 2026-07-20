import React from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { AppText } from "../../../components/primitives/AppText";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";

/**
 * Used for: customer app disabled, marketplace disabled, tenant suspended,
 * region unsupported, or no valid configuration at all — a policy state,
 * not a transient failure, so there is no retry action.
 */
export function AppUnavailableScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("startup");

  return (
    <ScreenContainer scrollable={false}>
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: theme.spacing[5], paddingHorizontal: theme.spacing[7] }}>
        <AppIcon name="information-circle" size="xl" color="iconSecondary" />
        <AppText variant="headingLarge" align="center" accessibilityRole="header">
          {t("applicationUnavailableTitle")}
        </AppText>
        <AppText variant="bodyMedium" color="textSecondary" align="center">
          {t("applicationUnavailableMessage")}
        </AppText>
      </View>
    </ScreenContainer>
  );
}
