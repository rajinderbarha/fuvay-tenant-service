import React from "react";
import { View, TextInput, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { Icon } from "../Icon";

export interface BookingSearchBarProps {
  value: string;
  onChangeText: (value: string) => void;
  /** Highlighted when a non-default filter is applied, so the control
   * shows that the list is narrowed rather than hiding it. */
  filterActive?: boolean;
  onPressFilter: () => void;
}

/**
 * Search + filter row above the booking tabs.
 *
 * The term is sent to the backend (`q` on
 * /v1/customer/my-activity/bookings), never applied client-side: the list
 * is paginated, so filtering locally would only ever search the pages
 * already loaded and quietly miss older bookings.
 */
export function BookingSearchBar({ value, onChangeText, filterActive = false, onPressFilter }: BookingSearchBarProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
      <View
        style={{
          flex: 1, flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
          minHeight: theme.touchTargets.comfortable,
          paddingHorizontal: theme.spacing.base,
          borderRadius: theme.radiusUsage.input,
          backgroundColor: theme.colors.surfaceSecondary,
        }}
      >
        <Icon name="search-outline" size="standard" color={theme.colors.iconDefault} decorative />
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder="Search by service or booking ID"
          placeholderTextColor={theme.colors.textTertiary}
          returnKeyType="search"
          autoCorrect={false}
          accessibilityLabel="Search bookings"
          style={{ flex: 1, color: theme.colors.textPrimary, ...theme.typography.body }}
        />
        {value.length > 0 ? (
          <Pressable
            onPress={() => onChangeText("")}
            accessibilityRole="button"
            accessibilityLabel="Clear search"
            hitSlop={8}
          >
            <Icon name="close-circle" size="compact" color={theme.colors.iconDefault} decorative />
          </Pressable>
        ) : null}
      </View>

      <Pressable
        onPress={onPressFilter}
        accessibilityRole="button"
        accessibilityLabel="Filter bookings"
        accessibilityState={{ selected: filterActive }}
        style={({ pressed }) => ({
          width: theme.touchTargets.comfortable, height: theme.touchTargets.comfortable,
          alignItems: "center", justifyContent: "center",
          borderRadius: theme.radiusUsage.input,
          borderWidth: 1,
          borderColor: filterActive ? theme.colors.brandPrimary : theme.colors.borderSubtle,
          backgroundColor: filterActive ? theme.colors.surfaceInteractive : theme.colors.surfaceDefault,
          opacity: pressed ? 0.7 : 1,
        })}
      >
        <Icon
          name="options-outline"
          size="standard"
          color={filterActive ? theme.colors.brandPrimaryStrong : theme.colors.iconDefault}
          decorative
        />
      </Pressable>
    </View>
  );
}
