import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

export interface ProfileHeaderProps {
  onToggleTheme: () => void;
  themeIcon: "sunny-outline" | "moon-outline";
}

export function ProfileHeader({ onToggleTheme, themeIcon }: ProfileHeaderProps) {
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" }}>
      <View>
        <AppText variant="headingLarge" accessibilityRole="header">Profile</AppText>
        <AppText variant="bodySmall" color="secondary">Manage your account and preferences</AppText>
      </View>
      <AppIconButton name={themeIcon} onPress={onToggleTheme} accessibilityLabel="Change appearance" />
    </View>
  );
}
