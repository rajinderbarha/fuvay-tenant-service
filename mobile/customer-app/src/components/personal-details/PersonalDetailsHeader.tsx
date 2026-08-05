import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

export interface PersonalDetailsHeaderProps {
  onBack: () => void;
  onCancel: () => void;
}

export function PersonalDetailsHeader({ onBack, onCancel }: PersonalDetailsHeaderProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" accessibilityRole="header">Personal details</AppText>
        <AppText variant="bodySmall" color="secondary">Keep your account information up to date</AppText>
      </View>
      <AppText variant="labelStrong" color="link" onPress={onCancel} accessibilityRole="button">Cancel</AppText>
    </View>
  );
}
