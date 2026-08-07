import React from "react";
import { View, Text, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";

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
    <View style={{ marginLeft: 36, borderRadius: 20, padding: 20, alignItems: "center", backgroundColor: BOT.successBg, borderWidth: 1, borderColor: BOT.successBorder }}>
      <View style={{ width: 56, height: 56, borderRadius: 28, alignItems: "center", justifyContent: "center", marginBottom: 12, backgroundColor: BOT.successTint }}>
        <Ionicons name="checkmark-circle" size={28} color={BOT.success} />
      </View>
      <Text style={{ fontSize: 16, fontWeight: "700", color: BOT.textPrimary }}>Booking Confirmed</Text>
      <Text style={{ fontSize: 11.5, color: BOT.success, marginTop: 4 }}>Booking {bookingNumber}</Text>
      {providerName ? (
        <Text style={{ fontSize: 12.5, color: BOT.textSecondary, marginTop: 10, textAlign: "center" }}>
          {providerName} has been notified and will be in touch.
        </Text>
      ) : (
        <Text style={{ fontSize: 12.5, color: BOT.textSecondary, marginTop: 10, textAlign: "center" }}>
          We&apos;ll notify you as soon as a professional is assigned.
        </Text>
      )}
      <View style={{ marginTop: 16, width: "100%" }}>
        <Pressable
          onPress={onTrackBooking}
          accessibilityRole="button"
          accessibilityLabel="Track this booking"
          style={{ height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand }}
        >
          <Text style={{ fontSize: 12.5, fontWeight: "700", color: BOT.bubbleOnBrand }}>Track Booking</Text>
        </Pressable>
      </View>
    </View>
  );
}
