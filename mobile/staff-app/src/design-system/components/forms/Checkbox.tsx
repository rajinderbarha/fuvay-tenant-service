import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Icon } from "../Icon";
import { layout } from "../../tokens/spacing";

export interface CheckboxProps {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  helperText?: string;
}

export function Checkbox({ label, checked, onChange, disabled, helperText }: CheckboxProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={() => !disabled && onChange(!checked)}
      disabled={disabled}
      accessibilityRole="checkbox"
      accessibilityState={{ checked, disabled }}
      accessibilityLabel={label}
      style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, minHeight: layout.minTouchTarget, opacity: disabled ? theme.opacity.disabled : 1 }}
    >
      <View
        style={{
          width: 22, height: 22, borderRadius: theme.radius.radiusSmall,
          borderWidth: 2, borderColor: checked ? theme.colors.brandPrimary : theme.colors.borderStrong,
          backgroundColor: checked ? theme.colors.brandPrimary : "transparent",
          alignItems: "center", justifyContent: "center",
        }}
      >
        {checked ? <Icon name="checkmark" size="compact" color={theme.colors.brandOnPrimary} decorative /> : null}
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="body">{label}</AppText>
        {helperText ? <AppText variant="caption" color="tertiary">{helperText}</AppText> : null}
      </View>
    </Pressable>
  );
}
