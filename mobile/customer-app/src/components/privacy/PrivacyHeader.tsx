import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

export interface PrivacyHeaderProps {
  onBack: () => void;
}

export function PrivacyHeader({ onBack }: PrivacyHeaderProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" accessibilityRole="header">Privacy & data</AppText>
        <AppText variant="bodySmall" color="secondary">Manage your information and privacy requests</AppText>
      </View>
    </View>
  );
}
