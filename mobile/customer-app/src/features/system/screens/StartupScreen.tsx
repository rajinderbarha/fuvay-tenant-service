import React, { useEffect, useRef } from "react";
import { View, AccessibilityInfo } from "react-native";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { AppText } from "../../../components/primitives/AppText";
import { LoadingIndicator } from "../../../components/feedback/LoadingIndicator";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";

/**
 * In-app startup screen — shown after the native splash hides but before
 * startup finishes. Never displays raw phase names (e.g.
 * "evaluating-maintenance-policy") to the customer; announces the loading
 * state exactly once rather than on every phase transition.
 */
export function StartupScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("startup");
  const announced = useRef(false);

  useEffect(() => {
    if (announced.current) return;
    announced.current = true;
    AccessibilityInfo.announceForAccessibility?.(t("loadingApplication"));
  }, [t]);

  return (
    <ScreenContainer scrollable={false} background="primary">
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: theme.spacing[6] }}>
        <AppText variant="displayMedium" align="center">
          ServiceOS
        </AppText>
        <LoadingIndicator variant="inline" label={t("loadingApplication")} />
        <AppText variant="bodyMedium" color="textSecondary" align="center">
          {t("loadingApplication")}
        </AppText>
      </View>
    </ScreenContainer>
  );
}
