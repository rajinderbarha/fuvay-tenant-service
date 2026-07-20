import React, { useState } from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppText } from "../../../components/primitives/AppText";
import { AppTextArea } from "../../../components/forms/AppTextArea";
import { AppButton } from "../../../components/primitives/AppButton";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";

const MAX_LENGTH = 500;

export interface ShortTextRendererProps {
  title: string;
  helperText?: string;
  initialValue?: string;
  required?: boolean;
  onSubmit: (text: string) => void;
}

export function ShortTextRenderer({ title, helperText, initialValue = "", required = false, onSubmit }: ShortTextRendererProps) {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const [value, setValue] = useState(initialValue);
  const canContinue = !required || value.trim().length > 0;

  return (
    <View style={{ gap: theme.spacing[4] }}>
      <AppText variant="headingLarge" accessibilityRole="header">
        {title}
      </AppText>
      <AppTextArea
        label={helperText ?? title}
        value={value}
        onChangeText={setValue}
        maxLength={MAX_LENGTH}
        showCharacterCount
        required={required}
        testID="short-text-input"
      />
      <AppButton
        label={t("assistant.continue")}
        onPress={() => onSubmit(value)}
        variant="primary"
        size="large"
        disabled={!canContinue}
        testID="short-text-continue"
      />
    </View>
  );
}
