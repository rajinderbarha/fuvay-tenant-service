import React from "react";
import { View } from "react-native";
import { AppPressable } from "../primitives/AppPressable";
import { AppText } from "../primitives/AppText";
import { AppIcon } from "../primitives/AppIcon";
import { FieldMessage } from "./FieldMessage";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface AppCheckboxProps {
  checked: boolean | "indeterminate";
  onChange: (checked: boolean) => void;
  label: string;
  helperText?: string;
  errorText?: string;
  disabled?: boolean;
}

export function AppCheckbox({ checked, onChange, label, helperText, errorText, disabled }: AppCheckboxProps) {
  const { theme } = useAppTheme();
  const isChecked = checked === true;
  const isIndeterminate = checked === "indeterminate";

  return (
    <View>
      <AppPressable
        onPress={() => onChange(!isChecked)}
        disabled={disabled}
        accessibilityRole="checkbox"
        accessibilityLabel={label}
        accessibilityState={{ checked: isIndeterminate ? "mixed" : isChecked, disabled: Boolean(disabled) }}
        enforceMinTouchTarget
        style={{ flexDirection: "row", alignItems: "center", justifyContent: "flex-start", gap: theme.spacing[3] }}
      >
        <View
          style={{
            width: 20,
            height: 20,
            borderRadius: theme.radii.xs,
            borderWidth: 2,
            borderColor: disabled ? theme.colors.borderSubtle : isChecked || isIndeterminate ? theme.colors.actionPrimary : theme.colors.borderDefault,
            backgroundColor: (isChecked || isIndeterminate) && !disabled ? theme.colors.actionPrimary : "transparent",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {isChecked ? (
            <AppIcon name="checkmark-circle" size="xs" color="iconInverse" />
          ) : isIndeterminate ? (
            <View style={{ width: 10, height: 2, backgroundColor: theme.colors.iconInverse }} />
          ) : null}
        </View>
        <AppText variant="bodyMedium" color={disabled ? "textDisabled" : "textPrimary"}>
          {label}
        </AppText>
      </AppPressable>
      {errorText ? <FieldMessage tone="error">{errorText}</FieldMessage> : helperText ? <FieldMessage tone="helper">{helperText}</FieldMessage> : null}
    </View>
  );
}
