import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";

export interface NoOtherActiveBookingsCardProps {
  onViewCompleted: () => void;
}

/** Violet accent per the design -- a fixed brand colour, not a themed
 * surface, same reasoning as the empty state's calendar circle. */
const VIOLET = "#7C3AED";

/**
 * Sits directly below the single active-booking card on the Active tab,
 * telling the customer there is nothing else in flight rather than
 * leaving the list looking cut off after just one card.
 *
 * Rendered by MyBookingsScreen only when the Active tab's full result set
 * (not just the loaded page) is exactly one booking -- with zero it would
 * be misleading ("no OTHER" implies one exists), and with two or more
 * there IS something else active, so the card would be wrong either way.
 */
export function NoOtherActiveBookingsCard({ onViewCompleted }: NoOtherActiveBookingsCardProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onViewCompleted}
      accessibilityRole="button"
      accessibilityLabel="No other active bookings. View completed requests."
    >
      <AppCard>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
          <View
            style={{
              width: 40, height: 40, borderRadius: theme.radius.radiusFull,
              backgroundColor: VIOLET, alignItems: "center", justifyContent: "center",
            }}
          >
            {/* Calendar-with-clock in the design; Ionicons has no combined
                glyph, so the calendar carries it. */}
            <Icon name="calendar-outline" size="standard" color="#FFFFFF" decorative />
          </View>
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">No other active bookings</AppText>
            <AppText variant="bodySmall" color="secondary">
              Completed requests will appear in the Completed tab.
            </AppText>
          </View>
          <View
            style={{
              width: 32, height: 32, borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.brandPrimary, alignItems: "center", justifyContent: "center",
            }}
          >
            <Icon name="arrow-forward" size="compact" color={theme.colors.brandOnPrimary} decorative />
          </View>
        </View>
      </AppCard>
    </Pressable>
  );
}
