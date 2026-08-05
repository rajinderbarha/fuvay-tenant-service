import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

export interface SavedAddressesHeaderProps {
  onBack: () => void;
  onAddNew?: () => void;
}

/** `Add new` renders only when a functional Address Form exists (spec
 * section 6) -- `onAddNew` is `undefined` this phase. */
export function SavedAddressesHeader({ onBack, onAddNew }: SavedAddressesHeaderProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" accessibilityRole="header">Saved addresses</AppText>
        <AppText variant="bodySmall" color="secondary">Manage addresses used for service requests</AppText>
      </View>
      {onAddNew ? (
        <AppText variant="labelStrong" color="link" onPress={onAddNew} accessibilityRole="button">Add new</AppText>
      ) : null}
    </View>
  );
}
