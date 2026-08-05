import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

export interface SecurityHeaderProps {
  onBack: () => void;
}

export function SecurityHeader({ onBack }: SecurityHeaderProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" accessibilityRole="header">Security</AppText>
        <AppText variant="bodySmall" color="secondary">Manage how you sign in and protect your account</AppText>
      </View>
    </View>
  );
}
