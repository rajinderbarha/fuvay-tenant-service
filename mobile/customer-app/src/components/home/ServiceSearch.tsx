import React from "react";
import { View, TextInput } from "react-native";
import { useTheme } from "../../design-system/theme";
import { Icon } from "../Icon";

export interface ServiceSearchProps {
  value: string;
  onChangeText: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
}

/**
 * Full-width elevated search field. `GET /v1/customer/search` is a
 * confirmed real route (Phase D audit), but no query hook is wired to it
 * this task -- submitting is a no-op until a data-fetching phase connects
 * it, so this stays honestly UI-only rather than faking results.
 */
export function ServiceSearch({ value, onChangeText, onSubmit, placeholder = "Search AC repair, plumbing, cleaning…" }: ServiceSearchProps) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
        minHeight: theme.touchTargets.comfortable, paddingHorizontal: theme.spacing.base,
        borderRadius: theme.radiusUsage.input, backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1, borderColor: theme.colors.borderSubtle,
        ...theme.shadow.sm,
      }}
    >
      <Icon name="search-outline" size="standard" color={theme.colors.iconDefault} decorative />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        onSubmitEditing={onSubmit}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.textTertiary}
        returnKeyType="search"
        accessibilityLabel="Search services"
        style={{ flex: 1, color: theme.colors.textPrimary, ...theme.typography.body }}
      />
    </View>
  );
}
