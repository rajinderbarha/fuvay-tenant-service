import React, { useState } from "react";
import { View, Modal, Pressable, ScrollView, AccessibilityInfo } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import * as Clipboard from "expo-clipboard";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";
import { CustomerBookingDetails } from "../../domain/customerBookingDetails";
import { formatCreatedAt, ServerTimestamp } from "../../domain/dates";

export interface ServiceOverviewCardProps {
  service: CustomerBookingDetails["service"];
  bookingNumber: string | null;
  createdAt: ServerTimestamp | null;
}

const COLUMNS = 2;

/** Renders whatever answers the finalized booking actually carries --
 * never a hardcoded AC-only field list (spec section 5: "The screen must
 * support categories with different questions"). "View all answers" opens
 * a read-only sheet; there is no path back into the editable assistant
 * flow from here.
 *
 * The booking id + copy action live here rather than in the header --
 * this is the section actually ABOUT the booked service, so its own
 * identifier reads more naturally next to the service name than sitting
 * above the status card.
 *
 * NO ICONS on answer rows. They were wording-derived glyphs, which meant a
 * different icon for the same field depending on how it was phrased -- and they
 * decorated text the customer wrote themselves. Dropping them also removes a
 * per-row glyph resolution from a list that can be long. */
export function ServiceOverviewCard({ service, bookingNumber, createdAt }: ServiceOverviewCardProps) {
  const { theme } = useTheme();
  // The sheet is a Modal, so it sits outside any screen-level safe area and has
  // to clear the home indicator itself.
  const insets = useSafeAreaInsets();
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!bookingNumber) return;
    await Clipboard.setStringAsync(bookingNumber);
    setCopied(true);
    AccessibilityInfo.announceForAccessibility("Booking ID copied");
    setTimeout(() => setCopied(false), 2000);
  }

  const rows: typeof service.answers[] = [];
  for (let i = 0; i < service.answers.length; i += COLUMNS) {
    rows.push(service.answers.slice(i, i + COLUMNS));
  }

  return (
    <AppCard style={{ padding: 0, overflow: "hidden" }}>
      <View style={{ padding: theme.spacing.base, paddingBottom: theme.spacing.sm }}>
        <AppText variant="labelStrong" color="secondary">Service overview</AppText>
      </View>

      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm, paddingHorizontal: theme.spacing.base, paddingBottom: theme.spacing.base }}>
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
          {bookingNumber ? (
            <Pressable
              onPress={handleCopy}
              accessibilityRole="button"
              accessibilityLabel={`Booking ${bookingNumber}. Copy to clipboard.`}
              style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}
            >
              <AppText variant="caption" color="secondary">{bookingNumber} {copied ? "· Copied" : ""}</AppText>
              <Icon name={copied ? "checkmark" : "copy-outline"} size="compact" color={theme.colors.textSecondary} decorative />
            </Pressable>
          ) : null}
          {service.inspectionRequired ? <AppText variant="caption" color="tertiary">Inspection-based service</AppText> : null}
        </View>
        <View style={{ alignItems: "flex-end", flexShrink: 0, gap: theme.spacing.xxs }}>
          {service.answers.length > 0 ? (
            <Pressable
              onPress={() => setOpen(true)}
              accessibilityRole="button"
              accessibilityLabel="View all answers"
              style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}
            >
              <AppText variant="labelStrong" color="link" numberOfLines={1}>View all answers</AppText>
              <Icon name="chevron-forward" size="compact" color={theme.colors.brandPrimary} decorative />
            </Pressable>
          ) : null}
          {createdAt ? (
            <AppText variant="caption" color="tertiary" numberOfLines={1}>{formatCreatedAt(createdAt)}</AppText>
          ) : null}
        </View>
      </View>

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

      {/* The answers sheet.
       *
       * Was a label/value ROW per answer with `justifyContent: "space-between"`
       * and no flex: a long question and a long answer pushed each other off
       * both edges of the screen, unreadable and unwrappable. Nor could the
       * sheet scroll or bound its height, so a booking with many answers ran off
       * the bottom of the display.
       *
       * Now: label above value, both allowed to wrap, one divider between rows,
       * a scrolling body capped at 80% of the screen, and a bottom inset so the
       * last answer clears the home indicator. */}
      <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
          {/* Tapping the dimmed area behind the sheet closes it. */}
          <Pressable
            style={{ flex: 1 }}
            accessibilityRole="button"
            accessibilityLabel="Close all answers"
            onPress={() => setOpen(false)}
          />
          <View
            style={{
              maxHeight: "80%",
              backgroundColor: theme.colors.surfaceDefault,
              borderTopLeftRadius: theme.radiusUsage.card,
              borderTopRightRadius: theme.radiusUsage.card,
            }}
          >
            <View
              style={{
                flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
                paddingHorizontal: theme.spacing.base,
                paddingTop: theme.spacing.base, paddingBottom: theme.spacing.sm,
                borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle,
              }}
            >
              <View style={{ flex: 1, minWidth: 0 }}>
                <AppText variant="headingSmall">Your answers</AppText>
                <AppText variant="caption" color="tertiary">
                  {service.answers.length} {service.answers.length === 1 ? "detail" : "details"} you told us
                </AppText>
              </View>
              <AppIconButton name="close" onPress={() => setOpen(false)} accessibilityLabel="Close" />
            </View>

            <ScrollView
              style={{ flexGrow: 0 }}
              contentContainerStyle={{ paddingBottom: theme.spacing.base + insets.bottom }}
              showsVerticalScrollIndicator={false}
            >
              {service.answers.map((a, index) => (
                <View
                  key={a.id}
                  style={{
                    flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm,
                    paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
                    borderTopWidth: index === 0 ? 0 : 1,
                    borderTopColor: theme.colors.borderSubtle,
                  }}
                >
                  {/* minWidth: 0 is what actually lets long text wrap inside a
                      row instead of overflowing it. */}
                  <View style={{ flex: 1, minWidth: 0, gap: 2 }}>
                    <AppText variant="caption" color="tertiary">{a.label}</AppText>
                    <AppText variant="body">{a.value}</AppText>
                  </View>
                </View>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </AppCard>
  );
}
