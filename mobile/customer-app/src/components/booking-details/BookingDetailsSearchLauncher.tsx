import React, { useState } from "react";
import { View, TextInput, Pressable } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { Icon } from "../Icon";

/**
 * "Search by service or booking ID" row on Booking Details.
 *
 * This screen is already one specific, open booking -- there is nothing
 * HERE for a search box to search across. Rather than ship it as a dead
 * control (the earlier decision on this screen) or silently drop it, it
 * is real: submitting jumps to My Bookings with the term already applied
 * server-side there, and the filter icon jumps to My Bookings with its
 * status sheet already open. Either way the search/filter actually runs
 * where a list exists to run it against.
 */
export function BookingDetailsSearchLauncher() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const [value, setValue] = useState("");

  function launchSearch() {
    if (!value.trim()) return;
    (navigation as unknown as { navigate: (name: string, params?: object) => void })
      .navigate("Bookings", { initialSearch: value.trim() });
  }

  function launchFilter() {
    (navigation as unknown as { navigate: (name: string, params?: object) => void })
      .navigate("Bookings", { openFilter: true });
  }

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
          onChangeText={setValue}
          onSubmitEditing={launchSearch}
          placeholder="Search by service or booking ID"
          placeholderTextColor={theme.colors.textTertiary}
          returnKeyType="search"
          autoCorrect={false}
          accessibilityLabel="Search your bookings"
          accessibilityHint="Opens My Bookings with this search applied"
          style={{ flex: 1, color: theme.colors.textPrimary, ...theme.typography.body }}
        />
      </View>
      <Pressable
        onPress={launchFilter}
        accessibilityRole="button"
        accessibilityLabel="Filter bookings"
        accessibilityHint="Opens My Bookings with the status filter"
        style={({ pressed }) => ({
          width: theme.touchTargets.comfortable, height: theme.touchTargets.comfortable,
          alignItems: "center", justifyContent: "center",
          borderRadius: theme.radiusUsage.input,
          borderWidth: 1, borderColor: theme.colors.borderSubtle,
          backgroundColor: theme.colors.surfaceDefault,
          opacity: pressed ? 0.7 : 1,
        })}
      >
        <Icon name="options-outline" size="standard" color={theme.colors.iconDefault} decorative />
      </Pressable>
    </View>
  );
}
