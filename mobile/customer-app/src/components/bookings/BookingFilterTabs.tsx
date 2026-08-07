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
 * useCustomerBookingsListQuery.ts.
 *
 * Rendered as one full-width segmented control per the design: a single
 * bordered track, equal-width segments split by hairlines, and the
 * selected segment filled. */
export function BookingFilterTabs({ selected, onSelect, activeCount, completedCount }: BookingFilterTabsProps) {
  const { theme } = useTheme();
  const tabs: Array<{ key: BookingListFilter; label: string; count: number | null }> = [
    { key: "active", label: "Active", count: activeCount },
    { key: "completed", label: "Completed", count: completedCount === 0 ? null : completedCount },
    { key: "all", label: "All", count: null },
  ];

  return (
    <View
      accessibilityRole="tablist"
      style={{
        flexDirection: "row",
        borderRadius: theme.radiusUsage.input,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        backgroundColor: theme.colors.surfaceSecondary,
        overflow: "hidden",
      }}
    >
      {tabs.map((tab, index) => {
        const isSelected = selected === tab.key;
        return (
          <Pressable
            key={tab.key}
            onPress={() => onSelect(tab.key)}
            accessibilityRole="tab"
            accessibilityState={{ selected: isSelected }}
            accessibilityLabel={tab.count != null ? `${tab.label}, ${tab.count}` : tab.label}
            style={{
              flex: 1,
              flexDirection: "row", alignItems: "center", justifyContent: "center",
              gap: theme.spacing.xs,
              minHeight: theme.touchTargets.minimum,
              paddingHorizontal: theme.spacing.xs,
              borderRadius: theme.radiusUsage.input,
              // The divider belongs between unselected segments only --
              // drawing it against a filled segment leaves a seam on its edge.
              borderLeftWidth: index > 0 && !isSelected && selected !== tabs[index - 1].key ? 1 : 0,
              borderLeftColor: theme.colors.borderSubtle,
              backgroundColor: isSelected ? theme.colors.brandPrimary : "transparent",
            }}
          >
            <AppText
              variant="labelStrong"
              numberOfLines={1}
              style={{ color: isSelected ? theme.colors.brandOnPrimary : theme.colors.textSecondary }}
            >
              {tab.label}
            </AppText>
            {tab.count != null ? (
              <View
                style={{
                  minWidth: 20, height: 20, borderRadius: theme.radius.radiusFull,
                  alignItems: "center", justifyContent: "center", paddingHorizontal: 5,
                  backgroundColor: isSelected ? theme.colors.brandOnPrimary : theme.colors.brandPrimary,
                }}
              >
                <AppText
                  variant="caption"
                  style={{ color: isSelected ? theme.colors.brandPrimary : theme.colors.brandOnPrimary }}
                >
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
