import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppInput } from "../AppInput";

export interface BasicInformationFormProps {
  fullName: string;
  onChangeFullName: (value: string) => void;
  error: string | null;
}

export function BasicInformationForm({ fullName, onChangeFullName, error }: BasicInformationFormProps) {
  const { theme } = useTheme();
  return (
    <AppCard style={{ gap: theme.spacing.xs }}>
      <AppText variant="bodyStrong">Basic information</AppText>
      <AppInput
        label="Full name"
        value={fullName}
        onChangeText={onChangeFullName}
        accessibilityLabel="Full name"
        error={error ?? undefined}
        autoComplete="name"
        textContentType="name"
        returnKeyType="done"
        maxLength={255}
      />
      {!error ? <AppText variant="caption" color="tertiary">Use the name you want shown in the app.</AppText> : null}
    </AppCard>
  );
}
