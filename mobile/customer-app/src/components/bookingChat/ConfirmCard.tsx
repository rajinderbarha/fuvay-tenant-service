import React from "react";
import { View, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { BotText } from "./BotText";
import { BOT_GUTTER } from "./BotPrimitives";

export interface ConfirmCardProps {
  bookingNumber: string;
  providerName: string | null;
  onTrackBooking: () => void;
}

/** Only real, backend-confirmed fields -- `bookingNumber` is the real
 * `booking_number` from confirmDraft's response, never a client-generated
 * id. No ETA/arrival time is invented here (see PromisedSlotCard's own
 * documented reason no such field exists anywhere in the backend). */
export function ConfirmCard({ bookingNumber, providerName, onTrackBooking }: ConfirmCardProps) {
  const BOT = useBotColors();
  return (
    <View style={{ marginLeft: BOT_GUTTER, borderRadius: 20, padding: 20, alignItems: "center", backgroundColor: BOT.successBg, borderWidth: 1, borderColor: BOT.successBorder }}>
      <View style={{ width: 56, height: 56, borderRadius: 28, alignItems: "center", justifyContent: "center", marginBottom: 12, backgroundColor: BOT.successTint }}>
        <Ionicons name="checkmark-circle" size={28} color={BOT.success} />
      </View>
      <BotText style={{ fontSize: 18, fontWeight: "700", color: BOT.textPrimary }}>Booking Confirmed</BotText>
      <BotText style={{ fontSize: 13, color: BOT.success, marginTop: 4 }}>Booking {bookingNumber}</BotText>
      {providerName ? (
        <BotText style={{ fontSize: 15, color: BOT.textSecondary, marginTop: 10, textAlign: "center" }}>
          {providerName} has been notified and will be in touch.
        </BotText>
      ) : (
        <BotText style={{ fontSize: 15, color: BOT.textSecondary, marginTop: 10, textAlign: "center" }}>
          We&apos;ll notify you as soon as a professional is assigned.
        </BotText>
      )}
      <View style={{ marginTop: 16, width: "100%" }}>
        <Pressable
          onPress={onTrackBooking}
          accessibilityRole="button"
          accessibilityLabel="Track this booking"
          style={{ height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand }}
        >
          <BotText style={{ fontSize: 15, fontWeight: "700", color: BOT.bubbleOnBrand }}>Track Booking</BotText>
        </Pressable>
      </View>
    </View>
  );
}
