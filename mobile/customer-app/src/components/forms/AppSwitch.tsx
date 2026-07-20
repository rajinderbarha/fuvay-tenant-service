import React from "react";
import { Switch, View } from "react-native";
import { AppText } from "../primitives/AppText";
import { FieldMessage } from "./FieldMessage";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface AppSwitchProps {
  value: boolean;
  onValueChange: (value: boolean) => void;
  label: string;
  helperText?: string;
  disabled?: boolean;
}

export function AppSwitch({ value, onValueChange, label, helperText, disabled }: AppSwitchProps) {
  const { theme } = useAppTheme();

  return (
    <View>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: theme.spacing[4] }}>
        <AppText variant="bodyMedium" color={disabled ? "textDisabled" : "textPrimary"} style={{ flex: 1 }}>
          {label}
        </AppText>
        <Switch
          value={value}
          onValueChange={onValueChange}
          disabled={disabled}
          accessibilityRole="switch"
          accessibilityLabel={label}
          accessibilityState={{ checked: value, disabled: Boolean(disabled) }}
          trackColor={{ false: theme.colors.borderDefault, true: theme.colors.actionPrimary }}
          thumbColor={theme.colors.backgroundPrimary}
        />
      </View>
      {helperText ? <FieldMessage tone="helper">{helperText}</FieldMessage> : null}
    </View>
  );
}
