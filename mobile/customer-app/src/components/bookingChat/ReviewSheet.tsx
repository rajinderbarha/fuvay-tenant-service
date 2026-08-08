import React, { useEffect, useRef } from "react";
import { View, Text, Pressable, ScrollView, Animated, Easing } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useReducedMotion } from "../../design-system/theme";
import { useBotColors } from "./botTheme";
import { RequestSummaryCard } from "./RequestSummaryCard";
import { ProviderTrustCard } from "./ProviderTrustCard";
import { FeeAssuranceCard } from "./FeeAssuranceCard";
import { BookingReviewSummary } from "../../domain/bookingReview";
import { formatMoney } from "../../domain/money";

export interface ReviewSheetProps {
  summary: BookingReviewSummary;
  slotLabel: string | null;
  confirming: boolean;
  confirmDisabledReason: string | null;
  onConfirm: () => void;
  onEditSlot: () => void;
  onEditPhotos: () => void;
  /** Returns to the conversation without booking. */
  onClose: () => void;
}

/**
 * The review, as a full-screen sheet rather than a card in the chat.
 *
 * Confirming a booking is the one irreversible step in the flow, and it was
 * competing for attention with a scrolling transcript, a stage tracker and a
 * composer. A dedicated surface gives it a fixed header, one scrolling column of
 * sections, and a pinned action bar -- so the price and the button are always
 * visible instead of being somewhere in the middle of a chat log.
 *
 * Layout discipline: a single content column at one padding, sections separated
 * by full-bleed dividers (never nested cards-within-cards), one accent colour for
 * money, and exactly one primary action on screen.
 */
export function ReviewSheet({
  summary, slotLabel, confirming, confirmDisabledReason,
  onConfirm, onEditSlot, onEditPhotos, onClose,
}: ReviewSheetProps) {
  const BOT = useBotColors();
  const reduced = useReducedMotion();
  const rise = useRef(new Animated.Value(reduced ? 1 : 0)).current;

  useEffect(() => {
    if (reduced) return;
    Animated.timing(rise, {
      toValue: 1, duration: 320, easing: Easing.out(Easing.cubic), useNativeDriver: true,
    }).start();
  }, [rise, reduced]);

  const disabled = !!confirmDisabledReason || confirming;
  const payable = summary.inspection ? formatMoney(summary.inspection.visitFee) : null;

  return (
    <Animated.View
      style={{
        flex: 1,
        backgroundColor: BOT.bg,
        opacity: rise,
        transform: reduced
          ? undefined
          : [{ translateY: rise.interpolate({ inputRange: [0, 1], outputRange: [24, 0] }) }],
      }}
    >
      {/* Fixed header -- the customer always knows what this screen is and how
          to leave it without booking. */}
      <View
        style={{
          flexDirection: "row", alignItems: "center", gap: 12,
          paddingHorizontal: 20, paddingTop: 8, paddingBottom: 14,
          borderBottomWidth: 1, borderBottomColor: BOT.borderSubtle,
        }}
      >
        <Pressable
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="Back to chat"
          hitSlop={8}
          style={{
            width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center",
            backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.border,
          }}
        >
          <Ionicons name="chevron-back" size={17} color={BOT.textTertiary} />
        </Pressable>
        <View style={{ flex: 1, minWidth: 0 }}>
          <Text style={{ fontSize: 17, fontWeight: "700", color: BOT.textPrimary }}>
            Review &amp; confirm
          </Text>
          <Text style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 1 }}>
            Check the details before you book
          </Text>
        </View>
        <View
          style={{
            flexDirection: "row", alignItems: "center", gap: 5,
            paddingHorizontal: 10, height: 28, borderRadius: 14, backgroundColor: BOT.successBg,
          }}
        >
          <Ionicons name="shield-checkmark" size={12} color={BOT.success} />
          <Text style={{ fontSize: 12, fontWeight: "700", color: BOT.success }}>Protected</Text>
        </View>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingBottom: 28 }}
        showsVerticalScrollIndicator={false}
      >
        <Section BOT={BOT}>
          <RequestSummaryCard summary={summary} slotLabel={slotLabel} embedded />
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 16 }}>
            <EditChip
              BOT={BOT}
              icon="time-outline"
              label={slotLabel ? "Change time" : "Choose a time"}
              onPress={onEditSlot}
            />
            <EditChip
              BOT={BOT}
              icon="camera-outline"
              label={summary.photoUrls.length > 0 ? "Edit photos" : "Add a photo"}
              onPress={onEditPhotos}
            />
          </View>
        </Section>

        {summary.provider ? (
          <>
            <Divider BOT={BOT} />
            <Section BOT={BOT}>
              <ProviderTrustCard provider={summary.provider} embedded />
            </Section>
          </>
        ) : null}

        {summary.inspection || (summary.isEmergency && summary.emergencySurcharge) ? (
          <>
            <Divider BOT={BOT} />
            {/* The one tinted section: money is the thing a customer re-reads. */}
            <Section BOT={BOT} tint={BOT.successBg}>
              <FeeAssuranceCard
                inspection={summary.inspection}
                emergencySurcharge={summary.isEmergency ? summary.emergencySurcharge : null}
                embedded
              />
            </Section>
          </>
        ) : null}
      </ScrollView>

      {/* Pinned action bar: the total and the single primary action stay visible
          however long the details column gets. */}
      <View
        style={{
          paddingHorizontal: 20, paddingTop: 14, paddingBottom: 16,
          borderTopWidth: 1, borderTopColor: BOT.borderSubtle,
          backgroundColor: BOT.bgComposer,
        }}
      >
        {payable ? (
          <View
            style={{
              flexDirection: "row", alignItems: "center", justifyContent: "space-between",
              marginBottom: 12,
            }}
          >
            <Text style={{ fontSize: 15, color: BOT.textTertiary }}>Due at the visit</Text>
            <Text style={{ fontSize: 20, fontWeight: "800", color: BOT.textPrimary }}>{payable}</Text>
          </View>
        ) : null}

        <Pressable
          onPress={onConfirm}
          disabled={disabled}
          accessibilityRole="button"
          accessibilityLabel={confirming ? "Confirming" : "Confirm and book"}
          accessibilityState={{ disabled }}
          style={{
            height: 54, borderRadius: 16, flexDirection: "row", gap: 8,
            alignItems: "center", justifyContent: "center",
            backgroundColor: disabled && !confirming ? BOT.surfaceRaised : BOT.brand,
            opacity: disabled && !confirming ? 0.6 : 1,
          }}
        >
          {!confirming ? <Ionicons name="lock-closed" size={15} color={BOT.bubbleOnBrand} /> : null}
          <Text
            style={{
              fontSize: 16, fontWeight: "700",
              color: disabled && !confirming ? BOT.textDim : BOT.bubbleOnBrand,
            }}
          >
            {confirming ? "Confirming…" : "Confirm & Book"}
          </Text>
        </Pressable>

        <Text style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 10, textAlign: "center" }}>
          {confirmDisabledReason ?? "Free cancellation before the technician sets off."}
        </Text>
      </View>
    </Animated.View>
  );
}

function Section({
  BOT, children, tint,
}: { BOT: ReturnType<typeof useBotColors>; children: React.ReactNode; tint?: string }) {
  return (
    <View style={{ paddingHorizontal: 20, paddingVertical: 18, backgroundColor: tint ?? BOT.bg }}>
      {children}
    </View>
  );
}

/** Full-bleed, so sections read as one document rather than stacked cards. */
function Divider({ BOT }: { BOT: ReturnType<typeof useBotColors> }) {
  return <View style={{ height: 1, backgroundColor: BOT.borderSubtle }} />;
}

function EditChip({
  BOT, icon, label, onPress,
}: {
  BOT: ReturnType<typeof useBotColors>;
  icon: React.ComponentProps<typeof Ionicons>["name"];
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={{
        flexDirection: "row", alignItems: "center", gap: 6,
        paddingHorizontal: 14, height: 38, borderRadius: 19,
        backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.border,
      }}
    >
      <Ionicons name={icon} size={14} color={BOT.textSecondary} />
      <Text style={{ fontSize: 13, fontWeight: "600", color: BOT.textSecondary }}>{label}</Text>
    </Pressable>
  );
}
