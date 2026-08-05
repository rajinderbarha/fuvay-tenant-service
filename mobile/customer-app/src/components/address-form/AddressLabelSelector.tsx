import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { ADDRESS_LABELS, AddressLabel } from "../../domain/addressForm";

export interface AddressLabelSelectorProps {
  value: AddressLabel;
  onChange: (label: AddressLabel) => void;
}

/** Home/Work/Other segmented control -- the only three values the real
 * backend's `label` column accepts (spec section 3/6). */
export function AddressLabelSelector({ value, onChange }: AddressLabelSelectorProps) {
  const { theme } = useTheme();
  return (
    <View>
      <AppText variant="label" color="secondary" style={{ marginBottom: theme.spacing.xxs }}>Address label</AppText>
      <View style={{ flexDirection: "row", gap: theme.spacing.xs }} accessibilityRole="radiogroup">
        {ADDRESS_LABELS.map(label => {
          const selected = value === label;
          return (
            <Pressable
              key={label}
              onPress={() => onChange(label)}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              accessibilityLabel={label}
              hitSlop={4}
              style={{
                flex: 1,
                minHeight: theme.touchTargets.minimum,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: theme.radiusUsage.input,
                borderWidth: 1,
                borderColor: selected ? theme.colors.brandPrimary : theme.colors.borderDefault,
                backgroundColor: selected ? theme.colors.brandPrimaryMuted : theme.colors.surfaceDefault,
              }}
            >
              <AppText variant="labelStrong" style={{ color: selected ? theme.colors.brandPrimary : theme.colors.textPrimary }}>
                {label}
              </AppText>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}
