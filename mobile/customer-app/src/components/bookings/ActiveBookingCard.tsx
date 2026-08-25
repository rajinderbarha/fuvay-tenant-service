import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { CustomerBookingListItem } from "../../domain/bookingList";
import { RECEIPT_TIMELINE_STEPS, resolveTimelineStepState } from "../../domain/bookingStatus";
import { formatMoney } from "../../domain/money";
import { formatCreatedAt } from "../../domain/dates";
import { formatScheduleWindow } from "../../domain/activeJobPresentation";
import { FuvayIcon } from "../FuvayIcon";

export interface ActiveBookingCardProps {
  item: CustomerBookingListItem;
  onViewDetails: () => void;
  onContactSupport: () => void;
}

/** Scan-first summary; the full receipt remains on Booking Details. */
export function ActiveBookingCard({ item, onViewDetails, onContactSupport }: ActiveBookingCardProps) {
  const { theme } = useTheme();
  const cancelled = item.rawStatus === "cancelled";
  const needsAttention = item.urgency === "late";
  const statusColor = cancelled || needsAttention
    ? theme.colors.statusDanger
    : item.stage === "unknown"
      ? theme.colors.statusNeutral
      : theme.colors.statusSuccess;
  const statusSurface = cancelled || needsAttention
    ? theme.colors.statusDangerSurface
    : item.stage === "unknown"
      ? theme.colors.statusNeutralSurface
      : theme.colors.statusSuccessSurface;
  const scheduleLabel = formatScheduleWindow(item.scheduledDate, item.scheduledTimeWindow);
  const priceLabel = item.pricing.inspection
    ? formatMoney(item.pricing.inspection.visitFee)
    : item.pricing.state.kind === "valid"
      ? formatMoney(item.pricing.state.amount)
      : null;

  return (
    <AppCard style={{ padding: 0, overflow: "hidden" }}>
      <View style={{ padding: theme.spacing.base, gap: theme.spacing.md }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.md }}>
          <View
            style={{
              width: 48,
              height: 48,
              borderRadius: theme.radiusUsage.card,
              backgroundColor: theme.colors.brandPrimaryMuted,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name="snow-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1, minWidth: 0 }}>
            <AppText variant="bodyStrong" numberOfLines={1}>{item.serviceName ?? "Service request"}</AppText>
            {item.bookingNumber ? <AppText variant="caption" color="tertiary">{item.bookingNumber}</AppText> : null}
            {item.createdAt ? <AppText variant="caption" color="secondary">{formatCreatedAt(item.createdAt)}</AppText> : null}
          </View>
          <View
            style={{
              paddingVertical: theme.spacing.xxs,
              paddingHorizontal: theme.spacing.sm,
              borderRadius: theme.radiusUsage.statusPill,
              backgroundColor: statusSurface,
              borderWidth: 1,
              borderColor: statusColor,
              maxWidth: 132,
            }}
          >
            <AppText variant="caption" numberOfLines={1} style={{ color: statusColor }}>
              {needsAttention ? item.latenessLabel ?? "Needs attention" : item.statusLabel}
            </AppText>
          </View>
        </View>

        {item.activityText ? (
          <View
            style={{
              flexDirection: "row",
              alignItems: "flex-start",
              gap: theme.spacing.sm,
              padding: theme.spacing.md,
              borderRadius: theme.radiusUsage.input,
              backgroundColor: theme.colors.surfaceInteractive,
            }}
          >
            <View
              style={{
                width: 32,
                height: 32,
                borderRadius: theme.radius.radiusFull,
                backgroundColor: theme.colors.surfaceDefault,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <FuvayIcon size={22} accessibilityLabel="Fuvay assistant" />
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="caption" style={{ color: theme.colors.brandPrimaryStrong }}>NEXT STEP</AppText>
              <AppText variant="bodyStrong">{item.activityText}</AppText>
              {item.supportingText ? <AppText variant="caption" color="secondary">{item.supportingText}</AppText> : null}
            </View>
          </View>
        ) : null}

        <View accessibilityLabel={`Booking progress: ${item.statusLabel}`}>
          <View style={{ flexDirection: "row", gap: theme.spacing.xs }}>
            {RECEIPT_TIMELINE_STEPS.map(step => {
              const state = resolveTimelineStepState(step.key, item.stage);
              return (
                <View
                  key={step.key}
                  style={{
                    flex: 1,
                    height: 5,
                    borderRadius: theme.radius.radiusFull,
                    backgroundColor: state === "complete"
                      ? theme.colors.statusSuccess
                      : state === "active"
                        ? theme.colors.brandPrimary
                        : theme.colors.backgroundSunken,
                  }}
                />
              );
            })}
          </View>
          <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: theme.spacing.xs }}>
            <AppText variant="caption" color="tertiary">Request</AppText>
            <AppText variant="caption" color="tertiary">Professional</AppText>
            <AppText variant="caption" color="tertiary">Visit</AppText>
          </View>
        </View>

        {scheduleLabel || item.address.formatted || priceLabel ? (
          <View
            style={{
              gap: theme.spacing.sm,
              paddingTop: theme.spacing.sm,
              borderTopWidth: 1,
              borderTopColor: theme.colors.borderSubtle,
            }}
          >
            {scheduleLabel ? <FactRow icon="calendar-outline" label={scheduleLabel} /> : null}
            {item.address.formatted ? <FactRow icon="location-outline" label={item.address.formatted} /> : null}
            {priceLabel ? (
              <FactRow
                icon="wallet-outline"
                label={item.pricing.inspection ? `Inspection visit · ${priceLabel}` : `Service price · ${priceLabel}`}
              />
            ) : null}
          </View>
        ) : null}
      </View>

      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          gap: theme.spacing.sm,
          padding: theme.spacing.md,
          backgroundColor: theme.colors.backgroundSecondary,
          borderTopWidth: 1,
          borderTopColor: theme.colors.borderSubtle,
        }}
      >
        <View style={{ flex: 1 }}>
          <AppButton
            label="View booking"
            onPress={onViewDetails}
            fullWidth
            style={{ borderRadius: theme.radius.radiusFull }}
            trailingIcon={<Icon name="arrow-forward" size="compact" color={theme.colors.brandOnPrimary} decorative />}
          />
        </View>
        <Pressable
          onPress={onContactSupport}
          accessibilityRole="button"
          accessibilityLabel="Contact support"
          hitSlop={8}
          style={({ pressed }) => ({
            width: theme.touchTargets.minimum,
            height: theme.touchTargets.minimum,
            borderRadius: theme.radius.radiusFull,
            alignItems: "center",
            justifyContent: "center",
            borderWidth: 1,
            borderColor: theme.colors.borderDefault,
            backgroundColor: theme.colors.surfaceDefault,
            opacity: pressed ? 0.72 : 1,
          })}
        >
          <Icon name="headset-outline" size="standard" color={theme.colors.iconDefault} decorative />
        </Pressable>
      </View>
    </AppCard>
  );
}

function FactRow({ icon, label }: { icon: React.ComponentProps<typeof Icon>["name"]; label: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
      <Icon name={icon} size="compact" color={theme.colors.textSecondary} decorative />
      <AppText variant="bodySmall" color="secondary" numberOfLines={2} style={{ flex: 1 }}>{label}</AppText>
    </View>
  );
}
