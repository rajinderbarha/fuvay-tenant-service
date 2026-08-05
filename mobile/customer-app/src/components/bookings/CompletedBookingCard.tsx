import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { CustomerBookingListItem } from "../../domain/bookingList";
import { formatMoney } from "../../domain/money";

export interface CompletedBookingCardProps {
  item: CustomerBookingListItem;
  onViewDetails: () => void;
}

/** No Rate/Rebook/Invoice actions -- none of those has a proven canonical
 * customer route yet (spec section 7). */
export function CompletedBookingCard({ item, onViewDetails }: CompletedBookingCardProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onViewDetails}
      accessibilityRole="button"
      accessibilityLabel={`${item.serviceName ?? "Booking"} ${item.bookingNumber ?? ""}, ${item.statusLabel}`}
    >
      <AppCard>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <View style={{ width: 40, height: 40, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.statusSuccessSurface, alignItems: "center", justifyContent: "center" }}>
          <Icon name="checkmark-circle-outline" size="standard" color={theme.colors.statusSuccess} decorative />
        </View>
        <View style={{ flex: 1 }}>
          {item.serviceName ? <AppText variant="bodyStrong">{item.serviceName}</AppText> : null}
          {item.bookingNumber ? <AppText variant="caption" color="tertiary">{item.bookingNumber}</AppText> : null}
        </View>
        <View style={{ alignItems: "flex-end", gap: theme.spacing.xxs }}>
          <AppBadge label="Completed" tone="success" />
          {item.pricing.state.kind === "valid" ? (
            <AppText variant="bodySmall">{formatMoney(item.pricing.state.amount)}</AppText>
          ) : null}
        </View>
      </View>
      </AppCard>
    </Pressable>
  );
}
