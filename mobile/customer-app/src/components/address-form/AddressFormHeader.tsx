import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

export interface AddressFormHeaderProps {
  mode: "add" | "edit";
  onBack: () => void;
}

export function AddressFormHeader({ mode, onBack }: AddressFormHeaderProps) {
  const { theme } = useTheme();
  const title = mode === "add" ? "Add address" : "Edit address";
  const subtitle = mode === "add"
    ? "Save an address for future service requests"
    : "Update this address for future service requests";
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" accessibilityRole="header">{title}</AppText>
        <AppText variant="bodySmall" color="secondary">{subtitle}</AppText>
      </View>
    </View>
  );
}
