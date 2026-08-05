import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { BookingListFilter } from "../../domain/bookingFilters";

export interface BookingFilterTabsProps {
  selected: BookingListFilter;
  onSelect: (filter: BookingListFilter) => void;
  activeCount: number;
  completedCount: number;
}

/** Counts come from the complete, authoritative fetched set (spec: "Never
 * calculate 'Active 1' from only one loaded page") -- see
 * useCustomerBookingsListQuery.ts. */
export function BookingFilterTabs({ selected, onSelect, activeCount, completedCount }: BookingFilterTabsProps) {
  const { theme } = useTheme();
  const tabs: Array<{ key: BookingListFilter; label: string; count: number | null }> = [
    { key: "active", label: "Active", count: activeCount },
    { key: "completed", label: "Completed", count: completedCount === 0 ? null : completedCount },
    { key: "all", label: "All", count: null },
  ];

  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.xs }}>
      {tabs.map(tab => {
        const isSelected = selected === tab.key;
        return (
          <Pressable
            key={tab.key}
            onPress={() => onSelect(tab.key)}
            accessibilityRole="tab"
            accessibilityState={{ selected: isSelected }}
            accessibilityLabel={tab.count != null ? `${tab.label}, ${tab.count}` : tab.label}
            style={{
              flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
              paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xs,
              borderRadius: theme.radiusUsage.statusPill,
              backgroundColor: isSelected ? theme.colors.brandPrimary : theme.colors.surfaceInteractive,
            }}
          >
            <AppText variant="labelStrong" style={{ color: isSelected ? theme.colors.brandOnPrimary : theme.colors.textPrimary }}>
              {tab.label}
            </AppText>
            {tab.count != null ? (
              <View
                style={{
                  minWidth: 18, height: 18, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
                  backgroundColor: isSelected ? theme.colors.brandOnPrimary : theme.colors.brandPrimary,
                  paddingHorizontal: 4,
                }}
              >
                <AppText variant="caption" style={{ color: isSelected ? theme.colors.brandPrimary : theme.colors.brandOnPrimary }}>
                  {tab.count}
                </AppText>
              </View>
            ) : null}
          </Pressable>
        );
      })}
    </View>
  );
}
