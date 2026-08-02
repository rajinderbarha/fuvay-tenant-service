import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";

export interface SegmentedControlOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentedControlOption<T>[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
}

export function SegmentedControl<T extends string>({ options, value, onChange, disabled }: SegmentedControlProps<T>) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityRole="tablist"
      style={{
        flexDirection: "row", padding: 3, borderRadius: theme.radiusUsage.button,
        backgroundColor: theme.colors.surfaceInteractive, opacity: disabled ? theme.opacity.disabled : 1,
      }}
    >
      {options.map(opt => {
        const selected = opt.value === value;
        return (
          <Pressable
            key={opt.value}
            onPress={() => !disabled && onChange(opt.value)}
            disabled={disabled}
            accessibilityRole="tab"
            accessibilityState={{ selected, disabled }}
            accessibilityLabel={opt.label}
            style={{
              flex: 1, paddingVertical: theme.spacing.sm, borderRadius: theme.radiusUsage.button - 2,
              alignItems: "center", backgroundColor: selected ? theme.colors.surfaceRaised : "transparent",
            }}
          >
            <AppText variant="bodySmall" color={selected ? "primary" : "secondary"}>{opt.label}</AppText>
          </Pressable>
        );
      })}
    </View>
  );
}
