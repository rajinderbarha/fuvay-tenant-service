import React from "react";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { useStartup } from "../../../app/startup/use-startup";

export interface StartupErrorScreenProps {
  onContactSupport?: () => void;
}

export function StartupErrorScreen({ onContactSupport }: StartupErrorScreenProps) {
  const { t } = useTranslation("startup");
  const { snapshot, retry } = useStartup();

  return (
    <ScreenContainer scrollable={false}>
      <ErrorState
        mode="recoverable"
        title={t("startupErrorTitle")}
        description={t("startupErrorMessage")}
        errorReferenceId={snapshot.error?.errorReferenceId}
        onRetry={retry}
        onContactSupport={onContactSupport}
      />
    </ScreenContainer>
  );
}
