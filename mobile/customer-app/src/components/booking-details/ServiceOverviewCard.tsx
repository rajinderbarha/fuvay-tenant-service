import React, { useState } from "react";
import { View, Modal, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";
import { CustomerBookingDetails } from "../../domain/customerBookingDetails";
import { resolveAnswerFieldIcon } from "../../domain/answerFieldIcon";
import { formatCreatedAt, ServerTimestamp } from "../../domain/dates";

export interface ServiceOverviewCardProps {
  service: CustomerBookingDetails["service"];
  bookingNumber: string | null;
  createdAt: ServerTimestamp | null;
}

const COLUMNS = 2;

/** Renders whatever answers the finalized booking actually carries --
 * never a hardcoded AC-only field list (spec section 5: "The screen must
 * support categories with different questions"). Tapping the header's
 * timestamp opens a read-only sheet with every answer; there is no path
 * back into the editable assistant flow from here.
 *
 * Icons per cell are the same wording-derived glyphs used on the My
 * Bookings list card (answerFieldIcon.ts) -- one icon system, not a
 * second invented for this screen. */
export function ServiceOverviewCard({ service, bookingNumber, createdAt }: ServiceOverviewCardProps) {
  const { theme } = useTheme();
  const [open, setOpen] = useState(false);

  const rows: typeof service.answers[] = [];
  for (let i = 0; i < service.answers.length; i += COLUMNS) {
    rows.push(service.answers.slice(i, i + COLUMNS));
  }

  return (
    <AppCard style={{ padding: 0, overflow: "hidden" }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, padding: theme.spacing.base }}>
        <View
          style={{
            width: 44, height: 44, borderRadius: theme.radiusUsage.card,
            backgroundColor: theme.colors.surfaceInteractive,
            alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}
        >
          <Icon name="snow-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
        </View>
        <View style={{ flex: 1, minWidth: 0 }}>
          {service.name ? <AppText variant="bodyStrong" numberOfLines={1}>{service.name}</AppText> : null}
          {bookingNumber ? <AppText variant="caption" color="tertiary">{bookingNumber}</AppText> : null}
        </View>
        {createdAt ? (
          <Pressable
            onPress={() => setOpen(true)}
            accessibilityRole="button"
            accessibilityLabel={`Created ${formatCreatedAt(createdAt)}. View all answers.`}
            style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, flexShrink: 0 }}
          >
            <AppText variant="labelStrong" color="link" numberOfLines={1}>{formatCreatedAt(createdAt)}</AppText>
            <Icon name="chevron-forward" size="compact" color={theme.colors.brandPrimary} decorative />
          </Pressable>
        ) : service.answers.length > 0 ? (
          <AppText variant="labelStrong" color="link" onPress={() => setOpen(true)}>View all answers</AppText>
        ) : null}
      </View>

      {service.inspectionRequired || service.issueSummary ? (
        <View style={{ paddingHorizontal: theme.spacing.base, paddingBottom: theme.spacing.sm }}>
          {service.inspectionRequired ? <AppText variant="bodySmall" color="secondary">Inspection-based service</AppText> : null}
          {service.issueSummary ? <AppText variant="body">Issue: {service.issueSummary}</AppText> : null}
        </View>
      ) : null}

      {rows.length > 0 ? (
        <View style={{ borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
          {rows.map((row, rowIndex) => (
            <View
              key={rowIndex}
              style={{
                flexDirection: "row",
                borderTopWidth: rowIndex === 0 ? 0 : 1,
                borderTopColor: theme.colors.borderSubtle,
              }}
            >
              {row.map((a, colIndex) => (
                <View
                  key={a.id}
                  style={{
                    flex: 1, minWidth: 0,
                    flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.xs,
                    padding: theme.spacing.base,
                    borderLeftWidth: colIndex === 0 ? 0 : 1,
                    borderLeftColor: theme.colors.borderSubtle,
                  }}
                >
                  <Icon name={resolveAnswerFieldIcon(a.value, a.label)} size="compact" color={theme.colors.iconDefault} decorative />
                  <View style={{ flex: 1, minWidth: 0 }}>
                    <AppText variant="caption" color="tertiary" numberOfLines={1}>{a.label}</AppText>
                    <AppText variant="bodySmall" numberOfLines={1}>{a.value}</AppText>
                  </View>
                </View>
              ))}
              {row.length < COLUMNS ? <View style={{ flex: 1 }} /> : null}
            </View>
          ))}
        </View>
      ) : null}

      <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
          <View style={{ backgroundColor: theme.colors.surfaceDefault, borderTopLeftRadius: theme.radiusUsage.card, borderTopRightRadius: theme.radiusUsage.card, padding: theme.spacing.base, gap: theme.spacing.xs }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <AppText variant="headingSmall">All answers</AppText>
              <AppIconButton name="close" onPress={() => setOpen(false)} accessibilityLabel="Close" />
            </View>
            {service.answers.map(a => (
              <View key={a.id} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.xxs }}>
                <AppText variant="body" color="secondary">{a.label}</AppText>
                <AppText variant="body">{a.value}</AppText>
              </View>
            ))}
          </View>
        </View>
      </Modal>
    </AppCard>
  );
}
