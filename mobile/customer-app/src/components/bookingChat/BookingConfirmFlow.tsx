import React, { useEffect, useRef } from "react";
import { ActivityIndicator, Animated, Easing, Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useTheme } from "../../design-system/theme";
import { AppLucideIcon } from "../AppLucideIcon";
import { AppText } from "../AppText";

export interface BookingConfirmFlowProps {
  phase: "confirming" | "confirmed";
  bookingNumber: string | null;
  providerName: string | null;
  slotLabel: string | null;
  amountLabel: string | null;
  feeCreditedAgainstWork: boolean;
  onTrackBooking: () => void;
  onDone: () => void;
  onBookAnother?: () => void;
}

const confettiPattern = [
  { left: "8%", delay: 0.01, turn: "180deg" },
  { left: "16%", delay: 0.08, turn: "-220deg" },
  { left: "25%", delay: 0.16, turn: "260deg" },
  { left: "35%", delay: 0.04, turn: "-190deg" },
  { left: "45%", delay: 0.2, turn: "300deg" },
  { left: "55%", delay: 0.1, turn: "-250deg" },
  { left: "65%", delay: 0.18, turn: "230deg" },
  { left: "74%", delay: 0.02, turn: "-280deg" },
  { left: "84%", delay: 0.14, turn: "210deg" },
  { left: "92%", delay: 0.06, turn: "-240deg" },
] as const;

function BookingCelebration() {
  const { theme } = useTheme();
  const f = theme.fuvay;
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.timing(progress, {
      toValue: 1,
      duration: f.motion.confirmationMs,
      easing: Easing.inOut(Easing.cubic),
      useNativeDriver: true,
    });
    animation.start();
    return () => animation.stop();
  }, [f.motion.confirmationMs, progress]);

  const opacity = progress.interpolate({
    inputRange: [0, f.motion.confirmationFadeInEnd, f.motion.confirmationFadeOutStart, 1],
    outputRange: [0, 1, 1, 0],
  });
  const badgeScale = progress.interpolate({ inputRange: [0, 0.12, 0.2, 1], outputRange: [0.45, 1.12, 1, 1] });
  const haloScale = progress.interpolate({ inputRange: [0, 0.45, 1], outputRange: [0.4, 1.35, 1.7] });
  const haloOpacity = progress.interpolate({ inputRange: [0, 0.25, 0.72, 1], outputRange: [0, 0.42, 0.12, 0] });
  const accents = [f.accents.a2, f.accents.a3, f.accents.a1, f.accents.a4];

  return (
    <Animated.View pointerEvents="none" accessibilityElementsHidden style={{ position: "absolute", top: 0, right: 0, bottom: 0, left: 0, zIndex: 20, alignItems: "center", justifyContent: "center", paddingHorizontal: 28, backgroundColor: f.surfaces.shell, opacity }}>
      {confettiPattern.map((piece, index) => {
        const start = piece.delay;
        const end = Math.min(start + 0.68, 0.9);
        return (
          <Animated.View key={`${piece.left}-${index}`} style={{ position: "absolute", left: piece.left, top: -18, width: index % 3 === 0 ? 7 : 5, height: index % 2 === 0 ? 15 : 10, borderRadius: 3, backgroundColor: accents[index % accents.length], opacity: progress.interpolate({ inputRange: [0, start, Math.min(start + 0.08, end), end, 1], outputRange: [0, 0, 1, 0.65, 0] }), transform: [{ translateY: progress.interpolate({ inputRange: [0, start, end, 1], outputRange: [-20, -20, 760, 820] }) }, { rotate: progress.interpolate({ inputRange: [0, end], outputRange: ["0deg", piece.turn] }) }] }} />
        );
      })}
      <View style={{ width: 220, height: 220, alignItems: "center", justifyContent: "center" }}>
        <Animated.View style={{ position: "absolute", width: 174, height: 174, borderRadius: 87, backgroundColor: f.soft(f.accents.a3), opacity: haloOpacity, transform: [{ scale: haloScale }] }} />
        <Animated.View style={{ width: 132, height: 132, borderRadius: 44, alignItems: "center", justifyContent: "center", backgroundColor: f.surfaces.panel, borderWidth: 2, borderColor: f.accents.a3, transform: [{ scale: badgeScale }] }}>
          <View style={{ width: 92, height: 92, borderRadius: 46, alignItems: "center", justifyContent: "center", borderWidth: 3, borderColor: f.accents.a3 }}>
            <AppLucideIcon name="check" size={48} color={f.accents.a3} strokeWidth={2.4} />
          </View>
        </Animated.View>
      </View>
      <AppText variant="metaLabel" align="center" style={{ marginTop: 12, color: f.accents.a3 }}>BOOKING CONFIRMED</AppText>
      <AppText variant="headingLarge" align="center" style={{ marginTop: 12, color: f.surfaces.text }}>You’re all set</AppText>
      <AppText variant="bodySmall" align="center" style={{ marginTop: 8, maxWidth: 300, color: f.surfaces.sub }}>Assigning the best technician for your slot — profile coming up.</AppText>
    </Animated.View>
  );
}

export function BookingConfirmFlow({
  phase,
  bookingNumber,
  providerName,
  slotLabel,
  amountLabel,
  feeCreditedAgainstWork,
  onTrackBooking,
  onDone,
  onBookAnother,
}: BookingConfirmFlowProps) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  const f = theme.fuvay;

  if (phase === "confirming") {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: 28, backgroundColor: f.surfaces.shell }}>
        <ActivityIndicator size="large" color={f.accents.a2} />
        <AppText variant="headingSmall" align="center" style={{ marginTop: 24, color: f.surfaces.text }}>Confirming your booking</AppText>
        <AppText variant="bodySmall" align="center" style={{ marginTop: 8, color: f.surfaces.sub }}>Please keep this screen open.</AppText>
      </View>
    );
  }

  const provider = providerName ?? "Your professional";
  return (
    <View style={{ flex: 1, paddingTop: Math.max(insets.top, 12), paddingBottom: Math.max(insets.bottom, 12), paddingHorizontal: 12, backgroundColor: f.surfaces.shell }}>
      <BookingCelebration />
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} showsVerticalScrollIndicator={false}>
        <View style={{ flex: 1, minHeight: 620, borderRadius: 30, paddingHorizontal: 20, paddingTop: 52, paddingBottom: 24, backgroundColor: f.surfaces.panel, borderWidth: 1, borderColor: f.surfaces.edge, alignItems: "center" }}>
          <View style={{ width: 98, height: 98, borderRadius: 49, alignItems: "center", justifyContent: "center", borderWidth: 3, borderColor: f.accents.a3 }}><AppLucideIcon name="check" size={44} color={f.accents.a3} strokeWidth={2.2} /></View>
          <AppText variant="headingLarge" align="center" style={{ marginTop: 28, color: f.surfaces.text }}>Booking confirmed</AppText>
          <AppText variant="bodySmall" align="center" style={{ marginTop: 8, color: f.surfaces.sub }}>{providerName ? (slotLabel ? `${provider} will arrive ${slotLabel}. You'll get a call before the visit.` : `${provider} has been notified. Your provider will confirm a time.`) : "We'll notify you as soon as a professional is assigned."}</AppText>
          {bookingNumber ? <View style={{ marginTop: 10, paddingHorizontal: 14, paddingVertical: 5, borderRadius: 99, backgroundColor: f.soft(f.accents.a3) }}><AppText variant="metaLabel" style={{ color: f.accents.a3 }}>ID · {bookingNumber}</AppText></View> : null}

          <View style={{ width: "100%", marginTop: 18, padding: 15, borderRadius: 18, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge, gap: 13 }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
              <View style={{ width: 56, height: 56, borderRadius: 16, backgroundColor: f.soft(f.accents.a2), alignItems: "center", justifyContent: "center" }}><AppLucideIcon name="person-outline" size={25} color={f.accents.a2} /></View>
              <View style={{ flex: 1 }}><AppText variant="title" style={{ color: f.surfaces.text }}>{provider}</AppText><AppText variant="caption" style={{ color: f.surfaces.sub }}>{providerName ? "Assigned professional" : "Assignment pending"}</AppText></View>
              <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: f.soft(f.accents.a3), alignItems: "center", justifyContent: "center" }}><AppLucideIcon name="phone" size={17} color={f.accents.a3} /></View>
              <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: f.soft(f.accents.a2), alignItems: "center", justifyContent: "center" }}><AppLucideIcon name="message-circle" size={17} color={f.accents.a2} /></View>
            </View>
            <View style={{ height: 1, backgroundColor: f.surfaces.rule }} />
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}>
              <View style={{ flex: 1, gap: 2 }}>
                <AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>Nothing charged yet</AppText>
                <AppText variant="caption" style={{ color: f.surfaces.sub }}>Pay after the inspection or completed work</AppText>
              </View>
              {amountLabel ? <AppText variant="numericMedium" style={{ color: f.surfaces.text }}>{amountLabel}</AppText> : null}
            </View>
          </View>

          {feeCreditedAgainstWork && amountLabel ? <View style={{ width: "100%", marginTop: 10, paddingHorizontal: 13, paddingVertical: 10, borderRadius: 13, backgroundColor: f.soft(f.accents.a3), flexDirection: "row", gap: 8 }}><AppLucideIcon name="shield-check-outline" size={15} color={f.accents.a3} /><AppText variant="caption" style={{ flex: 1, color: f.surfaces.sub }}>After inspection, {amountLabel} is credited against the repair if you approve the work.</AppText></View> : null}

          <Pressable accessibilityRole="button" accessibilityLabel="Track this booking" onPress={onTrackBooking} style={{ width: "100%", minHeight: 54, marginTop: 18, borderRadius: 27, backgroundColor: f.accents.a2, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 9 }}><AppText variant="button" style={{ color: f.ink(f.accents.a2) }}>Track booking</AppText><AppLucideIcon name="arrow-forward" size={16} color={f.ink(f.accents.a2)} /></Pressable>
          {onBookAnother ? <Pressable accessibilityRole="button" accessibilityLabel="Book another service" onPress={onBookAnother} style={{ width: "100%", minHeight: 52, marginTop: 10, borderRadius: 26, borderWidth: 1, borderColor: f.surfaces.edge, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 9 }}><AppText variant="button" style={{ color: f.surfaces.sub }}>Start new booking</AppText><AppLucideIcon name="plus" size={16} color={f.surfaces.sub} /></Pressable> : null}
          <Pressable accessibilityRole="button" accessibilityLabel="Done" onPress={onDone} style={{ width: "100%", minHeight: 50, marginTop: 8, paddingHorizontal: 20, borderRadius: 25, alignItems: "center", justifyContent: "center" }}><AppText variant="button" style={{ color: f.surfaces.sub, fontSize: 14 }}>Done</AppText></Pressable>
        </View>
      </ScrollView>
    </View>
  );
}
