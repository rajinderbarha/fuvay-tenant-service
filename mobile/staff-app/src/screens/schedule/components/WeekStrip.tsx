import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function toLocalIso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export interface WeekStripProps {
  weekDates: Date[];
  selectedDate: Date;
  onSelect: (date: Date) => void;
  hasWorkByDate: Record<string, boolean>;
}

/** Seven-day horizontal strip -- selected date highlighted, dots indicate
 * assigned work (spec section 3). Month/year label renders separately by
 * the caller since it reflects the selected date, not necessarily the
 * strip's own first day. */
export function WeekStrip({ weekDates, selectedDate, onSelect, hasWorkByDate }: WeekStripProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
      {weekDates.map(date => {
        const selected = isSameDay(date, selectedDate);
        const key = toLocalIso(date);
        return (
          <Pressable
            key={key}
            onPress={() => onSelect(date)}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            accessibilityLabel={`${DAY_LABELS[date.getDay()]} ${date.getDate()}${hasWorkByDate[key] ? ", has assigned work" : ""}`}
            style={{
              alignItems: "center", paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.xs,
              borderRadius: theme.radiusUsage.card, backgroundColor: selected ? theme.colors.brandPrimary : "transparent",
              minWidth: 40,
            }}
          >
            <AppText variant="caption" color={selected ? "inverse" : "tertiary"}>{DAY_LABELS[date.getDay()]}</AppText>
            <AppText variant="bodyStrong" style={{ color: selected ? theme.colors.brandOnPrimary : theme.colors.textPrimary }}>{date.getDate()}</AppText>
            <View style={{ width: 5, height: 5, borderRadius: 3, marginTop: 2, backgroundColor: hasWorkByDate[key] ? (selected ? theme.colors.brandOnPrimary : theme.colors.statusSuccess) : "transparent" }} />
          </Pressable>
        );
      })}
    </View>
  );
}
