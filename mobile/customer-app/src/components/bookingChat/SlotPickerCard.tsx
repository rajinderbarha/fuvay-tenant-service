import React, { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Pressable, View } from "react-native";

import { useTheme } from "../../design-system/theme";
import type { AvailableSlot, BookingReviewSummary } from "../../domain/bookingReview";
import { AppLucideIcon } from "../AppLucideIcon";
import { AppText } from "../AppText";
import { FuvayIcon } from "../FuvayIcon";
import { BotPrimaryButton } from "./BotPrimitives";
import { FuvayAssistantSheet } from "./FuvayAssistantSheet";

export interface SlotPickerCardProps {
  addressTitle: string;
  addressLine: string;
  promisedSlot: BookingReviewSummary["promisedSlot"];
  priceLabel: string | null;
  emergencySurchargeLabel: string | null;
  availableSlots: AvailableSlot[] | null;
  slotsLoading: boolean;
  slotSelectionError: string | null;
  onLoadSlots: (emergency: boolean) => void;
  onSelectSlot: (dateIso: string, timeWindow: string, emergency: boolean) => Promise<void>;
  onContinue: () => Promise<void>;
}

function dayLabel(dateIso: string, daysAhead: number): string {
  if (daysAhead === 0) return "Today";
  if (daysAhead === 1) return "Tomorrow";
  const date = new Date(`${dateIso}T00:00:00`);
  return Number.isNaN(date.getTime()) ? dateIso : date.toLocaleDateString(undefined, { weekday: "short" });
}

export function SlotPickerCard({
  addressTitle,
  addressLine,
  promisedSlot,
  priceLabel,
  emergencySurchargeLabel,
  availableSlots,
  slotsLoading,
  slotSelectionError,
  onLoadSlots,
  onSelectSlot,
  onContinue,
}: SlotPickerCardProps) {
  const { theme } = useTheme();
  const f = theme.fuvay;
  const [open, setOpen] = useState(false);
  const [emergency, setEmergency] = useState(false);
  const [pickingKey, setPickingKey] = useState<string | null>(null);
  const [continuing, setContinuing] = useState(false);
  const didAutoOpen = useRef(false);
  const groups = useMemo(() => {
    const byDay = new Map<string, AvailableSlot[]>();
    (availableSlots ?? []).forEach(slot => {
      const key = `${slot.date}|${slot.daysAhead}`;
      byDay.set(key, [...(byDay.get(key) ?? []), slot]);
    });
    return [...byDay.entries()].map(([key, slots]) => ({ key, slots, label: dayLabel(slots[0].date, slots[0].daysAhead) }));
  }, [availableSlots]);

  useEffect(() => {
    if (didAutoOpen.current) return;
    didAutoOpen.current = true;
    setOpen(true);
    onLoadSlots(false);
  }, [onLoadSlots]);

  function showPicker(nextEmergency = false) {
    setEmergency(nextEmergency);
    setOpen(true);
    onLoadSlots(nextEmergency);
  }

  async function pick(slot: AvailableSlot) {
    const key = `${slot.date}|${slot.timeWindow}`;
    setPickingKey(key);
    try {
      await onSelectSlot(slot.date, slot.timeWindow, emergency);
      setOpen(false);
    } finally {
      setPickingKey(null);
    }
  }

  async function continueFlow() {
    setContinuing(true);
    try { await onContinue(); } finally { setContinuing(false); }
  }

  return (
    <View style={{ gap: 14 }}>
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 10 }}>
        <View style={{ width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }}><FuvayIcon size={17} accessibilityLabel="Fuvay booking assistant" /></View>
        <View style={{ flex: 1, paddingHorizontal: 15, paddingVertical: 13, borderRadius: 18, borderTopLeftRadius: 4, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }}>
          <AppText variant="body" style={{ color: f.surfaces.text }}>Where should the technician come?</AppText>
        </View>
      </View>
      <View style={{ marginLeft: 42, alignSelf: "flex-end", maxWidth: "84%", paddingHorizontal: 13, paddingVertical: 11, borderRadius: 18, borderBottomRightRadius: 4, backgroundColor: f.soft(f.accents.a2), borderWidth: 1, borderColor: f.surfaces.edge, flexDirection: "row", alignItems: "center", gap: 10 }}>
        <AppLucideIcon name="map-marker-path" size={15} color={f.accents.a2} />
        <View style={{ flex: 1 }}><AppText variant="labelStrong" style={{ color: f.surfaces.text }}>{addressTitle}</AppText><AppText variant="caption" numberOfLines={1} style={{ color: f.surfaces.sub }}>{addressLine}</AppText></View>
        <AppLucideIcon name="pencil" size={13} color={f.accents.a2} />
      </View>
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 10 }}>
        <View style={{ width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }}><FuvayIcon size={17} accessibilityLabel="Fuvay booking assistant" /></View>
        <View style={{ flex: 1, paddingHorizontal: 15, paddingVertical: 13, borderRadius: 18, borderTopLeftRadius: 4, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }}>
          <AppText variant="body" style={{ color: f.surfaces.text }}>And when suits you? Pick any open slot — or choose emergency for a visit within 2 hours.</AppText>
        </View>
      </View>
      <Pressable accessibilityRole="button" accessibilityLabel="Pick a slot" onPress={() => showPicker(false)} style={({ pressed }) => ({ marginLeft: 42, alignSelf: "flex-end", minHeight: 40, paddingHorizontal: 16, borderRadius: 20, flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: f.soft(f.accents.a2), borderWidth: 1, borderColor: f.surfaces.edge, opacity: pressed ? theme.opacity.pressed : 1 })}>
        <AppLucideIcon name="calendar-clock" size={16} color={f.accents.a2} />
        <AppText variant="labelStrong" style={{ color: f.accents.a2 }}>{promisedSlot ? `${dayLabel(promisedSlot.date, promisedSlot.daysAhead)}, ${promisedSlot.timeWindow}` : "Pick a slot"}</AppText>
        <AppLucideIcon name="chevron-right" size={14} color={f.accents.a2} />
      </Pressable>
      {priceLabel ? <View style={{ paddingHorizontal: 14, paddingVertical: 12, borderRadius: 16, borderWidth: 1, borderColor: f.surfaces.edge, backgroundColor: f.surfaces.card, flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 }}><View style={{ flex: 1 }}><AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>Nothing due now</AppText><AppText variant="caption" style={{ color: f.surfaces.faint }}>Inspection fee is payable after the visit</AppText></View><AppText variant="numericMedium" style={{ color: f.surfaces.text }}>{priceLabel.replace(" inspection visit", "")}</AppText></View> : null}
      {promisedSlot ? <BotPrimaryButton label={continuing ? "Checking time…" : "Review booking  →"} onPress={continueFlow} disabled={continuing} loading={continuing} /> : null}

      <FuvayAssistantSheet visible={open} title="Choose a time" subtitle="All available slots · 2-hour arrival window" onClose={() => setOpen(false)} scroll>
        <Pressable accessibilityRole="button" accessibilityLabel="Emergency within 2 hours" onPress={() => showPicker(true)} style={{ minHeight: 58, paddingHorizontal: 14, borderRadius: 14, borderWidth: 1, borderColor: emergency ? f.accents.a1 : f.surfaces.edge, backgroundColor: f.surfaces.card, flexDirection: "row", alignItems: "center", gap: 12 }}>
          <View style={{ width: 38, height: 38, borderRadius: 19, alignItems: "center", justifyContent: "center", backgroundColor: f.soft(f.accents.a1) }}><AppLucideIcon name="lightning-bolt-outline" size={18} color={f.accents.a1} /></View>
          <View style={{ flex: 1 }}><AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>Emergency · within 2 hours</AppText><AppText variant="caption" style={{ color: f.surfaces.sub }}>Priority dispatch{emergencySurchargeLabel ? `, +${emergencySurchargeLabel}` : ""}</AppText></View>
          <AppLucideIcon name="chevron-right" size={16} color={f.accents.a1} />
        </Pressable>
        {slotSelectionError ? <AppText variant="caption" style={{ color: theme.colors.statusDanger }}>{slotSelectionError}</AppText> : null}
        {slotsLoading ? <ActivityIndicator color={f.accents.a2} /> : groups.map(group => (
          <View key={group.key} style={{ gap: 9 }}>
            <AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>{group.label}</AppText>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 9 }}>
              {group.slots.map(slot => {
                const key = `${slot.date}|${slot.timeWindow}`;
                const current = promisedSlot?.date === slot.date && promisedSlot?.timeWindow === slot.timeWindow;
                return <Pressable key={key} accessibilityRole="button" accessibilityLabel={`${group.label}, ${slot.timeWindow}`} disabled={pickingKey !== null} onPress={() => pick(slot)} style={({ pressed }) => ({ width: "31%", minHeight: 46, borderRadius: 12, alignItems: "center", justifyContent: "center", backgroundColor: current ? f.accents.a2 : f.surfaces.card, borderWidth: 1, borderColor: current ? f.accents.a2 : f.surfaces.edge, opacity: pressed ? theme.opacity.pressed : 1 })}>{pickingKey === key ? <ActivityIndicator size="small" color={f.accents.a2} /> : <AppText variant="labelStrong" style={{ color: current ? f.ink(f.accents.a2) : f.surfaces.text }}>{slot.timeWindow}</AppText>}</Pressable>;
              })}
            </View>
          </View>
        ))}
      </FuvayAssistantSheet>
    </View>
  );
}
