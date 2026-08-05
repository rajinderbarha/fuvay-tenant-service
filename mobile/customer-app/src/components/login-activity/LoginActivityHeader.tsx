import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

export interface LoginActivityHeaderProps {
  onBack: () => void;
}

export function LoginActivityHeader({ onBack }: LoginActivityHeaderProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" accessibilityRole="header">Login activity</AppText>
        <AppText variant="bodySmall" color="secondary">Review recent sign-ins to your account</AppText>
      </View>
    </View>
  );
}
