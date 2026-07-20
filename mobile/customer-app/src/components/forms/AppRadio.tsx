import React from "react";
import { View } from "react-native";
import { AppPressable } from "../primitives/AppPressable";
import { AppText } from "../primitives/AppText";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface AppRadioProps {
  selected: boolean;
  onSelect: () => void;
  label: string;
  disabled?: boolean;
  /** Groups radios for screen-reader semantics; pass the same value to every option in a set. */
  groupLabel?: string;
}

export function AppRadio({ selected, onSelect, label, disabled, groupLabel }: AppRadioProps) {
  const { theme } = useAppTheme();

  return (
    <AppPressable
      onPress={onSelect}
      disabled={disabled}
      accessibilityRole="radio"
      accessibilityLabel={groupLabel ? `${label}, ${groupLabel}` : label}
      accessibilityState={{ selected, disabled: Boolean(disabled) }}
      enforceMinTouchTarget
      style={{ flexDirection: "row", alignItems: "center", justifyContent: "flex-start", gap: theme.spacing[3] }}
    >
      <View
        style={{
          width: 20,
          height: 20,
          borderRadius: theme.radii.full,
          borderWidth: 2,
          borderColor: disabled ? theme.colors.borderSubtle : selected ? theme.colors.actionPrimary : theme.colors.borderDefault,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {selected ? (
          <View
            style={{
              width: 10,
              height: 10,
              borderRadius: theme.radii.full,
              backgroundColor: disabled ? theme.colors.borderSubtle : theme.colors.actionPrimary,
            }}
          />
        ) : null}
      </View>
      <AppText variant="bodyMedium" color={disabled ? "textDisabled" : "textPrimary"}>
        {label}
      </AppText>
    </AppPressable>
  );
}
