import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { FieldLabel, FieldHelper, FormError, useFieldChrome } from "./FieldParts";
import { Icon } from "../Icon";

export interface SelectFieldProps {
  label?: string;
  placeholder?: string;
  /** Already-resolved display value -- SelectField does not fetch or
   * manage option lists; pair it with a BottomSheet/ActionSheet from
   * ../overlays for the actual picker interaction. */
  displayValue?: string;
  helperText?: string;
  errorText?: string;
  required?: boolean;
  disabled?: boolean;
  disabledReason?: string;
  onPress: () => void;
}

export function SelectField({ label, placeholder = "Select…", displayValue, helperText, errorText, required, disabled, disabledReason, onPress }: SelectFieldProps) {
  const { theme } = useTheme();
  const chrome = useFieldChrome({ error: !!errorText, disabled });

  return (
    <View>
      {label ? <FieldLabel label={label} required={required} /> : null}
      <Pressable
        onPress={onPress}
        disabled={disabled}
        accessibilityRole="button"
        accessibilityLabel={label ?? placeholder}
        accessibilityState={{ disabled }}
        style={{
          flexDirection: "row", alignItems: "center", justifyContent: "space-between",
          paddingHorizontal: theme.spacing.md, minHeight: 48, opacity: disabled ? theme.opacity.disabled : 1,
          ...chrome,
        }}
      >
        <AppText variant="body" color={displayValue ? "primary" : "tertiary"}>
          {displayValue ?? placeholder}
        </AppText>
        <Icon name="chevron-down" size="standard" color={theme.colors.textTertiary} decorative />
      </Pressable>
      {disabled && disabledReason ? <FieldHelper text={disabledReason} /> : <FieldHelper text={helperText} />}
      <FormError message={errorText} />
    </View>
  );
}
