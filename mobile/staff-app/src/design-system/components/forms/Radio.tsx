import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { layout } from "../../tokens/spacing";

export interface RadioProps {
  label: string;
  selected: boolean;
  onSelect: () => void;
  disabled?: boolean;
}

export function Radio({ label, selected, onSelect, disabled }: RadioProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={() => !disabled && onSelect()}
      disabled={disabled}
      accessibilityRole="radio"
      accessibilityState={{ selected, disabled }}
      accessibilityLabel={label}
      style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, minHeight: layout.minTouchTarget, opacity: disabled ? theme.opacity.disabled : 1 }}
    >
      <View
        style={{
          width: 22, height: 22, borderRadius: theme.radiusUsage.avatar,
          borderWidth: 2, borderColor: selected ? theme.colors.brandPrimary : theme.colors.borderStrong,
          alignItems: "center", justifyContent: "center",
        }}
      >
        {selected ? <View style={{ width: 12, height: 12, borderRadius: theme.radiusUsage.avatar, backgroundColor: theme.colors.brandPrimary }} /> : null}
      </View>
      <AppText variant="body">{label}</AppText>
    </Pressable>
  );
}
