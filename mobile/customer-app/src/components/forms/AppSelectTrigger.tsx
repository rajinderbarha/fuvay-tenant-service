import React from "react";
import { View } from "react-native";
import { AppPressable } from "../primitives/AppPressable";
import { AppText } from "../primitives/AppText";
import { AppIcon } from "../primitives/AppIcon";
import { FieldMessage } from "./FieldMessage";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

/**
 * A reusable trigger + interface for opening a selection surface (bottom
 * sheet, modal, native picker) that a future feature supplies. This sprint
 * intentionally does not implement service-selection workflows — only the
 * shared trigger control and its contract.
 */
export interface AppSelectTriggerProps {
  label: string;
  valueLabel?: string;
  placeholder?: string;
  onPress: () => void;
  disabled?: boolean;
  errorText?: string;
}

export function AppSelectTrigger({ label, valueLabel, placeholder = "Select", onPress, disabled, errorText }: AppSelectTriggerProps) {
  const { theme } = useAppTheme();
  const hasError = Boolean(errorText);

  return (
    <View>
      <AppText variant="labelMedium" color="textSecondary" style={{ marginBottom: theme.spacing[2] }}>
        {label}
      </AppText>
      <AppPressable
        onPress={onPress}
        disabled={disabled}
        accessibilityRole="button"
        accessibilityLabel={`${label}: ${valueLabel ?? placeholder}`}
        accessibilityState={{ disabled: Boolean(disabled) }}
        enforceMinTouchTarget={false}
        style={{
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          borderWidth: 1,
          borderColor: hasError ? theme.colors.borderDanger : theme.colors.borderDefault,
          borderRadius: theme.radii.md,
          backgroundColor: disabled ? theme.colors.backgroundDisabled : theme.colors.surfacePrimary,
          paddingHorizontal: theme.spacing[5],
          minHeight: theme.sizes.inputHeight.md as number,
        }}
      >
        <AppText variant="bodyMedium" color={valueLabel ? "textPrimary" : "textTertiary"}>
          {valueLabel ?? placeholder}
        </AppText>
        <AppIcon name="chevron-forward" size="sm" color="iconSecondary" />
      </AppPressable>
      {hasError ? <FieldMessage tone="error">{errorText}</FieldMessage> : null}
    </View>
  );
}
