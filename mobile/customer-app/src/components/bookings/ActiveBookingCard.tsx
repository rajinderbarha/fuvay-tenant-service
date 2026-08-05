import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { CustomerBookingListItem } from "../../domain/bookingList";
import { BookingJourney } from "../booking-details/BookingJourney";
import { formatMoney } from "../../domain/money";

export interface ActiveBookingCardProps {
  item: CustomerBookingListItem;
  onViewDetails: () => void;
}

/** Adapts to whatever real fields the booking actually carries -- never
 * hardcodes AC/LG/Split AC (spec section 6). Same status/pricing adapters
 * as Booking Details, never re-derived here. */
export function ActiveBookingCard({ item, onViewDetails }: ActiveBookingCardProps) {
  const { theme } = useTheme();
  return (
    <AppCard style={{ gap: theme.spacing.sm }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, flex: 1 }}>
          <View style={{ width: 44, height: 44, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center" }}>
            <Icon name="construct-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1 }}>
            {item.serviceName ? <AppText variant="bodyStrong">{item.serviceName}</AppText> : null}
            {item.bookingNumber ? <AppText variant="caption" color="tertiary">{item.bookingNumber}</AppText> : null}
          </View>
        </View>
        <AppBadge label={item.statusLabel} tone={item.stage === "unknown" ? "neutral" : "warning"} />
      </View>

      {item.activityText ? (
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <Icon name="sparkles" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">{item.activityText}</AppText>
            {item.supportingText ? <AppText variant="bodySmall" color="secondary">{item.supportingText}</AppText> : null}
          </View>
        </View>
      ) : null}

      <BookingJourney stage={item.stage} />

      {item.summaryFields.length > 0 ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.base }}>
          {item.summaryFields.slice(0, 4).map(f => (
            <AppText key={f.key} variant="bodySmall" color="secondary">{f.value}</AppText>
          ))}
        </View>
      ) : null}

      {item.address.formatted ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          <Icon name="location-outline" size="compact" color={theme.colors.textSecondary} decorative />
          <AppText variant="bodySmall" color="secondary">{item.address.formatted}</AppText>
        </View>
      ) : null}

      {item.pricing.inspection ? (
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <AppText variant="bodySmall" color="secondary">Inspection visit</AppText>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
            <AppText variant="bodyStrong">{formatMoney(item.pricing.inspection.visitFee)}</AppText>
            <AppBadge label="Backend confirmed" tone="success" />
          </View>
        </View>
      ) : item.pricing.state.kind === "valid" ? (
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <AppText variant="bodySmall" color="secondary">Price</AppText>
          <AppText variant="bodyStrong">{formatMoney(item.pricing.state.amount)}</AppText>
        </View>
      ) : null}

      <AppButton label="View details" onPress={onViewDetails} fullWidth />
    </AppCard>
  );
}
