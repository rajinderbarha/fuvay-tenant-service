import React from "react";
import { View, Text, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { RequestSummaryCard } from "./RequestSummaryCard";
import { ProviderTrustCard } from "./ProviderTrustCard";
import { FeeAssuranceCard } from "./FeeAssuranceCard";
import { BookingReviewSummary } from "../../domain/bookingReview";

export interface ReviewSummaryPanelProps {
  summary: BookingReviewSummary;
  slotLabel: string | null;
  confirming: boolean;
  confirmDisabledReason: string | null;
  onConfirm: () => void;
  /** Jump back to the slot picker. The customer can still change their mind at
   * the last moment without restarting the whole conversation. */
  onEditSlot: () => void;
  /** Jump back to the photo step. */
  onEditPhotos: () => void;
}

/**
 * The whole review, in ONE box.
 *
 * It was previously four separate cards stacked down the chat (request,
 * technician, money, confirm), which read as four unrelated things rather than
 * one decision. A single panel with internal dividers is both calmer to look at
 * and truer to what is happening: these are sections of one agreement.
 *
 * Every section still renders only when it has real data, and each is the same
 * component used standalone elsewhere -- passed `embedded` so it contributes its
 * content without its own card chrome.
 */
export function ReviewSummaryPanel({
  summary, slotLabel, confirming, confirmDisabledReason,
  onConfirm, onEditSlot, onEditPhotos,
}: ReviewSummaryPanelProps) {
  const BOT = useBotColors();
  const disabled = !!confirmDisabledReason || confirming;

  return (
    <View
      style={{
        marginLeft: 36, borderRadius: 20, overflow: "hidden",
        backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle,
      }}
    >
      <View style={{ padding: 16 }}>
        <RequestSummaryCard summary={summary} slotLabel={slotLabel} embedded />
        <EditRow
          BOT={BOT}
          items={[
            { label: slotLabel ? "Change time" : "Choose a time", icon: "time-outline", onPress: onEditSlot },
            {
              label: summary.photoUrls.length > 0 ? "Edit photos" : "Add a photo",
              icon: "camera-outline",
              onPress: onEditPhotos,
            },
          ]}
        />
      </View>

      {summary.provider ? (
        <>
          <Divider BOT={BOT} />
          <View style={{ padding: 16 }}>
            <ProviderTrustCard provider={summary.provider} embedded />
          </View>
        </>
      ) : null}

      {summary.inspection || (summary.isEmergency && summary.emergencySurcharge) ? (
        <>
          <Divider BOT={BOT} />
          {/* Tinted so the money section reads as the important one without
              becoming a separate floating card. */}
          <View style={{ padding: 16, backgroundColor: BOT.successBg }}>
            <FeeAssuranceCard
              inspection={summary.inspection}
              emergencySurcharge={summary.isEmergency ? summary.emergencySurcharge : null}
              embedded
            />
          </View>
        </>
      ) : null}

      <Divider BOT={BOT} />
      <View style={{ padding: 16 }}>
        <Pressable
          onPress={onConfirm}
          disabled={disabled}
          accessibilityRole="button"
          accessibilityLabel={confirming ? "Confirming" : "Confirm and book"}
          accessibilityState={{ disabled }}
          style={{
            height: 52, borderRadius: 16, alignItems: "center", justifyContent: "center",
            flexDirection: "row", gap: 8,
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

        {confirmDisabledReason ? (
          <Text style={{ fontSize: 13, color: BOT.textDim, marginTop: 8, textAlign: "center" }}>
            {confirmDisabledReason}
          </Text>
        ) : (
          <Text style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 8, textAlign: "center" }}>
            You can cancel free of charge before the technician sets off.
          </Text>
        )}
      </View>
    </View>
  );
}

function Divider({ BOT }: { BOT: ReturnType<typeof useBotColors> }) {
  return <View style={{ height: 1, backgroundColor: BOT.borderSubtle }} />;
}

/** Inline "change this" affordances. Placed with the recap rather than at the
 * bottom, so they read as editing the thing above them rather than as extra
 * actions competing with Confirm. */
function EditRow({
  BOT, items,
}: {
  BOT: ReturnType<typeof useBotColors>;
  items: { label: string; icon: React.ComponentProps<typeof Ionicons>["name"]; onPress: () => void }[];
}) {
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
      {items.map(item => (
        <Pressable
          key={item.label}
          onPress={item.onPress}
          accessibilityRole="button"
          accessibilityLabel={item.label}
          style={{
            flexDirection: "row", alignItems: "center", gap: 6,
            paddingHorizontal: 12, height: 36, borderRadius: 18,
            backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.border,
          }}
        >
          <Ionicons name={item.icon} size={14} color={BOT.textSecondary} />
          <Text style={{ fontSize: 13, fontWeight: "600", color: BOT.textSecondary }}>
            {item.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}
