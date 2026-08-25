import React from "react";
import { View, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { BotCard, BotPrimaryButton } from "./BotPrimitives";
import { BookingReviewSummary } from "../../domain/bookingReview";
import { formatMoney } from "../../domain/money";
import { resolveServicePriceDisplay } from "../../domain/servicePricing";

export interface PriceProviderCardProps {
  summary: BookingReviewSummary;
  confirming: boolean;
  onConfirm: () => void;
  confirmDisabledReason: string | null;
}

/**
 * Real matched provider + real resolved price, rendered as one card --
 * every field here is backend data already flowing through
 * useBookingReviewController's proven load sequence (checkServiceability
 * -> matchAndPrice -> confirmPriceChoice), just
 * restyled into the chat's dark card language. Nothing here is invented:
 * a bargain-available or unresolved price renders its own honest message
 * instead of a fabricated total.
 */
export function PriceProviderCard({ summary, confirming, onConfirm, confirmDisabledReason }: PriceProviderCardProps) {
  const BOT = useBotColors();
  const provider = summary.provider;
  return (
    <BotCard>
      {provider ? (
        <>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <View style={{ width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brandTint }}>
              <Ionicons name="construct" size={18} color={BOT.brand} />
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <Text style={{ fontSize: 16, fontWeight: "700", color: BOT.textPrimary }}>{provider.providerName}</Text>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginTop: 2 }}>
                {provider.rating != null ? (
                  <>
                    <Ionicons name="star" size={11} color={BOT.warning} />
                    <Text style={{ fontSize: 13, color: BOT.textTertiary }}>{provider.rating.toFixed(1)} · </Text>
                  </>
                ) : null}
                {provider.publicBadges.slice(0, 2).map((b, i) => (
                  <Text key={b.name} style={{ fontSize: 13, color: BOT.textTertiary }}>
                    {b.name}{i < Math.min(provider.publicBadges.length, 2) - 1 ? " · " : ""}
                  </Text>
                ))}
              </View>
            </View>
          </View>
        </>
      ) : (
        <Text style={{ fontSize: 15, color: BOT.textMuted }}>Matching you with an eligible professional…</Text>
      )}

      <View style={{ marginTop: 14, paddingTop: 14, borderTopWidth: 1, borderTopColor: BOT.borderSubtle, borderStyle: "dashed" }}>
        {summary.inspection ? (
          <>
            <Row label="Visit fee" value={formatMoney(summary.inspection.visitFee)} />
            <Row label="Repair price" value="After inspection" muted />
            <Row label="Payment" value="Pay provider directly" muted />
          </>
        ) : summary.priceState.kind === "valid" ? (
          <Row label="Estimated total" value={formatMoney(summary.priceState.amount)} big />
        ) : (
          <Text style={{ fontSize: 15, color: BOT.textMuted }}>
            {resolveServicePriceDisplay(summary.priceState).label}
          </Text>
        )}
      </View>

      <View style={{ marginTop: 16 }}>
        <BotPrimaryButton
          label={confirming ? "Confirming…" : "Confirm & Book"}
          onPress={onConfirm}
          disabled={!!confirmDisabledReason}
          loading={confirming}
        />
        {confirmDisabledReason ? (
          <Text style={{ fontSize: 12, color: BOT.textDim, marginTop: 6, textAlign: "center" }}>{confirmDisabledReason}</Text>
        ) : null}
      </View>
    </BotCard>
  );
}

function Row({ label, value, big, muted }: { label: string; value: string; big?: boolean; muted?: boolean }) {
  const BOT = useBotColors();
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
      <Text style={{ fontSize: 13, color: BOT.textMuted }}>{label}</Text>
      <Text style={{ fontSize: big ? 15 : 12, fontWeight: big ? "700" : "400", color: muted ? BOT.textSecondary : BOT.brandLight }}>
        {value}
      </Text>
    </View>
  );
}
