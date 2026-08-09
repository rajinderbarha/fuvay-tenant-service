import React, { useEffect, useRef } from "react";
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
  /** Focus the field as soon as it appears. Set when the bar was opened by the
   * customer tapping search, so the keyboard is already up and they can type -- an
   * empty box they then have to tap again is a wasted step. */
  autoFocus?: boolean;
  /** Collapses the bar. Absent when the bar cannot be closed, which is the case
   * while a term is applied: hiding the reason a list is narrowed is how customers
   * conclude their bookings have vanished. */
  onClose?: () => void;
}

/**
 * Search + filter row above the booking tabs. Shown ON DEMAND -- it used to occupy
 * the top of the screen permanently, spending a fixed slice of a phone on a control
 * most visits never touch.
 *
 * The term is sent to the backend (`q` on
 * /v1/customer/my-activity/bookings), never applied client-side: the list
 * is paginated, so filtering locally would only ever search the pages
 * already loaded and quietly miss older bookings.
 */
export function BookingSearchBar({
  value, onChangeText, filterActive = false, onPressFilter, autoFocus = false, onClose,
}: BookingSearchBarProps) {
  const { theme } = useTheme();
  const inputRef = useRef<TextInput>(null);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
      <View
        style={{
          flex: 1, flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
          // `minimum`, not `comfortable`: still a legal 44pt target, but the
          // comfortable size made a secondary control the tallest thing on the
          // screen after the title.
          minHeight: theme.touchTargets.minimum,
          paddingHorizontal: theme.spacing.sm,
          borderRadius: theme.radiusUsage.input,
          backgroundColor: theme.colors.surfaceSecondary,
        }}
      >
        <Icon name="search-outline" size="standard" color={theme.colors.iconDefault} decorative />
        <TextInput
          ref={inputRef}
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
        ) : onClose ? (
          // Only offered with the field empty: with a term applied, closing would
          // leave a narrowed list and no visible reason for it.
          <Pressable
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel="Close search"
            hitSlop={8}
          >
            <Icon name="close" size="compact" color={theme.colors.iconDefault} decorative />
          </Pressable>
        ) : null}
      </View>

      <Pressable
        onPress={onPressFilter}
        accessibilityRole="button"
        accessibilityLabel="Filter bookings"
        accessibilityState={{ selected: filterActive }}
        style={({ pressed }) => ({
          width: theme.touchTargets.minimum, height: theme.touchTargets.minimum,
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
