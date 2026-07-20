import React from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";

export interface InformationRendererProps {
  title: string;
  body: string;
  required: boolean;
  onContinue: () => void;
}

/** No answer is collected — only acknowledgement (CUSTOMER-L5-05 §23/§27's media-request boundary). */
export function InformationRenderer({ title, body, required, onContinue }: InformationRendererProps) {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");

  return (
    <View style={{ gap: theme.spacing[4] }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
        <AppIcon name="information-circle" size="lg" color="iconPrimary" />
        <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
          {title}
        </AppText>
      </View>
      <AppText variant="bodyMedium" color="textSecondary">
        {body}
      </AppText>
      {required ? (
        <AppText variant="caption" color="textTertiary">
          {t("assistant.mediaRequiredNote")}
        </AppText>
      ) : null}
      <AppButton label={t("assistant.continue")} onPress={onContinue} variant="primary" size="large" testID="information-continue" />
    </View>
  );
}
