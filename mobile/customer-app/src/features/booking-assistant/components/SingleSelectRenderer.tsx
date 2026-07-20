import React from "react";
import { View } from "react-native";
import { AppText } from "../../../components/primitives/AppText";
import { AppRadio } from "../../../components/forms/AppRadio";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";

export interface SingleSelectOption {
  id: string;
  label: string;
  description?: string | null;
}

export interface SingleSelectRendererProps {
  title: string;
  options: SingleSelectOption[];
  selectedId: string | null;
  onSelect: (option: SingleSelectOption) => void;
}

/** Immediate-submit on selection — no separate "continue" tap, matching CUSTOMER-L5-05 §18/§15's "minimal typing" pattern. */
export function SingleSelectRenderer({ title, options, selectedId, onSelect }: SingleSelectRendererProps) {
  const { theme } = useAppTheme();

  return (
    <View accessibilityRole="radiogroup" style={{ gap: theme.spacing[3] }}>
      <AppText variant="headingLarge" accessibilityRole="header">
        {title}
      </AppText>
      <View style={{ gap: theme.spacing[4] }}>
        {options.map((option) => (
          <View key={option.id}>
            <AppRadio selected={selectedId === option.id} onSelect={() => onSelect(option)} label={option.label} groupLabel={title} />
            {option.description ? (
              <AppText variant="bodySmall" color="textSecondary" style={{ marginLeft: 32 }}>
                {option.description}
              </AppText>
            ) : null}
          </View>
        ))}
      </View>
    </View>
  );
}
