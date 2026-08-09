import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { FinalizedPricingPresentation } from "../../domain/bookingReceipt";
import { resolveServicePriceDisplay } from "../../domain/servicePricing";
import { formatMoney } from "../../domain/money";

/**
 * One fact per row: label on the left, value on the right.
 *
 * Replaces a three-column grid whose values were clipped to a single line. At a third
 * of a phone's width, "Pay provider directly" and "After inspection" both ended as
 * "Pay provider…" — and a price card that hides half of what it says about payment is
 * worse than one that takes an extra line. Values wrap here instead of truncating.
 */
function Row({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "baseline",
        justifyContent: "space-between", gap: theme.spacing.base,
      }}
    >
      <AppText variant="bodySmall" color="secondary" style={{ flexShrink: 0 }}>{label}</AppText>
      <AppText
        variant={emphasis ? "bodyStrong" : "bodySmall"}
        style={{ flex: 1, textAlign: "right" }}
      >
        {value}
      </AppText>
    </View>
  );
}

/** Same zero/Free discipline as the Review phase's PricingReviewCard --
 * never a fabricated number, never ₹0/Free without an explicit backend
 * state (spec section 6). */
export function FinalizedPricingCard({ pricing }: { pricing: FinalizedPricingPresentation }) {
  const { theme } = useTheme();

  if (pricing.inspection) {
    return (
      <AppCard>
        <AppText variant="labelStrong" color="secondary">Visit & pricing</AppText>
        <View style={{ marginTop: theme.spacing.sm, gap: theme.spacing.xs }}>
          <Row label="Visit fee" value={formatMoney(pricing.inspection.visitFee)} emphasis />
          <Row label="Repair quote" value="After inspection" />
          <Row label="Payment" value="Pay the provider directly" />
        </View>

        {/* Was "Backend confirmed" -- our word for our own plumbing, on a screen a
            customer reads. What they need to know is that the visit fee above is the
            agreed figure and nothing has been charged yet. */}
        <View
          style={{
            marginTop: theme.spacing.base, paddingTop: theme.spacing.sm,
            borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle,
            flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.xs,
          }}
        >
          <Icon name="information-circle-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary" style={{ flex: 1 }}>
            The visit fee is confirmed. No online payment has been collected.
          </AppText>
        </View>
      </AppCard>
    );
  }

  if (pricing.state.kind === "valid") {
    const display = resolveServicePriceDisplay(pricing.state);
    return (
      <AppCard>
        <AppText variant="labelStrong" color="secondary">Visit & pricing</AppText>
        <View style={{ marginTop: theme.spacing.sm, gap: theme.spacing.xs }}>
          <Row label={display.label} value={formatMoney(pricing.state.amount)} emphasis />
          <Row label="Payment" value="Pay the provider directly" />
        </View>
        <View
          style={{
            marginTop: theme.spacing.base, paddingTop: theme.spacing.sm,
            borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle,
            flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.xs,
          }}
        >
          <Icon name="information-circle-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary" style={{ flex: 1 }}>
            No online payment has been collected.
          </AppText>
        </View>
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
