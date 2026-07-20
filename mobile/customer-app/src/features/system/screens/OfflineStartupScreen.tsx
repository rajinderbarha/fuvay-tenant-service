import React from "react";
import { Linking } from "react-native";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { AppButton } from "../../../components/primitives/AppButton";
import { useStartup } from "../../../app/startup/use-startup";

export function OfflineStartupScreen() {
  const { t } = useTranslation("startup");
  const { retry } = useStartup();

  return (
    <ScreenContainer scrollable={false}>
      <ErrorState mode="offline" title={t("offlineTitle")} description={t("offlineMessage")} onRetry={retry} />
      <AppButton label={t("openNetworkSettings")} variant="text" size="medium" onPress={() => void Linking.openSettings()} />
    </ScreenContainer>
  );
}
