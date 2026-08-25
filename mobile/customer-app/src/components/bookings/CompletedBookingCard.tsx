import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { CustomerBookingListItem } from "../../domain/bookingList";
import { formatMoney } from "../../domain/money";
import { formatCreatedAt } from "../../domain/dates";

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
      <AppCard style={{ padding: theme.spacing.md }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.md }}>
        <View style={{ width: 44, height: 44, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.statusSuccessSurface, alignItems: "center", justifyContent: "center" }}>
          <Icon name="checkmark-circle-outline" size="standard" color={theme.colors.statusSuccess} decorative />
        </View>
        <View style={{ flex: 1 }}>
          {item.serviceName ? <AppText variant="bodyStrong">{item.serviceName}</AppText> : null}
          {item.bookingNumber ? <AppText variant="caption" color="tertiary">{item.bookingNumber}</AppText> : null}
          {item.createdAt ? <AppText variant="caption" color="secondary">{formatCreatedAt(item.createdAt)}</AppText> : null}
        </View>
        <View style={{ alignItems: "flex-end", gap: theme.spacing.xxs }}>
          <AppBadge label="Completed" tone="success" />
          {item.pricing.state.kind === "valid" ? (
            <AppText variant="bodySmall">{formatMoney(item.pricing.state.amount)}</AppText>
          ) : null}
        </View>
        <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
      </View>
      </AppCard>
    </Pressable>
  );
}
