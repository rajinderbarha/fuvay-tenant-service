import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Icon } from "../Icon";
import { FieldLabel, FieldHelper } from "./FieldParts";

export interface QuantityFieldProps {
  label?: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  helperText?: string;
}

export function QuantityField({ label, value, onChange, min = 0, max = 999, step = 1, disabled, helperText }: QuantityFieldProps) {
  const { theme } = useTheme();
  const canDecrement = !disabled && value - step >= min;
  const canIncrement = !disabled && value + step <= max;

  return (
    <View>
      {label ? <FieldLabel label={label} /> : null}
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.md }}>
        <Pressable
          onPress={() => canDecrement && onChange(value - step)}
          disabled={!canDecrement}
          accessibilityRole="button"
          accessibilityLabel="Decrease quantity"
          style={{
            width: 40, height: 40, borderRadius: theme.radiusUsage.input, borderWidth: 1, borderColor: theme.colors.borderDefault,
            alignItems: "center", justifyContent: "center", opacity: canDecrement ? 1 : theme.opacity.disabled,
          }}
        >
          <Icon name="remove" size="standard" decorative />
        </Pressable>
        <AppText variant="numericMedium" style={{ minWidth: 32, textAlign: "center" }}>{value}</AppText>
        <Pressable
          onPress={() => canIncrement && onChange(value + step)}
          disabled={!canIncrement}
          accessibilityRole="button"
          accessibilityLabel="Increase quantity"
          style={{
            width: 40, height: 40, borderRadius: theme.radiusUsage.input, borderWidth: 1, borderColor: theme.colors.borderDefault,
            alignItems: "center", justifyContent: "center", opacity: canIncrement ? 1 : theme.opacity.disabled,
          }}
        >
          <Icon name="add" size="standard" decorative />
        </Pressable>
      </View>
      <FieldHelper text={helperText} />
    </View>
  );
}
