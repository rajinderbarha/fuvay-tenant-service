import React, { useEffect, useMemo, useRef } from "react";
import { View, Text, Pressable, Animated, Easing, Dimensions, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useReducedMotion } from "../../design-system/theme";
import { useBotColors } from "./botTheme";

export interface BookingConfirmedOverlayProps {
  bookingNumber: string;
  providerName: string | null;
  /** The slot the provider committed to, already formatted for display. Null
   * when no time could be promised -- the card then says the provider will make
   * contact, rather than inventing an arrival time. */
  slotLabel: string | null;
  /** Formatted amount due for the visit, or null when nothing is payable up
   * front. Never a fabricated total. */
  amountLabel: string | null;
  /** True when the visit fee is credited against the repair if the customer
   * goes ahead -- asserted by the backend, not assumed here. */
  feeCreditedAgainstWork: boolean;
  onTrackBooking: () => void;
  onDone: () => void;
}

const CONFETTI_COUNT = 26;
const CONFETTI_MS = 2600;

/**
 * The moment the booking lands. A full-bleed confirmation rather than another
 * chat card, because this is the one screen a customer screenshots and comes
 * back to -- it should feel like something happened.
 *
 * Everything stated is real: the backend's own booking number, the matched
 * provider's name, the slot they committed to, and the amount from the price
 * snapshot. Where a value is missing the line is omitted rather than filled
 * with a plausible-sounding placeholder.
 *
 * Confetti is decorative only and fully skipped under reduced-motion.
 */
export function BookingConfirmedOverlay({
  bookingNumber, providerName, slotLabel, amountLabel,
  feeCreditedAgainstWork, onTrackBooking, onDone,
}: BookingConfirmedOverlayProps) {
  const BOT = useBotColors();
  const reduced = useReducedMotion();

  const pop = useRef(new Animated.Value(reduced ? 1 : 0)).current;
  const rise = useRef(new Animated.Value(reduced ? 1 : 0)).current;

  useEffect(() => {
    if (reduced) return;
    Animated.sequence([
      Animated.spring(pop, { toValue: 1, friction: 5, tension: 90, useNativeDriver: true }),
      Animated.timing(rise, { toValue: 1, duration: 420, easing: Easing.out(Easing.cubic), useNativeDriver: true }),
    ]).start();
  }, [pop, rise, reduced]);

  const contentStyle = {
    opacity: rise,
    transform: [{ translateY: rise.interpolate({ inputRange: [0, 1], outputRange: [14, 0] }) }],
  };

  return (
    <View style={{ flex: 1, backgroundColor: BOT.bg }}>
      {!reduced ? <Confetti BOT={BOT} /> : null}

      <ScrollView
        contentContainerStyle={{
          flexGrow: 1, alignItems: "center", justifyContent: "center",
          paddingHorizontal: 28, paddingVertical: 40,
        }}
      >
        <Animated.View
          style={{
            width: 92, height: 92, borderRadius: 46,
            alignItems: "center", justifyContent: "center",
            backgroundColor: BOT.successBg,
            borderWidth: 2, borderColor: BOT.success,
            transform: reduced ? undefined : [{ scale: pop }],
          }}
        >
          <Ionicons name="checkmark" size={48} color={BOT.success} />
        </Animated.View>

        <Animated.View style={[{ alignItems: "center", width: "100%" }, contentStyle]}>
          <Text
            style={{
              fontSize: 24, fontWeight: "800", color: BOT.textPrimary,
              marginTop: 22, textAlign: "center",
            }}
          >
            You&apos;re booked
          </Text>
          <Text style={{ fontSize: 15, color: BOT.textSecondary, marginTop: 8, textAlign: "center" }}>
            {providerName
              ? `${providerName} has been notified and will be in touch.`
              : "We'll notify you as soon as a professional is assigned."}
          </Text>

          <View
            style={{
              width: "100%", marginTop: 24, borderRadius: 18, padding: 16,
              backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle,
            }}
          >
            <Row BOT={BOT} icon="receipt-outline" label="Booking" value={bookingNumber} mono />
            {slotLabel ? (
              <Row BOT={BOT} icon="time-outline" label="Arriving" value={slotLabel} />
            ) : (
              <Row BOT={BOT} icon="time-outline" label="Arriving"
                   value="Your provider will confirm a time" muted />
            )}
            {amountLabel ? (
              <Row BOT={BOT} icon="pricetag-outline" label="Visit fee" value={amountLabel} />
            ) : null}
            {providerName ? (
              <Row BOT={BOT} icon="person-outline" label="Technician" value={providerName} last />
            ) : null}
          </View>

          {/* The reassurance that matters most at this moment, stated only when
              the backend actually asserted the policy. */}
          {feeCreditedAgainstWork && amountLabel ? (
            <View
              style={{
                flexDirection: "row", gap: 8, alignItems: "flex-start", width: "100%",
                marginTop: 12, padding: 14, borderRadius: 14, backgroundColor: BOT.brandTint,
              }}
            >
              <Ionicons name="return-down-forward" size={16} color={BOT.brand} style={{ marginTop: 2 }} />
              <Text style={{ flex: 1, fontSize: 15, lineHeight: 21, color: BOT.textPrimary }}>
                Your {amountLabel} visit fee is{" "}
                <Text style={{ fontWeight: "800" }}>credited against the repair</Text> if you go
                ahead with the work.
              </Text>
            </View>
          ) : null}

          <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginTop: 16 }}>
            <Ionicons name="shield-checkmark" size={15} color={BOT.success} />
            <Text style={{ fontSize: 13, color: BOT.textTertiary }}>
              No work starts until you approve the price.
            </Text>
          </View>

          <Pressable
            onPress={onTrackBooking}
            accessibilityRole="button"
            accessibilityLabel="Track this booking"
            style={{
              width: "100%", height: 52, borderRadius: 18, marginTop: 26,
              alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand,
            }}
          >
            <Text style={{ fontSize: 16, fontWeight: "700", color: BOT.bubbleOnBrand }}>
              Track my booking
            </Text>
          </Pressable>

          <Pressable
            onPress={onDone}
            accessibilityRole="button"
            accessibilityLabel="Done"
            style={{ height: 44, marginTop: 6, alignItems: "center", justifyContent: "center" }}
          >
            <Text style={{ fontSize: 15, fontWeight: "600", color: BOT.textTertiary }}>Done</Text>
          </Pressable>
        </Animated.View>
      </ScrollView>
    </View>
  );
}

function Row({
  BOT, icon, label, value, mono, muted, last,
}: {
  BOT: ReturnType<typeof useBotColors>;
  icon: React.ComponentProps<typeof Ionicons>["name"];
  label: string;
  value: string;
  mono?: boolean;
  muted?: boolean;
  last?: boolean;
}) {
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: 10,
        paddingVertical: 10,
        borderBottomWidth: last ? 0 : 1,
        borderBottomColor: BOT.borderSubtle,
      }}
    >
      <Ionicons name={icon} size={15} color={BOT.textTertiary} />
      <Text style={{ fontSize: 15, color: BOT.textTertiary, flex: 1 }}>{label}</Text>
      <Text
        numberOfLines={1}
        style={{
          fontSize: 15, fontWeight: mono ? "700" : "600",
          color: muted ? BOT.textTertiary : BOT.textPrimary,
          flexShrink: 1, textAlign: "right",
        }}
      >
        {value}
      </Text>
    </View>
  );
}

/** Purely decorative falling pieces. Deterministic per mount (no re-randomising
 * on every render) and never blocks interaction -- pointerEvents is off, so the
 * Track button underneath is always tappable even mid-animation. */
function Confetti({ BOT }: { BOT: ReturnType<typeof useBotColors> }) {
  const { width } = Dimensions.get("window");
  const palette = [BOT.brand, BOT.success, BOT.warning, BOT.brandLight];

  const pieces = useMemo(
    () =>
      Array.from({ length: CONFETTI_COUNT }, (_, i) => ({
        key: `c${i}`,
        left: Math.random() * width,
        size: 6 + Math.random() * 6,
        color: palette[i % palette.length],
        delay: Math.random() * 700,
        drift: (Math.random() - 0.5) * 90,
        spin: Math.random() > 0.5 ? 1 : -1,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [width],
  );

  return (
    <View pointerEvents="none" style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
      {pieces.map(piece => (
        <ConfettiPiece {...piece} />
      ))}
    </View>
  );
}

function ConfettiPiece({
  left, size, color, delay, drift, spin,
}: {
  left: number; size: number; color: string; delay: number; drift: number; spin: number;
}) {
  const progress = useRef(new Animated.Value(0)).current;
  const { height } = Dimensions.get("window");

  useEffect(() => {
    Animated.timing(progress, {
      toValue: 1, duration: CONFETTI_MS, delay,
      easing: Easing.in(Easing.quad), useNativeDriver: true,
    }).start();
  }, [progress, delay]);

  return (
    <Animated.View
      style={{
        position: "absolute",
        left,
        top: -20,
        width: size,
        height: size * 1.6,
        borderRadius: 2,
        backgroundColor: color,
        opacity: progress.interpolate({ inputRange: [0, 0.1, 0.85, 1], outputRange: [0, 1, 1, 0] }),
        transform: [
          { translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [0, height + 60] }) },
          { translateX: progress.interpolate({ inputRange: [0, 1], outputRange: [0, drift] }) },
          {
            rotate: progress.interpolate({
              inputRange: [0, 1],
              outputRange: ["0deg", `${spin * 540}deg`],
            }),
          },
        ],
      }}
    />
  );
}
