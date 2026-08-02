import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { SelectOption } from "../../../services/inspection/types";

export interface SelectChipsProps {
  options: SelectOption[];
  selected: string[];
  onToggle: (value: string) => void;
  multi: boolean;
  disabled?: boolean;
}

/** Diagnosis/single/multi-select answer editor -- pill chips matching the
 * approved reference design. Options come entirely from the backend-authored
 * checklist definition (ChecklistItem.select_options), never hardcoded. */
export function SelectChips({ options, selected, onToggle, multi, disabled }: SelectChipsProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
      {options.map(opt => {
        const isSelected = selected.includes(opt.value);
        return (
          <Pressable
            key={opt.value}
            onPress={() => !disabled && onToggle(opt.value)}
            disabled={disabled}
            accessibilityRole={multi ? "checkbox" : "radio"}
            accessibilityState={{ selected: isSelected, disabled }}
            accessibilityLabel={opt.label}
            style={{
              paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
              borderRadius: theme.radiusUsage.statusPill, borderWidth: 1,
              borderColor: isSelected ? theme.colors.brandPrimary : theme.colors.borderDefault,
              backgroundColor: isSelected ? theme.colors.brandPrimary : "transparent",
              opacity: disabled ? theme.opacity.disabled : 1,
            }}
          >
            <AppText variant="bodySmall" style={{ color: isSelected ? theme.colors.brandOnPrimary : theme.colors.textPrimary }}>
              {opt.label}
            </AppText>
          </Pressable>
        );
      })}
    </View>
  );
}
