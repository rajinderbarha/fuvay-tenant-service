import React, { useEffect, useMemo, useRef, useState } from "react";
import { View, Pressable, Animated, Easing, Dimensions, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useReducedMotion } from "../../design-system/theme";
import { useBotColors } from "./botTheme";
import { BotText } from "./BotText";

export interface BookingConfirmFlowProps {
  /** "confirming" while the backend call is in flight, "confirmed" once it has
   * genuinely returned a booking number. Driven by the real controller state --
   * this component never advances itself on a timer. */
  phase: "confirming" | "confirmed";
  bookingNumber: string | null;
  providerName: string | null;
  slotLabel: string | null;
  amountLabel: string | null;
  feeCreditedAgainstWork: boolean;
  onTrackBooking: () => void;
  onDone: () => void;
  /** Starts a brand-new request. Without this, the success screen was a dead end
   * -- the only exits led away from the tab, and coming back showed the same
   * stale "You're booked" because the confirmed booking is terminal. */
  onBookAnother?: () => void;
}

const CONFETTI_COUNT = 44;
/** Long enough to actually be seen. The first version was ~2.6s including a
 * random start delay, so late pieces barely appeared before the whole thing was
 * over -- it read as a flicker rather than a celebration. */
const CONFETTI_FALL_MS = 5200;
const CONFETTI_MAX_DELAY_MS = 1400;

/** The steps shown while the booking is being committed. These name real work
 * the backend performs on confirm (validating the draft, creating the booking
 * and job, notifying the provider) -- not invented filler. They are paced, but
 * the flow NEVER moves to "confirmed" on a timer: only the real API result does
 * that, so a slow backend keeps showing progress and a failure never lands on a
 * success screen. */
const PROCESSING_STEPS = [
  "Checking everything over…",
  "Reserving your time slot…",
  "Notifying your technician…",
  "Finishing up…",
];
const STEP_MS = 900;

/**
 * The moment the booking is committed: a full-bleed processing screen that turns
 * green and bursts into confetti the instant the backend confirms.
 *
 * The colour transition is the point -- a screen that visibly changes state
 * makes the outcome feel like it happened to you, rather than a card quietly
 * swapping in.
 */
export function BookingConfirmFlow({
  phase, bookingNumber, providerName, slotLabel, amountLabel,
  feeCreditedAgainstWork, onTrackBooking, onDone, onBookAnother,
}: BookingConfirmFlowProps) {
  const BOT = useBotColors();
  const reduced = useReducedMotion();
  // Full-screen overlay: it owns its own safe-area padding so the Done/Track
  // actions are never under the home indicator.
  const insets = useSafeAreaInsets();
  const confirmed = phase === "confirmed";

  // 0 = neutral processing background, 1 = success green.
  const wash = useRef(new Animated.Value(0)).current;
  const pop = useRef(new Animated.Value(0)).current;
  const details = useRef(new Animated.Value(0)).current;
  const [step, setStep] = useState(0);

  // Advance the processing copy while waiting. Stops at the last line rather
  // than looping, so it never implies more stages than there are.
  useEffect(() => {
    if (confirmed || reduced) return;
    if (step >= PROCESSING_STEPS.length - 1) return;
    const timer = setTimeout(() => setStep(n => n + 1), STEP_MS);
    return () => clearTimeout(timer);
  }, [step, confirmed, reduced]);

  useEffect(() => {
    if (!confirmed) return;
    if (reduced) {
      wash.setValue(1);
      pop.setValue(1);
      details.setValue(1);
      return;
    }
    Animated.parallel([
      Animated.timing(wash, {
        toValue: 1, duration: 620, easing: Easing.out(Easing.cubic), useNativeDriver: false,
      }),
      Animated.sequence([
        Animated.delay(120),
        Animated.spring(pop, { toValue: 1, friction: 5, tension: 90, useNativeDriver: true }),
      ]),
      Animated.sequence([
        Animated.delay(320),
        Animated.timing(details, {
          toValue: 1, duration: 420, easing: Easing.out(Easing.cubic), useNativeDriver: true,
        }),
      ]),
    ]).start();
  }, [confirmed, reduced, wash, pop, details]);

  // useNativeDriver must be false for colour, hence the separate animation above.
  const background = wash.interpolate({
    inputRange: [0, 1],
    outputRange: [BOT.bg, BOT.successBg],
  });

  return (
    <Animated.View style={{ flex: 1, backgroundColor: background }}>
      {confirmed && !reduced ? <Confetti BOT={BOT} /> : null}

      <ScrollView
        contentContainerStyle={{
          flexGrow: 1, alignItems: "center", justifyContent: "center",
          paddingHorizontal: 28,
          paddingTop: Math.max(insets.top, 12) + 28,
          paddingBottom: Math.max(insets.bottom, 12) + 28,
        }}
      >
        {!confirmed ? (
          <Processing BOT={BOT} reduced={reduced} label={PROCESSING_STEPS[step]} />
        ) : (
          <>
            <Animated.View
              style={{
                width: 96, height: 96, borderRadius: 48,
                alignItems: "center", justifyContent: "center",
                backgroundColor: BOT.surface,
                borderWidth: 3, borderColor: BOT.success,
                transform: reduced ? undefined : [{ scale: pop }],
              }}
            >
              <Ionicons name="checkmark" size={52} color={BOT.success} />
            </Animated.View>

            <Animated.View
              style={{
                alignItems: "center", width: "100%",
                opacity: details,
                transform: reduced
                  ? undefined
                  : [{ translateY: details.interpolate({ inputRange: [0, 1], outputRange: [16, 0] }) }],
              }}
            >
              <BotText
                style={{
                  fontSize: 26, fontWeight: "800", color: BOT.textPrimary,
                  marginTop: 22, textAlign: "center",
                }}
              >
                You&apos;re booked
              </BotText>
              <BotText style={{ fontSize: 15, color: BOT.textSecondary, marginTop: 8, textAlign: "center" }}>
                {providerName
                  ? `${providerName} has been notified and will be in touch.`
                  : "We'll notify you as soon as a professional is assigned."}
              </BotText>

              <View
                style={{
                  width: "100%", marginTop: 24, borderRadius: 18, padding: 16,
                  backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle,
                }}
              >
                {bookingNumber ? (
                  <Row BOT={BOT} icon="receipt-outline" label="Booking" value={bookingNumber} strong />
                ) : null}
                <Row
                  BOT={BOT} icon="time-outline" label="Arriving"
                  value={slotLabel ?? "Your provider will confirm a time"}
                  muted={!slotLabel}
                />
                {amountLabel ? (
                  <Row BOT={BOT} icon="pricetag-outline" label="Visit fee" value={amountLabel} />
                ) : null}
                {providerName ? (
                  <Row BOT={BOT} icon="person-outline" label="Technician" value={providerName} last />
                ) : null}
              </View>

              {feeCreditedAgainstWork && amountLabel ? (
                <View
                  style={{
                    flexDirection: "row", gap: 8, alignItems: "flex-start", width: "100%",
                    marginTop: 12, padding: 14, borderRadius: 14, backgroundColor: BOT.surface,
                  }}
                >
                  <Ionicons name="return-down-forward" size={16} color={BOT.brand} style={{ marginTop: 2 }} />
                  <BotText style={{ flex: 1, fontSize: 15, lineHeight: 21, color: BOT.textPrimary }}>
                    Your {amountLabel} visit fee is{" "}
                    <BotText style={{ fontWeight: "800" }}>credited against the repair</BotText> if you go
                    ahead with the work.
                  </BotText>
                </View>
              ) : null}

              <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginTop: 16 }}>
                <Ionicons name="shield-checkmark" size={15} color={BOT.success} />
                <BotText style={{ fontSize: 13, color: BOT.textTertiary }}>
                  No work starts until you approve the price.
                </BotText>
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
                <BotText style={{ fontSize: 16, fontWeight: "700", color: BOT.bubbleOnBrand }}>
                  Track my booking
                </BotText>
              </Pressable>

              {onBookAnother ? (
                <Pressable
                  onPress={onBookAnother}
                  accessibilityRole="button"
                  accessibilityLabel="Book another service"
                  style={{
                    width: "100%", height: 48, borderRadius: 18, marginTop: 10,
                    alignItems: "center", justifyContent: "center",
                    backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.border,
                  }}
                >
                  <BotText style={{ fontSize: 15, fontWeight: "700", color: BOT.textPrimary }}>
                    Book another service
                  </BotText>
                </Pressable>
              ) : null}

              <Pressable
                onPress={onDone}
                accessibilityRole="button"
                accessibilityLabel="Done"
                style={{ height: 44, marginTop: 6, alignItems: "center", justifyContent: "center" }}
              >
                <BotText style={{ fontSize: 15, fontWeight: "600", color: BOT.textTertiary }}>Done</BotText>
              </Pressable>
            </Animated.View>
          </>
        )}
      </ScrollView>
    </Animated.View>
  );
}

/** Spinner + the current real stage. */
function Processing({
  BOT, reduced, label,
}: { BOT: ReturnType<typeof useBotColors>; reduced: boolean; label: string }) {
  const spin = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (reduced) return;
    const spinning = Animated.loop(
      Animated.timing(spin, { toValue: 1, duration: 900, easing: Easing.linear, useNativeDriver: true }),
    );
    const pulsing = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 0.6, duration: 620, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 620, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    spinning.start();
    pulsing.start();
    return () => { spinning.stop(); pulsing.stop(); };
  }, [spin, pulse, reduced]);

  return (
    <View style={{ alignItems: "center" }}>
      <Animated.View
        style={{
          width: 72, height: 72, borderRadius: 36,
          borderWidth: 3, borderColor: BOT.borderSubtle, borderTopColor: BOT.brand,
          transform: reduced
            ? undefined
            : [{ rotate: spin.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] }) }],
        }}
      />
      <BotText style={{ fontSize: 20, fontWeight: "700", color: BOT.textPrimary, marginTop: 24 }}>
        Confirming your booking
      </BotText>
      <Animated.Text
        style={{
          fontSize: 15, color: BOT.textTertiary, marginTop: 8, textAlign: "center",
          opacity: reduced ? 1 : pulse,
        }}
      >
        {label}
      </Animated.Text>
      <BotText style={{ fontSize: 13, color: BOT.textDim, marginTop: 20, textAlign: "center" }}>
        Please keep this screen open.
      </BotText>
    </View>
  );
}

function Row({
  BOT, icon, label, value, strong, muted, last,
}: {
  BOT: ReturnType<typeof useBotColors>;
  icon: React.ComponentProps<typeof Ionicons>["name"];
  label: string;
  value: string;
  strong?: boolean;
  muted?: boolean;
  last?: boolean;
}) {
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10,
        borderBottomWidth: last ? 0 : 1, borderBottomColor: BOT.borderSubtle,
      }}
    >
      <Ionicons name={icon} size={15} color={BOT.textTertiary} />
      <BotText style={{ fontSize: 15, color: BOT.textTertiary, flex: 1 }}>{label}</BotText>
      <BotText
        numberOfLines={1}
        style={{
          fontSize: 15, fontWeight: strong ? "700" : "600",
          color: muted ? BOT.textTertiary : BOT.textPrimary,
          flexShrink: 1, textAlign: "right",
        }}
      >
        {value}
      </BotText>
    </View>
  );
}

/** Decorative falling pieces. pointerEvents off so the Track button underneath
 * stays tappable throughout. */
function Confetti({ BOT }: { BOT: ReturnType<typeof useBotColors> }) {
  const { width } = Dimensions.get("window");
  const palette = [BOT.brand, BOT.success, BOT.warning, BOT.brandLight, BOT.danger];

  const pieces = useMemo(
    () =>
      Array.from({ length: CONFETTI_COUNT }, (_, i) => ({
        id: `c${i}`,
        left: Math.random() * width,
        size: 7 + Math.random() * 7,
        color: palette[i % palette.length],
        delay: Math.random() * CONFETTI_MAX_DELAY_MS,
        drift: (Math.random() - 0.5) * 120,
        spin: Math.random() > 0.5 ? 1 : -1,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [width],
  );

  return (
    <View pointerEvents="none" style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
      {pieces.map(piece => (
        <ConfettiPiece
          key={piece.id}
          left={piece.left}
          size={piece.size}
          color={piece.color}
          delay={piece.delay}
          drift={piece.drift}
          spin={piece.spin}
        />
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
      toValue: 1, duration: CONFETTI_FALL_MS, delay,
      // Gentler than a pure quad fall, so pieces linger on screen instead of
      // dropping out almost immediately.
      easing: Easing.bezier(0.35, 0, 0.7, 1),
      useNativeDriver: true,
    }).start();
  }, [progress, delay]);

  return (
    <Animated.View
      style={{
        position: "absolute",
        left,
        top: -24,
        width: size,
        height: size * 1.6,
        borderRadius: 2,
        backgroundColor: color,
        opacity: progress.interpolate({ inputRange: [0, 0.06, 0.9, 1], outputRange: [0, 1, 1, 0] }),
        transform: [
          { translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [0, height + 80] }) },
          { translateX: progress.interpolate({ inputRange: [0, 1], outputRange: [0, drift] }) },
          {
            rotate: progress.interpolate({
              inputRange: [0, 1], outputRange: ["0deg", `${spin * 720}deg`],
            }),
          },
        ],
      }}
    />
  );
}
