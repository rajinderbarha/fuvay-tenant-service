import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { FinalizedPricingPresentation } from "../../domain/bookingReceipt";
import { resolveServicePriceDisplay } from "../../domain/servicePricing";
import { formatMoney } from "../../domain/money";

function Column({ label, value }: { label: string; value: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flex: 1, minWidth: 0 }}>
      <AppText variant="caption" color="tertiary">{label}</AppText>
      <AppText variant="bodyStrong" numberOfLines={1} style={{ marginTop: theme.spacing.xxs }}>{value}</AppText>
    </View>
  );
}

/** Same zero/Free discipline as the Review phase's PricingReviewCard --
 * never a fabricated number, never ₹0/Free without an explicit backend
 * state (spec section 6). Three-column layout for the inspection case
 * matches the design; the "valid" fixed-price case has no equivalent
 * reference layout, so it keeps its simpler single-value presentation. */
export function FinalizedPricingCard({ pricing }: { pricing: FinalizedPricingPresentation }) {
  const { theme } = useTheme();

  if (pricing.inspection) {
    return (
      <AppCard>
        <AppText variant="labelStrong" color="secondary">Visit & pricing</AppText>
        <View style={{ flexDirection: "row", marginTop: theme.spacing.sm }}>
          <Column label="Visit fee" value={formatMoney(pricing.inspection.visitFee)} />
          <Column label="Repair quote" value="After inspection" />
          <Column label="Payment" value="Pay provider directly" />
        </View>
        <View
          style={{
            marginTop: theme.spacing.sm, alignSelf: "flex-start",
            paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
            borderRadius: theme.radiusUsage.statusPill,
            borderWidth: 1, borderColor: theme.colors.statusSuccess,
            backgroundColor: theme.colors.statusSuccessSurface,
          }}
        >
          <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>Backend confirmed</AppText>
        </View>
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
          No online payment has been collected.
        </AppText>
      </AppCard>
    );
  }

  if (pricing.state.kind === "valid") {
    const display = resolveServicePriceDisplay(pricing.state);
    return (
      <AppCard>
        <AppText variant="labelStrong" color="secondary">Visit & pricing</AppText>
        <AppText variant="bodyStrong" style={{ marginTop: theme.spacing.xxs }}>{formatMoney(pricing.state.amount)}</AppText>
        <AppText variant="caption" color="tertiary">{display.label}</AppText>
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
          No online payment has been collected.
        </AppText>
      </AppCard>
    );
  }

  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Visit & pricing</AppText>
      <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>
        Pricing details will be confirmed shortly. Check My Bookings for updates.
      </AppText>
    </AppCard>
  );
}
