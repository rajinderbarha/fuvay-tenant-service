import React from "react";
import { View, TextInput, Pressable, ActivityIndicator } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";
import { Icon } from "./Icon";
import { PlaceSuggestionDto } from "../api/contracts/places";

export interface AddressSearchFieldProps {
  value: string;
  onChangeText: (value: string) => void;
  suggestions: readonly PlaceSuggestionDto[];
  available: boolean;
  searching: boolean;
  resolving: boolean;
  onSelect: (placeId: string) => void;
  /** Theme override so this can sit inside the chat's own dark bot surface as well
   * as an ordinary form. */
  palette?: {
    surface: string;
    border: string;
    text: string;
    placeholder: string;
    muted: string;
  };
}

/**
 * "Search your address" — the input plus its suggestion list.
 *
 * Renders NOTHING when address lookup is unavailable on this deployment. A search box
 * that can never return a result is worse than no search box: the customer types into
 * it, nothing happens, and they conclude the app is broken rather than that the
 * feature is off. The typed fields underneath are always there and always sufficient.
 *
 * Selecting a suggestion is a starting point, not a lock-in. Every field it fills
 * stays editable, because Google's idea of an Indian address and the one the
 * technician needs to find the door are not always the same thing -- and it will
 * often have no PIN code at all for a rural locality.
 */
export function AddressSearchField({
  value, onChangeText, suggestions, available, searching, resolving, onSelect, palette,
}: AddressSearchFieldProps) {
  const { theme } = useTheme();
  if (!available) return null;

  const colors = palette ?? {
    surface: theme.colors.surfaceSecondary,
    border: theme.colors.borderSubtle,
    text: theme.colors.textPrimary,
    placeholder: theme.colors.textTertiary,
    muted: theme.colors.textSecondary,
  };

  return (
    <View style={{ gap: theme.spacing.xs }}>
      <View
        style={{
          flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
          minHeight: theme.touchTargets.minimum,
          paddingHorizontal: theme.spacing.base,
          borderRadius: theme.radiusUsage.input,
          backgroundColor: colors.surface,
          borderWidth: 1, borderColor: colors.border,
        }}
      >
        <Icon name="search-outline" size="standard" color={colors.placeholder} decorative />
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder="Search your address or area"
          placeholderTextColor={colors.placeholder}
          autoCorrect={false}
          accessibilityLabel="Search your address"
          style={{ flex: 1, color: colors.text, ...theme.typography.body }}
        />
        {searching || resolving ? (
          <ActivityIndicator size="small" color={theme.colors.brandPrimaryStrong} />
        ) : value.length > 0 ? (
          <Pressable
            onPress={() => onChangeText("")}
            accessibilityRole="button"
            accessibilityLabel="Clear address search"
            hitSlop={8}
          >
            <Icon name="close-circle" size="compact" color={colors.placeholder} decorative />
          </Pressable>
        ) : null}
      </View>

      {suggestions.length > 0 ? (
        <View
          style={{
            borderRadius: theme.radiusUsage.input,
            backgroundColor: colors.surface,
            borderWidth: 1, borderColor: colors.border,
            overflow: "hidden",
          }}
        >
          {suggestions.map((suggestion, index) => (
            <Pressable
              key={suggestion.place_id}
              onPress={() => onSelect(suggestion.place_id)}
              accessibilityRole="button"
              accessibilityLabel={suggestion.description}
              style={({ pressed }) => ({
                flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
                paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
                borderTopWidth: index === 0 ? 0 : 1,
                borderTopColor: colors.border,
                opacity: pressed ? 0.7 : 1,
              })}
            >
              <Icon name="location-outline" size="compact" color={colors.muted} decorative />
              <AppText variant="bodySmall" style={{ flex: 1, color: colors.text }} numberOfLines={2}>
                {suggestion.description}
              </AppText>
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}
