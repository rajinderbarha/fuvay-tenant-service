import React from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppText } from "../../../components/primitives/AppText";
import { AppCheckbox } from "../../../components/forms/AppCheckbox";
import { AppButton } from "../../../components/primitives/AppButton";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";

export interface MultiSelectOption {
  id: string;
  label: string;
}

export interface MultiSelectRendererProps {
  title: string;
  options: MultiSelectOption[];
  selectedIds: string[];
  onToggle: (optionId: string) => void;
  onContinue: () => void;
}

/** Explicit "Continue" action (unlike single-select) since multiple choices need an apply step — CUSTOMER-L5-05 §19. */
export function MultiSelectRenderer({ title, options, selectedIds, onToggle, onContinue }: MultiSelectRendererProps) {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");

  return (
    <View style={{ gap: theme.spacing[4] }}>
      <AppText variant="headingLarge" accessibilityRole="header">
        {title}
      </AppText>
      <View style={{ gap: theme.spacing[3] }}>
        {options.map((option) => (
          <AppCheckbox key={option.id} checked={selectedIds.includes(option.id)} onChange={() => onToggle(option.id)} label={option.label} />
        ))}
      </View>
      <AppButton label={t("assistant.continue")} onPress={onContinue} variant="primary" size="large" testID="multi-select-continue" />
    </View>
  );
}
