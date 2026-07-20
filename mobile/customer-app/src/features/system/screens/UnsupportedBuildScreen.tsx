import React from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { AppText } from "../../../components/primitives/AppText";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";

/**
 * Used for invalid build metadata, a blocked build, an incompatible remote
 * schema version, or an unsupported OS policy — distinct from
 * MandatoryUpdateScreen, which is for "you can fix this by updating".
 * There is deliberately no update/retry action here — the build itself is
 * the problem, not the version policy.
 */
export function UnsupportedBuildScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("startup");

  return (
    <ScreenContainer scrollable={false}>
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: theme.spacing[5], paddingHorizontal: theme.spacing[7] }}>
        <AppIcon name="close-circle" size="xl" color="iconDanger" />
        <AppText variant="headingLarge" align="center" accessibilityRole="header">
          {t("unsupportedVersionTitle")}
        </AppText>
        <AppText variant="bodyMedium" color="textSecondary" align="center">
          {t("unsupportedVersionMessage")}
        </AppText>
      </View>
    </ScreenContainer>
  );
}
