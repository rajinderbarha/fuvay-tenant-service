import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { CustomerBookingListItem } from "../../domain/bookingList";
import { BookingJourney } from "../booking-details/BookingJourney";
import { formatMoney } from "../../domain/money";
import { resolveAnswerFieldIcon } from "../../domain/answerFieldIcon";
import { formatCreatedAt } from "../../domain/dates";

export interface ActiveBookingCardProps {
  item: CustomerBookingListItem;
  onViewDetails: () => void;
  onContactSupport: () => void;
}

/** Three answer cells per row, matching the design's grid. */
const COLUMNS = 3;

/** Adapts to whatever real fields the booking actually carries -- never
 * hardcodes AC/LG/Split AC (spec section 6). Same status/pricing adapters
 * as Booking Details, never re-derived here. */
export function ActiveBookingCard({ item, onViewDetails, onContactSupport }: ActiveBookingCardProps) {
  const { theme } = useTheme();

  // "text" is the free-text input_type (admin_catalog INPUT_TYPES) -- it
  // reads as a note, so the design gives it its own box rather than a
  // cell in the answer grid. Everything else is a chosen value.
  const noteField = item.summaryFields.find(f => f.questionType === "text") ?? null;
  const gridFields = item.summaryFields.filter(f => f.questionType !== "text");

  const rows: typeof gridFields[] = [];
  for (let i = 0; i < gridFields.length; i += COLUMNS) {
    rows.push(gridFields.slice(i, i + COLUMNS));
  }

  const divider = (
    <View style={{ height: 1, backgroundColor: theme.colors.borderSubtle, marginHorizontal: -theme.spacing.base }} />
  );

  return (
    <AppCard style={{ gap: theme.spacing.sm }}>
      {/* Header: service, reference, status pill and when it was raised. */}
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", gap: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, flex: 1, minWidth: 0 }}>
          <View
            style={{
              width: 44, height: 44, borderRadius: theme.radiusUsage.card,
              backgroundColor: theme.colors.surfaceInteractive,
              alignItems: "center", justifyContent: "center",
            }}
          >
            <Icon name="snow-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1, minWidth: 0 }}>
            {item.serviceName ? <AppText variant="bodyStrong" numberOfLines={1}>{item.serviceName}</AppText> : null}
            {item.bookingNumber ? <AppText variant="caption" color="tertiary">{item.bookingNumber}</AppText> : null}
          </View>
        </View>
        <View style={{ alignItems: "flex-end", gap: theme.spacing.xxs }}>
          {/* Outline pill per the design, not a filled badge. */}
          <View
            style={{
              paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
              borderRadius: theme.radiusUsage.statusPill,
              borderWidth: 1,
              borderColor: item.stage === "unknown" ? theme.colors.borderDefault : theme.colors.statusSuccess,
              backgroundColor: item.stage === "unknown" ? theme.colors.surfaceSecondary : theme.colors.statusSuccessSurface,
            }}
          >
            <AppText
              variant="caption"
              style={{ color: item.stage === "unknown" ? theme.colors.textSecondary : theme.colors.statusSuccess }}
            >
              {item.statusLabel}
            </AppText>
          </View>
          {item.createdAt ? (
            <AppText variant="caption" color="tertiary">{formatCreatedAt(item.createdAt)}</AppText>
          ) : null}
        </View>
      </View>

      {item.activityText ? (
        <>
          {divider}
          <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
            <View
              style={{
                width: 40, height: 40, borderRadius: theme.radiusUsage.card,
                backgroundColor: theme.colors.surfaceInteractive,
                alignItems: "center", justifyContent: "center",
              }}
            >
              <Icon name="sparkles" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">{item.activityText}</AppText>
              {item.supportingText ? <AppText variant="bodySmall" color="secondary">{item.supportingText}</AppText> : null}
            </View>
          </View>
        </>
      ) : null}

      <BookingJourney stage={item.stage} bare />

      {/* Answer grid: cells divided by hairlines, edge-to-edge like the
          design. Rows are whatever the booking really answered -- a
          category with two answers gets one short row, not padding. */}
      {rows.length > 0 ? (
        <>
          {divider}
          <View style={{ marginHorizontal: -theme.spacing.base }}>
            {rows.map((row, rowIndex) => (
              <View
                key={rowIndex}
                style={{
                  flexDirection: "row",
                  borderTopWidth: rowIndex === 0 ? 0 : 1,
                  borderTopColor: theme.colors.borderSubtle,
                }}
              >
                {row.map((f, colIndex) => (
                  <View
                    key={f.key}
                    style={{
                      flex: 1, minWidth: 0,
                      flexDirection: "row", alignItems: "center", gap: theme.spacing.xs,
                      paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.sm,
                      borderLeftWidth: colIndex === 0 ? 0 : 1,
                      borderLeftColor: theme.colors.borderSubtle,
                    }}
                  >
                    <Icon
                      name={resolveAnswerFieldIcon(f.value, f.label)}
                      size="compact"
                      color={theme.colors.iconDefault}
                      decorative
                    />
                    <AppText variant="caption" numberOfLines={1} style={{ flex: 1 }}>{f.value}</AppText>
                  </View>
                ))}
                {/* Keep the last row's cells the same width as a full row. */}
                {row.length < COLUMNS
                  ? Array.from({ length: COLUMNS - row.length }, (_, i) => <View key={`pad-${i}`} style={{ flex: 1 }} />)
                  : null}
              </View>
            ))}
          </View>
        </>
      ) : null}

      {/* The free-text answer the booking assistant collected -- a
          paragraph the customer typed once, captured into the immutable
          answer_snapshot at finalize() time. It is display-only by
          nature: nothing updates it after the booking exists, so the
          design's "Type here…" input is rendered as the text itself.
          Omitted entirely when the flow never asked for one, rather than
          leaving an empty box on the card. */}
      {noteField ? (
        <>
          {divider}
          <View>
            {/* The design's fixed heading, not the raw question label --
                the real catalog question is a full sentence ("Please share
                any additional details about the issue."), which reads as
                a prompt rather than a section title on a summary card. */}
            <AppText variant="bodySmall" color="secondary">Additional Detail</AppText>
            <View
              style={{
                marginTop: theme.spacing.xxs, padding: theme.spacing.sm,
                borderRadius: theme.radiusUsage.input,
                borderWidth: 1, borderColor: theme.colors.borderSubtle,
                backgroundColor: theme.colors.surfaceSecondary,
              }}
            >
              <AppText variant="bodySmall">{noteField.value}</AppText>
            </View>
          </View>
        </>
      ) : null}

      {item.address.formatted ? (
        <>
          {divider}
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
            <Icon name="location-outline" size="compact" color={theme.colors.textSecondary} decorative />
            <AppText variant="bodySmall" numberOfLines={2} style={{ flex: 1 }}>{item.address.formatted}</AppText>
          </View>
        </>
      ) : null}

      {item.pricing.inspection ? (
        <>
          {divider}
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: theme.spacing.sm }}>
            <View>
              <AppText variant="caption" color="tertiary">Inspection visit</AppText>
              <AppText variant="bodyStrong">{formatMoney(item.pricing.inspection.visitFee)}</AppText>
            </View>
            <View style={{ flexDirection: "row", gap: theme.spacing.xs, flexShrink: 1 }}>
              <View
                style={{
                  paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
                  borderRadius: theme.radiusUsage.statusPill,
                  borderWidth: 1, borderColor: theme.colors.statusSuccess,
                  backgroundColor: theme.colors.statusSuccessSurface,
                }}
              >
                <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>Backend confirmed</AppText>
              </View>
              <View
                style={{
                  paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
                  borderRadius: theme.radiusUsage.statusPill,
                  borderWidth: 1, borderColor: theme.colors.borderDefault,
                }}
              >
                <AppText variant="caption" color="secondary">Pay provider directly</AppText>
              </View>
            </View>
          </View>
        </>
      ) : item.pricing.state.kind === "valid" ? (
        <>
          {divider}
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <AppText variant="bodySmall" color="secondary">Price</AppText>
            <AppText variant="bodyStrong">{formatMoney(item.pricing.state.amount)}</AppText>
          </View>
        </>
      ) : null}

      <View style={{ gap: theme.spacing.sm }}>
        <AppButton
          label="View details"
          onPress={onViewDetails}
          fullWidth
          style={{ borderRadius: theme.radius.radiusFull }}
          trailingIcon={<Icon name="arrow-forward" size="compact" color={theme.colors.brandOnPrimary} decorative />}
        />
        <AppButton
          label="Contact support"
          onPress={onContactSupport}
          tone="secondary"
          fullWidth
          style={{ borderRadius: theme.radius.radiusFull, borderColor: theme.colors.brandPrimary, backgroundColor: "transparent" }}
          trailingIcon={<Icon name="arrow-forward" size="compact" color={theme.colors.textPrimary} decorative />}
        />
      </View>
    </AppCard>
  );
}
